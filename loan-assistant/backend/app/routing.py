"""Router: decides which loan-product workflow (rules + policy documents) an application follows."""
import re

from .rules import PRODUCTS, ProductRules
from .schemas import LoanApplication, RouteDecision

GENERAL_DOC = "general_credit_policy"

_KEYWORDS = {
    "home": ("home", "mortgage", "house", "property", "apartment", "flat"),
    "auto": ("auto", "car", "vehicle", "motorcycle", "truck", "van"),
    "personal": ("personal", "debt", "consolidation", "medical", "travel", "wedding", "education", "renovation"),
}


class RoutingError(ValueError):
    pass


_PATTERNS = {key: re.compile(r"\b(?:" + "|".join(words) + r")s?\b", re.IGNORECASE) for key, words in _KEYWORDS.items()}


def _match(text: str) -> str | None:
    for key in ("home", "auto", "personal"):
        if _PATTERNS[key].search(text):
            return key
    return None


class LoanRouter:
    """Router-based workflow: the declared loan type picks the product route; if it is missing or
    unrecognised the stated purpose is used to infer one."""

    def route(self, app: LoanApplication) -> tuple[RouteDecision, ProductRules]:
        key, method, reason = _match(app.loan_type), "declared", f"Application declares loan type '{app.loan_type}'."
        if key is None:
            key = _match(app.purpose)
            method = "inferred"
            reason = f"Loan type '{app.loan_type}' not recognised; inferred from purpose '{app.purpose}'."
        if key is None:
            raise RoutingError(
                f"Cannot route application: loan type '{app.loan_type}' and purpose '{app.purpose}' "
                "do not match a supported product (personal, home, auto)."
            )
        product = PRODUCTS[key]
        decision = RouteDecision(
            loan_type=key,
            product_name=product.name,
            method=method,
            reason=reason,
            policy_docs=[GENERAL_DOC, product.doc_id],
        )
        return decision, product
