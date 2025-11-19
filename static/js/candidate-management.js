/**
 * Candidate Management Module
 * Handles candidate pipeline, filtering, and bulk actions
 */

import { api } from './api.js';

class CandidateManagement {
  constructor() {
    this.candidates = [];
    this.filteredCandidates = [];
    this.selectedCandidates = new Set();
    this.filters = {
      aiScore: null,
      location: null,
      source: null,
      tags: null,
    };
  }

  async init() {
    await this.loadCandidates();
    this.setupEventListeners();
    this.render();
  }

  async loadCandidates() {
    try {
      const response = await api.get('/api/candidates');
      this.candidates = response;
      this.applyFilters();
    } catch (error) {
      console.error('Failed to load candidates:', error);
      this.candidates = [];
      this.filteredCandidates = [];
    }
  }

  setupEventListeners() {
    // Select all checkbox
    const selectAllCheckbox = document.querySelector('#candidate-management input[type="checkbox"]');
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
          this.filteredCandidates.forEach(c => this.selectedCandidates.add(c.candidate_id));
        } else {
          this.selectedCandidates.clear();
        }
        this.updateSelectedCount();
      });
    }

    // Bulk action apply button
    const applyButton = document.querySelector('#candidate-management .rounded-full.bg-primary\\/10');
    const actionSelect = document.querySelector('#candidate-management select');
    if (applyButton && actionSelect) {
      applyButton.addEventListener('click', async () => {
        const action = actionSelect.value;
        await this.handleBulkAction(action);
      });
    }

    // Filter selects
    const filterContainer = document.querySelector('#candidate-management .mt-4.grid.gap-3');
    if (filterContainer) {
      const selects = filterContainer.querySelectorAll('select');
      selects.forEach((select, index) => {
        select.addEventListener('change', (e) => {
          const filterType = ['aiScore', 'location', 'source', 'tags'][index];
          this.filters[filterType] = e.target.value || null;
          this.applyFilters();
          this.render();
        });
      });
    }
  }

  applyFilters() {
    this.filteredCandidates = this.candidates.filter(candidate => {
      // AI Score filter
      if (this.filters.aiScore) {
        const minScore = parseInt(this.filters.aiScore.replace('+', '')) / 100;
        const candidateScore = typeof candidate.ai_score === 'number'
          ? candidate.ai_score
          : (typeof candidate.ai_score === 'object' && candidate.ai_score !== null ? 0 : 0);
        if (candidateScore < minScore) return false;
      }

      // Location filter (from tags or would need to be in candidate data)
      if (this.filters.location) {
        const hasLocationTag = candidate.tags?.some(tag =>
          tag.toLowerCase().includes(this.filters.location.toLowerCase())
        );
        if (!hasLocationTag) return false;
      }

      // Source filter
      if (this.filters.source) {
        if (candidate.source !== this.filters.source) return false;
      }

      // Tags filter
      if (this.filters.tags) {
        const hasTag = candidate.tags?.some(tag =>
          tag.toLowerCase().includes(this.filters.tags.toLowerCase())
        );
        if (!hasTag) return false;
      }

      return true;
    });
  }

  groupCandidatesByStatus() {
    const groups = {
      new: [],
      screening: [],
      interview: [],
      offer: [],
    };

    this.filteredCandidates.forEach(candidate => {
      const status = candidate.status.toLowerCase();
      if (status === 'new') {
        groups.new.push(candidate);
      } else if (status === 'screening') {
        groups.screening.push(candidate);
      } else if (status === 'interview' || status === 'interviewing') {
        groups.interview.push(candidate);
      } else if (status === 'offer' || status === 'hired') {
        groups.offer.push(candidate);
      }
    });

    return groups;
  }

  render() {
    this.renderStatusCards();
    this.renderPipelineBoard();
  }

  renderStatusCards() {
    const groups = this.groupCandidatesByStatus();

    const cards = document.querySelectorAll('#candidate-management-ai-screening .grid.gap-6.lg\\:grid-cols-4 > div');
    if (cards.length >= 4) {
      // New candidates
      const newCount = groups.new.length;
      cards[0].querySelector('.text-2xl').textContent = newCount || '—';
      cards[0].querySelector('.text-xs.text-slate-400').textContent =
        newCount > 0 ? `${newCount} candidate${newCount !== 1 ? 's' : ''} awaiting screening` : 'Awaiting incoming candidates.';

      // Screening candidates
      const screeningCount = groups.screening.length;
      cards[1].querySelector('.text-2xl').textContent = screeningCount || '—';
      cards[1].querySelector('.text-xs.text-slate-400').textContent =
        screeningCount > 0 ? `${screeningCount} candidate${screeningCount !== 1 ? 's' : ''} in screening` : 'No screening data yet.';

      // Interview candidates
      const interviewCount = groups.interview.length;
      cards[2].querySelector('.text-2xl').textContent = interviewCount || '—';
      cards[2].querySelector('.text-xs.text-slate-400').textContent =
        interviewCount > 0 ? `${interviewCount} interview${interviewCount !== 1 ? 's' : ''} scheduled` : 'Interviews pending.';

      // Offer/Hired candidates
      const offerCount = groups.offer.length;
      cards[3].querySelector('.text-2xl').textContent = offerCount || '—';
      cards[3].querySelector('.text-xs.text-slate-400').textContent =
        offerCount > 0 ? `${offerCount} offer${offerCount !== 1 ? 's' : ''}/hire${offerCount !== 1 ? 's' : ''}` : 'No offers recorded.';
    }
  }

  renderPipelineBoard() {
    const groups = this.groupCandidatesByStatus();
    const pipelineColumns = document.querySelectorAll('#candidate-management-ai-screening .grid.gap-4.lg\\:grid-cols-4 > div');

    if (pipelineColumns.length >= 4) {
      this.renderPipelineColumn(pipelineColumns[0], groups.new, 'New');
      this.renderPipelineColumn(pipelineColumns[1], groups.screening, 'Screening');
      this.renderPipelineColumn(pipelineColumns[2], groups.interview, 'Interview');
      this.renderPipelineColumn(pipelineColumns[3], groups.offer, 'Offer');
    }
  }

  renderPipelineColumn(column, candidates, stageName) {
    const list = column.querySelector('ul');
    if (!list) return;

    if (candidates.length === 0) {
      list.innerHTML = '<li class="rounded-xl border border-dashed border-slate-800/60 bg-slate-950/80 p-3 text-center">No candidates in this stage.</li>';
      return;
    }

    list.innerHTML = candidates.map(candidate => {
      const aiScore = typeof candidate.ai_score === 'number'
        ? Math.round(candidate.ai_score * 100)
        : 0;
      const isSelected = this.selectedCandidates.has(candidate.candidate_id);

      return `
        <li class="rounded-xl border border-slate-700/60 bg-slate-900/80 p-3 hover:border-primary/40 hover:bg-slate-900/90 transition cursor-pointer ${isSelected ? 'ring-2 ring-primary/40' : ''}"
            data-candidate-id="${candidate.candidate_id}">
          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-white text-sm truncate">${this.escapeHtml(candidate.name)}</p>
              ${candidate.email ? `<p class="text-xs text-slate-400 truncate">${this.escapeHtml(candidate.email)}</p>` : ''}
              ${aiScore > 0 ? `<p class="text-xs text-primary mt-1">AI Score: ${aiScore}%</p>` : ''}
            </div>
            <input type="checkbox" ${isSelected ? 'checked' : ''}
                   class="candidate-checkbox rounded border-slate-700 bg-slate-950/80"
                   data-candidate-id="${candidate.candidate_id}">
          </div>
        </li>
      `;
    }).join('');

    // Add click handlers
    list.querySelectorAll('li').forEach(li => {
      const candidateId = li.dataset.candidateId;
      const checkbox = li.querySelector('.candidate-checkbox');

      li.addEventListener('click', (e) => {
        if (e.target.tagName !== 'INPUT') {
          window.location.href = `/candidate-profile?candidate_id=${candidateId}`;
        }
      });

      checkbox.addEventListener('click', (e) => {
        e.stopPropagation();
      });

      checkbox.addEventListener('change', (e) => {
        if (e.target.checked) {
          this.selectedCandidates.add(candidateId);
        } else {
          this.selectedCandidates.delete(candidateId);
        }
        this.updateSelectedCount();
        this.render();
      });
    });
  }

  updateSelectedCount() {
    const count = this.selectedCandidates.size;
    const label = document.querySelector('#candidate-management label');
    if (label) {
      const text = label.childNodes[0];
      if (text) {
        text.textContent = count > 0 ? `${count} selected` : 'Select all';
      }
    }
  }

  async handleBulkAction(action) {
    if (this.selectedCandidates.size === 0) {
      alert('Please select at least one candidate');
      return;
    }

    const candidateIds = Array.from(this.selectedCandidates);

    if (action === 'Move to Interview') {
      await this.moveToInterview(candidateIds);
    } else if (action === 'Add to Project') {
      alert('Add to Project feature coming soon');
    } else if (action === 'Send Outreach') {
      alert('Send Outreach feature coming soon');
    }
  }

  async moveToInterview(candidateIds) {
    try {
      // Update each candidate's status to interview
      for (const candidateId of candidateIds) {
        await api.patch(`/api/candidates/${candidateId}`, { status: 'interview' });
      }

      // Reload candidates
      await this.loadCandidates();
      this.selectedCandidates.clear();
      this.render();
      this.updateSelectedCount();

      alert(`Moved ${candidateIds.length} candidate${candidateIds.length !== 1 ? 's' : ''} to interview stage`);
    } catch (error) {
      console.error('Failed to move candidates:', error);
      alert('Failed to move candidates. Please try again.');
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize candidate management when the page loads
let candidateManagement;

document.addEventListener('DOMContentLoaded', () => {
  const candidateSection = document.getElementById('candidate-management');
  if (candidateSection) {
    candidateManagement = new CandidateManagement();
    candidateManagement.init();
  }
});

// Refresh candidates when returning to the candidate management tab
document.addEventListener('click', (e) => {
  if (e.target.id === 'candidate-management-tab-ai-screening' && candidateManagement) {
    candidateManagement.loadCandidates().then(() => candidateManagement.render());
  }
});

export { CandidateManagement };
