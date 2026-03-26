/* ═══════════════════════════════════════════════════
   Shared UI Utilities
   ═══════════════════════════════════════════════════ */

// ── Toast Notifications ──
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️',
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Modal Controls ──
function openModal(modalId) {
    const overlay = document.getElementById(modalId);
    if (overlay) {
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const overlay = document.getElementById(modalId);
    if (overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// ── Tab System ──
function initTabs(container) {
    const tabBtns = container.querySelectorAll('.tab-btn');
    const tabContents = container.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            const targetEl = document.getElementById(target);
            if (targetEl) targetEl.classList.add('active');
        });
    });
}

// ── Format Helpers ──
function formatCurrency(amount, currency = 'PHP') {
    if (amount === null || amount === undefined) return 'Any Amount';
    return `₱${parseFloat(amount).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleDateString('en-PH', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function formatDateShort(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleDateString('en-PH', { month: 'short', day: 'numeric' });
}

function timeAgo(isoString) {
    if (!isoString) return '';
    const now = new Date();
    const date = new Date(isoString);
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return formatDate(isoString);
}

function getStatusBadge(status) {
    return `<span class="badge badge-${status}">${status}</span>`;
}

function getWalletBadge(type) {
    return `<span class="badge badge-${type}">${type === 'maya' ? 'Maya' : 'GCash'}</span>`;
}

// ── Copy to Clipboard ──
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
    } catch {
        const input = document.createElement('input');
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        showToast('Copied!', 'success');
    }
}

// ── Skeleton Loaders ──
function showSkeleton(container, count = 3) {
    let html = '';
    for (let i = 0; i < count; i++) {
        html += `
            <div class="glass-card" style="margin-bottom:1rem">
                <div class="skeleton skeleton-text" style="width:70%"></div>
                <div class="skeleton skeleton-text" style="width:50%"></div>
                <div class="skeleton skeleton-text" style="width:40%"></div>
            </div>
        `;
    }
    container.innerHTML = html;
}

// ── Lightbox ──
function openLightbox(imageUrl) {
    const lb = document.createElement('div');
    lb.className = 'lightbox';
    lb.innerHTML = `<img src="${imageUrl}" alt="Proof">`;
    lb.addEventListener('click', () => lb.remove());
    document.body.appendChild(lb);
}

// ── Payment URL ──
function getPaymentUrl(slug) {
    return `${window.location.origin}/pay/${slug}`;
}

// ── Debounce ──
function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}
