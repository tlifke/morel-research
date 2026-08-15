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
    help: str = ""
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
        Decision("accept", "a", "ok", "the rule is real, and the checker sketch could be built"),
        Decision("edit", "e", "warn", "the rule or its checker needs changing before it is usable"),
        Decision("reject", "r", "bad", "the rule is wrong, or is not a rule about extraction"),
        Decision("defer", "d", "info",
                 "understood, but not rulable yet — needs more evidence, a footprint, "
                 "or a decision made elsewhere"),
        Decision("unclear", "x", "alt",
                 "NOT defer. The statement itself is not comprehensible: you cannot tell "
                 "what it is asserting, so there is nothing to weigh evidence against. "
                 "Say in the rationale which part is unreadable"),
    ),
    pending_decisions=("defer", "unclear"),
    edit_decision="edit",
    list_keys=("id", "provenance"),
    fields=(
        Field("statement", "Statement", "longtext", editable=True, slot="headline",
              hint="The rule, one sentence."),
        Field("footprint", "Empirical footprint", "footprint", slot="feature",
              config={"index": "footprint"},
              hint="Measured, not proposed: the checker sketch implemented and run over "
                   "the dev split.",
              help="Someone implemented this principle's checker and ran it. "
                   "APPLICABILITY is how often it fires at all — near 0% means it is "
                   "untestable in practice, near 100% means it fires on everything and "
                   "separates nothing. DISTRIBUTION shows whether that firing is spread "
                   "across categories and contracts or concentrated in one corner. "
                   "DISCRIMINATION is whether it actually splits gold-conforming from "
                   "non-conforming material. These numbers outrank the proposer's "
                   "argument: a principle that reads well and measures flat is not a "
                   "principle. Absent means round 2 has not measured this one yet."),
        Field("cross_source_validation", "Cross-source validation", "cross_source",
              slot="feature", config={"index": "cross_source"},
              hint="The principle checked against the source it did NOT come from.",
              help="Every candidate was derived from one source — either the Atticus "
                   "Handbook or the mined CUAD data. This block tests it against the "
                   "OTHER one. CORROBORATED means the second source independently "
                   "agrees. CONTRADICTED means the second source says something "
                   "different, and the quantification says how often. SILENT is a "
                   "third, NEUTRAL outcome and must not be read as disagreement: it "
                   "means the second source has nothing to say on this claim, usually "
                   "because it structurally cannot — the Handbook has no chapter for "
                   "some categories, and its rules are written per-sentence so a "
                   "document-provenance claim has nowhere to be stated. A silent "
                   "record is exactly as unvalidated as it was before this check, "
                   "no worse; the reason for the silence is printed in full. Direction "
                   "tells you which way the check ran."),
        Field("critique", "Adversarial critique", "critique",
              slot="feature", config={"index": "critiques"},
              hint="A critic instructed to argue AGAINST every candidate, plus the "
                   "strongest case it could still make for it.",
              help="A separate blinded pass was told to build the strongest honest "
                   "case against each candidate, so objections here are commissioned, "
                   "not spontaneous — every principle has some, including the good "
                   "ones. Read the per-objection CONFIDENCE, not the count: STRONG "
                   "means the critic thinks the candidate should not ship as written, "
                   "MODERATE means survivable with a rewrite, WEAK means real but "
                   "small, and COULD NOT BREAK means it attacked and failed, which is "
                   "positive evidence. The STRONGEST DEFENCE is written by the same "
                   "critic and carries the same weight as the objections — it is the "
                   "best argument for the candidate that survived the attack. "
                   "Judging on objection count alone converts this into an argument "
                   "for rejection, which is the mirror of round 1's accept-by-default "
                   "and just as wrong."),
        Field("trigger_guidance", "Trigger guidance", "longtext", editable=True, slot="body",
              hint="When to consider it."),
        Field("checker_sketch", "Checker sketch", "longtext", editable=True, slot="body",
              hint="How gold applicability would be computed. No feasible checker, no scored set.",
              help="A checker sketch is a proposed PROGRAMMATIC test — code someone "
                   "could actually write — that decides, for a given contract, whether "
                   "this principle applies and whether a prediction obeys it. It is "
                   "computed from the contract text plus its CUAD gold annotations, with "
                   "no human judgement at scoring time. You are judging exactly two "
                   "things. (1) IMPLEMENTABLE: could this be written against the "
                   "contract text, gold spans and character offsets we already have, "
                   "without new annotation or a second model? (2) FAITHFUL: does it test "
                   "the statement above — no wider, no narrower? A sound rule with a "
                   "broken checker is an EDIT of the sketch, not a reject of the rule; "
                   "a checker that quietly tests something easier than the statement is "
                   "the failure mode to watch for."),
        Field("type", "Type", "badge", editable=True, slot="meta"),
        Field("scope", "Scope", "list", editable=True, slot="meta",
              hint="Target ids it can touch; empty = global."),
        Field("provenance", "Provenance", "badge", slot="meta"),
        Field("proposer.model", "Proposer model", "text", slot="meta"),
        Field("proposer.prompt_version", "Prompt version", "text", slot="meta"),
        Field("proposer.batch_id", "Batch", "text", slot="meta"),
        Field("evidence", "Evidence", "evidence", slot="body",
              config={"index": "pairs"},
              hint="What this was read off. Mined pair ids resolve to the two spans "
                   "in full; anything else is a citation, shown as written.",
              help="A contrastive pair is two gold spans that look alike to the miner "
                   "but carry different CUAD labels. The CONTRAST is the evidence: the "
                   "question is whether the statement above is what actually separates "
                   "the left side from the right side, or whether something else does "
                   "and the rule is an after-the-fact story. Similarity is the miner's "
                   "score, not a confidence. Guideline-provenance principles cite the "
                   "Atticus Handbook instead and have no pairs to open."),
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
        Field("detected_by", "Detected by", "badge", slot="meta"),
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
              config={"columns": ["contract_id", "split", "excluded_as",
                                  "twin_label", "detector", "similarity",
                                  "doc_containment", "offsets", "passage"]},
              hint="twin_label is that contract's label for THIS passage. "
                   "'marked_absent' = category ruled absent there; "
                   "'category_annotated_elsewhere' = category IS annotated there but "
                   "not on this passage, i.e. a missing span rather than a missing "
                   "category. "
                   "'marked_absent' or 'not_annotated' against an identical passage "
                   "is the inconsistent_across_duplicates case. A high "
                   "n_contracts_with_passage means boilerplate, not a near-twin. "
                   "detector=exact_normalized is byte-identical text; "
                   "fuzzy_idf_jaccard is a similarity match, so read its passage "
                   "before trusting it. A non-empty excluded_as means that contract "
                   "was removed from ft_train for cross-split duplication (INV1-D7); "
                   "it is still valid evidence that the gold disagrees."),
        Field("title", "Contract title", "longtext", slot="body"),
        Field("sample", "Sampling provenance", "kv", slot="body",
              hint="Seed and stratum this record was drawn under."),
    ),
    facets=(
        Facet("category", "Category"),
        Facet("split", "Split"),
        Facet("detected_by", "Detected by"),
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
        "detected_by",
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
