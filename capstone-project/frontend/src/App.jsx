import { useState } from "react";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { logout } from "./api.js";
import { useSession } from "./session.js";
import HomePage from "./pages/HomePage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import AdminLoginPage from "./pages/AdminLoginPage.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import AdminDashboardPage from "./pages/AdminDashboardPage.jsx";
import ApplicationListPage from "./pages/ApplicationListPage.jsx";
import ApplicationDetailPage from "./pages/ApplicationDetailPage.jsx";
import AssessmentPage from "./pages/AssessmentPage.jsx";
import AboutPage from "./pages/AboutPage.jsx";

const GUEST_LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/login", label: "Applicant login" },
  { to: "/admin/login", label: "Admin login" },
  { to: "/about", label: "About us" },
];

const USER_LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/upload", label: "Apply for a loan" },
  { to: "/my-applications", label: "My applications" },
  { to: "/about", label: "About us" },
];

const ADMIN_LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/admin", label: "Dashboard", end: true },
  { to: "/approved", label: "Approved" },
  { to: "/rejected", label: "Rejected" },
  { to: "/pending", label: "Pending review" },
  { to: "/about", label: "About us" },
];

// Redirects to the right login page when nobody is signed in, or to the home page of the other role.
function RequireRole({ role, children }) {
  const session = useSession();
  if (!session) {
    return <Navigate to={role === "ADMIN" ? "/admin/login" : "/login"} replace />;
  }
  if (role && session.role !== role) {
    return <Navigate to={session.role === "ADMIN" ? "/admin" : "/my-applications"} replace />;
  }
  return children;
}

function AppShell() {
  const session = useSession();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const links = !session ? GUEST_LINKS : session.role === "ADMIN" ? ADMIN_LINKS : USER_LINKS;
  const displayName = session ? (session.role === "ADMIN" ? "Administrator" : session.full_name || session.username) : "";
  const initial = displayName.charAt(0).toUpperCase();

  async function handleLogout() {
    setMenuOpen(false);
    await logout().catch(() => {});
    navigate("/");
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">AI Loan Eligibility</div>
        <nav className="nav">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        {session && (
          <div className="profile">
            <button
              type="button"
              className="profile-button"
              aria-label="Open profile"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              {initial}
            </button>
            {menuOpen && (
              <div className="profile-menu">
                <div className="profile-avatar">{initial}</div>
                <strong>{displayName}</strong>
                <span className="muted small">@{session.username}</span>
                <span className="profile-role">{session.role === "ADMIN" ? "Administrator" : "Applicant"}</span>
                <button type="button" className="button logout-button" onClick={handleLogout}>
                  Log out
                </button>
              </div>
            )}
          </div>
        )}
      </header>

      <main className="page">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin/login" element={<AdminLoginPage />} />

          <Route path="/upload" element={<RequireRole role="USER"><UploadPage /></RequireRole>} />
          <Route
            path="/my-applications"
            element={
              <RequireRole role="USER">
                <ApplicationListPage title="My applications" />
              </RequireRole>
            }
          />

          <Route path="/admin" element={<RequireRole role="ADMIN"><AdminDashboardPage /></RequireRole>} />
          <Route
            path="/approved"
            element={
              <RequireRole role="ADMIN">
                <ApplicationListPage status="APPROVED" title="Approved applications" />
              </RequireRole>
            }
          />
          <Route
            path="/rejected"
            element={
              <RequireRole role="ADMIN">
                <ApplicationListPage status="REJECTED" title="Rejected applications" />
              </RequireRole>
            }
          />
          <Route
            path="/pending"
            element={
              <RequireRole role="ADMIN">
                <ApplicationListPage status="PENDING_REVIEW" title="Pending review" />
              </RequireRole>
            }
          />

          <Route path="/applications/:id" element={<RequireRole><ApplicationDetailPage /></RequireRole>} />
          <Route path="/assessment/:id" element={<RequireRole><AssessmentPage /></RequireRole>} />
        </Routes>
      </main>

      <footer className="app-footer">
        <span>AI Loan Eligibility · Capstone project</span>
        <span>Powered by FastAPI, React and Google Gemini</span>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
