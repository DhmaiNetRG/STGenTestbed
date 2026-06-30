import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API methods
export default {
  // Health
  health: () => api.get('/api/health'),
  
  // Protocols & Config
  getProtocols: () => api.get('/api/protocols'),
  getSensors: () => api.get('/api/sensors'),
  getNetworkProfiles: () => api.get('/api/network-profiles'),
  
  // Experiments
  listExperiments: () => api.get('/api/experiments'),
  createExperiment: (config) => api.post('/api/experiments', config),
  getExperiment: (id) => api.get(`/api/experiments/${id}`),
  startExperiment: (id) => api.post(`/api/experiments/${id}/start`),
  stopExperiment: (id) => api.post(`/api/experiments/${id}/stop`),
  deleteExperiment: (id) => api.delete(`/api/experiments/${id}`),
  
  // Results & Logs
  getExperimentLogs: (id, lines = 100) => api.get(`/api/experiments/${id}/logs?lines=${lines}`),
  getExperimentResults: (id) => api.get(`/api/experiments/${id}/results`),
  downloadResults: (id) => `${API_BASE}/api/experiments/${id}/download`,
  
  // System
  getSystemStats: () => api.get('/api/system/stats'),
  
  // WebSocket
  getWebSocketURL: (id) => `ws://localhost:8000/ws/${id}`,
};
