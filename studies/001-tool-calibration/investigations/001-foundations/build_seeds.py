"""Expand seeds_spec.yaml into seeds.jsonl.

Reads the compact pair specification at `seeds_spec.yaml` (alongside
this file) and emits a JSONL corpus at
`../../seeds.jsonl` (study root). Each pair generates two
records; each record conforms to `metadata.schema.json`.

Conventions:

- shortuuid for each half is deterministic:
  first 8 hex chars of sha256("{pair_id}|{half_index}"). Idempotent.
- LLM curator signature on every difficulty_label.llm_assessment is
  taken from `_metadata.llm_curator_model` and `_metadata.llm_curator_date`
  in the spec file (one signing model per spec run).
- pair_id is shared across both halves of a pair (per Decision 7 /
  Decision 12 / Decision 15). For Type A pairs, the pair_id's
  {difficulty} slot reflects the pair's probe target (typically the
  harder half's difficulty); the trivial sibling's own
  difficulty_label.value still reports per-half difficulty correctly.

Usage:
    uv run build_seeds.py            # write seeds.jsonl
    uv run build_seeds.py --validate # also run jsonschema against each record

Exits 0 on success; non-zero on any validation or expansion failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

from id_scheme import make_prompt_id

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "seeds_spec.yaml"
APPROVALS_PATH = HERE / "seeds_approvals.yaml"
SCHEMA_PATH = HERE / "metadata.schema.json"
STUDY_ROOT = HERE.parent.parent
OUT_PATH = STUDY_ROOT / "seeds.jsonl"


def deterministic_shortuuid(pair_id: str, half_index: int) -> str:
    digest = hashlib.sha256(f"{pair_id}|{half_index}".encode()).hexdigest()
    return digest[:8]


def _materialize_human_review(
    raw: dict | None,
    default_reviewer: str | None,
    default_date: str | None,
) -> dict | None:
    if raw is None:
        return None
    block = dict(raw)
    if "reviewer" not in block and default_reviewer:
        block["reviewer"] = default_reviewer
    if "date" not in block and default_date:
        block["date"] = default_date
    date_val = block.get("date")
    if date_val is not None and not isinstance(date_val, str):
        block["date"] = date_val.isoformat()
    block.setdefault("overridden_to", None)
    block.setdefault("notes", None)
    return block


def expand_pair(
    pair: dict,
    curator_model: str,
    curator_date: str,
    approvals_for_pair: list | None,
    default_reviewer: str | None,
    default_date: str | None,
) -> list[dict]:
    pair_id = pair["pair_id"]
    halves = pair["halves"]
    if len(halves) != 2:
        raise ValueError(f"pair {pair_id} must have exactly 2 halves, got {len(halves)}")
    records = []
    for idx, half in enumerate(halves):
        shortuuid = deterministic_shortuuid(pair_id, idx)
        full_id = make_prompt_id(pair_id, shortuuid=shortuuid)
        record = {
            "id": full_id,
            "pair_id": pair_id,
            "condition": half["condition"],
            "pair_type": pair["pair_type"],
            "tool_target": pair["tool_target"],
            "domain": pair["domain"],
            "sub_domain": pair.get("sub_domain"),
            "difficulty_label": {
                "value": half["difficulty_value"],
                "llm_assessment": {
                    "model": curator_model,
                    "date": curator_date,
                    "value": half["difficulty_value"],
                    "confidence": half.get("difficulty_confidence", "medium"),
                    "reasoning": half.get("difficulty_reasoning"),
                },
                "human_review": _materialize_human_review(
                    (approvals_for_pair[idx] if approvals_for_pair else None),
                    default_reviewer,
                    default_date,
                ),
            },
            "difficulty_calibrated": None,
            "human_feasibility": half["human_feasibility"],
            "frequency_class": pair["frequency_class"],
            "register_tone": pair["register_tone"],
            "register_form": pair["register_form"],
            "register_length": pair["register_length"],
            "register_notes": pair.get("register_notes"),
            "system_prompt_id": half["system_prompt_id"],
            "user_prompt": half["user_prompt"],
            "token_counts": None,
            "expected_tool_call": half["expected_tool_call"],
            "expected_call_confidence": half.get("expected_call_confidence", "medium"),
            "expected_pair_behavior": pair["expected_pair_behavior"],
            "calibration_status": "assumed",
            "calibration_verified_on": None,
            "tags": pair.get("tags", []),
            "source": "hand_curated",
            "source_record_id": None,
            "notes": half.get("notes", ""),
        }
        records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate every record against metadata.schema.json",
    )
    args = parser.parse_args()

    spec = yaml.safe_load(SPEC_PATH.read_text())
    meta = spec.get("_metadata", {})
    curator_model = meta.get("llm_curator_model")
    curator_date = meta.get("llm_curator_date")
    if curator_date is not None and not isinstance(curator_date, str):
        curator_date = curator_date.isoformat()
    if not curator_model or not curator_date:
        print(
            "ERROR: seeds_spec.yaml._metadata.llm_curator_model and "
            "llm_curator_date are required",
            file=sys.stderr,
        )
        return 2

    approvals_doc = {}
    if APPROVALS_PATH.exists():
        approvals_doc = yaml.safe_load(APPROVALS_PATH.read_text()) or {}
    approvals_map = approvals_doc.get("approvals", {}) or {}
    approvals_meta = approvals_doc.get("_metadata", {}) or {}
    default_reviewer = approvals_meta.get("default_reviewer")
    default_date = approvals_meta.get("default_date")
    if default_date is not None and not isinstance(default_date, str):
        default_date = default_date.isoformat()

    pairs = spec["pairs"]
    all_records: list[dict] = []
    n_approved_halves = 0
    for pair in pairs:
        approvals_for_pair = approvals_map.get(pair["pair_id"])
        if approvals_for_pair:
            n_approved_halves += len(approvals_for_pair)
        all_records.extend(
            expand_pair(
                pair,
                curator_model,
                curator_date,
                approvals_for_pair,
                default_reviewer,
                default_date,
            )
        )

    if args.validate:
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text())
        for rec in all_records:
            jsonschema.validate(rec, schema)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    n_pairs = len(pairs)
    n_records = len(all_records)
    print(
        f"wrote {OUT_PATH.relative_to(STUDY_ROOT.parent.parent)}: "
        f"{n_pairs} pairs, {n_records} records"
    )
    print(
        f"human-reviewed: {n_approved_halves}/{n_records} halves "
        f"({n_approved_halves // 2}/{n_pairs} pairs)"
    )
    if args.validate:
        print(f"validated all {n_records} records against {SCHEMA_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
