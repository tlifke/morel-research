import argparse
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
RAW = STUDY / "data" / "raw" / "CUADv1.json"
SPLITS = STUDY / "data" / "processed" / "splits"
CATS = STUDY / "data" / "processed" / "categories.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="harness_val")
    ap.add_argument("--n-contracts", type=int, default=2)
    ap.add_argument("--categories", nargs="*", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.split == "test":
        raise SystemExit("test split is sealed until G4")

    members = set(SPLITS.joinpath(args.split + ".txt").read_text().split("\n")) - {""}
    cats = args.categories or json.loads(CATS.read_text())["subset"][:4]

    src = json.loads(RAW.read_text())
    picked = [d for d in src["data"] if d["title"] in members]
    picked.sort(key=lambda d: len(d["paragraphs"][0]["context"]))
    n = len(picked)
    k = min(args.n_contracts, n)
    if k >= n:
        pass
    elif k <= 5:
        qs = sorted([0.5, 0.9, 0.25, 0.75, 0.1][:k])
        picked = [picked[min(n - 1, int(q * n))] for q in qs]
    else:
        picked = [picked[round(i * (n - 1) / (k - 1))] for i in range(k)]

    out = {"version": src.get("version", "1.0"), "data": []}
    for d in picked:
        p = d["paragraphs"][0]
        qas = [q for q in p["qas"] if q["id"].rsplit("__", 1)[-1] in cats]
        out["data"].append(
            {"title": d["title"], "paragraphs": [{"context": p["context"], "qas": qas}]}
        )

    Path(args.out).write_text(json.dumps(out))

    n_q = sum(len(x["paragraphs"][0]["qas"]) for x in out["data"])
    n_pos = sum(
        1
        for x in out["data"]
        for q in x["paragraphs"][0]["qas"]
        if not q["is_impossible"]
    )
    print(
        json.dumps(
            {
                "split": args.split,
                "contracts": [x["title"] for x in out["data"]],
                "chars": [len(x["paragraphs"][0]["context"]) for x in out["data"]],
                "categories": cats,
                "questions": n_q,
                "answerable_questions": n_pos,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
