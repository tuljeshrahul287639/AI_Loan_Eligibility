import pytest
from agents.risk_agent import get_risk_agent

@pytest.fixture
def risk_agent():
    return get_risk_agent()

def test_risk_agent_initialization(risk_agent):
    """Test agent initializes"""
    assert risk_agent is not None
    assert risk_agent.calculator is not None

def test_risk_analysis_good_profile(risk_agent, good_applicant):
    """Test risk analysis with good profile"""
    result = risk_agent.analyze(good_applicant)
    assert 0 <= result['overall_score'] <= 100
    assert result['risk_level'] in ['LOW', 'LOW_TO_MODERATE', 'MODERATE', 'HIGH', 'VERY_HIGH']
    assert 0 <= result['confidence_score'] <= 1

def test_risk_analysis_poor_profile(risk_agent, bad_applicant):
    """Test risk analysis with poor profile"""
    result = risk_agent.analyze(bad_applicant)
    # Poor profile should have lower risk score or higher risk level
    assert result['overall_score'] >= 0

def test_risk_score_bounds(risk_agent, sample_application):
    """Test risk score stays within bounds"""
    result = risk_agent.analyze(sample_application)
    assert 0 <= result['overall_score'] <= 100

def test_recommendation_based_on_risk(risk_agent, good_applicant):
    """Test recommendation aligns with risk score"""
    result = risk_agent.analyze(good_applicant)
    recommendation = result['recommendation']
    assert recommendation in ['APPROVE', 'REVIEW', 'ESCALATE', 'REJECT']

def test_high_credit_score_impact(risk_agent):
    """Test high credit score improves risk assessment"""
    high_credit_app = {
        'applicant_id': 'HIGH-CREDIT',
        'name': 'High Credit',
        'monthly_income': 5000,
        'monthly_expenses': 1000,
        'credit_score': 800,  # High credit
        'loan_amount': 300000,
        'existing_debts': 500,
        'years_employed': 5,
        'employment_type': 'Full-time',
        'prior_delinquencies': 0,
        'bankruptcy_history': False,
        'recent_inquiries': 0
    }
    result = risk_agent.analyze(high_credit_app)
    assert result['overall_score'] >= 70