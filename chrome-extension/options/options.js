import {
  getSettings,
  setSettings,
  getUserTokens,
  setUserTokens,
  readUserTokensFromForm,
  checkServerStatus,
} from '../lib/api.js';
import { initTokenHelp } from '../lib/token-help.js';

const $ = (id) => document.getElementById(id);

async function loadOptions() {
  const settings = await getSettings();
  const tokens = await getUserTokens();
  $('serverUrl').value = settings.serverUrl;
  $('defaultCommand').value = settings.defaultCommand;
  $('versionLimit').value = settings.versionLimit;
  $('githubToken').value = tokens.github;
  $('gitlabToken').value = tokens.gitlab;
  $('bitbucketToken').value = tokens.bitbucket;
}

function readFormTokens() {
  return readUserTokensFromForm({
    githubToken: $('githubToken').value,
    gitlabToken: $('gitlabToken').value,
    bitbucketToken: $('bitbucketToken').value,
  });
}

function showStatus(ok, msg) {
  const el = $('statusMsg');
  el.textContent = msg;
  el.className = `status ${ok ? 'ok' : 'err'}`;
}

$('saveBtn').addEventListener('click', async () => {
  const serverUrl = $('serverUrl').value.trim().replace(/\/$/, '');
  const defaultCommand = $('defaultCommand').value;
  const versionLimit = parseInt($('versionLimit').value, 10) || 30;

  if (!serverUrl) {
    showStatus(false, '请输入后端服务地址');
    return;
  }

  await setSettings({ serverUrl, defaultCommand, versionLimit });
  await setUserTokens(readFormTokens());
  showStatus(true, '设置已保存');
});

$('testBtn').addEventListener('click', async () => {
  const serverUrl = $('serverUrl').value.trim().replace(/\/$/, '');
  if (!serverUrl) {
    showStatus(false, '请输入后端服务地址');
    return;
  }

  showStatus(true, '正在测试连接...');
  const status = await checkServerStatus(serverUrl, readFormTokens());
  if (status.online) {
    showStatus(
      true,
      `连接成功！${status.summary || (status.hasToken ? 'Token 已配置' : '未配置个人 Token（仅公有仓库可用）')}`
    );
  } else {
    showStatus(false, '连接失败。请确认远程后端服务已启动，或检查后端地址');
  }
});

initTokenHelp({
  overlay: 'tokenHelpOverlay',
  title: 'tokenHelpTitle',
  body: 'tokenHelpBody',
  link: 'tokenHelpLink',
  close: 'tokenHelpClose',
});

loadOptions();
