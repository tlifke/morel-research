"""Build study 010's contract dataset from study 009's raw CUAD data.

Reads:
  studies/009-project-grimoire/data/raw/CUADv1.json          (contract texts)
  studies/009-project-grimoire/data/processed/instances.jsonl (ground truth)

Writes:
  data/contract_text/<contract_id>.txt    one file per contract
  data/contract_ground_truth              JSONL, one record per contract

Every contract's text is verified against its `text_sha256` before writing;
the script fails loudly on any mismatch or missing contract.
"""

import hashlib
import json
import sys
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = STUDY_DIR.parent.parent
CUAD_PATH = REPO_ROOT / "studies/009-project-grimoire/data/raw/CUADv1.json"
INSTANCES_PATH = REPO_ROOT / "studies/009-project-grimoire/data/processed/instances.jsonl"
OUT_TEXT_DIR = STUDY_DIR / "data/contract_text"
OUT_GT_PATH = STUDY_DIR / "data/contract_ground_truth"


def main() -> None:
    cuad = json.loads(CUAD_PATH.read_text())
    # CUAD stores full contract text in paragraphs[].context; contracts have
    # exactly one paragraph entry in this dataset.
    texts = {}
    for item in cuad["data"]:
        title = item["title"]
        contexts = [p["context"] for p in item["paragraphs"]]
        texts[title] = "\n\n".join(contexts)

    instances = [json.loads(line) for line in INSTANCES_PATH.read_text().splitlines() if line.strip()]
    print(f"instances: {len(instances)}, cuad contracts: {len(texts)}")

    OUT_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    mismatches = []
    missing = []
    gt_lines = []
    for inst in instances:
        cid = inst["contract_id"]
        text = texts.get(cid)
        if text is None:
            missing.append(cid)
            continue
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if inst.get("text_sha256") and sha != inst["text_sha256"]:
            mismatches.append((cid, inst["text_sha256"], sha))
            continue
        (OUT_TEXT_DIR / f"{cid}.txt").write_text(text)
        gt_lines.append(json.dumps(inst, ensure_ascii=False))

    if missing or mismatches:
        print(f"MISSING contracts ({len(missing)}):", file=sys.stderr)
        for cid in missing[:10]:
            print(f"  {cid}", file=sys.stderr)
        print(f"SHA MISMATCHES ({len(mismatches)}):", file=sys.stderr)
        for cid, want, got in mismatches[:10]:
            print(f"  {cid}: want {want[:12]} got {got[:12]}", file=sys.stderr)
        sys.exit(1)

    OUT_GT_PATH.write_text("\n".join(gt_lines) + "\n")
    print(f"wrote {len(gt_lines)} contract texts to {OUT_TEXT_DIR}")
    print(f"wrote {len(gt_lines)} GT records to {OUT_GT_PATH}")


if __name__ == "__main__":
    main()
