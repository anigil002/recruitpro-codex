/**
 * Utility functions for DOM manipulation and event management
 */

/**
 * Component manager for handling event listeners with automatic cleanup
 */
class ComponentManager {
  constructor() {
    this.listeners = [];
    this.intervals = [];
    this.timeouts = [];
  }

  /**
   * Add event listener with automatic cleanup tracking
   */
  addEventListener(element, event, handler, options) {
    element.addEventListener(event, handler, options);
    this.listeners.push({ element, event, handler, options });
  }

  /**
   * Set interval with automatic cleanup tracking
   */
  setInterval(callback, delay) {
    const id = setInterval(callback, delay);
    this.intervals.push(id);
    return id;
  }

  /**
   * Set timeout with automatic cleanup tracking
   */
  setTimeout(callback, delay) {
    const id = setTimeout(callback, delay);
    this.timeouts.push(id);
    return id;
  }

  /**
   * Clean up all tracked listeners, intervals, and timeouts
   */
  cleanup() {
    // Remove event listeners
    this.listeners.forEach(({ element, event, handler, options }) => {
      element.removeEventListener(event, handler, options);
    });
    this.listeners = [];

    // Clear intervals
    this.intervals.forEach(id => clearInterval(id));
    this.intervals = [];

    // Clear timeouts
    this.timeouts.forEach(id => clearTimeout(id));
    this.timeouts = [];
  }
}

/**
 * Create element from HTML string
 */
function createElement(html) {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  return template.content.firstChild;
}

/**
 * Create multiple elements from HTML string
 */
function createElements(html) {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  return Array.from(template.content.children);
}

/**
 * Debounce function calls
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function calls
 */
function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  if (typeof text !== 'string') return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Format date/time
 */
function formatDateTime(dateString, options = {}) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  };
  return date.toLocaleString(undefined, { ...defaultOptions, ...options });
}

/**
 * Format date only
 */
function formatDate(dateString, options = {}) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  };
  return date.toLocaleDateString(undefined, { ...defaultOptions, ...options });
}

/**
 * Format time only
 */
function formatTime(dateString, options = {}) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const defaultOptions = {
    hour: '2-digit',
    minute: '2-digit',
  };
  return date.toLocaleTimeString(undefined, { ...defaultOptions, ...options });
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
  return formatDate(dateString);
}

/**
 * Format number with commas
 */
function formatNumber(num) {
  if (typeof num !== 'number') return num;
  return num.toLocaleString();
}

/**
 * Format currency
 */
function formatCurrency(amount, currency = 'USD') {
  if (typeof amount !== 'number') return amount;
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
  }).format(amount);
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength = 100) {
  if (typeof text !== 'string') return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

/**
 * Get query parameter from URL
 */
function getQueryParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

/**
 * Set query parameter in URL without reload
 */
function setQueryParam(name, value) {
  const url = new URL(window.location);
  url.searchParams.set(name, value);
  window.history.pushState({}, '', url);
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (error) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    const success = document.execCommand('copy');
    document.body.removeChild(textarea);
    return success;
  }
}

/**
 * Download data as file
 */
function downloadFile(data, filename, mimeType = 'text/plain') {
  const blob = new Blob([data], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

/**
 * Smooth scroll to element
 */
function scrollToElement(element, options = {}) {
  const defaultOptions = {
    behavior: 'smooth',
    block: 'start',
    inline: 'nearest',
  };
  element.scrollIntoView({ ...defaultOptions, ...options });
}

// Add to global namespace
window.RecruitPro = window.RecruitPro || {};
Object.assign(window.RecruitPro, {
  ComponentManager,
  createElement,
  createElements,
  debounce,
  throttle,
  escapeHtml,
  formatDateTime,
  formatDate,
  formatTime,
  formatRelativeTime,
  formatNumber,
  formatCurrency,
  truncate,
  getQueryParam,
  setQueryParam,
  copyToClipboard,
  downloadFile,
  isInViewport,
  scrollToElement,
});

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    ComponentManager,
    createElement,
    createElements,
    debounce,
    throttle,
    escapeHtml,
    formatDateTime,
    formatDate,
    formatTime,
    formatRelativeTime,
    formatNumber,
    formatCurrency,
    truncate,
    getQueryParam,
    setQueryParam,
    copyToClipboard,
    downloadFile,
    isInViewport,
    scrollToElement,
  };
}
