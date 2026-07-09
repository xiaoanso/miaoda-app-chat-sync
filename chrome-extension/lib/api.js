/**
 * API client for local web-ui/server.py backend.
 */

const DEFAULT_SERVER_URL = 'http://localhost:8080';

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

function apiUrl(serverUrl, path) {
  return `${serverUrl}${path}`;
}

export async function checkServerStatus(serverUrl) {
  try {
    const res = await fetch(apiUrl(serverUrl, '/api/status'), {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return { online: false, hasToken: false };
    const data = await res.json();
    return { online: true, hasToken: !!data.hasToken };
  } catch {
    return { online: false, hasToken: false };
  }
}

export async function fetchBranches(serverUrl, repo) {
  const res = await fetch(
    apiUrl(serverUrl, `/api/branches?repo=${encodeURIComponent(repo)}`),
    { signal: AbortSignal.timeout(120000) }
  );
  return res.json();
}

export async function fetchCommits(serverUrl, repo, branch, limit) {
  const url = apiUrl(
    serverUrl,
    `/api/commits?repo=${encodeURIComponent(repo)}&branch=${encodeURIComponent(branch)}&limit=${limit}`
  );
  const res = await fetch(url, { signal: AbortSignal.timeout(120000) });
  return res.json();
}

export async function generateJson(serverUrl, requestData) {
  const res = await fetch(apiUrl(serverUrl, '/api/generate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData),
    signal: AbortSignal.timeout(600000),
  });
  return res.json();
}
