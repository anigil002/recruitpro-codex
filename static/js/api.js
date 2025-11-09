/**
 * Enhanced API client with request cancellation and error handling
 */

class APIClient {
  constructor() {
    this.pendingRequests = new Map();
    this.defaultTimeout = 30000; // 30 seconds
  }

  /**
   * Make an API request with automatic cancellation of duplicate requests
   * @param {string} path - API endpoint path
   * @param {Object} options - Fetch options
   * @param {string} options.cancelKey - Key to identify requests for cancellation (default: path)
   * @param {number} options.timeout - Request timeout in ms
   * @param {Function} options.onUploadProgress - Upload progress callback
   * @returns {Promise<any>} Response data
   */
  async request(path, options = {}) {
    const {
      cancelKey = path,
      timeout = this.defaultTimeout,
      onUploadProgress,
      ...fetchOptions
    } = options;

    // Cancel previous request with same key
    if (this.pendingRequests.has(cancelKey)) {
      this.pendingRequests.get(cancelKey).abort();
    }

    // Create new abort controller
    const controller = new AbortController();
    this.pendingRequests.set(cancelKey, controller);

    // Set up fetch options
    const init = {
      credentials: 'include',
      signal: controller.signal,
      ...fetchOptions,
    };

    // Set headers
    init.headers = new Headers(init.headers || {});
    const authHeader = this.getAuthHeader();
    if (authHeader) {
      init.headers.set('Authorization', authHeader);
    }

    // Handle body serialization
    if (init.body && typeof init.body === 'object' && !(init.body instanceof FormData)) {
      init.headers.set('Content-Type', 'application/json');
      init.body = JSON.stringify(init.body);
    }

    // Set up timeout
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, timeout);

    try {
      const response = await fetch(path, init);
      clearTimeout(timeoutId);

      // Parse response
      const contentType = response.headers.get('content-type');
      let data;

      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      // Handle errors
      if (!response.ok) {
        const error = new Error(
          (typeof data === 'object' && (data.message || data.detail)) ||
          data ||
          `Request failed with status ${response.status}`
        );
        error.status = response.status;
        error.response = data;
        throw error;
      }

      return data;
    } catch (error) {
      clearTimeout(timeoutId);

      // Handle abort
      if (error.name === 'AbortError') {
        const abortError = new Error('Request cancelled');
        abortError.cancelled = true;
        throw abortError;
      }

      // Handle timeout
      if (error.message === 'The user aborted a request.') {
        const timeoutError = new Error('Request timeout');
        timeoutError.timeout = true;
        throw timeoutError;
      }

      throw error;
    } finally {
      this.pendingRequests.delete(cancelKey);
    }
  }

  /**
   * Cancel a specific request by key
   */
  cancel(cancelKey) {
    if (this.pendingRequests.has(cancelKey)) {
      this.pendingRequests.get(cancelKey).abort();
      this.pendingRequests.delete(cancelKey);
    }
  }

  /**
   * Cancel all pending requests
   */
  cancelAll() {
    this.pendingRequests.forEach(controller => controller.abort());
    this.pendingRequests.clear();
  }

  /**
   * GET request
   */
  async get(path, options = {}) {
    return this.request(path, { ...options, method: 'GET' });
  }

  /**
   * POST request
   */
  async post(path, body, options = {}) {
    return this.request(path, { ...options, method: 'POST', body });
  }

  /**
   * PUT request
   */
  async put(path, body, options = {}) {
    return this.request(path, { ...options, method: 'PUT', body });
  }

  /**
   * PATCH request
   */
  async patch(path, body, options = {}) {
    return this.request(path, { ...options, method: 'PATCH', body });
  }

  /**
   * DELETE request
   */
  async delete(path, options = {}) {
    return this.request(path, { ...options, method: 'DELETE' });
  }

  /**
   * Get authorization header
   */
  getAuthHeader() {
    try {
      const token = window.localStorage?.getItem('recruitpro.token');
      const tokenType = window.localStorage?.getItem('recruitpro.tokenType') || 'Bearer';
      return token ? `${tokenType} ${token}` : '';
    } catch (error) {
      return '';
    }
  }
}

// Create global instance
window.RecruitPro = window.RecruitPro || {};
window.RecruitPro.api = new APIClient();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { APIClient };
}
