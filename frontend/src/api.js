import axios from 'axios';

const API_BASE = '/api';

class API {
  constructor() {
    this.token = localStorage.getItem('token');
    this.client = axios.create({ baseURL: API_BASE });

    // Always inject token at request time so it stays in sync
    this.client.interceptors.request.use(config => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('token');
  }

  async login(username, password) {
    const response = await this.client.post('/auth/login', null, {
      params: { username, password }
    });
    this.setToken(response.data.access_token);
    return response.data;
  }

  async getStatus() {
    const response = await this.client.get('/dashboard/status');
    return response.data;
  }

  async getTrades(limit = 50, offset = 0) {
    const response = await this.client.get('/dashboard/trades', {
      params: { limit, offset }
    });
    return response.data;
  }

  async getPerformance(period = '30d') {
    const response = await this.client.get('/dashboard/performance', {
      params: { period }
    });
    return response.data;
  }

  async getLogs(level = null, limit = 100) {
    const response = await this.client.get('/dashboard/logs', {
      params: { level, limit }
    });
    return response.data;
  }

  async testRun() {
    const response = await this.client.post('/trading/test-run');
    return response.data;
  }

  async killSwitch() {
    const response = await this.client.post('/trading/kill-switch');
    return response.data;
  }

  async pauseTrading() {
    const response = await this.client.post('/trading/pause');
    return response.data;
  }

  async resumeTrading() {
    const response = await this.client.post('/trading/resume');
    return response.data;
  }

  async getScreenerResults() {
    const response = await this.client.get('/screener/latest');
    return response.data;
  }
}

export default new API();
