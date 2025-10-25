const { EventEmitter } = require('events');
const http = require('http');

class HealthChecker extends EventEmitter {
  constructor(options = {}) {
    super();
    const {
      host = '127.0.0.1',
      port = 8000,
      path = '/health',
      intervalMs = 10000,
      logger = console
    } = options;

    this.host = host;
    this.port = port;
    this.path = path.startsWith('/') ? path : `/${path}`;
    this.intervalMs = intervalMs;
    this.logger = logger;

    this._interval = undefined;
    this._lastStatus = undefined;
    this._pending = false;
  }

  start() {
    if (this._interval) {
      return;
    }

    this.logger.info?.(`Starting backend health checker on ${this.host}:${this.port}${this.path}`);
    this._interval = setInterval(() => {
      void this.check();
    }, this.intervalMs);

    // kick off immediately
    void this.check();
  }

  stop() {
    if (this._interval) {
      clearInterval(this._interval);
      this._interval = undefined;
    }
  }

  async check() {
    if (this._pending) {
      return;
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
      }
    } finally {
      this._pending = false;
    }
  }
}

module.exports = HealthChecker;
