import { create } from "zustand";
import api from "../lib/api";

export const useAuthStore = create((set) => ({
  token: localStorage.getItem("token") || null,
  user: JSON.parse(localStorage.getItem("user")) || null,
  isAuthenticated: !!localStorage.getItem("token"),
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const response = await api.post(`/auth/login`, { email, password });
      const { success, data, message } = response.data;
      
      if (success && data.access_token) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data));
        
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

  register: async (email, password, name, clinicName, did, industry) => {
    set({ loading: true, error: null });
    try {
      const response = await api.post(`/auth/register`, {
        email,
        password,
        name,
        clinic_name: clinicName,
        role: "doctor",
        did,
        industry
      });
      
      const { success, data, message } = response.data;
      if (success && data.access_token) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data));
        
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
    set({ token: null, user: null, isAuthenticated: false });
  }
}));
