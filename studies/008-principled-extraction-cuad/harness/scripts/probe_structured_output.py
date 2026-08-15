from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

BASE_URL = "https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1"
ANTHROPIC_URL = "https://tinker.thinkingmachines.dev/services/tinker-prod/anthropic/api/v1/messages"
USER_AGENT = "curl/8.7.1"

MODELS = ["Qwen/Qwen3.5-4B", "Qwen/Qwen3.5-9B", "thinkingmachines/Inkling-Small"]

SMALL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "status": {"type": "string", "enum": ["active", "expired", "unknown"]},
        "parties": {"type": "array", "items": {"type": "string"}},
        "year": {"type": "integer"},
    },
    "required": ["title", "status", "parties", "year"],
    "additionalProperties": False,
}

ADVERSARIAL_PROMPT = (
    "Here is a contract summary: The Distribution Agreement between Acme Corp "
    "and Globex Inc was signed in 2019 and is still in force.\n\n"
    "Report the title, status (active/expired/unknown), parties and year. "
    "First explain your reasoning in a short paragraph of prose, then present "
    "the answer as a JSON object inside a ```json markdown code block, and "
    "finish with a one-sentence caveat."
)

CUAD_CATEGORIES = [
    "governing_law",
    "expiration_date",
    "renewal_term",
    "notice_period_to_terminate_renewal",
    "exclusivity",
    "non_compete",
    "change_of_control",
    "anti_assignment",
    "cap_on_liability",
    "insurance",
    "audit_rights",
    "most_favored_nation",
]

CUAD_SCHEMA = {
    "type": "object",
    "properties": {
        "extractions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CUAD_CATEGORIES},
                    "spans": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "principles_cited": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["category", "spans", "principles_cited"],
                "additionalProperties": False,
            },
        },
        "absent": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CUAD_CATEGORIES},
                    "principles_cited": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["category", "principles_cited"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["extractions", "absent"],
    "additionalProperties": False,
}

CUAD_CONTRACT = """DISTRIBUTION AGREEMENT

This Distribution Agreement (the "Agreement") is entered into as of March 3, 2019
(the "Effective Date") by and between Acme Corporation, a Delaware corporation
("Supplier"), and Globex International Inc., a New York corporation ("Distributor").

1. TERM. The initial term of this Agreement shall be three (3) years from the
Effective Date and shall automatically renew for successive one (1) year terms
unless either party gives written notice of non-renewal at least ninety (90) days
prior to the end of the then-current term.

2. EXCLUSIVITY. Supplier hereby appoints Distributor as its sole and exclusive
distributor of the Products in the Territory during the Term.

3. ASSIGNMENT. Neither party may assign this Agreement, in whole or in part,
without the prior written consent of the other party, which consent shall not be
unreasonably withheld.

4. LIMITATION OF LIABILITY. In no event shall either party's aggregate liability
under this Agreement exceed the total fees paid by Distributor to Supplier in the
twelve (12) months preceding the claim.

5. INSURANCE. Distributor shall maintain commercial general liability insurance
with limits of not less than $2,000,000 per occurrence.

6. GOVERNING LAW. This Agreement shall be governed by and construed in accordance
with the laws of the State of New York, without regard to its conflict of laws
principles.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.
"""

CUAD_SYSTEM = (
    "You are a careful analyst. You read a document and produce a single JSON "
    "object that answers the task exactly as specified. You never add commentary "
    "outside the JSON object."
)

CUAD_TARGETS = {
    "governing_law": "the state/country whose law governs the contract",
    "expiration_date": "the date on which the contract's initial term expires",
    "renewal_term": "the length of any renewal term",
    "notice_period_to_terminate_renewal": "the notice period required to avoid renewal",
    "exclusivity": "an exclusive dealing or exclusive appointment obligation",
    "non_compete": "a restriction on competing with the counterparty",
    "change_of_control": "a right triggered by a change of control of a party",
    "anti_assignment": "a restriction on assigning the contract",
    "cap_on_liability": "a cap or limitation on a party's aggregate liability",
    "insurance": "an obligation to maintain insurance",
    "audit_rights": "a right to audit the counterparty's books or records",
    "most_favored_nation": "a most-favored-nation or best-pricing obligation",
}


def cuad_prompt(invite_prose: bool) -> str:
    lines = [
        "TASK DEFINITION",
        "Read the contract and decide, for each target category, whether the "
        "contract contains a clause of that type.",
        "",
        "Decision kinds: extraction, absence",
        "",
        "Targets (you must make exactly one decision per target):",
    ]
    for t, d in CUAD_TARGETS.items():
        lines.append(f"- {t}: {d}")
    lines += [
        "",
        "The `principles_cited` field must be left as an empty list for every "
        "decision. Do not populate it.",
        "",
        "OUTPUT FORMAT",
        "Reply with one JSON object and nothing else. It must validate against "
        "this JSON Schema:",
        json.dumps(CUAD_SCHEMA, indent=2, sort_keys=True),
        "",
        "DOCUMENT",
        "Title: Distribution Agreement",
        "Id: probe_0001",
        "---",
        CUAD_CONTRACT,
        "---",
    ]
    if invite_prose:
        lines += [
            "",
            "Explain your reasoning in prose first, then give the JSON inside a "
            "```json markdown code block.",
        ]
    return "\n".join(lines)


