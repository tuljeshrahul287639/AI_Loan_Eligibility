import httpx
import pytest

from app import config
from app.llm import Narrator
from app.orchestrator import AssessmentOrchestrator
from app.policy_store import PolicyStore
from helpers import make_app

policies = PolicyStore()
REFS = policies.retrieve("debt to income", ["general_credit_policy"], 1)


@pytest.fixture
def local_model(monkeypatch):
    monkeypatch.setattr(config, "LLM_ENABLED", True)
    monkeypatch.setattr(config, "OLLAMA_MODEL", "test-model")


def narrator_with(handler) -> Narrator:
    return Narrator(transport=httpx.MockTransport(handler))


def test_template_mode_without_a_configured_model():
    n = Narrator()
    assert (n.configured, n.mode) == (False, "template")
    assert n.narrate("loan_summary", {}, REFS, "fallback text") == ("fallback text", "template")


def test_local_model_text_is_used_and_request_is_well_formed(local_model):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"], seen["body"] = request.url.path, request.read().decode()
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "  Generated narrative [GCP-3.1].  "}})

    n = narrator_with(handler)
    text, source = n.narrate("risk_explanation", {"risk_score": 12}, REFS, "fallback")
    assert (text, source, n.mode, n.last_error) == ("Generated narrative [GCP-3.1].", "ollama", "ollama", None)
    assert seen["path"] == "/api/chat"
    assert '"model":"test-model"' in seen["body"].replace(" ", "") and '"stream":false' in seen["body"].replace(" ", "")
    assert "GCP-3.1" in seen["body"] and "risk_score" in seen["body"]


@pytest.mark.parametrize("handler", [
    lambda request: (_ for _ in ()).throw(httpx.ConnectError("connection refused")),
    lambda request: httpx.Response(500, json={"error": "model not found"}),
    lambda request: httpx.Response(200, json={"message": {"content": "   "}}),
], ids=["server down", "http error", "empty reply"])
def test_failures_fall_back_to_template_and_are_reported(local_model, handler):
    n = narrator_with(handler)
    assert n.narrate("recommendation", {}, REFS, "fallback") == ("fallback", "template")
    assert n.configured and n.mode == "template" and n.last_error


def test_pipeline_keeps_decisions_identical_with_and_without_the_model(local_model):
    app = make_app(credit_score=640, delinquencies_24m=1)
    def down(request):
        raise httpx.ConnectError("connection refused")

    plain = AssessmentOrchestrator(policies, narrator_with(down)).assess(app)  # falls back to templates
    ok = AssessmentOrchestrator(policies, narrator_with(
        lambda request: httpx.Response(200, json={"message": {"content": "LLM prose"}}))).assess(app)
    assert ok.llm_mode == "ollama" and ok.financial.summary == "LLM prose" and ok.risk.explanation == "LLM prose"
    assert ok.recommendation.rationale_source == "ollama"
    # the model changes wording only
    assert ok.recommendation.decision == plain.recommendation.decision
    assert ok.risk.score == plain.risk.score and ok.recommendation.conditions == plain.recommendation.conditions
