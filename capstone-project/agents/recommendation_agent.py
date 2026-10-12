from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
import config
from utils.logging_setup import log_agent_decision, log_workflow_step

class RecommendationAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0.7
        )
        self.agent_name = "RecommendationAgent"
    
    def synthesize(self, application: Dict[str, Any], financial_result: Dict[str, Any], risk_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            financial_rec = financial_result.get('recommendation', 'REVIEW')
            financial_conf = financial_result.get('confidence_score', 0.5)
            risk_rec = risk_result.get('recommendation', 'REVIEW')
            risk_conf = risk_result.get('confidence_score', 0.5)
            
            agent_agreement = self._check_agreement(financial_rec, risk_rec)
            combined_confidence = (financial_conf + risk_conf) / 2
            combined_confidence = self._adjust_confidence_by_agreement(combined_confidence, agent_agreement)
            final_recommendation = self._determine_final_decision(financial_rec, risk_rec, agent_agreement)
            requires_approval = self._check_approval_required(combined_confidence, final_recommendation)
            
            result = {
                'final_recommendation': final_recommendation,
                'confidence_score': round(combined_confidence, 3),
                'agent_agreement': agent_agreement,
                'financial_recommendation': financial_rec,
                'risk_recommendation': risk_rec,
                'requires_human_approval': requires_approval,
                'summary': f"Agent Agreement: {agent_agreement} | Confidence: {combined_confidence:.1%}"
            }
            
            log_workflow_step("synthesis", f"Final: {final_recommendation}")
            log_agent_decision(self.agent_name, final_recommendation, combined_confidence)
            return result
        
        except Exception as e:
            return self._error_response(str(e))
    
    def _check_agreement(self, financial_rec: str, risk_rec: str) -> str:
        if financial_rec == risk_rec:
            return 'STRONG'
        if (financial_rec in ['APPROVE', 'REVIEW'] and risk_rec in ['APPROVE', 'REVIEW']):
            return 'MODERATE'
        if (financial_rec in ['REVIEW', 'REJECT'] and risk_rec in ['REVIEW', 'REJECT']):
            return 'MODERATE'
        return 'CONFLICTING'
    
    def _adjust_confidence_by_agreement(self, confidence: float, agreement: str) -> float:
        if agreement == 'STRONG':
            return min(confidence * 1.1, 1.0)
        elif agreement == 'MODERATE':
            return confidence
        else:
            return confidence * 0.6
    
    def _determine_final_decision(self, financial_rec: str, risk_rec: str, agreement: str) -> str:
        if financial_rec == 'APPROVE' and risk_rec == 'APPROVE':
            return 'APPROVE'
        if financial_rec == 'REJECT' or risk_rec == 'REJECT':
            return 'REJECT'
        if financial_rec == 'ESCALATE' or risk_rec == 'ESCALATE':
            return 'ESCALATE'
        if agreement == 'CONFLICTING':
            return 'REVIEW'
        return 'REVIEW'
    
    def _check_approval_required(self, confidence: float, recommendation: str) -> bool:
        if confidence < 0.75:
            return True
        if recommendation in ['REVIEW', 'ESCALATE']:
            return True
        return False
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        return {'final_recommendation': 'REVIEW', 'confidence_score': 0.0, 'agent_agreement': 'ERROR', 'requires_human_approval': True, 'error': error_msg}

def get_recommendation_agent() -> RecommendationAgent:
    return RecommendationAgent()