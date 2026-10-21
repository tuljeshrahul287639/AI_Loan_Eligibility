"""Optional free, local narration for the agents (Ollama).

Decisions, scores and numbers are always computed deterministically. A local model is only asked to write
the prose (loan summary, risk explanation, recommendation rationale) from those facts and the retrieved
policy clauses. It needs no account, API key or internet access. If no model is configured, or the call
fails, the agent's template text is used.
"""
import json
import logging

import httpx

from . import config
from .schemas import PolicyRef, Source

log = logging.getLogger("loan_assistant.llm")

SYSTEM_PROMPT = (
    "You are a lending analyst assistant inside a bank's loan eligibility tool. Write the requested "
    "passage for a loan officer using only the facts and policy clauses supplied. Never change, "
    "contradict or re-derive the decision or any figure. Cite policy clause ids in square brackets "
    "where relevant, for example [GCP-3.1]. Plain prose, no markdown, no headings, at most 110 words."
)

TASKS = {
    "loan_summary": "Summarize the loan request and the applicant's financial position.",
    "risk_explanation": "Explain in plain language what drives the risk score and any policy knockouts or exceptions.",
    "recommendation": "Explain the eligibility recommendation, the recommended terms and any conditions.",
}


class Narrator:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.model = config.OLLAMA_MODEL if config.LLM_ENABLED else None
        self.last_error: str | None = None
        self._http = httpx.Client(base_url=config.OLLAMA_URL, timeout=config.OLLAMA_TIMEOUT, transport=transport) if self.model else None

    @property
    def configured(self) -> bool:
        return self._http is not None

    @property
    def mode(self) -> Source:
        """'ollama' only while a model is configured and the latest call did not fail."""
        return "ollama" if self._http and not self.last_error else "template"

    def narrate(self, task: str, facts: dict, refs: list[PolicyRef], fallback: str) -> tuple[str, Source]:
        if not self._http:
            return fallback, "template"
        clauses = "\n".join(f"[{r.id}] {r.text}" for r in refs)
        prompt = (
            f"Task: {TASKS[task]}\n\nFacts (JSON):\n{json.dumps(facts, indent=2, default=str)}\n\n"
            f"Policy clauses:\n{clauses}"
        )
        try:
            response = self._http.post("/api/chat", json={
                "model": self.model,
                "stream": False,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                "options": {"temperature": 0.2, "num_predict": 350},
            })
            response.raise_for_status()
            text = (response.json().get("message", {}).get("content") or "").strip()
            if not text:
                raise RuntimeError("empty response")
            self.last_error = None
            return text, "ollama"
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            log.warning("Local model narration failed, using template: %s", self.last_error)
            return fallback, "template"
