const { EventEmitter } = require('events');
const http = require('http');

class HealthChecker extends EventEmitter {
  constructor(options = {}) {
    super();
    const {
      host = '127.0.0.1',
      port = 8000,
      path = '/api/health',
      intervalMs = 5000,
      logger = console,
      startupTimeoutMs = 30000,
      startupInitialDelayMs = 500,
      startupMaxDelayMs = 5000
    } = options;

    this.host = host;
    this.port = port;
    this.path = path.startsWith('/') ? path : `/${path}`;
    this.intervalMs = intervalMs;
    this.logger = logger;
    this.startupTimeoutMs = startupTimeoutMs;
    this.startupInitialDelayMs = startupInitialDelayMs;
    this.startupMaxDelayMs = startupMaxDelayMs;

    this._interval = undefined;
    this._lastStatus = undefined;
    this._pending = false;
    this._startupPromise = undefined;
    this._stopped = true;
    this._readyNotified = false;
  }

  async start() {
    if (this._interval) {
      return this._startupPromise ?? Promise.resolve();
    }

    this.logger.info?.(`Starting backend health checker on ${this.host}:${this.port}${this.path}`);
    this._stopped = false;
    this._readyNotified = false;
    this._interval = setInterval(() => {
      void this.check();
    }, this.intervalMs);

    const startupPromise = this._runStartupChecks();
    this._startupPromise = startupPromise;
    startupPromise.finally(() => {
      if (this._startupPromise === startupPromise) {
        this._startupPromise = undefined;
      }
    });
    void this.check();
    return startupPromise;
  }

  stop() {
    if (this._interval) {
      clearInterval(this._interval);
      this._interval = undefined;
    }
    this._stopped = true;
    this._startupPromise = undefined;
    this._lastStatus = undefined;
    this._readyNotified = false;
  }

  async check() {
    if (this._pending) {
      return this._lastStatus ?? false;
    }

    this._pending = true;

    try {
      const healthy = await new Promise((resolve) => {
        const request = http.get(
          {
            host: this.host,
            port: this.port,
            path: this.path,
            timeout: this.intervalMs / 2
          },
          (response) => {
            const success = response.statusCode && response.statusCode < 500;
            response.resume();
            resolve(success);
          }
        );

        request.on('timeout', () => {
          request.destroy(new Error('Health check timed out'));
          resolve(false);
        });

        request.on('error', (error) => {
          this.logger.debug?.('Health check error', error);
          resolve(false);
        });
      });

      if (healthy !== this._lastStatus) {
        this._lastStatus = healthy;
        this.emit('status-changed', healthy);
        this.emit(healthy ? 'healthy' : 'unhealthy', { healthy });
      }

      if (healthy && !this._readyNotified) {
        this.emit('ready');
        this._readyNotified = true;
      }

      return healthy;
    } finally {
      this._pending = false;
    }
  }

  async _runStartupChecks() {
    const deadline = Date.now() + this.startupTimeoutMs;
    let delayMs = this.startupInitialDelayMs;
    this.emit('startup');

    while (!this._stopped) {
      const healthy = await this.check();
      if (healthy) {
        this.logger.info?.('Backend passed health check during startup');
        return true;
      }

      const now = Date.now();
      if (now >= deadline) {
        this.logger.error?.('Backend failed to pass health checks within startup timeout');
        this.emit('startup-timeout');
        return false;
      }

      const waitMs = Math.min(delayMs, deadline - now);
      this.emit('startup-delay', { delayMs: waitMs });
      await new Promise((resolve) => setTimeout(resolve, waitMs));
      delayMs = Math.min(delayMs * 2, this.startupMaxDelayMs);
    }

    return false;
  }
}

module.exports = HealthChecker;
