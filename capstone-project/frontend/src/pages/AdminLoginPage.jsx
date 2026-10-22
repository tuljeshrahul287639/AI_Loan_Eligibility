import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { adminLogin } from "../api.js";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await adminLogin({ username: username.trim(), password });
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card admin-auth" onSubmit={handleSubmit}>
        <span className="hero-kicker">Admin portal</span>
        <h1>Admin login</h1>
        <p className="muted">
          Review pending applications and see every approved, rejected and pending decision. Applicants cannot use
          this page.
        </p>

        <label>
          Admin username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>

        {error && <div className="alert">{error}</div>}

        <button type="submit" className="button primary" disabled={busy}>
          {busy ? "Please wait…" : "Log in as admin"}
        </button>

        <p className="muted small">
          Applicant? <Link to="/login">Go to the applicant login</Link>
        </p>
      </form>
    </div>
  );
}
