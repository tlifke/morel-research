from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = "text"
    editable: bool = False
    slot: str = "body"
    hint: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Facet:
    key: str
    label: str


@dataclass(frozen=True)
class Decision:
    name: str
    hotkey: str
    tone: str = "neutral"
    hint: str = ""


@dataclass(frozen=True)
class RecordType:
    name: str
    label: str
    id_key: str
    headline_key: str
    review_key: str
    decisions: tuple[Decision, ...]
    fields: tuple[Field, ...]
    facets: tuple[Facet, ...]
    key_order: tuple[str, ...]
    review_key_order: tuple[str, ...]
    edit_decision: str | None = None
    pending_decisions: tuple[str, ...] = ("defer",)
    list_keys: tuple[str, ...] = ()
    edited_from_key: str = "edited_from"
    required_rationale: bool = True

    def decision_names(self) -> list[str]:
        return [d.name for d in self.decisions]

    def editable_keys(self) -> list[str]:
        return [f.key for f in self.fields if f.editable]

    def as_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["fields"] = [asdict(f) for f in self.fields]
        d["facets"] = [asdict(f) for f in self.facets]
        d["decisions"] = [asdict(x) for x in self.decisions]
        d["key_order"] = list(self.key_order)
        d["review_key_order"] = list(self.review_key_order)
        d["pending_decisions"] = list(self.pending_decisions)
        d["list_keys"] = list(self.list_keys)
        return d


PRINCIPLE = RecordType(
    name="principle",
    label="Principle",
    id_key="id",
    headline_key="statement",
    review_key="review",
    decisions=(
        Decision("accept", "a", "ok"),
        Decision("edit", "e", "warn"),
        Decision("reject", "r", "bad"),
        Decision("defer", "d", "info"),
    ),
    edit_decision="edit",
    list_keys=("id", "provenance"),
    fields=(
        Field("statement", "Statement", "longtext", editable=True, slot="headline",
              hint="The rule, one sentence."),
        Field("trigger_guidance", "Trigger guidance", "longtext", editable=True, slot="body",
              hint="When to consider it."),
        Field("checker_sketch", "Checker sketch", "longtext", editable=True, slot="body",
              hint="How gold applicability would be computed. No feasible checker, no scored set."),
        Field("type", "Type", "badge", editable=True, slot="meta"),
        Field("scope", "Scope", "list", editable=True, slot="meta",
              hint="Target ids it can touch; empty = global."),
        Field("provenance", "Provenance", "badge", slot="meta"),
        Field("proposer.model", "Proposer model", "text", slot="meta"),
        Field("proposer.prompt_version", "Prompt version", "text", slot="meta"),
        Field("proposer.batch_id", "Batch", "text", slot="meta"),
        Field("evidence", "Evidence", "list", slot="body",
              hint="Pair ids this was read off."),
    ),
    facets=(
        Facet("provenance", "Provenance"),
        Facet("type", "Type"),
        Facet("proposer.model", "Proposer model"),
    ),
    key_order=(
        "id",
        "statement",
        "trigger_guidance",
        "type",
        "scope",
        "provenance",
        "proposer",
        "evidence",
        "checker_sketch",
        "review",
    ),
    review_key_order=("decision", "reviewer", "date", "rationale", "edited_from"),
)


