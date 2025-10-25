const { contextBridge, ipcRenderer } = require('electron');

const isPlainObject = (value) =>
  Object.prototype.toString.call(value) === '[object Object]';

const sanitizeString = (value, fallback = undefined) =>
  typeof value === 'string' ? value : fallback;

const sanitizeBoolean = (value, fallback = false) =>
  typeof value === 'boolean' ? value : Boolean(value ?? fallback);

const sanitizeNumber = (value, fallback = undefined) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  const coerced = Number(value);
  return Number.isFinite(coerced) ? coerced : fallback;
};

const sanitizeArray = (value, { sanitizer = (item) => item, fallback = undefined } = {}) => {
  if (!Array.isArray(value)) {
    return fallback;
  }
  return value.map((item) => sanitizer(item)).filter((item) => item !== undefined);
};

function deepFreeze(object) {
  if (!isPlainObject(object) && !Array.isArray(object)) {
    return object;
  }

  Object.freeze(object);
  Object.getOwnPropertyNames(object).forEach((key) => {
    const value = object[key];
    if ((isPlainObject(value) || Array.isArray(value)) && !Object.isFrozen(value)) {
      deepFreeze(value);
    }
  });
  return object;
}

function sanitizeDialogOptions(options = {}) {
  if (!isPlainObject(options)) {
    return {};
  }

  const sanitized = {};

  if (options.title !== undefined) {
    sanitized.title = sanitizeString(options.title);
  }

  if (options.defaultPath !== undefined) {
    sanitized.defaultPath = sanitizeString(options.defaultPath);
  }

  if (options.buttonLabel !== undefined) {
    sanitized.buttonLabel = sanitizeString(options.buttonLabel);
  }

  if (options.filters !== undefined) {
    sanitized.filters = sanitizeArray(options.filters, {
      sanitizer: (filter) => {
        if (!isPlainObject(filter)) {
          return undefined;
        }
        const filterSanitized = {};
        if (filter.name) {
          filterSanitized.name = sanitizeString(filter.name, '');
        }
        if (filter.extensions) {
          filterSanitized.extensions = sanitizeArray(filter.extensions, {
            sanitizer: (extension) => sanitizeString(extension, ''),
            fallback: []
          });
        }
        return filterSanitized;
      },
      fallback: []
    });
  }

  if (options.properties !== undefined) {
    sanitized.properties = sanitizeArray(options.properties, {
      sanitizer: (property) => sanitizeString(property, ''),
      fallback: []
    });
  }

  return sanitized;
}

function sanitizeTrayItems(items) {
  return sanitizeArray(items, {
    sanitizer: (item) => {
      if (!isPlainObject(item)) {
        return undefined;
      }

      const sanitizedItem = {};

      if (item.type) {
        sanitizedItem.type = sanitizeString(item.type, 'normal');
      }

      if (item.label) {
        sanitizedItem.label = sanitizeString(item.label, '');
      }

      if (item.tooltip) {
        sanitizedItem.tooltip = sanitizeString(item.tooltip, '');
      }

      if (item.enabled !== undefined) {
        sanitizedItem.enabled = sanitizeBoolean(item.enabled, true);
      }

      if (item.checked !== undefined) {
        sanitizedItem.checked = sanitizeBoolean(item.checked, false);
      }

      if (item.submenu) {
        sanitizedItem.submenu = sanitizeTrayItems(item.submenu);
      }

      return sanitizedItem;
    },
    fallback: []
  });
}

function sanitizeMenuItems(items) {
  return sanitizeArray(items, {
    sanitizer: (item) => {
      if (!isPlainObject(item)) {
        return undefined;
      }

      const sanitizedItem = {};

      if (item.role) {
        sanitizedItem.role = sanitizeString(item.role, '');
      }

      if (item.label) {
        sanitizedItem.label = sanitizeString(item.label, '');
      }

      if (item.type) {
        sanitizedItem.type = sanitizeString(item.type, 'normal');
      }

      if (item.submenu) {
        sanitizedItem.submenu = sanitizeMenuItems(item.submenu);
      }

      if (item.accelerator) {
        sanitizedItem.accelerator = sanitizeString(item.accelerator, '');
      }

      if (item.enabled !== undefined) {
        sanitizedItem.enabled = sanitizeBoolean(item.enabled, true);
      }

      if (item.visible !== undefined) {
        sanitizedItem.visible = sanitizeBoolean(item.visible, true);
      }

      if (item.checked !== undefined) {
        sanitizedItem.checked = sanitizeBoolean(item.checked, false);
      }

      return sanitizedItem;
    },
    fallback: []
  });
}

