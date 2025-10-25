const patchRequestUrl = (url, baseUrl) => {
  if (typeof url !== 'string') {
    return url;
  }

  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return url;
  }

  if (trimmed.startsWith('/')) {
    return `${baseUrl}${trimmed}`;
  }

  return url;
};

const initializeBackendIntegration = async () => {
  if (!window.electronAPI || !window.electronAPI.getBackendUrl) {
    console.warn('Electron API not available; backend integration skipped.');
    return;
  }

  const backendUrl = await window.electronAPI.getBackendUrl();
  if (!backendUrl) {
    console.warn('Backend URL could not be resolved.');
    return;
  }

  window.backendBaseUrl = backendUrl;

  // Update form actions that use relative API paths.
  document.querySelectorAll('form[action]').forEach((form) => {
    const action = form.getAttribute('action');
    if (action && action.startsWith('/')) {
      form.setAttribute('action', `${backendUrl}${action}`);
    }
  });

  document.querySelectorAll('a[href]').forEach((anchor) => {
    const href = anchor.getAttribute('href');
    if (!href || href.startsWith('#')) {
      return;
    }
    if (href.startsWith('/')) {
      anchor.setAttribute('href', `${backendUrl}${href}`);
    }
  });

  // Patch fetch to prefix backend base URL for relative API calls.
  const originalFetch = window.fetch;
  window.fetch = async (input, init) => {
    const patchedInput = patchRequestUrl(input, backendUrl);
    return originalFetch(patchedInput, init);
  };

  // Provide helper for other scripts to resolve absolute API URLs.
  window.resolveApiUrl = (path) => {
    if (!path) {
      return backendUrl;
    }
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    if (!path.startsWith('/')) {
      return `${backendUrl}/${path}`;
    }
    return `${backendUrl}${path}`;
  };

  if (window.electronAPI.onBackendReady) {
    window.electronAPI.onBackendReady(({ url }) => {
      if (url) {
        window.backendBaseUrl = url;
      }
    });
  }

  if (window.electronAPI.onBackendExit) {
    window.electronAPI.onBackendExit(({ message }) => {
      const detail = message || 'The RecruitPro backend stopped unexpectedly.';
      window.alert(detail);
    });
  }
};

window.addEventListener('DOMContentLoaded', () => {
  initializeBackendIntegration().catch((error) => {
    console.error('Failed to initialize backend integration', error);
  });
});
