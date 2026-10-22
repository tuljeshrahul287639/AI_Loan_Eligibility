"""Plain-English reasons for a loan decision. Written so an applicant can follow them without finance knowledge."""

from typing import Any, Dict, List, Optional

import config
from utils.money import rupees

# Same bands as agents/risk_agent.py: <=40 low, 41-60 medium, >60 high
LOW_RISK_SCORE = 40
HIGH_RISK_SCORE = 60


def _money(value: Any) -> str:
    return rupees(value)


def _percent(ratio: Optional[float]) -> str:
    return f"{ratio:.0%}" if ratio is not None else "unknown"


def explain_decision(
    application: Dict[str, Any],
    decision: str,
    financial_result: Optional[Dict[str, Any]],
    risk_result: Optional[Dict[str, Any]],
    policy_flags: List[str],
) -> List[str]:
    """Return one short sentence per reason. Used for approvals, reviews and rejections."""
    financial_result = financial_result or {}
    risk_result = risk_result or {}
    credit_score = application.get("credit_score", 0)
    income = application.get("monthly_income", 0)
    dti = financial_result.get("dti_with_loan")
    risk_score = risk_result.get("risk_score")

    if decision == "APPROVE":
        return [
            f"Credit score {credit_score} is above the minimum of {config.MIN_CREDIT_SCORE}.",
            f"Monthly income of {_money(income)} meets the minimum of {_money(config.MIN_MONTHLY_INCOME)}.",
            f"Debt after this loan is {_percent(dti)} of income, within the {_percent(config.MAX_DTI_RATIO)} limit.",
            f"Risk score is {risk_score:.0f}/100, which is low." if risk_score is not None else "Risk checks passed.",
        ]

    reasons: List[str] = []
    if decision == "REJECT":
        if dti is not None and dti > config.CRITICAL_DTI_RATIO:
            reasons.append(
                f"Debt after this loan would be {_percent(dti)} of income, "
                f"above the {_percent(config.CRITICAL_DTI_RATIO)} limit."
            )
        if risk_score is not None and risk_score > HIGH_RISK_SCORE:
            reasons.append(f"Risk score is {risk_score:.0f}/100, which is high.")
        if not reasons:
            reasons.append("The automated checks did not approve this application.")
        return reasons

    # REVIEW / ESCALATE: a person must look at it before a decision
    reasons.extend(policy_flags)
    if dti is not None and dti > config.MAX_DTI_RATIO:
        reasons.append(
            f"Debt after this loan is {_percent(dti)} of income, "
            f"above the {_percent(config.MAX_DTI_RATIO)} approval limit."
        )
    if risk_score is not None and risk_score > LOW_RISK_SCORE:
        reasons.append(f"Risk score is {risk_score:.0f}/100, which is medium risk.")
    if not reasons:
        reasons.append("The automated checks disagree, so a person must confirm the decision.")
    return reasons
