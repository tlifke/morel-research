import argparse
import json

from common import (
    FROZEN,
    HERE,
    WORK,
    category_definitions,
    clip,
    config,
    dataset,
    principles,
    questions_for,
)

TRUNCATED_NOTE = (
    "NOTE: this contract is longer than the labelling cap. The head and tail are "
    "shown and the middle is omitted. If a question turns on material you cannot "
    "see, answer not_applicable with confidence low and say so in `reason`."
)


def render_questions(pairs, records, definitions, fold):
    lines = []
    for idx, (pid, category) in enumerate(pairs, start=1):
        record = records[pid]
        definition = definitions.get(fold(category).lower(), "")
        lines.append(
            "### q%02d\n\n"
            "- **target category**: %s\n"
            "- **category definition (CUAD v1)**: %s\n"
            "- **principle %s**: %s\n"
            "- **when to consider it**: %s\n"
            % (
                idx,
                category,
                definition,
                pid,
                " ".join(record["statement"].split()),
                " ".join((record.get("trigger_guidance") or "").split()),
            )
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=5)
    args = ap.parse_args()

    cfg = config()
    records = principles()
    data = dataset()
    categories = data.categories
    definitions, fold = category_definitions()
    template = (
        HERE / "prompts" / (cfg["labeler"]["prompt_version"] + ".md")
    ).read_text()
    body = template.split("## System", 1)[1]

    (WORK / "prompts").mkdir(parents=True, exist_ok=True)
    (WORK / "responses").mkdir(parents=True, exist_ok=True)
    (WORK / ".gitignore").write_text("*\n")
    FROZEN.mkdir(parents=True, exist_ok=True)

    pairs = questions_for(sorted(records), records, categories)
    contract_ids = []
    for split in cfg["splits"]:
        contract_ids.extend(data.contract_ids(split))

    manifest = {
        "version": cfg["version"],
        "prompt_version": cfg["labeler"]["prompt_version"],
        "principle_set_version": cfg["principle_set_version"],
        "splits": cfg["splits"],
        "categories": categories,
        "questions": [
            {"qid": "q%02d" % (i + 1), "principle": pid, "category": category}
            for i, (pid, category) in enumerate(pairs)
        ],
        "contracts": [],
    }

    for contract_id in contract_ids:
        record = data.record(contract_id)
        text, truncated = clip(data.texts[contract_id], cfg["text_cap"])
        rendered = (
            body.replace("{{N_QUESTIONS}}", str(len(pairs)))
            .replace("{{CONTRACT_ID}}", contract_id)
            .replace("{{TITLE}}", record["title"])
            .replace("{{TRUNCATION_NOTE}}", TRUNCATED_NOTE if truncated else "")
            .replace("{{CONTRACT_TEXT}}", text)
            .replace(
                "{{QUESTIONS}}", render_questions(pairs, records, definitions, fold)
            )
        )
        (WORK / "prompts" / f"{contract_id}.md").write_text(rendered)
        manifest["contracts"].append(
            {
                "contract_id": contract_id,
                "split": record["split"],
                "n_tokens": record["n_tokens"],
                "n_chars": len(data.texts[contract_id]),
                "truncated": truncated,
            }
        )

    batches = []
    ordered = sorted(
        manifest["contracts"], key=lambda c: c["n_chars"], reverse=True
    )
    n_batches = max(1, (len(ordered) + args.batch_size - 1) // args.batch_size)
    buckets = [[] for _ in range(n_batches)]
    for i, entry in enumerate(ordered):
        buckets[i % n_batches].append(entry["contract_id"])
    for i, bucket in enumerate(buckets, start=1):
        batch_id = "batch_%02d" % i
        (WORK / f"{batch_id}.json").write_text(
            json.dumps({"batch_id": batch_id, "contract_ids": sorted(bucket)}, indent=2)
        )
        batches.append(batch_id)
    manifest["batches"] = batches

    (WORK / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {
                "n_contracts": len(manifest["contracts"]),
                "n_questions_per_contract": len(pairs),
                "n_judgements": len(pairs) * len(manifest["contracts"]),
                "n_truncated": sum(1 for c in manifest["contracts"] if c["truncated"]),
                "n_batches": len(batches),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
