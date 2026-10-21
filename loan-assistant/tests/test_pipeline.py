import re
from pathlib import Path

import pytest

from app.generator import generate_applications
from app.llm import Narrator
from app.orchestrator import AssessmentOrchestrator
from app.pdf_tools import ApplicationParseError, parse_pdf, render_pdf
from app.policy_store import PolicyStore
from app.routing import LoanRouter, RoutingError
from helpers import make_app

APP_DIR = Path(__file__).resolve().parent.parent / "backend" / "app"
policies = PolicyStore()
orchestrator = AssessmentOrchestrator(policies, Narrator())


def assess(**overrides):
    return orchestrator.assess(make_app(**overrides))


# ---------- policy knowledge base ----------

def test_every_clause_cited_in_code_exists_in_policy_documents():
    cited = set()
    for path in APP_DIR.rglob("*.py"):
        cited |= set(re.findall(r"\b(?:GCP|PL|HL|AL)-\d+\.\d+\b", path.read_text(encoding="utf8")))
    assert cited
    assert cited <= set(policies.clauses), cited - set(policies.clauses)


def test_retrieval_finds_relevant_clause_and_respects_document_scope():
    top = policies.retrieve("loan to value mortgage insurance", ["general_credit_policy", "home_loan_policy"], k=1)[0]
    assert top.id == "HL-3.2"
    only_auto = policies.retrieve("loan to value", ["auto_loan_policy"], k=5)
    assert only_auto and all(r.id.startswith("AL-") for r in only_auto)


# ---------- PDF intake ----------

def test_generated_applications_survive_pdf_round_trip():
    for app in generate_applications(30, seed=3):
        assert parse_pdf(render_pdf(app)) == app


def test_pdf_missing_fields_and_non_pdf_are_rejected():
    with pytest.raises(ApplicationParseError):
        parse_pdf(b"%PDF-1.4 not really a pdf")
    from reportlab.pdfgen import canvas
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 700, "Full Name: Only A. Name")
    c.save()
    with pytest.raises(ApplicationParseError, match="missing required"):
        parse_pdf(buf.getvalue())


# ---------- router ----------

def test_router_declared_and_inferred_routes():
    router = LoanRouter()
    route, product = router.route(make_app(loan_type="Home Loan"))
    assert (route.loan_type, route.method, product.key) == ("home", "declared", "home")
    assert route.policy_docs == ["general_credit_policy", "home_loan_policy"]
    route, _ = router.route(make_app(loan_type="Loan", purpose="Buying a car"))
    assert (route.loan_type, route.method) == ("auto", "inferred")
    with pytest.raises(RoutingError):
        router.route(make_app(loan_type="Loan", purpose="Something else"))


def test_home_loan_requires_collateral_value():
    with pytest.raises(ValueError, match="collateral"):
        assess(loan_type="Home Loan", loan_amount=200_000, term_months=300, asset_value=None)


# ---------- decisions ----------

def test_strong_applicant_is_approved_as_requested():
    r = assess()
    rec = r.recommendation
    assert rec.decision == "APPROVED" and r.risk.band == "LOW" and not r.risk.exceptions
    assert rec.recommended_amount == 20_000 and rec.conditions == []
    assert [s.step for s in r.trace] == ["Route", "Financial analysis", "Risk assessment", "Eligibility recommendation"]
    assert all(s.status == "completed" for s in r.trace)


def test_dti_between_43_and_50_is_conditional_with_reduced_affordable_amount():
    r = assess(annual_income=60_000, monthly_debt_payments=1_200, loan_amount=30_000, term_months=36)
    rec = r.recommendation
    assert 0.43 < r.financial.post_loan_dti <= 0.50
    assert rec.decision == "CONDITIONAL"
    assert rec.recommended_amount < 30_000
    assert rec.post_loan_dti <= 0.43
    assert any("reduced" in c for c in rec.conditions)


def test_dti_above_50_is_declined():
    r = assess(annual_income=60_000, monthly_debt_payments=2_500, loan_amount=30_000, term_months=36)
    assert r.recommendation.decision == "DECLINED"
    assert any(k.code == "DTI" and k.clause == "GCP-3.2" for k in r.risk.knockouts)
    assert r.recommendation.recommended_amount is None


def test_age_and_credit_score_knockouts():
    young = assess(age=19)
    assert young.recommendation.decision == "DECLINED" and any(k.code == "AGE" for k in young.risk.knockouts)
    low = assess(credit_score=590)
    assert any(k.code == "SCORE" and k.clause == "GCP-2.2" for k in low.risk.knockouts)
    # personal loan floor is 620 (PL-2.2), above the general floor of 600
    mid = assess(credit_score=610)
    assert any(k.code == "SCORE" and k.clause == "PL-2.2" for k in mid.risk.knockouts)


def test_three_delinquencies_decline_and_one_is_conditional():
    assert assess(delinquencies_24m=3).recommendation.decision == "DECLINED"
    one = assess(delinquencies_24m=1)
    assert one.recommendation.decision == "CONDITIONAL"
    assert any("GCP-4.2" in c for c in one.recommendation.conditions)


def test_personal_loan_above_half_of_income_is_reduced_to_the_limit():
    r = assess(annual_income=50_000, loan_amount=30_000)
    assert r.recommendation.decision == "CONDITIONAL"
    assert r.recommendation.recommended_amount == 25_000


def test_home_loan_ltv_85_needs_mortgage_insurance_and_over_90_is_declined():
    kw = dict(loan_type="Home Loan", annual_income=150_000, savings_balance=60_000, term_months=300, purpose="Home purchase",
              monthly_debt_payments=0)
    ok = assess(asset_value=400_000, loan_amount=340_000, **kw)
    assert ok.recommendation.decision == "CONDITIONAL"
    assert ok.recommendation.recommended_amount == 340_000
    assert any("mortgage insurance" in c.lower() for c in ok.recommendation.conditions)
    bad = assess(asset_value=400_000, loan_amount=380_000, **kw)
    assert bad.recommendation.decision == "DECLINED" and any(k.code == "LTV" for k in bad.risk.knockouts)


def test_auto_loan_ltv_95_is_reduced_to_90_percent_of_price():
    r = assess(loan_type="Auto Loan", asset_value=40_000, loan_amount=38_000, annual_income=100_000, term_months=60,
               purpose="New car purchase")
    assert r.recommendation.decision == "CONDITIONAL"
    assert r.recommendation.recommended_amount == 36_000


def test_risk_score_is_bounded_and_factors_sum_to_it():
    for app in generate_applications(40, seed=11):
        r = orchestrator.assess(app)
        assert 0 <= r.risk.score <= 100
        assert r.risk.score == sum(f.points for f in r.risk.factors)
        assert r.risk.band == ("LOW" if r.risk.score <= 35 else "MEDIUM" if r.risk.score <= 60 else "HIGH")


def test_generated_batch_has_every_decision_outcome():
    decisions = {orchestrator.assess(a).recommendation.decision for a in generate_applications(60, seed=7)}
    assert decisions == {"APPROVED", "CONDITIONAL", "DECLINED"}


def test_conditional_recommendations_never_exceed_dti_limit():
    for app in generate_applications(60, seed=5):
        rec = orchestrator.assess(app).recommendation
        if rec.decision != "DECLINED":
            assert rec.post_loan_dti <= 0.50
            assert rec.recommended_amount <= app.loan_amount
