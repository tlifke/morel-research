import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

FIELDS = ["compares_to_history", "builds_on_wins", "handles_regressions", "tracks_learning", "stays_coherent"]


def render(trace_path):
    recs = [json.loads(l) for l in trace_path.read_text().splitlines() if l.strip()]
    out = []
    it = 0
    for r in recs:
        k = r["kind"]
        if k == "meta" or k == "end":
            continue
        if k == "input":
            it += 1
            out.append(f"\n=== iteration {it} ===")
            out.append(f"task: {r.get('text','')}")
        elif k == "thinking":
            out.append(f"[reasoning] {r.get('text','')[:500]}")
        elif k == "tool_use":
            out.append(f"[tool {r.get('name')}] {json.dumps(r.get('arguments',{}))[:160]}")
        elif k == "tool_result":
            out.append(f"[result] {r.get('text','')[:200]}")
        elif k == "assistant_text":
            out.append(f"[answer] {r.get('text','')[:300]}")
    return "\n".join(out)


def call_gemini(model, system, user):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": user}]}], "generationConfig": {"temperature": 0}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))["candidates"][0]["content"]["parts"][0]["text"]


def parse(text):
    low = text.lower()
    out = {}
    for f in FIELDS:
        m = re.search(rf"{f}\W+(true|false|yes|no|na|n/a)", low)
        if m:
            g = m.group(1)
            out[f] = "na" if g in ("na", "n/a") else (g in ("true", "yes"))
        else:
            out[f] = None
    m = re.search(r"rationale\W+(.+)", text, re.IGNORECASE)
    out["rationale"] = m.group(1).strip()[:300] if m else ""
    out["reasoning"] = text[:1500]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_dir")
    ap.add_argument("out_json")
    ap.add_argument("--model", default="gemini-3.5-flash")
    args = ap.parse_args()
    rubric = Path(Path(__file__).resolve().parent / "loop_rubric.md").read_text()
    system = (
        rubric
        + "\n\nFirst, under 'AUDIT:', walk through the iterations and cite specific evidence for each field. THEN, under 'VERDICT:', output exactly these lines:\n"
        + "\n".join(f"{f}: <true|false" + ("|na>" if f in ("builds_on_wins", "handles_regressions") else ">") for f in FIELDS)
        + "\nconfidence: <0..1>\nrationale: <one sentence>"
    )
    verdicts = {}
    for p in sorted(Path(args.batch_dir).glob("run_*/trace.jsonl")):
        run = p.parent.name
        try:
            verdicts[run] = parse(call_gemini(args.model, system, render(p)))
        except Exception as e:
            verdicts[run] = {"rationale": f"error: {e}"[:200]}
        print(f"{run}: " + " ".join(f"{f[:5]}={verdicts[run].get(f)}" for f in FIELDS))
    Path(args.out_json).write_text(json.dumps(verdicts, indent=2))

    print(f"\n=== aggregate (n={len(verdicts)}) ===")
    for f in FIELDS:
        vals = [v.get(f) for v in verdicts.values()]
        t = sum(1 for x in vals if x is True)
        applicable = sum(1 for x in vals if x in (True, False))
        print(f"  {f:22}: {t}/{applicable} true ({100*t//max(applicable,1)}%)")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
