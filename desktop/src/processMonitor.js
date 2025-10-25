const { EventEmitter } = require('events');

class ProcessMonitor extends EventEmitter {
  constructor(options = {}) {
    super();
    const { logger = console, pollIntervalMs = 10000 } = options;

    this.logger = logger;
    this.pollIntervalMs = pollIntervalMs;

    this._process = undefined;
    this._timer = undefined;
    this._exitHandler = undefined;
  }

  watch(childProcess) {
    this.stop();

    if (!childProcess) {
      return;
    }

    this._process = childProcess;
    this.logger.info?.('Attaching process monitor', {
      pid: childProcess.pid
    });

    this._exitHandler = (code, signal) => {
      const usage = typeof childProcess.resourceUsage === 'function' ? childProcess.resourceUsage() : undefined;
      this.logger.error?.('Backend process exited', { code, signal, usage });
      this.emit('exit', { code, signal, usage });
      this.stop();
    };

    childProcess.once('exit', this._exitHandler);

    this._timer = setInterval(() => {
      void this._poll();
    }, this.pollIntervalMs);

    void this._poll();
  }

  stop() {
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = undefined;
    }

    if (this._process && this._exitHandler) {
      this._process.off('exit', this._exitHandler);
    }

    this._process = undefined;
    this._exitHandler = undefined;
  }

  async _poll() {
    if (!this._process || !this._process.pid) {
      return;
    }

    const { pid } = this._process;

    try {
      process.kill(pid, 0);
    } catch (error) {
      if (error.code === 'ESRCH') {
        this.logger.warn?.('Backend process is no longer running. Possible zombie detected.', { pid });
        this.emit('zombie-detected', { pid });
        this.stop();
      } else {
        this.logger.debug?.('Process monitor unable to query process state', { pid, error });
      }
      return;
    }

    let usage;
    try {
      usage = typeof this._process.resourceUsage === 'function' ? this._process.resourceUsage() : undefined;
    } catch (error) {
      this.logger.debug?.('Failed to capture resource usage for backend process', { pid, error });
    }

    if (usage) {
      this.logger.debug?.('Backend resource usage snapshot', { pid, usage });
    }

    this.emit('stats', { pid, usage });
  }
}

module.exports = ProcessMonitor;
