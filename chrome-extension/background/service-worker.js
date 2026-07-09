/**
 * Background service worker: page context, context menu, badge.
 */

const CONTEXT_MENU_ID = 'repo-json-generator-open';

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: CONTEXT_MENU_ID,
    title: '用 Repo JSON Generator 打开',
    contexts: ['page'],
    documentUrlPatterns: [
      'https://github.com/*',
      'https://gitlab.com/*',
      'https://bitbucket.org/*',
    ],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== CONTEXT_MENU_ID || !tab?.id) return;

  await chrome.storage.session.set({ pendingFillTabId: tab.id });
  try {
    await chrome.action.openPopup();
  } catch {
    // openPopup may fail without user gesture; user can click the extension icon
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'PAGE_CONTEXT' && sender.tab?.id) {
    const tabId = sender.tab.id;
    chrome.storage.session.get(['pageContexts']).then((data) => {
      const contexts = data.pageContexts || {};
      contexts[tabId] = {
        ...message.context,
        tabId,
        updatedAt: Date.now(),
      };
      chrome.storage.session.set({ pageContexts: contexts });
      chrome.action.setBadgeText({ text: '✓', tabId });
      chrome.action.setBadgeBackgroundColor({ color: '#9ece6a', tabId });
    });
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === 'GET_TAB_CONTEXT') {
    chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
      if (!tab?.id) {
        sendResponse({ context: null, tabUrl: null });
        return;
      }
      chrome.storage.session.get(['pageContexts']).then((data) => {
        const ctx = (data.pageContexts || {})[tab.id] || null;
        sendResponse({
          context: ctx,
          tabId: tab.id,
          tabUrl: tab.url || null,
        });
      });
    });
    return true;
  }

  if (message.type === 'CLEAR_BADGE' && sender.tab?.id) {
    chrome.action.setBadgeText({ text: '', tabId: sender.tab.id });
    sendResponse({ ok: true });
    return true;
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.session.get(['pageContexts']).then((data) => {
    const contexts = data.pageContexts || {};
    delete contexts[tabId];
    chrome.storage.session.set({ pageContexts: contexts });
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url) {
    chrome.action.setBadgeText({ text: '', tabId });
    chrome.storage.session.get(['pageContexts']).then((data) => {
      const contexts = data.pageContexts || {};
      delete contexts[tabId];
      chrome.storage.session.set({ pageContexts: contexts });
    });
  }
});
