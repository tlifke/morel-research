import argparse
import json
import re
import sys

from common import FROZEN, WORK, config, dataset, manifest

LABELS = {"applicable", "not_applicable"}
CONFIDENCE = {"high", "medium", "low"}


def norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def parse_response(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("answers"), list):
        return raw["answers"]
    if isinstance(raw, str):
        match = re.search(r"\[.*\]", raw, re.S)
        if match:
            return json.loads(match.group(0))
    raise ValueError("response is not a JSON array")


def validate(contract_id, raw, questions, text, title=""):
    body = norm(title + " " + text)
    answers = parse_response(raw)
    by_qid = {}
    problems = []
    for item in answers:
        if not isinstance(item, dict) or "qid" not in item:
            problems.append({"qid": None, "reason": "row_not_a_mapping"})
            continue
        by_qid[item["qid"]] = item
    rows = []
    for question in questions:
        qid = question["qid"]
        item = by_qid.get(qid)
        if item is None:
            problems.append({"qid": qid, "reason": "missing_answer"})
            continue
        label = item.get("label")
        if label not in LABELS:
            problems.append({"qid": qid, "reason": "bad_label:%r" % label})
            continue
        confidence = item.get("confidence")
        if confidence not in CONFIDENCE:
            confidence = None
            problems.append({"qid": qid, "reason": "bad_confidence", "kept": True})
        evidence = item.get("evidence")
        if label == "applicable":
            if not isinstance(evidence, str) or len(evidence.strip()) < 10:
                problems.append({"qid": qid, "reason": "missing_evidence"})
                continue
            if norm(evidence) not in body:
                problems.append(
                    {
                        "qid": qid,
                        "reason": "evidence_not_verbatim",
                        "evidence": evidence[:160],
                    }
                )
                continue
        rows.append(
            {
                "contract_id": contract_id,
                "qid": qid,
                "principle": question["principle"],
                "category": question["category"],
                "label": label,
                "confidence": confidence,
                "evidence": evidence if label == "applicable" else None,
                "reason": (item.get("reason") or "")[:400],
            }
        )
    extra = sorted(set(by_qid) - {q["qid"] for q in questions})
    if extra:
        problems.append({"qid": None, "reason": "unknown_qids:%s" % ",".join(extra)})
    return rows, problems


def ingest(allow_missing=False):
    cfg = config()
    man = manifest()
    data = dataset()
    questions = man["questions"]
    rows, problems, missing = [], [], []
    for entry in man["contracts"]:
        contract_id = entry["contract_id"]
        path = WORK / "responses" / f"{contract_id}.json"
        if not path.exists():
            missing.append(contract_id)
            continue
        got, bad = validate(
            contract_id,
            json.loads(path.read_text()),
            questions,
            data.texts[contract_id],
            data.record(contract_id)["title"],
        )
        rows.extend(got)
        for item in bad:
            item["contract_id"] = contract_id
            problems.append(item)
    if missing and not allow_missing:
        sys.exit(
            "no response for %d contract(s), first: %s. Run the labeler or pass "
            "--allow-missing to freeze a partial artifact." % (len(missing), missing[0])
        )
    return cfg, man, rows, problems, missing


def load_labels(rows=None):
    if rows is None:
        _, _, rows, _, _ = ingest(allow_missing=True)
    labels = {}
    for row in rows:
        per = labels.setdefault(row["contract_id"], {})
        bucket = per.setdefault(row["category"], [])
        if row["label"] == "applicable":
            bucket.append(row["principle"])
    for per in labels.values():
        for category in per:
            per[category] = sorted(set(per[category]))
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-missing", action="store_true")
    ap.add_argument("--max-invalid-rate", type=float, default=0.02)
    args = ap.parse_args()

    cfg, man, rows, problems, missing = ingest(allow_missing=args.allow_missing)
    expected = len(man["questions"]) * (len(man["contracts"]) - len(missing))
    dropped = [p for p in problems if not p.get("kept")]
    invalid_rate = len(dropped) / expected if expected else 0.0

    (WORK / "judgements.json").write_text(json.dumps(rows, indent=2))
    (WORK / "problems.json").write_text(
        json.dumps({"missing_contracts": missing, "problems": problems}, indent=2)
    )

    if invalid_rate > args.max_invalid_rate:
        sys.exit(
            "invalid judgement rate %.4f exceeds %.4f (%d of %d). See work/problems.json; "
            "re-run the labeler on the affected contracts before freezing."
            % (invalid_rate, args.max_invalid_rate, len(dropped), expected)
        )

    labels = load_labels(rows)

    from screen import screen

    screening = screen(labels, cfg)
    FROZEN.mkdir(parents=True, exist_ok=True)
    (FROZEN / "screening.json").write_text(json.dumps(screening, indent=2))

    labeler = dict(cfg["labeler"])
    labeler.update(
        {
            "n_judgements": len(rows),
            "n_judgements_expected": expected,
            "invalid_rate": round(invalid_rate, 4),
            "n_contracts": len(man["contracts"]) - len(missing),
            "splits": cfg["splits"],
            "text_cap": cfg["text_cap"],
            "n_truncated_contracts": sum(
                1 for c in man["contracts"] if c["truncated"] and c["contract_id"] not in missing
            ),
            "screening_file": "frozen/screening.json",
            "d21_disqualified": screening["disqualified"],
            "judgement_record": "work/judgements.json (gitignored; carries contract text)",
        }
    )

    spot_check = {}
    labels_path = FROZEN / "spot_check.json"
    if labels_path.exists():
        spot_check = json.loads(labels_path.read_text())

    def payload(instances, note):
        return {
            "version": cfg["version"] + note,
            "principle_set_version": cfg["principle_set_version"],
            "labeler": labeler,
            "spot_check": spot_check,
            "instances": instances,
        }

    full = payload(labels, "")
    (FROZEN / f"applicability-{cfg['version']}.json").write_text(
        json.dumps(full, indent=2)
    )

    keep = set(screening["qualified"])
    scored = {
        cid: {
            cat: [p for p in pids if p in keep]
            for cat, pids in per.items()
        }
        for cid, per in labels.items()
    }
    (FROZEN / f"applicability-{cfg['version']}.scored.json").write_text(
        json.dumps(payload(scored, "-scored"), indent=2)
    )

    print(
        json.dumps(
            {
                "n_contracts": labeler["n_contracts"],
                "n_judgements": len(rows),
                "invalid_rate": labeler["invalid_rate"],
                "n_applicable": sum(len(v) for per in labels.values() for v in per.values()),
                "d21_disqualified": screening["disqualified"],
                "d21_qualified": screening["qualified"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
