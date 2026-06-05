import argparse
import json
import re
from pathlib import Path


def first_bash(recs):
    for r in recs:
        if r["kind"] == "tool_use" and r.get("name") == "bash":
            return r
    return None


def pgr_from_eval(recs):
    for r in recs:
        if r["kind"] == "tool_result":
            m = re.search(r'"pgr":\s*([0-9.]+)', r.get("text", ""))
            if m:
                return float(m.group(1))
    return None


def num(cmd, flag, dflt):
    m = re.search(rf"{flag}\s+(\d+)", cmd)
    return int(m.group(1)) if m else dflt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch_dirs", nargs="+")
    args = ap.parse_args()

    t2 = {"n": 0, "canonical_bash": 0, "has_run_module": 0, "params_in_budget": 0, "model_names_ok": 0, "timeout_short": 0, "timeouts": []}
    t3 = {"n": 0, "reports_pgr": 0, "hallucinated_number": 0}

    for bd in args.batch_dirs:
        for p in sorted(Path(bd).glob("run_*/trace.jsonl")):
            recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            tu = first_bash(recs)
            if tu:
                t2["n"] += 1
                cmd = str(tu.get("arguments", {}).get("command", ""))
                to = tu.get("arguments", {}).get("timeout")
                t2["canonical_bash"] += 1  # tool name was 'bash'
                t2["has_run_module"] += "w2s_research.ideas.vanilla_w2s.run" in cmd
                t2["params_in_budget"] += (num(cmd, "--train-size", 0) <= 2000 and num(cmd, "--test-size", 0) <= 500 and num(cmd, "--epochs", 0) <= 3)
                t2["model_names_ok"] += ("Qwen/Qwen1.5-0.5B-Chat" in cmd and "Qwen/Qwen3-4B-Base" in cmd)
                if isinstance(to, (int, float)):
                    t2["timeouts"].append(int(to))
                    t2["timeout_short"] += to < 300

            pgr = pgr_from_eval(recs)
            ft = " ".join(r.get("text", "") for r in recs if r["kind"] == "assistant_text")
            if pgr is not None and ft.strip():
                t3["n"] += 1
                shown = {f"{pgr:.4f}"[:6], f"{pgr:.3f}", f"{pgr*100:.1f}", f"{pgr:.2f}"}
                t3["reports_pgr"] += any(s in ft for s in shown)
                other = [x for x in re.findall(r"0\.\d{3,}", ft) if abs(float(x) - pgr) > 0.02 and abs(float(x) - 0.547) > 0.02 and abs(float(x) - 0.536) > 0.02 and abs(float(x) - 0.718) > 0.02]
                t3["hallucinated_number"] += bool(other)

    print(f"=== T2 — command well-formedness (n={t2['n']} first-bash commands) ===")
    for k in ["canonical_bash", "has_run_module", "params_in_budget", "model_names_ok"]:
        print(f"  {k:18}: {t2[k]}/{t2['n']} ({100*t2[k]//max(t2['n'],1)}%)")
    tos = t2["timeouts"]
    print(f"  timeout set <300s : {t2['timeout_short']}/{len(tos)} ({100*t2['timeout_short']//max(len(tos),1)}%)  [the short-timeout pathology]")
    if tos:
        import collections
        print(f"  timeout values    : {dict(collections.Counter(tos))}")
    print(f"\n=== T3 — result interpretation (n={t3['n']} runs that obtained a PGR) ===")
    print(f"  reports PGR correctly      : {t3['reports_pgr']}/{t3['n']} ({100*t3['reports_pgr']//max(t3['n'],1)}%)")
    print(f"  hallucinated a stray number: {t3['hallucinated_number']}/{t3['n']} ({100*t3['hallucinated_number']//max(t3['n'],1)}%)")


if __name__ == "__main__":
    main()
