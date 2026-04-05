const API_BASE = '/api';

/**
 * Parse DRF error responses into readable messages.
 * Handles: {field: ["error"]}, {detail: "..."}, {error: "..."}, {non_field_errors: ["..."]}
 */
function parseApiError(data, statusCode) {
  if (!data || typeof data !== 'object') return `Request failed (${statusCode})`;

  // Our custom format: {error: "message"}
  if (data.error) return data.error;

  // DRF default: {detail: "message"}
  if (data.detail) return data.detail;

  // DRF field errors: {field_name: ["error1", "error2"], ...}
  const fieldErrors = [];
  for (const [key, value] of Object.entries(data)) {
    const field = key === 'non_field_errors' ? '' : key.replace(/_/g, ' ');
    const messages = Array.isArray(value) ? value.join(', ') : String(value);
    if (field) {
      fieldErrors.push(`${field}: ${messages}`);
    } else {
      fieldErrors.push(messages);
    }
  }

  return fieldErrors.length > 0 ? fieldErrors.join('\n') : `Request failed (${statusCode})`;
}

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('access_token');
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('access_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  async request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${path}`, opts);

    if (res.status === 401) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.token}`;
        const retry = await fetch(`${API_BASE}${path}`, { ...opts, headers });
        if (!retry.ok) {
          const err = await retry.json().catch(() => ({}));
          throw new Error(parseApiError(err, retry.status));
        }
        return retry.json();
      }
      this.clearToken();
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseApiError(err, res.status));
    }

    return res.json();
  }

  async uploadFile(path, formData) {
    const headers = {};
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (res.status === 401) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.token}`;
        const retry = await fetch(`${API_BASE}${path}`, { method: 'POST', headers, body: formData });
        if (!retry.ok) {
          const err = await retry.json().catch(() => ({}));
          throw new Error(parseApiError(err, retry.status));
        }
        return retry.json();
      }
      this.clearToken();
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(parseApiError(err, res.status));
    }

    return res.json();
  }

  async refreshToken() {
    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) return false;
    try {
      const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      });
      if (res.ok) {
        const data = await res.json();
        this.setToken(data.access);
        return true;
      }
    } catch {}
    return false;
  }

  // Auth
  login(username, password) { return this.request('POST', '/auth/login/', { username, password }); }
  logout() { return this.request('POST', '/auth/logout/'); }
  getMe() { return this.request('GET', '/auth/me/'); }

  // Dashboard
  getStats() { return this.request('GET', '/dashboard/stats/'); }

  // Tickets
  getTickets(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request('GET', `/tickets/${qs ? '?' + qs : ''}`);
  }
  getTicket(id) { return this.request('GET', `/tickets/${id}/`); }
  pickTicket(id) { return this.request('POST', `/tickets/${id}/pick/`); }
  transferTicket(id, toAgentId, reason = '') {
    return this.request('POST', `/tickets/${id}/transfer/`, { to_agent_id: toAgentId, reason });
  }
  changeTicketStatus(id, status) {
    return this.request('POST', `/tickets/${id}/change_status/`, { status });
  }

  // Messages
  getMessages(ticketId) { return this.request('GET', `/tickets/${ticketId}/messages/`); }
  sendMessage(ticketId, content, isInternal = false) {
    return this.request('POST', `/tickets/${ticketId}/messages/`, { content, is_internal_note: isInternal });
  }
  sendMedia(ticketId, file, caption = '', isInternal = false) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('caption', caption);
    formData.append('is_internal_note', isInternal ? 'true' : 'false');
    return this.uploadFile(`/tickets/${ticketId}/send-media/`, formData);
  }

  // Users / Agents
  getUsers(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request('GET', `/users/${qs ? '?' + qs : ''}`);
  }
  createUser(data) { return this.request('POST', '/users/', data); }
  updateUser(id, data) { return this.request('PATCH', `/users/${id}/`, data); }
  toggleUserActive(id) { return this.request('POST', `/users/${id}/toggle_active/`); }

  // Services
  getServices() { return this.request('GET', '/services/'); }
  createService(data) { return this.request('POST', '/services/', data); }
  updateService(id, data) { return this.request('PATCH', `/services/${id}/`, data); }

  // Companies
  getCompanies(serviceId = null) {
    const params = serviceId ? `?service=${serviceId}` : '';
    return this.request('GET', `/companies/${params}`);
  }
  createCompany(data) { return this.request('POST', '/companies/', data); }
  updateCompany(id, data) { return this.request('PATCH', `/companies/${id}/`, data); }

  // Bot Config
  getBots() { return this.request('GET', '/bots/'); }
  activateBot(id) { return this.request('POST', `/bots/${id}/activate/`); }
  healthCheckBot(id) { return this.request('POST', `/bots/${id}/health_check/`); }
}

export const api = new ApiClient();
export default api;