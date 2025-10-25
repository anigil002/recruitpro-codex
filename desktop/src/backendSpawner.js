const { spawn } = require('child_process');
const { EventEmitter } = require('events');
const net = require('net');
const path = require('path');

class BackendSpawner extends EventEmitter {
  constructor(options = {}) {
    super();
    const {
      app,
      host = '127.0.0.1',
      port = 8000,
      logger = console,
      pythonExecutable,
      reloadOnDev = true
    } = options;

    this.app = app;
    this.host = host;
    this.port = port;
    this.logger = logger;
    this.pythonExecutable = pythonExecutable || this.getPythonExecutable();
    this.reloadOnDev = reloadOnDev;

    this.process = undefined;
    this.ready = false;
    this._startupPromise = undefined;
    this._isQuitting = false;
  }

  getPythonExecutable() {
    if (process.env.ELECTRON_PYTHON) {
      return process.env.ELECTRON_PYTHON;
    }

    return process.platform === 'win32' ? 'python' : 'python3';
  }

  resolveBackendRoot() {
    if (this.app && this.app.isPackaged) {
      return path.join(process.resourcesPath, 'backend');
    }
    return path.resolve(__dirname, '..', '..');
  }

  waitForReady(timeoutMs = 30000, intervalMs = 500) {
    const start = Date.now();

    return new Promise((resolve, reject) => {
      const check = () => {
        const socket = net.createConnection({ host: this.host, port: this.port });
        socket.once('connect', () => {
          socket.end();
          resolve();
        });
        socket.once('error', (error) => {
          socket.destroy();
          if (Date.now() - start > timeoutMs) {
            reject(
              new Error(
                `Backend did not become ready on ${this.host}:${this.port} within ${timeoutMs}ms (${error.message})`
              )
            );
            return;
          }
          setTimeout(check, intervalMs);
        });
      };

      check();
    });
  }

  start() {
    if (this.process) {
      if (this.ready) {
        return Promise.resolve();
      }
      return this._startupPromise ?? Promise.resolve();
    }

    const backendRoot = this.resolveBackendRoot();
    const args = ['-m', 'uvicorn', 'app.main:app', '--host', this.host, '--port', String(this.port)];

    if (!this.app?.isPackaged && this.reloadOnDev && process.env.UVICORN_RELOAD !== '0') {
      args.push('--reload');
    }

    this.logger.info?.('Starting backend process', {
      executable: this.pythonExecutable,
      args,
      cwd: backendRoot
    });

    const env = {
      ...process.env,
      PYTHONPATH: backendRoot,
      BACKEND_HOST: this.host,
      BACKEND_PORT: String(this.port)
    };

    this.process = spawn(this.pythonExecutable, args, {
      cwd: backendRoot,
      env,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    this.process.stdout?.on('data', (chunk) => {
      this.logger.info?.(`[backend] ${chunk.toString().trim()}`);
      this.emit('stdout', chunk.toString());
    });

    this.process.stderr?.on('data', (chunk) => {
      this.logger.error?.(`[backend] ${chunk.toString().trim()}`);
      this.emit('stderr', chunk.toString());
    });

    this.process.on('error', (error) => {
      this.logger.error?.('Failed to spawn backend process', error);
      this.emit('error', error);
    });

    this.process.on('exit', (code, signal) => {
      this.logger.error?.(`Backend exited with code ${code} signal ${signal}`);
      this.ready = false;
      this.process = undefined;
      this._startupPromise = undefined;
      this.emit('exit', { code, signal });
    });

    this._startupPromise = this.waitForReady()
      .then(() => {
        this.ready = true;
        this.emit('ready', { host: this.host, port: this.port });
      })
      .catch((error) => {
        this.logger.error?.('Backend failed to become ready', error);
        this.emit('error', error);
        throw error;
      });

    return this._startupPromise;
  }

  async stop(options = {}) {
    const { force = false } = options;
    this._isQuitting = true;

    if (!this.process) {
      this._startupPromise = undefined;
      this.ready = false;
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      const handleExit = () => {
        this.ready = false;
        this.process = undefined;
        this._startupPromise = undefined;
        resolve();
      };

      this.process.once('exit', handleExit);
      try {
        this.process.kill(force ? 'SIGKILL' : undefined);
      } catch (error) {
        this.logger.error?.('Unable to terminate backend process', error);
        this.process.off('exit', handleExit);
        resolve();
      }
    });
  }

  async restart() {
    await this.stop();
    this._isQuitting = false;
    return this.start();
  }

  getStatus() {
    return {
      running: Boolean(this.process),
      ready: this.ready,
      pid: this.process?.pid ?? null,
      host: this.host,
      port: this.port
    };
  }
}

module.exports = BackendSpawner;
