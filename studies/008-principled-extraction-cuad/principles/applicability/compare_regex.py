import json
import sys

from common import FROZEN, HERE, STUDY, config, dataset, eligible_categories, principles

PILOT = STUDY / "principles" / "pilot"
for path in (str(STUDY / "scripts"), str(PILOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from round2.checkers.checkers2 import REGISTRY, set_corpus  # noqa: E402
from round2.checkers.run_footprints2 import GOLD_DEPENDENCY  # noqa: E402
from screen import cells, verdict_for  # noqa: E402


def checker_scope(checker, categories):
    scope = checker.eligible or checker.scope or list(categories)
    return [c for c in categories if c in scope]


def main():
    judgements = {}
    for row in json.loads((HERE / "work" / "judgements.json").read_text()):
        judgements[(row["contract_id"], row["category"], row["principle"])] = row

    def detail(row, pid):
        record = judgements.get((row[0], row[1], pid), {})
        return {
            "contract_id": row[0],
            "category": row[1],
            "llm_label": record.get("label"),
            "llm_confidence": record.get("confidence"),
            "llm_reason": record.get("reason"),
            "llm_evidence": record.get("evidence"),
        }

    cfg = config()
    data = dataset()
    records = principles()
    categories = data.categories
    labels = json.loads(
        (FROZEN / f"applicability-{cfg['version']}.json").read_text()
    )["instances"]

    contract_ids = [cid for cid in labels]
    instances = {cid: data.get_instance(cid) for cid in contract_ids}
    set_corpus({cid: inst.text for cid, inst in instances.items()})

    report = {"version": cfg["version"], "principles": {}}
    for pid, round2_ids in cfg["regex_comparison"]["lineage"].items():
        entry = {"round2_checkers": round2_ids, "comparisons": {}}
        if not round2_ids:
            entry["note"] = "no pilot regex checker exists for this principle"
            report["principles"][pid] = entry
            continue
        llm_scope = eligible_categories(records[pid], categories)
        for rid in round2_ids:
            checker = REGISTRY[rid]
            scope = [c for c in checker_scope(checker, categories) if c in llm_scope]
            rows = []
            regex_rows = []
            for cid in contract_ids:
                instance = instances[cid]
                for category in scope:
                    llm = pid in labels[cid].get(category, [])
                    regex = bool(checker.applies(instance, category))
                    rows.append((cid, category, llm, regex))
                    label = instance.gold[category]
                    regex_rows.append(
                        {
                            "applicable": regex,
                            "gold_present": (not label.is_impossible)
                            and bool(label.spans),
                        }
                    )
            both = sum(1 for r in rows if r[2] and r[3])
            llm_only = [r for r in rows if r[2] and not r[3]]
            regex_only = [r for r in rows if r[3] and not r[2]]
            neither = sum(1 for r in rows if not r[2] and not r[3])
            n = len(rows)
            agree = both + neither
            regex_cells = cells(regex_rows)
            regex_screen = verdict_for(regex_cells, cfg)
            regex_screen["cells"] = regex_cells
            regex_screen["declared_gold_dependency"] = GOLD_DEPENDENCY[rid]
            entry["comparisons"][rid] = {
                "regex_screening_same_decisions": regex_screen,
                "n_decisions_compared": n,
                "scope_compared": scope,
                "n_llm_applicable": both + len(llm_only),
                "n_regex_applicable": both + len(regex_only),
                "both": both,
                "llm_only": len(llm_only),
                "regex_only": len(regex_only),
                "neither": neither,
                "agreement": round(agree / n, 4) if n else None,
                "disagreement_rate": round((n - agree) / n, 4) if n else None,
                "jaccard": round(both / (both + len(llm_only) + len(regex_only)), 4)
                if (both + len(llm_only) + len(regex_only))
                else None,
                "examples_llm_only": [detail(r, pid) for r in llm_only[:4]],
                "examples_regex_only": [detail(r, pid) for r in regex_only[:4]],
            }
        report["principles"][pid] = entry

    (FROZEN / "regex_comparison.json").write_text(json.dumps(report, indent=2))
    for pid, entry in report["principles"].items():
        for rid, block in entry.get("comparisons", {}).items():
            print(
                "%s vs %s: n=%d llm=%d regex=%d both=%d disagree=%.3f"
                % (
                    pid,
                    rid,
                    block["n_decisions_compared"],
                    block["n_llm_applicable"],
                    block["n_regex_applicable"],
                    block["both"],
                    block["disagreement_rate"],
                )
            )


if __name__ == "__main__":
    main()
