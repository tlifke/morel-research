from __future__ import annotations

import glob
import html
import json
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

STUDY_ROOT = Path(__file__).resolve().parents[2]
if str(STUDY_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDY_ROOT))

from harness.envs.cuad_env import CuadEnvironment
from harness.model_registry import REFERENCE_TOKENIZER_ID
from harness.models import Principle, PrincipleSet, TaskOutput
from harness.principles_io import load_principle_set
from harness.prompts import PROMPT_TEMPLATE_VERSION, build_prompt, render_principles

AS_RUN_PRINCIPLES = STUDY_ROOT / "principles" / "pilot" / "candidates_round2.yaml"
AS_RUN_VERSION = "pilot-round2-all23"
WORKING_SET = STUDY_ROOT / "principles" / "working_set.yaml"
SMOKE_ROOT = STUDY_ROOT / "data" / "traces" / "smoke"
RUN_ID = "2026-08-16T18-16-01Z-smoke"
SPLIT = "scratch"
CONTRACT_ID = "ADUROBIOTECH,INC_06_02_2020-EX-10.7-CONSULTING AGREEMENT"
SCHEMA_VARIANT = "field_present"
OUT = STUDY_ROOT / "reviews" / "prompt-inspector.html"

CONDITIONS = ["C1", "C2", "C3"]
BLOCK_ORDER = ["task_definition", "principles", "citation", "output_format", "instance"]
BLOCK_TITLES = {
    "system": "SYSTEM MESSAGE",
    "task_definition": "TASK DEFINITION",
    "principles": "PRINCIPLES",
    "citation": "CITATION INSTRUCTION",
    "output_format": "OUTPUT FORMAT (JSON Schema)",
    "instance": "DOCUMENT (the contract)",
}


def load_working_set() -> tuple[PrincipleSet, dict[str, str]]:
    payload = yaml.safe_load(WORKING_SET.read_text(encoding="utf-8"))
    rows = payload["principles"]
    notes: dict[str, str] = {}
    normalised = []
    for row in rows:
        row = dict(row)
        prov = row.get("provenance")
        if isinstance(prov, list):
            notes[row["id"]] = " + ".join(prov)
            row["provenance"] = prov[0] if prov else "authored"
        normalised.append(
            Principle.model_validate(
                {
                    "id": row["id"],
                    "statement": row["statement"],
                    "trigger_guidance": row["trigger_guidance"],
                    "type": row["type"],
                    "scope": row.get("scope") or [],
                    "provenance": row["provenance"],
                }
            )
        )
    return PrincipleSet(version="working_set", principles=normalised), notes


def load_traces() -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(glob.glob(str(SMOKE_ROOT / "traces" / RUN_ID / "*.json"))):
        trace = json.loads(Path(path).read_text(encoding="utf-8"))
        out[(trace["contract_id"], trace["condition"])] = trace
    return out


def load_trials() -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    path = SMOKE_ROOT / RUN_ID / "trials.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out[(row["contract_id"], row["condition"])] = row
    return out


def load_decisions() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    path = SMOKE_ROOT / RUN_ID / "decisions.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out.setdefault(row["trial_id"], []).append(row)
    return out


class Counter:
    def __init__(self) -> None:
        from transformers import AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(REFERENCE_TOKENIZER_ID)

    def __call__(self, text: str) -> int:
        return len(self.tok(text, add_special_tokens=False)["input_ids"])


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def render_lines(text: str) -> str:
    out = []
    for raw in text.split("\n"):
        if raw == "":
            out.append('<div class="ln blank"></div>')
            continue
        stripped = raw.rstrip(" \t")
        trail = raw[len(stripped) :]
        body = esc(stripped)
        if trail:
            body += f'<span class="trail">{esc(trail).replace(" ", "&middot;").replace(chr(9), "&#8594;")}</span>'
        out.append(f'<div class="ln">{body}</div>')
    return "".join(out)


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "&mdash;"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return esc(str(value))


