/** Token acquisition guides for new users (Web UI). */

export const TOKEN_HELP = {
  github: {
    title: '如何获取 GitHub Token',
    link: 'https://github.com/settings/tokens/new',
    linkText: '前往 GitHub 创建 Token',
    steps: [
      '登录 GitHub，打开右上角头像 → Settings（设置）',
      '左侧最下方进入 Developer settings → Personal access tokens',
      '点击 Generate new token，选择 Classic（经典）',
      'Note 随意填写，Expiration 建议选 90 天或自定义',
      '勾选权限 <code>repo</code>（读取私有仓库所需）',
      '点击 Generate token，复制以 <code>ghp_</code> 开头的字符串',
      '粘贴到本页面「访问令牌」区域，点击「保存 Token」',
    ],
    note: 'Token 仅保存在你的浏览器本机，不会上传到服务器。',
  },
  gitlab: {
    title: '如何获取 GitLab Token',
    link: 'https://gitlab.com/-/user_settings/personal_access_tokens',
    linkText: '前往 GitLab 创建 Token',
    steps: [
      '登录 GitLab，点击右上角头像 → Edit profile（编辑资料）',
      '左侧选择 Access tokens（访问令牌）',
      '填写 Token name，勾选 <code>read_repository</code>',
      '点击 Create personal access token',
      '复制以 <code>glpat-</code> 开头的字符串并粘贴到本页面',
    ],
    note: '自建 GitLab 请在对应实例的 User Settings → Access tokens 中创建。',
  },
  bitbucket: {
    title: '如何获取 Bitbucket App Password',
    link: 'https://bitbucket.org/account/settings/app-passwords/',
    linkText: '前往 Bitbucket 创建 App Password',
    steps: [
      '登录 Bitbucket，点击左下角个人头像 → Personal settings',
      '左侧选择 App passwords（应用密码）',
      '点击 Create app password，Label 随意填写',
      '勾选 Repositories → Read（读取仓库）',
      '创建后复制密码并粘贴到本页面（只显示一次，请及时保存）',
    ],
    note: 'Bitbucket 使用 App Password，不是普通登录密码。',
  },
};

function renderHelpContent(platform) {
  const guide = TOKEN_HELP[platform];
  if (!guide) return '';

  const steps = guide.steps
    .map((step, i) => `<li><span class="help-step-num">${i + 1}</span>${step}</li>`)
    .join('');

  return `
    <ol class="help-steps">${steps}</ol>
    ${guide.note ? `<p class="help-note">${guide.note}</p>` : ''}
  `;
}

export function initTokenHelp(ids = {}) {
  const overlay = ids.overlay ? document.getElementById(ids.overlay) : null;
  const titleEl = ids.title ? document.getElementById(ids.title) : null;
  const bodyEl = ids.body ? document.getElementById(ids.body) : null;
  const linkEl = ids.link ? document.getElementById(ids.link) : null;
  const closeBtn = ids.close ? document.getElementById(ids.close) : null;

  function closeHelp() {
    if (overlay) overlay.hidden = true;
  }

  function openHelp(platform) {
    const guide = TOKEN_HELP[platform];
    if (!guide) return;

    if (overlay && titleEl && bodyEl && linkEl) {
      titleEl.textContent = guide.title;
      bodyEl.innerHTML = renderHelpContent(platform);
      linkEl.href = guide.link;
      linkEl.textContent = `${guide.linkText} →`;
      overlay.hidden = false;
      closeBtn?.focus();
      return;
    }

    const text = guide.steps.map((s, i) => `${i + 1}. ${s.replace(/<[^>]+>/g, '')}`).join('\n');
    window.alert(`${guide.title}\n\n${text}\n\n${guide.note || ''}\n\n${guide.linkText}: ${guide.link}`);
  }

  document.querySelectorAll('[data-token-help]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openHelp(btn.dataset.tokenHelp);
    });
  });

  closeBtn?.addEventListener('click', closeHelp);
  overlay?.addEventListener('click', (e) => {
    if (e.target === overlay) closeHelp();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay && !overlay.hidden) closeHelp();
  });
}
