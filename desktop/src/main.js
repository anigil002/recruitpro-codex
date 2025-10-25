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
const util = require('util');
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

const DEFAULT_CONFIGURATION = Object.freeze({
  preferences: {},
  apiKeys: {}
});

let mainWindow;
let tray;
let backendStartupError = null;
let configuration = null;

const FORCE_AUTO_UPDATE = process.env.FORCE_AUTO_UPDATE === '1';
let autoUpdaterReady = false;

const APP_PATHS = computeApplicationPaths();
initializeApplicationDirectories(APP_PATHS);

const log = createLogger('desktop-main', { directory: APP_PATHS.logsDir });

configuration = loadConfiguration(APP_PATHS.configFile, log);
applyConfigurationToEnvironment(configuration, APP_PATHS, log);

log.info('Main process bootstrapped', {
  configPath: APP_PATHS.configFile,
  logsDir: APP_PATHS.logsDir,
  storageDir: APP_PATHS.storageDir,
  databaseFile: APP_PATHS.databaseFile
});

log.info('Configuration loaded', {
  preferenceCount: Object.keys(configuration?.preferences ?? {}).length,
  apiKeyCount: Object.keys(configuration?.apiKeys ?? {}).length
});

process.on('uncaughtException', (error) => {
  log.error('Uncaught exception in main process', error);
});

