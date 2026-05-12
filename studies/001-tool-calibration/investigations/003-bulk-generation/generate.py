"""Bulk-generation runner for Phase A3.

Reads ``bulk_seeds_spec.yaml``, expands each generation cell into matched
pairs via per-tool template functions in ``axis_templates``, validates
every record against ``metadata.schema.json``, and writes the output
JSONL at ``../../bulk_seeds.jsonl`` (study root).

Usage:
    uv run generate.py
    uv run generate.py --spot-review-fraction 0.05
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
A1_DIR = HERE.parent / "001-foundations"
sys.path.insert(0, str(A1_DIR))
sys.path.insert(0, str(HERE))

from id_scheme import make_prompt_id  # noqa: E402
import axis_templates as AT  # noqa: E402

SPEC_PATH = HERE / "bulk_seeds_spec.yaml"
SCHEMA_PATH = A1_DIR / "metadata.schema.json"
STUDY_ROOT = HERE.parent.parent
OUT_PATH = STUDY_ROOT / "bulk_seeds.jsonl"
SPOT_REVIEW_PATH = HERE / "spot_review.yaml"


def shortuuid(pair_id: str, half_index: int, salt: str = "") -> str:
    return hashlib.sha256(f"{pair_id}|{half_index}|{salt}".encode()).hexdigest()[:8]


def _build_record(
    *,
    full_id: str,
    pair_id: str,
    condition: str,
    pair_type: str,
    tool: str,
    domain: str,
    sub_domain: str | None,
    difficulty_value: str,
    difficulty_reasoning: str,
    human_feasibility: str,
    frequency_class: str,
    register_tone: str,
    register_form: str,
    register_length: str,
    system_prompt_id: str,
    user_prompt: str,
    expected_tool_call: bool,
    expected_pair_behavior: str,
    tags: list[str],
    curator_model: str,
    curator_date: str,
    confidence: str = "medium",
) -> dict:
    return {
        "id": full_id,
        "pair_id": pair_id,
        "condition": condition,
        "pair_type": pair_type,
        "tool_target": tool,
        "domain": domain,
        "sub_domain": sub_domain,
        "difficulty_label": {
            "value": difficulty_value,
            "llm_assessment": {
                "model": curator_model,
                "date": curator_date,
                "value": difficulty_value,
                "confidence": confidence,
                "reasoning": difficulty_reasoning,
            },
            "human_review": None,
        },
        "difficulty_calibrated": None,
        "human_feasibility": human_feasibility,
        "frequency_class": frequency_class,
        "register_tone": register_tone,
        "register_form": register_form,
        "register_length": register_length,
        "register_notes": None,
        "system_prompt_id": system_prompt_id,
        "user_prompt": user_prompt,
        "token_counts": None,
        "expected_tool_call": expected_tool_call,
        "expected_call_confidence": "medium",
        "expected_pair_behavior": expected_pair_behavior,
        "calibration_status": "assumed",
        "calibration_verified_on": None,
        "tags": tags,
        "source": "llm_generated",
        "source_record_id": None,
        "notes": "",
    }


_TOOL_DOMAIN = {
    "calculator": "math",
    "python_execute": "math",
    "datetime_now": "time",
    "unit_convert": "units",
    "general_knowledge_lookup": "general_knowledge",  # overridden per-entry
    "user_knowledge_lookup": "personal",
}


def expand_cell(
    cell: dict, rng: random.Random, counters: dict, curator_model: str, curator_date: str
) -> list[dict]:
    tool = cell["tool"]
    pair_type = cell["pair_type"]
    count = cell["count"]
    sys_w = cell["system_prompt_warranted"]
    sys_t = cell["system_prompt_trivial"]

    records: list[dict] = []

    # tools that take an "entry" axis pre-selected
    if tool == "general_knowledge_lookup":
        entries = list(AT._GKL_ENTRIES)
        rng.shuffle(entries)
        entries = entries[: count]
        for entry in entries:
            tdata = AT.gen_general_knowledge_lookup(rng, {"entry": entry})
            records.extend(_emit_pair(
                tdata, tool, pair_type, sys_w, sys_t, cell, counters,
                curator_model, curator_date, rng,
            ))
        return records

    if tool == "user_knowledge_lookup":
        entries = list(AT._UKL_ENTRIES)
        rng.shuffle(entries)
        entries = entries[: count]
        for entry in entries:
            tdata = AT.gen_user_knowledge_lookup(rng, {"entry": entry})
            records.extend(_emit_pair(
                tdata, tool, pair_type, sys_w, sys_t, cell, counters,
                curator_model, curator_date, rng,
            ))
        return records

    # generic axis-driven tools
    gen_fn = {
        "calculator": AT.gen_calculator,
        "python_execute": AT.gen_python_execute,
        "datetime_now": AT.gen_datetime_now,
        "unit_convert": AT.gen_unit_convert,
    }[tool]
    for _ in range(count):
        tdata = gen_fn(rng, cell.get("axes", {}))
        records.extend(_emit_pair(
            tdata, tool, pair_type, sys_w, sys_t, cell, counters,
            curator_model, curator_date, rng,
        ))
    return records


def _next_counter(counters: dict, key: tuple) -> int:
    counters[key] = counters.get(key, 0) + 1
    return counters[key]


def _emit_pair(
    tdata: dict,
    tool: str,
    pair_type: str,
    sys_w: str,
    sys_t: str,
    cell: dict,
    counters: dict,
    curator_model: str,
    curator_date: str,
    rng: random.Random,
) -> list[dict]:
    domain = tdata.get("domain") or _TOOL_DOMAIN[tool]
    sub_domain = tdata.get("sub_domain")
    disamb = tdata["disambiguator_hint"]
    freq = cell.get("frequency_class") or tdata.get("frequency_class", "common")

    # pair_id difficulty slot = warranted-half difficulty
    diff_w = tdata["difficulty_warranted"]
    counter_key = (tool, domain, diff_w, disamb)
    counter = _next_counter(counters, counter_key)
    pair_id = f"{tool}-{domain}-{diff_w}-{disamb}-{counter:03d}"

    # Calibrated-agent expectation: only medium+ difficulty really warrants a call.
    warranted_expect = diff_w in ("medium", "hard", "extreme")

    if pair_type == "A":
        # warranted half
        rec_w = _build_record(
            full_id=make_prompt_id(pair_id, shortuuid=shortuuid(pair_id, 0)),
            pair_id=pair_id,
            condition="tool_warranted",
            pair_type="A",
            tool=tool,
            domain=domain,
            sub_domain=sub_domain,
            difficulty_value=diff_w,
            difficulty_reasoning=tdata["reasoning_warranted"],
            human_feasibility=tdata["human_feasibility_warranted"],
            frequency_class=freq,
            register_tone=cell["register_tone"],
            register_form=cell["register_form"],
            register_length=cell["register_length"],
            system_prompt_id=sys_w,
            user_prompt=tdata["user_prompt_warranted"],
            expected_tool_call=warranted_expect,
            expected_pair_behavior=(
                "Type A: warranted half probes whether the model recognizes the "
                "tool is needed; trivial sibling holds register constant with an "
                "in-head-easy task. Calibrated agent calls on the warranted half "
                "and not the trivial one."
            ),
            tags=tdata["tags"],
            curator_model=curator_model,
            curator_date=curator_date,
        )
        rec_t = _build_record(
            full_id=make_prompt_id(pair_id, shortuuid=shortuuid(pair_id, 1)),
            pair_id=pair_id,
            condition="tool_trivial",
            pair_type="A",
            tool=tool,
            domain=domain,
            sub_domain=sub_domain,
            difficulty_value=tdata["difficulty_trivial"],
            difficulty_reasoning=tdata["reasoning_trivial"],
            human_feasibility=tdata["human_feasibility_trivial"],
            frequency_class=freq,
            register_tone=cell["register_tone"],
            register_form=cell["register_form"],
            register_length=cell["register_length"],
            system_prompt_id=sys_t,
            user_prompt=tdata["user_prompt_trivial"],
            expected_tool_call=False,
            expected_pair_behavior=(
                "Type A trivial sibling: same tool target, in-head-easy task."
            ),
            tags=tdata["tags"],
            curator_model=curator_model,
            curator_date=curator_date,
        )
        return [rec_w, rec_t]

    elif pair_type == "B":
        # Both halves share the warranted user_prompt; differ only in system prompt.
        prompt = tdata["user_prompt_warranted"]
        rec_w = _build_record(
            full_id=make_prompt_id(pair_id, shortuuid=shortuuid(pair_id, 0)),
            pair_id=pair_id,
            condition="tool_warranted",
            pair_type="B",
            tool=tool,
            domain=domain,
            sub_domain=sub_domain,
            difficulty_value=diff_w,
            difficulty_reasoning=tdata["reasoning_warranted"],
            human_feasibility=tdata["human_feasibility_warranted"],
            frequency_class=freq,
            register_tone=cell["register_tone"],
            register_form=cell["register_form"],
            register_length=cell["register_length"],
            system_prompt_id=sys_w,
            user_prompt=prompt,
            expected_tool_call=warranted_expect,
            expected_pair_behavior=(
                "Type B affordance pair: identical user_prompt across halves; "
                "warranted half exposes the tool, no-tools half does not. "
                "Calibrated agent should call when available; refuse / hedge "
                "rather than fabricate when not."
            ),
            tags=tdata["tags"] + ["no_affordance"],
            curator_model=curator_model,
            curator_date=curator_date,
        )
        rec_t = _build_record(
            full_id=make_prompt_id(pair_id, shortuuid=shortuuid(pair_id, 1)),
            pair_id=pair_id,
            condition="no_tools_available",
            pair_type="B",
            tool=tool,
            domain=domain,
            sub_domain=sub_domain,
            difficulty_value=diff_w,
            difficulty_reasoning=(
                tdata["reasoning_warranted"]
                + " Tool not available in this half; correct behavior is to "
                "refuse / hedge rather than fabricate."
            ),
            human_feasibility=tdata["human_feasibility_warranted"],
            frequency_class=freq,
            register_tone=cell["register_tone"],
            register_form=cell["register_form"],
            register_length=cell["register_length"],
            system_prompt_id=sys_t,
            user_prompt=prompt,
            expected_tool_call=False,
            expected_pair_behavior=(
                "Type B no-tools half: identical user_prompt; tool removed."
            ),
            tags=tdata["tags"] + ["no_affordance"],
            curator_model=curator_model,
            curator_date=curator_date,
        )
        return [rec_w, rec_t]

    else:
        raise ValueError(f"unknown pair_type: {pair_type}")


_FORBIDDEN_IN_TRIVIAL = ("calculator", "compute", "search", "lookup")


def check_anti_leakage(records: list[dict]) -> list[str]:
    """Anti-leakage check: in Type A trivial halves (where the task itself
    is intentionally in-head-easy), surface keywords like 'calculator',
    'compute', 'search', 'lookup' could bias the model toward not calling.

    Type B no-tools halves are exempt by design — the user_prompt is held
    constant across both halves of the affordance pair, so the surface
    text is the same as the warranted half.
    """
    violations = []
    for r in records:
        if r["condition"] != "tool_trivial":
            continue
        text = r["user_prompt"].lower()
        for kw in _FORBIDDEN_IN_TRIVIAL:
            if kw in text:
                violations.append(f"{r['id']}: contains forbidden keyword '{kw}'")
    return violations


def sample_spot_review(records: list[dict], rng: random.Random, fraction: float) -> list[dict]:
    """Pick ~fraction of pairs for human review, biased toward boundaries.

    Returns a list of dicts with pair_id, reason."""
    by_pair: dict[str, list[dict]] = {}
    for r in records:
        by_pair.setdefault(r["pair_id"], []).append(r)
    pairs = list(by_pair.keys())
    target_n = max(10, int(round(fraction * len(pairs))))

    picked = []
    reasons = []

    # boundary pairs: extreme difficulty
    extremes = [p for p in pairs if any(
        r["difficulty_label"]["value"] == "extreme" for r in by_pair[p]
    )]
    for p in extremes[: target_n // 4]:
        picked.append(p)
        reasons.append("extreme difficulty band — boundary case")

    # type B no-tools (affordance probe correctness is subtle)
    type_b = [p for p in pairs if by_pair[p][0]["pair_type"] == "B" and p not in picked]
    rng.shuffle(type_b)
    for p in type_b[: target_n // 4]:
        picked.append(p)
        reasons.append("Type B affordance probe — review refusal-vs-fabrication framing")

    # KB-grounded
    kb_grounded = [
        p for p in pairs
        if by_pair[p][0]["tool_target"] in ("general_knowledge_lookup", "user_knowledge_lookup")
        and p not in picked
    ]
    rng.shuffle(kb_grounded)
    for p in kb_grounded[: target_n // 4]:
        picked.append(p)
        reasons.append("KB-grounded prompt — verify entry resolves correctly")

    # random fill across remaining
    remaining = [p for p in pairs if p not in picked]
    rng.shuffle(remaining)
    while len(picked) < target_n and remaining:
        p = remaining.pop()
        picked.append(p)
        reasons.append("random sample across distribution")

    return [{"pair_id": pid, "reason": rs} for pid, rs in zip(picked, reasons)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spot-review-fraction", type=float, default=0.05)
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    spec = yaml.safe_load(SPEC_PATH.read_text())
    meta = spec.get("_metadata", {})
    curator_model = meta["llm_curator_model"]
    curator_date = meta["llm_curator_date"]
    if not isinstance(curator_date, str):
        curator_date = curator_date.isoformat()
    seed = meta.get("random_seed", 0)
    rng = random.Random(seed)

    records: list[dict] = []
    counters: dict = {}
    for cell in spec["cells"]:
        records.extend(expand_cell(cell, rng, counters, curator_model, curator_date))

    # anti-leakage check
    violations = check_anti_leakage(records)
    if violations:
        print("ANTI-LEAKAGE VIOLATIONS:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 2

    # schema validation
    if not args.no_validate:
        import jsonschema
        schema = json.loads(SCHEMA_PATH.read_text())
        validator = jsonschema.Draft202012Validator(schema)
        errors = []
        for r in records:
            for err in validator.iter_errors(r):
                errors.append(f"{r['id']}: {err.message} at {list(err.path)}")
        if errors:
            print("SCHEMA VIOLATIONS:", file=sys.stderr)
            for e in errors[:25]:
                print(f"  {e}", file=sys.stderr)
            print(f"  ... ({len(errors)} total)", file=sys.stderr)
            return 3

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_pairs = len(records) // 2
    print(f"wrote {OUT_PATH.relative_to(STUDY_ROOT.parent.parent)}: "
          f"{n_pairs} pairs, {len(records)} records")

    # distribution summary
    dist: dict = {}
    for r in records:
        key = (r["tool_target"], r["difficulty_label"]["value"])
        dist[key] = dist.get(key, 0) + 1
    tools = sorted({k[0] for k in dist})
    bands = ["trivial", "easy", "medium", "hard", "extreme"]
    print("\nrecord count per (tool × difficulty):")
    print(f"  {'tool':<28}  " + "  ".join(f"{b:>8}" for b in bands))
    for t in tools:
        row = "  ".join(f"{dist.get((t, b), 0):>8}" for b in bands)
        print(f"  {t:<28}  {row}")

    n_a = sum(1 for r in records if r["pair_type"] == "A") // 2
    n_b = sum(1 for r in records if r["pair_type"] == "B") // 2
    print(f"\npair_type: A={n_a}, B={n_b}")
    common = sum(1 for r in records if r["frequency_class"] == "common") // 2
    edge = sum(1 for r in records if r["frequency_class"] == "edge") // 2
    print(f"frequency_class: common={common} pairs, edge={edge} pairs")

    # spot review
    spot = sample_spot_review(records, rng, args.spot_review_fraction)
    SPOT_REVIEW_PATH.write_text(yaml.safe_dump(
        {
            "_metadata": {
                "fraction": args.spot_review_fraction,
                "n_pairs_total": n_pairs,
                "n_pairs_sampled": len(spot),
                "generated_by": curator_model,
                "generated_on": curator_date,
            },
            "samples": spot,
        },
        sort_keys=False,
    ))
    print(f"\nwrote spot_review.yaml: {len(spot)} pairs for human review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
