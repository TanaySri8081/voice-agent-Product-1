import { create } from "zustand";
import axios from "axios";

const API_URL = "http://localhost:8002/api";

export const useAuthStore = create((set, get) => ({
  token: localStorage.getItem("token") || null,
  user: JSON.parse(localStorage.getItem("user")) || null,
  isAuthenticated: !!localStorage.getItem("token"),
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const response = await axios.post(`${API_URL}/auth/login`, { email, password });
      const { success, data, message } = response.data;
      
      if (success && data.access_token) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data));
        
        // Set Auth header for subsequent calls
        axios.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
        
        set({
          token: data.access_token,
          user: data,
          isAuthenticated: true,
          loading: false
        });
        return true;
      } else {
        set({ error: message || "Invalid credentials", loading: false });
        return false;
      }
    } catch (err) {
      let errMsg = "Login connection failed";
      const resData = err.response?.data;
      if (resData) {
        if (resData.detail) {
          if (Array.isArray(resData.detail)) {
            errMsg = resData.detail.map(d => `${d.loc[d.loc.length - 1]}: ${d.msg}`).join(", ");
          } else {
            errMsg = resData.detail;
          }
        } else if (resData.message) {
          errMsg = resData.message;
        } else if (resData.error) {
          errMsg = resData.error;
        }
      }
      set({ error: errMsg, loading: false });
      return false;
    }
  },

  register: async (email, password, name, clinicName, did) => {
    set({ loading: true, error: null });
    try {
      const response = await axios.post(`${API_URL}/auth/register`, {
        email,
        password,
        name,
        clinic_name: clinicName,
        role: "doctor",
        did
      });
      
      const { success, data, message } = response.data;
      if (success && data.access_token) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data));
        
        axios.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
        
        set({
          token: data.access_token,
          user: data,
          isAuthenticated: true,
          loading: false
        });
        return true;
      } else {
        set({ error: message || "Registration failed", loading: false });
        return false;
      }
    } catch (err) {
      let errMsg = "Registration connection failed";
      const resData = err.response?.data;
      if (resData) {
        if (resData.detail) {
          if (Array.isArray(resData.detail)) {
            errMsg = resData.detail.map(d => `${d.loc[d.loc.length - 1]}: ${d.msg}`).join(", ");
          } else {
            errMsg = resData.detail;
          }
        } else if (resData.message) {
          errMsg = resData.message;
        } else if (resData.error) {
          errMsg = resData.error;
        }
      }
      set({ error: errMsg, loading: false });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    delete axios.defaults.headers.common["Authorization"];
    set({ token: null, user: null, isAuthenticated: false });
  }
}));

// Initialize headers on reload if token exists
const initialToken = localStorage.getItem("token");
if (initialToken) {
  axios.defaults.headers.common["Authorization"] = `Bearer ${initialToken}`;
}
