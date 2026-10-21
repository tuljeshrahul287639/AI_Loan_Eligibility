"""Risk Agent: composite risk score, policy knockouts/exceptions and the risk explanation."""
from .. import rules
from ..schemas import Finding, RiskAssessment, RiskFactor
from .base import BaseAgent, PipelineContext


def _level(points: int, max_points: int) -> str:
    ratio = points / max_points
    return "low" if ratio <= 0.25 else "moderate" if ratio <= 0.6 else "high"


def _band(score: int) -> str:
    if score <= rules.RISK_LOW_MAX:
        return "LOW"
    return "MEDIUM" if score <= rules.RISK_MEDIUM_MAX else "HIGH"


def _step(value: float, steps: list[tuple[float, int]], above: int) -> int:
    """Points for the first threshold the value does not exceed, else `above`."""
    for limit, pts in steps:
        if value <= limit:
            return pts
    return above


class RiskAgent(BaseAgent):
    name = "Risk Agent"
    step = "Risk assessment"

    def run(self, ctx: PipelineContext) -> RiskAssessment:
        factors = self._factors(ctx)
        score = sum(f.points for f in factors)
        knockouts, exceptions = self._findings(ctx)

        cited = [f.clause for f in factors if f.points] + [x.clause for x in knockouts + exceptions] + ["GCP-6.1", "GCP-6.2"]
        refs = self.evidence(ctx, "risk score credit behaviour delinquency utilization", cited, k=1)

        drivers = sorted((f for f in factors if f.points), key=lambda f: -f.points)[:3]
        parts = [f"Composite risk score is {score}/100 ({_band(score)} risk) [GCP-6.2]."]
        if drivers:
            parts.append("Main drivers: " + "; ".join(f"{f.name} ({f.display_value}, +{f.points}) [{f.clause}]" for f in drivers) + ".")
        else:
            parts.append("No factor adds risk points.")
        if knockouts:
            parts.append("Automatic-decline rules triggered: " + "; ".join(f"{k.message} [{k.clause}]" for k in knockouts) + ".")
        if exceptions:
            parts.append(("Other policy exceptions: " if knockouts else "Policy exceptions needing conditions: ") + "; ".join(f"{x.message} [{x.clause}]" for x in exceptions) + ".")
        if not knockouts and not exceptions:
            parts.append("No policy knockouts or exceptions were found.")
        fallback = " ".join(parts)

        facts = {
            "risk_score": score,
            "band": _band(score),
            "factors": [f.model_dump() for f in factors],
            "knockouts": [k.model_dump() for k in knockouts],
            "exceptions": [x.model_dump() for x in exceptions],
        }
        explanation, source = self.narrator.narrate("risk_explanation", facts, refs, fallback)
        return RiskAssessment(
            score=score, band=_band(score), factors=factors, knockouts=knockouts, exceptions=exceptions,
            explanation=explanation, explanation_source=source, policy_refs=refs,
        )

    def describe(self, result: RiskAssessment) -> str:
        return (
            f"Risk {result.score}/100 ({result.band}); "
            f"{len(result.knockouts)} knockout(s), {len(result.exceptions)} exception(s)"
        )

    # -- scoring -----------------------------------------------------------------------------------------

    def _factors(self, ctx: PipelineContext) -> list[RiskFactor]:
        app, product, fin = ctx.application, ctx.product, ctx.financial

        def factor(name, display, points, max_points, clause, note):
            return RiskFactor(
                name=name, display_value=display, points=points, max_points=max_points,
                level=_level(points, max_points), clause=clause, note=note,
            )

        tier, _ = rules.credit_tier(app.credit_score)
        score_pts = {"Excellent": 0, "Good": 6, "Fair": 13, "Weak": 20, "Poor": 25}[tier]
        dti_pts = _step(fin.post_loan_dti, [(0.20, 0), (0.30, 5), (0.36, 10), (0.43, 15), (0.50, 21)], 25)
        util_pts = _step(app.credit_utilization, [(30, 0), (50, 3), (80, 7)], 10)
        delinq_pts = {0: 0, 1: 7, 2: 11}.get(app.delinquencies_24m, 15)
        need = rules.required_tenure(product, app.employment_type)
        tenure_pts = 10 if app.years_employed < need else 4 if app.years_employed < need + 2 else 2 if app.years_employed < 5 else 0
        cover_pts = 10 if fin.savings_coverage < rules.SAVINGS_FLOOR_MONTHS else 7 if fin.savings_coverage < 2 else 3 if fin.savings_coverage < 6 else 0

        out = [
            factor("Credit score", f"{app.credit_score} ({tier})", score_pts, 25, "GCP-2.1", "Bureau score tier."),
            factor("Post-loan DTI", f"{fin.post_loan_dti:.1%}", dti_pts, 25, "GCP-3.1", "Existing debt plus proposed instalment vs income; standard limit is 43%."),
            factor("Credit utilization", f"{app.credit_utilization:.0f}%", util_pts, 10, "GCP-4.1", "Revolving balances vs limits."),
            factor("Delinquencies (24m)", str(app.delinquencies_24m), delinq_pts, 15, "GCP-4.2", "Payments 30+ days past due."),
            factor("Employment stability", f"{app.years_employed:g} yrs (need {need:g})", tenure_pts, 10,
                   product.tenure_clause, "Tenure vs product requirement."),
            factor("Liquidity", f"{fin.savings_coverage:.1f}x instalment", cover_pts, 10, "GCP-5.1", "Savings as multiples of the proposed instalment; target is 2x."),
        ]
        if fin.ltv is None:
            out.append(factor("Collateral exposure", "Unsecured", 3, 5, product.limits_clause, "Unsecured lending carries a fixed exposure charge."))
        else:
            ltv_pts = _step(fin.ltv, [(0.60, 0), (0.80, 2), (0.90, 4)], 5)
            out.append(factor("Collateral exposure", f"LTV {fin.ltv:.1%}", ltv_pts, 5, product.ltv_clause, "Loan vs collateral value."))
        return out

    # -- policy rules ------------------------------------------------------------------------------------

    def _findings(self, ctx: PipelineContext) -> tuple[list[Finding], list[Finding]]:
        app, p, fin = ctx.application, ctx.product, ctx.financial
        ko: list[Finding] = []
        ex: list[Finding] = []

        if not rules.AGE_MIN <= app.age <= rules.AGE_MAX:
            ko.append(Finding(code="AGE", clause="GCP-1.1", message=f"age {app.age} is outside {rules.AGE_MIN}-{rules.AGE_MAX}",
                              remedy="Applicant must be between 21 and 65."))
        if not p.min_amount <= app.loan_amount <= p.max_amount or not p.min_term <= app.term_months <= p.max_term:
            ko.append(Finding(code="LIMITS", clause=p.limits_clause,
                              message=f"requested ${app.loan_amount:,.0f} over {app.term_months} months is outside product limits "
                                      f"(${p.min_amount:,.0f}-${p.max_amount:,.0f}, {p.min_term}-{p.max_term} months)",
                              remedy="Resubmit within the product amount and term limits."))
        if app.annual_income < p.min_income:
            ko.append(Finding(code="INCOME", clause=p.income_clause,
                              message=f"annual income ${app.annual_income:,.0f} is below the ${p.min_income:,.0f} minimum",
                              remedy=f"Minimum gross annual income is ${p.min_income:,.0f}."))
        floor = max(rules.SCORE_FLOOR, p.min_score)
        if app.credit_score < floor:
            ko.append(Finding(code="SCORE", clause="GCP-2.2" if app.credit_score < rules.SCORE_FLOOR else p.score_clause,
                              message=f"credit score {app.credit_score} is below the {floor} minimum",
                              remedy=f"Credit score must reach at least {floor}."))
        if fin.post_loan_dti > rules.DTI_MAX:
            ko.append(Finding(code="DTI", clause="GCP-3.2", message=f"post-loan DTI {fin.post_loan_dti:.1%} exceeds 50%",
                              remedy="Reduce existing debt or the requested amount so post-loan DTI is at most 43%."))
        if app.delinquencies_24m >= 3:
            ko.append(Finding(code="DELINQUENCY", clause="GCP-4.2", message=f"{app.delinquencies_24m} delinquencies in 24 months",
                              remedy="Fewer than 3 delinquencies in the last 24 months are required."))
        if p.ltv_max and fin.ltv is not None and fin.ltv > p.ltv_max:
            ko.append(Finding(code="LTV", clause=p.ltv_clause, message=f"LTV {fin.ltv:.1%} exceeds the {p.ltv_max:.0%} maximum",
                              remedy=f"Increase the down payment so LTV is at most {p.ltv_max:.0%}."))
        if p.key == "personal" and app.credit_utilization > 80 and app.delinquencies_24m >= 1:
            ko.append(Finding(code="UTIL_DELINQ", clause="PL-4.1",
                              message="utilization above 80% combined with a delinquency on an unsecured loan",
                              remedy="Reduce revolving balances and clear delinquencies before reapplying."))

        if rules.DTI_STANDARD < fin.post_loan_dti <= rules.DTI_MAX:
            ex.append(Finding(code="DTI", clause="GCP-3.2", message=f"post-loan DTI {fin.post_loan_dti:.1%} is above the 43% standard limit",
                              remedy=f"Reduce the amount to about ${fin.max_affordable_amount:,.0f} or extend the term."))
        need = rules.required_tenure(p, app.employment_type)
        if app.years_employed < need:
            ex.append(Finding(code="TENURE", clause=p.tenure_clause,
                              message=f"{app.years_employed:g} years of {'trading history' if app.employment_type == 'Self-employed' else 'employment'} is below the {need:g}-year requirement",
                              remedy="Provide additional income and employment verification."))
        if app.credit_utilization > 80:
            ex.append(Finding(code="UTILIZATION", clause="PL-4.1" if p.key == "personal" else "GCP-4.1",
                              message=f"credit utilization {app.credit_utilization:.0f}% is above 80%",
                              remedy="Reduce revolving balances below 80% of limits."))
        if 1 <= app.delinquencies_24m <= 2:
            ex.append(Finding(code="DELINQUENCY", clause="GCP-4.2", message=f"{app.delinquencies_24m} delinquenc{'y' if app.delinquencies_24m == 1 else 'ies'} in the last 24 months",
                              remedy="Provide a written explanation and evidence of the account being brought current."))
        if fin.savings_coverage < rules.SAVINGS_TARGET_MONTHS:
            ex.append(Finding(code="LIQUIDITY", clause="GCP-5.1", message=f"savings cover only {fin.savings_coverage:.1f}x the instalment (target 2x)",
                              remedy="Demonstrate liquid reserves of at least 2x the monthly instalment."))
        if p.ltv_standard and fin.ltv is not None and p.ltv_standard < fin.ltv <= (p.ltv_max or 1):
            remedy = ("Obtain mortgage insurance." if p.key == "home"
                      else f"Add down payment so the loan is at most ${p.ltv_standard * app.asset_value:,.0f} ({p.ltv_standard:.0%} of vehicle price).")
            ex.append(Finding(code="LTV", clause=p.ltv_clause, message=f"LTV {fin.ltv:.1%} is above the {p.ltv_standard:.0%} standard", remedy=remedy))
        if p.max_income_multiple and app.loan_amount > p.max_income_multiple * app.annual_income:
            ex.append(Finding(code="INCOME_MULTIPLE", clause=p.income_multiple_clause,
                              message=f"amount is {app.loan_amount / app.annual_income:.0%} of annual income (limit {p.max_income_multiple:.0%})",
                              remedy=f"Reduce the amount to ${p.max_income_multiple * app.annual_income:,.0f}."))
        return ko, ex
