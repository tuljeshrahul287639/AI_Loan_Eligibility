# Architecture

## Workflow

```
 PDF (stored or uploaded)
        |
        v
 [1] PDF Parser ---------- extract labelled fields -> LoanApplication (validated)
        |
        v
 [2] Router -------------- Personal | Home | Auto  (declared type, else inferred from purpose)
        |                  selects product rules + policy documents (general + product)
        v
 [3] Financial Analysis Agent --> metrics + loan summary
        |
        v
 [4] Risk Agent -------------- --> score, factors, knockouts, exceptions + risk explanation
        |
        v
 [5] Recommendation Agent ---- --> decision, terms, conditions + rationale
        |
        v
 AssessmentResult (with a per-step timing trace shown in the UI)
```

The workflow is **sequential**: each agent reads the results of the earlier ones from a shared `PipelineContext`. It is **router-based** because the Router chooses the product route (rules and policy documents) before any agent runs. If the loan type is missing or unrecognised the Router uses the stated purpose; if that fails too, the request is rejected with a clear error.

## Agents

All agents extend `BaseAgent` (`run(ctx)`, `describe(result)`, and an `evidence()` helper) and share a `PolicyStore` and a `Narrator`.

| Agent | Inputs | Output | Narrative |
|---|---|---|---|
| Financial Analysis | Application, product rules | Monthly income, credit tier, indicative rate, instalment, existing and post-loan DTI, loan-to-income, LTV, savings cover, free income, maximum affordable amount at 43% DTI | Loan summary |
| Risk | Application, financial analysis | Score 0-100, band, seven weighted factors, knockouts (automatic decline), exceptions (need conditions) | Risk explanation |
| Recommendation | All of the above | Decision, recommended amount/term/rate/instalment/DTI, conditions, reasons | Recommendation rationale |

### Where AI is and is not used

- **Deterministic code** decides everything that matters: figures, scores, knockouts, exceptions and the final decision. The same application always yields the same decision.
- **A local Ollama model (optional, free)** only writes the three prose passages from the computed facts and retrieved clauses, with instructions not to change any figure or the decision. Failure or no configured model falls back to template text without affecting the result.

## Policy knowledge base (retrieval)

`backend/policies/*.md` hold four documents: General Credit Policy (`GCP-`), Personal (`PL-`), Home (`HL-`) and Auto (`AL-`). Each clause is a line beginning `**ID**`. `PolicyStore` parses them into clauses and builds a BM25 index (section title plus text). Each agent assembles its **policy evidence** from two sources:

1. clauses its rules cite directly (looked up by id), and
2. top BM25 matches for a query about the step, restricted to the documents of the selected route.

The evidence is passed to the narrator as context and shown to the user. `rules.py` holds the numeric thresholds, each commented with its clause, and a test checks that every clause id cited anywhere in the code exists in the documents.

## Risk score

The score is the sum of factor points (maximum 100); higher is riskier. Bands per GCP-6.2: **Low 0-35, Medium 36-60, High 61+**.

| Factor (max points) | Points |
|---|---|
| Credit score (25) | Excellent 0, Good 6, Fair 13, Weak 20, Poor 25 |
| Post-loan DTI (25) | up to 20%: 0, to 30%: 5, to 36%: 10, to 43%: 15, to 50%: 21, above: 25 |
| Credit utilization (10) | up to 30%: 0, to 50%: 3, to 80%: 7, above: 10 |
| Delinquencies, 24 months (15) | 0: 0, 1: 7, 2: 11, 3 or more: 15 |
| Employment stability (10) | below required tenure: 10, below required+2 years: 4, below 5 years: 2, else 0 |
| Liquidity, savings as multiples of instalment (10) | below 1x: 10, below 2x: 7, below 6x: 3, else 0 |
| Collateral exposure (5) | Unsecured: 3. Secured by LTV: up to 60%: 0, to 80%: 2, to 90%: 4, above: 5 |

## Decision rules

**Knockouts (decline):** age outside 21-65 (GCP-1.1); amount or term outside product limits; income below the product minimum; credit score below 600 (GCP-2.2) or the product floor (personal 620, home 650, auto 600); post-loan DTI above 50% (GCP-3.2); three or more delinquencies (GCP-4.2); LTV above the product maximum (home 90%, auto 100%); personal loan with utilization above 80% and any delinquency (PL-4.1).

**Exceptions (conditional approval):** post-loan DTI 43-50%; tenure below the requirement; utilization above 80%; one or two delinquencies; savings below 2x the instalment; LTV above the standard (home 80%, auto 90%); personal loan amount above 50% of annual income.

**Mapping (GCP-6.3):**

| Condition | Decision |
|---|---|
| Any knockout, or High band | Declined |
| Medium band, or any exception | Conditionally approved |
| Low band and no exceptions | Approved |

**Recommended terms.** For approvals the requested terms stand. For conditional approvals the amount is reduced, rounded down to the nearest $10, where an exception requires it: to the maximum affordable at 43% DTI (GCP-3.3), to 50% of income for personal loans (PL-1.2), or to 90% of the vehicle price for auto loans (AL-3.2). Other exceptions become written conditions (for example mortgage insurance for a home loan at 80-90% LTV). If the affordable amount falls below the product minimum, the outcome becomes a decline. The instalment uses an indicative rate of the product base rate plus a credit-tier adjustment (GCP-7.1).

## Data and PDFs

Synthetic applicants are drawn from four weighted profiles (strong 30%, average 30%, stretched 25%, weak 15%), then loan type, amount and collateral are sized from income so that a batch produces approvals, conditional approvals and declines. Application PDFs contain `Label: value` lines in three sections (Applicant, Financial, Loan Request); the parser matches those labels, normalises numbers, validates them with Pydantic and reports missing or invalid fields. Any PDF with the same labels can be uploaded.

## Frontend

Plain HTML, CSS and JavaScript (no build step) served by FastAPI. The result view renders the workflow trace, decision banner, narratives with clause badges, a metrics grid, the risk gauge and factor table, knockouts and exceptions, and collapsible policy evidence. All text from the API is HTML-escaped before display.
