import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import Login from "@/pages/Login";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import NewSale from "@/pages/NewSale";
import MySales from "@/pages/MySales";
import AdminPanel from "@/pages/AdminPanel";
import ActivityLog from "@/pages/ActivityLog";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";

function AppRouter() {
  const location = useLocation();
  // Detect OAuth callback synchronously to avoid race conditions
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/sales/new" element={<NewSale />} />
        <Route path="/sales" element={<MySales />} />
        <Route path="/admin" element={<ProtectedRoute adminOnly><AdminPanel /></ProtectedRoute>} />
        <Route path="/admin/activity" element={<ProtectedRoute adminOnly><ActivityLog /></ProtectedRoute>} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster theme="dark" position="top-right" toastOptions={{
            style: { background: "#141414", border: "1px solid #262626", color: "#fff", borderRadius: 0 }
          }} />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
