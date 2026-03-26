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

    // Auth
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

    // Payment Links
    async getPaymentLinks(page = 1, status = '') {
        const params = new URLSearchParams({ page, per_page: 20 });
        if (status) params.set('status', status);
        return this.request('GET', `/payments?${params}`);
    }

    async createPaymentLink(data) {
        return this.request('POST', '/payments', data);
    }

    async getPaymentLink(id) {
        return this.request('GET', `/payments/${id}`);
    }

    async updatePaymentLink(id, data) {
        return this.request('PUT', `/payments/${id}`, data);
    }

    async deletePaymentLink(id) {
        return this.request('DELETE', `/payments/${id}`);
    }

    // Public payment link
    async getPublicPaymentLink(slug) {
        return this.request('GET', `/payments/public/${slug}`);
    }

    async submitPayment(slug, data) {
        return this.request('POST', `/payments/public/${slug}/submit`, data);
    }

    // QR Wallets
    async getQrWallets() {
        return this.request('GET', '/qr-wallets');
    }

    async createQrWallet(formData) {
        return this.request('POST', '/qr-wallets', formData, true);
    }

    async updateQrWallet(id, formData) {
        return this.request('PUT', `/qr-wallets/${id}`, formData, true);
    }

    async deleteQrWallet(id) {
        return this.request('DELETE', `/qr-wallets/${id}`);
    }

    // Transactions
    async getTransactions(page = 1, status = '', linkId = null) {
        const params = new URLSearchParams({ page, per_page: 20 });
        if (status) params.set('status', status);
        if (linkId) params.set('link_id', linkId);
        return this.request('GET', `/transactions?${params}`);
    }

    async approveTransaction(id, note = '') {
        return this.request('POST', `/transactions/${id}/approve`, { note });
    }

    async rejectTransaction(id, note = '') {
        return this.request('POST', `/transactions/${id}/reject`, { note });
    }

    // Stats
    async getStats() {
        return this.request('GET', '/payments/stats');
    }

    // Uploads
    async uploadProof(transactionId, file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('POST', `/uploads/proof/${transactionId}`, formData, true);
    }
}

// Global instance
const api = new ApiClient();
