from app.schemas import LoanApplication


def make_app(**overrides) -> LoanApplication:
    """A strong personal-loan applicant; tests override the fields they care about."""
    base = dict(
        application_id="APP-T", customer_id="CUST-T", full_name="Test Person", age=35, employment_type="Salaried",
        years_employed=8, annual_income=90_000, monthly_debt_payments=300, savings_balance=30_000, credit_score=780,
        credit_utilization=15, delinquencies_24m=0, loan_type="Personal Loan", loan_amount=20_000, term_months=48,
        purpose="Travel", asset_value=None,
    )
    base.update(overrides)
    return LoanApplication(**base)
