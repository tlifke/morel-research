from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any, Optional

MAX_BODY_CHARS = 2600

VERDICTS: dict[str, dict[str, str]] = {}


def esc(s: Any) -> str:
    return html.escape(str(s))


def truncate(text: str, limit: int = MAX_BODY_CHARS) -> str:
    if len(text) <= limit:
        return esc(text)
    kept = esc(text[:limit])
    return (
        kept
        + f'<span class="trunc">\n\n[TRUNCATED BY THE RENDERER: {len(text) - limit} '
        f"more characters, {len(text)} total]</span>"
    )


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    z = 1.96
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def pct(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100*k/n:.0f}% ({k}/{n}) <span class='ci'>95% CI {100*lo:.0f}–{100*hi:.0f}</span>"


def rate_rows(samples: list[dict], keyfn) -> dict[str, dict[str, int]]:
    agg: dict[str, dict[str, int]] = {}
    for s in samples:
        key = keyfn(s)
        a = s.get("analysis") or {}
        c = s.get("coverage") or {}
        row = agg.setdefault(
            key,
            {
                "n": 0,
                "strict_json": 0,
                "lenient_json": 0,
                "schema_valid": 0,
                "fence": 0,
                "empty": 0,
                "prose": 0,
                "truncated": 0,
                "covered": 0,
                "schema_valid_and_covered": 0,
            },
        )
        row["n"] += 1
        row["strict_json"] += bool(a.get("strict_json"))
        row["lenient_json"] += bool(a.get("lenient_json"))
        row["schema_valid"] += bool(a.get("schema_valid"))
        row["fence"] += bool(a.get("has_fence"))
        row["empty"] += bool(a.get("empty_content"))
        row["prose"] += bool(a.get("leading_prose"))
        row["truncated"] += (s.get("response", {}).get("finish_reason") == "length")
        if c:
            row["covered"] += bool(c.get("covered"))
            if a.get("schema_valid") and c.get("covered"):
                row["schema_valid_and_covered"] += 1
    return agg


CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin:0; background:#faf9f7; color:#16150f;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size:16px; line-height:1.55; }
.wrap { max-width: 1020px; margin: 0 auto; padding: 32px 20px 96px; }
h1 { font-size: 30px; line-height:1.2; margin: 0 0 6px; }
h2 { font-size: 21px; margin: 44px 0 10px; padding-top: 14px; border-top: 1px solid #ddd9d0; }
h3 { font-size: 16px; margin: 26px 0 8px; }
.sub { color:#5f5a4e; margin: 0 0 24px; }
.verdict { background:#fff; border:2px solid #8c2f1d; border-radius:8px; padding:18px 20px; margin:20px 0 8px; }
.verdict h2 { border:0; margin:0 0 8px; padding:0; font-size:20px; color:#8c2f1d; }
.vline { display:flex; gap:10px; align-items:baseline; padding:7px 0; border-top:1px solid #eee9df; flex-wrap:wrap; }
.vline:first-of-type { border-top:0; }
.model { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:13px; font-weight:600; min-width:250px; }
.tag { display:inline-block; padding:1px 8px; border-radius:10px; font-size:12px; font-weight:700;
  letter-spacing:.02em; white-space:nowrap; }
.tag.bad { background:#f7dcd6; color:#7d2717; }
.tag.ok { background:#d9ecd9; color:#1e5a24; }
.tag.mid { background:#f6ecd2; color:#6d5310; }
table { border-collapse: collapse; width:100%; font-size:14px; background:#fff; }
th, td { border:1px solid #ddd9d0; padding:6px 9px; text-align:left; vertical-align:top; }
th { background:#f0ede6; font-weight:600; }
td.num { text-align:right; font-variant-numeric: tabular-nums; white-space:nowrap; }
.ci { color:#6d685c; font-size:11px; }
.scroll { overflow-x:auto; -webkit-overflow-scrolling:touch; margin: 10px 0 6px; border-radius:4px; }
pre { background:#1e1d1a; color:#e8e5dc; padding:12px 14px; border-radius:6px; overflow-x:auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px; line-height:1.45;
  white-space:pre; margin:6px 0; }
pre.light { background:#fff; color:#16150f; border:1px solid #ddd9d0; white-space:pre-wrap; word-break:break-word; }
.trunc { color:#d98a3a; font-weight:700; }
.pair { display:grid; grid-template-columns: 1fr; gap:8px; margin: 12px 0 22px; }
.lab { font-size:12px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:#6d685c; margin-bottom:2px; }
.note { background:#fff; border-left:4px solid #b9b3a4; padding:10px 14px; margin:14px 0; }
.note.warn { border-left-color:#8c2f1d; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:13px;
  background:#efece4; padding:1px 4px; border-radius:3px; }
ul { padding-left: 22px; }
li { margin: 5px 0; }
details { background:#fff; border:1px solid #ddd9d0; border-radius:6px; padding:8px 12px; margin:10px 0; }
summary { cursor:pointer; font-weight:600; font-size:14px; }
.meta { font-size:13px; color:#5f5a4e; }
"""


def payload_block(title: str, payload: Any, resp_text: str, extra: str = "") -> str:
    req = json.dumps(payload, indent=2)
    return f"""
<div class="pair">
  <div><div class="lab">{esc(title)} — request body (POST /chat/completions)</div>
  <pre>{truncate(req, 1800)}</pre></div>
  <div><div class="lab">response — message.content, verbatim</div>
  <pre class="light">{truncate(resp_text)}</pre>{extra}</div>
</div>"""


def build(phase1: dict, phase2: dict, phase3: dict, verdicts: list[dict]) -> str:
    parts: list[str] = []
    parts.append(
        f"""<title>Tinker Structured Output Evidence</title>
<style>{CSS}</style>
<div class="wrap">
<h1>Is structured output actually enforced on the Tinker OAI endpoint?</h1>
<p class="sub">Study 008 &middot; evidence page &middot; endpoint <code>{esc(phase1['meta']['base_url'])}</code>
&middot; probed {esc(phase1['meta']['timestamp'])}</p>
"""
    )

    parts.append('<div class="verdict"><h2>Verdict</h2>')
    for v in verdicts:
        parts.append(
            f'<div class="vline"><span class="model">{esc(v["model"])}</span>'
            f'<span class="tag {v["cls"]}">{esc(v["tag"])}</span>'
            f'<span>{v["text"]}</span></div>'
        )
    parts.append("</div>")
    parts.append(
        """<div class="note warn"><b>The framing question, answered directly.</b>
This is <i>not</i> a misconfiguration of <code>response_format</code>. Fourteen
distinct request shapes — every OpenAI and vLLM structured-output knob we could
name — were sent to the endpoint. All fourteen returned HTTP&nbsp;200, including
two deliberately invalid controls that any server parsing <code>response_format</code>
would have rejected with a 400. The endpoint validates <code>model</code> (400 on a bad
one) and honours <code>temperature</code>, so requests <i>are</i> parsed — the
structured-output parameters specifically are dropped before they reach anything
that could act on them. There is no knob here we failed to turn.
<br><br>The one real exception is function calling, which is not a decode constraint
but does change the output channel on one model. It is measured below and reported
separately.</div>"""
    )

    parts.append("<h2>Part 1 &mdash; what the endpoint accepts</h2>")
    parts.append(
        """<p>Each row is one live request with a small 4-field schema (one enum, one array)
and a prompt that explicitly asks for prose plus a markdown code fence. A working
constrained decode cannot emit a fence, so <b>fence = yes</b> is a direct falsification
of enforcement. <code>strict JSON</code> means <code>json.loads</code> succeeds on the whole
response with no repair; <code>schema-valid</code> is checked after lenient brace-extraction,
i.e. it is the generous reading.</p>"""
    )

    parts.append('<div class="scroll"><table><tr><th>variant</th><th>what was sent</th>'
                 "<th>HTTP</th><th>fence</th><th>strict JSON</th><th>schema-valid<br>(after repair)</th></tr>")
    seen: set[str] = set()
    by_variant: dict[str, list[dict]] = {}
    for t in phase1["trials"]:
        by_variant.setdefault(t["variant"], []).append(t)
    order = [t["variant"] for t in phase1["trials"] if not (t["variant"] in seen or seen.add(t["variant"]))]
    for var in order:
        ts = by_variant[var]
        desc = ts[0]["description"]
        status = "/".join(sorted({str(t["response"]["http_status"]) for t in ts}))
        def frac(key: str) -> str:
            vals = [bool((t.get("analysis") or {}).get(key)) for t in ts if t.get("analysis")]
            return f"{sum(vals)}/{len(vals)}" if vals else "n/a"
        parts.append(
            f"<tr><td><code>{esc(var)}</code></td><td>{esc(desc)}</td>"
            f'<td class="num">{esc(status)}</td>'
            f'<td class="num">{frac("has_fence")}</td>'
            f'<td class="num">{frac("strict_json")}</td>'
            f'<td class="num">{frac("schema_valid")}</td></tr>'
        )
    parts.append("</table></div>")
    parts.append(
        "<p class='meta'>Fractions are over the three models "
        f"({esc(', '.join(phase1['meta']['models']))}), one sample each.</p>"
    )

    parts.append("<h3>Raw payloads &mdash; the two controls that settle it</h3>")
    for var in ("bogus_response_format_type", "json_schema_missing_body", "bogus_param"):
        for t in phase1["trials"]:
            if t["variant"] == var and t["model"] == "Qwen/Qwen3.5-9B":
                parts.append(payload_block(f"{var} ({t['model']})", t["request"], t["response"].get("content", "")))
    parts.append(
        """<div class="note">A server that parsed <code>response_format</code> would reject
<code>{"type": "not_a_real_format"}</code> and <code>{"type": "json_schema"}</code> with no
<code>json_schema</code> body. Both are accepted with 200 and a normal completion. Combined
with a 400 on an unknown <code>model</code>, the request is definitely being parsed —
<code>response_format</code> is simply not part of what it parses.</div>"""
    )

    parts.append("<h3>Raw payloads &mdash; the mechanisms we actually wanted to work</h3>")
    for var in ("json_schema_strict", "guided_json", "structured_outputs", "json_object"):
        for t in phase1["trials"]:
            if t["variant"] == var and t["model"] == "Qwen/Qwen3.5-4B":
                parts.append(payload_block(f"{var} ({t['model']})", t["request"], t["response"].get("content", "")))

    parts.append("<h3>Endpoint introspection</h3>")
    for path, r in phase1["introspection"].items():
        body = r.get("body") or r.get("error_body") or r.get("transport_error") or ""
        parts.append(
            f'<div class="lab">GET {esc(path)} &rarr; HTTP {esc(r.get("http_status"))}</div>'
            f"<pre>{truncate(str(body), 900)}</pre>"
        )
    parts.append(
        """<p>No <code>/openapi.json</code>, <code>/docs</code>, or <code>/responses</code>.
<code>/models</code> lists only the caller's own fine-tuned sampler weights, not the base
models — so the base model ids we use are not discoverable from the endpoint and there is no
served capability document to consult. The 400 text on an unknown model
(<code>"Sampling is not supported for X."</code>) is not vLLM's wording; this is a bespoke
shim in front of the sampler, which is the most likely reason vLLM's
<code>guided_json</code> does nothing.</p>"""
    )

    parts.append("<h2>Part 2 &mdash; does anything constrain, or merely nudge?</h2>")
    parts.append(
        f"""<p>Every mechanism that could plausibly constrain, run {phase2['meta']['n']} times per
model at <b>temperature 1.0</b> against the fence-inviting prompt. A real constrained decode
would show 0% fences and 100% strict JSON. Anything less is the model complying voluntarily.</p>"""
    )
    agg2 = rate_rows(phase2["samples"], lambda s: f"{s['model']}||{s['variant']}")
    parts.append('<div class="scroll"><table><tr><th>model</th><th>mechanism</th><th>n</th>'
                 "<th>fence emitted</th><th>strict JSON</th><th>schema-valid (lenient)</th></tr>")
    for key in sorted(agg2):
        model, var = key.split("||")
        r = agg2[key]
        parts.append(
            f'<tr><td><code>{esc(model)}</code></td><td><code>{esc(var)}</code></td>'
            f'<td class="num">{r["n"]}</td><td class="num">{pct(r["fence"], r["n"])}</td>'
            f'<td class="num">{pct(r["strict_json"], r["n"])}</td>'
            f'<td class="num">{pct(r["schema_valid"], r["n"])}</td></tr>'
        )
    parts.append("</table></div>")

    parts.append("<h3>A fence, emitted under every mechanism</h3>")
    shown = 0
    for s in phase2["samples"]:
        if shown >= 3:
            break
        if (s.get("analysis") or {}).get("has_fence"):
            parts.append(
                f'<div class="lab">{esc(s["model"])} &middot; <code>{esc(s["variant"])}</code> '
                f'&middot; temp 1.0 &middot; sample {s["i"]}</div>'
                f'<pre class="light">{truncate(s.get("analyzed_text") or s["response"].get("content", ""), 1200)}</pre>'
            )
            shown += 1

    parts.append("<h2>Part 3 &mdash; measured rates on the study's real output schema</h2>")
    m3 = phase3["meta"]
    parts.append(
        f"""<p>CUAD-shaped output ({len(phase3.get('schema', {}).get('properties', {}).get('extractions', {}).get('items', {}).get('properties', {}).get('category', {}).get('enum', [])) or 12}
categories, <code>extractions</code> + <code>absent</code>, each carrying
<code>principles_cited</code>), at the study's actual sampling settings:
temperature {esc(m3['temperature'])}, <code>max_tokens</code> {esc(m3['max_tokens'])},
n={esc(m3['n'])} per cell. The prompt here does <i>not</i> invite prose — it says
&ldquo;Return only the JSON object&rdquo; — so these are the study's real-world rates,
not adversarial ones.</p>"""
    )
    agg3 = rate_rows(phase3["samples"], lambda s: f"{s['model']}||{s['variant']}")
    parts.append('<div class="scroll"><table><tr><th>model</th><th>mechanism</th><th>n</th>'
                 "<th>valid JSON<br>(no repair)</th><th>valid JSON<br>(after brace repair)</th>"
                 "<th>schema-valid</th><th>coverage-valid</th><th>schema &amp; coverage</th></tr>")
    for key in sorted(agg3):
        model, var = key.split("||")
        r = agg3[key]
        parts.append(
            f'<tr><td><code>{esc(model)}</code></td><td><code>{esc(var)}</code></td>'
            f'<td class="num">{r["n"]}</td>'
            f'<td class="num">{pct(r["strict_json"], r["n"])}</td>'
            f'<td class="num">{pct(r["lenient_json"], r["n"])}</td>'
            f'<td class="num">{pct(r["schema_valid"], r["n"])}</td>'
            f'<td class="num">{pct(r["covered"], r["n"])}</td>'
            f'<td class="num">{pct(r["schema_valid_and_covered"], r["n"])}</td></tr>'
        )
    parts.append("</table></div>")

    parts.append("<h3>Failure modes, counted</h3>")
    parts.append('<div class="scroll"><table><tr><th>model</th><th>mechanism</th><th>n</th>'
                 "<th>markdown fence</th><th>prose before JSON</th><th>empty content</th>"
                 "<th>finish_reason=length</th></tr>")
    for key in sorted(agg3):
        model, var = key.split("||")
        r = agg3[key]
        parts.append(
            f'<tr><td><code>{esc(model)}</code></td><td><code>{esc(var)}</code></td>'
            f'<td class="num">{r["n"]}</td><td class="num">{r["fence"]}</td>'
            f'<td class="num">{r["prose"]}</td><td class="num">{r["empty"]}</td>'
            f'<td class="num">{r["truncated"]}</td></tr>'
        )
    parts.append("</table></div>")

    parts.append("<h3>Verbatim failures</h3>")
    shown_keys: set[str] = set()
    for s in phase3["samples"]:
        a = s.get("analysis") or {}
        c = s.get("coverage") or {}
        mode = None
        if a.get("empty_content"):
            mode = "empty content"
        elif a.get("has_fence"):
            mode = "markdown fence"
        elif not a.get("strict_json"):
            mode = "not strict JSON"
        elif not a.get("schema_valid"):
            mode = f"schema invalid: {a.get('schema_detail')}"
        elif not c.get("covered"):
            mode = (
                f"coverage violation: missing={c.get('missing')} "
                f"duplicated={c.get('duplicated')} unknown={c.get('unknown')}"
            )
        if mode is None:
            continue
        key = f"{s['model']}|{s['variant']}|{mode.split(':')[0]}"
        if key in shown_keys:
            continue
        shown_keys.add(key)
        r = s["response"]
        parts.append(
            f'<div class="lab">{esc(s["model"])} &middot; <code>{esc(s["variant"])}</code> '
            f'&middot; sample {s["i"]} &middot; finish_reason={esc(r.get("finish_reason"))} '
            f'&middot; completion_tokens={esc((r.get("usage") or {}).get("completion_tokens"))} '
            f'&middot; <b>{esc(mode)}</b></div>'
            f'<pre class="light">{truncate(s.get("analyzed_text") or r.get("content") or "[EMPTY]", 1400)}</pre>'
        )
    parts.append("</div>")
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase1", type=Path, required=True)
    ap.add_argument("--phase2", type=Path, required=True)
    ap.add_argument("--phase3", type=Path, required=True)
    ap.add_argument("--verdicts", type=Path, required=True)
    ap.add_argument("--coverage-note", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    body = build(
        json.loads(args.phase1.read_text()),
        json.loads(args.phase2.read_text()),
        json.loads(args.phase3.read_text()),
        json.loads(args.verdicts.read_text()),
    )
    body = body.rsplit("</div>", 1)[0] + args.coverage_note.read_text() + "</div>"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(body)
    print(f"wrote {args.out} ({len(body)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
