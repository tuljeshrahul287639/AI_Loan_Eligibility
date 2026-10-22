import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchApplication } from "../api.js";
import { KeyValueTable, StatusBadge, formatPercent } from "../components/common.jsx";
import { useSession } from "../session.js";

const STATUS_LABEL = { PASS: "Passed", FAIL: "Failed", REVIEW: "Needs a person", INFO: "Info" };
const STATUS_CLASS = { PASS: "approve", FAIL: "reject", REVIEW: "review", INFO: "" };
const STEP_DELAY_MS = 800;

// Shows how an application was assessed: each step appears in turn, then the final result.
export default function AssessmentPage() {
  const { id } = useParams();
  const session = useSession();
  const [app, setApp] = useState(null);
  const [error, setError] = useState("");
  const [revealed, setRevealed] = useState(0);

  useEffect(() => {
    setApp(null);
    setRevealed(0);
    setError("");
    fetchApplication(id).then(setApp).catch((err) => setError(err.message));
  }, [id]);

  const steps = app?.workflow_trace || [];
  const finished = app !== null && revealed >= steps.length;

  // Reveal one more step every STEP_DELAY_MS until all of them are shown
  useEffect(() => {
    if (!app || finished) return undefined;
    const timer = setTimeout(() => setRevealed((count) => count + 1), STEP_DELAY_MS);
    return () => clearTimeout(timer);
  }, [app, revealed, finished]);

  if (error) {
    return (
      <div className="stack">
        <div className="alert">{error}</div>
        <Link to="/">Back to home</Link>
      </div>
    );
  }
  if (!app) return <p className="muted">Loading the assessment…</p>;

  const backLink = session?.role === "ADMIN" ? "/admin" : "/my-applications";

  return (
    <div className="stack">
      <section className="card">
        <div className="section-header">
          <div>
            <h1>Assessment of {app.applicant_name}</h1>
            <span className="muted">{app.applicant_id}</span>
          </div>
          {finished ? (
            <StatusBadge status={app.status} />
          ) : (
            <span className="badge">Step {Math.min(revealed + 1, steps.length)} of {steps.length}</span>
          )}
        </div>
        {!finished && (
          <div className="assessment-actions">
            <p className="muted small">The system is checking this application one step at a time.</p>
            <button type="button" className="button ghost-dark" onClick={() => setRevealed(steps.length)}>
              Show all steps
            </button>
          </div>
        )}
      </section>

      <section className="card">
        <h2>What happens to an application</h2>
        <p className="muted">
          Each application goes through the same steps, in order. The system reads any uploaded documents, checks the
          form against the lending policy, asks two specialist agents for their view, combines them, and then makes the
          final decision. Anything unclear goes to a person.
        </p>
        <h3 className="sub-heading">Information the system used</h3>
        <KeyValueTable data={app.input_data} />
      </section>

      {steps.length === 0 && (
        <section className="card">
          <p className="muted">No step-by-step history was saved for this application.</p>
        </section>
      )}

      <section className="stack">
        {steps.slice(0, revealed).map((step) => (
          <StepCard key={step.number} step={step} />
        ))}
        {!finished && (
          <div className="trace-step trace-running">
            <div className="trace-head">
              <span className="trace-number">{revealed + 1}</span>
              <div>
                <strong>{steps[revealed].title}</strong>
                <div className="muted small">{steps[revealed].agent}</div>
              </div>
              <span className="spinner" aria-hidden="true" />
            </div>
            <p className="muted">Working on this step…</p>
          </div>
        )}
      </section>

      {finished && steps.length > 0 && (
        <section className="card result-card">
          <div className="section-header">
            <h2>Final result</h2>
            <StatusBadge status={app.status} />
          </div>
          <div className="stat-grid compact">
            <div className="stat">
              <span className="muted">Decision</span>
              <strong>{app.decision}</strong>
            </div>
            <div className="stat">
              <span className="muted">Confidence</span>
              <strong>{formatPercent(app.confidence_score)}</strong>
            </div>
            <div className="stat">
              <span className="muted">Needs a person to check</span>
              <strong>{app.requires_human_approval ? "Yes" : "No"}</strong>
            </div>
          </div>
          {app.reason && (
            <div className={`reason-box ${app.status}`}>
              <h3>{RESULT_HEADINGS[app.status] || "Reason"}</h3>
              <ul>
                {app.reason.split("\n").map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="assessment-actions">
            <Link to={`/applications/${app.id}`} className="button primary">Open full details</Link>
            <Link to={backLink} className="button ghost-dark">Back to applications</Link>
          </div>
        </section>
      )}
    </div>
  );
}

const RESULT_HEADINGS = {
  APPROVED: "Why this was approved",
  REJECTED: "Why this was rejected",
  PENDING_REVIEW: "Why it needs manual review",
};

function StepCard({ step }) {
  const hasInputs = Object.keys(step.inputs || {}).length > 0;
  const hasOutputs = Object.keys(step.outputs || {}).length > 0;
  return (
    <div className="trace-step enter">
      <div className="trace-head">
        <span className="trace-number">{step.number}</span>
        <div>
          <strong>{step.title}</strong>
          <div className="muted small">{step.agent}</div>
        </div>
        <span className={`badge ${STATUS_CLASS[step.status] || ""}`}>
          {STATUS_LABEL[step.status] || step.status}
        </span>
      </div>
      <p>{step.explanation}</p>
      {(hasInputs || hasOutputs) && (
        <div className="trace-grid">
          {hasInputs && (
            <div>
              <span className="muted small">What it looked at</span>
              <KeyValueTable data={step.inputs} />
            </div>
          )}
          {hasOutputs && (
            <div>
              <span className="muted small">What it found</span>
              <KeyValueTable data={step.outputs} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
