import { Link } from "react-router-dom";

const TEAM = [
  "Pavan Naga Sai Krishna Yaddanapudi",
  "Varsha Thammi",
  "Tulijesh Rahul Anajipuram",
  "Harsh Pratap Singh",
  "Deepakarthika Madhanagopal",
];

const PIPELINE = [
  {
    icon: "👤",
    title: "Sign up and log in",
    text: "Applicants create an account or log in on the applicant page. The admin logs in on a separate admin page. Each user sees only what their role allows.",
  },
  {
    icon: "📄",
    title: "Upload income documents",
    text: "Payslips, bank statements, employment letters, tax returns or other documents (PDF, PNG, JPG, TXT or CSV, up to 10 MB). Gemini reads each one and fills in the income details.",
  },
  {
    icon: "📝",
    title: "Check the application",
    text: "The applicant reviews the filled-in form, corrects anything, and enters what the documents do not show: loan amount, expenses, debts and credit score.",
  },
  {
    icon: "🛡️",
    title: "Pre-screen against hard rules",
    text: "Before any agent runs, the application is checked against fixed lending rules: minimum credit score, minimum income, loan amount range, loan size against income, and the debt limit. A failure rejects it immediately.",
  },
  {
    icon: "🤖",
    title: "Three agents assess it",
    text: "The financial agent works out debt-to-income before and after the loan. The risk agent scores risk out of 100 and looks up matching lending policies. The recommendation agent combines both views into one decision.",
  },
  {
    icon: "⚖️",
    title: "Apply policy conditions",
    text: "Some cases always need a person to check, even if the agents agree: a bankruptcy history, several delinquencies, too many recent credit enquiries, or short employment.",
  },
  {
    icon: "🏁",
    title: "Final decision",
    text: "Approved, pending manual review, or rejected. Every outcome comes with plain-English reasons, and every step is kept so the applicant can see how the decision was reached.",
  },
  {
    icon: "🧑‍💼",
    title: "Admin review",
    text: "The admin opens each pending application, reads the reasons and documents, then approves or rejects it with a required note. The decision and note are kept in the review history.",
  },
];

const AGENTS = [
  {
    icon: "💰",
    name: "Financial agent",
    tone: "violet",
    text: "Measures debt-to-income now and after the new loan payment. Approval needs debt after the loan at or below 43% of income. Above 50% is an automatic rejection.",
  },
  {
    icon: "🛡️",
    name: "Risk agent",
    tone: "cyan",
    text: "Combines credit score, income and debt into a risk score out of 100 using weighted factors (credit 35%, income 25%, debt 25%, behaviour 15%). It also searches the lending policy documents for rules that match the applicant.",
  },
  {
    icon: "🎯",
    name: "Recommendation agent",
    tone: "pink",
    text: "Compares the financial and risk views. Agreement gives a confident result. Disagreement sends the file to a person, because the system should not decide alone when its own checks conflict.",
  },
];

const RULES = [
  ["Minimum credit score", "620"],
  ["Minimum monthly income", "₹1,500"],
  ["Loan amount range", "₹50,000 to ₹5,00,000"],
  ["Loan no more than 5 times the yearly income", "5x"],
  ["Debt after the loan: approval limit", "43% of income"],
  ["Debt after the loan: automatic rejection", "above 50% of income"],
  ["Bankruptcy history", "needs a discharge check (2+ years)"],
  ["Delinquencies", "more than 1 goes to a person"],
  ["Recent credit enquiries", "more than 3 goes to a person"],
  ["Employment history", "at least 1 year"],
];

const STACK = [
  "React + Vite",
  "FastAPI",
  "SQLAlchemy",
  "SQLite (MySQL supported)",
  "Google Gemini",
  "LangChain",
  "ChromaDB policy search",
  "PBKDF2 password hashing",
];

