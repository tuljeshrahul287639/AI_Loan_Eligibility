import pytest
from agents.financial_agent import get_financial_agent

@pytest.fixture
def financial_agent():
    return get_financial_agent()

def test_financial_agent_initialization(financial_agent):
    """Test agent initializes"""
    assert financial_agent is not None
    assert financial_agent.calculator is not None

def test_financial_analysis_good_profile(financial_agent, good_applicant):
    """Test financial analysis with good profile"""
    result = financial_agent.analyze(good_applicant)
    assert result['recommendation'] in ['APPROVE', 'REVIEW', 'REJECT']
    assert 0 <= result['confidence_score'] <= 1
    assert 'financial_metrics' in result
    assert result['dti_percentage'] > 0

def test_financial_analysis_poor_profile(financial_agent, bad_applicant):
    """Test financial analysis with poor profile"""
    result = financial_agent.analyze(bad_applicant)
    assert result['recommendation'] in ['APPROVE', 'REVIEW', 'REJECT']
    # Poor applicant should have lower confidence
    assert result['confidence_score'] < 0.85

def test_dti_calculation(financial_agent, sample_application):
    """Test DTI calculation"""
    result = financial_agent.analyze(sample_application)
    dti = result['dti_percentage']
    assert dti >= 0
    assert dti <= 100

def test_financial_health_classification(financial_agent, good_applicant):
    """Test financial health classification"""
    result = financial_agent.analyze(good_applicant)
    health = result['financial_health']
    assert health in ['POOR', 'FAIR', 'MARGINAL', 'GOOD', 'EXCELLENT']

def test_approval_recommendation_logic(financial_agent, good_applicant):
    """Test approval recommendation for healthy applicant"""
    result = financial_agent.analyze(good_applicant)
    if result['financial_health'] in ['GOOD', 'EXCELLENT']:
        assert result['recommendation'] in ['APPROVE', 'REVIEW']

def test_rejection_recommendation_logic(financial_agent, bad_applicant):
    """Test rejection recommendation for poor applicant"""
    result = financial_agent.analyze(bad_applicant)
    if result['financial_health'] == 'POOR':
        assert result['recommendation'] in ['REVIEW', 'REJECT']