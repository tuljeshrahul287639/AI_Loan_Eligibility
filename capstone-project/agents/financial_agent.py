from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
import config
from tools.financial_calculator import calculate_dti, calculate_loan_payment
from utils.logging_setup import log_agent_decision, log_error_with_context

class FinancialAnalysisAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0.7
        )
        self.agent_name = "FinancialAgent"
    
    def analyze(self, application: Dict[str, Any]) -> Dict[str, Any]:
        try:
            monthly_income = application.get('monthly_income', 0)
            monthly_debt = application.get('monthly_debt_payments', 0)
            loan_amount = application.get('loan_amount', 0)
            
            if monthly_income <= 0:
                return self._error_response("Invalid income information")
            
            current_dti = calculate_dti(monthly_income, monthly_debt)
            monthly_payment = calculate_loan_payment(loan_amount)
            total_debt_with_loan = monthly_debt + monthly_payment
            dti_with_loan = calculate_dti(monthly_income, total_debt_with_loan)
            
            recommendation, confidence = self._assess_financial_health(dti_with_loan, monthly_income)
            
            result = {
                'recommendation': recommendation,
                'confidence_score': confidence,
                'dti_current': round(current_dti, 4),
                'dti_with_loan': round(dti_with_loan, 4),
                'monthly_payment': round(monthly_payment, 2),
                'analysis': f"Current DTI: {current_dti:.2%} | Post-Loan DTI: {dti_with_loan:.2%}"
            }
            
            log_agent_decision(self.agent_name, recommendation, confidence)
            return result
        
        except Exception as e:
            log_error_with_context(str(e), "Financial analysis failed")
            return self._error_response(str(e))
    
    def _assess_financial_health(self, dti_with_loan: float, monthly_income: float) -> tuple:
        if dti_with_loan <= config.MAX_DTI_RATIO and monthly_income >= config.MIN_INCOME:
            return 'APPROVE', 0.90
        elif dti_with_loan <= (config.MAX_DTI_RATIO + 0.05):
            return 'REVIEW', 0.60
        else:
            return 'REJECT', 0.85
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        return {'recommendation': 'REVIEW', 'confidence_score': 0.0, 'error': error_msg}

def get_financial_agent() -> FinancialAnalysisAgent:
    return FinancialAnalysisAgent()