process.on('unhandledRejection', (reason) => {
  if (reason instanceof Error) {
    log.error('Unhandled promise rejection in main process', reason);
  } else {
    log.error('Unhandled promise rejection in main process', { reason });
  }
});

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
    if (!isAutoUpdaterSupported()) {
      log.info('Auto updater is disabled in the current environment.');
      sendToAllWindows('auto-updater:error', {
        message: 'Updates are only available in packaged builds.'
      });
      return;
    }

    if (!autoUpdaterReady) {
      const message = 'Auto update feed is not configured. Please verify publish settings.';
      log.warn(message);
      sendToAllWindows('auto-updater:error', { message });
      return;
    }

    autoUpdater.checkForUpdates().catch((error) => {
      log.error('Failed to check for updates', error);
      sendToAllWindows('auto-updater:error', { message: error.message });
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

function computeApplicationPaths() {
  const userData = app.getPath('userData');
  const runtimeDir = path.join(userData, 'runtime');

  return {
    userData,
    runtimeDir,
    logsDir: path.join(userData, 'logs'),
    storageDir: path.join(userData, 'storage'),
    databaseDir: path.join(userData, 'database'),
    databaseFile: path.join(userData, 'database', 'recruitpro.db'),
    backupsDir: path.join(userData, 'backups'),
    tempDir: path.join(userData, 'temp'),
    configFile: path.join(userData, 'config.json')
  };
}

function initializeApplicationDirectories(paths = {}) {
  const directories = [
    paths.userData,
    paths.runtimeDir,
    paths.logsDir,
    paths.storageDir,
    paths.databaseDir,
    paths.backupsDir,
    paths.tempDir
  ].filter(Boolean);

  directories.forEach((dir) => ensureDirectorySync(dir));
}

function ensureDirectorySync(directoryPath) {
  if (!directoryPath) {
    return;
  }

  try {
    fs.mkdirSync(directoryPath, { recursive: true });
  } catch (error) {
    console.error('Failed to create directory', directoryPath, error);
    throw error;
  }
}

function createLogger(namespace, options = {}) {
  const { directory } = options;
  const safeNamespace = String(namespace || 'app')
    .toLowerCase()
    .replace(/[^a-z0-9-_]/gi, '-');
  const dateSegment = new Date().toISOString().slice(0, 10);

  let logFilePath = null;
  let stream = null;

  if (directory) {
    try {
      ensureDirectorySync(directory);
      logFilePath = path.join(directory, `${safeNamespace}-${dateSegment}.log`);
      stream = fs.createWriteStream(logFilePath, { flags: 'a' });
    } catch (error) {
      console.error('Failed to initialize log file stream', error);
      logFilePath = null;
      stream = null;
    }
  }

  const write = (level, args) => {
    const timestamp = new Date().toISOString();
    const formatted = util.formatWithOptions({ depth: 5, colors: false }, ...args);

    if (stream) {
      stream.write(`[${timestamp}] [${level.toUpperCase()}] [${namespace}] ${formatted}\n`);
    }

    const consoleMethod =
      level === 'error'
        ? console.error
        : level === 'warn'
        ? console.warn
        : level === 'debug'
        ? console.debug
        : console.log;

    consoleMethod(`[${namespace}]`, ...args);
  };

  const logger = {
    info: (...args) => write('info', args),
    warn: (...args) => write('warn', args),
    error: (...args) => write('error', args),
    debug: (...args) => write('debug', args),
    filePath: logFilePath,
    dispose: () =>
      new Promise((resolve) => {
        if (!stream) {
          resolve();
          return;
        }

        stream.end(() => resolve());
      })
  };

  return logger;
}

function normalizeConfiguration(rawConfig) {
  const normalized = {
    preferences: {},
    apiKeys: {}
  };

  if (!rawConfig || typeof rawConfig !== 'object') {
    return normalized;
  }

  const { preferences, apiKeys, ...rest } = rawConfig;

  if (preferences && typeof preferences === 'object' && !Array.isArray(preferences)) {
    normalized.preferences = { ...preferences };
  }

  if (apiKeys && typeof apiKeys === 'object' && !Array.isArray(apiKeys)) {
    normalized.apiKeys = { ...apiKeys };
  }

  return { ...rest, ...normalized };
}

function loadConfiguration(configPath, logger) {
  try {
    if (!configPath || !fs.existsSync(configPath)) {
      return normalizeConfiguration(DEFAULT_CONFIGURATION);
    }

    const raw = fs.readFileSync(configPath, 'utf8');
    if (!raw.trim()) {
      return normalizeConfiguration(DEFAULT_CONFIGURATION);
    }

    const parsed = JSON.parse(raw);
    return normalizeConfiguration(parsed);
  } catch (error) {
    logger?.warn?.('Failed to read configuration file, falling back to defaults', {
      message: error.message,
      configPath
    });
    return normalizeConfiguration(DEFAULT_CONFIGURATION);
  }
}

function mergeConfiguration(currentConfig, updates) {
  const base = normalizeConfiguration(currentConfig ?? DEFAULT_CONFIGURATION);

  if (!updates || typeof updates !== 'object') {
    return base;
  }

  const next = {
    ...base,
    preferences: { ...base.preferences },
    apiKeys: { ...base.apiKeys }
  };

  if (updates.preferences && typeof updates.preferences === 'object' && !Array.isArray(updates.preferences)) {
    for (const [key, value] of Object.entries(updates.preferences)) {
      if (value === null) {
        delete next.preferences[key];
      } else {
        next.preferences[key] = value;
      }
    }
  }

  if (updates.apiKeys && typeof updates.apiKeys === 'object' && !Array.isArray(updates.apiKeys)) {
    for (const [key, value] of Object.entries(updates.apiKeys)) {
      if (value === null || value === undefined || value === '') {
        delete next.apiKeys[key];
      } else {
        next.apiKeys[key] = value;
      }
    }
  }

  for (const [key, value] of Object.entries(updates)) {
    if (key === 'preferences' || key === 'apiKeys') {
      continue;
    }
    next[key] = value;
  }

  return next;
}

async function saveConfiguration(configPath, config, logger) {
  const normalized = normalizeConfiguration(config);
  const serialized = `${JSON.stringify(normalized, null, 2)}\n`;

  try {
    await fsp.mkdir(path.dirname(configPath), { recursive: true });
    await fsp.writeFile(configPath, serialized, 'utf8');
    logger?.info?.('Configuration saved', { configPath });
  } catch (error) {
    logger?.error?.('Failed to persist configuration', error);
    throw error;
  }

  return normalized;
}

const appliedApiKeyEnvVars = new Set();

function applyConfigurationToEnvironment(config, paths, logger) {
  const normalized = normalizeConfiguration(config ?? DEFAULT_CONFIGURATION);

  if (paths?.storageDir) {
    process.env.RECRUITPRO_STORAGE_PATH = paths.storageDir;
  }

  if (paths?.databaseFile) {
    process.env.RECRUITPRO_DATABASE_URL = buildSqliteUrl(paths.databaseFile);
  }

  if (paths?.backupsDir) {
    process.env.RECRUITPRO_BACKUP_DIR = paths.backupsDir;
  }

  if (paths?.logsDir) {
    process.env.RECRUITPRO_LOG_DIR = paths.logsDir;
  }

  if (paths?.configFile) {
    process.env.RECRUITPRO_CONFIG_PATH = paths.configFile;
  }

  if (paths?.userData) {
    process.env.RECRUITPRO_USER_DATA = paths.userData;
  }

  if (paths?.runtimeDir) {
    process.env.RECRUITPRO_RUNTIME_PATH = paths.runtimeDir;
  }

  const apiKeys = normalized.apiKeys ?? {};
  const nextApplied = new Set();

  for (const [key, value] of Object.entries(apiKeys)) {
    let envKey = key;
    if (!envKey.startsWith('RECRUITPRO_')) {
      envKey = `RECRUITPRO_${envKey.toUpperCase()}`;
    }

    if (value === null || value === undefined || value === '') {
      continue;
    }

    process.env[envKey] = value;
    nextApplied.add(envKey);
  }

  for (const key of appliedApiKeyEnvVars) {
    if (!nextApplied.has(key)) {
      delete process.env[key];
    }
  }

  appliedApiKeyEnvVars.clear();
  nextApplied.forEach((key) => appliedApiKeyEnvVars.add(key));

  logger?.debug?.('Environment configured', {
    storageDir: paths?.storageDir ?? null,
    databaseFile: paths?.databaseFile ?? null,
    configPath: paths?.configFile ?? null,
    appliedApiKeyCount: nextApplied.size
  });

  return normalized;
}

function buildSqliteUrl(databaseFile) {
  const absolute = path.resolve(databaseFile);
  const normalized = absolute.replace(/\\/g, '/');

  if (process.platform === 'win32') {
    return `sqlite:///${normalized}`;
  }

  return `sqlite:////${normalized}`;
}

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
  return APP_PATHS.databaseFile;
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
  const databasePath = resolveDatabasePath();
  if (!(await fileExists(databasePath))) {
    throw new Error('Database file not found.');
  }

  let resolvedDestination = destinationPath;
  if (typeof resolvedDestination !== 'string' || !resolvedDestination.trim()) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    resolvedDestination = path.join(APP_PATHS.backupsDir, `recruitpro-${timestamp}.db`);
  }

  if (!path.isAbsolute(resolvedDestination)) {
    resolvedDestination = path.join(APP_PATHS.backupsDir, resolvedDestination);
  }

  resolvedDestination = path.resolve(resolvedDestination);

  if (resolvedDestination === path.resolve(databasePath)) {
    throw new Error('Destination must be different from the live database file.');
  }

  await copyFileAtomic(databasePath, resolvedDestination);

  log.info('Database backup created', { destination: resolvedDestination });

  return {
    success: true,
    destination: resolvedDestination,
    source: databasePath
  };
}

