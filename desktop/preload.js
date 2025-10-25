const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: () => ipcRenderer.invoke('backend:get-url'),
  onBackendReady: (callback) => {
    const handler = (_event, payload) => callback(payload);
    ipcRenderer.on('backend:ready', handler);
    return () => ipcRenderer.off('backend:ready', handler);
  },
  onBackendExit: (callback) => {
    const handler = (_event, payload) => callback(payload);
    ipcRenderer.on('backend:exit', handler);
    return () => ipcRenderer.off('backend:exit', handler);
  }
});