function createSubscription(allowedChannels) {
  return (channel, callback) => {
    if (!allowedChannels.has(channel)) {
      throw new Error(`Channel "${channel}" is not available.`);
    }
    if (typeof callback !== 'function') {
      throw new TypeError('Callback must be a function.');
    }

    const handler = (_event, payload) => {
      callback(payload);
    };

    ipcRenderer.on(channel, handler);
    return () => {
      ipcRenderer.off(channel, handler);
    };
  };
}

const backendEventChannels = new Set([
  'backend:spawned',
  'backend:ready',
  'backend:stderr',
  'backend:exit',
  'backend:error',
  'backend:health-startup',
  'backend:health-wait',
  'backend:health',
  'backend:zombie',
  'backend:resource-usage',
  'backend:process-exit',
  'backend:restart-scheduled',
  'backend:restarting',
  'backend:restarted',
  'backend:restart-attempt-failed',
  'backend:restart-failed'
]);

const autoUpdaterEventChannels = new Set([
  'auto-updater:checking',
  'auto-updater:update-available',
  'auto-updater:update-not-available',
  'auto-updater:download-progress',
  'auto-updater:update-downloaded',
  'auto-updater:error'
]);

const subscribeBackendEvent = createSubscription(backendEventChannels);
const subscribeAutoUpdaterEvent = createSubscription(autoUpdaterEventChannels);

const backendApi = {
  getUrl: () => ipcRenderer.invoke('backend:get-url'),
  getStatus: () => ipcRenderer.invoke('backend:get-status'),
  start: () => ipcRenderer.invoke('backend:start'),
  stop: (options = {}) => {
    const sanitized = { force: sanitizeBoolean(options.force, false) };
    return ipcRenderer.invoke('backend:stop', sanitized);
  },
  restart: () => ipcRenderer.invoke('backend:restart'),
  on: subscribeBackendEvent,
  onReady: (callback) => subscribeBackendEvent('backend:ready', callback),
  onExit: (callback) => subscribeBackendEvent('backend:exit', callback)
};

const dialogApi = {
  openDirectory: (options) => ipcRenderer.invoke('dialog:open-directory', sanitizeDialogOptions(options)),
  openFile: (options) => ipcRenderer.invoke('dialog:open-file', sanitizeDialogOptions(options)),
  saveFile: (options) => ipcRenderer.invoke('dialog:save-file', sanitizeDialogOptions(options))
};

const windowApi = {
  minimize: () => ipcRenderer.invoke('window:minimize'),
  maximize: () => ipcRenderer.invoke('window:maximize'),
  unmaximize: () => ipcRenderer.invoke('window:unmaximize'),
  toggleMaximize: () => ipcRenderer.invoke('window:toggle-maximize'),
  focus: () => ipcRenderer.invoke('window:focus'),
  close: () => ipcRenderer.invoke('window:close'),
  getState: () => ipcRenderer.invoke('window:get-state')
};

const notificationApi = {
  show: ({ title, body } = {}) =>
    ipcRenderer.invoke('notification:show', {
      title: sanitizeString(title),
      body: sanitizeString(body)
    })
};

const appApi = {
  quit: () => ipcRenderer.invoke('app:quit')
};

const systemApi = {
  setBadgeCount: (count) => ipcRenderer.invoke('system:badge:set-count', sanitizeNumber(count, 0)),
  clearBadge: () => ipcRenderer.invoke('system:badge:clear'),
  updateTray: ({ tooltip, items } = {}) =>
    ipcRenderer.invoke('system:tray:update', {
      tooltip: sanitizeString(tooltip),
      items: sanitizeTrayItems(items)
    }),
  setApplicationMenu: (items) =>
    ipcRenderer.invoke('system:menu:set-application-menu', {
      items: sanitizeMenuItems(items)
    }),
  clearApplicationMenu: () => ipcRenderer.invoke('system:menu:clear')
};

const autoUpdaterApi = {
  checkNow: () => ipcRenderer.invoke('auto-updater:check-now'),
  quitAndInstall: () => ipcRenderer.invoke('auto-updater:quit-and-install'),
  on: subscribeAutoUpdaterEvent
};

const databaseApi = {
  backup: (destination) =>
    ipcRenderer.invoke('database:backup', {
      destination: sanitizeString(destination, '')
    }),
  restore: (source) =>
    ipcRenderer.invoke('database:restore', {
      source: sanitizeString(source, '')
    })
};

const electronAPI = {
  backend: backendApi,
  dialog: dialogApi,
  window: windowApi,
  notification: notificationApi,
  app: appApi,
  system: systemApi,
  autoUpdater: autoUpdaterApi,
  database: databaseApi,
  // Backwards compatibility with earlier preload exports
  getBackendUrl: backendApi.getUrl,
  onBackendReady: backendApi.onReady,
  onBackendExit: backendApi.onExit
};

contextBridge.exposeInMainWorld('electronAPI', deepFreeze(electronAPI));
