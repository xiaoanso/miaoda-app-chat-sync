/**
 * chrome.storage.local helpers (replaces localStorage in Web UI).
 */

const PREFIX = 'repoJsonGenerator.';

export async function storageGet(key, fallback = null) {
  const result = await chrome.storage.local.get(PREFIX + key);
  const val = result[PREFIX + key];
  return val !== undefined ? val : fallback;
}

export async function storageSet(key, value) {
  await chrome.storage.local.set({ [PREFIX + key]: value });
}

export async function storageRemove(key) {
  await chrome.storage.local.remove(PREFIX + key);
}
