"""user_knowledge_lookup — ranked-list search over the user persona KB."""

from __future__ import annotations

from pathlib import Path

from ._lookup_engine import load_kb, search

_STUDY_ROOT = Path(__file__).resolve().parent.parent
_KB_PATH = _STUDY_ROOT / "kb" / "user_knowledge.json"

_RETURN_FIELDS = ("field", "snippet")
_SEARCH_FIELDS = ("field", "snippet", "aliases")


def user_knowledge_lookup(query: str) -> dict:
    kb = load_kb(_KB_PATH, entries_key="entries")
    hits = search(kb, query, text_keys=_SEARCH_FIELDS)
    return {
        "results": [{k: e.get(k) for k in _RETURN_FIELDS} for e in hits],
    }
