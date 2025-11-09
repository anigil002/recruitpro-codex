/**
 * Lightweight reactive state management store
 * Usage:
 *   const store = new Store({ count: 0 });
 *   store.subscribe((state) => console.log('State updated:', state));
 *   store.setState({ count: 1 });
 */

class Store {
  constructor(initialState = {}) {
    this.state = initialState;
    this.listeners = [];
  }

  getState() {
    return { ...this.state };
  }

  setState(updates) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...updates };

    // Notify all listeners
    this.listeners.forEach(listener => {
      try {
        listener(this.state, prevState);
      } catch (error) {
        console.error('Store listener error:', error);
      }
    });
  }

  subscribe(listener) {
    if (typeof listener !== 'function') {
      throw new Error('Listener must be a function');
    }

    this.listeners.push(listener);

    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  reset(newState = {}) {
    this.state = newState;
    this.listeners.forEach(listener => listener(this.state, {}));
  }
}

// Create global stores
window.RecruitPro = window.RecruitPro || {};

// Project store
window.RecruitPro.projectStore = new Store({
  currentProject: null,
  documents: [],
  candidates: [],
  positions: [],
  loading: false,
  error: null,
});

// UI store
window.RecruitPro.uiStore = new Store({
  activeScreen: 'dashboard',
  sidebarCollapsed: false,
  modalsOpen: [],
  toastsQueue: [],
});

// User store
window.RecruitPro.userStore = new Store({
  user: null,
  token: null,
  authenticated: false,
});

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { Store };
}
