"""Fixed test scenarios: the single source of truth for the generated test PDFs, the manual test
document (docs/TESTING.md) and tests/test_scenarios.py.

Each scenario overrides a strong personal-loan baseline (see helpers.make_app). `expect` lists what the
assessment must produce; keys: decision, route, method, amount, band, ko (knockout codes, exact set, default
none), ex (exception codes that must appear), clauses (policy clause ids that must be cited by a finding),
condition (substring that must appear in a condition), error (substring of the rejection).
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    purpose: str  # what the case proves
    overrides: dict = field(default_factory=dict)
    expect: dict = field(default_factory=dict)


HOME = dict(loan_type="Home Loan", annual_income=150_000, monthly_debt_payments=0, savings_balance=60_000,
            term_months=300, purpose="Home purchase")

SCENARIOS = [
    Scenario("TC-01", "Strong personal loan", "Happy path: low risk, no exceptions",
             {}, dict(decision="APPROVED", route="personal", method="declared", amount=20_000)),
    Scenario("TC-02", "DTI between 43% and 50%", "Amount is cut to the affordable maximum (GCP-3.2, GCP-3.3)",
             dict(annual_income=60_000, monthly_debt_payments=1_200, loan_amount=30_000, term_months=36),
             dict(decision="CONDITIONAL", ex=["DTI"], condition="reduced")),
    Scenario("TC-03", "DTI above 50%", "Automatic decline (GCP-3.2)",
             dict(annual_income=60_000, monthly_debt_payments=2_500, loan_amount=30_000, term_months=36),
             dict(decision="DECLINED", ko=["DTI"], clauses=["GCP-3.2"])),
    Scenario("TC-04", "Applicant under 21", "Age knockout (GCP-1.1)",
             dict(age=19), dict(decision="DECLINED", ko=["AGE"], clauses=["GCP-1.1"])),
    Scenario("TC-05", "Credit score below 600", "General score floor (GCP-2.2)",
             dict(credit_score=590), dict(decision="DECLINED", ko=["SCORE"], clauses=["GCP-2.2"])),
    Scenario("TC-06", "Personal loan score 610", "Product floor of 620 is above the general floor (PL-2.2)",
             dict(credit_score=610), dict(decision="DECLINED", ko=["SCORE"], clauses=["PL-2.2"])),
    Scenario("TC-07", "Three delinquencies", "Automatic decline (GCP-4.2)",
             dict(delinquencies_24m=3), dict(decision="DECLINED", ko=["DELINQUENCY"], clauses=["GCP-4.2"])),
    Scenario("TC-08", "One delinquency", "Conditional approval with an explanation condition (GCP-4.2)",
             dict(delinquencies_24m=1), dict(decision="CONDITIONAL", ex=["DELINQUENCY"], condition="GCP-4.2")),
    Scenario("TC-09", "Personal loan above 50% of income", "Amount reduced to 50% of income (PL-1.2)",
             dict(annual_income=50_000, loan_amount=30_000),
             dict(decision="CONDITIONAL", ex=["INCOME_MULTIPLE"], clauses=["PL-1.2"], amount=25_000)),
    Scenario("TC-10", "Home loan at 85% LTV", "Mortgage insurance condition, amount unchanged (HL-3.2)",
             dict(**HOME, asset_value=400_000, loan_amount=340_000),
             dict(decision="CONDITIONAL", route="home", ex=["LTV"], amount=340_000, condition="mortgage insurance")),
    Scenario("TC-11", "Home loan at 95% LTV", "LTV above 90% is an automatic decline (HL-3.2)",
             dict(**HOME, asset_value=400_000, loan_amount=380_000),
             dict(decision="DECLINED", route="home", ko=["LTV"], clauses=["HL-3.2"])),
    Scenario("TC-12", "Auto loan at 95% LTV", "Amount reduced to 90% of vehicle price (AL-3.2)",
             dict(loan_type="Auto Loan", asset_value=40_000, loan_amount=38_000, annual_income=100_000,
                  term_months=60, purpose="New car purchase"),
             dict(decision="CONDITIONAL", route="auto", ex=["LTV"], amount=36_000)),
    Scenario("TC-13", "Strong home loan", "Happy path on the home route",
             dict(**HOME, asset_value=500_000, loan_amount=350_000),
             dict(decision="APPROVED", route="home", amount=350_000)),
    Scenario("TC-14", "Strong auto loan", "Happy path on the auto route",
             dict(loan_type="Auto Loan", asset_value=40_000, loan_amount=28_000, annual_income=100_000,
                  term_months=60, purpose="New car purchase"),
             dict(decision="APPROVED", route="auto", amount=28_000)),
    Scenario("TC-15", "Six months in current job", "Tenure exception needs income verification (GCP-1.2)",
             dict(years_employed=0.5), dict(decision="CONDITIONAL", ex=["TENURE"], condition="verification")),
    Scenario("TC-16", "Unrecognised loan type, purpose says car", "Router infers the Auto route from the purpose",
             dict(loan_type="Loan", purpose="Buying a car", asset_value=30_000, loan_amount=20_000, term_months=60),
             dict(decision="APPROVED", route="auto", method="inferred")),
    Scenario("TC-19", "Medium risk band, no exceptions", "Band alone triggers conditional approval with officer review (GCP-6.3)",
             dict(credit_score=660, credit_utilization=70, annual_income=90_000, monthly_debt_payments=2_450,
                  savings_balance=2_200, years_employed=3),
             dict(decision="CONDITIONAL", band="MEDIUM", condition="credit officer review")),
    Scenario("TC-20", "High risk band, no knockouts", "Band alone triggers a decline (GCP-6.3)",
             dict(credit_score=620, credit_utilization=78, annual_income=60_000, monthly_debt_payments=1_350,
                  savings_balance=800, years_employed=0.5, delinquencies_24m=2, loan_amount=30_000, term_months=36),
             dict(decision="DECLINED", band="HIGH")),
    Scenario("TC-17", "Cannot be routed", "Loan type and purpose match no product: rejected with a clear message",
             dict(loan_type="Loan", purpose="Something else"), dict(error="Cannot route")),
    Scenario("TC-18", "Home loan without collateral value", "Secured products must state the collateral value",
             dict(**HOME, asset_value=None, loan_amount=340_000), dict(error="collateral value")),
]
SCENARIOS.sort(key=lambda s: s.id)
