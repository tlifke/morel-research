"""Grade JSONL generations with a Claude judge using a rubric from data/judge_rubrics.yaml.

Adds `judge_<rubric>` (label) and `judge_<rubric>_raw` (full judge text) to each record and
writes a new JSONL. Records that already have the label are skipped (resumable).

  python judge.py --rubric rh_honesty --inp runs/m/rh_desperate.jsonl --out runs/m/rh_desperate.judged.jsonl
  python judge.py --rubric sycophancy --inp runs/m/syco.jsonl --prompts syco.yaml --out ...

For response-level rubrics (sycophancy/harshness/coherence) pass --prompts so the judge
sees the user message ({user}); records are matched on prompt_id.

ALWAYS spot-check judge labels against your own reading on a sample before trusting rates.
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
import yaml

DATA = Path(__file__).resolve().parent.parent / "data"
MODEL = "claude-opus-5-5"


def render_transcript(msgs, limit=60000):
    parts = [f"[{m['role'].upper()}]\n{m['content']}" for m in msgs if m["role"] != "system"]
    s = "\n\n".join(parts)
    return s if len(s) <= limit else s[: limit // 2] + "\n...[truncated]...\n" + s[-limit // 2:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubric", required=True)
    ap.add_argument("--inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompts", help="YAML/JSONL prompt file with id/user (response rubrics)")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    R = yaml.safe_load((DATA / "judge_rubrics.yaml").read_text())[args.rubric]
    users = {}
    if args.prompts:
        from steer_sweep import load_prompts
        users = {p["id"]: p["user"] for p in load_prompts(args.prompts)}
    recs = [json.loads(l) for l in open(args.inp) if l.strip()]
    key = f"judge_{args.rubric}"
    client = anthropic.Anthropic()

    def fill(r):
        if r.get(key):
            return r
        if R["input"] == "transcript":
            prompt = R["prompt"].format(outcome=r["label"], visible_pass=r["visible_pass"],
                                        hidden_pass=r["hidden_pass"], tampered=r["label"] == "tampered",
                                        transcript=render_transcript(r["messages"]),
                                        submit_message=r.get("submit_message") or "(no submission)")
        else:
            prompt = R["prompt"].format(user=users.get(r.get("prompt_id"), "(unknown)"), response=r["response"])
        msg = client.beta.messages.create(
            model=MODEL, max_tokens=4000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": "low"}, messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if b.type == "text")
        m = re.findall(r"LABEL:\s*([A-Za-z_]+)", text)
        label = m[-1] if m and m[-1] in R["labels"] else "unparsed"
        return {**r, key: label, key + "_raw": text}

    with ThreadPoolExecutor(args.workers) as ex:
        out = list(ex.map(fill, recs))
    Path(args.out).write_text("".join(json.dumps(r) + "\n" for r in out))
    counts = {}
    for r in out:
        counts[r[key]] = counts.get(r[key], 0) + 1
    print(f"wrote {args.out}: {counts}")


if __name__ == "__main__":
    main()
