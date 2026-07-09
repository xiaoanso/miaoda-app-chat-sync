import {
  getSettings,
  setSettings,
  checkServerStatus,
  fetchBranches,
  fetchCommits,
  generateJson,
} from '../lib/api.js';
import { storageGet, storageSet } from '../lib/storage.js';

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
let serverUrl = 'http://localhost:8080';
let serverOnline = false;
let versionLimit = 30;
let userEdited = false;
let autoFilled = { repo: '', branch: '', commit: '' };
let inputMode = 'manual';

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
  $('executeBtn').disabled = show || !serverOnline;
}

function showStatus(success, text) {
  $('statusBar').style.display = 'flex';
  $('statusDot').className = `status-dot ${success ? 'success' : 'error'}`;
  $('statusText').textContent = text;
}

function updateSourceTag(mode) {
  inputMode = mode;
  const tag = $('sourceTag');
  tag.textContent = mode === 'page' ? '来自当前页面' : '手动输入';
  tag.className = `source-tag ${mode}`;
}

function isValidRepoUrl(url) {
  try {
    const u = new URL(url);
    return ['http:', 'https:', 'git:'].includes(u.protocol) || url.includes('@');
  } catch {
    return /^git@[\w.-]+:[\w./-]+\.git$/.test(url);
  }
}

function markUserEdited() {
  userEdited = true;
  updateSourceTag('manual');
}

function setFieldValue(id, value, fromAuto = false) {
  const el = $(id);
  const key = id === 'repoUrl' ? 'repo' : id;
  const current = el.value.trim();

  if (fromAuto) {
    if (userEdited) return;
    if (current && current !== (autoFilled[key] || '')) return;
    el.value = value || '';
    autoFilled[key] = value || '';
  } else {
    el.value = value || '';
  }
}

async function saveForm() {
  const form = {
    repo: $('repoUrl').value.trim(),
    branch: $('branch').value.trim(),
    commit: $('commit').value.trim(),
    command: currentCommand,
    filter: $('fileFilter').value.trim(),
    exclude: $('excludeFilter').value.trim(),
    maxFiles: parseInt($('maxFiles').value, 10) || 50,
    userEdited,
    inputMode,
  };
  await storageSet('form', form);
}

async function loadForm() {
  try {
    const form = await storageGet('form');
    if (!form) return;
    if (form.repo) $('repoUrl').value = form.repo;
    if (form.branch) $('branch').value = form.branch;
    if (form.commit) $('commit').value = form.commit;
    if (form.filter) $('fileFilter').value = form.filter;
    if (form.exclude) $('excludeFilter').value = form.exclude;
    if (form.maxFiles) $('maxFiles').value = form.maxFiles;
    if (form.command) selectCommand(form.command, false);
    userEdited = !!form.userEdited;
    updateSourceTag(form.inputMode || (userEdited ? 'manual' : 'manual'));
  } catch (_) {}
}

async function saveHistory() {
  await storageSet('history', executionHistory);
}

async function loadHistoryFromStorage() {
  try {
    executionHistory = (await storageGet('history')) || [];
  } catch {
    executionHistory = [];
  }
  renderHistory();
}

async function saveLastSummary(item) {
  try {
    const payload = JSON.stringify(item);
    if (payload.length > 1024 * 1024) return;
    await storageSet('lastSummary', item);
  } catch (_) {}
}

