# AI Loan Eligibility Assessment Assistant

A working proof of concept for the Finance-domain brief **"AI Loan Eligibility Assessment Assistant"**.

> **Problem:** Banks manually review loan applications, slowing approvals and introducing inconsistency.

The assistant reads a loan application PDF, runs it through three cooperating agents, and returns a consistent, policy-grounded eligibility recommendation with the reasoning shown.

## How the brief maps to the build

| Brief | Implementation |
|---|---|
| Synthetic customer financial data | `backend/app/generator.py` creates applicants in four credit profiles (strong, average, stretched, weak) so batches show every outcome |
| Loan application PDFs | `backend/app/pdf_tools.py` renders each synthetic application to a PDF and parses PDFs back (including uploaded ones) |
| Financial Analysis Agent | `agents/financial.py`: income, instalment, DTI, LTV, savings cover, affordable amount, and the **loan summary** |
| Risk Agent | `agents/risk.py`: 0-100 risk score, policy knockouts and exceptions, and the **risk explanation** |
| Recommendation Agent | `agents/recommendation.py`: the **eligibility recommendation** with terms and conditions |
| Sequential workflow | `orchestrator.py` runs PDF extraction, then Financial, then Risk, then Recommendation, passing a shared context |
| Router-based workflow | `routing.py` sends each application down the Personal, Home or Auto route, which selects the rules and policy documents |
| Lending policy documents | `backend/policies/*.md`, indexed clause by clause and retrieved with BM25 (`policy_store.py`) |
| Loan summarization / Risk explanation / Eligibility recommendation | The three narrative sections of the result screen |

Nothing outside this brief was added: no authentication, database, payment, or document-management features.

## Quick start

Requires Python 3.10+ and Windows PowerShell. The commands run the virtual environment's Python by full path, so the environment does not need to be activated.

1. **Open PowerShell in the project folder.**
   ```powershell
   cd "C:\Users\308352\OneDrive - UST\Desktop\project\loan-assistant"
   ```
2. **One-time setup** (skip if the `.venv` folder already exists).
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python -m pip install -r requirements.txt
   ```
3. **Free port 8000** if an earlier copy is still running (safe if nothing is).
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
   ```
4. **Start the app.**
   ```powershell
   cd backend
   ..\.venv\Scripts\python -m uvicorn app.main:app --port 8000
   ```
   Wait for `Uvicorn running on http://127.0.0.1:8000` and leave the window open.
5. **Open <http://localhost:8000>** in a browser. On first start, 12 synthetic applications and their PDFs are generated automatically.
6. **Stop the app** with `Ctrl+C` in the window from step 4.

To test the app, follow [docs/TESTING.md](docs/TESTING.md).

### Using the UI

1. Pick an application in the left list (or **Generate** more, or **Upload** your own application PDF).
2. Click **Run assessment**. The application's PDF is read by the parser, so stored and uploaded applications take the same path.
3. Read the result: agent workflow trace, decision banner with recommended terms and conditions, loan summary, risk score with per-factor breakdown, and the policy clauses retrieved. Citation badges such as `GCP-3.1` point to clauses on the **Lending policies** tab.

### Cost: free

The whole app runs at **zero cost with no accounts or API keys**. The decision, score, every figure and the three narrative passages (loan summary, risk explanation, recommendation rationale) are produced by deterministic code and built-in templates by default.

### Optional: AI-written narrative with a free local model

If you want the three narrative passages written by a language model, you can run one on your own machine with [Ollama](https://ollama.com) (free, open source, no account, nothing leaves your computer):

```powershell
winget install Ollama.Ollama          # or download the installer from ollama.com
ollama pull llama3.2:3b               # about 2 GB, one-time download
$env:OLLAMA_MODEL = "llama3.2:3b"     # then start the app in this same window
```

The decision, score and figures are still computed by code; the model only writes the prose from those facts and the retrieved clauses. If the model is not configured or Ollama is not running, the app silently uses the templates. The header pill and the badge on each passage show which was used; if a configured model cannot be reached, the pill says so and hovering it shows the error. A 3B model on CPU may take tens of seconds per assessment; the template text is instant.

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | unset | Local model name; unset means templates |
| `OLLAMA_URL` | `http://localhost:11434` | Where Ollama is listening |
| `OLLAMA_TIMEOUT` | `120` | Seconds to wait for each generation |
| `LLM_ENABLED` | `1` | Set to `0` to force template text |
| `SEED_COUNT` | `12` | Applications generated on first start |
| `LOAN_DATA_DIR` | `backend/data` | Where `customers.json` and PDFs are stored |

## REST API

| Method and path | Description |
|---|---|
| `GET /api/health` | Status, narration mode, counts |
| `GET /api/applications` | Synthetic customer applications |
| `POST /api/synthetic/generate` | Body `{"count": 1-50, "replace": false}` generates applications and PDFs |
| `GET /api/applications/{id}/pdf` | Download an application PDF |
| `POST /api/applications/{id}/assess` | Assess a stored application (via its PDF) |
| `POST /api/assess/upload` | Multipart `file`: assess an uploaded application PDF (max 5 MB) |
| `GET /api/policies` | Policy documents and clauses |

Interactive docs are at <http://localhost:8000/docs>. Unreadable or incomplete PDFs return `422` with the missing fields listed.

## Tests

```powershell
.\.venv\Scripts\python -m pytest -q
```

45 tests cover policy parsing and retrieval, the PDF round trip, routing, every decision rule, score integrity, the API including error paths, the optional local-model path, and 20 fixed end-to-end scenarios. A test also asserts that every clause id cited in code exists in the policy documents, so the rules and documents cannot drift apart silently.

For manual testing, generate ready-made test PDFs (20 scenarios plus 3 bad-input files) into `test-data/`:

```powershell
.\.venv\Scripts\python tests\make_test_pdfs.py
```

The full test plan, expected results for every scenario, and the step-by-step manual flow are in [docs/TESTING.md](docs/TESTING.md).

## Project layout

```
loan-assistant/
  backend/
    app/
      main.py            FastAPI app, serves the UI
      orchestrator.py    PDF intake -> router -> sequential agents, with timing trace
      routing.py         Router (declared type, or inferred from purpose)
      agents/            BaseAgent + Financial / Risk / Recommendation agents
      policy_store.py    Clause parser and BM25 retrieval over policy documents
      rules.py           Numeric thresholds mirroring the policy clauses
      llm.py             Optional free local-model (Ollama) narration with template fallback
      pdf_tools.py       Application PDF rendering and parsing
      generator.py       Synthetic customer data
      store.py           JSON/PDF-backed application store
      schemas.py         Pydantic models
    policies/            Lending policy documents (markdown)
    data/                Generated at runtime
  frontend/              index.html, styles.css, app.js (no build step)
  tests/                 Automated tests, fixed scenarios, test-PDF generator
  test-data/             Generated test PDFs for manual testing
  docs/ARCHITECTURE.md   Design, scoring and decision rules
  docs/TESTING.md        Test plan and manual test flow
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the workflow, scoring tables and decision mapping.

## Scope and limitations

- All data is synthetic. Policies, rates and thresholds are illustrative, not real bank policy.
- Rates used for the instalment are indicative values defined in the policy documents (GCP-7.1 and product clauses), not live pricing.
- The local-model path is covered by tests against a simulated Ollama server; it has not been run against a real model on this machine because Ollama is not installed. Small local models can phrase things imperfectly, which is why the decision banner and figures never depend on them.
- Assessments are not persisted; each run is computed fresh.
- The recommendation is decision support for a loan officer, not an automated credit decision.
