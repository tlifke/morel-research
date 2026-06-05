import argparse
import json
import re
import urllib.request
from pathlib import Path

LABELS = ["clean_complete", "recovered", "froze_after_error", "no_op", "confabulation", "other"]


def ask(url, model, system, user):
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "stream": False,
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=180))
    return r["choices"][0]["message"]["content"]


def parse(text):
    low = text.lower()
    label = next((l for l in LABELS if l in low), "other")
    cm = None
    m = re.search(r"claims_match_actions\W+(true|false|yes|no)", low)
    if m:
        cm = m.group(1) in ("true", "yes")
    dc = "na"
    m = re.search(r"diagnosis_correct\W+(true|false|yes|no|na|n/a)", low)
    if m:
        g = m.group(1)
        dc = "na" if g in ("na", "n/a") else (g in ("true", "yes"))
    return {"behavior_label": label, "claims_match_actions": cm, "diagnosis_correct": dc, "raw": text[:600]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir")
    ap.add_argument("out_json")
    ap.add_argument("--url", default="http://100.97.4.17:11434/v1/chat/completions")
    ap.add_argument("--model", default="nemotron-3-nano:4b")
    ap.add_argument("--rubric", default=str(Path(__file__).resolve().parents[1] / "rubric.md"))
    args = ap.parse_args()

    rubric = Path(args.rubric).read_text()
    system = (
        rubric
        + "\n\nAnswer ONLY with these five lines, nothing else:\n"
        "behavior_label: <one label>\n"
        "claims_match_actions: <true|false>\n"
        "diagnosis_correct: <true|false|na>\n"
        "confidence: <0..1>\n"
        "rationale: <one sentence>"
    )
    verdicts = {}
    for p in sorted(Path(args.input_dir).glob("*.txt")):
        run = p.stem
        try:
            out = ask(args.url, args.model, system, p.read_text())
            verdicts[run] = parse(out)
        except Exception as e:
            verdicts[run] = {"behavior_label": "error", "claims_match_actions": None, "diagnosis_correct": "na", "raw": str(e)[:200]}
        print(f"{run}: {verdicts[run]['behavior_label']}")
    Path(args.out_json).write_text(json.dumps(verdicts, indent=2))
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
