const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');

const BACKEND_HOST = process.env.BACKEND_HOST || '127.0.0.1';
const BACKEND_PORT = Number.parseInt(process.env.BACKEND_PORT || '8000', 10);

let mainWindow;
let backendProcess;
let backendReady = false;
let backendStartupError = null;
let isQuitting = false;

const log = (...args) => {
  console.log('[desktop]', ...args);
};

function resolveBackendRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend');
  }
  return path.resolve(__dirname, '..', '..');
}

function getPythonExecutable() {
  if (process.env.ELECTRON_PYTHON) {
    return process.env.ELECTRON_PYTHON;
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

function spawnBackend() {
  const pythonExec = getPythonExecutable();
  const backendRoot = resolveBackendRoot();
  const args = [
    '-m',
    'uvicorn',
    'app.main:app',
    '--host',
    BACKEND_HOST,
    '--port',
    String(BACKEND_PORT)
  ];

  if (!app.isPackaged && process.env.UVICORN_RELOAD !== '0') {
    args.push('--reload');
  }

  log(`Starting backend using ${pythonExec} ${args.join(' ')}`);
  backendProcess = spawn(pythonExec, args, {
    cwd: backendRoot,
    env: {
      ...process.env,
      PYTHONPATH: backendRoot,
      BACKEND_HOST,
      BACKEND_PORT: String(BACKEND_PORT)
    },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  backendProcess.on('error', (error) => {
    console.error('Unable to spawn backend process', error);
  });

  backendProcess.stdout.on('data', (chunk) => {
    log(`[backend] ${chunk.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (chunk) => {
    console.error('[backend]', chunk.toString().trim());
  });

  backendProcess.on('exit', (code, signal) => {
    console.error(`[backend] exited with code ${code} signal ${signal}`);
    backendProcess = undefined;
    backendReady = false;
    if (!isQuitting) {
      const options = { type: 'warning', message: 'Backend exited unexpectedly. Please restart the application.' };
      if (BrowserWindow.getAllWindows().length > 0) {
        BrowserWindow.getAllWindows()[0].webContents.send('backend:exit', options);
      }
    }
  });
}

function waitForBackendReady(host, port, timeoutMs = 30000, intervalMs = 500) {
  const start = Date.now();

  return new Promise((resolve, reject) => {
    const check = () => {
      const socket = net.createConnection({ host, port });
      socket.once('connect', () => {
        socket.end();
        resolve();
      });
      socket.once('error', (error) => {
        socket.destroy();
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Backend did not become ready on ${host}:${port} within ${timeoutMs}ms (${error.message})`));
          return;
        }
        setTimeout(check, intervalMs);
      });
    };

    check();
  });
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
    if (backendReady) {
      mainWindow.webContents.send('backend:ready', {
        url: `http://${BACKEND_HOST}:${BACKEND_PORT}`
      });
    }
    if (backendStartupError) {
      mainWindow.webContents.send('backend:exit', {
        type: 'error',
        message: backendStartupError.message || 'Backend failed to start.'
      });
    }
  });

  const rendererPath = path.join(__dirname, '..', 'renderer', 'recruitpro_ats.html');
  await mainWindow.loadFile(rendererPath);
}

function broadcastBackendReady() {
  backendReady = true;
  backendStartupError = null;
  BrowserWindow.getAllWindows().forEach((window) => {
    window.webContents.send('backend:ready', {
      url: `http://${BACKEND_HOST}:${BACKEND_PORT}`
    });
  });
}

function handleAppReady() {
  spawnBackend();
  waitForBackendReady(BACKEND_HOST, BACKEND_PORT)
    .then(() => {
      log(`Backend ready on http://${BACKEND_HOST}:${BACKEND_PORT}`);
      broadcastBackendReady();
    })
    .catch((error) => {
      console.error('Backend failed to start', error);
      backendStartupError = error;
    })
    .finally(() => {
      createWindow().catch((err) => console.error('Failed to create window', err));
    });
}

app.whenReady().then(() => {
  if (process.platform === 'win32') {
    app.setAppUserModelId('com.recruitpro.desktop');
  }
  handleAppReady();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow().catch((err) => console.error('Failed to recreate window', err));
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
});

ipcMain.handle('backend:get-url', () => {
  return `http://${BACKEND_HOST}:${BACKEND_PORT}`;
});
