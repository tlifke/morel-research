"""Shared lookup engine for general_knowledge_lookup and
user_knowledge_lookup.

Per Decision 8 the lookup tools mimic a real web-search shape: free-form
query in, ranked list of result records out, empty list on no match. We
implement a lightweight BM25-ish ranker over `snippet + aliases` text
for each entry. Small KBs (~20 entries each) make this scoring scheme
deterministic and unambiguous; we don't need a real retrieval index.
"""

from __future__ import annotations

import re
from collections import Counter
from math import log
from pathlib import Path
import json

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _document_text(entry: dict, entry_text_keys: tuple[str, ...]) -> str:
    parts = []
    for k in entry_text_keys:
        v = entry.get(k)
        if v is None:
            continue
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
        else:
            parts.append(str(v))
    return " ".join(parts)


def load_kb(path: Path, entries_key: str) -> list[dict]:
    data = json.loads(path.read_text())
    return data[entries_key]


def search(
    kb: list[dict],
    query: str,
    *,
    text_keys: tuple[str, ...],
    top_k: int = 3,
    score_threshold: float = 0.5,
) -> list[dict]:
    """BM25-lite ranker.

    Scores each entry by sum over query terms of:
        (term in entry doc text ? idf(term) : 0)
    Empty when no entry scores above `score_threshold` * max possible
    score for the query.

    Returns the matching entries (un-modified) in score-descending order,
    capped at `top_k`.
    """
    q_terms = _tokenize(query)
    if not q_terms:
        return []

    docs = [_tokenize(_document_text(e, text_keys)) for e in kb]
    n_docs = len(docs)
    df = Counter()
    for d in docs:
        for term in set(d):
            df[term] += 1

    def idf(t: str) -> float:
        return log(1 + (n_docs - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))

    max_score = sum(idf(t) for t in set(q_terms))
    if max_score <= 0:
        return []

    scored = []
    for entry, dtokens in zip(kb, docs):
        dset = set(dtokens)
        score = sum(idf(t) for t in set(q_terms) if t in dset)
        if score >= score_threshold * max_score:
            scored.append((score, entry))
    scored.sort(key=lambda p: -p[0])
    return [e for _, e in scored[:top_k]]
