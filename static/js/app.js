/**
 * Workline App JavaScript
 * CSRF protection, Kanban drag & drop, modal toggles, and interactivity.
 */

// Retrieve CSRF token from cookies
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Toast notification helper
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const bgClass = type === 'success' ? 'bg-emerald-600 text-white' : (type === 'error' ? 'bg-red-600 text-white' : 'bg-slate-800 text-white');
  toast.className = `${bgClass} px-4 py-2.5 rounded-lg shadow-lg text-sm font-medium flex items-center justify-between gap-3 transform transition-all duration-300 translate-y-2 opacity-0 z-50`;
  toast.innerHTML = `
    <span>${message}</span>
    <button onclick="this.parentElement.remove()" class="text-white opacity-70 hover:opacity-100">&times;</button>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal control helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
    if (firstInput) firstInput.focus();
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

// Kanban Board Drag and Drop Setup
document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.kanban-card');
  const cols = document.querySelectorAll('.kanban-col');

  cards.forEach(card => {
    card.addEventListener('dragstart', (e) => {
      card.classList.add('dragging');
      e.dataTransfer.setData('text/plain', card.dataset.taskId);
      e.dataTransfer.effectAllowed = 'move';
    });

    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
    });
  });

  cols.forEach(col => {
    col.addEventListener('dragover', (e) => {
      e.preventDefault();
      col.classList.add('drag-over');
      e.dataTransfer.dropEffect = 'move';
    });

    col.addEventListener('dragleave', () => {
      col.classList.remove('drag-over');
    });

    col.addEventListener('drop', async (e) => {
      e.preventDefault();
      col.classList.remove('drag-over');
      const taskId = e.dataTransfer.getData('text/plain');
      const newStatus = col.dataset.status;

      const card = document.querySelector(`.kanban-card[data-task-id="${taskId}"]`);
      if (!card) return;

      const oldCol = card.closest('.kanban-col');
      const oldStatus = oldCol ? oldCol.dataset.status : null;

      if (oldStatus === newStatus) return;

      // Optimistic move
      col.querySelector('.kanban-cards-container').appendChild(card);
      updateColumnCounts();

      try {
        const response = await fetch(`/tasks/api/${taskId}/status/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({ status: newStatus })
        });

        const data = await response.json();
        if (data.success) {
          showToast(`Task ${data.identifier} moved to ${data.status_display}`);
        } else {
          // Revert move
          if (oldCol) oldCol.querySelector('.kanban-cards-container').appendChild(card);
          updateColumnCounts();
          showToast(data.error || 'Permission denied or update failed.', 'error');
        }
      } catch (err) {
        if (oldCol) oldCol.querySelector('.kanban-cards-container').appendChild(card);
        updateColumnCounts();
        showToast('Network error while updating task status.', 'error');
      }
    });
  });

  function updateColumnCounts() {
    cols.forEach(col => {
      const countEl = col.querySelector('.col-task-count');
      const cardsInCol = col.querySelectorAll('.kanban-card').length;
      if (countEl) countEl.textContent = cardsInCol;
    });
  }

  // Instant Navigation Progress Bar
  const progressBar = document.createElement('div');
  progressBar.id = 'page-progress-bar';
  progressBar.style.cssText = 'position:fixed;top:0;left:0;height:3px;width:0%;background:#6366f1;z-index:99999;transition:width 0.2s ease, opacity 0.3s ease;pointer-events:none;';
  document.body.appendChild(progressBar);

  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (link && link.href && !link.target && !link.hasAttribute('download')) {
      try {
        const url = new URL(link.href, window.location.origin);
        if (url.origin === window.location.origin && !url.pathname.startsWith('/static/') && !url.hash && url.href !== window.location.href) {
          progressBar.style.opacity = '1';
          progressBar.style.width = '70%';
        }
      } catch (err) {}
    }
  });

  document.addEventListener('submit', (e) => {
    const form = e.target;
    if (form && !form.target && form.method && form.method.toUpperCase() === 'POST') {
      const btn = form.querySelector('button[type="submit"]');
      if (btn && !btn.disabled) {
        btn.dataset.originalText = btn.innerHTML;
        btn.disabled = true;
        btn.style.opacity = '0.75';
        btn.innerHTML = `<span class="inline-flex items-center gap-1.5"><svg class="animate-spin h-3.5 w-3.5 inline" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>Saving...</span>`;
      }
      progressBar.style.opacity = '1';
      progressBar.style.width = '80%';
    }
  });

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    // If typing in input or textarea, don't trigger shortcuts
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach(m => closeModal(m.id));
      }
      return;
    }

    if (e.key === 'c' || e.key === 'n') {
      e.preventDefault();
      openModal('quick-create-modal');
    } else if (e.key === '/') {
      e.preventDefault();
      const searchInput = document.getElementById('global-search-input');
      if (searchInput) searchInput.focus();
    } else if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach(m => closeModal(m.id));
    }
  });
});
