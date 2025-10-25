const { contextBridge, ipcRenderer } = require('electron');

function sanitizeDialogOptions(options = {}) {
  try {
    return JSON.parse(JSON.stringify(options));
  } catch (error) {
    console.warn('Failed to sanitize dialog options', error);
    return {};
  }
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
    const sanitized = { force: Boolean(options.force) };
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
      title: typeof title === 'string' ? title : undefined,
      body: typeof body === 'string' ? body : undefined
    })
};

const appApi = {
  quit: () => ipcRenderer.invoke('app:quit')
};

const systemApi = {
  setBadgeCount: (count) => ipcRenderer.invoke('system:badge:set-count', Number(count)),
  clearBadge: () => ipcRenderer.invoke('system:badge:clear'),
  updateTray: ({ tooltip, items } = {}) =>
    ipcRenderer.invoke('system:tray:update', {
      tooltip: typeof tooltip === 'string' ? tooltip : undefined,
      items: Array.isArray(items) ? items : undefined
    }),
  setApplicationMenu: (items) =>
    ipcRenderer.invoke('system:menu:set-application-menu', {
      items: Array.isArray(items) ? items : undefined
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
      destination: typeof destination === 'string' ? destination : ''
    }),
  restore: (source) =>
    ipcRenderer.invoke('database:restore', {
      source: typeof source === 'string' ? source : ''
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

contextBridge.exposeInMainWorld('electronAPI', Object.freeze(electronAPI));