GOLD_AUDIT = RecordType(
    name="gold_audit",
    label="Gold span audit",
    id_key="id",
    headline_key="span_text",
    review_key="review",
    decisions=(
        Decision("clean", "c", "ok", "no defect; span is what the category means"),
        Decision("mislabeled", "m", "bad", "content does not match the category at all"),
        Decision("labeled_by_neighbourhood", "n", "warn",
                 "heading or adjacent text captured because the real clause is nearby"),
        Decision("artifact_split", "s", "bad",
                 "one legal thought split across gold spans by page furniture"),
        Decision("boundary_jitter", "b", "warn",
                 "boundaries off by a few characters vs an equivalent span"),
        Decision("redaction_dependent", "x", "alt",
                 "decisive content is redacted; the call rests on clause structure"),
        Decision("cross_category_overlap", "o", "info",
                 "byte-identical or strictly nested against another category's span"),
        Decision("inconsistent_across_duplicates", "t", "alt",
                 "this span is fine in isolation; a near-identical passage in another "
                 "contract carries the opposite label. Judge the counterpart table, "
                 "not this span"),
        Decision("defer", "d", "neutral", "cannot call it without more context"),
    ),
    pending_decisions=("defer",),
    list_keys=("category", "span_index", "split"),
    fields=(
        Field("span_text", "Gold span", "span", slot="headline",
              config={"before": "context_before", "after": "context_after",
                      "start": "start", "end": "end"},
              hint="Gold span in place, with surrounding contract text."),
        Field("category", "Category", "badge", slot="meta"),
        Field("contract_id", "Contract", "text", slot="meta"),
        Field("split", "Split", "badge", slot="meta"),
        Field("offsets", "Offsets", "text", slot="meta"),
        Field("n_chars", "Span chars", "text", slot="meta"),
        Field("span_index", "Span", "text", slot="meta"),
        Field("n_spans_in_category", "Of", "text", slot="meta"),
        Field("has_counterpart", "Counterpart", "badge", slot="meta"),
        Field("n_contracts_with_passage", "Passage seen in N others", "text", slot="meta"),
        Field("siblings", "Sibling gold spans, same category", "rows", slot="body",
              config={"columns": ["span_index", "offsets", "n_chars", "text"]},
              hint="Artifact-split shows up here: two spans that are one thought."),
        Field("overlaps", "Other categories overlapping this span", "rows", slot="body",
              config={"columns": ["category", "relation", "offsets", "text"]},
              hint="Byte-identical or nested spans under a different category."),
        Field("duplicate_counterparts",
              "Same passage in other contracts, and how it is labeled there",
              "rows", slot="body",
              config={"columns": ["contract_id", "split", "twin_label",
                                  "doc_containment", "offsets", "passage"]},
              hint="twin_label is that contract's label for THIS category. "
                   "'marked_absent' or 'not_annotated' against an identical passage "
                   "is the inconsistent_across_duplicates case. A high "
                   "n_contracts_with_passage means boilerplate, not a near-twin."),
        Field("title", "Contract title", "longtext", slot="body"),
        Field("sample", "Sampling provenance", "kv", slot="body",
              hint="Seed and stratum this record was drawn under."),
    ),
    facets=(
        Facet("category", "Category"),
        Facet("split", "Split"),
        Facet("has_counterpart", "Has counterpart"),
    ),
    key_order=(
        "id",
        "contract_id",
        "title",
        "split",
        "category",
        "span_index",
        "n_spans_in_category",
        "start",
        "end",
        "n_chars",
        "span_text",
        "context_before",
        "context_after",
        "siblings",
        "overlaps",
        "duplicate_counterparts",
        "n_contracts_with_passage",
        "has_counterpart",
        "sample",
        "review",
    ),
    review_key_order=("decision", "reviewer", "date", "rationale"),
)


REGISTRY: dict[str, RecordType] = {
    PRINCIPLE.name: PRINCIPLE,
    GOLD_AUDIT.name: GOLD_AUDIT,
}


def get(name: str) -> RecordType:
    if name not in REGISTRY:
        raise KeyError(f"unknown record type {name!r}; known: {sorted(REGISTRY)}")
    return REGISTRY[name]


def dotted(record: dict[str, Any], key: str) -> Any:
    cur: Any = record
    for part in key.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def set_dotted(record: dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    cur = record
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


DEFAULT_TYPE = PRINCIPLE.name


def infer_type(records: list[dict[str, Any]]) -> str:
    for name, rt in REGISTRY.items():
        if not records:
            continue
        probe = records[0]
        if rt.id_key in probe and rt.headline_key in probe:
            return name
    return DEFAULT_TYPE


__all__ = [
    "Decision",
    "Facet",
    "Field",
    "RecordType",
    "REGISTRY",
    "DEFAULT_TYPE",
    "dotted",
    "set_dotted",
    "get",
    "infer_type",
]
