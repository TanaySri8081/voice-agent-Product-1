import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Analytics from "./pages/Analytics";
import Agents from "./pages/Agents";
import Billing from "./pages/Billing";
import CallLogs from "./pages/CallLogs";
import Campaigns from "./pages/Campaigns";
import Contacts from "./pages/Contacts";
import Dashboard from "./pages/Dashboard";
import KnowledgeBase from "./pages/KnowledgeBase";
import LiveCalls from "./pages/LiveCalls";
import PhoneNumbers from "./pages/PhoneNumbers";
import Settings from "./pages/Settings";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Routes>
                <Route element={<AppLayout />}>
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/agents" element={<Agents />} />
                  <Route path="/campaigns" element={<Campaigns />} />
                  <Route path="/contacts" element={<Contacts />} />
                  <Route path="/calls/live" element={<LiveCalls />} />
                  <Route path="/call-logs" element={<CallLogs />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/knowledge-base" element={<KnowledgeBase />} />
                  <Route path="/phone-numbers" element={<PhoneNumbers />} />
                  <Route path="/billing" element={<Billing />} />
                  <Route path="/settings" element={<Settings />} />
                </Route>
              </Routes>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
