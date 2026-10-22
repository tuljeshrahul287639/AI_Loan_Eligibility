from services.document_extractor import EXTRACTED_FIELDS, _sanitize


def test_sanitize_keeps_only_allowed_fields():
    raw = {
        "name": "Jane Doe",
        "ssn": "123-45-6789",
        "bank_account_number": "000111222",
        "monthly_income": 4000,
        "unexpected": "value",
    }
    clean = _sanitize(raw)
    assert set(clean) == set(EXTRACTED_FIELDS)
    assert "ssn" not in clean
    assert "bank_account_number" not in clean


def test_sanitize_parses_money_strings_and_drops_bad_values():
    clean = _sanitize(
        {
            "monthly_income": "$4,500.50",
            "monthly_expenses": "not a number",
            "existing_debts": True,
            "employment_type": "Contractor",
            "years_employed": "6.7",
        }
    )
    assert clean["monthly_income"] == 4500.5
    assert clean["monthly_expenses"] is None
    assert clean["existing_debts"] is None
    assert clean["employment_type"] is None
    assert clean["years_employed"] == 6


def test_sanitize_fills_missing_fields_with_none():
    clean = _sanitize({})
    assert all(value is None for value in clean.values())