async function restoreDatabase(sourcePath) {
  if (typeof sourcePath !== 'string' || !sourcePath.trim()) {
    throw new Error('A source path is required to restore the database.');
  }

  let resolvedSource = sourcePath;
  if (!path.isAbsolute(resolvedSource)) {
    resolvedSource = path.join(APP_PATHS.backupsDir, resolvedSource);
  }

  resolvedSource = path.resolve(resolvedSource);
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

  log.info('Database restored from backup', {
    source: resolvedSource,
    restoredTo: databasePath
  });

  return {
    success: true,
    restoredTo: databasePath,
    backupPath: backupPath ?? null
  };
}

async function prepareRuntimeResources() {
  const directories = [
    APP_PATHS.storageDir,
    APP_PATHS.databaseDir,
    APP_PATHS.backupsDir,
    APP_PATHS.runtimeDir,
    APP_PATHS.tempDir
  ].filter(Boolean);

  for (const directory of directories) {
    try {
      await fsp.mkdir(directory, { recursive: true });
    } catch (error) {
      log.error('Failed to ensure application directory', { directory, error });
      throw error;
    }
  }

  const databasePath = resolveDatabasePath();
  const databaseExists = await fileExists(databasePath);

  if (!databaseExists) {
    const backendRoot = backendSpawner.resolveBackendRoot();
    const bundledDatabase = path.join(backendRoot, 'data', 'recruitpro.db');

    if (await fileExists(bundledDatabase)) {
      try {
        await copyFileAtomic(bundledDatabase, databasePath);
        log.info('Seeded database from bundled copy', { source: bundledDatabase, target: databasePath });
      } catch (error) {
        log.error('Failed to seed database from bundled copy', error);
        throw error;
      }
    } else {
      log.debug('No bundled database found, backend will initialize a new database', {
        databasePath
      });
    }
  }
}

function getBackendUrl() {
  return `http://${BACKEND_HOST}:${BACKEND_PORT}`;
}

function sendToAllWindows(channel, payload) {
  BrowserWindow.getAllWindows().forEach((window) => {
    window.webContents.send(channel, payload);
  });
}

function getSerializablePathsSnapshot() {
  return {
    userData: APP_PATHS.userData,
    runtimeDir: APP_PATHS.runtimeDir,
    logsDir: APP_PATHS.logsDir,
    storageDir: APP_PATHS.storageDir,
    databaseDir: APP_PATHS.databaseDir,
    databaseFile: APP_PATHS.databaseFile,
    backupsDir: APP_PATHS.backupsDir,
    tempDir: APP_PATHS.tempDir,
    configFile: APP_PATHS.configFile,
    logFile: log.filePath ?? null
  };
}

