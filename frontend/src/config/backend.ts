export const BACKEND_CONFIG = {
  WS_URL: import.meta.env.VITE_BACKEND_WS_URL || 'ws://localhost:8000/ws',
  API_URL: import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000',
} as const;