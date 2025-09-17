export const BACKEND_CONFIG = {
  WS_URL: import.meta.env.VITE_BACKEND_WS_URL || 'ws://localhost:8000/ws',
  API_URL: import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000',
  // Legacy support for Beam config
  BEAM_WS_URL: import.meta.env.VITE_BEAM_WS_URL,
  BEAM_TOKEN: import.meta.env.VITE_BEAM_TOKEN,
} as const;

// Backward compatibility
export const BEAM_CONFIG = {
  WS_URL: BACKEND_CONFIG.BEAM_WS_URL || BACKEND_CONFIG.WS_URL,
  TOKEN: BACKEND_CONFIG.BEAM_TOKEN,
} as const;