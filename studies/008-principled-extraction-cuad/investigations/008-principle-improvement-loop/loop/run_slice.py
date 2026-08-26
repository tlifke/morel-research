from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

INV = Path(__file__).resolve().parents[1]
STUDY = INV.parents[1]
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(INV))

from harness.backends.base import BackendError, BackendUnavailable
from harness.backends.tinker_backend import TinkerBackend
from harness.models import PrincipleSet
from harness.parsing import ParseFailure, parse_output
from loop.ledger import Ledger, TrialKey, TrialRecord
from loop.models import LoopOutput
from loop.prompt import TaskDefinition, build

SLICE = INV / "mvp_slice.json"
INSTANCES = STUDY / "data/processed/instances.jsonl"
RAW = STUDY / "data/raw/CUADv1.json"

TEMPERATURE = 1.0
TOP_P = 0.95
MAX_OUTPUT_TOKENS = 32768
HEADROOM_MARGIN = 512


def load_contracts(contract_ids: list[str]) -> list[dict]:
    wanted = set(contract_ids)
    rows = [json.loads(l) for l in INSTANCES.read_text().splitlines()]
    picked = {r["contract_id"]: r for r in rows if r["contract_id"] in wanted}
    missing = wanted - set(picked)
    if missing:
        raise SystemExit(f"missing contracts: {sorted(missing)}")

    raw = json.loads(RAW.read_text())
    texts = {d["title"]: d["paragraphs"][0]["context"] for d in raw["data"] if d["title"] in wanted}
    for cid, row in picked.items():
        text = texts.get(cid)
        if text is None:
            raise SystemExit(f"no CUAD text for {cid}")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != row["text_sha256"]:
            raise SystemExit(f"text hash mismatch for {cid}")
        row["text"] = text
    return [picked[c] for c in contract_ids]


def load_principle_set(path: Optional[Path]) -> tuple[Optional[PrincipleSet], str]:
    if path is None:
        return None, "empty"
    data = json.loads(path.read_text())
    ps = PrincipleSet(**data)
    return ps, ps.version


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--model", default="Qwen/Qwen3.5-9B")
    ap.add_argument("--principles", type=Path, default=None)
    ap.add_argument("--contracts", nargs="*", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-dir", type=Path, default=None, help="override Ledger root (default: study/runs)")
    args = ap.parse_args()

    task = TaskDefinition.load()
    contract_ids = args.contracts or [
        c["contract_id"] for c in json.loads(SLICE.read_text())["contracts"]
    ]
    contracts = load_contracts(contract_ids)
    principle_set, principle_set_version = load_principle_set(args.principles)

    ledger = Ledger(args.run_id, root=args.run_dir) if args.run_dir else Ledger(args.run_id)
    already = ledger.done()

    backend = None
    if not args.dry_run:
        backend = TinkerBackend(model=args.model, separate_reasoning=True, top_p=TOP_P)

    ledger.write_manifest(
        {
            "run_id": args.run_id,
            "arm": args.arm,
            "model": args.model,
            "split": "principle_train",
            "task_definition_version": task.version,
            "task_definition_sha256": task.content_sha256,
            "principle_set_version": principle_set_version,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "repeats": args.repeats,
            "contracts": contract_ids,
            "n_categories": len(task.questions),
            "backend": backend.describe() if backend else "dry-run",
            "unreachable_sampling_params": ["top_k", "min_p", "presence_penalty"],
        }
    )

    for contract in contracts:
        prompt = build(task, contract["text"], principle_set)
        for repeat in range(args.repeats):
            key = TrialKey(
                task_definition_version=task.version,
                task_definition_sha256=task.content_sha256,
                principle_set_version=principle_set_version,
                arm=args.arm,
                model=args.model,
                contract_id=contract["contract_id"],
                repeat_idx=repeat,
            )
            if key.trial_id in already:
                continue

            if args.dry_run:
                n_prompt = sum(len(m["content"]) // 4 for m in prompt.messages())
                print(f"{contract['contract_id'][:50]:50s} r{repeat} ~{n_prompt} prompt tokens")
                continue

            messages = prompt.messages()
            est_prompt = sum(backend.count_tokens(m["content"]) for m in messages)
            headroom = backend.context_limit - est_prompt - HEADROOM_MARGIN
            budget = min(MAX_OUTPUT_TOKENS, headroom)
            if budget <= 0:
                ledger.append(
                    TrialRecord(
                        key=key,
                        run_id=args.run_id,
                        outcome="no_budget",
                        temperature=TEMPERATURE,
                        top_p=TOP_P,
                        max_output_tokens=0,
                        n_prompt_tokens=est_prompt,
                        n_completion_tokens=None,
                        finish_reason=None,
                        latency_ms=0,
                        failure_detail=f"prompt {est_prompt} exceeds context {backend.context_limit}",
                    )
                )
                continue

            try:
                res = backend.sample(messages, None, TEMPERATURE, repeat, budget)
            except (BackendError, BackendUnavailable) as exc:
                print(f"BACKEND ERROR on {contract['contract_id'][:40]} r{repeat}: {exc}", file=sys.stderr)
                raise

            parsed_ok, output, detail, conformance = True, None, None, None
            try:
                out = parse_output(res.text, LoopOutput)
                output = out.model_dump()
                conformance = out.conformance(task.categories)
            except (ParseFailure, ValueError) as exc:
                parsed_ok = False
                detail = str(exc)[:400]

            ledger.append(
                TrialRecord(
                    key=key,
                    run_id=args.run_id,
                    outcome="ok" if parsed_ok else "parse_failure",
                    temperature=TEMPERATURE,
                    top_p=TOP_P,
                    max_output_tokens=budget,
                    n_prompt_tokens=res.n_prompt_tokens,
                    n_completion_tokens=res.n_completion_tokens,
                    finish_reason=res.finish_reason,
                    latency_ms=res.latency_ms,
                    response_sha256=hashlib.sha256(res.text.encode()).hexdigest(),
                    parsed=parsed_ok,
                    output=output,
                    failure_detail=detail,
                    notes={"n_reasoning_chars": res.raw.get("n_reasoning_chars"), "conformance": conformance},
                )
            )
            (ledger.dir / f"{key.trial_id}.txt").write_text(res.text)
            reasoning = (
                ((res.raw.get("choices") or [{}])[0].get("message") or {}).get("reasoning_content")
                or ""
            )
            if reasoning:
                (ledger.dir / f"{key.trial_id}.reasoning.txt").write_text(reasoning)


if __name__ == "__main__":
    main()
