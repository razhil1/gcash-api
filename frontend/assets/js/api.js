/* ═══════════════════════════════════════════════════
   API Client — Handles all backend communication
   ═══════════════════════════════════════════════════ */

const API_BASE = window.location.origin + '/api';

class ApiClient {
    constructor() {
        this.token = (localStorage.getItem('auth_token') || '').trim();
    }

    setToken(token) {
        this.token = token.trim();
        localStorage.setItem('auth_token', this.token);
    }

    clearToken() {
        this.token = '';
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
    }

    getUser() {
        try {
            return JSON.parse(localStorage.getItem('auth_user') || 'null');
        } catch {
            return null;
        }
    }

    setUser(user) {
        localStorage.setItem('auth_user', JSON.stringify(user));
    }

    isAuthenticated() {
        return !!this.token;
    }

    isAdmin() {
        const user = this.getUser();
        return user && user.role === 'admin';
    }

    async request(method, endpoint, data = null, isFormData = false) {
        const url = `${API_BASE}${endpoint}`;
        const headers = {};

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const options = { method, headers };

        if (data) {
            if (isFormData) {
                options.body = data;
            } else {
                headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(data);
            }
        }

        try {
            const response = await fetch(url, options);
            const result = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    this.clearToken();
                    if (!window.location.pathname.includes('/login') &&
                        !window.location.pathname.includes('/pay/')) {
                        window.location.href = '/login';
                    }
                }
                throw new Error(result.error || `Request failed (${response.status})`);
            }

            return result;
        } catch (error) {
            if (error.message.includes('Failed to fetch')) {
                throw new Error('Cannot connect to server. Please check if the backend is running.');
            }
            throw error;
        }
    }

    // ── Auth ──
    async login(email, password) {
        const result = await this.request('POST', '/auth/login', { email, password });
        this.setToken(result.token);
        this.setUser(result.user);
        return result;
    }

    async register(email, password, name) {
        const result = await this.request('POST', '/auth/register', { email, password, name });
        this.setToken(result.token);
        this.setUser(result.user);
        return result;
    }

    async getMe() {
        return this.request('GET', '/auth/me');
    }

    async changePassword(currentPassword, newPassword) {
        return this.request('POST', '/auth/change-password', {
            current_password: currentPassword,
            new_password: newPassword,
        });
    }

    // ── User Stats & Data ──
    async getStats() {
        return this.request('GET', '/user/stats');
    }

    async getTransactions(page = 1, status = '') {
        const params = new URLSearchParams({ page, per_page: 20 });
        if (status) params.set('status', status);
        return this.request('GET', `/user/transactions?${params}`);
    }

    async getPaymentLinks(page = 1, status = '') {
        const params = new URLSearchParams({ page, per_page: 20 });
        if (status) params.set('status', status);
        return this.request('GET', `/user/payment-links?${params}`);
    }

    async createPaymentLink(data) {
        return this.request('POST', '/user/payment-links', data);
    }

    async updatePaymentLink(id, data) {
        return this.request('PUT', `/user/payment-links/${id}`, data);
    }

    async deletePaymentLink(id) {
        return this.request('DELETE', `/user/payment-links/${id}`);
    }

    async getQrWallets() {
        return this.request('GET', '/user/wallets');
    }

    // ── QR Wallets ──
    async createQrWallet(formData) {
        return this.request('POST', '/qr-wallets', formData, true);
    }

    async updateQrWallet(id, formData) {
        return this.request('PUT', `/qr-wallets/${id}`, formData, true);
    }

    async deleteQrWallet(id) {
        return this.request('DELETE', `/qr-wallets/${id}`);
    }

    // ── Transactions (admin actions) ──
    async approveTransaction(id, note = '') {
        return this.request('POST', `/admin/transactions/${id}/review`, { action: 'approve', note });
    }

    async rejectTransaction(id, note = '') {
        return this.request('POST', `/admin/transactions/${id}/review`, { action: 'reject', note });
    }

    // ── Public Payment (no auth) ──
    async getPublicPaymentLink(slug) {
        return this.request('GET', `/payments/public/${slug}`);
    }

    async submitPayment(slug, data) {
        return this.request('POST', `/payments/public/${slug}/submit`, data);
    }

    // ── Uploads ──
    async uploadProof(transactionId, file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('POST', `/uploads/proof/${transactionId}`, formData, true);
    }

    // ── API Keys ──
    async listApiKeys() {
        return this.request('GET', '/keys');
    }

    async createApiKey(name) {
        return this.request('POST', '/keys', { name });
    }

    async revokeApiKey(id) {
        return this.request('DELETE', `/keys/${id}`);
    }

    async renameApiKey(id, name) {
        return this.request('PUT', `/keys/${id}/name`, { name });
    }

    // ── Admin ──
    async adminGetStats() {
        return this.request('GET', '/admin/stats');
    }

    async adminGetUsers(page = 1, search = '', role = '') {
        const params = new URLSearchParams({ page, per_page: 20 });
        if (search) params.set('q', search);
        if (role) params.set('role', role);
        return this.request('GET', `/admin/users?${params}`);
    }

    async adminToggleUser(id, isActive) {
        return this.request('POST', `/admin/users/${id}/toggle`, { is_active: isActive });
    }

    async adminUpdateRole(id, role) {
        return this.request('PUT', `/admin/users/${id}/role`, { role });
    }

    async adminGetTransactions(page = 1, status = '', search = '') {
        const params = new URLSearchParams({ page, per_page: 20 });
        if (status) params.set('status', status);
        if (search) params.set('q', search);
        return this.request('GET', `/admin/transactions?${params}`);
    }

    async adminReviewTransaction(id, action, note = '') {
        return this.request('POST', `/admin/transactions/${id}/review`, { action, note });
    }

    async adminGetRevenueChart(days = 7) {
        return this.request('GET', `/admin/revenue/chart?days=${days}`);
    }

    async adminGetPaymentLinks(page = 1, status = '', search = '') {
        const params = new URLSearchParams({ page, per_page: 20 });
        if (status) params.set('status', status);
        if (search) params.set('q', search);
        return this.request('GET', `/admin/payment-links?${params}`);
    }
}

// Global instance
const api = new ApiClient();
