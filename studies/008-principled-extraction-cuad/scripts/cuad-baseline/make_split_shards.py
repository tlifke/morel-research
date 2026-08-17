import argparse
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
RAW = STUDY / "data" / "raw" / "CUADv1.json"
SPLITS = STUDY / "data" / "processed" / "splits"
CATS = STUDY / "data" / "processed" / "categories.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--group-size", type=int, default=4)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    if args.split == "test":
        raise SystemExit("test split is sealed until G4")

    members = [
        l.strip()
        for l in SPLITS.joinpath(args.split + ".txt").read_text().splitlines()
        if l.strip()
    ]
    if "test" in {args.split}:
        raise SystemExit("test split is sealed until G4")
    subset = json.loads(CATS.read_text())["subset"]

    src = json.loads(RAW.read_text())
    picked = [d for d in src["data"] if d["title"] in set(members)]
    assert len(picked) == len(members), (len(picked), len(members))

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"split": args.split, "contracts": len(picked), "shards": []}

    groups = [
        subset[i : i + args.group_size]
        for i in range(0, len(subset), args.group_size)
    ]
    for gi, cats in enumerate(groups):
        cset = set(cats)
        out = {"version": src.get("version", "1.0"), "data": []}
        for d in picked:
            p = d["paragraphs"][0]
            qas = [q for q in p["qas"] if q["id"].rsplit("__", 1)[-1] in cset]
            assert len(qas) == len(cats), (d["title"], len(qas))
            out["data"].append(
                {
                    "title": d["title"],
                    "paragraphs": [{"context": p["context"], "qas": qas}],
                }
            )
        name = f"{args.split}_g{gi}"
        (outdir / f"{name}.json").write_text(json.dumps(out))
        n_q = sum(len(x["paragraphs"][0]["qas"]) for x in out["data"])
        n_pos = sum(
            1
            for x in out["data"]
            for q in x["paragraphs"][0]["qas"]
            if not q["is_impossible"]
        )
        manifest["shards"].append(
            {
                "name": name,
                "categories": cats,
                "questions": n_q,
                "answerable_questions": n_pos,
                "chars": sum(
                    len(x["paragraphs"][0]["context"]) for x in out["data"]
                ),
            }
        )

    (outdir / f"{args.split}_manifest.json").write_text(
        json.dumps(manifest, indent=2)
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
