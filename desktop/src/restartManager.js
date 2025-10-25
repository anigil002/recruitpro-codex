const { EventEmitter } = require('events');

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

class RestartManager extends EventEmitter {
  constructor(spawner, options = {}) {
    super();

    const {
      logger = console,
      maxAttempts = 3,
      baseDelayMs = 2000,
      maxDelayMs = 30000
    } = options;

    this.spawner = spawner;
    this.logger = logger;
    this.maxAttempts = maxAttempts;
    this.baseDelayMs = baseDelayMs;
    this.maxDelayMs = maxDelayMs;

    this._attempts = 0;
    this._restartTimer = undefined;
    this._enabled = true;

    this._handleExit = this._handleExit.bind(this);
    this._handleError = this._handleError.bind(this);
    this._handleReady = this._handleReady.bind(this);

    spawner.on('exit', this._handleExit);
    spawner.on('error', this._handleError);
    spawner.on('ready', this._handleReady);
  }

  disable() {
    this._enabled = false;
    this._clearTimer();
  }

  stop() {
    this.disable();
    this.spawner.off('exit', this._handleExit);
    this.spawner.off('error', this._handleError);
    this.spawner.off('ready', this._handleReady);
  }

  resetAttempts() {
    this._attempts = 0;
  }

  _clearTimer() {
    if (this._restartTimer) {
      clearTimeout(this._restartTimer);
      this._restartTimer = undefined;
    }
  }

  _handleReady() {
    this.logger.info?.('Backend reported ready. Resetting restart attempts.');
    this.resetAttempts();
    this._enabled = true;
    this._clearTimer();
    this.emit('ready');
  }

  _handleError(error) {
    if (this.spawner.isQuitting?.()) {
      return;
    }
    this.logger.error?.('Backend encountered an error', error);
    void this._scheduleRestart('error', error);
  }

  _handleExit(details) {
    if (this.spawner.isQuitting?.()) {
      this.logger.info?.('Backend exited due to intentional shutdown. Skipping auto restart.');
      this.resetAttempts();
      return;
    }
    void this._scheduleRestart('exit', details);
  }

  async _scheduleRestart(reason, details) {
    if (!this._enabled) {
      return;
    }

    if (this._attempts >= this.maxAttempts) {
      this.logger.error?.('Maximum backend restart attempts reached.');
      this.emit('failed', { attempts: this._attempts, reason, details });
      this.disable();
      return;
    }

    this._attempts += 1;
    const delayMs = Math.min(this.baseDelayMs * 2 ** (this._attempts - 1), this.maxDelayMs);

    this.logger.warn?.(`Scheduling backend restart attempt ${this._attempts} in ${delayMs}ms due to ${reason}.`);
    this.emit('scheduled', {
      attempt: this._attempts,
      delayMs,
      reason,
      details
    });

    this._clearTimer();

    this._restartTimer = setTimeout(async () => {
      this.emit('restarting', { attempt: this._attempts, reason });
      try {
        await this.spawner.start();
        this.logger.info?.('Backend restart attempt succeeded.');
        this.emit('restarted', { attempt: this._attempts });
      } catch (error) {
        this.logger.error?.('Backend restart attempt failed', error);
        this.emit('attempt-failed', { attempt: this._attempts, error });
        await wait(this.baseDelayMs);
        void this._scheduleRestart('error', error);
      }
    }, delayMs);
  }
}

module.exports = RestartManager;
