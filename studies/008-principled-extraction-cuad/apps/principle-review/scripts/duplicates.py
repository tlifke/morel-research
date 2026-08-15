from __future__ import annotations

import re
from functools import lru_cache

WHITESPACE = re.compile(r"\s+")
MIN_MATCH_CHARS = 60
MAX_COUNTERPARTS = 4
DETECTOR = "exact_normalized"
SKETCH_K = 400
SHINGLE = 8


def normalize(text: str) -> str:
    return WHITESPACE.sub(" ", text.lower()).strip()


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    out = []
    positions = []
    pending_space = False
    for index, char in enumerate(text):
        if char.isspace():
            pending_space = bool(out)
            continue
        if pending_space:
            out.append(" ")
            positions.append(index)
            pending_space = False
        out.append(char.lower())
        positions.append(index)
    return "".join(out), positions


def sketch(normalized_text: str) -> set[int]:
    tokens = normalized_text.split()
    grams = {
        hash(" ".join(tokens[i:i + SHINGLE])) & 0xFFFFFFFF
        for i in range(max(1, len(tokens) - SHINGLE + 1))
    }
    return set(sorted(grams)[:SKETCH_K])


class Corpus:
    def __init__(self, dataset):
        self.dataset = dataset
        self.texts = dataset._text
        self._normalized = {cid: normalize(text) for cid, text in self.texts.items()}
        self._sketches = {cid: sketch(text) for cid, text in self._normalized.items()}

    def containment(self, a: str, b: str) -> float:
        sa, sb = self._sketches[a], self._sketches[b]
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / min(len(sa), len(sb))

    @lru_cache(maxsize=64)
    def _mapped(self, contract_id: str) -> tuple[str, tuple[int, ...]]:
        normalized, positions = normalize_with_map(self.texts[contract_id])
        return normalized, tuple(positions)

    def _split_of(self, contract_id: str) -> str:
        record = self.dataset._records.get(contract_id)
        return record["split"] if record else "unassigned"

    def _gold_for(self, contract_id: str, category: str):
        record = self.dataset._records.get(contract_id)
        if not record or category not in record.get("gold", {}):
            return None
        return record["gold"][category]

    def find_counterparts(
        self,
        contract_id: str,
        category: str,
        span_text: str,
        min_chars: int = MIN_MATCH_CHARS,
        limit: int = MAX_COUNTERPARTS,
    ) -> tuple[list[dict], int]:
        needle = normalize(span_text)
        if len(needle) < min_chars:
            return [], 0

        hits = [
            other
            for other, text in self._normalized.items()
            if other != contract_id and needle in text
        ]
        if not hits:
            return [], 0

        ranked = sorted(
            hits, key=lambda o: (-self.containment(contract_id, o), o)
        )[:limit]

        counterparts = []
        for other in ranked:
            normalized, positions = self._mapped(other)
            at = normalized.find(needle)
            if at < 0:
                continue
            start = positions[at]
            end = positions[min(at + len(needle) - 1, len(positions) - 1)] + 1
            gold = self._gold_for(other, category)
            twin_spans = []
            if gold:
                twin_spans = [
                    {"offsets": f"{s}-{e}", "text": self.texts[other][s:e]}
                    for s, e in gold["spans"]
                    if s < end and start < e
                ]
            if gold is None:
                label = "category_not_in_subset"
            elif twin_spans:
                label = "annotated"
            elif gold.get("is_impossible"):
                label = "marked_absent"
            else:
                label = "not_annotated"
            counterparts.append(
                {
                    "contract_id": other,
                    "split": self._split_of(other),
                    "detector": DETECTOR,
                    "similarity": 1.0,
                    "doc_containment": round(self.containment(contract_id, other), 4),
                    "twin_label": label,
                    "offsets": f"{start}-{end}",
                    "twin_span_offsets": twin_spans[0]["offsets"] if twin_spans else None,
                    "passage": self.texts[other][start:end],
                }
            )
        return counterparts, len(hits)
