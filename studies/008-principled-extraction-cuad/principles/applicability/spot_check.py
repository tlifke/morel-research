import argparse
import html
import json
import math
import random
import re

import yaml

from common import FROZEN, STUDY, WORK, config, dataset, principles

REVIEWS = STUDY / "reviews"
LABELS_FILE = FROZEN / "spot_check_labels.yaml"
VERDICTS = {"applicable", "not_applicable", "unclear"}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(centre - half, 4), round(centre + half, 4)]


def excerpt(text, quote, window=500):
    if quote:
        needle = re.escape(" ".join(quote.split()[:6]))
        match = re.search(needle.replace(r"\ ", r"\s+"), text, re.I)
        if match:
            start = max(0, match.start() - window)
            return ("..." if start else "") + text[start : match.end() + window] + "..."
    return text[: 2 * window] + "..."


def sample(cfg, judgements, per_principle):
    rng = random.Random(cfg["spot_check"]["seed"])
    by_key = {}
    for row in judgements:
        by_key.setdefault((row["principle"], row["label"]), []).append(row)
    picked = []
    for pid in sorted({r["principle"] for r in judgements}):
        for label in ("applicable", "not_applicable"):
            pool = list(by_key.get((pid, label), []))
            rng.shuffle(pool)
            want = per_principle // 2
            chosen, seen_cat, seen_contract = [], set(), set()
            for row in pool:
                if len(chosen) >= want:
                    break
                if row["category"] in seen_cat and len(seen_cat) < want:
                    continue
                if row["contract_id"] in seen_contract:
                    continue
                chosen.append(row)
                seen_cat.add(row["category"])
                seen_contract.add(row["contract_id"])
            for row in pool:
                if len(chosen) >= want:
                    break
                if row not in chosen:
                    chosen.append(row)
            picked.extend(chosen)
    rng.shuffle(picked)
    return picked


def render(rows, records, data, cfg):
    blocks = []
    for row in rows:
        instance_text = data.texts[row["contract_id"]]
        record = records[row["principle"]]
        blocks.append(
            """
<section id="{sid}">
  <h2>{sid} &mdash; {pid} &times; {category}</h2>
  <p class="meta">contract <code>{cid}</code></p>
  <div class="principle"><b>{pid}</b>: {statement}<br><i>when to consider it:</i> {trigger}</div>
  <p class="q"><b>Does {pid} bear on the {category} decision for this contract?</b></p>
  <details><summary>contract excerpt</summary><pre>{excerpt}</pre></details>
  <details><summary>model answer (open only after you have decided)</summary>
    <p>label <b>{label}</b>, confidence {confidence}</p>
    <p>reason: {reason}</p>
    <p>evidence: <q>{evidence}</q></p>
  </details>
</section>""".format(
                sid=row["sid"],
                pid=row["principle"],
                category=html.escape(row["category"]),
                cid=html.escape(row["contract_id"]),
                statement=html.escape(" ".join(record["statement"].split())),
                trigger=html.escape(
                    " ".join((record.get("trigger_guidance") or "").split())
                ),
                excerpt=html.escape(excerpt(instance_text, row["evidence"])),
                label=row["label"],
                confidence=row["confidence"],
                reason=html.escape(row["reason"] or ""),
                evidence=html.escape(row["evidence"] or "(none — not_applicable)"),
            )
        )
    return """<!doctype html>
<meta charset="utf-8">
<title>Applicability spot-check — study 008</title>
<style>
body {{ font: 15px/1.5 -apple-system, system-ui, sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; }}
section {{ border-top: 1px solid #ddd; padding: 1rem 0; }}
h2 {{ font-size: 1rem; margin: 0 0 .3rem; }}
.meta {{ color: #666; font-size: .85rem; margin: 0 0 .6rem; }}
.principle {{ background: #f6f6f4; padding: .6rem .8rem; border-radius: 4px; }}
.q {{ margin: .8rem 0; }}
pre {{ white-space: pre-wrap; background: #fafafa; padding: .6rem; font-size: .82rem; max-height: 30rem; overflow: auto; }}
code {{ font-size: .82rem; }}
summary {{ cursor: pointer; color: #444; }}
header p {{ color: #444; }}
</style>
<header>
<h1>Applicability spot-check</h1>
<p>Study 008, artifact <code>{version}</code>, labeller <code>{model}</code> / prompt <code>{prompt}</code>.
{n} items, sampled balanced by (principle &times; label) with seed {seed}.</p>
<p>For each item, decide <b>before</b> opening the model answer, and record your verdict in
<code>principles/applicability/frozen/spot_check_labels.yaml</code> as
<code>applicable</code>, <code>not_applicable</code>, or <code>unclear</code>.
Then run <code>uv run python spot_check.py --score</code>.</p>
<p>The excerpt is a window around the model's evidence quote (or the head of the contract where
there is none). The full contract is in <code>principles/applicability/work/prompts/&lt;contract_id&gt;.md</code>.
Gold annotations are deliberately not shown: the labeller did not see them and neither should the
adjudicator, or the agreement number stops measuring the same thing.</p>
</header>
{body}
""".format(
        version=cfg["version"],
        model=cfg["labeler"]["model"],
        prompt=cfg["labeler"]["prompt_version"],
        n=len(rows),
        seed=cfg["spot_check"]["seed"],
        body="\n".join(blocks),
    )


