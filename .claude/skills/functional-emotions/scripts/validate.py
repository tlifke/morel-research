"""Validate emotion vectors outside the stories they were trained on.

Subcommands (each writes a JSON file you can plot / inspect):

  logit-lens     top/bottom-k tokens of each vector through the unembedding
                 (paper Table 1: "desperate" -> desperate, urgent, bankrupt).
  scenarios      probe values at user_end and assistant_colon for the implicit-emotion
                 scenarios (Table 2) and the user/assistant dissociation prompts (Table 3);
                 with --continue N also samples N tokens and records the mean probe value
                 over the response, so you can reproduce "colon predicts response".
  intensity      numeric-template sweeps (Figure 3) at the assistant colon.
  he-feels       causal sanity check: steer on the Assistant-turn tokens of
                 "Human: How does he feel? / Assistant: He feels" and measure the
                 log-prob change of each emotion's own word (Appendix, Figure 52).
  max-act        sweep a JSONL corpus ({"text": ...}) and keep the top-k activating
                 snippets per emotion (Figure 1).

Common flags: --model, --vectors (npz from extract_vectors.py), --layer (default ~2/3 depth).
"""

from __future__ import annotations

import argparse
import contextlib
import heapq
import json
from pathlib import Path

import numpy as np
import torch
import yaml

import emo_lib as E

DATA = Path(__file__).resolve().parent.parent / "data"


def cmd_logit_lens(model, tok, ev, layer, args):
    W_U, final_norm = E.get_unembed(model)
    W = W_U.detach().float().cpu()
    # Direct effect of adding v to the final residual: W_U @ (g * v) where g is the
    # final norm's elementwise gain (ignores the norm's data-dependent scaling).
    gain = None
    if final_norm is not None and getattr(final_norm, "weight", None) is not None and args.apply_norm_gain:
        gain = final_norm.weight.detach().float().cpu()
        if "gemma" in type(model).__name__.lower():  # Gemma RMSNorm uses (1 + weight)
            gain = 1 + gain
    out = {}
    for e in args.emotions or ev.emotions:
        v = torch.from_numpy(ev.vectors[layer, ev.idx(e)]).float()
        if gain is not None:
            v = v * gain
        logits = W @ v
        top = torch.topk(logits, args.k).indices.tolist()
        bot = torch.topk(-logits, args.k).indices.tolist()
        out[e] = {"up": [tok.decode([i]) for i in top], "down": [tok.decode([i]) for i in bot]}
        print(f"{e:>14}  up: {out[e]['up']}\n{'':>14}  down: {out[e]['down']}")
    return out


def probe_at(model, tok, ev, layer_list, f: E.Formatted, positions: dict[str, int]):
    res = E.residuals(model, f.ids, layer_list)
    out = {}
    for name, p in positions.items():
        if p is None:
            continue
        out[name] = {str(l): E.project_scores(res[l][0, p].numpy(), ev.unit(l), args_kind).tolist() for l in layer_list}
    return out


