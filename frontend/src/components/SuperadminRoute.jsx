import React from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

// Platform-admin only. Without this, anyone typing /admin loads a page whose
// every request 403s (it fetches tenants, plans and upgrade requests on mount),
// which just looks broken. The backend still enforces access via
// require_superadmin — this only keeps the UI honest.
export default function SuperadminRoute({ children }) {
  const { user } = useAuthStore();

  if (!user?.is_superadmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