def post(payload: dict[str, Any], timeout: int = 600) -> dict[str, Any]:
    key = os.environ.get("TINKER_API_KEY")
    if not key:
        raise SystemExit("TINKER_API_KEY is not set")
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return {
                "http_status": resp.status,
                "latency_ms": int((time.time() - t0) * 1000),
                "body": json.loads(raw),
            }
    except urllib.error.HTTPError as exc:
        return {
            "http_status": exc.code,
            "latency_ms": int((time.time() - t0) * 1000),
            "error_body": exc.read().decode()[:4000],
        }
    except Exception as exc:
        return {
            "http_status": None,
            "latency_ms": int((time.time() - t0) * 1000),
            "transport_error": repr(exc)[:800],
        }


def get(path: str) -> dict[str, Any]:
    key = os.environ.get("TINKER_API_KEY")
    req = urllib.request.Request(
        BASE_URL + path,
        headers={"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return {"http_status": resp.status, "body": resp.read().decode()[:4000]}
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code, "error_body": exc.read().decode()[:4000]}
    except Exception as exc:
        return {"http_status": None, "transport_error": repr(exc)[:500]}


def post_anthropic(payload: dict[str, Any], timeout: int = 600) -> dict[str, Any]:
    key = os.environ.get("TINKER_API_KEY")
    if not key:
        raise SystemExit("TINKER_API_KEY is not set")
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {
                "http_status": resp.status,
                "latency_ms": int((time.time() - t0) * 1000),
                "body": json.loads(resp.read().decode()),
            }
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code, "error_body": exc.read().decode()[:4000]}
    except Exception as exc:
        return {"http_status": None, "transport_error": repr(exc)[:800]}


def phase_anthropic(args) -> dict[str, Any]:
    trials = []
    for model in args.models:
        for tc_name, tc in (
            ("forced_named_tool", {"type": "tool", "name": "report"}),
            ("any_tool", {"type": "any"}),
        ):
            for i in range(args.n):
                payload = {
                    "model": model,
                    "max_tokens": args.max_tokens,
                    "messages": [{"role": "user", "content": ADVERSARIAL_PROMPT}],
                    "tools": [
                        {
                            "name": "report",
                            "description": "Report the structured answer.",
                            "input_schema": SMALL_SCHEMA,
                        }
                    ],
                    "tool_choice": tc,
                }
                resp = post_anthropic(payload)
                body = resp.get("body") or {}
                blocks = body.get("content") or []
                tool_use = [b for b in blocks if b.get("type") == "tool_use"]
                text = "".join(b.get("text") or "" for b in blocks if b.get("type") == "text")
                trials.append(
                    {
                        "model": model,
                        "variant": tc_name,
                        "i": i,
                        "request": payload,
                        "http_status": resp.get("http_status"),
                        "stop_reason": body.get("stop_reason"),
                        "block_types": [b.get("type") for b in blocks],
                        "emitted_tool_use": bool(tool_use),
                        "tool_input": tool_use[0].get("input") if tool_use else None,
                        "tool_input_valid": small_schema_check(tool_use[0].get("input"))[0] if tool_use else False,
                        "text": text,
                        "error_body": resp.get("error_body"),
                    }
                )
    return {"trials": trials}


