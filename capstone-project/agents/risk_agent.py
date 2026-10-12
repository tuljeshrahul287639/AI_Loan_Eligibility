from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
import config
from tools.risk_calculator import calculate_risk_score
from rag.rag_pipeline import RAGPipeline
from utils.logging_setup import log_agent_decision, log_error_with_context

class RiskAnalysisAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0.7
        )
        self.rag = RAGPipeline()
        self.agent_name = "RiskAgent"
    
    def analyze(self, application: Dict[str, Any]) -> Dict[str, Any]:
        try:
            credit_score = application.get('credit_score', 600)
            monthly_income = application.get('monthly_income', 0)
            monthly_debt = application.get('monthly_debt_payments', 0)
            
            risk_score = calculate_risk_score(credit_score, monthly_income, monthly_debt)
            policy_context = self.rag.retrieve(f"credit score {credit_score} approval guidelines")
            recommendation, confidence = self._assess_risk_level(risk_score)
            
            result = {
                'recommendation': recommendation,
                'confidence_score': confidence,
                'risk_score': round(risk_score, 2),
                'policy_retrieved': bool(policy_context),
                'risk_level': self._get_risk_level(risk_score),
                'analysis': f"Risk Score: {risk_score:.0f}/100"
            }
            
            log_agent_decision(self.agent_name, recommendation, confidence)
            return result
        
        except Exception as e:
            log_error_with_context(str(e), "Risk analysis failed")
            return self._error_response(str(e))
    
    def _assess_risk_level(self, risk_score: float) -> tuple:
        if risk_score <= 40:
            return 'APPROVE', 0.90
        elif risk_score <= 60:
            return 'REVIEW', 0.70
        else:
            return 'REJECT', 0.85
    
    def _get_risk_level(self, score: float) -> str:
        if score <= 40:
            return "LOW"
        elif score <= 60:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        return {'recommendation': 'REVIEW', 'confidence_score': 0.0, 'risk_score': 50, 'error': error_msg}

def get_risk_agent() -> RiskAnalysisAgent:
    return RiskAnalysisAgent()