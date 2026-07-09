/**
 * Detect Git repository context from GitHub / GitLab / Bitbucket pages.
 */

(function () {
  const SKIP_SEGMENTS = new Set([
    'settings', 'pulls', 'issues', 'actions', 'projects', 'wiki',
    'security', 'pulse', 'graphs', 'discussions', 'releases', 'tags',
    'compare', 'search', 'login', 'signup', 'orgs', 'organizations',
    'explore', 'marketplace', 'notifications', 'new', 'users',
  ]);

  function parseGitHub(url) {
    const parts = url.pathname.split('/').filter(Boolean);
    if (parts.length < 2) return null;
    const [owner, repo, ...rest] = parts;
    if (SKIP_SEGMENTS.has(owner) || SKIP_SEGMENTS.has(repo)) return null;
    if (repo.endsWith('.git')) return null;

    const ctx = {
      repo: `https://github.com/${owner}/${repo}`,
      branch: '',
      commit: '',
      host: 'github',
    };

    if (rest[0] === 'tree' && rest[1]) {
      ctx.branch = decodeURIComponent(rest.slice(1).join('/'));
    } else if (rest[0] === 'commit' && rest[1]) {
      ctx.commit = rest[1];
    } else if (rest[0] === 'blob' && rest[1]) {
      ctx.branch = decodeURIComponent(rest.slice(1).join('/'));
    }

    return ctx;
  }

  function parseGitLab(url) {
    const parts = url.pathname.split('/').filter(Boolean);
    if (parts.length < 2) return null;

    let owner, repo, rest;
    const dashIdx = parts.indexOf('-');
    if (parts.includes('-') && parts.indexOf('-') > 0) {
      const treeIdx = parts.indexOf('-');
      if (treeIdx >= 0) {
        owner = parts.slice(0, treeIdx).join('/');
        rest = parts.slice(treeIdx);
      }
    }

    if (!owner) {
      owner = parts[0];
      repo = parts[1];
      rest = parts.slice(2);
    } else {
      repo = '';
      rest = parts.slice(parts.indexOf('-'));
    }

    if (!repo && rest[0] === '-') {
      repo = parts[1];
      rest = parts.slice(2);
    }

    if (!repo) {
      if (parts.length >= 2 && parts[2] !== '-') {
        owner = parts[0];
        repo = parts[1];
        rest = parts.slice(2);
      } else if (parts.length >= 3) {
        const dashAt = parts.indexOf('-');
        if (dashAt > 0) {
          owner = parts.slice(0, dashAt).join('/');
          repo = parts.slice(dashAt + 1, dashAt + 2).join('/') || parts[dashAt + 1];
          rest = parts.slice(dashAt);
        }
      }
    }

    if (!owner || !repo || repo === '-' || SKIP_SEGMENTS.has(repo)) return null;

    const namespace = parts[0].includes('.') ? parts.slice(0, -1) : [parts[0]];
    let namespacePath, projectName, remainder;

    if (parts.includes('-')) {
      const idx = parts.indexOf('-');
      namespacePath = parts.slice(0, idx).join('/');
      projectName = parts[idx + 1];
      remainder = parts.slice(idx + 2);
    } else {
      namespacePath = parts[0];
      projectName = parts[1];
      remainder = parts.slice(2);
    }

    if (!projectName || SKIP_SEGMENTS.has(projectName)) return null;

    const ctx = {
      repo: `${url.origin}/${namespacePath}/${projectName}`,
      branch: '',
      commit: '',
      host: 'gitlab',
    };

    if (remainder[0] === 'tree' && remainder[1]) {
      ctx.branch = decodeURIComponent(remainder[1]);
    } else if (remainder[0] === 'commit' && remainder[1]) {
      ctx.commit = remainder[1];
    } else if (remainder[0] === 'blob' && remainder[1]) {
      ctx.branch = decodeURIComponent(remainder[1]);
    }

    return ctx;
  }

  function parseGitLabSimple(url) {
    const path = url.pathname;
    const treeMatch = path.match(/^\/(.+?)\/-\/tree\/([^/]+)/);
    const commitMatch = path.match(/^\/(.+?)\/-\/commit\/([a-f0-9]+)/i);
    const blobMatch = path.match(/^\/(.+?)\/-\/blob\/([^/]+)/);
    const repoMatch = path.match(/^\/([^/]+\/[^/]+)\/?$/);

    if (commitMatch) {
      const ns = commitMatch[1];
      const parts = ns.split('/');
      if (parts.length < 2) return null;
      return {
        repo: `${url.origin}/${ns}`,
        branch: '',
        commit: commitMatch[2],
        host: 'gitlab',
      };
    }
    if (treeMatch) {
      return {
        repo: `${url.origin}/${treeMatch[1]}`,
        branch: decodeURIComponent(treeMatch[2]),
        commit: '',
        host: 'gitlab',
      };
    }
    if (blobMatch) {
      return {
        repo: `${url.origin}/${blobMatch[1]}`,
        branch: decodeURIComponent(blobMatch[2]),
        commit: '',
        host: 'gitlab',
      };
    }
    if (repoMatch) {
      const ns = repoMatch[1];
      const seg = ns.split('/');
      if (seg.length < 2 || SKIP_SEGMENTS.has(seg[0])) return null;
      return { repo: `${url.origin}/${ns}`, branch: '', commit: '', host: 'gitlab' };
    }
    return null;
  }

  function parseBitbucket(url) {
    const parts = url.pathname.split('/').filter(Boolean);
    if (parts.length < 2 || parts[0] !== 'projects') return null;
    if (parts[2] !== 'repos') return null;

    const workspace = parts[1];
    const repo = parts[3];
    const rest = parts.slice(4);

    const ctx = {
      repo: `${url.origin}/projects/${workspace}/repos/${repo}`,
      branch: '',
      commit: '',
      host: 'bitbucket',
    };

    if (rest[0] === 'browse' && rest[1]) {
      ctx.branch = decodeURIComponent(rest[1]);
    } else if (rest[0] === 'commits' && rest[1]) {
      ctx.commit = rest[1];
    } else if (rest[0] === 'src' && rest[1]) {
      ctx.branch = decodeURIComponent(rest[1]);
    }

    return ctx;
  }

  function parsePageContext() {
    const url = new URL(window.location.href);
    const host = url.hostname;

    if (host === 'github.com' || host.endsWith('.github.com')) {
      return parseGitHub(url);
    }
    if (host.includes('gitlab')) {
      return parseGitLabSimple(url) || parseGitLab(url);
    }
    if (host === 'bitbucket.org') {
      return parseBitbucket(url);
    }
    return null;
  }

  function publish() {
    const ctx = parsePageContext();
    if (!ctx) return;

    chrome.runtime.sendMessage({
      type: 'PAGE_CONTEXT',
      context: { ...ctx, source: 'page', url: window.location.href },
    }).catch(() => {});
  }

  publish();

  let lastHref = window.location.href;
  const observer = new MutationObserver(() => {
    if (window.location.href !== lastHref) {
      lastHref = window.location.href;
      publish();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  window.addEventListener('popstate', publish);
  const origPush = history.pushState.bind(history);
  const origReplace = history.replaceState.bind(history);
  history.pushState = (...args) => { origPush(...args); publish(); };
  history.replaceState = (...args) => { origReplace(...args); publish(); };
})();
