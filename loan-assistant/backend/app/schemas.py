"""Pydantic models shared by the agents, orchestrator and API."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

Decision = Literal["APPROVED", "CONDITIONAL", "DECLINED"]
RiskBand = Literal["LOW", "MEDIUM", "HIGH"]
Source = Literal["ollama", "template"]


class LoanApplication(BaseModel):
    application_id: str
    customer_id: str
    full_name: str
    age: int = Field(ge=16, le=110)
    employment_type: Literal["Salaried", "Self-employed"]
    years_employed: float = Field(ge=0, le=60)
    annual_income: float = Field(gt=0)
    monthly_debt_payments: float = Field(ge=0)
    savings_balance: float = Field(ge=0)
    credit_score: int = Field(ge=300, le=850)
    credit_utilization: float = Field(ge=0, le=100)
    delinquencies_24m: int = Field(ge=0)
    loan_type: str
    loan_amount: float = Field(gt=0)
    term_months: int = Field(gt=0)
    purpose: str = ""
    asset_value: Optional[float] = Field(default=None, gt=0)


class PolicyRef(BaseModel):
    id: str
    doc: str
    text: str
    score: Optional[float] = None


class RouteDecision(BaseModel):
    loan_type: Literal["personal", "home", "auto"]
    product_name: str
    method: Literal["declared", "inferred"]
    reason: str
    policy_docs: list[str]


class FinancialAnalysis(BaseModel):
    monthly_income: float
    credit_tier: str
    indicative_apr: float
    proposed_emi: float
    existing_dti: float
    post_loan_dti: float
    loan_to_income: float
    ltv: Optional[float]
    savings_coverage: float
    disposable_income: float
    max_affordable_amount: float
    summary: str
    summary_source: Source
    policy_refs: list[PolicyRef]


class RiskFactor(BaseModel):
    name: str
    display_value: str
    points: int
    max_points: int
    level: Literal["low", "moderate", "high"]
    clause: str
    note: str


class Finding(BaseModel):
    code: str
    clause: str
    message: str
    remedy: str


class RiskAssessment(BaseModel):
    score: int
    band: RiskBand
    factors: list[RiskFactor]
    knockouts: list[Finding]
    exceptions: list[Finding]
    explanation: str
    explanation_source: Source
    policy_refs: list[PolicyRef]


class Recommendation(BaseModel):
    decision: Decision
    headline: str
    recommended_amount: Optional[float]
    recommended_term_months: Optional[int]
    indicative_apr: Optional[float]
    monthly_installment: Optional[float]
    post_loan_dti: Optional[float]
    conditions: list[str]
    reasons: list[str]
    rationale: str
    rationale_source: Source
    policy_refs: list[PolicyRef]


class TraceStep(BaseModel):
    step: str
    agent: str
    status: Literal["completed", "failed"]
    duration_ms: int
    detail: str


class AssessmentResult(BaseModel):
    application: LoanApplication
    route: RouteDecision
    financial: FinancialAnalysis
    risk: RiskAssessment
    recommendation: Recommendation
    trace: list[TraceStep]
    llm_mode: Source


class GenerateRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=50)
    replace: bool = False
