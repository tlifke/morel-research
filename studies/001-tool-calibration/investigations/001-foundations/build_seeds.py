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
SCHEMA_PATH = HERE / "metadata.schema.json"
STUDY_ROOT = HERE.parent.parent
OUT_PATH = STUDY_ROOT / "seeds.jsonl"


def deterministic_shortuuid(pair_id: str, half_index: int) -> str:
    digest = hashlib.sha256(f"{pair_id}|{half_index}".encode()).hexdigest()
    return digest[:8]


def expand_pair(pair: dict, curator_model: str, curator_date: str) -> list[dict]:
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
                "human_review": None,
            },
            "difficulty_calibrated": None,
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

    pairs = spec["pairs"]
    all_records: list[dict] = []
    for pair in pairs:
        all_records.extend(expand_pair(pair, curator_model, curator_date))

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
    if args.validate:
        print(f"validated all {n_records} records against {SCHEMA_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