def main() -> None:
    as_run = load_principle_set(AS_RUN_PRINCIPLES, version=AS_RUN_VERSION)
    working, prov_notes = load_working_set()
    env = CuadEnvironment(principle_set=as_run)
    instances = {i.contract_id: i for i in env.load_instances(SPLIT)}
    if CONTRACT_ID not in instances:
        raise SystemExit(f"contract {CONTRACT_ID!r} not in split {SPLIT!r}")
    instance = instances[CONTRACT_ID]
    task = env.task_definition()

    traces = load_traces()
    trials = load_trials()
    decisions = load_decisions()

    count = Counter()

    bundles = {
        cond: build_prompt(
            task, as_run, cond, SCHEMA_VARIANT, instance, env.output_model()
        )
        for cond in CONDITIONS
    }

    verify: list[dict[str, Any]] = []
    for cond in CONDITIONS:
        trace = traces.get((CONTRACT_ID, cond))
        row: dict[str, Any] = {"condition": cond}
        if trace is None:
            row.update({"status": "MISSING", "detail": "no trace for this condition"})
        else:
            sent = trace["attempts"][0]["prompt_sent"]
            mine = bundles[cond].as_messages()
            same = sent == mine
            row.update(
                {
                    "status": "PASS" if same else "FAIL",
                    "n_prompt_tokens": trace["attempts"][0]["n_prompt_tokens"],
                    "prompt_sha256": trace["attempts"][0].get("prompt_sent_sha256"),
                    "trial_id": trace["trial_id"],
                }
            )
            if not same:
                diffs = []
                for a, b in zip(mine, sent):
                    if a["content"] != b["content"]:
                        diffs.append(
                            {
                                "role": a["role"],
                                "rendered_len": len(a["content"]),
                                "sent_len": len(b["content"]),
                            }
                        )
                row["diffs"] = diffs
        verify.append(row)

    all_pass = all(r["status"] == "PASS" for r in verify)

    working_principle_block = render_principles(working)

    unique_blocks: list[dict[str, Any]] = []
    unique_blocks.append(
        {
            "key": "system",
            "role": "system",
            "text": bundles["C1"].system,
            "conds": ["C1", "C2", "C3"],
            "added": None,
        }
    )
    seen: dict[str, list[str]] = {}
    for cond in CONDITIONS:
        for key in BLOCK_ORDER:
            text = bundles[cond].blocks.get(key)
            if text is None:
                continue
            seen.setdefault((key, text), []).append(cond)
    ordered: list[tuple[str, str, list[str]]] = []
    for cond in CONDITIONS:
        for key in BLOCK_ORDER:
            text = bundles[cond].blocks.get(key)
            if text is None:
                continue
            entry = (key, text, seen[(key, text)])
            if entry not in ordered:
                ordered.append(entry)
    order_index = {k: i for i, k in enumerate(BLOCK_ORDER)}
    ordered.sort(key=lambda e: (order_index[e[0]], e[2][0]))
    for key, text, conds in ordered:
        added = None
        if conds == ["C2", "C3"]:
            added = "C2"
        elif conds == ["C3"]:
            added = "C3"
        unique_blocks.append(
            {
                "key": key,
                "role": "user",
                "text": text,
                "conds": conds,
                "added": added,
            }
        )
    unique_blocks.append(
        {
            "key": "principles",
            "role": "user",
            "text": working_principle_block,
            "conds": [],
            "added": "C2",
            "variant": "working_set",
        }
    )

    for blk in unique_blocks:
        blk["tokens"] = count(blk["text"])

    token_table: dict[str, dict[str, Optional[int]]] = {}
    for cond in CONDITIONS:
        per: dict[str, Optional[int]] = {"system": count(bundles[cond].system)}
        for key in BLOCK_ORDER:
            text = bundles[cond].blocks.get(key)
            per[key] = count(text) if text is not None else None
        per["__sum__"] = sum(v for v in per.values() if v is not None)
        trace = traces.get((CONTRACT_ID, cond))
        per["__trace__"] = (
            trace["attempts"][0]["n_prompt_tokens"] if trace is not None else None
        )
        token_table[cond] = per

    working_tokens = count(working_principle_block)

    outputs: dict[str, dict[str, Any]] = {}
    for cond in CONDITIONS:
        trace = traces.get((CONTRACT_ID, cond))
        trial = trials.get((CONTRACT_ID, cond))
        if trace is None or trial is None:
            outputs[cond] = {"missing": True}
            continue
        attempt = trace["attempts"][0]
        raw = attempt.get("response_text") or ""
        parsed: Optional[dict[str, Any]] = None
        parse_error = None
        try:
            parsed = TaskOutput.model_validate_json(raw).model_dump()
        except Exception as exc:  # noqa: BLE001
            parse_error = str(exc)[:400]
        rows = decisions.get(trial["trial_id"], [])
        outputs[cond] = {
            "missing": False,
            "raw": raw,
            "reasoning": attempt.get("reasoning_content") or "",
            "parsed": parsed,
            "parse_error": parse_error,
            "outcome": trial["outcome"],
            "n_completion_tokens": trial["n_completion_tokens"],
            "n_prompt_tokens": trial["n_prompt_tokens"],
            "latency_ms": trial["latency_ms"],
            "truncated": trial["completion_truncated"],
            "level_a": trial["answer"]["level_a"]["micro"],
            "level_b": trial["answer"]["level_b"],
            "citation": trial["citation"],
            "compliance": trial["compliance"],
            "leakage": trial["leakage"],
            "decisions": [
                {
                    "target": d["target"],
                    "kind": d["decision_kind"],
                    "cell": (d["answer_score"] or {}).get("cell"),
                    "span_f1": (d["answer_score"] or {}).get("span_f1"),
                    "predicted": (d.get("predicted") or {}).get("spans", []),
                    "gold": d["gold"]["spans"],
                    "cited": d["principles_cited"],
                }
                for d in sorted(rows, key=lambda r: r["decision_idx"])
            ],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        build_html(
            instance=instance,
            unique_blocks=unique_blocks,
            token_table=token_table,
            working_tokens=working_tokens,
            working_set=working,
            as_run=as_run,
            prov_notes=prov_notes,
            verify=verify,
            all_pass=all_pass,
            outputs=outputs,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "out": str(OUT),
                "byte_identity": verify,
                "all_pass": all_pass,
                "tokens": token_table,
                "working_set_principle_block_tokens": working_tokens,
            },
            indent=2,
        )
    )


