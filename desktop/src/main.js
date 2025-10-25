const {
  app,
  BrowserWindow,
  ipcMain,
  shell,
  Notification,
  dialog,
  Tray,
  Menu,
  nativeImage
} = require('electron');
const path = require('path');
const { autoUpdater } = require('electron-updater');

const BackendSpawner = require('./backendSpawner');
const HealthChecker = require('./healthChecker');

const BACKEND_HOST = process.env.BACKEND_HOST || '127.0.0.1';
const BACKEND_PORT = Number.parseInt(process.env.BACKEND_PORT || '8000', 10);
const BACKEND_HEALTH_PATH = process.env.BACKEND_HEALTH_PATH || '/health';

const TRAY_ICON_DATA_URL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAALElEQVQ4T2NkIAIwEqmOYUACRmZgqEkSYDQqBgYGBob/QAaGBgYGhoYGhgYGNANAEWtDvxF9TxrAAAAAElFTkSuQmCC';

let mainWindow;
let tray;
let backendStartupError = null;

const log = {
  info: (...args) => console.log('[desktop]', ...args),
  error: (...args) => console.error('[desktop]', ...args),
  debug: (...args) => console.debug('[desktop]', ...args)
};

const backendSpawner = new BackendSpawner({
  app,
  host: BACKEND_HOST,
  port: BACKEND_PORT,
  logger: log
});

const healthChecker = new HealthChecker({
  host: BACKEND_HOST,
  port: BACKEND_PORT,
  path: BACKEND_HEALTH_PATH,
  intervalMs: 7000,
  logger: log
});

function getBackendUrl() {
  return `http://${BACKEND_HOST}:${BACKEND_PORT}`;
}

function sendToAllWindows(channel, payload) {
  BrowserWindow.getAllWindows().forEach((window) => {
    window.webContents.send(channel, payload);
  });
}

function showNotification(title, body) {
  if (!Notification.isSupported()) {
    return;
  }

  const notification = new Notification({
    title: title || 'RecruitPro Desktop',
    body: body || ''
  });

  notification.show();
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 900,
    show: false,
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.webContents.once('did-finish-load', () => {
    const status = backendSpawner.getStatus();
    if (status.ready) {
      mainWindow.webContents.send('backend:ready', { url: getBackendUrl() });
    }

    if (!status.running && backendStartupError) {
      mainWindow.webContents.send('backend:exit', {
        type: 'error',
        message: backendStartupError.message || 'Backend failed to start.'
      });
    }
  });

  const rendererPath = path.join(__dirname, '..', 'renderer', 'recruitpro_ats.html');
  await mainWindow.loadFile(rendererPath);
}

function createTray() {
  if (tray) {
    return;
  }

  const icon = nativeImage.createFromDataURL(TRAY_ICON_DATA_URL);
  icon.setTemplateImage(true);

  tray = new Tray(icon);
  tray.setToolTip('RecruitPro Desktop');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show RecruitPro',
      click: () => {
        if (mainWindow) {
          if (mainWindow.isMinimized()) {
            mainWindow.restore();
          }
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: 'Restart Backend',
      click: async () => {
        try {
          await backendSpawner.restart();
          showNotification('Backend restarted', 'RecruitPro backend is starting up again.');
        } catch (error) {
          showNotification('Backend restart failed', error.message);
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Check for Updates',
      click: () => {
        autoUpdater.checkForUpdates().catch((error) => {
          log.error('Failed to check for updates', error);
        });
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
}

function setupAutoUpdater() {
  autoUpdater.logger = log;
  autoUpdater.autoDownload = false;

  autoUpdater.on('checking-for-update', () => {
    sendToAllWindows('auto-updater:checking');
  });

  autoUpdater.on('update-available', (info) => {
    sendToAllWindows('auto-updater:update-available', info);
    showNotification('Update available', 'A new version is available. Downloading will begin shortly.');
    autoUpdater.downloadUpdate().catch((error) => {
      log.error('Auto update download failed', error);
    });
  });

  autoUpdater.on('update-not-available', (info) => {
    sendToAllWindows('auto-updater:update-not-available', info);
  });

  autoUpdater.on('download-progress', (progress) => {
    sendToAllWindows('auto-updater:download-progress', progress);
  });

  autoUpdater.on('update-downloaded', (info) => {
    sendToAllWindows('auto-updater:update-downloaded', info);
    showNotification('Update ready to install', 'Restart the application to apply the update.');
  });

  autoUpdater.on('error', (error) => {
    sendToAllWindows('auto-updater:error', { message: error.message });
    log.error('Auto updater encountered an error', error);
  });

  autoUpdater
    .checkForUpdates()
    .catch((error) => {
      log.error('Initial update check failed', error);
    });
}

function registerIpcHandlers() {
  ipcMain.handle('backend:get-url', () => getBackendUrl());

  ipcMain.handle('backend:get-status', () => backendSpawner.getStatus());

  ipcMain.handle('backend:restart', async () => {
    await backendSpawner.restart();
    return backendSpawner.getStatus();
  });

  ipcMain.handle('dialog:open-directory', async (_event, options = {}) => {
    const result = await dialog.showOpenDialog(mainWindow ?? undefined, {
      properties: ['openDirectory'],
      ...options
    });
    return result;
  });

  ipcMain.handle('dialog:open-file', async (_event, options = {}) => {
    const result = await dialog.showOpenDialog(mainWindow ?? undefined, {
      properties: ['openFile'],
      ...options
    });
    return result;
  });

  ipcMain.handle('notification:show', (_event, payload = {}) => {
    const { title, body } = payload;
    showNotification(title, body);
    return true;
  });

  ipcMain.handle('auto-updater:check-now', async () => {
    await autoUpdater.checkForUpdates();
    return true;
  });

  ipcMain.handle('auto-updater:quit-and-install', () => {
    autoUpdater.quitAndInstall();
  });
}

function wireBackendEvents() {
  backendSpawner.on('ready', () => {
    backendStartupError = null;
    healthChecker.start();
    const payload = { url: getBackendUrl() };
    sendToAllWindows('backend:ready', payload);
    showNotification('Backend ready', 'RecruitPro backend is now available.');
  });

  backendSpawner.on('stderr', (line) => {
    sendToAllWindows('backend:stderr', line);
  });

  backendSpawner.on('exit', (details) => {
    healthChecker.stop();
    sendToAllWindows('backend:exit', {
      type: 'warning',
      message: 'Backend exited unexpectedly. Please restart the application.',
      details
    });
    showNotification('Backend exited', 'RecruitPro backend process stopped unexpectedly.');
  });

  backendSpawner.on('error', (error) => {
    backendStartupError = error;
    sendToAllWindows('backend:error', { message: error.message });
  });

  healthChecker.on('status-changed', (healthy) => {
    sendToAllWindows('backend:health', { healthy });
    if (!healthy) {
      showNotification('Backend degraded', 'RecruitPro backend is not responding.');
    }
  });
}

async function handleAppReady() {
  if (process.platform === 'win32') {
    app.setAppUserModelId('com.recruitpro.desktop');
  }

  registerIpcHandlers();
  wireBackendEvents();
  createTray();
  setupAutoUpdater();

  try {
    await backendSpawner.start();
  } catch (error) {
    backendStartupError = error;
  }

  await createWindow();
}

app.whenReady().then(() => {
  handleAppReady().catch((error) => {
    log.error('Failed to initialize application', error);
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow().catch((err) => log.error('Failed to recreate window', err));
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  healthChecker.stop();
  backendSpawner.stop().catch((error) => {
    log.error('Failed to stop backend cleanly', error);
  });
});
