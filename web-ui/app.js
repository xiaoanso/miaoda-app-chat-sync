import {
  getUserTokens,
  setUserTokens,
  readUserTokensFromForm,
  apiFetch,
  normalizeRepoUrl,
  updateTokenBadge,
} from './lib/api.js';
import { initTokenHelp } from './lib/token-help.js';

const STORAGE_PREFIX = 'repoJsonGenerator.';
const COMMAND_DESC = {
    sync: '增量同步：获取指定 commit 的变更文件及其完整内容',
    info: '变更分析：获取 commit 信息、diff 统计及变更详情',
    full: '完整快照：获取指定 commit 下所有文件的完整内容',
};

let currentCommand = 'sync';
let executionHistory = [];
let lastResult = null;
let lastResultJson = '';
let contentExpanded = false;
let debounceTimers = {};

const $ = (id) => document.getElementById(id);

function debounce(key, fn, delay = 500) {
    clearTimeout(debounceTimers[key]);
    debounceTimers[key] = setTimeout(fn, delay);
}

function showToast(message, type = 'success') {
    const toast = $('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function showLoading(show, text = '正在执行...') {
    $('loadingOverlay').classList.toggle('show', show);
    $('loadingText').textContent = text;
    $('executeBtn').disabled = show;
}

function showStatus(success, text) {
    $('statusBar').style.display = 'flex';
    $('statusDot').className = `status-dot ${success ? 'success' : 'error'}`;
    $('statusText').textContent = text;
}

function isValidRepoUrl(url) {
    try {
        const u = new URL(url);
        return ['http:', 'https:', 'git:'].includes(u.protocol) || url.includes('@');
    } catch {
        return /^git@[\w.-]+:[\w./-]+\.git$/.test(url);
    }
}

function saveForm() {
    const form = {
        repo: $('repoUrl').value.trim(),
        branch: $('branch').value.trim(),
        commit: $('commit').value.trim(),
        command: currentCommand,
        filter: $('fileFilter').value.trim(),
        exclude: $('excludeFilter').value.trim(),
        maxFiles: parseInt($('maxFiles').value, 10) || 50,
        versionLimit: parseInt($('versionLimit').value, 10) || 30,
    };
    localStorage.setItem(STORAGE_PREFIX + 'form', JSON.stringify(form));
}

function loadForm() {
    try {
        const raw = localStorage.getItem(STORAGE_PREFIX + 'form');
        if (!raw) return;
        const form = JSON.parse(raw);
        if (form.repo) $('repoUrl').value = form.repo;
        if (form.branch) $('branch').value = form.branch;
        if (form.commit) $('commit').value = form.commit;
        if (form.filter) $('fileFilter').value = form.filter;
        if (form.exclude) $('excludeFilter').value = form.exclude;
        if (form.maxFiles) $('maxFiles').value = form.maxFiles;
        if (form.versionLimit) $('versionLimit').value = form.versionLimit;
        if (form.command) selectCommand(form.command, false);
    } catch (_) {}
}

function saveHistory() {
    localStorage.setItem(STORAGE_PREFIX + 'history', JSON.stringify(executionHistory));
}

function loadHistoryFromStorage() {
    try {
        const raw = localStorage.getItem(STORAGE_PREFIX + 'history');
        if (raw) executionHistory = JSON.parse(raw);
    } catch (_) {
        executionHistory = [];
    }
    renderHistory();
}

function saveLastSummary(item) {
    try {
        const payload = JSON.stringify(item);
        if (payload.length > 1024 * 1024) return;
        localStorage.setItem(STORAGE_PREFIX + 'lastSummary', payload);
    } catch (_) {}
}

function loadLastSummary() {
    try {
        const raw = localStorage.getItem(STORAGE_PREFIX + 'lastSummary');
        if (!raw) return;
        const item = JSON.parse(raw);
        if (item.summaryHtml) {
            $('summaryCard').innerHTML = item.summaryHtml;
            $('summaryCard').classList.add('show');
            $('emptyState').style.display = 'none';
        }
    } catch (_) {}
}

function selectCommand(command, save = true) {
    currentCommand = command;
    document.querySelectorAll('.command-btn').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.command === command);
    });
    $('commandDesc').textContent = COMMAND_DESC[command] || '';
    $('maxFilesGroup').style.display = command === 'info' ? 'none' : 'block';
    if (save) saveForm();
}