ANNOTATIONS = {
    "instance": {
        "id": "A1",
        "title": "DEFECT A1 &mdash; filename leakage",
        "body": (
            "<code>render_instance()</code> in <code>harness/prompts.py</code> prints "
            "<code>Title:</code> and <code>Id:</code> above the contract body. CUAD "
            "contract ids encode the filing date. The id in view here is "
            "<code>ADUROBIOTECH,INC_06_02_2020-EX-10.7-CONSULTING AGREEMENT</code> "
            "&mdash; <code>06_02_2020</code> is a date the model can read without ever "
            "looking at the contract. In the sibling trial of the same smoke run "
            "(<code>WOMENSGOLFUNLIMITEDINC_03_29_2000-EX-10.13-ENDORSEMENT AGREEMENT&hellip;</code>, "
            "C1) the model returned Agreement Date = <code>03_29_2000</code>, a string "
            "that appears in the id and <em>nowhere in the contract text</em>. It scored "
            "as a false positive with <code>invented_language_rate = 1.0</code>. The "
            "model is being handed an answer channel outside the document."
        ),
    },
    "task_definition": {
        "id": "A2",
        "title": "DEFECT A2 &mdash; answer-format hint",
        "body": (
            "Every target line ends with <code>(answer format: &hellip;)</code>. That "
            "text is appended by <code>load_category_definitions()</code> in "
            "<code>harness/envs/cuad_env.py</code>, which concatenates the CUAD CSV's "
            "<code>Answer Format</code> column onto the <code>Description</code> column. "
            "The <code>Answer Format</code> column describes what a human answers, not "
            "what span to cut. It pushes minimal-value answers: on this contract the "
            "model returned Governing Law = <code>\"State of California\"</code>, "
            "verbatim-exact in the text, against a sentence-level gold span &mdash; "
            "span-F1 <code>0.176</code> in all three conditions. The span was right; the "
            "granularity was wrong, and the prompt asked for the wrong granularity."
        ),
    },
    "granularity": {
        "id": "A3",
        "title": "OPEN QUESTION A3 &mdash; granularity is never specified",
        "body": (
            "Nowhere in the prompt is the expected span granularity stated. The framing "
            "says &ldquo;extract every verbatim span of the contract that the category "
            "covers&rdquo; &mdash; verbatim-ness is constrained, extent is not. The "
            "output schema types <code>spans</code> as an array of strings with "
            "<code>minLength: 1</code> and says nothing about what a span is. The only "
            "granularity signal reaching the model is the answer-format hint (A2), which "
            "points the wrong way. The as-run principle block "
            "(<code>pilot-round2-all23</code>) does not fix it either. "
            "<strong>The working set does:</strong> <code>w01</code> states the "
            "sentence-level rule with a carve-out for single-value categories &mdash; but "
            "the working set was not the set used in this run. Toggle the principle set "
            "above to read it. This is the open design question: state granularity in the "
            "task definition, or leave it to a principle and measure whether the "
            "principle carries it."
        ),
    },
}


