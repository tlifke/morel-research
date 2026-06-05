import argparse
import json
from pathlib import Path


def render(trace_path):
    recs = [json.loads(l) for l in trace_path.read_text().splitlines() if l.strip()]
    meta = next((r for r in recs if r.get("kind") == "meta"), {})
    steps = [r for r in recs if r.get("kind") != "meta"]
    lines = [f"SCENARIO: {meta.get('scenario','?')}", f"MODEL: {meta.get('model','?')}", ""]
    i = 0
    for r in steps:
        k = r["kind"]
        if k == "end":
            lines.append(f"--- END --- stop={r.get('stop_reason')} saw_error={r.get('saw_error')} acted_after_error={r.get('acted_after_error')}")
            continue
        i += 1
        if k == "tool_use":
            lines.append(f"--- step {i} [TOOL CALL: {r.get('name')}] ---")
            lines.append(json.dumps(r.get("arguments", {})))
        elif k == "tool_result":
            lines.append(f"--- step {i} [TOOL RESULT] ---")
            lines.append((r.get("text", "") or "")[:1200])
        elif k == "thinking":
            lines.append(f"--- step {i} [private reasoning] ---")
            lines.append(r.get("text", ""))
        elif k == "input":
            lines.append(f"--- step {i} [user task] ---")
            lines.append(r.get("text", ""))
        elif k == "assistant_text":
            lines.append(f"--- step {i} [FINAL ANSWER] ---")
            lines.append(r.get("text", ""))
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_dir")
    ap.add_argument("out_dir")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(Path(args.batch_dir).glob("run_*/trace.jsonl")):
        (out / f"{p.parent.name}.txt").write_text(render(p))
        n += 1
    print(f"wrote {n} judge inputs to {out}")


if __name__ == "__main__":
    main()
