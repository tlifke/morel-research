import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

STUDY = Path(__file__).resolve().parent.parent
PILOT = STUDY / "principles" / "pilot"
PROMPT = PILOT / "prompts" / "proposer_v1.md"
PAIRS = PILOT / "mined_pairs.jsonl"
RESPONSES = STUDY / "data" / "responses"

MODEL = "claude-opus-5"
PROMPT_VERSION = "proposer_v1"
TEMPERATURE = 1.0
MAX_TOKENS = 8000
TYPES = {"constraint", "procedure", "preference", "disambiguation", "absence"}


def system_and_body(text):
    head, rest = text.split("## System", 1)
    return rest.strip()


def category_block(categories):
    rows = []
    with open(STUDY / "data" / "raw" / "category_descriptions.csv", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            keys = list(row)
            name = row[keys[0]].removeprefix("Category: ")
            if name in categories:
                rows.append(
                    "- **%s** — %s (%s)"
                    % (
                        name,
                        row[keys[1]].removeprefix("Description: ").strip(),
                        row[keys[2]].removeprefix("Answer Format: ").strip(),
                    )
                )
    return "\n".join(rows)


def render_side(side):
    tag = "GOLD ABSENT (is_impossible) — this passage was NOT annotated" if side[
        "gold_status"
    ] == "absent" else "gold category: %s" % side["category"]
    return (
        "  contract: %s\n  %s\n  offsets: [%d:%d]\n  text: |\n%s"
        % (
            side["contract_id"],
            tag,
            side["start"],
            side["end"],
            "\n".join("    " + line for line in side["text"].splitlines()),
        )
    )


def pair_block(pairs):
    out = []
    for p in pairs:
        out.append(
            "### %s (%s, similarity %.3f, same contract: %s)\n\n"
            "A:\n%s\n\nB:\n%s\n"
            % (
                p["pair_id"],
                p["kind"],
                p["similarity"],
                p["same_contract"],
                render_side(p["left"]),
                render_side(p["right"]),
            )
        )
    return "\n".join(out)


def extract_yaml(text):
    fence = re.search(r"```(?:yaml)?\s*\n(.*?)```", text, re.S)
    return fence.group(1) if fence else text


def mechanical_filter(records, valid_ids, batch_id):
    kept, discarded = [], []

    def drop(rec, reason):
        discarded.append({"batch_id": batch_id, "reason": reason, "record": rec})

    for rec in records:
        if not isinstance(rec, dict):
            drop(rec, "not_a_mapping")
            continue
        ev = rec.get("evidence")
        if not isinstance(ev, list) or not ev:
            drop(rec, "missing_evidence")
            continue
        unknown = [e for e in ev if e not in valid_ids]
        if unknown:
            drop(rec, "evidence_ids_not_in_batch:%s" % ",".join(map(str, unknown)))
            continue
        sketch = rec.get("checker_sketch")
        if not isinstance(sketch, str) or len(sketch.strip()) < 20:
            drop(rec, "missing_checker_sketch")
            continue
        if not isinstance(rec.get("statement"), str) or not rec["statement"].strip():
            drop(rec, "missing_statement")
            continue
        if rec.get("type") not in TYPES:
            drop(rec, "bad_type:%r" % rec.get("type"))
            continue
        kept.append(rec)
    return kept, discarded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-model", default=MODEL)
    ap.add_argument("--batch", action="append")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        cfg = yaml.safe_load((PILOT / "mining_config.yaml").read_text())
        body = system_and_body(PROMPT.read_text())
        cats = category_block(set(cfg["pilot_categories"]))
        pairs = [json.loads(line) for line in open(PAIRS)]
        batches = defaultdict(list)
        for p in pairs:
            batches[p["batch_id"]].append(p)
        for batch_id in sorted(args.batch or batches):
            rendered = body.replace("{{CATEGORY_BLOCK}}", cats).replace(
                "{{PAIR_BLOCK}}", pair_block(batches[batch_id])
            )
            print(f"===== {batch_id} ({len(batches[batch_id])} pairs, "
                  f"{len(rendered)} chars) =====")
            print(rendered)
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ANTHROPIC_API_KEY is not set. The proposer is pinned to "
            f"{MODEL}; substituting another model would break the "
            "provenance stamp on every candidate. Export the key and re-run."
        )

    from anthropic import Anthropic

    cfg = yaml.safe_load((PILOT / "mining_config.yaml").read_text())
    template = PROMPT.read_text()
    body = system_and_body(template)
    cats = category_block(set(cfg["pilot_categories"]))

    pairs = [json.loads(line) for line in open(PAIRS)]
    batches = defaultdict(list)
    for p in pairs:
        batches[p["batch_id"]].append(p)
    selected = sorted(args.batch or batches)

    client = Anthropic()
    RESPONSES.mkdir(parents=True, exist_ok=True)
    all_kept, all_discarded = [], []

    for batch_id in selected:
        batch = batches[batch_id]
        prompt = body.replace("{{CATEGORY_BLOCK}}", cats).replace(
            "{{PAIR_BLOCK}}", pair_block(batch)
        )
        msg = client.messages.create(
            model=args.api_model,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in msg.content if b.type == "text")
        (RESPONSES / f"proposer_v1_{batch_id}.json").write_text(
            json.dumps(
                {
                    "batch_id": batch_id,
                    "model": MODEL,
                    "api_model": args.api_model,
                    "prompt_version": PROMPT_VERSION,
                    "temperature": TEMPERATURE,
                    "pair_ids": [p["pair_id"] for p in batch],
                    "prompt": prompt,
                    "response": raw,
                    "usage": msg.usage.model_dump(),
                },
                indent=2,
            )
        )
        try:
            parsed = yaml.safe_load(extract_yaml(raw))
        except yaml.YAMLError as exc:
            all_discarded.append(
                {"batch_id": batch_id, "reason": f"yaml_parse_error:{exc}", "record": None}
            )
            continue
        records = [r for r in (parsed or []) if isinstance(r, dict) and "statement" in r]
        kept, discarded = mechanical_filter(
            records, {p["pair_id"] for p in batch}, batch_id
        )
        for rec in kept:
            rec["provenance"] = "data_mined"
            rec["proposer"] = {
                "model": MODEL,
                "prompt_version": PROMPT_VERSION,
                "batch_id": batch_id,
            }
        all_kept.extend(kept)
        all_discarded.extend(discarded)

    (PILOT / "proposer_run.json").write_text(
        json.dumps(
            {
                "model": MODEL,
                "api_model": args.api_model,
                "prompt_version": PROMPT_VERSION,
                "temperature": TEMPERATURE,
                "batches": selected,
                "n_proposed": len(all_kept) + len(all_discarded),
                "n_kept_by_mechanical_filter": len(all_kept),
                "n_discarded": len(all_discarded),
                "discarded": all_discarded,
                "surviving": all_kept,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "n_proposed": len(all_kept) + len(all_discarded),
                "n_kept": len(all_kept),
                "n_discarded": len(all_discarded),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