export default function AboutPage() {
  return (
    <div className="stack about-page">
      <section className="about-hero">
        <span className="hero-kicker">About the project</span>
        <h1>AI Loan Eligibility</h1>
        <p>
          An AI-assisted system that reads an applicant's income documents, checks the application against lending
          rules, asks three specialist agents for their view, and reaches a decision. Anything the system cannot
          settle with confidence goes to a human admin.
        </p>
      </section>

      <section className="card">
        <h2>What the project does</h2>
        <p className="muted">
          Loan officers spend a long time reading payslips, working out how much of someone's income already goes on
          debt, and deciding whether the risk is acceptable. This project automates the first pass. It gives every
          applicant the same rules, shows the working behind each number, and keeps a person in charge of the cases
          that need judgement.
        </p>
        <p className="muted">
          The system has two sides. Applicants sign up, upload documents, and submit an application. Admins see every
          application, and they approve or reject the ones the system sends to manual review.
        </p>
      </section>

      <section className="card">
        <h2>How an application is processed</h2>
        <div className="steps">
          {PIPELINE.map((step, index) => (
            <div key={step.title} className="step">
              <div className="step-icon">{step.icon}</div>
              <div className="step-number">Step {index + 1}</div>
              <strong>{step.title}</strong>
              <p>{step.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>The three agents</h2>
        <div className="agent-tiles">
          {AGENTS.map((agent) => (
            <div key={agent.name} className={`agent-tile ${agent.tone}`}>
              <div className="agent-icon">{agent.icon}</div>
              <strong>{agent.name}</strong>
              <p>{agent.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>The lending rules</h2>
        <p className="muted">
          These values come from the policy documents in the project's data folder. Amounts are in Indian rupees.
        </p>
        <table className="kv-table">
          <tbody>
            {RULES.map(([rule, value]) => (
              <tr key={rule}>
                <th>{rule}</th>
                <td>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <h2>Outcomes</h2>
        <div className="outcomes">
          <span className="outcome approve">✅ Approved: all checks pass</span>
          <span className="outcome review">⏳ Pending review: a person must check it</span>
          <span className="outcome reject">❌ Rejected: a hard rule or risk limit fails</span>
        </div>
        <p className="muted">
          Every decision lists its reasons in plain language, and the step-by-step view shows what each check looked at
          and what it found.
        </p>
      </section>

      <section className="card">
        <h2>Security and privacy</h2>
        <ul className="about-list">
          <li>Passwords are stored as salted hashes, never as plain text.</li>
          <li>Login sessions expire after 7 days.</li>
          <li>Applicants see only their own applications and documents. Admins see all of them.</li>
          <li>Government ID numbers, bank account numbers and card numbers are never stored from documents.</li>
          <li>Each applicant's uploaded files are kept on the server for the assessment and are not shared with other applicants.</li>
        </ul>
      </section>

      <section className="card">
        <h2>Technology</h2>
        <div className="tech-chips dark">
          {STACK.map((item) => (
            <span key={item} className="tech-chip dark">{item}</span>
          ))}
        </div>
        <p className="muted">
          The backend is a FastAPI service with a database for users, sessions, applications, documents and reviews.
          The frontend is a React single-page app that talks to the backend.
        </p>
      </section>

      <section className="card">
        <h2>Limitations</h2>
        <ul className="about-list">
          <li>This is a capstone project for demonstration. It is not a real lending service.</li>
          <li>Some policy values disagree between the documents (for example the minimum income and the risk score scale). The system uses one set of values and notes the conflicts in its code.</li>
          <li>Amounts are shown in rupees, but the sample numbers are not converted from the dollar figures in the source documents.</li>
          <li>Document reading depends on Google Gemini, so extraction can fail when the service is busy. Those documents are marked for manual entry.</li>
        </ul>
      </section>

      <section className="card team-card">
        <h2>Created by</h2>
        <ol className="team-list">
          {TEAM.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ol>
        <p className="muted">
          <Link to="/">Back to the home page</Link>
        </p>
      </section>
    </div>
  );
}
