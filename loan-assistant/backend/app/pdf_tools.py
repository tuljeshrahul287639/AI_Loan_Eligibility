"""Loan application PDFs: render a LoanApplication to PDF and extract one back from PDF text."""
import io
import re
from datetime import date
from xml.sax.saxutils import escape

from pydantic import ValidationError
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from .schemas import LoanApplication


class ApplicationParseError(ValueError):
    pass


# (model field, label printed in the PDF, section)
FIELDS = [
    ("application_id", "Application ID", "Applicant Information"),
    ("customer_id", "Customer ID", "Applicant Information"),
    ("full_name", "Full Name", "Applicant Information"),
    ("age", "Age", "Applicant Information"),
    ("employment_type", "Employment Type", "Applicant Information"),
    ("years_employed", "Years in Current Employment", "Applicant Information"),
    ("annual_income", "Annual Income (USD)", "Financial Information"),
    ("monthly_debt_payments", "Monthly Existing Debt Payments (USD)", "Financial Information"),
    ("savings_balance", "Savings Balance (USD)", "Financial Information"),
    ("credit_score", "Credit Score", "Financial Information"),
    ("credit_utilization", "Credit Utilization (%)", "Financial Information"),
    ("delinquencies_24m", "Delinquencies in Last 24 Months", "Financial Information"),
    ("loan_type", "Loan Type", "Loan Request"),
    ("loan_amount", "Requested Loan Amount (USD)", "Loan Request"),
    ("term_months", "Requested Term (Months)", "Loan Request"),
    ("purpose", "Loan Purpose", "Loan Request"),
    ("asset_value", "Collateral Value (USD)", "Loan Request"),
]
_MONEY_FIELDS = {"annual_income", "monthly_debt_payments", "savings_balance", "loan_amount", "asset_value"}
_OPTIONAL = {"purpose", "asset_value", "application_id", "customer_id"}


def _display(field: str, value) -> str:
    if value is None:
        return "N/A"
    if field in _MONEY_FIELDS:
        return f"${value:,.2f}"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def render_pdf(app: LoanApplication) -> bytes:
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], textColor=colors.HexColor("#0b3d91"), fontSize=20, spaceAfter=4)
    section = ParagraphStyle("s", parent=styles["Heading3"], textColor=colors.HexColor("#0b3d91"), spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("b", parent=styles["BodyText"], fontSize=10.5, leading=17)
    note = ParagraphStyle("n", parent=styles["BodyText"], fontSize=8, textColor=colors.grey)

    story = [
        Paragraph("Loan Application Form", title),
        Paragraph(f"Application Date: {date.today().isoformat()}", body),
        HRFlowable(width="100%", color=colors.HexColor("#0b3d91"), thickness=1.2, spaceBefore=6),
    ]
    values = app.model_dump()
    current = None
    for field, label, sect in FIELDS:
        if sect != current:
            story.append(Paragraph(sect, section))
            current = sect
        story.append(Paragraph(f"<b>{escape(label)}:</b> {escape(_display(field, values[field]))}", body))
    story += [
        Spacer(1, 0.4 * inch),
        Paragraph("Synthetic data generated for demonstration purposes. It does not describe a real person.", note),
    ]

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=letter, title=f"Loan Application {app.application_id}",
                      leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch).build(story)
    return buf.getvalue()


def _number(raw: str) -> str:
    return re.sub(r"[$,\s%]", "", raw)


def parse_pdf(data: bytes) -> LoanApplication:
    try:
        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    except Exception as exc:
        raise ApplicationParseError(f"Could not read the file as a PDF: {exc}") from exc

    raw: dict[str, str] = {}
    for line in text.splitlines():
        for field, label, _ in FIELDS:
            m = re.match(rf"^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
            if m:
                raw.setdefault(field, m[1])

    missing = [label for field, label, _ in FIELDS if field not in raw and field not in _OPTIONAL]
    if missing:
        raise ApplicationParseError("The PDF is missing required application fields: " + ", ".join(missing))

    values: dict = {"application_id": raw.get("application_id", "UPLOADED"), "customer_id": raw.get("customer_id", "UNKNOWN"),
                    "purpose": raw.get("purpose", "")}
    for field, value in raw.items():
        if field in _MONEY_FIELDS:
            values[field] = None if value.strip().upper() == "N/A" else _number(value)
        elif field in {"age", "years_employed", "credit_score", "credit_utilization", "delinquencies_24m", "term_months"}:
            values[field] = _number(value)
        elif field == "employment_type":
            values[field] = "Self-employed" if "self" in value.lower() else "Salaried"
        else:
            values.setdefault(field, value)
    try:
        return LoanApplication(**values)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        raise ApplicationParseError(f"The PDF contains invalid values ({problems})") from exc
