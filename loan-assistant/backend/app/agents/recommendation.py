"""Recommendation Agent: eligibility decision, recommended terms and conditions."""
import math

from .. import rules
from ..schemas import Recommendation
from .base import BaseAgent, PipelineContext
from .financial import money


def _upper(text: str) -> str:
    return text[:1].upper() + text[1:]


class RecommendationAgent(BaseAgent):
    name = "Recommendation Agent"
    step = "Eligibility recommendation"

    def run(self, ctx: PipelineContext) -> Recommendation:
        app, p, fin, risk = ctx.application, ctx.product, ctx.financial, ctx.risk
        codes = {x.code for x in risk.exceptions}

        # GCP-6.3: decision mapping
        if risk.knockouts or risk.band == "HIGH":
            decision = "DECLINED"
        elif risk.band == "MEDIUM" or risk.exceptions:
            decision = "CONDITIONAL"
        else:
            decision = "APPROVED"

        amount = term = apr = emi = dti = None
        conditions: list[str] = []
        reasons: list[str] = []

        if decision != "DECLINED":
            amount = self._recommended_amount(ctx, codes)
            if amount < p.min_amount:
                decision = "DECLINED"
                amount = None
                reasons.append(
                    f"The most that fits within the 43% DTI limit ({money(fin.max_affordable_amount)}) is below the "
                    f"{money(p.min_amount)} product minimum [GCP-3.3, {p.limits_clause}]."
                )

        if decision == "DECLINED":
            for k in risk.knockouts:
                reasons.append(f"{_upper(k.message)} [{k.clause}]. {k.remedy}")
            if not risk.knockouts and not reasons:
                reasons.append(f"Risk score {risk.score}/100 is in the HIGH band [GCP-6.2]; the combined risk factors are outside appetite.")
        else:
            term = app.term_months
            apr = fin.indicative_apr
            if amount == app.loan_amount:
                emi, dti = fin.proposed_emi, fin.post_loan_dti
            else:
                emi = round(rules.monthly_installment(amount, apr, term), 2)
                dti = round((app.monthly_debt_payments + emi) / fin.monthly_income, 4)

            if amount < app.loan_amount:
                conditions.append(f"Loan amount reduced from {money(app.loan_amount)} to {money(amount)}.")
            for x in risk.exceptions:
                if x.code in {"DTI", "INCOME_MULTIPLE"} or (x.code == "LTV" and p.key == "auto"):
                    continue  # covered by the amount reduction above
                conditions.append(f"{x.remedy} [{x.clause}]")
            if risk.band == "MEDIUM" and not conditions:
                conditions.append("Refer for credit officer review before disbursal because the composite risk score is in the MEDIUM band [GCP-6.3].")

            if decision == "APPROVED":
                reasons.append(f"Risk score {risk.score}/100 is in the LOW band with no policy exceptions [GCP-6.3].")
                reasons.append(f"Post-loan DTI {fin.post_loan_dti:.1%} is within the 43% standard limit [GCP-3.1].")
            else:
                reasons.append(f"Risk score {risk.score}/100 ({risk.band}) with {len(risk.exceptions)} policy exception(s); approvable only with conditions [GCP-6.3].")
                for x in risk.exceptions:
                    reasons.append(f"{_upper(x.message)} [{x.clause}].")

        headline = {
            "APPROVED": f"Approve {money(amount or 0)} {p.name.lower()}",
            "CONDITIONAL": f"Approve {money(amount or 0)} {p.name.lower()} with conditions",
            "DECLINED": f"Decline the {p.name.lower()} request",
        }[decision]

        cited = [x.clause for x in risk.knockouts + risk.exceptions] + ["GCP-6.3"]
        refs = [self.policies.ref(cid) for cid in dict.fromkeys(cited)]

        fallback = f"{headline}. " + " ".join(reasons)
        if conditions:
            fallback += " Conditions: " + " ".join(conditions)
        if emi:
            fallback += f" Recommended terms: {money(amount)} over {term} months at an indicative {apr:.2%}, instalment {money(emi)}, post-loan DTI {dti:.1%}."

        facts = {
            "decision": decision, "headline": headline, "recommended_amount": amount, "term_months": term,
            "indicative_apr": apr, "monthly_installment": emi, "post_loan_dti": dti,
            "conditions": conditions, "reasons": reasons, "risk_score": risk.score, "risk_band": risk.band,
        }
        rationale, source = self.narrator.narrate("recommendation", facts, refs, fallback)
        return Recommendation(
            decision=decision, headline=headline, recommended_amount=amount, recommended_term_months=term,
            indicative_apr=apr, monthly_installment=emi, post_loan_dti=dti, conditions=conditions, reasons=reasons,
            rationale=rationale, rationale_source=source, policy_refs=refs,
        )

    @staticmethod
    def _recommended_amount(ctx: PipelineContext, codes: set[str]) -> float:
        """Requested amount, reduced where an exception requires it (GCP-3.3, PL-1.2, AL-3.2)."""
        app, p, fin = ctx.application, ctx.product, ctx.financial
        amount = app.loan_amount
        if "DTI" in codes:
            amount = min(amount, fin.max_affordable_amount)
        if "INCOME_MULTIPLE" in codes:
            amount = min(amount, p.max_income_multiple * app.annual_income)
        if "LTV" in codes and p.key == "auto":
            amount = min(amount, p.ltv_standard * app.asset_value)
        if amount < app.loan_amount:
            amount = math.floor(amount / 10) * 10  # round down so the limit is never exceeded
        return amount

    def describe(self, result: Recommendation) -> str:
        return result.headline
