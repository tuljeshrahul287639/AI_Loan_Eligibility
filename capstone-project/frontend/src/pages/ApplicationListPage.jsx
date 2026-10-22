import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchApplications } from "../api.js";
import { StatusBadge, formatDate, formatPercent } from "../components/common.jsx";

export default function ApplicationListPage({ status, title }) {
  const [applications, setApplications] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setApplications(null);
    setError("");
    fetchApplications({ status })
      .then(setApplications)
      .catch((err) => setError(err.message));
  }, [status]);

  return (
    <section className="card">
      <div className="section-header">
        <h2>{title}</h2>
        <span className="muted">{applications ? `${applications.length} found` : ""}</span>
      </div>

      {error && <div className="alert">{error}</div>}
      {!applications && !error && <p className="muted">Loading…</p>}
      {applications && applications.length === 0 && <p className="muted">Nothing here yet.</p>}

      {applications && applications.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Applicant</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Human approval</th>
              <th>Reason</th>
              <th>Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {applications.map((app) => (
              <tr key={app.id}>
                <td>
                  {app.applicant_name}
                  <div className="muted small">{app.applicant_id}</div>
                </td>
                <td><StatusBadge status={app.status} /></td>
                <td>{formatPercent(app.confidence_score)}</td>
                <td>{app.requires_human_approval ? "Required" : "No"}</td>
                <td className="small">{app.reason ? app.reason.split("\n").join(" ") : "—"}</td>
                <td>{formatDate(app.created_at)}</td>
                <td className="link-stack">
                  <Link to={`/assessment/${app.id}`}>View steps</Link>
                  <Link to={`/applications/${app.id}`}>Details</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