def build_html(
    instance: Any,
    unique_blocks: list[dict[str, Any]],
    token_table: dict[str, dict[str, Optional[int]]],
    working_tokens: int,
    working_set: PrincipleSet,
    as_run: PrincipleSet,
    prov_notes: dict[str, str],
    verify: list[dict[str, Any]],
    all_pass: bool,
    outputs: dict[str, dict[str, Any]],
) -> str:
    parts: list[str] = []
    a = parts.append

    a("<!doctype html>")
    a('<html lang="en"><head><meta charset="utf-8">')
    a('<meta name="viewport" content="width=device-width, initial-scale=1">')
    a("<title>Study 008 &mdash; Prompt Inspector</title>")
    a("<style>" + CSS + "</style></head>")
    a('<body data-cond="C1" data-pset="as_run" data-delta="on">')

    a('<header class="top">')
    a("<h1>Prompt Inspector &mdash; study 008, conditions C1 / C2 / C3</h1>")
    a(
        '<p class="sub">Exactly what the model sees for one contract, rendered through '
        "<code>harness/prompts.py</code>. Nothing on this page is hand-written prompt "
        "text. Generated by <code>harness/scripts/render_prompt_inspector.py</code>.</p>"
    )
    a("</header>")

    banner_cls = "ok" if all_pass else "bad"
    a(f'<section class="verify {banner_cls}">')
    a(
        "<h2>Byte-identity assertion: "
        + ("PASS" if all_pass else "FAIL")
        + "</h2>"
    )
    a(
        "<p>The prompt rendered on this page was compared element-by-element against "
        "<code>attempts[0].prompt_sent</code> recorded in the trace store for the same "
        f"trial (run <code>{esc(RUN_ID)}</code>). Equality is on the full messages list "
        "(role + content), not a summary.</p>"
    )
    a('<div class="scrollx"><table class="tbl"><thead><tr>'
      "<th>condition</th><th>result</th><th>trial_id</th>"
      "<th>prompt_sent_sha256</th><th>n_prompt_tokens (backend)</th>"
      "</tr></thead><tbody>")
    for row in verify:
        a(
            "<tr><td>{c}</td><td class='{k}'>{s}</td><td class='mono small'>{t}</td>"
            "<td class='mono small'>{h}</td><td>{n}</td></tr>".format(
                c=row["condition"],
                k="pass" if row["status"] == "PASS" else "fail",
                s=row["status"],
                t=esc(str(row.get("trial_id", "&mdash;"))),
                h=esc(str(row.get("prompt_sha256") or "—")),
                n=row.get("n_prompt_tokens", "—"),
            )
        )
    a("</tbody></table></div>")
    a("</section>")

    a('<section class="controls">')
    a('<div class="ctlgroup"><span class="ctllabel">Condition</span><div class="seg">')
    for cond in CONDITIONS:
        a(f'<button class="segbtn" data-setcond="{cond}">{cond}</button>')
    a("</div></div>")
    a('<div class="ctlgroup"><span class="ctllabel">Principle set</span><div class="seg">')
    a('<button class="segbtn" data-setpset="as_run">as-run (23)</button>')
    a('<button class="segbtn" data-setpset="working_set">working_set (9)</button>')
    a("</div></div>")
    a(
        '<div class="ctlgroup"><span class="ctllabel">Delta</span>'
        '<label class="chk"><input type="checkbox" id="deltachk" checked> '
        "highlight what this condition adds</label></div>"
    )
    a("</section>")

    a('<section class="meta"><div class="scrollx"><table class="tbl"><tbody>')
    for label, value in [
        ("contract_id", instance.contract_id),
        ("title", instance.title),
        ("split", instance.split + "  (the only split free to display)"),
        ("n_tokens (contract text, Qwen/Qwen3-8B)", str(instance.n_tokens)),
        ("n_chars (contract text)", str(len(instance.text))),
        ("model", "Qwen/Qwen3.5-9B via Tinker"),
        ("run_id", RUN_ID),
        ("schema_variant", SCHEMA_VARIANT),
        ("prompt_template_version", PROMPT_TEMPLATE_VERSION),
        ("as-run principle set", f"{as_run.version} ({len(as_run.principles)} principles)"),
        (
            "working set (not as-run)",
            f"{working_set.version} ({len(working_set.principles)} principles, w01&ndash;w09)",
        ),
        ("token counter", REFERENCE_TOKENIZER_ID + " (D-12 reference tokenizer)"),
    ]:
        a(f'<tr><th class="k">{esc(label)}</th><td class="mono">{esc(value)}</td></tr>')
    a("</tbody></table></div>")
    a(
        '<p class="warn"><strong>Principle-set caveat.</strong> The smoke run used '
        "<code>principles/pilot/candidates_round2.yaml</code> "
        f"(<code>{esc(as_run.version)}</code>, 23 principles). "
        "<code>principles/working_set.yaml</code> (9 principles, w01&ndash;w09) was "
        "<em>not</em> the set that produced the outputs below. Both are rendered here; "
        "the byte-identity assertion holds only for the as-run set, and the "
        "working-set view is labelled as prospective wherever it is shown.</p>"
    )
    a("</section>")

    a('<section class="tokens"><h2>Token counts per block, per condition</h2>')
    a(
        "<p>Counted with <code>"
        + esc(REFERENCE_TOKENIZER_ID)
        + "</code> (<code>add_special_tokens=False</code>), per D-12. Blocks are counted "
        "individually, so the column sum is slightly below the backend's "
        "<code>n_prompt_tokens</code>, which also covers the chat template and the "
        "<code>\\n\\n</code> joins between blocks. Both are shown.</p>"
    )
    a('<div class="scrollx"><table class="tbl tokens-tbl"><thead><tr><th>block</th>')
    for cond in CONDITIONS:
        a(f"<th>{cond}</th>")
    a("<th>C2 &minus; C1</th><th>C3 &minus; C2</th></tr></thead><tbody>")
    keys = ["system"] + BLOCK_ORDER
    for key in keys:
        vals = [token_table[c].get(key) for c in CONDITIONS]
        a(f'<tr><th class="k">{esc(BLOCK_TITLES[key])}</th>')
        for v in vals:
            a(f'<td class="num">{"&mdash;" if v is None else v}</td>')
        d21 = (vals[1] or 0) - (vals[0] or 0)
        d32 = (vals[2] or 0) - (vals[1] or 0)
        a(f'<td class="num delta">{d21:+d}</td><td class="num delta">{d32:+d}</td>')
        a("</tr>")
    sums = [token_table[c]["__sum__"] for c in CONDITIONS]
    a('<tr class="sumrow"><th class="k">sum of blocks</th>')
    for v in sums:
        a(f'<td class="num">{v}</td>')
    a(
        f'<td class="num delta">{sums[1]-sums[0]:+d}</td>'
        f'<td class="num delta">{sums[2]-sums[1]:+d}</td></tr>'
    )
    tr = [token_table[c]["__trace__"] for c in CONDITIONS]
    a('<tr class="sumrow"><th class="k">n_prompt_tokens as reported by backend</th>')
    for v in tr:
        a(f'<td class="num">{"&mdash;" if v is None else v}</td>')
    a(
        f'<td class="num delta">{(tr[1] or 0)-(tr[0] or 0):+d}</td>'
        f'<td class="num delta">{(tr[2] or 0)-(tr[1] or 0):+d}</td></tr>'
    )
    a("</tbody></table></div>")
    a(
        '<p class="callout-sm"><strong>What the principle block costs.</strong> The '
        f"as-run PRINCIPLES block is <strong>{token_table['C2']['principles']} tokens</strong>. "
        f"Backend-reported prompt length goes from {tr[0]} (C1) to {tr[1]} (C2), a delta of "
        f"<strong>{(tr[1] or 0)-(tr[0] or 0)} tokens</strong> &mdash; this is the "
        "~2.4k the smoke run measured, and it is attributable in full to the PRINCIPLES "
        "block plus its blank-line join. C3 adds only the CITATION REQUIREMENT block "
        f"({token_table['C3']['citation']} tokens vs {token_table['C1']['citation']} for "
        f"the C1/C2 no-citation block, net {(tr[2] or 0)-(tr[1] or 0)}). For reference the "
        f"<em>working_set</em> PRINCIPLES block would be <strong>{working_tokens} tokens</strong>, "
        f"{token_table['C2']['principles'] - working_tokens} fewer than the as-run set.</p>"
    )
    a("</section>")

    a('<section class="annidx"><h2>Our annotations on this prompt</h2>')
    a(
        '<p class="sub">Three callouts appear inline below, anchored to the block where '
        "each originates. They are <strong>our commentary</strong> and are not part of "
        "what the model sees &mdash; annotation cards are outlined in amber, prompt "
        "content is on the dark monospace ground.</p>"
    )
    a("<ul class='annlist'>")
    for key in ("instance", "task_definition", "granularity"):
        ann = ANNOTATIONS[key]
        a(f'<li><span class="annpill">{ann["id"]}</span> {ann["title"]}</li>')
    a("</ul></section>")

    a('<section class="prompt"><h2>The complete prompt as sent</h2>')
    a(
        '<p class="sub">Blocks are in the order the harness joins them, separated in the '
        "real prompt by a blank line (<code>\\n\\n</code>). Text is verbatim. Blank lines "
        "show as a faint rule; trailing whitespace, if any, shows as "
        '<span class="trail">&middot;</span> marks.</p>'
    )

    for blk in unique_blocks:
        variant = blk.get("variant", "as_run")
        conds = blk["conds"]
        classes = ["block", f"blk-{blk['key']}", f"pset-{variant}"]
        if variant == "working_set":
            classes.append("cond-C2 cond-C3")
        else:
            classes += [f"cond-{c}" for c in conds]
        if blk["added"]:
            classes.append(f"added-{blk['added']}")
        badges = []
        if blk["added"] == "C2":
            badges.append('<span class="badge add2">added in C2</span>')
        elif blk["added"] == "C3":
            badges.append('<span class="badge add3">added in C3</span>')
        else:
            badges.append('<span class="badge base">all conditions</span>')
        if blk["key"] == "citation" and blk["added"] is None:
            badges = ['<span class="badge base">C1 &amp; C2 (replaced in C3)</span>']
        if variant == "working_set":
            badges.append(
                '<span class="badge prospective">working_set &mdash; NOT the set used '
                "in this run</span>"
            )
        role = blk["role"]
        collapsible = blk["key"] in ("instance", "output_format")
        a(f'<div class="{" ".join(classes)}">')
        a('<div class="blkhead">')
        a(f'<span class="blkname">{BLOCK_TITLES[blk["key"]]}</span>')
        a(f'<span class="role role-{role}">{role}</span>')
        a("".join(badges))
        a(f'<span class="tok">{blk["tokens"]} tok</span>')
        if collapsible:
            a('<button class="toggle" data-toggle>collapse</button>')
        a("</div>")
        if blk["key"] == "task_definition":
            a(annotation_card(ANNOTATIONS["task_definition"]))
            a(annotation_card(ANNOTATIONS["granularity"]))
        if blk["key"] == "instance":
            a(annotation_card(ANNOTATIONS["instance"]))
        body_cls = "blkbody scrolly" if collapsible else "blkbody"
        a(f'<div class="{body_cls}"><pre class="code">{render_lines(blk["text"])}</pre></div>')
        a("</div>")
        if blk["key"] == "instance":
            pass
    a("</section>")

    a('<section class="pset-working psetonly"><h2>working_set.yaml as loaded</h2>')
    a(
        '<p class="sub">Loaded through <code>harness/models.Principle</code> after one '
        "normalisation (see below). The rendered block above is produced by the same "
        "<code>render_principles()</code> the runner uses.</p>"
    )
    a('<div class="scrollx"><table class="tbl"><thead><tr><th>id</th><th>type</th>'
      "<th>scope</th><th>provenance in file</th><th>provenance after normalisation</th>"
      "</tr></thead><tbody>")
    for p in working_set.principles:
        a(
            f'<tr><td class="mono">{esc(p.id)}</td><td>{esc(p.type)}</td>'
            f'<td class="small">{esc(", ".join(p.scope) or "all targets")}</td>'
            f'<td class="small">{esc(prov_notes.get(p.id, p.provenance))}</td>'
            f'<td class="mono small">{esc(p.provenance)}</td></tr>'
        )
    a("</tbody></table></div>")
    a(
        '<p class="warn"><strong>Normalisation applied by the generator, not by the '
        "harness.</strong> <code>working_set.yaml</code> stores <code>provenance</code> "
        "as a <em>list</em> (merged records have two source arms), while "
        "<code>harness/models.Principle.provenance</code> is a single-value "
        "<code>Literal</code>, so <code>principles_io.load_principle_set()</code> raises "
        "on this file. The generator reads the YAML directly and keeps only the first "
        "provenance value, discarding the rest, and drops the bookkeeping fields "
        "(<code>evidence</code>, <code>lineage</code>, <code>review</code>, &hellip;) "
        "that are not on the pinned model. <code>render_principles()</code> reads only "
        "<code>id</code>, <code>type</code>, <code>scope</code>, <code>statement</code> "
        "and <code>trigger_guidance</code>, so this normalisation is "
        "<strong>prompt-neutral</strong>: the rendered principle text is byte-identical "
        "to what a fixed loader would produce. Neither file was modified.</p>"
    )
    a("</section>")

    a('<section class="outputs"><h2>What the model actually returned</h2>')
    a(
        '<p class="sub">Pulled from the smoke trace store '
        f"(<code>data/traces/smoke/{esc(RUN_ID)}/</code>, gitignored) and embedded here, "
        "so this page survives the traces being deleted. The outputs below were produced "
        f"under the <strong>as-run</strong> principle set ({esc(as_run.version)}); there "
        "are no outputs for the working set.</p>"
    )
    for cond in CONDITIONS:
        out = outputs[cond]
        a(f'<div class="outblock cond-{cond}">')
        a(f"<h3>{cond} &mdash; model output</h3>")
        if out.get("missing"):
            a(
                '<p class="warn">No trace found for this condition in run '
                f"<code>{esc(RUN_ID)}</code>. Nothing is shown; nothing is inferred.</p>"
            )
            a("</div>")
            continue
        a('<div class="scrollx"><table class="tbl"><tbody>')
        for label, value in [
            ("outcome", out["outcome"]),
            ("n_prompt_tokens", out["n_prompt_tokens"]),
            ("n_completion_tokens", out["n_completion_tokens"]),
            ("completion_truncated", out["truncated"]),
            ("latency_ms", out["latency_ms"]),
        ]:
            a(f'<tr><th class="k">{esc(label)}</th><td class="mono">{fmt(value)}</td></tr>')
        a("</tbody></table></div>")

        a("<h4>Scores</h4>")
        la = out["level_a"]
        lb = out["level_b"]
        a('<div class="scrollx"><table class="tbl"><tbody>')
        counts = la["counts"]
        a(
            '<tr><th class="k">Level A confusion (12 decisions)</th>'
            f'<td class="mono">TP {counts["TP"]} / FP {counts["FP"]} / '
            f'TN {counts["TN"]} / FN {counts["FN"]}</td></tr>'
        )
        a(
            '<tr><th class="k">presence-class P / R / F1</th><td class="mono">'
            f'{fmt(la["presence_class"]["precision"])} / '
            f'{fmt(la["presence_class"]["recall"])} / '
            f'{fmt(la["presence_class"]["f1"])}</td></tr>'
        )
        a(
            '<tr><th class="k">absent-class P / R / F1</th><td class="mono">'
            f'{fmt(la["absent_class"]["precision"])} / '
            f'{fmt(la["absent_class"]["recall"])} / '
            f'{fmt(la["absent_class"]["f1"])}</td></tr>'
        )
        a(f'<tr><th class="k">Level B span_f1 (TP cells)</th><td class="mono">{fmt(lb.get("span_f1"))}</td></tr>')
        a(
            '<tr><th class="k">verbatim_exact_rate / not_found_rate</th>'
            f'<td class="mono">{fmt(lb.get("verbatim_exact_rate"))} / '
            f'{fmt(lb.get("verbatim_not_found_rate"))}</td></tr>'
        )
        a(
            '<tr><th class="k">compliance.pass_rate</th><td class="mono">'
            f'{fmt((out["compliance"] or {}).get("pass_rate"))} '
            "<span class='small'>(no checkers injected &rarr; unavailable, not 0)</span></td></tr>"
        )
        cit = out["citation"]
        a(
            '<tr><th class="k">citation F1</th><td class="mono">'
            + (
                fmt(cit.get("f1"))
                if cit
                else "&mdash; <span class='small'>no applicability source loaded; "
                "C3 citation metrics are NOT measurements</span>"
            )
            + "</td></tr>"
        )
        a(
            '<tr><th class="k">decisions with non-empty principles_cited</th>'
            f'<td class="mono">{out["leakage"]["n_decisions_with_nonempty_cited"]} / '
            f'{out["leakage"]["n_decisions"]}</td></tr>'
        )
        a("</tbody></table></div>")

        a("<h4>Parsed TaskOutput &mdash; 12 decisions</h4>")
        if out["parse_error"]:
            a(f'<p class="warn">re-parse failed: <code>{esc(out["parse_error"])}</code></p>')
        a('<div class="scrollx"><table class="tbl dec"><thead><tr>'
          "<th>target</th><th>kind</th><th>cell</th><th>span_f1</th>"
          "<th>predicted span(s)</th><th>gold span(s)</th><th>cited</th>"
          "</tr></thead><tbody>")
        for d in out["decisions"]:
            cell = d["cell"] or ""
            hl = ""
            if d["target"] == "Governing Law":
                hl = " rowhl-a2"
            if d["target"] == "Agreement Date":
                hl = " rowhl-a1"
            a(
                f'<tr class="cell-{cell}{hl}"><td>{esc(d["target"])}</td>'
                f'<td>{esc(d["kind"] or "—")}</td><td class="cellbadge">{esc(cell or "—")}</td>'
                f'<td class="num">{fmt(d["span_f1"])}</td>'
                f'<td class="mono small">{esc(json.dumps(d["predicted"], ensure_ascii=False))}</td>'
                f'<td class="mono small">{esc(json.dumps(d["gold"], ensure_ascii=False))}</td>'
                f'<td class="mono small">{esc(json.dumps(d["cited"]))}</td></tr>'
            )
        a("</tbody></table></div>")

        a('<div class="block"><div class="blkhead">'
          '<span class="blkname">RAW RESPONSE (response_text, verbatim)</span>'
          f'<span class="tok">{len(out["raw"])} chars</span>'
          '<button class="toggle" data-toggle>collapse</button></div>'
          f'<div class="blkbody scrolly"><pre class="code">{render_lines(out["raw"])}</pre></div></div>')
        if out["reasoning"]:
            a('<div class="block"><div class="blkhead">'
              '<span class="blkname">reasoning_content</span>'
              f'<span class="tok">{len(out["reasoning"])} chars</span>'
              '<button class="toggle" data-toggle>collapse</button></div>'
              f'<div class="blkbody scrolly"><pre class="code">{render_lines(out["reasoning"])}</pre></div></div>')
        a("</div>")
    a("</section>")

    a('<footer class="foot">')
    a(
        "<p>Contract text, category definitions and gold annotations are from "
        "<strong>CUAD v1</strong>, created by <strong>The Atticus Project</strong> and "
        "released under <strong>CC BY 4.0</strong>. Cite: Hendrycks, Burns, Chen and Ball, "
        "<em>CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review</em>, "
        "NeurIPS 2021 Datasets and Benchmarks "
        "(<code>hendrycks2021cuad</code>, arXiv:2103.06268).</p>"
    )
    a(
        "<p>Only the <code>scratch</code> split is displayed, per "
        "<code>plans/splits.md</code> standing rule 6. Generated by "
        "<code>harness/scripts/render_prompt_inspector.py</code>; regenerate with "
        "<code>uv run --with transformers python harness/scripts/render_prompt_inspector.py</code>.</p>"
    )
    a("</footer>")

    a("<script>" + JS + "</script>")
    a("</body></html>")
    return "\n".join(parts)


