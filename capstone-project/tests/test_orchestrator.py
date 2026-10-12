import pytest
from orchestrator import LoanProcessingOrchestrator

@pytest.fixture
def orchestrator():
    return LoanProcessingOrchestrator()

def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly"""
    assert orchestrator is not None
    assert orchestrator.financial_agent is not None
    assert orchestrator.risk_agent is not None
    assert orchestrator.recommendation_agent is not None

def test_process_good_applicant(orchestrator, good_applicant):
    """Test processing good applicant"""
    result = orchestrator.process_application(good_applicant)
    assert result['applicant_id'] == good_applicant['applicant_id']
    assert result['decision'] in ['APPROVE', 'REVIEW', 'REJECT']
    assert 0 <= result['confidence_score'] <= 1
    assert result['workflow_duration_seconds'] > 0

def test_process_bad_applicant(orchestrator, bad_applicant):
    """Test processing bad applicant"""
    result = orchestrator.process_application(bad_applicant)
    assert result['decision'] in ['APPROVE', 'REVIEW', 'REJECT']
    assert result['requires_human_approval'] == True

def test_prescreening_low_credit(orchestrator):
    """Test prescreening with low credit score"""
    low_credit = {
        'applicant_id': 'LOW-CREDIT',
        'name': 'Low Credit',
        'monthly_income': 5000,
        'monthly_expenses': 1000,
        'credit_score': 500,  # Below minimum
        'loan_amount': 300000,
        'existing_debts': 500
    }
    result = orchestrator.process_application(low_credit)
    assert result['decision'] == 'REJECT'

def test_prescreening_low_income(orchestrator):
    """Test prescreening with low income"""
    low_income = {
        'applicant_id': 'LOW-INCOME',
        'name': 'Low Income',
        'monthly_income': 1000,  # Below minimum
        'monthly_expenses': 800,
        'credit_score': 700,
        'loan_amount': 300000,
        'existing_debts': 500
    }
    result = orchestrator.process_application(low_income)
    assert result['decision'] == 'REJECT'

def test_invalid_application(orchestrator):
    """Test processing invalid application"""
    invalid = {'applicant_id': 'INVALID'}
    result = orchestrator.process_application(invalid)
    assert result['decision'] == 'REJECT'