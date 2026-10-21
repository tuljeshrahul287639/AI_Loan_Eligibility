"""Orchestrator: PDF intake -> router -> sequential agents (financial -> risk -> recommendation)."""
import time
from typing import Callable, TypeVar

from .agents.base import PipelineContext
from .agents.financial import FinancialAnalysisAgent
from .agents.recommendation import RecommendationAgent
from .agents.risk import RiskAgent
from .llm import Narrator
from .pdf_tools import parse_pdf
from .policy_store import PolicyStore
from .routing import LoanRouter
from .schemas import AssessmentResult, LoanApplication, TraceStep

T = TypeVar("T")


class AssessmentOrchestrator:
    def __init__(self, policies: PolicyStore, narrator: Narrator):
        self.narrator = narrator
        self.router = LoanRouter()
        self.financial = FinancialAnalysisAgent(policies, narrator)
        self.risk = RiskAgent(policies, narrator)
        self.recommendation = RecommendationAgent(policies, narrator)

    def assess_pdf(self, pdf_bytes: bytes) -> AssessmentResult:
        trace: list[TraceStep] = []
        app = self._timed(trace, "Extract application", "PDF Parser", lambda: parse_pdf(pdf_bytes),
                          lambda a: f"{a.full_name}, {a.loan_type} request of ${a.loan_amount:,.0f}")
        return self._assess(app, trace)

    def assess(self, app: LoanApplication) -> AssessmentResult:
        return self._assess(app, [])

    def _assess(self, app: LoanApplication, trace: list[TraceStep]) -> AssessmentResult:
        route, product = self._timed(trace, "Route", "Router", lambda: self.router.route(app),
                                     lambda r: f"{r[0].product_name} workflow ({r[0].method})")
        if product.ltv_standard and app.asset_value is None:
            raise ValueError(f"A {product.name} application must state the collateral value.")
        ctx = PipelineContext(application=app, route=route, product=product)

        for agent, attr in ((self.financial, "financial"), (self.risk, "risk"), (self.recommendation, "recommendation")):
            setattr(ctx, attr, self._timed(trace, agent.step, agent.name, lambda a=agent: a.run(ctx), agent.describe))

        return AssessmentResult(
            application=app, route=route, financial=ctx.financial, risk=ctx.risk,
            recommendation=ctx.recommendation, trace=trace, llm_mode=self.narrator.mode,
        )

    @staticmethod
    def _timed(trace: list[TraceStep], step: str, agent: str, fn: Callable[[], T], describe: Callable[[T], str]) -> T:
        start = time.perf_counter()
        try:
            result = fn()
        except Exception as exc:
            trace.append(TraceStep(step=step, agent=agent, status="failed",
                                   duration_ms=round((time.perf_counter() - start) * 1000), detail=str(exc)))
            raise
        trace.append(TraceStep(step=step, agent=agent, status="completed",
                               duration_ms=round((time.perf_counter() - start) * 1000), detail=describe(result)))
        return result
