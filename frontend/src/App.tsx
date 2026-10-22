import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import { ToastProvider } from "./context/ToastContext";
import AIReview from "./pages/AIReview";
import AuditDetailPage from "./pages/AuditDetail";
import Compare from "./pages/Compare";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Login from "./pages/Login";
import NewAudit from "./pages/NewAudit";
import Rules from "./pages/Rules";
import Users from "./pages/Users";

function Protected() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner label="Restoring session…" />;
  return user ? <Layout /> : <Navigate to="/login" replace />;
}

function AdminOnly({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth();
  return isAdmin ? <>{children}</> : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route element={<Protected />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/audits/new" element={<NewAudit />} />
                <Route path="/audits" element={<History />} />
                <Route path="/audits/compare" element={<Compare />} />
                <Route path="/audits/:id" element={<AuditDetailPage />} />
                <Route path="/rules" element={<Rules />} />
                <Route path="/ai-review" element={<AIReview />} />
                <Route path="/users" element={<AdminOnly><Users /></AdminOnly>} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