function broadcastConfiguration() {
  if (!configuration) {
    return;
  }

  sendToAllWindows('config:updated', configuration);
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
      sandbox: true
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
    if (configuration) {
      mainWindow.webContents.send('config:updated', configuration);
    }

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

function isAutoUpdaterSupported() {
  return app.isPackaged || FORCE_AUTO_UPDATE;
}

function configureAutoUpdaterFeed() {
  const envUrlCandidate = [
    process.env.RECRUITPRO_UPDATE_FEED_URL,
    process.env.RECRUITPRO_UPDATE_URL,
    process.env.AUTO_UPDATE_URL
  ].find((value) => typeof value === 'string' && value.trim().length > 0);

  if (envUrlCandidate) {
    const normalized = envUrlCandidate.replace(/\/+$/, '');
    try {
      autoUpdater.setFeedURL({ provider: 'generic', url: normalized });
      autoUpdaterReady = true;
      log.info('Auto updater feed configured from environment', { url: normalized });
      return;
    } catch (error) {
      log.error('Failed to configure auto updater feed from environment', error);
    }
  }

  if (typeof autoUpdater.getFeedURL === 'function') {
    try {
      const resolvedFeed = autoUpdater.getFeedURL();
      if (resolvedFeed) {
        autoUpdaterReady = true;
        log.info('Auto updater feed resolved from build configuration', { url: resolvedFeed });
        return;
      }
    } catch (error) {
      log.error('Failed to read auto updater feed URL', error);
    }
  }

  autoUpdaterReady = false;
  log.warn('Auto updater feed URL is not configured; updates are disabled.');
}

function setupAutoUpdater() {
  autoUpdater.logger = log;
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  if (!isAutoUpdaterSupported()) {
    autoUpdaterReady = false;
    log.info('Auto updater disabled for development builds.');
    return;
  }

  configureAutoUpdaterFeed();

  if (!autoUpdaterReady) {
    sendToAllWindows('auto-updater:error', {
      message: 'Auto updater feed URL is not configured.'
    });
    return;
  }

  autoUpdater.on('checking-for-update', () => {
    log.info('Checking for updates');
    sendToAllWindows('auto-updater:checking');
  });

  autoUpdater.on('update-available', (info) => {
    log.info('Update available', { version: info?.version ?? null });
    sendToAllWindows('auto-updater:update-available', info);
    showNotification('Update available', 'A new version is available. Downloading will begin shortly.');
    autoUpdater.downloadUpdate().catch((error) => {
      log.error('Auto update download failed', error);
    });
  });

  autoUpdater.on('update-not-available', (info) => {
    log.info('No update available', { version: info?.version ?? null });
    sendToAllWindows('auto-updater:update-not-available', info);
  });

  autoUpdater.on('download-progress', (progress) => {
    log.debug('Update download progress', {
      percent: Math.round(progress?.percent ?? 0),
      transferred: progress?.transferred ?? null,
      total: progress?.total ?? null
    });
    sendToAllWindows('auto-updater:download-progress', progress);
  });

  autoUpdater.on('update-downloaded', (info) => {
    log.info('Update downloaded', { version: info?.version ?? null });
    sendToAllWindows('auto-updater:update-downloaded', info);
    showNotification('Update ready to install', 'Restart the application to apply the update.');
  });

  autoUpdater.on('error', (error) => {
    log.error('Auto updater encountered an error', error);
    sendToAllWindows('auto-updater:error', { message: error.message });
  });

  autoUpdater
    .checkForUpdates()
    .catch((error) => {
      log.error('Initial update check failed', error);
      sendToAllWindows('auto-updater:error', { message: error.message });
    });
}

function registerIpcHandlers() {
  ipcMain.handle('config:get', () => configuration);

  ipcMain.handle('config:update', async (_event, payload = {}) => {
    configuration = mergeConfiguration(configuration, payload);
    configuration = await saveConfiguration(APP_PATHS.configFile, configuration, log);
    applyConfigurationToEnvironment(configuration, APP_PATHS, log);
    broadcastConfiguration();
    return configuration;
  });

  ipcMain.handle('system:paths:get', () => getSerializablePathsSnapshot());

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
    if (!isAutoUpdaterSupported() || !autoUpdaterReady) {
      log.info('Auto updater check skipped because the updater is not configured.');
      return false;
    }

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
  log.info('Electron app ready event received');

  if (process.platform === 'win32') {
    app.setAppUserModelId('com.recruitpro.desktop');
  }

  registerIpcHandlers();
  wireBackendEvents();
  createTray();
  setupAutoUpdater();

  log.info('Preparing application runtime');
  await prepareRuntimeResources();

  try {
    log.info('Starting backend process');
    await backendSpawner.start();
  } catch (error) {
    log.error('Backend failed to start on initial attempt', error);
    backendStartupError = error;
  }

  await createWindow();

  broadcastConfiguration();
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
  log.info('Application shutting down');
  healthChecker.stop();
  restartManager.stop();
  processMonitor.stop();
  backendSpawner.stop().catch((error) => {
    log.error('Failed to stop backend cleanly', error);
  });
});
