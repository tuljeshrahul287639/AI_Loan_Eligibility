# Testing Flow

Test plan and step-by-step test flow for the AI Loan Eligibility Assessment Assistant. It has two parts: an **automated suite** (45 tests, one command) and a **manual flow** a tester can follow in the browser using ready-made test PDFs. Every expected result below was produced by running the application, and the scenario suite re-checks them on every run.

## 1. Scope

| In scope | Where it is tested |
|---|---|
| PDF intake: rendering, parsing, rejection of bad files | Automated, manual TC-17/18, NEG-01 to NEG-03 |
| Router: declared and inferred product route, unroutable requests | Automated, manual TC-01, TC-10, TC-12, TC-16, TC-17 |
| Financial Analysis Agent: instalment, DTI, LTV, affordable amount | Automated, manual TC-02, TC-10 |
| Risk Agent: score, bands, knockouts, exceptions, clause citations | Automated, manual TC-03 to TC-12, TC-15, TC-19, TC-20 |
| Recommendation Agent: decision mapping, terms, conditions | Automated, all manual TCs |
| Policy retrieval (RAG) | Automated, manual Part C |
| REST API and error handling | Automated, manual Part D |
| Web UI: lists, generation, upload, results, policies tab | Manual Part B and C |
| Optional local-model narration | Automated against a simulated server; manual only if Ollama is installed (section 7) |

Out of scope: performance and load, security testing, accessibility audit, browser matrix (the UI was checked in Chrome only).

## 2. Launching the application

Requires Python 3.10 or later and Windows PowerShell. Every command below runs the virtual environment's own Python by its full path, so the environment does **not** need to be activated. All paths are relative to the project root (`loan-assistant`).

**Step 1. Open PowerShell in the project root.**
```powershell
cd "C:\Users\308352\OneDrive - UST\Desktop\project\loan-assistant"
dir        # you should see backend, frontend, tests, requirements.txt
```

**Step 2. One-time setup (skip if the `.venv` folder already exists).**
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