def build():
    cfg = config()
    data = dataset()
    records = principles()
    judgements = json.loads((WORK / "judgements.json").read_text())
    n_principles = len({r["principle"] for r in judgements})
    per_principle = max(2, 2 * (cfg["spot_check"]["n"] // (2 * n_principles)))
    rows = sample(cfg, judgements, per_principle)
    for i, row in enumerate(rows, start=1):
        row["sid"] = "s%03d" % i

    REVIEWS.mkdir(exist_ok=True)
    (REVIEWS / "applicability-spot-check.html").write_text(
        render(rows, records, data, cfg)
    )
    skeleton = {
        "version": cfg["version"],
        "prompt_version": cfg["labeler"]["prompt_version"],
        "reviewer": None,
        "date": None,
        "instructions": (
            "Fill `verdict` for each item with applicable | not_applicable | unclear. "
            "Decide from the contract and the principle before reading the model's answer. "
            "Leave `note` empty unless the item is interesting."
        ),
        "items": [
            {
                "sid": row["sid"],
                "principle": row["principle"],
                "category": row["category"],
                "contract_id": row["contract_id"],
                "model_label": row["label"],
                "model_confidence": row["confidence"],
                "verdict": None,
                "note": None,
            }
            for row in rows
        ],
    }
    if LABELS_FILE.exists():
        raise SystemExit(
            f"{LABELS_FILE} already exists; refusing to overwrite adjudicated labels"
        )
    LABELS_FILE.write_text(yaml.safe_dump(skeleton, sort_keys=False, width=100))
    (FROZEN / "spot_check_sample.json").write_text(json.dumps(rows, indent=2))
    print(
        json.dumps(
            {
                "n_sampled": len(rows),
                "per_principle": per_principle,
                "html": str(REVIEWS / "applicability-spot-check.html"),
                "labels_file": str(LABELS_FILE),
            },
            indent=2,
        )
    )


def score():
    cfg = config()
    payload = yaml.safe_load(LABELS_FILE.read_text())
    items = payload["items"]
    judged = [i for i in items if i.get("verdict") in VERDICTS]
    decided = [i for i in judged if i["verdict"] != "unclear"]
    if not decided:
        raise SystemExit(
            "no adjudicated verdicts found in %s; the human half of the spot check "
            "has not been done, so agreement is unavailable (not zero)." % LABELS_FILE
        )
    agree = sum(1 for i in decided if i["verdict"] == i["model_label"])
    n = len(decided)

    per_label = {}
    for label in ("applicable", "not_applicable"):
        subset = [i for i in decided if i["model_label"] == label]
        k = sum(1 for i in subset if i["verdict"] == label)
        per_label[label] = {
            "n": len(subset),
            "agreement": round(k / len(subset), 4) if subset else None,
            "ci95": wilson(k, len(subset)),
        }

    judgements = json.loads((WORK / "judgements.json").read_text())
    prevalence = sum(1 for r in judgements if r["label"] == "applicable") / len(
        judgements
    )
    weighted = None
    if per_label["applicable"]["agreement"] is not None and per_label[
        "not_applicable"
    ]["agreement"] is not None:
        weighted = round(
            prevalence * per_label["applicable"]["agreement"]
            + (1 - prevalence) * per_label["not_applicable"]["agreement"],
            4,
        )

    per_principle = {}
    for pid in sorted({i["principle"] for i in decided}):
        subset = [i for i in decided if i["principle"] == pid]
        k = sum(1 for i in subset if i["verdict"] == i["model_label"])
        per_principle[pid] = {
            "n": len(subset),
            "agreement": round(k / len(subset), 4),
            "ci95": wilson(k, len(subset)),
        }

    report = {
        "version": cfg["version"],
        "prompt_version": cfg["labeler"]["prompt_version"],
        "reviewer": payload.get("reviewer"),
        "date": payload.get("date"),
        "n_sampled": len(items),
        "n_adjudicated": len(judged),
        "n_unclear": len(judged) - n,
        "sample_design": "balanced by (principle x model label); not a population draw",
        "agreement_on_balanced_sample": round(agree / n, 4),
        "ci95_on_balanced_sample": wilson(agree, n),
        "per_label": per_label,
        "population_applicable_rate": round(prevalence, 4),
        "prevalence_weighted_agreement": weighted,
        "per_principle": per_principle,
    }
    (FROZEN / "spot_check.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(
        "\nre-run `uv run python freeze.py` to stamp this block into the frozen artifact"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true")
    args = ap.parse_args()
    score() if args.score else build()


if __name__ == "__main__":
    main()
