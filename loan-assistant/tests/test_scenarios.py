"""Runs every documented scenario end to end through the PDF -> router -> agents pipeline."""
import pytest
from helpers import make_app
from scenarios import SCENARIOS

from app.llm import Narrator
from app.orchestrator import AssessmentOrchestrator
from app.pdf_tools import render_pdf
from app.policy_store import PolicyStore

orchestrator = AssessmentOrchestrator(PolicyStore(), Narrator())


def run(scenario):
    app = make_app(application_id=scenario.id, **scenario.overrides)
    return orchestrator.assess_pdf(render_pdf(app))


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
def test_scenario(scenario):
    expect = scenario.expect
    if "error" in expect:
        with pytest.raises(ValueError, match=expect["error"]):
            run(scenario)
        return

    result = run(scenario)
    rec = result.recommendation
    assert rec.decision == expect["decision"]
    if "route" in expect:
        assert result.route.loan_type == expect["route"]
    if "method" in expect:
        assert result.route.method == expect["method"]
    if "amount" in expect:
        assert rec.recommended_amount == expect["amount"]
    knockouts = {k.code for k in result.risk.knockouts}
    assert knockouts == set(expect.get("ko", []))
    assert set(expect.get("ex", [])) <= {x.code for x in result.risk.exceptions}
    if "clauses" in expect:
        assert set(expect["clauses"]) <= {f.clause for f in result.risk.knockouts + result.risk.exceptions}
    if "band" in expect:
        assert result.risk.band == expect["band"]
    if "condition" in expect:
        assert any(expect["condition"].lower() in c.lower() for c in rec.conditions)
    if rec.decision == "DECLINED":
        assert rec.recommended_amount is None
    else:
        assert rec.post_loan_dti <= 0.50
