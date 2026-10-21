"""Lending policy knowledge base: clause parsing and BM25 retrieval (the RAG layer)."""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import POLICY_DIR
from .schemas import PolicyRef

_CLAUSE = re.compile(r"^\*\*([A-Z]+-\d+\.\d+)\*\*\s+(.*)$")
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "of", "to", "and", "or", "is", "are", "in", "for", "be", "by", "at", "as", "on", "with", "than", "that", "it"}


@dataclass(frozen=True)
class Clause:
    id: str
    doc_id: str
    doc_title: str
    section: str
    text: str


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class PolicyStore:
    """Loads every policy markdown file, splits it into clauses and indexes them with BM25."""

    def __init__(self, policy_dir: Path = POLICY_DIR, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.clauses: dict[str, Clause] = {}
        self.docs: dict[str, dict] = {}
        for path in sorted(policy_dir.glob("*.md")):
            self._load(path)
        self._order = list(self.clauses)
        self._tf = {cid: Counter(_tokens(f"{c.section} {c.text}")) for cid, c in self.clauses.items()}
        self._len = {cid: sum(tf.values()) for cid, tf in self._tf.items()}
        self._avg = sum(self._len.values()) / max(len(self._len), 1)
        df: Counter = Counter()
        for tf in self._tf.values():
            df.update(tf.keys())
        n = len(self._tf)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _load(self, path: Path) -> None:
        doc_id, title, section, ids = path.stem, path.stem, "", []
        for line in path.read_text(encoding="utf8").splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
            elif line.startswith("## "):
                section = line[3:].strip()
            elif m := _CLAUSE.match(line.strip()):
                self.clauses[m[1]] = Clause(m[1], doc_id, title, section, m[2].strip())
                ids.append(m[1])
        self.docs[doc_id] = {"id": doc_id, "title": title, "clause_ids": ids}

    def ref(self, clause_id: str, score: float | None = None) -> PolicyRef:
        c = self.clauses[clause_id]
        return PolicyRef(id=c.id, doc=c.doc_title, text=c.text, score=score)

    def retrieve(self, query: str, doc_ids: list[str], k: int = 3) -> list[PolicyRef]:
        q = _tokens(query)
        scored = []
        for cid in self._order:
            if self.clauses[cid].doc_id not in doc_ids:
                continue
            tf, dl = self._tf[cid], self._len[cid]
            s = 0.0
            for term in q:
                f = tf.get(term, 0)
                if f:
                    s += self._idf.get(term, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self._avg))
            if s > 0:
                scored.append((s, cid))
        scored.sort(reverse=True)
        return [self.ref(cid, round(s, 3)) for s, cid in scored[:k]]

    def documents(self) -> list[dict]:
        return [
            {
                "id": d["id"],
                "title": d["title"],
                "clauses": [
                    {"id": cid, "section": self.clauses[cid].section, "text": self.clauses[cid].text}
                    for cid in d["clause_ids"]
                ],
            }
            for d in self.docs.values()
        ]
