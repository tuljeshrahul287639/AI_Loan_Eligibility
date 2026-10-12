import time
import asyncio
from typing import Dict, Any
from agents.financial_agent import get_financial_agent
from agents.risk_agent import get_risk_agent
from agents.recommendation_agent import get_recommendation_agent
from utils.logging_setup import log_agent_decision
from utils.error_handler import validate_application_data
import config

class LoanProcessingOrchestrator:
    def __init__(self):
        self.financial_agent = get_financial_agent()
        self.risk_agent = get_risk_agent()
        self.recommendation_agent = get_recommendation_agent()
    
    def process_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # Step 1: Validate Application
            if not validate_application_data(application):
                return self._rejection_result(application, "Invalid application data")
            
            # Step 2: Pre-screening
            prescrean_result = self._prescreening(application)
            if prescrean_result:
                return prescrean_result
            
            # Step 3: Run Financial & Risk Agents in Parallel
            if config.PARALLEL_EXECUTION:
                financial_result, risk_result = asyncio.run(
                    self._run_agents_parallel(application)
                )
            else:
                financial_result = self.financial_agent.analyze(application)
                risk_result = self.risk_agent.analyze(application)
            
            # Step 4: Get Recommendation
            recommendation = self.recommendation_agent.synthesize(
                application, financial_result, risk_result
            )
            
            # Step 5: Final Decision
            duration = time.time() - start_time
            result = {
                'applicant_id': application.get('applicant_id'),
                'applicant_name': application.get('name'),
                'decision': recommendation.get('final_recommendation'),
                'status': 'APPROVED' if recommendation.get('final_recommendation') == 'APPROVE' else 'PENDING',
                'confidence_score': recommendation.get('confidence_score'),
                'requires_human_approval': recommendation.get('requires_human_approval'),
                'workflow_duration_seconds': duration,
                'financial_analysis': financial_result,
                'risk_analysis': risk_result
            }
            
            log_agent_decision('FINAL_DECISION', result)
            return result
            
        except Exception as e:
            return self._rejection_result(application, f"Error: {str(e)}")
    
    async def _run_agents_parallel(self, application):
        """Run Financial & Risk agents in parallel"""
        loop = asyncio.get_event_loop()
        financial = loop.run_in_executor(None, self.financial_agent.analyze, application)
        risk = loop.run_in_executor(None, self.risk_agent.analyze, application)
        return await financial, await risk
    
    def _prescreening(self, application):
        """Early rejection for policy violations"""
        credit_score = application.get('credit_score', 0)
        income = application.get('monthly_income', 0)
        debts = application.get('existing_debts', 0)
        
        if credit_score < config.MIN_CREDIT_SCORE:
            return self._rejection_result(application, "Credit score below minimum")
        
        if income < config.MIN_MONTHLY_INCOME:
            return self._rejection_result(application, "Income below minimum")
        
        if debts > income:
            return self._rejection_result(application, "Debts exceed income")
        
        return None
    
    def _rejection_result(self, application, reason):
        """Generate rejection result"""
        return {
            'applicant_id': application.get('applicant_id'),
            'applicant_name': application.get('name'),
            'decision': 'REJECT',
            'status': 'REJECTED',
            'confidence_score': 1.0,
            'requires_human_approval': False,
            'workflow_duration_seconds': 0,
            'reason': reason
        }

def get_orchestrator():
    return LoanProcessingOrchestrator()