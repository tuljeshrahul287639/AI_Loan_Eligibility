"use strict";

const $ = (id) => document.getElementById(id);
const state = { apps: [], selectedId: null, uploaded: null };

const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const usd = (n) => (n == null ? "N/A" : "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 }));
const usd2 = (n) => "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = (n, d = 1) => (n == null ? "N/A" : (n * 100).toFixed(d) + "%");

const prose = (t) => esc(t).replace(/\[([A-Z]+-\d+\.\d+(?:,\s*[A-Z]+-\d+\.\d+)*)\]/g, (_, ids) =>
  ids.split(/,\s*/).map((id) => `<span class="clause">${id}</span>`).join(" "));
const srcBadge = (s) => `<span class="src ${s}">${s === "ollama" ? "Written by local model" : "Template text"}</span>`;

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = res.statusText;
    try { const body = await res.json(); detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail); } catch {}
    throw new Error(detail);
  }
  return res.json();
}

function showMessage(text, info = false) {
  const el = $("message");
  el.textContent = text;
  el.className = "message" + (info ? " info" : "");
  el.hidden = !text;
}

function busy(button, label, on) {
  if (on) { button.dataset.label = button.innerHTML; button.innerHTML = `<span class="spinner"></span>${label}`; }
  else if (button.dataset.label) { button.innerHTML = button.dataset.label; }
  button.disabled = on;
}

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((t) => { t.classList.toggle("active", t === tab); t.setAttribute("aria-selected", t === tab); });
  $("tab-assess").hidden = tab.dataset.tab !== "assess";
  $("tab-policies").hidden = tab.dataset.tab !== "policies";
  if (tab.dataset.tab === "policies") loadPolicies();
}));


async function loadHealth() {
  try {
    const h = await api("/api/health");
    const pill = $("llm-pill");
    pill.textContent = h.llm_mode === "ollama" ? `Narrative: local model (${h.model})`
      : h.llm_key_configured ? "Narrative: templates (local model unavailable)" : "Narrative: templates (free, no model needed)";
    pill.title = h.llm_error || "How the agents write their narrative text";
    pill.classList.toggle("ollama", h.llm_mode === "ollama");
  } catch (e) { $("llm-pill").textContent = "Backend unreachable"; }
}


async function loadApps() {
  state.apps = await api("/api/applications");
  renderList();
}

function renderList() {
  $("app-count").textContent = `(${state.apps.length})`;
  $("app-list").innerHTML = state.apps.map((a) => `
    <li><button class="app-item ${a.application_id === state.selectedId ? "active" : ""}" data-id="${esc(a.application_id)}">
      <div class="name">${esc(a.full_name)}</div>
      <div class="meta"><span>${esc(a.application_id)} · ${esc(a.loan_type)}</span><span>${usd(a.loan_amount)}</span></div>
    </button></li>`).join("");
  document.querySelectorAll(".app-item").forEach((b) => b.addEventListener("click", () => selectApp(b.dataset.id)));
}

function selectApp(id) {
  state.selectedId = id;
  state.uploaded = null;
  renderList();
  renderSelected(state.apps.find((a) => a.application_id === id), true);
  $("results").hidden = true;
  showMessage("");
}

