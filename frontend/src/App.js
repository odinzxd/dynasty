import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import NewSale from "@/pages/NewSale";
import MySales from "@/pages/MySales";
import AdminPanel from "@/pages/AdminPanel";
import Corporate from "@/pages/Corporate";
import ActivityLog from "@/pages/ActivityLog";
import Employees from "@/pages/Employees";
import Accounting from "@/pages/Accounting";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import Stats from "@/pages/Stats";

function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/sales/new" element={<NewSale />} />
        <Route path="/sales" element={<MySales />} />
        <Route path="/admin" element={<ProtectedRoute adminOnly><AdminPanel /></ProtectedRoute>} />
        <Route path="/corporate" element={<ProtectedRoute><Corporate /></ProtectedRoute>} />
        <Route path="/admin/employees" element={<ProtectedRoute adminOnly><Employees /></ProtectedRoute>} />
        <Route path="/admin/activity" element={<ProtectedRoute adminOnly><ActivityLog /></ProtectedRoute>} />
        <Route path="/admin/accounting" element={<ProtectedRoute adminOnly><Accounting /></ProtectedRoute>} />
        <Route path="/admin/stats" element={<ProtectedRoute adminOnly><Stats /></ProtectedRoute>} />
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
