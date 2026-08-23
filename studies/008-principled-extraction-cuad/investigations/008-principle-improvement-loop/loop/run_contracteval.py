from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

INV = Path(__file__).resolve().parents[1]
STUDY = INV.parents[1]
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "scripts"))
sys.path.insert(0, str(INV))

import contracteval_prompt as cep
from harness.backends.base import BackendError, BackendUnavailable
from harness.backends.tinker_backend import TinkerBackend

from loop.ledger import Ledger, QuestionTrialKey, TrialRecord
from loop.prompt import TaskDefinition
from loop.run_slice import SLICE, load_contracts

TEMPERATURE = 1.0
TOP_P = 0.95
MAX_OUTPUT_TOKENS = 32768
HEADROOM_MARGIN = 512


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--model", default="Qwen/Qwen3.5-9B")
    ap.add_argument("--contracts", nargs="*", default=None)
    args = ap.parse_args()

    task = TaskDefinition.load()
    contract_ids = args.contracts or [
        c["contract_id"] for c in json.loads(SLICE.read_text())["contracts"]
    ]
    contracts = load_contracts(contract_ids)

    ledger = Ledger(args.run_id)
    already = ledger.done()
    backend = TinkerBackend(model=args.model, separate_reasoning=True, top_p=TOP_P)

    ledger.write_manifest(
        {
            "run_id": args.run_id,
            "arm": "contracteval_native",
            "model": args.model,
            "split": "principle_train",
            "task_definition_version": task.version,
            "task_definition_sha256": task.content_sha256,
            "principle_set_version": "none",
            "packaging": "one call per (contract, question), ContractEval's native unit",
            "system_prompt_sha256": cep.SYSTEM_PROMPT_SHA256,
            "user_template_sha256": cep.USER_TEMPLATE_SHA256,
            "prompt_source": cep.UPSTREAM_SOURCE,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "repeats": args.repeats,
            "contracts": contract_ids,
            "n_calls": len(contract_ids) * len(task.questions) * args.repeats,
            "backend": backend.describe(),
        }
    )

    for contract in contracts:
        for category, question in task.questions.items():
            for repeat in range(args.repeats):
                key = QuestionTrialKey(
                    task_definition_version=task.version,
                    task_definition_sha256=task.content_sha256,
                    principle_set_version="none",
                    arm="contracteval_native",
                    model=args.model,
                    contract_id=contract["contract_id"],
                    category=category,
                    repeat_idx=repeat,
                )
                if key.trial_id in already:
                    continue

                messages = cep.render(contract["text"], question)
                est_prompt = sum(backend.count_tokens(m["content"]) for m in messages)
                budget = min(MAX_OUTPUT_TOKENS, backend.context_limit - est_prompt - HEADROOM_MARGIN)
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
                        )
                    )
                    continue

                try:
                    res = backend.sample(messages, None, TEMPERATURE, repeat, budget)
                except (BackendError, BackendUnavailable) as exc:
                    print(f"BACKEND ERROR {contract['contract_id'][:30]} {category}: {exc}", file=sys.stderr)
                    raise

                spans = cep.response_to_spans(res.text)
                ledger.append(
                    TrialRecord(
                        key=key,
                        run_id=args.run_id,
                        outcome="ok",
                        temperature=TEMPERATURE,
                        top_p=TOP_P,
                        max_output_tokens=budget,
                        n_prompt_tokens=res.n_prompt_tokens,
                        n_completion_tokens=res.n_completion_tokens,
                        finish_reason=res.finish_reason,
                        latency_ms=res.latency_ms,
                        response_sha256=hashlib.sha256(res.text.encode()).hexdigest(),
                        parsed=True,
                        output={"spans": spans, "declined": cep.is_declination(res.text)},
                        notes={"n_reasoning_chars": res.raw.get("n_reasoning_chars")},
                    )
                )


if __name__ == "__main__":
    main()