async function loadLastSummary() {
  try {
    const item = await storageGet('lastSummary');
    if (item?.summaryHtml) {
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
  document.querySelectorAll('.output-tabs .tab-btn').forEach((b) => {
    b.classList.toggle('active', b.dataset.tab === tabName);
  });
  document.querySelectorAll('#view-result .tab-content').forEach((c) => c.classList.remove('active'));
  $('tab-' + tabName).classList.add('active');
}

function switchMainView(viewName) {
  document.querySelectorAll('.main-tab-btn').forEach((b) => {
    b.classList.toggle('active', b.dataset.view === viewName);
  });
  document.querySelectorAll('.main-view').forEach((v) => v.classList.remove('active'));
  $('view-' + viewName).classList.add('active');
  if (viewName === 'settings') loadSettingsPanel();
}

async function loadSettingsPanel() {
  const settings = await getSettings();
  $('settingsServerUrl').value = settings.serverUrl;
  $('settingsDefaultCommand').value = settings.defaultCommand;
  $('settingsVersionLimit').value = settings.versionLimit;
}

function showSettingsStatus(ok, msg) {
  const el = $('settingsStatus');
  el.textContent = msg;
  el.className = `settings-status ${ok ? 'ok' : 'err'}`;
}

async function saveSettings() {
  const serverUrlInput = $('settingsServerUrl').value.trim().replace(/\/$/, '');
  const defaultCommand = $('settingsDefaultCommand').value;
  const limit = parseInt($('settingsVersionLimit').value, 10) || 30;

  if (!serverUrlInput) {
    showSettingsStatus(false, '请输入后端服务地址');
    return;
  }

  await setSettings({ serverUrl: serverUrlInput, defaultCommand, versionLimit: limit });
  serverUrl = serverUrlInput;
  versionLimit = limit;
  selectCommand(defaultCommand, false);
  await refreshServerStatus();
  showSettingsStatus(true, '设置已保存');
  showToast('设置已保存');
}

async function testSettingsConnection() {
  const serverUrlInput = $('settingsServerUrl').value.trim().replace(/\/$/, '');
  if (!serverUrlInput) {
    showSettingsStatus(false, '请输入后端服务地址');
    return;
  }

  showSettingsStatus(true, '正在测试连接...');
  const status = await checkServerStatus(serverUrlInput);
  if (status.online) {
    showSettingsStatus(
      true,
      `连接成功！GITHUB_TOKEN ${status.hasToken ? '已配置' : '未配置（私有仓库可能失败）'}`
    );
  } else {
    showSettingsStatus(false, '连接失败。请确认已运行 python3 web-ui/server.py');
  }
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
  $('jsonToolbar').style.display =
    Array.isArray(data.files) && data.files.some((f) => f.content) ? 'flex' : 'none';
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

  const grid = items
    .map(
      ([k, v]) =>
        `<div class="summary-item"><span>${escapeHtml(k)}</span><strong>${escapeHtml(String(v))}</strong></div>`
    )
    .join('');
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
    switchMainView('result');
    switchTab('log');
  }
}

async function refreshServerStatus() {
  const settings = await getSettings();
  serverUrl = settings.serverUrl;
  const status = await checkServerStatus(serverUrl);

  serverOnline = status.online;
  const serverBadge = $('serverBadge');
  const tokenBadge = $('tokenBadge');
  const offlineBanner = $('offlineBanner');
  const executeBtn = $('executeBtn');

  if (status.online) {
    serverBadge.textContent = `后端在线 · ${serverUrl}`;
    serverBadge.className = 'badge ok';
    offlineBanner.classList.remove('show');
    executeBtn.disabled = false;

    if (status.hasToken) {
      tokenBadge.textContent = 'GITHUB_TOKEN 已配置';
      tokenBadge.className = 'badge ok';
    } else {
      tokenBadge.textContent = 'GITHUB_TOKEN 未配置';
      tokenBadge.className = 'badge warn';
    }
  } else {
    serverBadge.textContent = `后端离线 · ${serverUrl}`;
    serverBadge.className = 'badge error';
    tokenBadge.textContent = '无法检测 Token';
    tokenBadge.className = 'badge warn';
    offlineBanner.classList.add('show');
    executeBtn.disabled = true;
  }
}

async function applyPageContext(ctx, force = false) {
  if (!ctx?.repo) return false;

  if (force) {
    userEdited = false;
    autoFilled = { repo: '', branch: '', commit: '' };
  }

  if (!force && userEdited) return false;

  if (ctx.repo) setFieldValue('repoUrl', ctx.repo, true);
  if (ctx.branch) setFieldValue('branch', ctx.branch, true);
  if (ctx.commit) setFieldValue('commit', ctx.commit, true);

  updateSourceTag('page');
  await saveForm();

  if (ctx.repo) debounce('branches', () => loadBranches(false), 300);
  return true;
}

async function fillFromCurrentPage() {
  const response = await chrome.runtime.sendMessage({ type: 'GET_TAB_CONTEXT' });
  const ctx = response?.context;
  if (!ctx?.repo) {
    showToast('当前页面未识别到 Git 仓库', 'error');
    return;
  }
  const applied = await applyPageContext(ctx, true);
  if (applied) showToast('已从当前页面填充');
}

async function tryAutoFillFromTab() {
  const session = await chrome.storage.session.get(['pendingFillTabId', 'pageContexts']);
  let tabId = session.pendingFillTabId;

  const response = await chrome.runtime.sendMessage({ type: 'GET_TAB_CONTEXT' });
  const ctx = (tabId && session.pageContexts?.[tabId]) || response?.context;

  if (session.pendingFillTabId) {
    await chrome.storage.session.remove('pendingFillTabId');
  }

  if (ctx?.repo && !userEdited) {
    await applyPageContext(ctx, false);
  }
}

async function loadBranches(manual = false) {
  if (!serverOnline) {
    if (manual) showToast('后端未连接', 'error');
    return;
  }

  const repo = $('repoUrl').value.trim();
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
    const result = await fetchBranches(serverUrl, repo);
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
  if (!serverOnline) {
    if (manual) showToast('后端未连接', 'error');
    return;
  }

  const repo = $('repoUrl').value.trim();
  const branch = $('branch').value.trim();
  const limit = versionLimit || 30;
  const btn = $('loadCommitBtn');

  if (!repo || !branch) {
    if (manual) showToast('请先填写仓库和分支', 'error');
    return;
  }

  btn.classList.add('loading');
  btn.disabled = true;
  try {
    const result = await fetchCommits(serverUrl, repo, branch, limit);
    if (!result.success) throw new Error(result.error || '加载版本失败');

    const datalist = $('commitList');
    datalist.innerHTML = '';
    const commits = result.commits || [];
    commits.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.hash;
      opt.label = `${c.short_hash || c.hash.slice(0, 7)} · ${c.message || '(无消息)'} · ${c.date || ''}`;
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
  if (!serverOnline) {
    showToast('后端未连接，请先启动 server.py', 'error');
    return;
  }

  const repo = $('repoUrl').value.trim();
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
    const result = await generateJson(serverUrl, requestData);
    const duration = ((Date.now() - start) / 1000).toFixed(1);

    appendLog(`响应: success=${result.success}\n`);
    appendLog(`耗时: ${duration}s\n`);
    if (result.meta) appendLog(`Meta: ${JSON.stringify(result.meta, null, 2)}\n\n`);

    if (result.success) {
      appendLog('✅ 执行成功\n');
    } else {
      appendLog(`❌ 执行失败: ${result.error || '未知错误'}\n`);
    }

    showResult(result);
    addToHistory(currentCommand, repo, branch, !!result.success, result.meta?.duration || duration);
    switchMainView('result');
    switchTab('json');
  } catch (error) {
    appendLog(`❌ 网络错误: ${error.message}\n`);
    showStatus(false, `网络错误: ${error.message}`);
    showToast('请求失败，请检查后端连接', 'error');
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
    list.innerHTML = '<p class="empty-hint">暂无历史记录</p>';
    return;
  }
  list.innerHTML = executionHistory
    .map(
      (item) => `
    <div class="history-item" data-id="${escapeHtml(item.id)}">
      <div class="time">${escapeHtml(item.time)}</div>
      <div class="cmd">${escapeHtml(item.command)} - ${escapeHtml(item.branch)}</div>
      <div class="status ${item.success ? 'ok' : 'err'}">${item.success ? '✅ 成功' : '❌ 失败'} (${escapeHtml(String(item.duration))}s)</div>
    </div>`
    )
    .join('');
}

async function restoreHistoryItem(id) {
  const item = executionHistory.find((h) => h.id === id);
  if (!item) return;
  userEdited = true;
  $('repoUrl').value = item.repo;
  $('branch').value = item.branch;
  selectCommand(item.command);
  updateSourceTag('manual');
  await saveForm();
  debounce('branches', () => loadBranches(false), 200);
  showToast('已恢复历史配置');
}

function bindEvents() {
  document.querySelectorAll('.command-btn').forEach((btn) => {
    btn.addEventListener('click', () => selectCommand(btn.dataset.command));
  });

  document.querySelectorAll('.output-tabs .tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  document.querySelectorAll('.main-tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => switchMainView(btn.dataset.view));
  });

  $('optionsToggle').addEventListener('click', () => {
    $('optionsToggle').classList.toggle('open');
    $('optionsPanel').classList.toggle('show');
  });

  $('historyToggle').addEventListener('click', () => {
    $('historyToggle').classList.toggle('open');
    $('historyPanel').classList.toggle('show');
  });

  $('executeBtn').addEventListener('click', executeCommand);
  $('clearBtn').addEventListener('click', clearOutput);
  $('copyBtn').addEventListener('click', copyOutput);
  $('downloadBtn').addEventListener('click', downloadOutput);
  $('loadBranchBtn').addEventListener('click', () => loadBranches(true));
  $('loadCommitBtn').addEventListener('click', () => loadCommits(true));
  $('fillFromPageBtn').addEventListener('click', fillFromCurrentPage);

  $('sourceTag').addEventListener('click', () => {
    markUserEdited();
    showToast('已切换为手动输入模式');
  });

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
    markUserEdited();
    $('repoHint').textContent = '';
    $('repoUrl').classList.remove('invalid');
    saveForm();
    debounce('branches', () => loadBranches(false), 600);
  });

  $('repoUrl').addEventListener('blur', () => {
    if ($('repoUrl').value.trim()) loadBranches(false);
  });

  ['branch', 'commit', 'fileFilter', 'excludeFilter'].forEach((id) => {
    $(id).addEventListener('input', () => {
      markUserEdited();
      saveForm();
    });
  });

  $('branch').addEventListener('change', () => {
    markUserEdited();
    saveForm();
    debounce('commits', () => loadCommits(false), 400);
  });

  $('maxFiles').addEventListener('change', saveForm);
  $('saveSettingsBtn').addEventListener('click', saveSettings);
  $('testSettingsBtn').addEventListener('click', testSettingsConnection);

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      executeCommand();
    }
    if (e.key === 'Escape' && !$('executeBtn').disabled) {
      showLoading(false);
    }
  });

  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'sync') {
      if (changes.serverUrl) refreshServerStatus();
      if (changes.versionLimit) versionLimit = changes.versionLimit.newValue || 30;
      if (changes.defaultCommand && changes.defaultCommand.newValue) {
        selectCommand(changes.defaultCommand.newValue, false);
      }
    }
    if (area === 'session' && changes.pageContexts) {
      tryAutoFillFromTab();
    }
  });
}

async function init() {
  bindEvents();
  const settings = await getSettings();
  serverUrl = settings.serverUrl;
  versionLimit = settings.versionLimit;
  if (settings.defaultCommand) selectCommand(settings.defaultCommand, false);
  await loadSettingsPanel();
  await loadForm();
  await loadHistoryFromStorage();
  await loadLastSummary();
  await refreshServerStatus();
  await tryAutoFillFromTab();

  if ($('repoUrl').value.trim() && serverOnline) {
    debounce('branches', () => loadBranches(false), 300);
  }
}

init();
