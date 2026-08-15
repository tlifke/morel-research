import json
import sys
from pathlib import Path

import yaml

STUDY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(STUDY / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from checkers import lexicons as L  # noqa: E402
from checkers.span_predicates import (  # noqa: E402
    g05_entitlement_signal,
    g05_entitlement_signal_repaired,
    g06_administration_only,
)
from checkers.textutil import cached_sentences  # noqa: E402
from cuad_dataset import CuadDataset  # noqa: E402

CATEGORY = "Revenue/Profit Sharing"


def load_labels():
    path = Path(__file__).resolve().parent / "handscore_labels.yaml"
    return yaml.safe_load(path.read_text())


def gold_span_agreement(dataset, labels):
    index = {(row["contract"], row["index"]): row for row in labels["spans"]}
    rows = []
    for contract_id in dataset.contract_ids("dev"):
        for i, span in enumerate(dataset.gold(contract_id)[CATEGORY].spans):
            hand = index[(contract_id, i)]
            rows.append(
                {
                    "contract": contract_id,
                    "index": i,
                    "hand_g05_responsive": hand["g05_responsive"],
                    "as_written_signal": g05_entitlement_signal(span.text),
                    "repaired_signal": g05_entitlement_signal_repaired(span.text),
                    "as_written_g06_admin_only": g06_administration_only(span.text),
                    "hand_g06_admin_only": hand["g06_administration_only"],
                }
            )

    def summarise(key):
        agree = sum(1 for r in rows if bool(r[key]) == r["hand_g05_responsive"])
        false_fail = sum(
            1 for r in rows if r["hand_g05_responsive"] and not r[key]
        )
        false_pass = sum(
            1 for r in rows if (not r["hand_g05_responsive"]) and r[key]
        )
        return {
            "n": len(rows),
            "agreement": round(agree / len(rows), 4),
            "false_fail": false_fail,
            "false_fail_rate": round(false_fail / len(rows), 4),
            "false_pass": false_pass,
        }

    spurious_equity = [
        r
        for r in rows
        if r["as_written_signal"] == "equity" and r["repaired_signal"] != "equity"
    ]
    return rows, {
        "as_written": summarise("as_written_signal"),
        "repaired": summarise("repaired_signal"),
        "as_written_passes_via_spurious_equity_match": len(spurious_equity),
        "g06_admin_flag_on_gold_spans": {
            "checker": sum(1 for r in rows if r["as_written_g06_admin_only"]),
            "hand": sum(1 for r in rows if r["hand_g06_admin_only"]),
        },
    }


def negative_sentence_scan(dataset):
    negatives = [
        cid
        for cid in dataset.contract_ids("dev")
        if dataset.gold(cid)[CATEGORY].is_impossible
    ]
    as_written = {}
    repaired = {}
    n_sentences = 0
    for contract_id in negatives:
        for _, _, sentence in cached_sentences(dataset.texts[contract_id]):
            body = " ".join(sentence.split())
            if len(body) < 40:
                continue
            n_sentences += 1
            a = g05_entitlement_signal(body)
            b = g05_entitlement_signal_repaired(body)
            if a:
                as_written[a] = as_written.get(a, 0) + 1
            if b:
                repaired[b] = repaired.get(b, 0) + 1
    return {
        "n_rps_absent_contracts": len(negatives),
        "n_sentences_scanned": n_sentences,
        "as_written_passing_sentences": sum(as_written.values()),
        "as_written_by_branch": as_written,
        "repaired_passing_sentences": sum(repaired.values()),
        "repaired_by_branch": repaired,
        "reading": (
            "every sentence here sits in a contract CUAD rules Revenue/Profit "
            "Sharing absent, so a passing sentence is a candidate false pass"
        ),
    }


def g06_trigger_agreement(dataset, labels):
    hand = labels["g06_trigger_sentences"]["items"]
    fired = []
    for contract_id in dataset.contract_ids("dev"):
        gold = dataset.gold(contract_id)[CATEGORY]
        for start, end, sentence in cached_sentences(dataset.texts[contract_id]):
            body = " ".join(sentence.split())
            if len(body) < 40:
                continue
            if L.ADMINISTRATION.search(body) and L.ROYALTY_TERM.search(body):
                fired.append(
                    {
                        "contract": contract_id,
                        "in_gold": any(
                            start < s.end and s.start < end for s in gold.spans
                        ),
                    }
                )
    true_admin = sum(1 for row in hand if row["really_administration"])
    return {
        "n_trigger_sentences": len(fired),
        "n_hand_labelled": len(hand),
        "n_really_administration": true_admin,
        "trigger_precision": round(true_admin / len(hand), 4) if hand else None,
        "n_trigger_sentences_inside_gold_rps_spans": sum(
            1 for row in fired if row["in_gold"]
        ),
    }


def main():
    dataset = CuadDataset()
    labels = load_labels()
    rows, summary = gold_span_agreement(dataset, labels)
    out = {
        "meta": labels["meta"],
        "g05": {
            "gold_span_agreement": summary,
            "negative_sentence_scan": negative_sentence_scan(dataset),
            "per_span": rows,
        },
        "g06": {"trigger_agreement": g06_trigger_agreement(dataset, labels)},
    }
    path = Path(__file__).resolve().parent / "handscore.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["g05"]["gold_span_agreement"], indent=2))
    print(json.dumps(out["g05"]["negative_sentence_scan"], indent=2))
    print(json.dumps(out["g06"], indent=2))


if __name__ == "__main__":
    main()