def annotation_card(ann: dict[str, str]) -> str:
    return (
        '<aside class="ann">'
        f'<div class="annhead"><span class="annpill">{ann["id"]}</span>'
        f'<span class="anntitle">{ann["title"]}</span>'
        '<span class="annnote">our annotation &mdash; not sent to the model</span></div>'
        f'<div class="annbody"><p>{ann["body"]}</p></div>'
        "</aside>"
    )


CSS = """
:root{
  --bg:#12151a; --fg:#e6e9ef; --muted:#9aa4b2; --panel:#1a1f27; --panel2:#212832;
  --line:#2c3542; --accent:#7fb3ff; --amber:#f0b445; --amberbg:#2a2113;
  --green:#5fd39a; --red:#ff7b72; --code:#0e1116;
}
*{box-sizing:border-box}
html,body{max-width:100%;overflow-x:hidden}
body{margin:0;padding:0 20px 80px;background:var(--bg);color:var(--fg);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
h1{font-size:22px;margin:0 0 6px}
h2{font-size:17px;margin:0 0 8px;letter-spacing:.02em}
h3{font-size:15px;margin:22px 0 8px}
h4{font-size:13px;margin:18px 0 6px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
p{margin:0 0 10px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.9em;
  background:#232a34;padding:1px 4px;border-radius:3px;color:#d7e3f4}
.top{padding:26px 0 12px;border-bottom:1px solid var(--line);margin-bottom:18px}
.sub{color:var(--muted);font-size:13.5px;max-width:78ch}
section{margin:0 0 26px;padding:16px 18px;background:var(--panel);
  border:1px solid var(--line);border-radius:8px}
.scrollx{overflow-x:auto;max-width:100%}
.tbl{border-collapse:collapse;width:100%;font-size:13px}
.tbl th,.tbl td{border:1px solid var(--line);padding:5px 9px;text-align:left;vertical-align:top}
.tbl thead th{background:var(--panel2);color:var(--muted);font-weight:600;white-space:nowrap}
.tbl th.k{background:var(--panel2);color:var(--muted);font-weight:600;white-space:nowrap;width:1%}
.num{text-align:right;font-variant-numeric:tabular-nums;font-family:ui-monospace,Menlo,monospace}
.delta{color:var(--accent)}
.sumrow td,.sumrow th{background:#1e2530;font-weight:600}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.small{font-size:12px;color:var(--muted)}
.verify{border-left:4px solid var(--green)}
.verify.bad{border-left-color:var(--red)}
.verify h2{color:var(--green)}
.verify.bad h2{color:var(--red)}
td.pass{color:var(--green);font-weight:700}
td.fail{color:var(--red);font-weight:700}
.warn{background:var(--amberbg);border:1px solid #4a3a17;border-radius:6px;
  padding:10px 12px;font-size:13px;color:#f3ddb0}
.callout-sm{background:#152029;border:1px solid #24384a;border-radius:6px;
  padding:10px 12px;font-size:13px}
.controls{position:sticky;top:0;z-index:20;display:flex;gap:26px;flex-wrap:wrap;
  align-items:center;background:#161b22;border:1px solid var(--line)}
.ctlgroup{display:flex;align-items:center;gap:10px}
.ctllabel{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
.seg{display:flex;border:1px solid var(--line);border-radius:6px;overflow:hidden}
.segbtn{background:var(--panel2);color:var(--fg);border:0;border-right:1px solid var(--line);
  padding:6px 14px;font:inherit;font-size:13px;cursor:pointer}
.segbtn:last-child{border-right:0}
.segbtn.on{background:var(--accent);color:#0b1017;font-weight:700}
.chk{font-size:13px;color:var(--muted);cursor:pointer}
.block{border:1px solid var(--line);border-radius:7px;margin:0 0 14px;background:var(--panel2);
  overflow:hidden}
.blkhead{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 12px;
  background:#232b36;border-bottom:1px solid var(--line)}
.blkname{font-weight:700;font-size:12.5px;letter-spacing:.06em}
.role{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;padding:2px 6px;
  border-radius:3px;background:#2f3947;color:var(--muted)}
.role-system{background:#33304a;color:#c3b8ff}
.badge{font-size:11px;padding:2px 7px;border-radius:10px;border:1px solid var(--line);
  color:var(--muted)}
.badge.add2{background:#16302a;border-color:#2c5c4c;color:#7fe0b6}
.badge.add3{background:#2c1f37;border-color:#5a3c72;color:#d5aef5}
.badge.prospective{background:var(--amberbg);border-color:#4a3a17;color:var(--amber)}
.tok{margin-left:auto;font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--accent)}
.toggle{background:#2f3947;color:var(--fg);border:1px solid var(--line);border-radius:4px;
  font:inherit;font-size:11.5px;padding:2px 8px;cursor:pointer}
.blkbody{background:var(--code);overflow-x:auto}
.blkbody.scrolly{max-height:440px;overflow-y:auto;resize:vertical}
.blkbody.collapsed{display:none}
pre.code{margin:0;padding:12px 14px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12.5px;line-height:1.5;color:#dbe4f0;white-space:pre;min-width:max-content}
.ln{white-space:pre}
.ln.blank{height:1.5em;border-left:2px solid #2a3340;margin-left:-6px;padding-left:4px}
.trail{background:#4a2c2c;border-radius:2px;color:#ff9d95}
.ann{margin:0;border-left:4px solid var(--amber);background:var(--amberbg);
  border-bottom:1px solid #4a3a17}
.annhead{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 12px 4px}
.annpill{background:var(--amber);color:#1a1405;font-weight:800;font-size:11px;
  padding:2px 7px;border-radius:10px;letter-spacing:.05em}
.anntitle{font-weight:700;font-size:13px;color:#f6d99a}
.annnote{margin-left:auto;font-size:11px;color:#caa76a;font-style:italic}
.annbody{padding:0 12px 10px;font-size:13px;color:#f0e2c4;max-width:96ch}
.annlist{margin:0;padding-left:0;list-style:none}
.annlist li{padding:5px 0;font-size:13.5px;color:#f6d99a}
.deltaon .added-C2.showdelta,.deltaon .added-C3.showdelta{
  box-shadow:0 0 0 2px var(--amber),0 0 22px rgba(240,180,69,.25)}
.deltaon .added-C2.showdelta > .blkhead,.deltaon .added-C3.showdelta > .blkhead{
  background:#3a3016}
.dec td{font-size:12px}
.cellbadge{font-weight:700}
tr.cell-TP .cellbadge{color:var(--green)}
tr.cell-TN .cellbadge{color:#8fb0d8}
tr.cell-FP .cellbadge{color:var(--red)}
tr.cell-FN .cellbadge{color:var(--amber)}
tr.rowhl-a2 td,tr.rowhl-a1 td{background:#1e2129}
.foot{border-top:1px solid var(--line);padding:18px 0;color:var(--muted);font-size:12.5px}
"""

