import { getSettings, setSettings, checkServerStatus } from '../lib/api.js';

const $ = (id) => document.getElementById(id);

async function loadOptions() {
  const settings = await getSettings();
  $('serverUrl').value = settings.serverUrl;
  $('defaultCommand').value = settings.defaultCommand;
  $('versionLimit').value = settings.versionLimit;
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
  showStatus(true, '设置已保存');
});

$('testBtn').addEventListener('click', async () => {
  const serverUrl = $('serverUrl').value.trim().replace(/\/$/, '');
  if (!serverUrl) {
    showStatus(false, '请输入后端服务地址');
    return;
  }

  showStatus(true, '正在测试连接...');
  const status = await checkServerStatus(serverUrl);
  if (status.online) {
    showStatus(
      true,
      `连接成功！GITHUB_TOKEN ${status.hasToken ? '已配置' : '未配置（私有仓库可能失败）'}`
    );
  } else {
    showStatus(false, '连接失败。请确认已运行 python3 web-ui/server.py');
  }
});

loadOptions();
