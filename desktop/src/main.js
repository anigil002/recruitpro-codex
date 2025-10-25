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
const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');
const { pipeline } = require('stream/promises');
const { autoUpdater } = require('electron-updater');

const BackendSpawner = require('./backendSpawner');
const HealthChecker = require('./healthChecker');
const ProcessMonitor = require('./processMonitor');
const RestartManager = require('./restartManager');

const BACKEND_HOST = process.env.BACKEND_HOST || '127.0.0.1';
const BACKEND_PORT = Number.parseInt(process.env.BACKEND_PORT || '8000', 10);
const BACKEND_HEALTH_PATH = process.env.BACKEND_HEALTH_PATH || '/api/health';

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
  logger: log
});

const processMonitor = new ProcessMonitor({ logger: log, pollIntervalMs: 10000 });
const restartManager = new RestartManager(backendSpawner, { logger: log });

const TRAY_COMMANDS = {
  'show-window': () => {
    if (!mainWindow) {
      return;
    }
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    if (!mainWindow.isVisible()) {
      mainWindow.show();
    }
    mainWindow.focus();
  },
  'restart-backend': async () => {
    try {
      await backendSpawner.restart();
      showNotification('Backend restarted', 'RecruitPro backend is starting up again.');
    } catch (error) {
      log.error('Backend restart request from tray failed', error);
      showNotification('Backend restart failed', error.message);
    }
  },
  'check-for-updates': () => {
    autoUpdater.checkForUpdates().catch((error) => {
      log.error('Failed to check for updates', error);
    });
  },
  'toggle-devtools': () => {
    if (!mainWindow) {
      return;
    }
    if (mainWindow.webContents.isDevToolsOpened()) {
      mainWindow.webContents.closeDevTools();
    } else {
      mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
  },
  'reload-window': () => {
    mainWindow?.reload();
  },
  'quit-app': () => {
    app.quit();
  }
};

function sanitizeMenuItems(items = []) {
  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return null;
      }

      if (item.type === 'separator') {
        return { type: 'separator' };
      }

      const sanitized = {};

      if (typeof item.type === 'string' && ['normal', 'checkbox', 'radio'].includes(item.type)) {
        sanitized.type = item.type;
      }

      if (typeof item.label === 'string') {
        sanitized.label = item.label;
      }

      if (typeof item.role === 'string') {
        sanitized.role = item.role;
      }

      if (typeof item.accelerator === 'string') {
        sanitized.accelerator = item.accelerator;
      }

      if (item.type === 'checkbox' || item.type === 'radio') {
        sanitized.checked = Boolean(item.checked);
      }

      if (typeof item.enabled === 'boolean') {
        sanitized.enabled = item.enabled;
      }

      if (typeof item.command === 'string' && TRAY_COMMANDS[item.command]) {
        const commandHandler = TRAY_COMMANDS[item.command];
        sanitized.click = () => {
          Promise.resolve(commandHandler()).catch((error) => {
            log.error('Tray command handler rejected', { command: item.command, error });
          });
        };
      }

      if (Array.isArray(item.submenu)) {
        sanitized.submenu = sanitizeMenuItems(item.submenu);
      }

      if (!sanitized.type && (sanitized.label || sanitized.role || sanitized.submenu || sanitized.click)) {
        sanitized.type = 'normal';
      }

      if (!sanitized.type) {
        return null;
      }

      return sanitized;
    })
    .filter(Boolean);
}

function updateTrayMenu(template) {
  if (!tray) {
    return;
  }

  const sanitizedTemplate = sanitizeMenuItems(template);
  if (!sanitizedTemplate.length) {
    return;
  }

  const contextMenu = Menu.buildFromTemplate(sanitizedTemplate);
  tray.setContextMenu(contextMenu);
}

function getDefaultTrayTemplate() {
  return [
    {
      label: 'Show RecruitPro',
      command: 'show-window'
    },
    {
      label: 'Restart Backend',
      command: 'restart-backend'
    },
    { type: 'separator' },
    {
      label: 'Check for Updates',
      command: 'check-for-updates'
    },
    { type: 'separator' },
    {
      label: 'Quit',
      command: 'quit-app'
    }
  ];
}

function resolveDatabasePath() {
  const backendRoot = backendSpawner.resolveBackendRoot();
  return path.join(backendRoot, 'data', 'recruitpro.db');
}

async function fileExists(filePath) {
  try {
    const stats = await fsp.stat(filePath);
    return stats.isFile();
  } catch (error) {
    if (error && (error.code === 'ENOENT' || error.code === 'ENOTDIR')) {
      return false;
    }
    throw error;
  }
}

