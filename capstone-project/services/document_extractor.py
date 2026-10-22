import json
from typing import Any, Dict

from google import genai
from google.genai import types

import config

DOCUMENT_TYPES = ["Payslip", "Bank statement", "Employment letter", "Tax return", "Other"]

SUPPORTED_CONTENT_TYPES = {
    "application/pdf": "application/pdf",
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "text/plain": "text/plain",
    "text/csv": "text/csv",
}

# Only these keys are ever read from the model output. Anything else is dropped,
# so identity numbers and account details the model might mention are never stored.
EXTRACTED_FIELDS = [
    "name",
    "employer_name",
    "employment_type",
    "years_employed",
    "monthly_income",
    "monthly_expenses",
    "existing_debts",
]

MONEY_FIELDS = {"monthly_income", "monthly_expenses", "existing_debts"}
EMPLOYMENT_TYPES = {"Full-time", "Part-time", "Self-employed"}

PROMPT_TEMPLATE = """You are extracting income and employment details from a loan applicant's "{doc_type}" document.

Return ONLY a JSON object with exactly these keys:
- "name": applicant's full name, or null
- "employer_name": employer or company name, or null
- "employment_type": one of "Full-time", "Part-time", "Self-employed", or null
- "years_employed": whole number of years with the employer, or null
- "monthly_income": gross monthly income as a plain number, or null
- "monthly_expenses": total monthly outgoings if clearly shown (e.g. bank statement debits), else null
- "existing_debts": total monthly loan, EMI or credit-card minimum payments if clearly shown, else null

Rules:
- Use null when a value is missing or unclear. Do not guess.
- Money values are plain numbers in monthly terms: no currency symbols or commas. If only an annual salary is shown, divide it by 12.
- Privacy: never output government ID numbers (SSN, Aadhaar, PAN, passport, driver's license), bank account or card numbers, home addresses, dates of birth, or health information.
"""


class ExtractionError(Exception):
    """Raised when the document cannot be read or the model response is unusable."""


def _to_number(value: Any) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        cleaned = str(value).replace(",", "").replace("$", "").replace("₹", "").strip()
        return float(cleaned)
    except ValueError:
        return None


def _sanitize(raw: Dict[str, Any]) -> Dict[str, Any]:
    clean: Dict[str, Any] = {}
    for key in EXTRACTED_FIELDS:
        value = raw.get(key)
        if key in MONEY_FIELDS or key == "years_employed":
            value = _to_number(value)
            if key == "years_employed" and value is not None:
                value = int(value)
        elif key == "employment_type":
            value = value if value in EMPLOYMENT_TYPES else None
        elif value is not None:
            value = str(value).strip() or None
        clean[key] = value
    return clean


def extract_income_fields(file_bytes: bytes, content_type: str, doc_type: str) -> Dict[str, Any]:
    """Send one income document to Gemini and return only the allowed, sanitized fields."""
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ExtractionError(f"Unsupported file type: {content_type}")

    prompt = PROMPT_TEMPLATE.format(doc_type=doc_type)
    if content_type.startswith("text/"):
        document_part = types.Part.from_text(text=file_bytes.decode("utf-8", errors="replace"))
    else:
        document_part = types.Part.from_bytes(data=file_bytes, mime_type=content_type)

    try:
        client = genai.Client(
            api_key=config.GOOGLE_API_KEY,
            vertexai=False,  # always use the Gemini API key, never Vertex AI / OAuth credentials from the environment
            http_options=types.HttpOptions(
                timeout=60_000,  # milliseconds; fail instead of leaving the upload spinning
                retry_options=types.HttpRetryOptions(attempts=2),
            ),
        )
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[document_part, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
    except Exception as exc:
        raise ExtractionError(f"Gemini request failed: {exc}") from exc

    try:
        raw = json.loads(response.text or "")
    except (json.JSONDecodeError, TypeError) as exc:
        raise ExtractionError("Gemini returned a response that is not valid JSON") from exc

    if not isinstance(raw, dict):
        raise ExtractionError("Gemini returned an unexpected response structure")

    return _sanitize(raw)
