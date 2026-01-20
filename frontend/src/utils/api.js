import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests if it exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// API endpoints
export const apiService = {
  // Auth endpoints
  register: (userData) => api.post('/auth/register', userData),
  login: (credentials) => api.post('/auth/login', credentials),
  getCurrentUser: () => api.get('/auth/me'),
  changePassword: (currentPassword, newPassword) => api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  }),
  sendVerificationCode: (email) => api.post('/auth/send-verification', { email }),
  verifyEmail: (email, code) => api.post('/auth/verify-email', { email, code }),
  resendVerificationCode: (email) => api.post('/auth/resend-verification', { email }),

  // Trial endpoints
  startTrial: (email) => api.post('/trials/start', { email }),
  getTrialUsage: () => api.get('/trials/usage'),
  convertTrial: (password) => api.post('/auth/convert-trial', { password }),

  // Recording endpoints
  uploadAudio: (formData) => api.post('/recordings/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  getRecording: (recordingId) => api.get(`/recordings/${recordingId}`),
  listRecordings: (page = 1, pageSize = 10) => api.get(`/recordings/?page=${page}&page_size=${pageSize}`),
  deleteRecording: (recordingId) => api.delete(`/recordings/${recordingId}`),
  downloadAudio: (recordingId) => api.get(`/recordings/${recordingId}/audio`, {
    responseType: 'blob',
  }),

  // Transcription endpoints
  createTranscription: (recordingId) => api.post('/transcriptions/create', { recording_id: recordingId }),
  getTranscription: (recordingId) => api.get(`/transcriptions/${recordingId}`),
  updateTranscription: (transcriptionId, text) => api.put(`/transcriptions/${transcriptionId}`, { text }),

  // Summary endpoints
  generateSummary: (recordingId, format = 'quick_summary', customPrompt = null) => api.post('/summaries/generate', {
    recording_id: recordingId,
    format: format,
    custom_prompt: customPrompt,
  }),
  getSummary: (recordingId) => api.get(`/summaries/${recordingId}`),
  regenerateSummary: (summaryId, customPrompt = null) => {
    const url = `/summaries/${summaryId}/regenerate${customPrompt ? `?custom_prompt=${encodeURIComponent(customPrompt)}` : ''}`;
    return api.put(url);
  },
  exportWord: (recordingId) => api.get(`/summaries/${recordingId}/export/word`, {
    responseType: 'blob',
  }),
  exportPdf: (recordingId) => api.get(`/summaries/${recordingId}/export/pdf`, {
    responseType: 'blob',
  }),

  // Admin endpoints
  healthCheck: () => api.get('/admin/health'),
  getStats: () => api.get('/admin/stats'),

  // Payment endpoints
  getPricingPlans: () => api.get('/payments/plans'),
  getSubscriptionDetails: () => api.get('/payments/subscription/details'),
  createCheckoutSession: (plan, interval = 'monthly') => api.post('/payments/create-checkout-session', null, {
    params: { plan, interval }
  }),
  verifySubscription: () => api.post('/payments/verify-subscription'),
  cancelSubscription: () => api.post('/payments/cancel-subscription'),
  changePlan: (newPlan) => api.post('/payments/change-plan', { new_plan: newPlan }),

  // User usage endpoints
  getUserUsage: () => api.get('/users/usage'),
  checkUsageStatus: () => api.get('/users/usage/check'),

  // Audio retention endpoints
  enableAudioRetention: (recordingId) => api.post(`/recordings/${recordingId}/retain`),
  deleteAudio: (recordingId) => api.delete(`/recordings/${recordingId}/audio`),
  getRetentionStatus: (recordingId) => api.get(`/recordings/${recordingId}/retention`),
};

export default api;
