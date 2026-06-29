import axios from "axios";

// Base URL of the FastAPI backend. Configurable via Vite env (frontend/.env).
// Defaults to the backend's real port (8000) and MUST include the /api prefix.
const baseURL = (
  import.meta.env.VITE_API_URL || "http://localhost:8000/api"
).replace(/\/+$/, "");

const api = axios.create({ baseURL });

// Attach the JWT (when present) from localStorage on every request. Reading it
// per-request means auth survives full page reloads with no manual header
// bookkeeping, and logout takes effect as soon as the token is cleared.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
