/**
 * API client for web-ui/server.py backend.
 */

const DEFAULT_SERVER_URL = 'http://localhost:8080';
const TOKEN_HEADER_NAMES = {
  github: 'X-GitHub-Token',
  gitlab: 'X-GitLab-Token',
  bitbucket: 'X-Bitbucket-Token',
};

export async function getSettings() {
  const data = await chrome.storage.sync.get({
    serverUrl: DEFAULT_SERVER_URL,
    defaultCommand: 'sync',
    versionLimit: 30,
  });
  return {
    serverUrl: (data.serverUrl || DEFAULT_SERVER_URL).replace(/\/$/, ''),
    defaultCommand: data.defaultCommand || 'sync',
    versionLimit: data.versionLimit || 30,
  };
}

export async function setSettings(partial) {
  await chrome.storage.sync.set(partial);
}

/** User-provided tokens (stored locally, never synced). */
export async function getUserTokens() {
  const data = await chrome.storage.local.get({
    githubToken: '',
    gitlabToken: '',
    bitbucketToken: '',
  });
  return {
    github: (data.githubToken || '').trim(),
    gitlab: (data.gitlabToken || '').trim(),
    bitbucket: (data.bitbucketToken || '').trim(),
  };
}

export async function setUserTokens(tokens) {
  await chrome.storage.local.set({
    githubToken: tokens.github || '',
    gitlabToken: tokens.gitlab || '',
    bitbucketToken: tokens.bitbucket || '',
  });
}

export function readUserTokensFromForm(form = {}) {
  return {
    github: (form.githubToken || '').trim(),
    gitlab: (form.gitlabToken || '').trim(),
    bitbucket: (form.bitbucketToken || '').trim(),
  };
}

function apiUrl(serverUrl, path) {
  return `${serverUrl}${path}`;
}

function authHeaders(tokens = {}) {
  const headers = {};
  for (const [key, headerName] of Object.entries(TOKEN_HEADER_NAMES)) {
    if (tokens[key]) headers[headerName] = tokens[key];
  }
  return headers;
}

async function apiFetch(serverUrl, path, options = {}, userTokens = null) {
  const tokens = userTokens || await getUserTokens();
  const headers = {
    ...(options.headers || {}),
    ...authHeaders(tokens),
  };
  return fetch(apiUrl(serverUrl, path), { ...options, headers });
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

function summarizeTokens(tokens = {}) {
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

export async function checkServerStatus(serverUrl, userTokens = null) {
  const tokens = userTokens || await getUserTokens();
  const clientTokenInfo = summarizeTokens({
    github: !!tokens.github,
    gitlab: !!tokens.gitlab,
    bitbucket: !!tokens.bitbucket,
  });

  try {
    const res = await apiFetch(
      serverUrl,
      '/api/status',
      { method: 'GET', signal: AbortSignal.timeout(5000) },
      tokens
    );
    if (!res.ok) {
      return { online: false, hasToken: false, tokens: {}, summary: '' };
    }
    await res.json();
    return { online: true, ...clientTokenInfo };
  } catch {
    return { online: false, hasToken: false, tokens: {}, summary: '' };
  }
}

export async function fetchBranches(serverUrl, repo, userTokens = null) {
  const normalizedRepo = normalizeRepoUrl(repo);
  const res = await apiFetch(
    serverUrl,
    `/api/branches?repo=${encodeURIComponent(normalizedRepo)}`,
    { signal: AbortSignal.timeout(120000) },
    userTokens
  );
  return res.json();
}

export async function fetchCommits(serverUrl, repo, branch, limit, userTokens = null) {
  const normalizedRepo = normalizeRepoUrl(repo);
  const url = `/api/commits?repo=${encodeURIComponent(normalizedRepo)}&branch=${encodeURIComponent(branch)}&limit=${limit}`;
  const res = await apiFetch(
    serverUrl,
    url,
    { signal: AbortSignal.timeout(120000) },
    userTokens
  );
  return res.json();
}

export async function generateJson(serverUrl, requestData, userTokens = null) {
  const payload = {
    ...requestData,
    repo: normalizeRepoUrl(requestData.repo),
  };
  const res = await apiFetch(
    serverUrl,
    '/api/generate',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(600000),
    },
    userTokens
  );
  return res.json();
}
