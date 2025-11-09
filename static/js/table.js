/**
 * Enhanced table component with sorting, filtering, and pagination
 */

class DataTable {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container element not found: ${containerId}`);
    }

    this.options = {
      data: [],
      columns: [],
      pageSize: 20,
      searchable: true,
      sortable: true,
      paginated: true,
      emptyMessage: 'No data available',
      loadingMessage: 'Loading...',
      onRowClick: null,
      rowClass: null,
      ...options,
    };

    this.state = {
      data: [],
      filteredData: [],
      currentPage: 1,
      sortColumn: null,
      sortDirection: 'asc',
      searchTerm: '',
      loading: false,
    };

    this.manager = new window.RecruitPro.ComponentManager();
    this.render();
  }

  /**
   * Set table data
   */
  setData(data) {
    this.state.data = data || [];
    this.state.filteredData = [...this.state.data];
    this.state.currentPage = 1;
    this.applyFilters();
    this.renderTable();
  }

  /**
   * Set loading state
   */
  setLoading(loading) {
    this.state.loading = loading;
    this.renderTable();
  }

  /**
   * Apply search filter
   */
  applyFilters() {
    let filtered = [...this.state.data];

    // Apply search
    if (this.state.searchTerm) {
      const term = this.state.searchTerm.toLowerCase();
      filtered = filtered.filter(row => {
        return this.options.columns.some(col => {
          const value = col.field ? row[col.field] : '';
          return String(value).toLowerCase().includes(term);
        });
      });
    }

    // Apply sort
    if (this.state.sortColumn) {
      filtered.sort((a, b) => {
        const aVal = a[this.state.sortColumn];
        const bVal = b[this.state.sortColumn];

        if (aVal == null) return 1;
        if (bVal == null) return -1;

        let comparison = 0;
        if (typeof aVal === 'number' && typeof bVal === 'number') {
          comparison = aVal - bVal;
        } else {
          comparison = String(aVal).localeCompare(String(bVal));
        }

        return this.state.sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    this.state.filteredData = filtered;
  }

  /**
   * Handle search input
   */
  handleSearch(term) {
    this.state.searchTerm = term;
    this.state.currentPage = 1;
    this.applyFilters();
    this.renderTable();
  }

  /**
   * Handle column sort
   */
  handleSort(columnField) {
    if (this.state.sortColumn === columnField) {
      this.state.sortDirection = this.state.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.state.sortColumn = columnField;
      this.state.sortDirection = 'asc';
    }
    this.applyFilters();
    this.renderTable();
  }

  /**
   * Go to specific page
   */
  gotoPage(page) {
    const totalPages = Math.ceil(this.state.filteredData.length / this.options.pageSize);
    if (page < 1 || page > totalPages) return;
    this.state.currentPage = page;
    this.renderTable();
  }

  /**
   * Get paginated data
   */
  getPaginatedData() {
    if (!this.options.paginated) {
      return this.state.filteredData;
    }

    const start = (this.state.currentPage - 1) * this.options.pageSize;
    const end = start + this.options.pageSize;
    return this.state.filteredData.slice(start, end);
  }

  /**
   * Render the entire table structure
   */
  render() {
    this.container.innerHTML = `
      <div class="rp-table-container">
        ${this.options.searchable ? `
          <div class="mb-4 flex gap-2 items-center">
            <input
              type="search"
              class="rp-input flex-1"
              placeholder="Search..."
              id="${this.container.id}-search"
            >
          </div>
        ` : ''}

        <div class="rp-surface overflow-x-auto">
          <table class="rp-table" id="${this.container.id}-table">
            <thead></thead>
            <tbody></tbody>
          </table>
        </div>