**Step 3. Free port 8000 if an earlier copy of the app is still running.** Safe to run even if nothing is using it.
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**Step 4. Generate the test PDFs** (20 scenarios and 3 bad-input files, written to `test-data\`). Safe to repeat.
```powershell
.\.venv\Scripts\python tests\make_test_pdfs.py
```

**Step 5. Confirm the automated tests pass** (expected: `45 passed`).
```powershell
.\.venv\Scripts\python -m pytest -q
```

**Step 6. Start the application.**
```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```
Wait for the line `Uvicorn running on http://127.0.0.1:8000`. Leave this window open; closing it stops the app. On the very first start, 12 synthetic applications and their PDFs are created automatically.

**Step 7. Open the application** in a browser at http://localhost:8000, and open the `test-data\` folder in File Explorer so the test files are at hand.

**Step 8. Stop the application** when finished by pressing `Ctrl+C` in the window from step 6.

| Problem | Fix |
|---|---|
| `Address already in use` | Run step 3, then step 6 again |
| `..\.venv\Scripts\python` not found | Run step 2 from the project root, then continue from step 6 |
| Page does not load | Check the step 6 window for errors and that it shows `Uvicorn running` |
| `Activate.ps1` is blocked by PowerShell policy | Not needed. Use the full-path commands above |

The 12 applications created on first start are **random**, so manual testing uses the fixed PDFs in `test-data\` instead; those give the same result every time.

## 3. Automated tests

```powershell
.\.venv\Scripts\python -m pytest -q          # expected: 45 passed
```

| File | Tests | Covers |
|---|---|---|
| `tests/test_pipeline.py` | 17 | Clause parsing and retrieval, every clause cited in code exists in the policy documents, PDF round trip for 30 generated applications, bad PDFs, router, each decision rule, score integrity (score equals sum of factors, band matches score), a generated batch yields all three outcomes, recommended amount never breaches the DTI limit |
| `tests/test_scenarios.py` | 20 | The 20 scenarios in section 5, each run end to end through PDF, router and agents |
| `tests/test_api.py` | 2 | API flow (health, list, PDF download, assess, generate, replace, policies) and error paths (non-PDF, broken PDF, 404, invalid count) |
| `tests/test_llm.py` | 6 | Template mode, successful local-model reply and request shape, three failure modes fall back to templates, decisions identical with and without the model |

Scenarios are defined once in `tests/scenarios.py`, which feeds both `test_scenarios.py` and the PDF generator, so the manual PDFs and the automated checks cannot drift apart.

### Do the tests catch real defects?

A rule was deliberately broken one at a time and the scenario suite re-run. A control run with no change must pass.

| Deliberate defect | Result |
|---|---|
| Control, no change | Passed |
| Automatic-decline DTI limit 50% raised to 80% | Caught by TC-03 |
| Minimum age 21 lowered to 18 | Caught by TC-04 |
| General score floor 600 lowered to 500 | Caught by TC-05 |
| Personal-loan score floor 620 lowered to 580 | Caught by TC-06 |
| Standard DTI limit 43% raised to 55% | Caught by TC-02 |
| Home LTV maximum 90% raised to 99% | Caught by TC-11 |
| Medium-risk upper bound 60 raised to 90 | Caught by TC-20 |

Two of these slipped through on the first attempt, which led to tightening the scenarios (knockouts are now asserted exactly and the cited clause is checked).

## 4. Manual test flow

Work through the parts in order. Record results in section 8.

### Part A. Smoke test

| # | Step | Expected |
|---|---|---|
| A1 | Open http://localhost:8000 | Page loads with blue header, **Assessment** and **Lending policies** tabs, no error banner |
| A2 | Look at the header pill | "Narrative: templates (free, no model needed)" |
| A3 | Look at the **Applications** list | 12 entries (or more if generated), each with name, ID, loan type, amount |
| A4 | Open http://localhost:8000/api/health | JSON with `"status":"ok"`, `"policy_clauses":34` |

### Part B. Scenario tests by PDF upload

For each row: click **Upload application PDF**, choose the file from `test-data\`, and check the result screen. The decision banner, the agent workflow strip (five completed steps) and the risk table should all appear. Unless stated, the base applicant is: age 35, salaried, 8 years in role, income $90,000, existing debt $300/month, savings $30,000, credit score 780, utilization 15%, no delinquencies, personal loan $20,000 over 48 months.

| ID | File (`test-data\`) | What differs from the base applicant | Expected decision | Expected details |
|---|---|---|---|---|
| TC-01 | `TC-01_strong-personal-loan.pdf` | none | **APPROVED** | $20,000, risk 3 LOW, no conditions, no exceptions |
| TC-02 | `TC-02_dti-between-43pct-and-50pct.pdf` | income $60,000, debt $1,200/mo, loan $30,000 over 36 months | **CONDITIONAL** | Amount cut to **$29,010**, condition "Loan amount reduced from $30,000 to $29,010", exception `GCP-3.2`, recommended post-loan DTI at most 43% |
| TC-03 | `TC-03_dti-above-50pct.pdf` | income $60,000, debt $2,500/mo, loan $30,000 over 36 months | **DECLINED** | Automatic-decline rule `GCP-3.2` (post-loan DTI above 50%); no terms shown; risk band is still LOW (28), proving the knockout decides |
| TC-04 | `TC-04_applicant-under-21.pdf` | age 19 | **DECLINED** | Knockout `GCP-1.1` |
| TC-05 | `TC-05_credit-score-below-600.pdf` | score 590 | **DECLINED** | Knockout citing `GCP-2.2` |
| TC-06 | `TC-06_personal-loan-score-610.pdf` | score 610 | **DECLINED** | Knockout citing `PL-2.2` (product floor 620 applies, not the general 600) |
| TC-07 | `TC-07_three-delinquencies.pdf` | 3 delinquencies | **DECLINED** | Knockout `GCP-4.2` |
| TC-08 | `TC-08_one-delinquency.pdf` | 1 delinquency | **CONDITIONAL** | $20,000, risk 10, condition asking for a written explanation, citing `GCP-4.2` |
| TC-09 | `TC-09_personal-loan-above-50pct-of-income.pdf` | income $50,000, loan $30,000 | **CONDITIONAL** | Amount cut to **$25,000** (50% of income), exception `PL-1.2` |
| TC-10 | `TC-10_home-loan-at-85pct-ltv.pdf` | Home loan, income $150,000, no existing debt, property $400,000, loan $340,000 over 300 months | **CONDITIONAL** | Route **Home**, amount unchanged at $340,000, condition "Obtain mortgage insurance", exception `HL-3.2` |
| TC-11 | `TC-11_home-loan-at-95pct-ltv.pdf` | as TC-10 but loan $380,000 | **DECLINED** | Knockout `HL-3.2` (LTV above 90%) |
| TC-12 | `TC-12_auto-loan-at-95pct-ltv.pdf` | Auto loan, vehicle $40,000, loan $38,000, income $100,000, 60 months | **CONDITIONAL** | Route **Auto**, amount cut to **$36,000** (90% of price), exception `AL-3.2` |
| TC-13 | `TC-13_strong-home-loan.pdf` | Home loan, property $500,000, loan $350,000 | **APPROVED** | $350,000, risk 2 LOW |
| TC-14 | `TC-14_strong-auto-loan.pdf` | Auto loan, vehicle $40,000, loan $28,000 | **APPROVED** | $28,000, risk 2 LOW |
| TC-15 | `TC-15_six-months-in-current-job.pdf` | 0.5 years in role | **CONDITIONAL** | $20,000, risk 13 LOW, condition asking for income and employment verification |
| TC-16 | `TC-16_unrecognised-loan-type-purpose-says-car.pdf` | Loan type "Loan", purpose "Buying a car", vehicle $30,000, loan $20,000, 60 months | **APPROVED** | Workflow note says routed to **Auto** and mentions the type was not recognised and was inferred from the purpose |
| TC-17 | `TC-17_cannot-be-routed.pdf` | Loan type "Loan", purpose "Something else" | **Rejected** | Red banner: "Cannot route application: loan type 'Loan' and purpose 'Something else' do not match a supported product (personal, home, auto)." No result screen |
| TC-18 | `TC-18_home-loan-without-collateral-value.pdf` | Home loan with collateral value N/A | **Rejected** | Red banner: "A Home Loan application must state the collateral value." |
| TC-19 | `TC-19_medium-risk-band-no-exceptions.pdf` | score 660, utilization 70%, income $90,000, debt $2,450/mo, savings $2,200, 3 years in role | **CONDITIONAL** | Risk **43 MEDIUM**, no exceptions listed, single condition to refer for credit officer review citing `GCP-6.3` |
| TC-20 | `TC-20_high-risk-band-no-knockouts.pdf` | score 620, utilization 78%, income $60,000, debt $1,350/mo, savings $800, 0.5 years in role, 2 delinquencies, loan $30,000 over 36 months | **DECLINED** | Risk **82 HIGH**, no automatic-decline rules, exceptions listed (DTI, tenure, delinquency, liquidity), reason cites HIGH band `GCP-6.2` |

For every case that produces a result also check:

- Citation badges such as `GCP-3.2` appear next to findings and are in the **Lending policies** tab.
- The risk table's points add up to the score shown, and the gauge marker sits in the matching coloured zone (green up to 35, amber to 60, red above).
- Declined cases show **no** recommended amount, rate or instalment; approved and conditional cases show them.
- A recommended post-loan DTI never exceeds 50%, and is at most 43% where the amount was cut for affordability.

### Part C. Application list and UI functions

| # | Step | Expected |
|---|---|---|
| C1 | Click any application in the list | Row highlights; detail card shows the application fields (13 tiles: loan type, amount, term, purpose, collateral, age, employment, income, debt, savings, score, utilization, delinquencies); results area is cleared |
| C2 | Click **View PDF** | New tab opens with a "Loan Application Form" PDF whose values match the detail card |
| C3 | Click **Run assessment** | Button shows a spinner and is disabled, then results appear and the page scrolls to them |
| C4 | Run the same application twice | Identical decision, risk score and figures both times (decisions are deterministic) |
| C5 | Set count 5, tick nothing, click **Generate** | Blue message "Application list now has N synthetic applications", list grows by 5, IDs continue the sequence |
| C6 | Set count 4, tick **Replace existing**, click **Generate** | List shows exactly 4 applications starting at APP-1001; the detail and results panels reset |
| C7 | Reload the browser page | The same applications are still listed (they are stored on disk) |
| C8 | Open the **Lending policies** tab | Four documents (General Credit, Personal, Home, Auto) with 34 clauses in total, grouped by section |
| C9 | In a result, expand each **Policy evidence retrieved** panel | Clause ids, text and relevance scores are shown; clause counts are shown with correct singular/plural |
| C10 | Compare the **Loan summary** figures to the application | Monthly income equals annual income divided by 12; instalment, DTI and savings cover are consistent with the narrative sentence |
| C11 | Run assessments for stored applications of each loan type | Home and Auto results show a Loan-to-value figure; Personal shows N/A |

### Part D. Bad input and API checks

Upload each file in `test-data\` (the UI accepts them) or call the API as shown.

| ID | File | Expected message | HTTP |
|---|---|---|---|
| NEG-01 | `NEG-01_missing-fields.pdf` | "The PDF is missing required application fields: Age, Employment Type, Years in Current Employment, ..." (lists every missing field) | 422 |
| NEG-02 | `NEG-02_not-a-pdf.pdf` (text with a .pdf name) | "The uploaded file is not a PDF" | 422 |
| NEG-03 | `NEG-03_corrupt-pdf.pdf` | "Could not read the file as a PDF: Stream has ended unexpectedly" | 422 |
| NEG-04 | Any file over 5 MB | "File is larger than 5 MB" | 413 |

In the UI the message appears in a red banner prefixed "Could not assess the uploaded PDF:". The app must stay usable afterwards (pick an application and run it).

API spot checks (PowerShell):

```powershell
Invoke-RestMethod http://localhost:8000/api/health
(Invoke-RestMethod http://localhost:8000/api/applications).Count
Invoke-RestMethod -Method Post http://localhost:8000/api/applications/APP-1001/assess | Select-Object -ExpandProperty recommendation
curl.exe -s -F "file=@test-data/TC-02_dti-between-43pct-and-50pct.pdf;type=application/pdf" http://localhost:8000/api/assess/upload
curl.exe -s -o NUL -w "%{http_code}" http://localhost:8000/api/applications/NOPE/pdf          # expect 404
curl.exe -s -o NUL -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{\"count\":0}' http://localhost:8000/api/synthetic/generate   # expect 422
```

The interactive API page at http://localhost:8000/docs can also be used.

## 5. Scenario design notes

The 20 scenarios were chosen to cover each decision path at least once:

- **Every knockout:** age, score (general and product floor), DTI above 50%, delinquencies, LTV above maximum (TC-03 to TC-07, TC-11).
- **Every exception that changes the amount:** DTI, personal income multiple, auto LTV (TC-02, TC-09, TC-12).
- **Exceptions that add a condition only:** delinquency, tenure, home LTV (TC-08, TC-15, TC-10).
- **All three products** and **both router methods** (TC-01, TC-10, TC-12 to TC-14, TC-16).
- **Decisions driven by the risk band alone:** MEDIUM gives conditional approval, HIGH gives decline (TC-19, TC-20).
- **Rejected before assessment:** unroutable and missing collateral (TC-17, TC-18).

Knockouts and exceptions not covered by a dedicated scenario (age above 65, income below the product minimum, product amount or term out of range, utilization above 80%, savings below 2x the instalment as the only exception) are exercised only indirectly. Add scenarios in `tests/scenarios.py` to cover them.

## 6. Entry and exit criteria

- **Entry:** dependencies installed, `pytest` shows 45 passed, app starts and Part A passes.
- **Exit (pass):** all Part B decisions and details match, Parts C and D pass, no JavaScript errors in the browser console, and no unexpected error banners.
- **Fail:** any decision or amount that differs from the tables, a result screen for a rejected file, a missing citation, or a UI action that does nothing.

## 7. Optional: local-model narration

Skip this unless Ollama is installed (see the README). With `OLLAMA_MODEL` set before starting the app:

| # | Step | Expected |
|---|---|---|
| E1 | Check the header pill | "Narrative: local model (name)" |
| E2 | Run TC-02 | Same decision, amount and risk score as in Part B; the three narrative cards show a green "Written by local model" badge |
| E3 | Stop Ollama and run again | Assessment still succeeds with template text; pill says "templates (local model unavailable)" and hovering it shows the error |

The decision banner and every figure must be identical with and without the model. Only the wording of the three narrative cards may differ.

## 8. Results log

| ID | Pass / Fail | Tester | Date | Notes |
|---|---|---|---|---|
| A1 to A4 | | | | |
| TC-01 to TC-20 | | | | |
| C1 to C11 | | | | |
| NEG-01 to NEG-04 | | | | |
| Automated suite (45) | | | | |

## 9. Known limitations of this test effort

- Data and policies are synthetic; the tests prove the app follows its own policy documents, not any real bank's rules.
- The UI was exercised in headless Chrome only; other browsers and screen sizes were not checked.
- The optional local-model path has not been run against a real model on the development machine.
- No performance, load, security or accessibility testing was done.
