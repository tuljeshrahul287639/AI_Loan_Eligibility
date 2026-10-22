import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { signup, userLogin } from "../api.js";

export default function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isSignup = mode === "signup";

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (isSignup && password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      if (isSignup) {
        await signup({ username: username.trim(), full_name: fullName.trim(), password });
      } else {
        await userLogin({ username: username.trim(), password });
      }
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={handleSubmit}>
        <span className="hero-kicker">Applicant portal</span>
        <h1>{isSignup ? "Create your applicant account" : "Log in to apply"}</h1>
        <p className="muted">
          {isSignup
            ? "Sign up to submit a loan application and follow its status."
            : "Log in to submit a loan application and see only your own applications."}
        </p>

        {isSignup && (
          <label>
            Full name
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} />
          </label>
        )}
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
            placeholder={isSignup ? "3-40 letters, numbers, dots or _" : ""}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={isSignup ? 8 : 1}
            autoComplete={isSignup ? "new-password" : "current-password"}
            placeholder={isSignup ? "At least 8 characters" : ""}
          />
        </label>
        {isSignup && (
          <label>
            Confirm password
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              autoComplete="new-password"
            />
          </label>
        )}

        {error && <div className="alert">{error}</div>}

        <button type="submit" className="button primary" disabled={busy}>
          {busy ? "Please wait…" : isSignup ? "Create account" : "Log in"}
        </button>

        <p className="muted small">
          {isSignup ? "Already have an account? " : "New applicant? "}
          <button type="button" className="link-button" onClick={() => setMode(isSignup ? "login" : "signup")}>
            {isSignup ? "Log in" : "Create an account"}
          </button>
        </p>
        <p className="muted small">
          Admin or underwriter? <Link to="/admin/login">Go to the admin login</Link>
        </p>
      </form>
    </div>
  );
}