def cmd_scenarios(model, tok, ev, layer, args):
    P = yaml.safe_load((DATA / "probe_prompts.yaml").read_text())
    layer_list = sorted(set([layer] + (args.extra_layers or [])))
    results = []
    for group in ["implicit_scenarios", "dissociation"]:
        for item in P[group]:
            f = E.format_chat(tok, item["prompt"], mode=args.format)
            rec = {"group": group, **item, "positions": E.describe_positions(tok, f),
                   "probe": probe_at(model, tok, ev, layer_list, f,
                                     {"user_end": f.user_end, "assistant_colon": f.assistant_colon})}
            if args.continue_tokens:
                text = E.generate(model, tok, f.ids, max_new_tokens=args.continue_tokens, temperature=0)
                full = torch.cat([f.ids, tok(text, return_tensors="pt", add_special_tokens=False)["input_ids"]], 1)
                res = E.residuals(model, full, [layer])
                resp = res[layer][0, f.ids.shape[1]:].numpy()
                rec["response"] = text
                rec["response_mean"] = E.project_scores(resp, ev.unit(layer), args_kind).mean(0).tolist()
            results.append(rec)
    # Quick summary: diagonal accuracy for the implicit set at the colon.
    imp = [r for r in results if r["group"] == "implicit_scenarios" and r["target"] in ev.emotions]
    missing = {r["target"] for r in results if r["group"] == "implicit_scenarios"} - set(ev.emotions)
    if missing:
        print(f"note: no vector for scenario targets {sorted(missing)}; excluded from the diagonal check")
    names = [r["target"] for r in imp]
    M = np.array([[r["probe"]["assistant_colon"][str(layer)][ev.idx(t)] for t in names] for r in imp])
    Mz = (M - M.mean(0)) / (M.std(0) + 1e-8)  # z-score each probe across scenarios
    hits = int((Mz.argmax(1) == np.arange(len(names))).sum())
    print(f"implicit scenarios: {hits}/{len(names)} scenarios have their target as the top (column-z-scored) probe")
    if args.continue_tokens:
        dis = [r for r in results if r["group"] == "dissociation"]
        for pos in ["user_end", "assistant_colon"]:
            a = np.concatenate([np.array(r["probe"][pos][str(layer)]) for r in dis])
            b = np.concatenate([np.array(r["response_mean"]) for r in dis])
            print(f"corr({pos}, response mean) over prompts x emotions: r={np.corrcoef(a, b)[0, 1]:.2f}")
    return {"layer": layer, "emotions": ev.emotions, "results": results}


def cmd_intensity(model, tok, ev, layer, args):
    P = yaml.safe_load((DATA / "probe_prompts.yaml").read_text())
    out = []
    for t in P["intensity_templates"]:
        rows = []
        for x in t["values"]:
            f = E.format_chat(tok, t["template"].format(X=x), mode=args.format)
            res = E.residuals(model, f.ids, [layer])
            s = E.project_scores(res[layer][0, f.assistant_colon].numpy(), ev.unit(layer), args_kind)
            rows.append({"X": x, "scores": {e: float(s[ev.idx(e)]) for e in t["expect"] if e in ev.emotions}})
        verdict = {}
        for e, direction in t["expect"].items():
            if e not in ev.emotions:
                continue
            ys = [r["scores"][e] for r in rows]
            rho = np.corrcoef(np.arange(len(ys)), ys)[0, 1]
            verdict[e] = {"expected": direction, "trend_r": round(float(rho), 2),
                          "ok": bool((rho > 0) == (direction == "up"))}
        print(f"{t['name']:<26} {verdict}{'  [invented template]' if t.get('invented') else ''}")
        out.append({**t, "rows": rows, "verdict": verdict})
    return out


def cmd_he_feels(model, tok, ev, layer, args):
    P = yaml.safe_load((DATA / "probe_prompts.yaml").read_text())["he_feels"]
    f = E.format_chat(tok, P["user"], assistant_prefill=P["assistant_prefill"], mode=args.format)
    # Steer on the Assistant-turn tokens up to and including "He feels".
    positions = list(range(f.assistant_colon + 1, f.ids.shape[1]))
    layers = args.steer_layers or [layer]
    emos = args.emotions or ev.emotions
    # First token of " <emotion>" as the target word.
    first_tok = {e: tok(" " + e, add_special_tokens=False)["input_ids"][0] for e in emos}

    def logprobs(steer=None):
        with (steer.attach(model) if steer else contextlib.nullcontext()):
            logits = model(input_ids=f.ids.to(model.device)).logits[0, -1].float()
        return torch.log_softmax(logits, -1).cpu()

    base = logprobs()
    M = np.zeros((len(emos), len(emos)))
    for i, e in enumerate(emos):
        st = E.Steer(E.steer_layers(ev.vectors, ev.idx(e), layers), args.strength, ev.mean_norm_dict(), positions)
        lp = logprobs(st)
        for j, e2 in enumerate(emos):
            M[i, j] = float(lp[first_tok[e2]] - base[first_tok[e2]])
    diag = np.diag(M).mean()
    off = (M.sum() - np.trace(M)) / (M.size - len(emos))
    print(f"mean dlogp matching={diag:+.3f}  non-matching={off:+.3f}  (paper: matching up, non-matching down)")
    return {"emotions": emos, "delta_logprob": M.tolist(), "strength": args.strength, "layers": layers,
            "steered_positions": positions, "positions": E.describe_positions(tok, f)}


