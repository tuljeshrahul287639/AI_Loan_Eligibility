import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchApplications, fetchStats, importSamples } from "../api.js";
import { StatusBadge, formatDate, formatPercent } from "../components/common.jsx";

export default function AdminDashboardPage() {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState("");
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState("");

  const loadData = useCallback(() => {
    Promise.all([fetchStats(), fetchApplications({ limit: 10 })])
      .then(([statsData, recentData]) => {
        setStats(statsData);
        setRecent(recentData);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleImport() {
    setImporting(true);
    setMessage("");
    setError("");
    try {
      const result = await importSamples(10);
      setMessage(`Imported ${result.imported} sample applications (${result.skipped} already saved).`);
      loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <div className="section-header">
          <div>
            <h1>Admin dashboard</h1>
            <p className="muted">Every application from every applicant. Open a pending one to approve or reject it.</p>
          </div>
          <button type="button" className="button" onClick={handleImport} disabled={importing}>
            {importing ? "Importing…" : "Import sample applications"}
          </button>
        </div>
      </section>

      {error && <div className="alert">{error}</div>}
      {message && <div className="notice">{message}</div>}

      <section className="stat-grid">
        <StatCard label="Total applications" icon="📊" value={stats?.total} to="/admin" tone="violet" />
        <StatCard label="Approved" icon="✅" value={stats?.APPROVED} to="/approved" tone="green" />
        <StatCard label="Rejected" icon="❌" value={stats?.REJECTED} to="/rejected" tone="red" />
        <StatCard label="Pending review" icon="⏳" value={stats?.PENDING_REVIEW} to="/pending" tone="amber" />
      </section>

      <section className="card">
        <div className="section-header">
          <h2>Recent applications</h2>
          <Link to="/pending">Pending review →</Link>
        </div>
        {recent.length === 0 ? (
          <p className="muted">No applications yet. Applicants submit them, or import the samples to try the system.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {recent.map((app) => (
                <tr key={app.id}>
                  <td>
                    {app.applicant_name}
                    <div className="muted small">{app.applicant_id}</div>
                  </td>
                  <td><StatusBadge status={app.status} /></td>
                  <td>{formatPercent(app.confidence_score)}</td>
                  <td>{formatDate(app.created_at)}</td>
                  <td><Link to={`/applications/${app.id}`}>Details →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function StatCard({ label, icon, value, to, tone }) {
  return (
    <Link to={to} className={`stat-card ${tone}`}>
      <span className="stat-icon">{icon}</span>
      <span className="stat-label">{label}</span>
      <strong>{value ?? "—"}</strong>
    </Link>
  );
}
