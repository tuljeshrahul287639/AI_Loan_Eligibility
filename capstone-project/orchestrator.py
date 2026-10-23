import time
import asyncio
from typing import Dict, Any, List, Optional
from agents.financial_agent import get_financial_agent
from agents.risk_agent import get_risk_agent
from agents.recommendation_agent import get_recommendation_agent
from utils.logging_setup import log_agent_decision
from utils.error_handler import validate_application_data
from utils.decision_explainer import explain_decision
from tools.financial_calculator import calculate_loan_payment
from utils.money import rupees
import config

# Status shown for each recorded step: PASS (green), FAIL (red), REVIEW (amber), INFO (grey)
RECOMMENDATION_STATUS = {"APPROVE": "PASS", "REVIEW": "REVIEW", "ESCALATE": "REVIEW", "REJECT": "FAIL"}
AGREEMENT_TEXT = {"STRONG": "agree strongly", "MODERATE": "partly agree", "CONFLICTING": "disagree"}


def _step(trace: List[dict], title: str, agent: str, status: str, explanation: str,
          inputs: Optional[dict] = None, outputs: Optional[dict] = None) -> None:
    """Record one thing the system did, in plain words, for the step-by-step view."""
    trace.append({
        "number": len(trace) + 1,
        "title": title,
        "agent": agent,
        "status": status,
        "explanation": explanation,
        "inputs": inputs or {},
        "outputs": outputs or {},
    })


def _applicant_inputs(application: Dict[str, Any]) -> Dict[str, str]:
    return {
        "Name": str(application.get("name", "")),
        "Monthly income": rupees(application.get('monthly_income', 0)),
        "Monthly expenses": rupees(application.get('monthly_expenses', 0)),
        "Existing monthly debts": rupees(application.get('existing_debts', 0)),
        "Credit score": str(application.get("credit_score", "")),
        "Loan amount": rupees(application.get('loan_amount', 0)),
        "Years employed": str(application.get("years_employed", "")),
        "Employment type": str(application.get("employment_type", "")),
    }


