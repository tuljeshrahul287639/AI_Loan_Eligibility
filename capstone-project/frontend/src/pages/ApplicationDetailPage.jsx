import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchApplication, reviewApplication } from "../api.js";
import {
  KeyValueTable,
  StatusBadge,
  formatDate,
  formatPercent,
} from "../components/common.jsx";
import { useSession } from "../session.js";

const REASON_HEADINGS = {
  APPROVED: "Why this was approved",
  REJECTED: "Why this was rejected",
  PENDING_REVIEW: "Why it needs manual review",
};

export default function ApplicationDetailPage() {
  const { id } = useParams();
  const session = useSession();
  const [application, setApplication] = useState(null);
  const [error, setError] = useState("");

  function reload() {
    return fetchApplication(id)
      .then(setApplication)
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    reload();
  }, [id]);

  if (error) {
    return (
      <div className="stack">
        <div className="alert">{error}</div>
        <Link to="/">Back to home</Link>
      </div>
    );
  }
  if (!application) return <p className="muted">Loading…</p>;

  const app = application;
  return (
    <div className="stack">
      <section className="card">
        <div className="section-header">
          <div>
            <h1>{app.applicant_name}</h1>
            <span className="muted">{app.applicant_id}</span>
          </div>
          <div className="header-actions">
            <StatusBadge status={app.status} />
            <Link to={`/assessment/${app.id}`} className="button ghost-dark">View step-by-step</Link>
          </div>
        </div>

        <div className="stat-grid compact">
          <Info label="Decision" value={app.decision} />
          <Info label="Confidence" value={formatPercent(app.confidence_score)} />
          <Info label="Human approval required" value={app.requires_human_approval ? "Yes" : "No"} />
          <Info label="Processing time" value={`${app.workflow_duration_seconds.toFixed(2)}s`} />
          <Info label="Created" value={formatDate(app.created_at)} />
        </div>
        {app.reason && (
          <div className={`reason-box ${app.status}`}>
            <h3>{REASON_HEADINGS[app.status] || "Reason"}</h3>
            <ul>
              {app.reason.split("\n").map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {session?.role === "ADMIN" && app.status === "PENDING_REVIEW" && (
        <ReviewPanel applicationId={app.id} onReviewed={reload} />
      )}

      {app.reviews.length > 0 && (
        <section className="card">
          <h2>Review history</h2>
          {app.reviews.map((review) => (
            <div key={review.id} className="document-block">
              <div className="section-header">
                <strong>{review.decision === "APPROVED" ? "Approved by reviewer" : "Rejected by reviewer"}</strong>
                <span className="muted small">
                  {review.reviewer} · {formatDate(review.created_at)}
                </span>
              </div>
              <p>{review.note}</p>
            </div>
          ))}
        </section>
      )}

      <section className="card">
        <h2>Applicant input</h2>
        <KeyValueTable data={app.input_data} />
      </section>

      <section className="card">
        <h2>Uploaded documents</h2>
        {app.documents.length === 0 && <p className="muted">No documents were attached to this application.</p>}
        {app.documents.map((doc) => (
          <div key={doc.id} className="document-block">
            <div className="section-header">
              <strong>{doc.doc_type}</strong>
              <span className="muted small">
                {doc.original_filename} · {(doc.size_bytes / 1024).toFixed(1)} KB · {formatDate(doc.uploaded_at)}
              </span>
            </div>
            {doc.extraction_status === "FAILED" ? (
              <div className="alert">Extraction failed: {doc.extraction_error}</div>
            ) : (
              <KeyValueTable data={doc.extracted_data} />
            )}
          </div>
        ))}
      </section>

      <section className="agent-grid">
        <AgentCard
          title="Financial agent"
          description="Debt-to-income and affordability of the loan payment"
          data={app.financial_analysis}
        />
        <AgentCard
          title="Risk agent"
          description="Risk score from credit, income, debt and policy retrieval"
          data={app.risk_analysis}
        />
        <AgentCard
          title="Recommendation agent"
          description="Combines the two agents into the final decision"
          data={app.recommendation_analysis}
        />
      </section>
    </div>
  );
}

function ReviewPanel({ applicationId, onReviewed }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const noteTooShort = note.trim().length < 3;

  async function submit(decision) {
    setBusy(true);
    setError("");
    try {
      await reviewApplication(applicationId, { decision, note: note.trim() });
      setNote("");
      await onReviewed();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card review-panel">
      <h2>Make the decision</h2>
      <p className="muted small">
        The agents could not decide this one alone. Check the documents and reasons above, then approve or reject.
      </p>

      <label className="review-note">
        Reason for your decision (required)
        <textarea
          rows={3}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="For example: bankruptcy discharge letter checked, debts confirmed."
        />
      </label>

      {error && <div className="alert">{error}</div>}

      <div className="review-actions">
        <button
          type="button"
          className="button approve-button"
          disabled={busy || noteTooShort}
          onClick={() => submit("APPROVED")}
        >
          Approve loan
        </button>
        <button
          type="button"
          className="button reject-button"
          disabled={busy || noteTooShort}
          onClick={() => submit("REJECTED")}
        >
          Reject loan
        </button>
      </div>
    </section>
  );
}

function Info({ label, value }) {
  return (
    <div className="stat">
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AgentCard({ title, description, data }) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <p className="muted small">{description}</p>
      {data ? (
        <KeyValueTable data={data} />
      ) : (
        <p className="muted">Not run. The application was rejected during prescreening.</p>
      )}
    </div>
  );
}
