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
  generateSummary: (recordingId, customPrompt = null) => api.post('/summaries/generate', {
    recording_id: recordingId,
    custom_prompt: customPrompt,
  }),
  getSummary: (recordingId) => api.get(`/summaries/${recordingId}`),
  regenerateSummary: (summaryId, customPrompt = null) => {
    const url = `/summaries/${summaryId}/regenerate${customPrompt ? `?custom_prompt=${encodeURIComponent(customPrompt)}` : ''}`;
    return api.put(url);
  },

  // Admin endpoints
  healthCheck: () => api.get('/admin/health'),
  getStats: () => api.get('/admin/stats'),
};

export default api;