JS = """
(function(){
  var body=document.body;
  function apply(){
    var cond=body.getAttribute('data-cond');
    var pset=body.getAttribute('data-pset');
    document.querySelectorAll('[data-setcond]').forEach(function(b){
      b.classList.toggle('on', b.getAttribute('data-setcond')===cond);});
    document.querySelectorAll('[data-setpset]').forEach(function(b){
      b.classList.toggle('on', b.getAttribute('data-setpset')===pset);});
    document.querySelectorAll('.block, .outblock').forEach(function(el){
      var conds=[].filter.call(el.classList,function(c){return c.indexOf('cond-')===0;});
      var visible=true;
      if(conds.length){visible=el.classList.contains('cond-'+cond);}
      if(visible && el.classList.contains('pset-working_set')){visible=(pset==='working_set');}
      if(visible && el.classList.contains('pset-as_run')&&el.classList.contains('blk-principles')){
        visible=(pset==='as_run');}
      el.style.display=visible?'':'none';
      el.classList.toggle('showdelta',
        visible && (el.classList.contains('added-'+cond)));
    });
    document.querySelectorAll('.psetonly').forEach(function(el){
      el.style.display=(pset==='working_set')?'':'none';});
  }
  document.querySelectorAll('[data-setcond]').forEach(function(b){
    b.addEventListener('click',function(){body.setAttribute('data-cond',b.getAttribute('data-setcond'));apply();});});
  document.querySelectorAll('[data-setpset]').forEach(function(b){
    b.addEventListener('click',function(){body.setAttribute('data-pset',b.getAttribute('data-setpset'));apply();});});
  var chk=document.getElementById('deltachk');
  function delta(){document.body.classList.toggle('deltaon',chk.checked);}
  chk.addEventListener('change',delta);
  document.querySelectorAll('[data-toggle]').forEach(function(b){
    b.addEventListener('click',function(){
      var pane=b.closest('.block').querySelector('.blkbody');
      var hidden=pane.classList.toggle('collapsed');
      b.textContent=hidden?'expand':'collapse';});});
  delta();apply();
})();
"""


if __name__ == "__main__":
    main()