function renderSelected(a, canRun) {
  $("empty").hidden = true;
  const el = $("selected");
  el.hidden = false;
  el.innerHTML = `
    <div class="sel-head">
      <div><h2>${esc(a.full_name)}</h2><span class="muted">${esc(a.application_id)} · ${esc(a.customer_id)}</span></div>
      <div class="actions">
        ${canRun ? `<a class="btn btn-outline" href="/api/applications/${encodeURIComponent(a.application_id)}/pdf" target="_blank" rel="noopener">View PDF</a>
        <button id="run-btn" class="btn">Run assessment</button>` : ""}
      </div>
    </div>
    <dl class="kv">
      ${kv("Loan type", a.loan_type)}${kv("Requested amount", usd(a.loan_amount))}${kv("Term", a.term_months + " months")}
      ${kv("Purpose", a.purpose || "N/A")}${kv("Collateral value", usd(a.asset_value))}
      ${kv("Age", a.age)}${kv("Employment", `${a.employment_type}, ${a.years_employed} yrs`)}
      ${kv("Annual income", usd(a.annual_income))}${kv("Monthly debt payments", usd(a.monthly_debt_payments))}
      ${kv("Savings", usd(a.savings_balance))}${kv("Credit score", a.credit_score)}
      ${kv("Credit utilization", a.credit_utilization + "%")}${kv("Delinquencies (24m)", a.delinquencies_24m)}
    </dl>`;
  if (canRun) $("run-btn").addEventListener("click", runAssessment);
}
const kv = (k, v) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`;


$("gen-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.submitter;
  busy(btn, "Generating…", true);
  try {
    state.apps = await api("/api/synthetic/generate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count: Number($("gen-count").value), replace: $("gen-replace").checked }),
    });
    if (!state.apps.some((a) => a.application_id === state.selectedId)) {
      state.selectedId = null; $("selected").hidden = true; $("results").hidden = true; $("empty").hidden = false;
    }
    renderList();
    showMessage(`Application list now has ${state.apps.length} synthetic applications, each with a PDF.`, true);
    loadHealth();
  } catch (err) { showMessage(err.message); }
  busy(btn, "", false);
});

async function runAssessment() {
  const btn = $("run-btn");
  busy(btn, "Assessing…", true);
  showMessage("");
  try {
    renderResults(await api(`/api/applications/${encodeURIComponent(state.selectedId)}/assess`, { method: "POST" }));
    loadHealth();
  } catch (err) { showMessage("Assessment failed: " + err.message); }
  busy(btn, "", false);
}

$("upload-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  showMessage(`Assessing ${file.name}…`, true);
  const form = new FormData();
  form.append("file", file);
  try {
    const result = await api("/api/assess/upload", { method: "POST", body: form });
    state.selectedId = null;
    renderList();
    renderSelected(result.application, false);
    showMessage("");
    renderResults(result);
  } catch (err) { showMessage("Could not assess the uploaded PDF: " + err.message); }
});

// ---------- results ----------
function renderResults(r) {
  const rec = r.recommendation, fin = r.financial, risk = r.risk;
  const terms = rec.decision === "DECLINED" ? "" : `
    <div class="terms">
      ${term("Amount", usd(rec.recommended_amount))}${term("Term", rec.recommended_term_months + " months")}
      ${term("Indicative rate", pct(rec.indicative_apr, 2))}${term("Monthly instalment", usd2(rec.monthly_installment))}
      ${term("Post-loan DTI", pct(rec.post_loan_dti))}
    </div>`;
  const list = (title, items) => items.length ? `<h3>${title}</h3><ul>${items.map((i) => `<li>${prose(i)}</li>`).join("")}</ul>` : "";

  $("results").innerHTML = `
    <div class="card"><h2>Agent workflow</h2>
      <div class="trace">${r.trace.map((s) => `
        <div class="step ${s.status}"><span class="s-ms">${s.duration_ms} ms</span>
          <div class="s-title">${esc(s.step)}</div><div class="s-agent">${esc(s.agent)}</div>
          <div class="s-detail">${esc(s.detail)}</div></div>`).join("")}</div>
      <p class="muted" style="margin-top:10px">Routed to the <b>${esc(r.route.product_name)}</b> workflow. ${esc(r.route.reason)}
        Policy documents consulted: ${r.route.policy_docs.map((d) => esc(d.replace(/_/g, " "))).join(", ")}.</p>
    </div>

    <div class="decision ${rec.decision}">
      <span class="badge"><span>${rec.decision}</span></span>
      <h2>${esc(rec.headline)}</h2>
      ${terms}
      ${list("Conditions", rec.conditions)}
      ${list(rec.decision === "DECLINED" ? "Reasons for decline" : "Basis for decision", rec.reasons)}
    </div>

    <div class="card"><h2>Eligibility recommendation ${srcBadge(rec.rationale_source)}</h2>
      <p class="narrative">${prose(rec.rationale)}</p></div>

    <div class="card"><h2>Loan summary ${srcBadge(fin.summary_source)}</h2>
      <p class="narrative">${prose(fin.summary)}</p>
      <div class="metrics">
        ${metric("Monthly income", usd(fin.monthly_income))}${metric("Credit tier", fin.credit_tier)}
        ${metric("Indicative rate", pct(fin.indicative_apr, 2))}${metric("Proposed instalment", usd2(fin.proposed_emi))}
        ${metric("Existing DTI", pct(fin.existing_dti))}${metric("Post-loan DTI", pct(fin.post_loan_dti))}
        ${metric("Loan-to-income", pct(fin.loan_to_income, 0))}${metric("Loan-to-value", pct(fin.ltv))}
        ${metric("Savings cover", fin.savings_coverage.toFixed(1) + "x instalment")}${metric("Free monthly income", usd(fin.disposable_income))}
        ${metric("Max affordable at 43% DTI", usd(fin.max_affordable_amount))}
      </div>
    </div>

    <div class="card"><h2>Risk explanation ${srcBadge(risk.explanation_source)}</h2>
      <div class="score-row">
        <div class="score-num">${risk.score}<small>/100</small></div>
        <div class="gauge" role="img" aria-label="Risk score ${risk.score} of 100"><div class="marker" style="left:${risk.score}%"></div></div>
        <span class="band ${risk.band}">${risk.band}</span>
      </div>
      <p class="narrative">${prose(risk.explanation)}</p>
      <table><thead><tr><th>Factor</th><th>Value</th><th>Risk points</th><th></th><th>Policy</th></tr></thead><tbody>
        ${risk.factors.map((f) => `<tr><td>${esc(f.name)}</td><td>${esc(f.display_value)}</td><td>${f.points} / ${f.max_points}</td>
          <td><div class="bar" title="${f.level}"><i class="${f.level}" style="width:${(f.points / f.max_points) * 100}%"></i></div></td>
          <td><span class="clause">${esc(f.clause)}</span></td></tr>`).join("")}
      </tbody></table>
      ${findings("Automatic-decline rules triggered", "ko", risk.knockouts)}
      ${findings("Policy exceptions", "ex", risk.exceptions)}
    </div>

    <div class="card"><h2>Policy evidence retrieved</h2>
      ${refsBlock("Financial analysis", fin.policy_refs)}${refsBlock("Risk assessment", risk.policy_refs)}${refsBlock("Recommendation", rec.policy_refs)}
    </div>`;
  $("results").hidden = false;
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

const term = (l, v) => `<div class="term"><div class="label">${l}</div><div class="value">${esc(v)}</div></div>`;
const metric = (l, v) => `<div class="metric"><div class="label">${l}</div><div class="value">${esc(v)}</div></div>`;
const findings = (title, cls, items) => !items.length ? "" : `<h3>${title}</h3><ul class="findings ${cls}">${items.map((f) =>
  `<li>${esc(f.message.charAt(0).toUpperCase() + f.message.slice(1))} <span class="clause">${esc(f.clause)}</span><span class="remedy">${esc(f.remedy)}</span></li>`).join("")}</ul>`;
const refsBlock = (title, refs) => `<details><summary>${title} (${refs.length} ${refs.length === 1 ? "clause" : "clauses"})</summary><div class="inner">${refs.map((c) =>
  `<div class="ref"><span class="clause">${esc(c.id)}</span> ${esc(c.text)}${c.score != null ? `<span class="score">relevance ${c.score}</span>` : ""}</div>`).join("")}</div></details>`;

// ---------- policies tab ----------
let policiesLoaded = false;
async function loadPolicies() {
  if (policiesLoaded) return;
  try {
    const docs = await api("/api/policies");
    $("policy-docs").innerHTML = docs.map((d) => {
      let section = "";
      const rows = d.clauses.map((c) => {
        const head = c.section !== section ? `<div class="sec">${esc(c.section)}</div>` : "";
        section = c.section;
        return `${head}<div class="clause-row"><span class="clause">${esc(c.id)}</span> ${esc(c.text)}</div>`;
      }).join("");
      return `<div class="card policy-doc"><h2>${esc(d.title)}</h2>${rows}</div>`;
    }).join("");
    policiesLoaded = true;
  } catch (e) { $("policy-docs").innerHTML = `<div class="message">${esc(e.message)}</div>`; }
}

loadHealth();
loadApps().catch((e) => showMessage("Could not load applications: " + e.message));
