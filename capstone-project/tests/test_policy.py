import json

import pytest

import config
from data.synthetic_data_generator import load_curated_applications
from orchestrator import LoanProcessingOrchestrator

BASE = {
    "applicant_id": "POLICY-TEST",
    "name": "Policy Test",
    "monthly_income": 8000,
    "monthly_expenses": 2000,
    "credit_score": 750,
    "loan_amount": 250000,
    "existing_debts": 600,
    "years_employed": 6,
    "employment_type": "Full-time",
    "prior_delinquencies": 0,
    "bankruptcy_history": False,
    "recent_inquiries": 1,
}


@pytest.fixture(scope="module")
def orchestrator():
    return LoanProcessingOrchestrator()


def run(orchestrator, **overrides):
    return orchestrator.process_application({**BASE, **overrides})


def test_clean_profile_is_approved(orchestrator):
    result = run(orchestrator)
    assert result["decision"] == "APPROVE"
    assert result["policy_flags"] == []


@pytest.mark.parametrize(
    "overrides, expected_reason",
    [
        ({"credit_score": 600}, "is below the minimum of"),
        ({"monthly_income": 1000}, "is below the minimum of"),
        ({"loan_amount": 20000}, "Loan amount must be between"),
        ({"loan_amount": 600000}, "Loan amount must be between"),
        ({"monthly_income": 2000, "loan_amount": 150000}, "more than 5 times the yearly income"),
        ({"monthly_income": 4000, "loan_amount": 200000, "existing_debts": 1000}, "above the 50% limit"),
    ],
)
def test_hard_policy_rejections(orchestrator, overrides, expected_reason):
    result = run(orchestrator, **overrides)
    assert result["decision"] == "REJECT"
    assert expected_reason in result["reason"]


def test_bankruptcy_history_sends_approvable_file_to_review(orchestrator):
    result = run(orchestrator, bankruptcy_history=True)
    assert result["decision"] == "REVIEW"
    assert result["requires_human_approval"] is True
    assert any("Bankruptcy" in flag for flag in result["policy_flags"])


def test_too_many_inquiries_sends_file_to_review(orchestrator):
    result = run(orchestrator, recent_inquiries=5)
    assert result["decision"] == "REVIEW"
    assert any("inquiries" in flag for flag in result["policy_flags"])


def test_short_employment_sends_file_to_review(orchestrator):
    result = run(orchestrator, years_employed=0)
    assert result["decision"] == "REVIEW"
    assert any("Employment history" in flag for flag in result["policy_flags"])


def test_risk_output_lists_policy_sources(orchestrator):
    result = run(orchestrator)
    references = result["risk_analysis"]["policy_references"]
    assert references, "expected at least one policy excerpt"
    assert all(ref["source"].endswith(".txt") for ref in references)


def test_curated_samples_cover_every_outcome(orchestrator):
    seen = set()
    for sample in load_curated_applications():
        expected = sample.pop("expected_outcome").split(" - ")[0]
        result = orchestrator.process_application(sample)
        assert result["decision"] == expected, sample["applicant_id"]
        seen.add(expected)
    assert seen == {"APPROVE", "REVIEW", "REJECT"}
