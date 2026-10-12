import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def sample_application():
    """Sample loan application for testing"""
    return {
        'applicant_id': 'TEST-001',
        'name': 'Test Applicant',
        'monthly_income': 5000,
        'monthly_expenses': 1500,
        'credit_score': 700,
        'loan_amount': 300000,
        'existing_debts': 800,
        'years_employed': 3,
        'employment_type': 'Full-time',
        'prior_delinquencies': 0,
        'bankruptcy_history': False,
        'recent_inquiries': 1
    }

@pytest.fixture
def good_applicant():
    """Applicant with excellent profile"""
    return {
        'applicant_id': 'GOOD-001',
        'name': 'Good Applicant',
        'monthly_income': 8000,
        'monthly_expenses': 1500,
        'credit_score': 750,
        'loan_amount': 250000,
        'existing_debts': 300,
        'years_employed': 5,
        'employment_type': 'Full-time',
        'prior_delinquencies': 0,
        'bankruptcy_history': False,
        'recent_inquiries': 0
    }

@pytest.fixture
def bad_applicant():
    """Applicant with poor profile"""
    return {
        'applicant_id': 'BAD-001',
        'name': 'Bad Applicant',
        'monthly_income': 2000,
        'monthly_expenses': 1800,
        'credit_score': 580,
        'loan_amount': 400000,
        'existing_debts': 1500,
        'years_employed': 1,
        'employment_type': 'Part-time',
        'prior_delinquencies': 2,
        'bankruptcy_history': True,
        'recent_inquiries': 4
    }