        ${this.options.paginated ? `
          <div class="mt-4 flex items-center justify-between">
            <div class="text-sm text-text-secondary" id="${this.container.id}-info"></div>
            <div class="flex gap-2" id="${this.container.id}-pagination"></div>
          </div>
        ` : ''}
      </div>
    `;

    // Add event listeners
    if (this.options.searchable) {
      const searchInput = document.getElementById(`${this.container.id}-search`);
      const debouncedSearch = window.RecruitPro.debounce((e) => {
        this.handleSearch(e.target.value);
      }, 300);
      this.manager.addEventListener(searchInput, 'input', debouncedSearch);
    }

    this.renderTable();
  }

  /**
   * Render table content
   */
  renderTable() {
    const table = document.getElementById(`${this.container.id}-table`);
    if (!table) return;

    const thead = table.querySelector('thead');
    const tbody = table.querySelector('tbody');

    // Render header
    thead.innerHTML = `
      <tr>
        ${this.options.columns.map(col => `
          <th
            class="${this.options.sortable && col.sortable !== false ? 'cursor-pointer hover:bg-surface-elevated' : ''}"
            ${this.options.sortable && col.sortable !== false ? `data-field="${col.field}"` : ''}
          >
            <div class="flex items-center gap-2">
              ${col.label}
              ${this.options.sortable && col.sortable !== false ? `
                <span class="material-symbols-outlined text-sm">
                  ${this.state.sortColumn === col.field
                    ? (this.state.sortDirection === 'asc' ? 'arrow_upward' : 'arrow_downward')
                    : 'unfold_more'}
                </span>
              ` : ''}
            </div>
          </th>
        `).join('')}
      </tr>
    `;

    // Add sort listeners
    if (this.options.sortable) {
      thead.querySelectorAll('th[data-field]').forEach(th => {
        this.manager.addEventListener(th, 'click', () => {
          this.handleSort(th.dataset.field);
        });
      });
    }

    // Render body
    if (this.state.loading) {
      tbody.innerHTML = `
        <tr>
          <td colspan="${this.options.columns.length}" class="text-center py-8 text-text-secondary">
            <div class="flex items-center justify-center gap-2">
              <span class="rp-spinner"></span>
              ${this.options.loadingMessage}
            </div>
          </td>
        </tr>
      `;
      return;
    }

    const pageData = this.getPaginatedData();

    if (pageData.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="${this.options.columns.length}" class="text-center py-8 text-text-secondary">
            ${this.options.emptyMessage}
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = pageData.map((row, index) => {
      const rowClass = this.options.rowClass ? this.options.rowClass(row) : '';
      return `
        <tr
          class="${rowClass} ${this.options.onRowClick ? 'cursor-pointer' : ''}"
          data-index="${index}"
          tabindex="${this.options.onRowClick ? '0' : '-1'}"
        >
          ${this.options.columns.map(col => {
            let value = col.field ? row[col.field] : '';
            if (col.render) {
              value = col.render(value, row);
            } else if (value == null) {
              value = '-';
            }
            return `<td>${value}</td>`;
          }).join('')}
        </tr>
      `;
    }).join('');

    // Add row click listeners
    if (this.options.onRowClick) {
      tbody.querySelectorAll('tr[data-index]').forEach(tr => {
        const index = parseInt(tr.dataset.index);
        const row = pageData[index];

        this.manager.addEventListener(tr, 'click', () => {
          this.options.onRowClick(row);
        });

        this.manager.addEventListener(tr, 'keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.options.onRowClick(row);
          }
        });
      });
    }

    // Render pagination
    if (this.options.paginated) {
      this.renderPagination();
    }
  }

  /**
   * Render pagination controls
   */
  renderPagination() {
    const totalItems = this.state.filteredData.length;
    const totalPages = Math.ceil(totalItems / this.options.pageSize);
    const currentPage = this.state.currentPage;

    const infoEl = document.getElementById(`${this.container.id}-info`);
    const paginationEl = document.getElementById(`${this.container.id}-pagination`);

    if (!infoEl || !paginationEl) return;

    // Render info
    const start = (currentPage - 1) * this.options.pageSize + 1;
    const end = Math.min(currentPage * this.options.pageSize, totalItems);
    infoEl.textContent = `Showing ${start}-${end} of ${totalItems}`;

    // Render pagination buttons
    const pages = [];

    // Previous button
    pages.push(`
      <button
        class="rp-button-secondary"
        ${currentPage === 1 ? 'disabled' : ''}
        data-page="${currentPage - 1}"
        aria-label="Previous page"
      >
        <span class="material-symbols-outlined">chevron_left</span>
      </button>
    `);

    // Page numbers
    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);

    if (endPage - startPage < maxButtons - 1) {
      startPage = Math.max(1, endPage - maxButtons + 1);
    }

    if (startPage > 1) {
      pages.push(`
        <button class="rp-button-secondary" data-page="1">1</button>
      `);
      if (startPage > 2) {
        pages.push('<span class="px-2 text-text-secondary">...</span>');
      }
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(`
        <button
          class="${i === currentPage ? 'rp-button-primary' : 'rp-button-secondary'}"
          data-page="${i}"
        >
          ${i}
        </button>
      `);
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pages.push('<span class="px-2 text-text-secondary">...</span>');
      }
      pages.push(`
        <button class="rp-button-secondary" data-page="${totalPages}">${totalPages}</button>
      `);
    }

    // Next button
    pages.push(`
      <button
        class="rp-button-secondary"
        ${currentPage === totalPages ? 'disabled' : ''}
        data-page="${currentPage + 1}"
        aria-label="Next page"
      >
        <span class="material-symbols-outlined">chevron_right</span>
      </button>
    `);

    paginationEl.innerHTML = pages.join('');

    // Add click listeners
    paginationEl.querySelectorAll('button[data-page]').forEach(btn => {
      this.manager.addEventListener(btn, 'click', () => {
        const page = parseInt(btn.dataset.page);
        this.gotoPage(page);
      });
    });
  }

  /**
   * Clean up event listeners
   */
  destroy() {
    this.manager.cleanup();
  }
}

// Add to global namespace
window.RecruitPro = window.RecruitPro || {};
window.RecruitPro.DataTable = DataTable;

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { DataTable };
}
