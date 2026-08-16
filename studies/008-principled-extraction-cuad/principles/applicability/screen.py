import json
import math

from common import FROZEN, config, dataset, eligible_categories, principles

DISQUALIFYING = {
    "never_fires": "no decision in scope is labelled applicable; nothing can be scored",
    "gold_presence_gated": (
        "every applicable decision is gold-present; the applicable x gold-absent cell "
        "is empty, so compliance cannot vary independently of correctness (D-21)"
    ),
    "gold_absence_gated": (
        "every applicable decision is gold-absent; the applicable x gold-present cell "
        "is empty (D-21)"
    ),
    "degenerate_universal": (
        "applicable to every decision in scope; it cannot localise an effect and a "
        "citation metric over it measures nothing"
    ),
}


def phi(a, b, c, d):
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denom == 0:
        return None
    return (a * d - b * c) / denom


def cells(rows):
    a = sum(1 for r in rows if r["applicable"] and r["gold_present"])
    b = sum(1 for r in rows if r["applicable"] and not r["gold_present"])
    c = sum(1 for r in rows if not r["applicable"] and r["gold_present"])
    d = sum(1 for r in rows if not r["applicable"] and not r["gold_present"])
    return {
        "applicable_present": a,
        "applicable_absent": b,
        "notapplicable_present": c,
        "notapplicable_absent": d,
    }


def verdict_for(cell, cfg):
    a = cell["applicable_present"]
    b = cell["applicable_absent"]
    c = cell["notapplicable_present"]
    d = cell["notapplicable_absent"]
    n = a + b + c + d
    reasons = []
    if a + b == 0:
        reasons.append("never_fires")
    elif b == 0:
        reasons.append("gold_presence_gated")
    elif a == 0:
        reasons.append("gold_absence_gated")
    if c + d == 0 and a + b > 0:
        reasons.append("degenerate_universal")
    rate = (a + b) / n if n else None
    warnings = []
    if rate is not None and reasons == []:
        if rate >= cfg["screening"]["degenerate_high"]:
            reasons.append("degenerate_universal")
        elif rate >= cfg["screening"]["near_degenerate_high"]:
            warnings.append("near_degenerate_frequency")
        elif rate <= cfg["screening"]["degenerate_low"]:
            warnings.append("degenerate_rarity")
    return {
        "verdict": "fail" if reasons else "pass",
        "reasons": reasons,
        "reason_notes": [DISQUALIFYING[r] for r in reasons],
        "warnings": warnings,
        "rate_in_scope": round(rate, 4) if rate is not None else None,
        "phi_in_scope": round(p, 4) if (p := phi(a, b, c, d)) is not None else None,
        "p_present_given_applicable": round(a / (a + b), 4) if (a + b) else None,
        "p_present_given_not_applicable": round(c / (c + d), 4) if (c + d) else None,
    }


def build_rows(labels, data, records, categories):
    rows = []
    for contract_id, per_category in labels.items():
        record = data.record(contract_id)
        gold = data.gold(contract_id)
        for pid, principle in records.items():
            for category in eligible_categories(principle, categories):
                label = gold[category]
                rows.append(
                    {
                        "contract_id": contract_id,
                        "split": record["split"],
                        "category": category,
                        "principle": pid,
                        "applicable": pid in per_category.get(category, []),
                        "gold_present": (not label.is_impossible) and bool(label.spans),
                    }
                )
    return rows


def screen(labels, cfg=None):
    cfg = cfg or config()
    data = dataset()
    records = principles()
    categories = data.categories
    rows = build_rows(labels, data, records, categories)

    out = {"n_decisions_screened": len(rows), "principles": {}}
    for pid in sorted(records):
        mine = [r for r in rows if r["principle"] == pid]
        entry = {
            "scope": records[pid].get("scope") or [],
            "n_decisions_in_scope": len(mine),
            "union": {"cells": cells(mine)},
        }
        entry["union"].update(verdict_for(entry["union"]["cells"], cfg))
        for split in cfg["splits"]:
            subset = [r for r in mine if r["split"] == split]
            block = {"cells": cells(subset)}
            block.update(verdict_for(block["cells"], cfg))
            entry[split] = block
        entry["splits_agree"] = len(
            {entry[s]["verdict"] for s in cfg["splits"]}
        ) == 1
        entry["disqualified"] = entry["union"]["verdict"] == "fail"
        out["principles"][pid] = entry

    out["disqualified"] = sorted(
        pid for pid, e in out["principles"].items() if e["disqualified"]
    )
    out["qualified"] = sorted(
        pid for pid, e in out["principles"].items() if not e["disqualified"]
    )
    return out


def main():
    from freeze import load_labels

    report = screen(load_labels())
    (FROZEN / "screening.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("disqualified", "qualified")}, indent=2))


if __name__ == "__main__":
    main()