async function copyFileAtomic(source, destination) {
  await fsp.mkdir(path.dirname(destination), { recursive: true });
  const tempPath = `${destination}.${Date.now()}.tmp`;
  try {
    await pipeline(fs.createReadStream(source), fs.createWriteStream(tempPath));
    await fsp.rename(tempPath, destination);
  } catch (error) {
    await fsp.rm(tempPath, { force: true }).catch(() => {});
    throw error;
  }
}

async function backupDatabase(destinationPath) {
  if (typeof destinationPath !== 'string' || !destinationPath.trim()) {
    throw new Error('A destination path is required for database backups.');
  }

  const databasePath = resolveDatabasePath();
  if (!(await fileExists(databasePath))) {
    throw new Error('Database file not found.');
  }

  const resolvedDestination = path.resolve(destinationPath);
  if (resolvedDestination === path.resolve(databasePath)) {
    throw new Error('Destination must be different from the live database file.');
  }
  await copyFileAtomic(databasePath, resolvedDestination);

  return {
    success: true,
    destination: resolvedDestination
  };
}

async function restoreDatabase(sourcePath) {
  if (typeof sourcePath !== 'string' || !sourcePath.trim()) {
    throw new Error('A source path is required to restore the database.');
  }

  const resolvedSource = path.resolve(sourcePath);
  if (!(await fileExists(resolvedSource))) {
    throw new Error('Database backup file not found.');
  }

  const databasePath = resolveDatabasePath();
  const databaseDirectory = path.dirname(databasePath);
  await fsp.mkdir(databaseDirectory, { recursive: true });

  const wasRunning = backendSpawner.getStatus().running;
  if (wasRunning) {
    await backendSpawner.stop();
  }

  let backupPath;

  try {
    if (await fileExists(databasePath)) {
      backupPath = `${databasePath}.bak-${Date.now()}`;
      await copyFileAtomic(databasePath, backupPath);
    }

    await copyFileAtomic(resolvedSource, databasePath);
  } catch (error) {
    if (backupPath && (await fileExists(backupPath))) {
      try {
        await copyFileAtomic(backupPath, databasePath);
      } catch (restoreError) {
        log.error('Failed to restore original database after error', restoreError);
      }
    }
    throw error;
  } finally {
    if (wasRunning) {
      try {
        await backendSpawner.start();
      } catch (startError) {
        log.error('Failed to restart backend after database restore', startError);
        throw new Error(`Database restored but backend could not be restarted: ${startError.message}`);
      }
    }
  }

  return {
    success: true,
    restoredTo: databasePath,
    backupPath: backupPath ?? null
  };
}

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
  updateTrayMenu(getDefaultTrayTemplate());
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

  ipcMain.handle('backend:start', async () => {
    await backendSpawner.start();
    return backendSpawner.getStatus();
  });

  ipcMain.handle('backend:stop', async (_event, options = {}) => {
    const { force = false } = options || {};
    await backendSpawner.stop({ force: Boolean(force) });
    return backendSpawner.getStatus();
  });

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

  ipcMain.handle('dialog:save-file', async (_event, options = {}) => {
    const result = await dialog.showSaveDialog(mainWindow ?? undefined, { ...options });
    return result;
  });

  ipcMain.handle('notification:show', (_event, payload = {}) => {
    const { title, body } = payload;
    showNotification(title, body);
    return true;
  });

  ipcMain.handle('window:minimize', (event) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    window?.minimize();
    return true;
  });

  ipcMain.handle('window:maximize', (event) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    window?.maximize();
    return true;
  });

  ipcMain.handle('window:unmaximize', (event) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    window?.unmaximize();
    return true;
  });

  ipcMain.handle('window:toggle-maximize', (event) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (!window) {
      return false;
    }
    if (window.isMaximized()) {
      window.unmaximize();
    } else {
      window.maximize();
    }
    return window.isMaximized();
  });

  ipcMain.handle('window:focus', (event) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    if (!window) {
      return false;
    }
    window.show();
    window.focus();
    return true;
  });

  ipcMain.handle('window:close', (event) => {
    const window = BrowserWindow.fromWebContents(event.sender);
    window?.close();
    return true;
  });

  ipcMain.handle('window:get-state', () => {
    if (!mainWindow) {
      return {
        isFocused: false,
        isVisible: false,
        isMinimized: false,
        isMaximized: false
      };
    }

    return {
      isFocused: mainWindow.isFocused(),
      isVisible: mainWindow.isVisible(),
      isMinimized: mainWindow.isMinimized(),
      isMaximized: mainWindow.isMaximized()
    };
  });

  ipcMain.handle('app:quit', () => {
    app.quit();
    return true;
  });

  ipcMain.handle('system:badge:set-count', (_event, count) => {
    if (typeof count !== 'number' || Number.isNaN(count)) {
      throw new Error('Badge count must be a number.');
    }

    if (typeof app.setBadgeCount === 'function') {
      return app.setBadgeCount(Math.max(0, Math.floor(count)));
    }

    if (process.platform === 'win32' && mainWindow) {
      // Windows does not support badge counts natively; clear overlay icon instead.
      if (count > 0) {
        mainWindow.flashFrame(true);
      } else {
        mainWindow.flashFrame(false);
      }
      return true;
    }

    return false;
  });

  ipcMain.handle('system:badge:clear', () => {
    if (typeof app.setBadgeCount === 'function') {
      app.setBadgeCount(0);
      return true;
    }

    if (process.platform === 'win32' && mainWindow) {
      mainWindow.flashFrame(false);
      return true;
    }

    return false;
  });

  ipcMain.handle('system:tray:update', (_event, payload = {}) => {
    if (!tray) {
      createTray();
    }

    const { tooltip, items } = payload;

    if (typeof tooltip === 'string') {
      tray?.setToolTip(tooltip);
    }

    if (Array.isArray(items)) {
      updateTrayMenu(items);
    }

    return true;
  });

  ipcMain.handle('system:menu:set-application-menu', (_event, payload = {}) => {
    const { items } = payload;
    const sanitizedItems = sanitizeMenuItems(items);
    if (!sanitizedItems.length) {
      Menu.setApplicationMenu(null);
      return true;
    }

    const menu = Menu.buildFromTemplate(sanitizedItems);
    Menu.setApplicationMenu(menu);
    return true;
  });

  ipcMain.handle('system:menu:clear', () => {
    Menu.setApplicationMenu(null);
    return true;
  });

  ipcMain.handle('database:backup', async (_event, payload = {}) => {
    const { destination } = payload;
    return backupDatabase(destination);
  });

  ipcMain.handle('database:restore', async (_event, payload = {}) => {
    const { source } = payload;
    return restoreDatabase(source);
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
  backendSpawner.on('spawned', ({ process }) => {
    processMonitor.watch(process);
    void healthChecker.start();
    sendToAllWindows('backend:spawned', {
      pid: process?.pid ?? null,
      host: BACKEND_HOST,
      port: BACKEND_PORT
    });
  });

  backendSpawner.on('ready', () => {
    backendStartupError = null;
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
      message: 'Backend exited unexpectedly. Attempting automatic restart.',
      details
    });
  });

  backendSpawner.on('error', (error) => {
    backendStartupError = error;
    sendToAllWindows('backend:error', { message: error.message });
  });

  healthChecker.on('startup', () => {
    sendToAllWindows('backend:health-startup', {});
  });

  healthChecker.on('startup-delay', ({ delayMs }) => {
    sendToAllWindows('backend:health-wait', { delayMs });
  });

  healthChecker.on('startup-timeout', () => {
    sendToAllWindows('backend:health', { healthy: false, reason: 'timeout' });
    showNotification('Backend startup delayed', 'RecruitPro backend did not respond within 30 seconds.');
  });

  healthChecker.on('healthy', () => {
    sendToAllWindows('backend:health', { healthy: true });
  });

  healthChecker.on('unhealthy', () => {
    sendToAllWindows('backend:health', { healthy: false });
    showNotification('Backend degraded', 'RecruitPro backend is not responding.');
  });

  processMonitor.on('stats', (stats) => {
    sendToAllWindows('backend:resource-usage', stats);
  });

  processMonitor.on('zombie-detected', ({ pid }) => {
    sendToAllWindows('backend:zombie', { pid });
    showNotification('Backend monitor warning', 'Backend process is unresponsive and will be restarted.');
  });

  processMonitor.on('exit', (details) => {
    sendToAllWindows('backend:process-exit', details);
  });

  restartManager.on('scheduled', ({ attempt, delayMs, reason }) => {
    sendToAllWindows('backend:restart-scheduled', { attempt, delayMs, reason });
  });

  restartManager.on('restarting', ({ attempt }) => {
    sendToAllWindows('backend:restarting', { attempt });
  });

  restartManager.on('restarted', ({ attempt }) => {
    sendToAllWindows('backend:restarted', { attempt });
    showNotification('Backend restarted', `Attempt ${attempt} succeeded.`);
  });

  restartManager.on('attempt-failed', ({ attempt, error }) => {
    sendToAllWindows('backend:restart-attempt-failed', { attempt, message: error?.message });
  });

  restartManager.on('failed', ({ attempts }) => {
    sendToAllWindows('backend:restart-failed', { attempts });
    showNotification('Backend restart failed', 'RecruitPro backend could not be restarted. Please restart the app.');
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
  restartManager.stop();
  processMonitor.stop();
  backendSpawner.stop().catch((error) => {
    log.error('Failed to stop backend cleanly', error);
  });
});
