import { Link } from "react-router-dom";
import { useSession } from "../session.js";

const AGENTS = [
  {
    icon: "💰",
    name: "Financial agent",
    tone: "violet",
    text: "Works out debt-to-income before and after the new loan payment, and checks whether the applicant can afford it.",
  },
  {
    icon: "🛡️",
    name: "Risk agent",
    tone: "cyan",
    text: "Scores risk from credit score, income and debt, and looks up the matching lending policies.",
  },
  {
    icon: "🎯",
    name: "Recommendation agent",
    tone: "pink",
    text: "Combines the two reports into one decision and flags cases that need a human to check them.",
  },
];

const TECH = ["Google Gemini", "FastAPI", "React + Vite", "SQLite", "ChromaDB policy search"];

const STEPS = [
  { icon: "📝", title: "Apply", text: "The applicant's details are entered and checked." },
  { icon: "🤖", title: "Assess", text: "The three agents analyse the application together." },
  { icon: "🏁", title: "Decide", text: "Approved, rejected, or sent for manual review, with the full reasoning." },
];

export default function HomePage() {
  const session = useSession();

  return (
    <div className="stack">
      <section className={session ? "hero greeting-hero" : "hero"}>
        {session ? (
          <div className="hero-text">
            <h1 className="greeting-hi">Hi, {session.role === "ADMIN" ? "Administrator" : session.full_name || session.username}</h1>
            <p className="greeting-welcome">Welcome to AI Loan Eligibility application</p>
          </div>
        ) : (
          <div className="hero-text">
            <span className="hero-kicker">AI-powered lending</span>
            <h1>Smarter loan decisions in minutes</h1>
            <p>
              Three AI agents review each loan application for finances, risk and the overall recommendation.
              You see the decision and every number behind it.
            </p>
          </div>
        )}
        <div className={session ? "hero-actions centered" : "hero-actions"}>
          {!session && (
            <>
              <Link to="/login" className="button hero-button">Applicant login</Link>
              <Link to="/admin/login" className="button hero-button ghost">Admin login</Link>
            </>
          )}
          {session?.role === "USER" && (
            <>
              <Link to="/upload" className="button hero-button">Apply for a loan</Link>
              <Link to="/my-applications" className="button hero-button ghost">My applications</Link>
            </>
          )}
          {session?.role === "ADMIN" && (
            <Link to="/admin" className="button hero-button">Open the admin dashboard</Link>
          )}
        </div>
      </section>

      <section className="card about">
        <div className="about-banner">
          <span className="hero-kicker">About this project</span>
          <h2>AI Loan Eligibility</h2>
          <p>
            A multi-agent loan eligibility system. Google Gemini reads income documents, three specialist
            agents assess the applicant, and every result is saved with the reasons behind it.
          </p>
          <div className="tech-chips">
            {TECH.map((item) => (
              <span key={item} className="tech-chip">{item}</span>
            ))}
          </div>
        </div>

        <h3 className="sub-heading">How it works</h3>
        <div className="steps">
          {STEPS.map((step, index) => (
            <div key={step.title} className="step">
              <div className="step-icon">{step.icon}</div>
              <div className="step-number">Step {index + 1}</div>
              <strong>{step.title}</strong>
              <p>{step.text}</p>
            </div>
          ))}
        </div>

        <h3 className="sub-heading">The three agents</h3>
        <div className="agent-tiles">
          {AGENTS.map((agent) => (
            <div key={agent.name} className={`agent-tile ${agent.tone}`}>
              <div className="agent-icon">{agent.icon}</div>
              <strong>{agent.name}</strong>
              <p>{agent.text}</p>
            </div>
          ))}
        </div>

        <h3 className="sub-heading">Possible outcomes</h3>
        <div className="outcomes">
          <span className="outcome approve">✅ Approved: all checks pass</span>
          <span className="outcome review">⏳ Pending review: a person must check it</span>
          <span className="outcome reject">❌ Rejected: a hard rule or risk limit fails</span>
        </div>
      </section>
    </div>
  );
}
