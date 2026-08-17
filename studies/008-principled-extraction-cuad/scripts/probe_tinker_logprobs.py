import json
import os
import sys

import tinker
from tinker import types


def main():
    base_model = os.environ.get("PROBE_MODEL", "Qwen/Qwen3.5-9B")
    sc = tinker.ServiceClient()

    caps = sc.get_server_capabilities()
    report = {"base_model": base_model, "tinker_version": tinker.__version__}
    report["supported_models"] = [m.model_name for m in caps.supported_models]

    client = sc.create_sampling_client(base_model=base_model)
    tok = client.get_tokenizer()

    def mi(text):
        return types.ModelInput.from_ints(tok.encode(text))

    probes = {
        "paris": "The capital of France is Paris.",
        "berlin": "The capital of France is Berlin.",
        "banana": "The capital of France is banana.",
    }

    report["compute_logprobs"] = {}
    for name, text in probes.items():
        ids = tok.encode(text)
        lp = client.compute_logprobs(mi(text)).result()
        report["compute_logprobs"][name] = {
            "text": text,
            "n_tokens": len(ids),
            "n_logprobs": len(lp),
            "first_is_none": lp[0] is None,
            "per_token": [
                {"token": tok.decode([i]), "logprob": v} for i, v in zip(ids, lp)
            ],
            "sum_logprob": sum(v for v in lp if v is not None),
            "mean_logprob": sum(v for v in lp if v is not None) / max(1, sum(1 for v in lp if v is not None)),
        }

    ctx = "Contract excerpt: This Agreement shall be governed by the laws of the State of New York.\nQuestion: What is the governing law?\nAnswer: "
    cands = [
        "the laws of the State of New York",
        "the laws of the State of Delaware",
        "This Agreement shall be governed by the laws of the State of New York",
        "the Parties hereto",
    ]
    report["candidate_scoring"] = []
    ctx_ids = tok.encode(ctx)
    ctx_lp = client.compute_logprobs(mi(ctx)).result()
    for c in cands:
        cand_ids = tok.encode(c)
        full_ids = ctx_ids + cand_ids
        lp = client.compute_logprobs(types.ModelInput.from_ints(full_ids)).result()
        tail = [v for v in lp[len(ctx_ids):] if v is not None]
        report["candidate_scoring"].append(
            {
                "candidate": c,
                "n_cand_tokens": len(tail),
                "sum_logprob": sum(tail),
                "mean_logprob": sum(tail) / len(tail),
            }
        )
    report["ctx_prefix_stable"] = all(
        abs((a or 0) - (b or 0)) < 1e-6
        for a, b in zip(ctx_lp[1:], client.compute_logprobs(mi(ctx)).result()[1:])
    )

    sp = types.SamplingParams(max_tokens=8, temperature=0.0)
    for k in (0, 1, 5, 20, 100):
        try:
            resp = client.sample(
                prompt=mi("The capital of France is Paris."),
                num_samples=1,
                sampling_params=sp,
                include_prompt_logprobs=True,
                topk_prompt_logprobs=k,
            ).result()
            seq = resp.sequences[0]
            tkpl = getattr(resp, "topk_prompt_logprobs", None)
            entry = {
                "ok": True,
                "response_attrs": [a for a in dir(resp) if not a.startswith("_")],
                "sequence_attrs": [a for a in dir(seq) if not a.startswith("_")],
                "prompt_logprobs_head": (getattr(resp, "prompt_logprobs", None) or [None] * 4)[:4],
                "topk_type": type(tkpl).__name__,
            }
            if tkpl is not None:
                entry["topk_attrs"] = [a for a in dir(tkpl) if not a.startswith("_")]
                entry["topk_repr_head"] = repr(tkpl)[:900]
            report.setdefault("sample_prompt_logprobs", {})[str(k)] = entry
        except Exception as exc:
            report.setdefault("sample_prompt_logprobs", {})[str(k)] = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}"[:400],
            }

    json.dump(report, sys.stdout, indent=2, default=str)
    print()


if __name__ == "__main__":
    main()
