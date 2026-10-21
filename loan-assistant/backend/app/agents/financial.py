"""Financial Analysis Agent: affordability metrics and the loan summary."""
from ..rules import (
    DTI_STANDARD,
    credit_tier,
    indicative_apr,
    monthly_installment,
    principal_for_installment,
)
from ..schemas import FinancialAnalysis
from .base import BaseAgent, PipelineContext


def money(value: float) -> str:
    return f"${value:,.0f}"


class FinancialAnalysisAgent(BaseAgent):
    name = "Financial Analysis Agent"
    step = "Financial analysis"

    def run(self, ctx: PipelineContext) -> FinancialAnalysis:
        app, product = ctx.application, ctx.product
        monthly_income = app.annual_income / 12
        tier, _ = credit_tier(app.credit_score)
        apr = indicative_apr(product, app.credit_score)
        emi = monthly_installment(app.loan_amount, apr, app.term_months)
        existing_dti = app.monthly_debt_payments / monthly_income
        post_dti = (app.monthly_debt_payments + emi) / monthly_income
        headroom = DTI_STANDARD * monthly_income - app.monthly_debt_payments
        max_affordable = principal_for_installment(max(headroom, 0), apr, app.term_months)
        ltv = app.loan_amount / app.asset_value if app.asset_value else None

        metrics = {
            "monthly_income": round(monthly_income, 2),
            "credit_tier": tier,
            "indicative_apr": apr,
            "proposed_emi": round(emi, 2),
            "existing_dti": round(existing_dti, 4),
            "post_loan_dti": round(post_dti, 4),
            "loan_to_income": round(app.loan_amount / app.annual_income, 4),
            "ltv": round(ltv, 4) if ltv is not None else None,
            "savings_coverage": round(app.savings_balance / emi, 2),
            "disposable_income": round(monthly_income - app.monthly_debt_payments - emi, 2),
            "max_affordable_amount": round(max_affordable, 2),
        }

        asset = f", against collateral valued at {money(app.asset_value)} (LTV {ltv:.0%})" if ltv is not None else ""
        fallback = (
            f"{app.full_name} ({app.age}, {app.employment_type.lower()}, {app.years_employed:g} yrs in role) requests a "
            f"{money(app.loan_amount)} {product.name.lower()} over {app.term_months} months"
            f"{' for ' + app.purpose.lower() if app.purpose else ''}{asset}. Gross monthly income is {money(monthly_income)} "
            f"with existing debt payments of {money(app.monthly_debt_payments)} (DTI {existing_dti:.1%}). At an indicative "
            f"{apr:.2%} ({tier} credit tier) the instalment would be {money(emi)}, taking post-loan DTI to {post_dti:.1%} "
            f"[GCP-3.1]. Savings of {money(app.savings_balance)} cover {metrics['savings_coverage']:.1f} instalments "
            f"[GCP-5.1], leaving {money(metrics['disposable_income'])} of monthly income after obligations."
        )
        refs = self.evidence(
            ctx, "debt-to-income affordability instalment indicative rate",
            ["GCP-3.1", "GCP-5.1", product.rate_clause],
        )
        summary, source = self.narrator.narrate(
            "loan_summary", {"application": app.model_dump(), "route": product.name, "metrics": metrics}, refs, fallback
        )
        return FinancialAnalysis(**metrics, summary=summary, summary_source=source, policy_refs=refs)

    def describe(self, result: FinancialAnalysis) -> str:
        return (
            f"EMI {money(result.proposed_emi)} at {result.indicative_apr:.2%}; "
            f"post-loan DTI {result.post_loan_dti:.1%}"
        )
