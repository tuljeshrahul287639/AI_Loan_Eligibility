"""Shared context and base class for the assessment agents."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..llm import Narrator
from ..policy_store import PolicyStore
from ..rules import ProductRules
from ..schemas import (
    FinancialAnalysis,
    LoanApplication,
    PolicyRef,
    Recommendation,
    RiskAssessment,
    RouteDecision,
)


@dataclass
class PipelineContext:
    """State handed from one agent to the next in the sequential workflow."""

    application: LoanApplication
    route: RouteDecision
    product: ProductRules
    financial: FinancialAnalysis | None = None
    risk: RiskAssessment | None = None
    recommendation: Recommendation | None = None


class BaseAgent(ABC):
    name: str
    step: str

    def __init__(self, policies: PolicyStore, narrator: Narrator):
        self.policies = policies
        self.narrator = narrator

    @abstractmethod
    def run(self, ctx: PipelineContext) -> Any:
        """Read earlier results from ctx, return this agent's result (the orchestrator stores it)."""

    @abstractmethod
    def describe(self, result: Any) -> str:
        """One-line summary of the result for the workflow trace."""

    def evidence(self, ctx: PipelineContext, query: str, cited: list[str], k: int = 2) -> list[PolicyRef]:
        """Policy evidence for a step: clauses the rules cited plus the top retrieved clauses for the query."""
        refs: dict[str, PolicyRef] = {cid: self.policies.ref(cid) for cid in dict.fromkeys(cited)}
        for ref in self.policies.retrieve(query, ctx.route.policy_docs, k=k):
            refs.setdefault(ref.id, ref)
        return list(refs.values())
