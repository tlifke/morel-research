import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "scripts"))

import contracteval_prompt as cep
from harness.backends.tinker_backend import TinkerBackend

RAW = STUDY / "data" / "raw" / "CUADv1.json"
SPLITS = STUDY / "data" / "processed" / "splits"


def load_contracts(split, titles):
    src = json.loads(RAW.read_text())
    members = [l.strip() for l in (SPLITS / f"{split}.txt").read_text().splitlines() if l.strip()]
    wanted = set(titles) if titles else set(members)
    picked = [d for d in src["data"] if d["title"] in wanted]
    assert len(picked) == len(wanted), (len(picked), len(wanted))
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="harness_val")
    ap.add_argument("--titles-file", required=True)
    ap.add_argument("--model", default="qwen3.5-9b")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=0)
    ap.add_argument("--headroom-margin", type=int, default=512)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if args.split == "test":
        raise SystemExit("test split is sealed until G4")

    titles = [l.strip() for l in Path(args.titles_file).read_text().splitlines() if l.strip()]
    docs = load_contracts(args.split, titles)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    trace_path = outdir / "trials.jsonl"
    done = set()
    if trace_path.exists():
        for line in trace_path.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["question_id"])

    backend = TinkerBackend(model=args.model, separate_reasoning=True)

    manifest = {
        "split": args.split,
        "model": args.model,
        "served_model": backend.served_model,
        "contracts": [d["title"] for d in docs],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "seed": args.seed,
        "separate_reasoning": True,
        "system_prompt": cep.SYSTEM_PROMPT,
        "user_template": cep.USER_TEMPLATE,
        "prompt_source": "ContractEval main @ github.com/olivialiu121/ContractEval",
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    n = 0
    with trace_path.open("a") as fh:
        for d in docs:
            context = d["paragraphs"][0]["context"]
            for qa in d["paragraphs"][0]["qas"]:
                qid = qa["id"]
                if qid in done:
                    continue
                if args.limit and n >= args.limit:
                    break
                messages = cep.render(context, qa["question"])
                est_prompt = sum(backend.count_tokens(m["content"]) for m in messages)
                headroom = backend.context_limit - est_prompt - args.headroom_margin
                budget = headroom if not args.max_tokens else min(args.max_tokens, headroom)
                t0 = time.time()
                err = None
                res = None
                if budget <= 0:
                    err = (
                        f"prompt does not fit: est_prompt={est_prompt} "
                        f"context_limit={backend.context_limit}"
                    )
                else:
                    try:
                        res = backend.sample(
                            messages=messages,
                            json_schema=None,
                            temperature=args.temperature,
                            seed=args.seed,
                            max_tokens=budget,
                        )
                    except Exception as exc:
                        err = f"{type(exc).__name__}: {exc}"
                        res = None
                row = {
                    "question_id": qid,
                    "contract_id": d["title"],
                    "category": qid.rsplit("__", 1)[-1],
                    "question": qa["question"],
                    "context_chars": len(context),
                    "context_sha256": hashlib.sha256(context.encode()).hexdigest()[:16],
                    "est_prompt_tokens": est_prompt,
                    "max_tokens_budget": budget,
                    "error": err,
                    "raw_response": res.text if res else None,
                    "finish_reason": res.finish_reason if res else None,
                    "n_prompt_tokens": res.n_prompt_tokens if res else None,
                    "n_completion_tokens": res.n_completion_tokens if res else None,
                    "n_reasoning_chars": res.raw.get("n_reasoning_chars") if res else None,
                    "latency_ms": int((time.time() - t0) * 1000),
                }
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                n += 1
                print(
                    f"{n:4d} {row['category'][:28]:28s} "
                    f"{'ERR' if err else (row['finish_reason'] or '')[:6]:6s} "
                    f"in={row['n_prompt_tokens']} out={row['n_completion_tokens']} "
                    f"{row['latency_ms']}ms",
                    flush=True,
                )

    print(f"wrote {n} rows to {trace_path}")


if __name__ == "__main__":
    main()
