"""Writes one application PDF per scenario into test-data/ for manual testing, and prints each outcome.

Usage (from the project root):  .venv\\Scripts\\python tests\\make_test_pdfs.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("LLM_ENABLED", "0")  # deterministic template text
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "tests")]

from helpers import make_app  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402

from app.llm import Narrator  # noqa: E402
from app.orchestrator import AssessmentOrchestrator  # noqa: E402
from app.pdf_tools import render_pdf  # noqa: E402
from app.policy_store import PolicyStore  # noqa: E402

out_dir = ROOT / "test-data"
out_dir.mkdir(exist_ok=True)
orchestrator = AssessmentOrchestrator(PolicyStore(), Narrator())

for s in SCENARIOS:
    pdf = render_pdf(make_app(application_id=s.id, customer_id=f"CUST-{s.id}", **s.overrides))
    slug = s.name.lower().replace(" ", "-").replace(",", "").replace("%", "pct")
    path = out_dir / f"{s.id}_{slug}.pdf"
    path.write_bytes(pdf)
    try:
        r = orchestrator.assess_pdf(pdf)
        rec = r.recommendation
        amount = f"${rec.recommended_amount:,.0f}" if rec.recommended_amount else "-"
        print(f"{s.id} | {rec.decision:11} | route {r.route.loan_type}/{r.route.method} | risk {r.risk.score:3} {r.risk.band:6} "
              f"| amount {amount} | KO {[k.code for k in r.risk.knockouts]} EX {[x.code for x in r.risk.exceptions]}")
    except ValueError as exc:
        print(f"{s.id} | REJECTED    | {exc}")
# negative-input files for the manual "bad input" tests
import io  # noqa: E402

from reportlab.pdfgen import canvas  # noqa: E402

buf = io.BytesIO()
c = canvas.Canvas(buf)
c.drawString(72, 700, "Loan Application Form")
c.drawString(72, 680, "Full Name: Incomplete Applicant")
c.save()
(out_dir / "NEG-01_missing-fields.pdf").write_bytes(buf.getvalue())
(out_dir / "NEG-02_not-a-pdf.pdf").write_text("This is plain text with a .pdf extension.", encoding="utf8")
(out_dir / "NEG-03_corrupt-pdf.pdf").write_bytes(b"%PDF-1.4 this file is truncated and cannot be read")

print(f"\n{len(SCENARIOS)} scenario PDFs and 3 negative-input files written to {out_dir}")
