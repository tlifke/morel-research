import json
import sys
from pathlib import Path

GROUND_TRUTH = """GROUND TRUTH (privileged hindsight you have, the researcher did NOT):
- Goal: minimize validation loss by choosing learning rate (lr) and batch size (bs); budget 50 experiments.
- True optimum: lr=0.007812, bs=1024 -> loss 2.34201 (regret 0).
- Worst config loss 2.5332 -> max possible regret 0.191. A random config gives median regret ~0.029.
- The optimum is a BROAD SHALLOW basin: 5 of 120 configs are within 0.002 regret, 13 within 0.005. So regret ~0.0016 = "a near-best config one cell off optimum", barely distinguishable in loss.
- KEY STRUCTURE: lr and bs INTERACT. The optimum needs JOINTLY high lr AND large bs (>=736). A researcher who freezes batch size small (e.g. 128) and sweeps lr finds a clean but WRONG minimum at low lr (~1.38e-3, loss ~2.358, regret ~0.016) - a confident dead end. Reaching the optimum requires varying BOTH axes / probing the high-lr + large-bs region.
- A competent researcher should recognize this as a small smooth 2-D optimization, reason about the lr-bs relationship (from knowledge or experiment), and could even recognize it as a grid-search-class problem and proceed systematically."""


def short(s, n=240):
    return " ".join(s.split())[:n]


def render(run_dir):
    rd = Path(run_dir)
    rows = [json.loads(l) for l in open(rd / "trace.jsonl")]
    summ = json.load(open(rd / "loop_summary.json"))
    out = [GROUND_TRUTH, "", "=== THE RESEARCHER'S RUN (full trajectory, in order) ==="]
    exp = 0
    for r in rows:
        k = r["kind"]
        if k == "thinking":
            out.append(f"  [reasoning] {short(r['text'])}")
        elif k == "reflection":
            out.append(f"  [advisor] {short(r['text'])}")
        elif k == "assistant_text":
            out.append(f"  [says] {short(r['text'])}")
        elif k == "tool_use" and r.get("name") == "run_config":
            exp += 1
            out.append(f"  EXPERIMENT {exp}: run_config({json.dumps(r['arguments'])})")
        elif k == "tool_use" and r.get("name") == "finish":
            out.append(f"  FINISH: {json.dumps(r['arguments'])}")
        elif k == "tool_result":
            t = r["text"]
            if '"error"' in t:
                out.append(f"    -> REJECTED: {short(t,160)}")
            else:
                out.append(f"    -> {short(t,200)}")
        elif k == "input" and r.get("actuate_retry"):
            out.append(f"  [harness re-prompt to finish] (actuation nudge #{r['actuate_retry']})")
    bc = summ.get("best_config") or {}
    out += ["", "=== OUTCOME ===",
            f"experiments run: {summ['experiments']}   outcome: {summ['outcome']}   finish_kind: {summ.get('finish_kind')}",
            f"best config found: lr={bc.get('lr')} bs={bc.get('bs')}   final regret: {max(0.0, summ['final_regret']):.4f}",
            f"reached exact optimum: {'YES' if any(abs(__import__('math').log(t['lr'])-__import__('math').log(0.007812))<1e-6 and t['bs']==1024 for t in summ['trajectory']) else 'NO'}"]
    return "\n".join(out)


if __name__ == "__main__":
    print(render(sys.argv[1]))
