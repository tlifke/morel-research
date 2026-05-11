"""general_knowledge_lookup — ranked-list search over the verified KB.

Decision 19: the verified KB (`kb/general_knowledge_real.json`) is the
canonical source for test cases. The fabricated KB
(`kb/general_knowledge.json`) is available via `source="fabricated"`
for sibling experiments that probe model behavior under counterfactual
KB content.
"""

from __future__ import annotations

from pathlib import Path

from ._lookup_engine import load_kb, search

_STUDY_ROOT = Path(__file__).resolve().parent.parent
_KB_PATHS = {
    "real": _STUDY_ROOT / "kb" / "general_knowledge_real.json",
    "fabricated": _STUDY_ROOT / "kb" / "general_knowledge.json",
}

# Project each entry into the API shape per Decision 8.
_RETURN_FIELDS = ("id", "date", "domain", "snippet")
_SEARCH_FIELDS = ("snippet", "aliases", "domain")


def general_knowledge_lookup(query: str, *, source: str = "real") -> dict:
    if source not in _KB_PATHS:
        raise ValueError(f"source must be one of {list(_KB_PATHS)}; got {source!r}")
    kb = load_kb(_KB_PATHS[source], entries_key="facts")
    hits = search(kb, query, text_keys=_SEARCH_FIELDS)
    return {
        "results": [{k: e.get(k) for k in _RETURN_FIELDS} for e in hits],
    }
