"""Quantitative thresholds from the lending policy documents in backend/policies.

Every constant here mirrors a clause (cited in the comment). Agents cite the clause id with each finding.
"""
from dataclasses import dataclass
from typing import Optional

# GCP-1.1
AGE_MIN, AGE_MAX = 21, 65
# GCP-2.2
SCORE_FLOOR = 600
# GCP-3.1 / GCP-3.2
DTI_STANDARD, DTI_MAX = 0.43, 0.50
# GCP-6.2
RISK_LOW_MAX, RISK_MEDIUM_MAX = 35, 60
# GCP-5.1
SAVINGS_TARGET_MONTHS, SAVINGS_FLOOR_MONTHS = 2.0, 1.0

# GCP-2.1 and GCP-7.1: (minimum score, tier, rate adjustment)
CREDIT_TIERS = [
    (750, "Excellent", 0.000),
    (700, "Good", 0.010),
    (650, "Fair", 0.025),
    (600, "Weak", 0.045),
    (0, "Poor", 0.070),
]


@dataclass(frozen=True)
class ProductRules:
    key: str
    name: str
    doc_id: str
    base_rate: float
    min_amount: float
    max_amount: float
    min_term: int
    max_term: int
    min_income: float
    min_score: int
    tenure_salaried: float
    tenure_self_employed: float
    limits_clause: str
    income_clause: str
    score_clause: str
    tenure_clause: str
    rate_clause: str
    ltv_standard: Optional[float] = None
    ltv_max: Optional[float] = None
    ltv_clause: Optional[str] = None
    max_income_multiple: Optional[float] = None
    income_multiple_clause: Optional[str] = None


PRODUCTS = {
    "personal": ProductRules(
        key="personal", name="Personal Loan", doc_id="personal_loan_policy", base_rate=0.11,
        min_amount=2_000, max_amount=75_000, min_term=12, max_term=84,
        min_income=30_000, min_score=620, tenure_salaried=1, tenure_self_employed=2,
        limits_clause="PL-1.1", income_clause="PL-2.1", score_clause="PL-2.2",
        tenure_clause="GCP-1.2", rate_clause="PL-3.1",
        max_income_multiple=0.5, income_multiple_clause="PL-1.2",
    ),
    "home": ProductRules(
        key="home", name="Home Loan", doc_id="home_loan_policy", base_rate=0.065,
        min_amount=50_000, max_amount=1_000_000, min_term=120, max_term=360,
        min_income=40_000, min_score=650, tenure_salaried=2, tenure_self_employed=2,
        limits_clause="HL-1.1", income_clause="HL-2.3", score_clause="HL-2.1",
        tenure_clause="HL-2.2", rate_clause="HL-4.1",
        ltv_standard=0.80, ltv_max=0.90, ltv_clause="HL-3.2",
    ),
    "auto": ProductRules(
        key="auto", name="Auto Loan", doc_id="auto_loan_policy", base_rate=0.075,
        min_amount=5_000, max_amount=100_000, min_term=24, max_term=84,
        min_income=24_000, min_score=600, tenure_salaried=1, tenure_self_employed=2,
        limits_clause="AL-1.1", income_clause="AL-2.2", score_clause="AL-2.1",
        tenure_clause="GCP-1.2", rate_clause="AL-4.1",
        ltv_standard=0.90, ltv_max=1.00, ltv_clause="AL-3.2",
    ),
}


def credit_tier(score: int) -> tuple[str, float]:
    for floor, name, adj in CREDIT_TIERS:
        if score >= floor:
            return name, adj
    return "Poor", 0.070


def indicative_apr(product: ProductRules, score: int) -> float:
    return round(product.base_rate + credit_tier(score)[1], 4)


def monthly_installment(principal: float, apr: float, months: int) -> float:
    r = apr / 12
    if r == 0:
        return principal / months
    return principal * r / (1 - (1 + r) ** -months)


def principal_for_installment(installment: float, apr: float, months: int) -> float:
    if installment <= 0:
        return 0.0
    r = apr / 12
    if r == 0:
        return installment * months
    return installment * (1 - (1 + r) ** -months) / r


def required_tenure(product: ProductRules, employment_type: str) -> float:
    return product.tenure_self_employed if employment_type == "Self-employed" else product.tenure_salaried