function appendLog(text) {
    $('logOutput').value += text;
}

function setLog(text) {
    $('logOutput').value = text;
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach((b) => {
        b.classList.toggle('active', b.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
    $('tab-' + tabName).classList.add('active');
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function highlightJson(jsonStr) {
    return jsonStr
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"([^"\\]*(?:\\.[^"\\]*)*)"\s*:/g, '<span class="json-key">"$1"</span>:')
        .replace(/:\s*"([^"\\]*(?:\\.[^"\\]*)*)"/g, ': <span class="json-string">"$1"</span>')
        .replace(/:\s*(-?\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
        .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
        .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
}

function collapseFileContent(data) {
    const copy = JSON.parse(JSON.stringify(data));
    if (Array.isArray(copy.files)) {
        copy.files = copy.files.map((f) => {
            if (f.content && f.content.length > 200) {
                return { ...f, content: `[${f.content.length} chars collapsed]` };
            }
            return f;
        });
    }
    return copy;
}

function renderJsonOutput(data, expand = false) {
    contentExpanded = expand;
    const displayData = expand ? data : collapseFileContent(data);
    const jsonStr = JSON.stringify(displayData, null, 2);
    lastResultJson = JSON.stringify(data, null, 2);
    $('jsonOutput').innerHTML = highlightJson(jsonStr);
    $('jsonOutput').style.display = 'block';
    $('jsonToolbar').style.display = Array.isArray(data.files) && data.files.some((f) => f.content) ? 'flex' : 'none';
    $('emptyState').style.display = 'none';
}

function buildSummaryHtml(result, meta) {
    if (!result.success) {
        return `<h3>执行失败</h3><p>${escapeHtml(result.error || '未知错误')}</p>`;
    }
    const data = result.data || {};
    const summary = data.summary || {};
    const source = data.source || {};
    const items = [
        ['命令', meta.command],
        ['耗时', `${meta.duration}s`],
        ['仓库', source.repository || meta.repo],
        ['分支', source.branch || meta.branch],
        ['Commit', (source.commit || meta.commit || '').slice(0, 12)],
    ];
    if (summary.files_changed != null) items.push(['变更文件', summary.files_changed]);
    if (summary.total_additions != null) items.push(['新增行', `+${summary.total_additions}`]);
    if (summary.total_deletions != null) items.push(['删除行', `-${summary.total_deletions}`]);
    if (summary.files_processed != null) items.push(['已处理', summary.files_processed]);
    if (summary.total_files_in_commit != null) items.push(['Commit 文件总数', summary.total_files_in_commit]);

    const grid = items.map(([k, v]) =>
        `<div class="summary-item"><span>${escapeHtml(k)}</span><strong>${escapeHtml(String(v))}</strong></div>`
    ).join('');
    return `<h3>执行摘要</h3><div class="summary-grid">${grid}</div>`;
}

function showResult(result) {
    lastResult = result;
    const meta = result.meta || {};
    const summaryHtml = buildSummaryHtml(result, meta);
    const card = $('summaryCard');
    card.innerHTML = summaryHtml;
    card.className = 'summary-card show' + (result.success ? '' : ' error');
    saveLastSummary({ summaryHtml, success: result.success, time: Date.now() });

    if (result.success && result.data) {
        const size = JSON.stringify(result.data).length;
        renderJsonOutput(result.data, size <= 500 * 1024);
        showStatus(true, `执行成功 (${meta.duration || 0}s)`);
        showToast('命令执行成功！');
    } else {
        $('jsonOutput').style.display = 'none';
        $('jsonToolbar').style.display = 'none';
        $('emptyState').style.display = 'block';
        $('emptyState').querySelector('p').textContent = result.error || '执行失败，请查看日志';
        showStatus(false, result.error || '执行失败');
        showToast(result.error || '执行失败', 'error');
        switchTab('log');
    }
}

function loadTokens() {
  const tokens = getUserTokens();
  $('githubToken').value = tokens.github;
  $('gitlabToken').value = tokens.gitlab;
  $('bitbucketToken').value = tokens.bitbucket;
  updateTokenBadge($('tokenBadge'));
}

function saveTokens(showMessage = true) {
  setUserTokens(readUserTokensFromForm({
    githubToken: $('githubToken').value,
    gitlabToken: $('gitlabToken').value,
    bitbucketToken: $('bitbucketToken').value,
  }));
  updateTokenBadge($('tokenBadge'));
  if (showMessage) showToast('Token 已保存');
}

function readTokensFromForm() {
  return readUserTokensFromForm({
    githubToken: $('githubToken').value,
    gitlabToken: $('gitlabToken').value,
    bitbucketToken: $('bitbucketToken').value,
  });
}

async function loadBranches(manual = false) {
    const repo = normalizeRepoUrl($('repoUrl').value.trim());
    const btn = $('loadBranchBtn');
    if (!repo) {
        if (manual) showToast('请先输入仓库地址', 'error');
        return;
    }
    if (!isValidRepoUrl(repo)) {
        $('repoHint').textContent = '请输入有效的 Git 仓库 URL';
        $('repoUrl').classList.add('invalid');
        if (manual) showToast('仓库 URL 格式无效', 'error');
        return;
    }
    $('repoHint').textContent = '';
    $('repoUrl').classList.remove('invalid');

    btn.classList.add('loading');
    btn.disabled = true;
    try {
        const res = await apiFetch(
            `/api/branches?repo=${encodeURIComponent(repo)}`,
            { signal: AbortSignal.timeout(120000) },
            readTokensFromForm()
        );
        const result = await res.json();
        if (!result.success) throw new Error(result.error || '加载分支失败');

        const datalist = $('branchList');
        datalist.innerHTML = '';
        const branches = result.branches || [];
        branches.forEach((b) => {
            const opt = document.createElement('option');
            opt.value = b;
            datalist.appendChild(opt);
        });

        if (branches.length > 0) {
            const current = $('branch').value.trim();
            if (!current || !branches.includes(current)) {
                const preferred = branches.find((b) => b === 'main' || b === 'master') || branches[0];
                $('branch').value = preferred;
            }
            if (manual) showToast(`已加载 ${branches.length} 个分支`);
            debounce('commits', () => loadCommits(false), 300);
        } else if (manual) {
            showToast('未找到远程分支', 'error');
        }
        saveForm();
    } catch (e) {
        if (manual) showToast(`加载失败: ${e.message}`, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

async function loadCommits(manual = false) {
    const repo = normalizeRepoUrl($('repoUrl').value.trim());
    const branch = $('branch').value.trim();
    const limit = parseInt($('versionLimit').value, 10) || 30;
    const btn = $('loadCommitBtn');

    if (!repo || !branch) {
        if (manual) showToast('请先填写仓库和分支', 'error');
        return;
    }

    btn.classList.add('loading');
    btn.disabled = true;
    try {
        const url = `/api/commits?repo=${encodeURIComponent(repo)}&branch=${encodeURIComponent(branch)}&limit=${limit}`;
        const res = await apiFetch(url, { signal: AbortSignal.timeout(120000) }, readTokensFromForm());
        const result = await res.json();
        if (!result.success) throw new Error(result.error || '加载版本失败');

        const datalist = $('commitList');
        datalist.innerHTML = '';
        const commits = result.commits || [];
        commits.forEach((c) => {
            const opt = document.createElement('option');
            opt.value = c.hash;
            const label = `${c.short_hash || c.hash.slice(0, 7)} · ${c.message || '(无消息)'} · ${c.date || ''}`;
            opt.label = label;
            datalist.appendChild(opt);
        });

        if (manual) showToast(`已加载 ${commits.length} 个版本`);
        saveForm();
    } catch (e) {
        if (manual) showToast(`加载失败: ${e.message}`, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

async function executeCommand() {
    const repo = normalizeRepoUrl($('repoUrl').value.trim());
    const branch = $('branch').value.trim() || 'main';
    const commit = $('commit').value.trim();
    const filter = $('fileFilter').value.trim();
    const exclude = $('excludeFilter').value.trim();
    const maxFiles = parseInt($('maxFiles').value, 10) || 50;

    if (!repo) {
        showToast('请输入仓库地址', 'error');
        return;
    }
    if (!isValidRepoUrl(repo)) {
        $('repoHint').textContent = '请输入有效的 Git 仓库 URL';
        $('repoUrl').classList.add('invalid');
        return;
    }

    const requestData = { command: currentCommand, repo, branch, commit, filter, exclude, maxFiles };
    saveForm();

    showLoading(true, '正在连接仓库...');
    setLog(`[${new Date().toLocaleString()}] 开始执行 ${currentCommand}\n`);
    appendLog(`请求: ${JSON.stringify(requestData, null, 2)}\n\n`);

    try {
        showLoading(true, '正在克隆仓库并生成 JSON...');
        const start = Date.now();
        const response = await apiFetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData),
            signal: AbortSignal.timeout(600000),
        }, readTokensFromForm());
        const result = await response.json();
        const duration = ((Date.now() - start) / 1000).toFixed(1);

        appendLog(`响应: HTTP ${response.status}\n`);
        appendLog(`耗时: ${duration}s\n`);
        if (result.meta) appendLog(`Meta: ${JSON.stringify(result.meta, null, 2)}\n\n`);

        if (result.success) {
            appendLog('✅ 执行成功\n');
        } else {
            appendLog(`❌ 执行失败: ${result.error || '未知错误'}\n`);
        }

        showResult(result);
        addToHistory(currentCommand, repo, branch, !!result.success, result.meta?.duration || duration);
        switchTab('json');
    } catch (error) {
        appendLog(`❌ 网络错误: ${error.message}\n`);
        showStatus(false, `网络错误: ${error.message}`);
        showToast('请求失败，请检查服务器连接', 'error');
    } finally {
        showLoading(false);
    }
}

function clearOutput() {
    $('jsonOutput').innerHTML = '';
    $('jsonOutput').style.display = 'none';
    $('logOutput').value = '';
    $('emptyState').style.display = 'block';
    $('emptyState').querySelector('p').innerHTML = '等待执行...<br>配置参数后点击「执行」或按 Ctrl+Enter';
    $('summaryCard').classList.remove('show');
    $('summaryCard').innerHTML = '';
    $('jsonToolbar').style.display = 'none';
    $('statusBar').style.display = 'none';
    lastResult = null;
    lastResultJson = '';
}

function copyOutput() {
    const text = lastResultJson || $('jsonOutput').textContent;
    if (!text) {
        showToast('没有可复制的内容', 'error');
        return;
    }
    navigator.clipboard.writeText(text).then(() => showToast('已复制到剪贴板')).catch(() => showToast('复制失败', 'error'));
}

function downloadOutput() {
    const text = lastResultJson || $('jsonOutput').textContent;
    if (!text) {
        showToast('没有可下载的内容', 'error');
        return;
    }
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `generator-${currentCommand}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('文件已下载');
}

function addToHistory(command, repo, branch, success, duration) {
    executionHistory.unshift({
        id: Date.now().toString(),
        command,
        repo,
        branch,
        success,
        duration,
        time: new Date().toLocaleString('zh-CN'),
    });
    if (executionHistory.length > 20) executionHistory.pop();
    saveHistory();
    renderHistory();
}

function renderHistory() {
    const list = $('historyList');
    if (executionHistory.length === 0) {
        list.innerHTML = '<p style="text-align:center;color:var(--text-secondary);font-size:0.85rem;">暂无历史记录</p>';
        return;
    }
    list.innerHTML = executionHistory.map((item) => `
        <div class="history-item" data-id="${escapeHtml(item.id)}">
            <div class="time">${escapeHtml(item.time)}</div>
            <div class="cmd">${escapeHtml(item.command)} - ${escapeHtml(item.branch)}</div>
            <div class="status ${item.success ? 'ok' : 'err'}">${item.success ? '✅ 成功' : '❌ 失败'} (${escapeHtml(String(item.duration))}s)</div>
        </div>
    `).join('');
}

function restoreHistoryItem(id) {
    const item = executionHistory.find((h) => h.id === id);
    if (!item) return;
    $('repoUrl').value = item.repo;
    $('branch').value = item.branch;
    selectCommand(item.command);
    saveForm();
    debounce('branches', () => loadBranches(false), 200);
    showToast('已恢复历史配置');
}

function bindEvents() {
    document.querySelectorAll('.command-btn').forEach((btn) => {
        btn.addEventListener('click', () => selectCommand(btn.dataset.command));
    });

    document.querySelectorAll('.tab-btn').forEach((btn) => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    $('tokenToggle').addEventListener('click', () => {
        $('tokenToggle').classList.toggle('open');
        $('tokenPanel').classList.toggle('show');
    });

    $('optionsToggle').addEventListener('click', () => {
        $('optionsToggle').classList.toggle('open');
        $('optionsPanel').classList.toggle('show');
    });

    $('historyToggle').addEventListener('click', () => {
        $('historyToggle').classList.toggle('open');
        $('historyPanel').classList.toggle('show');
    });

    $('saveTokensBtn').addEventListener('click', () => saveTokens(true));
    ['githubToken', 'gitlabToken', 'bitbucketToken'].forEach((id) => {
        $(id).addEventListener('input', () => updateTokenBadge($('tokenBadge'), readTokensFromForm()));
    });

    initTokenHelp({
        overlay: 'tokenHelpOverlay',
        title: 'tokenHelpTitle',
        body: 'tokenHelpBody',
        link: 'tokenHelpLink',
        close: 'tokenHelpClose',
    });

    $('executeBtn').addEventListener('click', executeCommand);
    $('clearBtn').addEventListener('click', clearOutput);
    $('copyBtn').addEventListener('click', copyOutput);
    $('downloadBtn').addEventListener('click', downloadOutput);
    $('loadBranchBtn').addEventListener('click', () => loadBranches(true));
    $('loadCommitBtn').addEventListener('click', () => loadCommits(true));

    $('expandContentBtn').addEventListener('click', () => {
        if (lastResult?.data) renderJsonOutput(lastResult.data, true);
    });
    $('collapseContentBtn').addEventListener('click', () => {
        if (lastResult?.data) renderJsonOutput(lastResult.data, false);
    });

    $('historyList').addEventListener('click', (e) => {
        const item = e.target.closest('.history-item');
        if (item?.dataset.id) restoreHistoryItem(item.dataset.id);
    });

    $('repoUrl').addEventListener('input', () => {
        $('repoHint').textContent = '';
        $('repoUrl').classList.remove('invalid');
        saveForm();
        debounce('branches', () => loadBranches(false), 600);
    });

    $('repoUrl').addEventListener('blur', () => {
        if ($('repoUrl').value.trim()) loadBranches(false);
    });

    $('branch').addEventListener('change', () => {
        saveForm();
        debounce('commits', () => loadCommits(false), 400);
    });

    $('branch').addEventListener('input', saveForm);
    $('commit').addEventListener('input', saveForm);
    $('fileFilter').addEventListener('input', saveForm);
    $('excludeFilter').addEventListener('input', saveForm);
    $('maxFiles').addEventListener('change', saveForm);
    $('versionLimit').addEventListener('change', saveForm);

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            executeCommand();
        }
        if (e.key === 'Escape' && !$('executeBtn').disabled) {
            showLoading(false);
        }
    });
}

function init() {
    bindEvents();
    loadForm();
    loadTokens();
    loadHistoryFromStorage();
    loadLastSummary();
    if ($('repoUrl').value.trim()) {
        debounce('branches', () => loadBranches(false), 300);
    }
}

init();
