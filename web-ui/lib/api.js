/**
 * API client for web-ui/server.py (browser / localStorage).
 */

const STORAGE_PREFIX = 'repoJsonGenerator.';

const TOKEN_HEADER_NAMES = {
  github: 'X-GitHub-Token',
  gitlab: 'X-GitLab-Token',
  bitbucket: 'X-Bitbucket-Token',
};

export function getUserTokens() {
  return {
    github: (localStorage.getItem(STORAGE_PREFIX + 'githubToken') || '').trim(),
    gitlab: (localStorage.getItem(STORAGE_PREFIX + 'gitlabToken') || '').trim(),
    bitbucket: (localStorage.getItem(STORAGE_PREFIX + 'bitbucketToken') || '').trim(),
  };
}

export function setUserTokens(tokens) {
  localStorage.setItem(STORAGE_PREFIX + 'githubToken', tokens.github || '');
  localStorage.setItem(STORAGE_PREFIX + 'gitlabToken', tokens.gitlab || '');
  localStorage.setItem(STORAGE_PREFIX + 'bitbucketToken', tokens.bitbucket || '');
}

export function readUserTokensFromForm(form = {}) {
  return {
    github: (form.githubToken || '').trim(),
    gitlab: (form.gitlabToken || '').trim(),
    bitbucket: (form.bitbucketToken || '').trim(),
  };
}

export function authHeaders(tokens = {}) {
  const headers = {};
  for (const [key, headerName] of Object.entries(TOKEN_HEADER_NAMES)) {
    if (tokens[key]) headers[headerName] = tokens[key];
  }
  return headers;
}

export async function apiFetch(path, options = {}, userTokens = null) {
  const tokens = userTokens || getUserTokens();
  const headers = {
    ...(options.headers || {}),
    ...authHeaders(tokens),
  };
  return fetch(path, { ...options, headers });
}

/** Normalize SSH/scp Git URLs to HTTPS (matches backend behavior). */
export function normalizeRepoUrl(url) {
  const trimmed = String(url || '').trim();
  const scp = trimmed.match(/^git@([^:]+):(.+)$/);
  if (scp) {
    return `https://${scp[1]}/${scp[2].replace(/^\/+/, '')}`;
  }
  if (trimmed.startsWith('ssh://')) {
    try {
      const parsed = new URL(trimmed);
      return `https://${parsed.hostname}${parsed.pathname}`;
    } catch {
      return trimmed;
    }
  }
  return trimmed;
}

export function summarizeTokens(tokens = {}) {
  const labels = [];
  if (tokens.github) labels.push('GitHub');
  if (tokens.gitlab) labels.push('GitLab');
  if (tokens.bitbucket) labels.push('Bitbucket');
  const hasToken = labels.length > 0;
  return {
    hasToken,
    tokens,
    summary: hasToken
      ? `你的 ${labels.join('/')} Token 已配置`
      : '未配置个人 Token（仅公有仓库可用）',
  };
}

export function updateTokenBadge(badgeEl, userTokens = null) {
  if (!badgeEl) return;
  const tokens = userTokens || getUserTokens();
  const info = summarizeTokens({
    github: !!tokens.github,
    gitlab: !!tokens.gitlab,
    bitbucket: !!tokens.bitbucket,
  });
  badgeEl.textContent = info.summary;
  badgeEl.className = `badge ${info.hasToken ? 'ok' : 'warn'}`;
}