def variants(schema: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (
            "json_schema_current",
            "response_format json_schema, name + schema (what tinker_backend would send if it sent json_schema)",
            {"response_format": {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}}},
        ),
        (
            "json_schema_strict",
            "response_format json_schema with strict:true and name",
            {"response_format": {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": schema}}},
        ),
        (
            "json_schema_no_name",
            "response_format json_schema with strict:true, no name",
            {"response_format": {"type": "json_schema", "json_schema": {"strict": True, "schema": schema}}},
        ),
        (
            "json_object",
            "response_format json_object (what tinker_backend sends today)",
            {"response_format": {"type": "json_object"}},
        ),
        (
            "guided_json",
            "vLLM guided decoding: top-level guided_json",
            {"guided_json": schema},
        ),
        (
            "guided_json_backend",
            "vLLM guided decoding: guided_json + guided_decoding_backend=xgrammar",
            {"guided_json": schema, "guided_decoding_backend": "xgrammar"},
        ),
        (
            "guided_json_outlines",
            "vLLM guided decoding: guided_json + guided_decoding_backend=outlines",
            {"guided_json": schema, "guided_decoding_backend": "outlines"},
        ),
        (
            "structured_outputs",
            "vLLM >=0.10 structured_outputs {json: schema}",
            {"structured_outputs": {"json": schema}},
        ),
        (
            "extra_body_nested",
            "guided_json nested under extra_body (wrong for raw HTTP; tests param tolerance)",
            {"extra_body": {"guided_json": schema}},
        ),
        (
            "nvext_guided_json",
            "NIM-style nvext.guided_json",
            {"nvext": {"guided_json": schema}},
        ),
        (
            "bogus_param",
            "control: an obviously unknown parameter",
            {"zzz_definitely_not_a_real_param": 12345},
        ),
        (
            "bogus_response_format_type",
            "control: response_format with an invalid type value",
            {"response_format": {"type": "not_a_real_format"}},
        ),
        (
            "json_schema_missing_body",
            "control: response_format type json_schema with no json_schema key",
            {"response_format": {"type": "json_schema"}},
        ),
        (
            "tools_required",
            "function calling: tools + tool_choice=required, schema as function parameters",
            {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "report",
                            "description": "Report the structured answer.",
                            "parameters": schema,
                        },
                    }
                ],
                "tool_choice": "required",
            },
        ),
        (
            "tools_forced",
            "function calling: tool_choice pinned to the single function by name",
            {
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "report",
                            "description": "Report the structured answer.",
                            "parameters": schema,
                        },
                    }
                ],
                "tool_choice": {"type": "function", "function": {"name": "report"}},
            },
        ),
        (
            "none",
            "control: no structured-output parameter at all",
            {},
        ),
    ]


def summarize(resp: dict[str, Any]) -> dict[str, Any]:
    out = {"http_status": resp.get("http_status"), "latency_ms": resp.get("latency_ms")}
    if "error_body" in resp:
        out["error_body"] = resp["error_body"]
        return out
    if "transport_error" in resp:
        out["transport_error"] = resp["transport_error"]
        return out
    body = resp.get("body") or {}
    choice = (body.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    out["content"] = msg.get("content") or ""
    out["reasoning_content"] = msg.get("reasoning_content") or ""
    out["tool_calls"] = msg.get("tool_calls")
    out["finish_reason"] = choice.get("finish_reason")
    out["usage"] = body.get("usage")
    return out


def analyzed_text(variant: str, summary: dict[str, Any]) -> str:
    if variant.startswith("tools_"):
        calls = summary.get("tool_calls") or []
        if calls:
            return ((calls[0].get("function") or {}).get("arguments")) or ""
        return summary.get("content") or ""
    return summary.get("content") or ""


def classify(content: str, schema_check) -> dict[str, Any]:
    has_fence = "```" in content
    stripped = content.strip()
    try:
        parsed = json.loads(stripped)
        strict_json = isinstance(parsed, dict)
    except Exception:
        parsed = None
        strict_json = False
    lenient = None
    if not strict_json:
        s = stripped
        i = s.find("{")
        j = s.rfind("}")
        if i >= 0 and j > i:
            try:
                lenient = json.loads(s[i : j + 1])
            except Exception:
                lenient = None
    obj = parsed if strict_json else lenient
    valid = schema_check(obj) if isinstance(obj, dict) else (False, "no object")
    return {
        "empty_content": stripped == "",
        "has_fence": has_fence,
        "strict_json": strict_json,
        "lenient_json": obj is not None,
        "schema_valid": valid[0],
        "schema_detail": valid[1],
        "leading_prose": (not strict_json) and bool(stripped) and not stripped.startswith("{"),
    }


def small_schema_check(obj: Optional[dict]) -> tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "not an object"
    want = {"title", "status", "parties", "year"}
    if set(obj) != want:
        return False, f"keys={sorted(obj)}"
    if obj.get("status") not in ("active", "expired", "unknown"):
        return False, f"status={obj.get('status')!r}"
    if not isinstance(obj.get("parties"), list):
        return False, "parties not a list"
    if not isinstance(obj.get("year"), int):
        return False, f"year type={type(obj.get('year')).__name__}"
    return True, "ok"


def cuad_schema_check(obj: Optional[dict]) -> tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "not an object"
    if set(obj) != {"extractions", "absent"}:
        return False, f"keys={sorted(obj)}"
    for key in ("extractions", "absent"):
        if not isinstance(obj[key], list):
            return False, f"{key} not a list"
        for item in obj[key]:
            if not isinstance(item, dict):
                return False, f"{key} item not an object"
            required = {"category", "spans", "principles_cited"} if key == "extractions" else {"category", "principles_cited"}
            if not required <= set(item):
                return False, f"{key} item missing {sorted(required - set(item))}"
            if set(item) - required:
                return False, f"{key} item extra {sorted(set(item) - required)}"
            if item["category"] not in CUAD_CATEGORIES:
                return False, f"unknown category {item['category']!r}"
            if not isinstance(item["principles_cited"], list):
                return False, "principles_cited not a list"
            if key == "extractions":
                if not isinstance(item["spans"], list) or not item["spans"]:
                    return False, "spans empty or not a list"
    return True, "ok"


def coverage_check(obj: Optional[dict]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {"covered": False, "reason": "unparseable"}
    seen: list[str] = []
    for key in ("extractions", "absent"):
        for item in obj.get(key) or []:
            if isinstance(item, dict) and isinstance(item.get("category"), str):
                seen.append(item["category"])
    missing = [c for c in CUAD_CATEGORIES if c not in seen]
    dupes = sorted({c for c in seen if seen.count(c) > 1})
    unknown = sorted({c for c in seen if c not in CUAD_CATEGORIES})
    return {
        "covered": not missing and not dupes and not unknown,
        "n_seen": len(seen),
        "missing": missing,
        "duplicated": dupes,
        "unknown": unknown,
    }


def phase_config(args) -> dict[str, Any]:
    out: dict[str, Any] = {"introspection": {}, "trials": []}
    for path in ("/models", "", "/chat/completions"):
        out["introspection"][path or "/"] = get(path)
    jobs = []
    for model in args.models:
        for name, desc, extra in variants(SMALL_SCHEMA):
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": ADVERSARIAL_PROMPT}],
                "temperature": args.temperature,
                "max_tokens": args.max_tokens,
                "seed": 0,
                **extra,
            }
            jobs.append((model, name, desc, payload))

    def run(job):
        model, name, desc, payload = job
        resp = post(payload)
        summary = summarize(resp)
        entry = {
            "model": model,
            "variant": name,
            "description": desc,
            "request": payload,
            "response": summary,
        }
        if "content" in summary:
            entry["analyzed_text"] = analyzed_text(name, summary)
            entry["analysis"] = classify(entry["analyzed_text"], small_schema_check)
        return entry

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        out["trials"] = list(pool.map(run, jobs))
    return out


def phase_stress(args) -> dict[str, Any]:
    jobs = []
    for model in args.models:
        for name, desc, extra in variants(SMALL_SCHEMA):
            if name not in args.variants:
                continue
            for i in range(args.n):
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": ADVERSARIAL_PROMPT}],
                    "temperature": 1.0,
                    "max_tokens": args.max_tokens,
                    "seed": 1000 + i,
                    **extra,
                }
                jobs.append((model, name, i, payload))

    def run(job):
        model, name, i, payload = job
        resp = post(payload)
        summary = summarize(resp)
        entry = {"model": model, "variant": name, "i": i, "response": summary}
        if "content" in summary:
            entry["analyzed_text"] = analyzed_text(name, summary)
            entry["analysis"] = classify(entry["analyzed_text"], small_schema_check)
        return entry

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        return {"samples": list(pool.map(run, jobs))}