class LoanProcessingOrchestrator:
    def __init__(self):
        self.financial_agent = get_financial_agent()
        self.risk_agent = get_risk_agent()
        self.recommendation_agent = get_recommendation_agent()

    def process_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        trace: List[dict] = []

        try:
            # Step 1: Validate application
            if not validate_application_data(application):
                _step(trace, "Check the application form", "System", "FAIL",
                      "Some required fields are missing or outside the allowed range.",
                      inputs=_applicant_inputs(application))
                return self._rejection_result(application, "Invalid application data", trace)
            _step(trace, "Check the application form", "System", "PASS",
                  "All required fields are present and inside the allowed ranges.",
                  inputs=_applicant_inputs(application))

            # Step 2: Pre-screening (hard policy rules, checked before any agent runs)
            prescreen_rejection = self._prescreening(application, trace)
            if prescreen_rejection:
                return prescreen_rejection

            # Step 3: Run Financial & Risk Agents in parallel
            if config.PARALLEL_EXECUTION:
                financial_result, risk_result = asyncio.run(
                    self._run_agents_parallel(application)
                )
            else:
                financial_result = self.financial_agent.analyze(application)
                risk_result = self.risk_agent.analyze(application)

            self._record_financial(trace, financial_result)
            self._record_risk(trace, risk_result)

            # Step 4: Get recommendation
            recommendation = self.recommendation_agent.synthesize(
                application, financial_result, risk_result
            )
            self._record_recommendation(trace, recommendation)

            # Step 5: Policy flags. A file the agents would approve still goes to a human if a policy condition applies.
            decision = recommendation.get('final_recommendation')
            requires_approval = recommendation.get('requires_human_approval')
            policy_flags = self._policy_flags(application)
            if policy_flags and decision == 'APPROVE':
                decision = 'REVIEW'
                requires_approval = True
            _step(trace, "Policy conditions check", "Policy check",
                  "REVIEW" if policy_flags else "PASS",
                  "; ".join(policy_flags) if policy_flags else "No policy condition needs a human check.",
                  outputs={"Conditions found": str(len(policy_flags))})

            # Step 6: Plain-English reasons for approval, review or rejection
            reasons = explain_decision(application, decision, financial_result, risk_result, policy_flags)

            # Step 7: Final decision
            duration = time.time() - start_time
            _step(trace, "Final decision", "Final decision", RECOMMENDATION_STATUS.get(decision, "REVIEW"),
                  "\n".join(reasons), outputs={"Decision": decision})

            result = {
                'applicant_id': application.get('applicant_id'),
                'applicant_name': application.get('name'),
                'decision': decision,
                'status': 'APPROVED' if decision == 'APPROVE' else 'PENDING',
                'confidence_score': recommendation.get('confidence_score'),
                'requires_human_approval': requires_approval,
                'reason': "\n".join(reasons),
                'policy_flags': policy_flags,
                'workflow_duration_seconds': duration,
                'workflow_trace': trace,
                'financial_analysis': financial_result,
                'risk_analysis': risk_result,
                'recommendation_analysis': recommendation
            }

            log_agent_decision('FINAL_DECISION', result['decision'], result['confidence_score'])
            return result

        except Exception as e:
            return self._rejection_result(application, f"Error: {str(e)}", trace)

    async def _run_agents_parallel(self, application):
        """Run Financial & Risk agents in parallel"""
        loop = asyncio.get_event_loop()
        financial = loop.run_in_executor(None, self.financial_agent.analyze, application)
        risk = loop.run_in_executor(None, self.risk_agent.analyze, application)
        return await financial, await risk

    def _gate(self, application, trace, title, passed, pass_text, fail_text, inputs, limits):
        """Record one pre-screening check. Returns a rejection result when it fails, otherwise None."""
        _step(trace, title, "Pre-screen", "PASS" if passed else "FAIL",
              pass_text if passed else fail_text, inputs=inputs, outputs=limits)
        return None if passed else self._rejection_result(application, fail_text, trace)

    def _prescreening(self, application, trace):
        """Hard policy rejections, applied before any agent runs"""
        credit_score = application.get('credit_score', 0)
        income = application.get('monthly_income', 0)
        debts = application.get('existing_debts', 0)
        loan_amount = application.get('loan_amount', 0)

        rejection = self._gate(
            application, trace, "Credit score check",
            credit_score >= config.MIN_CREDIT_SCORE,
            f"Credit score {credit_score} meets the minimum of {config.MIN_CREDIT_SCORE}.",
            f"Credit score {credit_score} is below the minimum of {config.MIN_CREDIT_SCORE}.",
            {"Credit score": str(credit_score)}, {"Minimum allowed": str(config.MIN_CREDIT_SCORE)},
        )
        if rejection:
            return rejection

        rejection = self._gate(
            application, trace, "Income check",
            income >= config.MIN_MONTHLY_INCOME,
            f"Monthly income of {rupees(income)} meets the minimum of {rupees(config.MIN_MONTHLY_INCOME)}.",
            f"Monthly income of {rupees(income)} is below the minimum of {rupees(config.MIN_MONTHLY_INCOME)}.",
            {"Monthly income": rupees(income)}, {"Minimum allowed": rupees(config.MIN_MONTHLY_INCOME)},
        )
        if rejection:
            return rejection

        amount_ok = config.MIN_LOAN_AMOUNT <= loan_amount <= config.MAX_LOAN_AMOUNT
        rejection = self._gate(
            application, trace, "Loan amount check",
            amount_ok,
            f"Loan amount of {rupees(loan_amount)} is inside the allowed range.",
            f"Loan amount must be between {rupees(config.MIN_LOAN_AMOUNT)} and {rupees(config.MAX_LOAN_AMOUNT)}",
            {"Loan amount": rupees(loan_amount)},
            {"Allowed range": f"{rupees(config.MIN_LOAN_AMOUNT)} to {rupees(config.MAX_LOAN_AMOUNT)}"},
        )
        if rejection:
            return rejection

        rejection = self._gate(
            application, trace, "Loan compared with yearly income",
            loan_amount <= config.MAX_LOAN_TO_ANNUAL_INCOME * income * 12,
            f"Loan is within {config.MAX_LOAN_TO_ANNUAL_INCOME} times the yearly income.",
            f"Loan of {rupees(loan_amount)} is more than {config.MAX_LOAN_TO_ANNUAL_INCOME} times the yearly income.",
            {"Loan amount": rupees(loan_amount), "Yearly income": rupees(income * 12)},
            {"Maximum allowed": f"{config.MAX_LOAN_TO_ANNUAL_INCOME} x yearly income"},
        )
        if rejection:
            return rejection

        dti_with_loan = (debts + calculate_loan_payment(loan_amount)) / income
        rejection = self._gate(
            application, trace, "Debt after the loan check",
            dti_with_loan <= config.CRITICAL_DTI_RATIO,
            f"Debt after this loan would be {dti_with_loan:.0%} of income, under the {config.CRITICAL_DTI_RATIO:.0%} hard limit.",
            f"Debt after this loan would be {dti_with_loan:.0%} of income, above the {config.CRITICAL_DTI_RATIO:.0%} limit.",
            {"Existing debts": rupees(debts), "Monthly income": rupees(income)},
            {"Hard limit": f"{config.CRITICAL_DTI_RATIO:.0%}", "Debt after loan": f"{dti_with_loan:.0%}"},
        )
        if rejection:
            return rejection

        return None

    def _record_financial(self, trace, result):
        if result.get('error'):
            _step(trace, "Financial agent: debt and affordability", "Financial agent", "REVIEW",
                  f"The financial check could not finish: {result['error']}")
            return
        dti = result.get('dti_with_loan', 0)
        _step(trace, "Financial agent: debt and affordability", "Financial agent",
              RECOMMENDATION_STATUS.get(result.get('recommendation'), "REVIEW"),
              f"Debt after this loan would be {dti:.0%} of income. The approval limit is {config.MAX_DTI_RATIO:.0%}.",
              inputs={"Monthly payment on this loan": rupees(result.get('monthly_payment', 0), 2)},
              outputs={"Debt now": f"{result.get('dti_current', 0):.0%}",
                       "Debt after loan": f"{dti:.0%}",
                       "Result": str(result.get('recommendation'))})

    def _record_risk(self, trace, result):
        if result.get('error'):
            _step(trace, "Risk agent: score and policy lookup", "Risk agent", "REVIEW",
                  f"The risk check could not finish: {result['error']}")
            return
        score = result.get('risk_score', 0)
        level = result.get('risk_level', '')
        policies = result.get('policy_references') or []
        _step(trace, "Risk agent: score and policy lookup", "Risk agent",
              RECOMMENDATION_STATUS.get(result.get('recommendation'), "REVIEW"),
              f"Risk score is {score:.0f} out of 100 ({level.lower()} risk). "
              f"{len(policies)} matching lending rule(s) were found.",
              outputs={"Risk score": f"{score:.0f} / 100", "Risk level": level,
                       "Lending rules matched": str(len(policies)),
                       "Result": str(result.get('recommendation'))})

    def _record_recommendation(self, trace, recommendation):
        final = recommendation.get('final_recommendation')
        _step(trace, "Recommendation agent: combine the two reports", "Recommendation agent",
              RECOMMENDATION_STATUS.get(final, "REVIEW"),
              f"Financial agent said {recommendation.get('financial_recommendation')}, risk agent said "
              f"{recommendation.get('risk_recommendation')}. The two reports {AGREEMENT_TEXT.get(recommendation.get('agent_agreement'), 'were compared')}.",
              outputs={"Agreement": str(recommendation.get('agent_agreement')),
                       "Confidence": f"{recommendation.get('confidence_score', 0):.0%}",
                       "Recommendation": str(final),
                       "Needs a person to check": "Yes" if recommendation.get('requires_human_approval') else "No"})

    def _policy_flags(self, application):
        """Conditions that need a human underwriter even when the agents agree"""
        flags = []
        if application.get('bankruptcy_history'):
            flags.append("Bankruptcy history: discharge date must be confirmed (2+ years required)")
        if application.get('prior_delinquencies', 0) > config.MAX_DELINQUENCIES:
            flags.append("Multiple delinquencies: manual review required")
        if application.get('recent_inquiries', 0) > config.MAX_RECENT_INQUIRIES:
            flags.append(f"More than {config.MAX_RECENT_INQUIRIES} recent credit inquiries")
        if application.get('years_employed', 0) < config.MIN_YEARS_EMPLOYED:
            flags.append(f"Employment history below {config.MIN_YEARS_EMPLOYED} year(s)")
        return flags

    def _rejection_result(self, application, reason, trace=None):
        """Generate rejection result, ending the recorded steps with the final decision"""
        trace = trace if trace is not None else []
        _step(trace, "Final decision", "Final decision", "FAIL", reason, outputs={"Decision": "REJECT"})
        return {
            'applicant_id': application.get('applicant_id'),
            'applicant_name': application.get('name'),
            'decision': 'REJECT',
            'status': 'REJECTED',
            'confidence_score': 1.0,
            'requires_human_approval': False,
            'workflow_duration_seconds': 0,
            'workflow_trace': trace,
            'reason': reason
        }

def get_orchestrator():
    return LoanProcessingOrchestrator()