def cmd_max_act(model, tok, ev, layer, args):
    U = ev.unit(layer)
    heaps = {e: [] for e in ev.emotions}
    all_scores = []
    for n, rec in enumerate(E.read_jsonl(args.corpus)):
        if args.limit and n >= args.limit:
            break
        ids = tok(rec["text"], return_tensors="pt", truncation=True, max_length=args.max_len)["input_ids"]
        res = E.residuals(model, ids, [layer])[layer][0, 1:].numpy()
        S = E.project_scores(res, U, args_kind)  # [T-1, E]
        all_scores.append(S[:: max(1, len(S) // 16)])
        for j, e in enumerate(ev.emotions):
            t = int(S[:, j].argmax())
            item = (float(S[t, j]), n, t + 1)
            if len(heaps[e]) < args.k:
                heapq.heappush(heaps[e], item)
            else:
                heapq.heappushpop(heaps[e], item)
        if n % 500 == 0:
            print(f"  {n} docs")
    p90 = np.percentile(np.concatenate(all_scores), 90, axis=0)
    docs = {}
    out = {}
    for j, e in enumerate(ev.emotions):
        snippets = []
        for score, n, t in sorted(heaps[e], reverse=True):
            docs.setdefault(n, None)
            snippets.append({"score": score, "doc": n, "token": t})
        out[e] = {"p90": float(p90[j]), "top": snippets}
    # Attach text windows around the peak token.
    for n, rec in enumerate(E.read_jsonl(args.corpus)):
        if n in docs:
            docs[n] = tok(rec["text"], truncation=True, max_length=args.max_len)["input_ids"]
    for e in out:
        for s in out[e]["top"]:
            ids = docs[s["doc"]]
            lo, hi = max(0, s["token"] - 40), min(len(ids), s["token"] + 10)
            s["window"] = tok.decode(ids[lo:s["token"]]) + " [[" + tok.decode(ids[s["token"]:s["token"] + 1]) + "]] " + tok.decode(ids[s["token"] + 1:hi])
    return out


args_kind = "dot"


def main():
    global args_kind
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["logit-lens", "scenarios", "intensity", "he-feels", "max-act"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--layer", type=int, default=None)
    ap.add_argument("--extra-layers", type=int, nargs="*", help="scenarios: also record these layers")
    ap.add_argument("--emotions", nargs="*")
    ap.add_argument("--format", default="auto", choices=["auto", "chat", "paper"])
    ap.add_argument("--score", default="dot", choices=["dot", "cos"],
                    help="dot = projection onto unit vector; cos = cosine similarity (paper uses both)")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--apply-norm-gain", action="store_true", help="logit-lens: multiply by final-norm gain")
    ap.add_argument("--continue-tokens", type=int, default=0)
    ap.add_argument("--strength", type=float, default=0.5)
    ap.add_argument("--steer-layers", type=int, nargs="*")
    ap.add_argument("--corpus")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--dtype", default="bfloat16")
    args = ap.parse_args()
    args_kind = args.score

    model, tok = E.load_model(args.model, args.dtype)
    ev = E.EmotionVectors.load(args.vectors)
    layer = args.layer if args.layer is not None else ev.meta.get("default_layer", E.default_layer(E.n_layers(model)))
    fn = {"logit-lens": cmd_logit_lens, "scenarios": cmd_scenarios, "intensity": cmd_intensity,
          "he-feels": cmd_he_feels, "max-act": cmd_max_act}[args.cmd]
    out = fn(model, tok, ev, layer, args)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"cmd": args.cmd, "layer": layer, "model": args.model, "result": out}, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    torch.set_grad_enabled(False)
    main()