def phase_rates(args) -> dict[str, Any]:
    prompt = cuad_prompt(invite_prose=False)
    jobs = []
    for model in args.models:
        for name, desc, extra in variants(CUAD_SCHEMA):
            if name not in args.variants:
                continue
            for i in range(args.n):
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": CUAD_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "seed": 2000 + i,
                    **extra,
                }
                jobs.append((model, name, i, payload))

    def run(job):
        model, name, i, payload = job
        resp = post(payload)
        summary = summarize(resp)
        entry = {"model": model, "variant": name, "i": i, "response": summary}
        if "content" in summary:
            entry["analyzed_text"] = analyzed_text(name, summary)
            entry["analysis"] = classify(entry["analyzed_text"], cuad_schema_check)
            content = entry["analyzed_text"].strip()
            obj = None
            try:
                obj = json.loads(content)
            except Exception:
                a, b = content.find("{"), content.rfind("}")
                if a >= 0 and b > a:
                    try:
                        obj = json.loads(content[a : b + 1])
                    except Exception:
                        obj = None
            entry["coverage"] = coverage_check(obj)
        return entry

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        return {"samples": list(pool.map(run, jobs)), "prompt": prompt, "schema": CUAD_SCHEMA}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["config", "stress", "rates", "anthropic"])
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--variants", nargs="*", default=["json_object"])
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if args.phase == "config":
        data = phase_config(args)
    elif args.phase == "stress":
        data = phase_stress(args)
    elif args.phase == "rates":
        data = phase_rates(args)
    else:
        data = phase_anthropic(args)

    data["meta"] = {
        "phase": args.phase,
        "base_url": BASE_URL,
        "models": args.models,
        "variants": args.variants,
        "n": args.n,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
