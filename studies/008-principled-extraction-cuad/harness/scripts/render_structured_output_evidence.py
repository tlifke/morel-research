from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
from typing import Any

MAX_BODY_CHARS = 2400


def esc(s: Any) -> str:
    return html.escape(str(s))


def truncate(text: str, limit: int = MAX_BODY_CHARS) -> str:
    if len(text) <= limit:
        return esc(text)
    return (
        esc(text[:limit])
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
    return (
        f"{100*k/n:.0f}% <span class='ci'>{k}/{n}, CI {100*lo:.0f}–{100*hi:.0f}</span>"
    )


def rate_rows(samples: list[dict]) -> dict[tuple[str, str], dict[str, int]]:
    agg: dict[tuple[str, str], dict[str, int]] = {}
    for s in samples:
        a = s.get("analysis") or {}
        c = s.get("coverage") or {}
        key = (s["model"], s["variant"])
        row = agg.setdefault(
            key,
            {k: 0 for k in (
                "n", "strict_json", "lenient_json", "schema_valid", "fence", "empty",
                "prose", "truncated", "covered", "sv_cov", "toolcall",
            )},
        )
        row["n"] += 1
        row["strict_json"] += bool(a.get("strict_json"))
        row["lenient_json"] += bool(a.get("lenient_json"))
        row["schema_valid"] += bool(a.get("schema_valid"))
        row["fence"] += bool(a.get("has_fence"))
        row["empty"] += bool(a.get("empty_content"))
        row["prose"] += bool(a.get("leading_prose"))
        row["truncated"] += s.get("response", {}).get("finish_reason") == "length"
        row["toolcall"] += bool(s.get("response", {}).get("tool_calls"))
        row["covered"] += bool(c.get("covered"))
        row["sv_cov"] += bool(a.get("schema_valid") and c.get("covered"))
    return agg


CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin:0; background:#faf9f7; color:#16150f;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  font-size:16px; line-height:1.55; }
.wrap { max-width:1040px; margin:0 auto; padding:32px 20px 100px; }
h1 { font-size:29px; line-height:1.2; margin:0 0 6px; }
h2 { font-size:21px; margin:46px 0 10px; padding-top:14px; border-top:1px solid #ddd9d0; }
h3 { font-size:16px; margin:26px 0 8px; }
.sub { color:#5f5a4e; margin:0 0 22px; font-size:14px; }
.verdict { background:#fff; border:2px solid #8c2f1d; border-radius:8px; padding:18px 20px; margin:18px 0 10px; }
.verdict h2 { border:0; margin:0 0 10px; padding:0; font-size:20px; color:#8c2f1d; }
.vline { padding:9px 0; border-top:1px solid #eee9df; }
.vline:first-of-type { border-top:0; }
.model { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px; font-weight:700; }
.tag { display:inline-block; padding:1px 8px; border-radius:10px; font-size:12px; font-weight:700; white-space:nowrap; margin-left:8px; }
.tag.bad { background:#f7dcd6; color:#7d2717; }
.tag.ok { background:#d9ecd9; color:#1e5a24; }
.tag.mid { background:#f6ecd2; color:#6a5010; }
table { border-collapse:collapse; width:100%; font-size:13.5px; background:#fff; }
th,td { border:1px solid #ddd9d0; padding:6px 9px; text-align:left; vertical-align:top; }
th { background:#f0ede6; font-weight:600; }
td.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.ci { color:#6d685c; font-size:11px; }
.scroll { overflow-x:auto; -webkit-overflow-scrolling:touch; margin:10px 0 6px; }
pre { background:#1e1d1a; color:#e8e5dc; padding:12px 14px; border-radius:6px; overflow-x:auto;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; line-height:1.45;
  white-space:pre; margin:6px 0; }
pre.light { background:#fff; color:#16150f; border:1px solid #ddd9d0; white-space:pre-wrap; word-break:break-word; }
.trunc { color:#c4761f; font-weight:700; }
.pair { display:grid; grid-template-columns:1fr; gap:8px; margin:12px 0 22px; }
.lab { font-size:11.5px; font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:#6d685c; margin-bottom:2px; }
.note { background:#fff; border-left:4px solid #b9b3a4; padding:11px 15px; margin:14px 0; }
.note.warn { border-left-color:#8c2f1d; }
.note.good { border-left-color:#2f6b34; }
code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px;
  background:#efece4; padding:1px 4px; border-radius:3px; }
pre code { background:none; padding:0; }
ul { padding-left:22px; } li { margin:5px 0; }
.meta { font-size:13px; color:#5f5a4e; }
"""


def payload_block(title: str, request: Any, response_text: str) -> str:
    return f"""
<div class="pair">
  <div><div class="lab">{esc(title)} &mdash; request body</div>
  <pre>{truncate(json.dumps(request, indent=2), 1500)}</pre></div>
  <div><div class="lab">response &mdash; message.content, verbatim</div>
  <pre class="light">{truncate(response_text)}</pre></div>
</div>"""


def build(p1: dict, p2: dict, p3: dict, p4: dict, verdicts: list[dict], coverage: str) -> str:
    out: list[str] = []
    a = out.append
    a(f"<title>Tinker Structured Output Evidence</title><style>{CSS}</style><div class='wrap'>")
    a("<h1>Is structured output actually enforced on the Tinker OAI endpoint?</h1>")
    a(
        f"<p class='sub'>Study 008 &middot; endpoint <code>{esc(p1['meta']['base_url'])}</code>"
        f" &middot; all payloads below are live responses captured {esc(p1['meta']['timestamp'])}"
        f" &middot; reproduce with <code>harness/scripts/probe_structured_output.py</code></p>"
    )

    a("<div class='verdict'><h2>Verdict</h2>")
    for v in verdicts:
        a(
            f"<div class='vline'><span class='model'>{esc(v['model'])}</span>"
            f"<span class='tag {v['cls']}'>{esc(v['tag'])}</span><br>{v['text']}</div>"
        )
    a("</div>")

    a(
        """<div class="note warn"><b>Answering the framing question directly: this is NOT a
misconfiguration.</b> Fourteen distinct request shapes &mdash; every OpenAI and vLLM
structured-output knob we could name &mdash; were sent live to the endpoint. All fourteen
returned HTTP&nbsp;200, <i>including two deliberately invalid controls that any server parsing
<code>response_format</code> would have rejected with a 400</i>. The endpoint does validate
<code>model</code> (400 on an unknown one) and does honour <code>temperature</code>, so requests
are genuinely parsed &mdash; the structured-output parameters specifically are dropped before
reaching anything that could act on them. Three independent lines of evidence agree, below:
live probes, the published docs, and Thinking Machines' own cookbook proxy, which rejects
<code>response_format</code> with a clean 400 rather than pretending to honour it.</div>"""
    )
    a(
        """<div class="note good"><b>And the finding that changes the stakes.</b> &ldquo;Not
enforced&rdquo; turned out <i>not</i> to mean &ldquo;models cannot conform.&rdquo; Under the
study's real prompt &mdash; which embeds the JSON Schema verbatim &mdash; all three models
produced strictly parseable JSON on 20/20 samples and schema-valid, coverage-valid output on
19&ndash;20/20. The catastrophic-looking rates in the earlier assessment came from prompts that
either omitted the schema or actively invited prose. Both effects are shown separately below so
you can see which is which. <b>Read the limitation in Part&nbsp;3 before quoting these rates:</b>
they are measured on one short synthetic contract, not on real CUAD documents.</div>"""
    )

    a("<h2>Part 1 &mdash; what the endpoint accepts</h2>")
    a(
        """<p>Each row is one live request carrying a small 4-field schema (one enum, one array)
and a prompt that <i>explicitly asks</i> for prose plus a markdown code fence. A working
constrained decode cannot emit a fence, so <b>fence = yes</b> directly falsifies enforcement.
&ldquo;strict JSON&rdquo; means <code>json.loads</code> succeeds on the entire response with no
repair. &ldquo;schema-valid&rdquo; is checked <i>after</i> lenient brace extraction, i.e. it is
the generous reading and says nothing about enforcement.</p>"""
    )
    by_variant: dict[str, list[dict]] = {}
    order: list[str] = []
    for t in p1["trials"]:
        if t["variant"] not in by_variant:
            order.append(t["variant"])
        by_variant.setdefault(t["variant"], []).append(t)
    a("<div class='scroll'><table><tr><th>variant</th><th>what was sent</th><th>HTTP</th>"
      "<th>fence emitted</th><th>strict JSON</th><th>schema-valid<br>(after repair)</th></tr>")
    for var in order:
        ts = by_variant[var]
        status = "/".join(sorted({str(t["response"]["http_status"]) for t in ts}))

        def frac(key: str, ts=ts) -> str:
            vals = [bool((t.get("analysis") or {}).get(key)) for t in ts if t.get("analysis")]
            return f"{sum(vals)}/{len(vals)}" if vals else "n/a"

        a(
            f"<tr><td><code>{esc(var)}</code></td><td>{esc(ts[0]['description'])}</td>"
            f"<td class='num'>{esc(status)}</td><td class='num'>{frac('has_fence')}</td>"
            f"<td class='num'>{frac('strict_json')}</td><td class='num'>{frac('schema_valid')}</td></tr>"
        )
    a("</table></div>")
    a(
        f"<p class='meta'>Fractions are over the three models "
        f"({esc(', '.join(p1['meta']['models']))}), one sample each. "
        f"<code>tools_*</code> rows are analysed on the tool-call arguments when a tool call was "
        f"emitted, otherwise on <code>content</code>.</p>"
    )

    a("<h3>The two controls that settle it</h3>")
    for var in ("bogus_response_format_type", "json_schema_missing_body"):
        for t in p1["trials"]:
            if t["variant"] == var and t["model"] == "Qwen/Qwen3.5-9B":
                a(payload_block(f"{var} — {t['model']}", t["request"], t["response"].get("content", "")))
    a(
        """<div class="note">A server that parsed <code>response_format</code> would reject
<code>{"type": "not_a_real_format"}</code> and would reject <code>{"type": "json_schema"}</code>
sent with no <code>json_schema</code> body. Both are accepted with HTTP 200 and a normal
completion. Since an unknown <code>model</code> <i>does</i> produce a 400
(<code>{"detail":"Sampling is not supported for not/a-real-model."}</code>), the request body is
being parsed; <code>response_format</code> is simply not part of what it parses.</div>"""
    )

    a("<h3>The mechanisms we wanted to work</h3>")
    for var in ("json_schema_strict", "guided_json", "structured_outputs", "json_object"):
        for t in p1["trials"]:
            if t["variant"] == var and t["model"] == "Qwen/Qwen3.5-4B":
                a(payload_block(f"{var} — {t['model']}", t["request"], t["response"].get("content", "")))

    a("<h3>Endpoint introspection</h3>")
    for path, r in p1["introspection"].items():
        body = r.get("body") or r.get("error_body") or r.get("transport_error") or ""
        a(
            f"<div class='lab'>GET {esc(path)} &rarr; HTTP {esc(r.get('http_status'))}</div>"
            f"<pre>{truncate(str(body), 800)}</pre>"
        )
    a(
        """<p>No <code>/openapi.json</code>, no <code>/docs</code>, no <code>/responses</code>.
<code>/models</code> lists only the caller's own fine-tuned sampler weights, not the base models
&mdash; so the base model ids the study uses are not discoverable from the endpoint, and there is
no served capability document to consult. The 400 wording on an unknown model is not vLLM's; this
is a bespoke shim in front of Tinker's sampler, which is the most likely reason vLLM's
<code>guided_json</code> does nothing.</p>"""
    )

    a("<h3>What the documentation says</h3>")
    a(
        """<p>Independently checked against the published docs and source (fetched
2026-08-15). Relay these as claims to spot-check, not as things I ran:</p>
<ul>
<li><a href="https://tinker-docs.thinkingmachines.ai/tinker/compatible-apis/openai/">The
OpenAI-compatibility page</a> documents only <code>model</code>, <code>messages</code>,
<code>prompt</code>, <code>max_tokens</code>, <code>temperature</code>, <code>top_p</code>,
<code>separate_reasoning</code> and <code>reasoning_effort</code>. It never mentions
<code>response_format</code>, <code>json_schema</code>, <code>json_object</code>,
<code>guided_json</code>, <code>logit_bias</code>, or any grammar feature &mdash; and it never
states how unknown parameters are handled. Our probe answers that omission: silently ignored.</li>
<li>The native SDK's <code>SamplingParams</code> has exactly six fields:
<code>max_tokens, seed, stop, temperature, top_k, top_p</code>. There is no structured-output,
grammar, guided-decoding, logit-bias, or logit-processor surface anywhere in the SDK. So the
capability does not exist one layer down either &mdash; the shim is not hiding it.</li>
<li>Thinking Machines' own cookbook ships a self-hosted OpenAI-compatible proxy whose
<code>_UNSUPPORTED_OPENAI_KEYS</code> includes <code>response_format</code>, with a test asserting
it returns HTTP 400, and a README line: &ldquo;Anything else that changes semantics is rejected
with a clean 400 rather than silently ignored.&rdquo; Their own stack has nothing to implement
<code>response_format</code> with. The hosted shim differs only in being less honest about it.</li>
<li><code>separate_reasoning</code> defaults to <code>true</code> (changed from <code>false</code>
in June 2026), which is why <code>reasoning_content</code> arrives split out of
<code>content</code> without us asking. Worth setting explicitly in the backend so a future
default flip cannot silently move reasoning text back into <code>content</code>.</li>
<li>No recipe in the cookbook does enforced structured output. Their mechanism is: render the
schema into the prompt, sample free text, parse afterwards, and report a
<code>MALFORMED</code> termination on failure. That is exactly what this harness already does.</li>
</ul>"""
    )

    a("<h2>Part 1b &mdash; function calling, the one surface that is not nothing</h2>")
    a(
        """<p>Tinker also serves an Anthropic-compatible endpoint at
<code>/anthropic/api/v1/messages</code> (undocumented on the OAI page; found by probing) which
accepts <code>tools</code> with an <code>input_schema</code> and a <code>tool_choice</code>. This
is the closest thing to a schema-shaped surface Tinker offers, so it was tested rather than
assumed. <b>It is not enforcement either:</b> <code>tool_choice</code> forcing is not honoured
&mdash; both Qwen models simply ignore the tools and answer in prose &mdash; and the one model
that does emit tool calls emits them only some of the time.</p>"""
    )
    a("<div class='scroll'><table><tr><th>model</th><th>tool_choice</th><th>n</th>"
      "<th>emitted a tool_use block</th><th>tool input schema-valid</th><th>stop_reason values</th></tr>")
    agg4: dict[tuple[str, str], dict[str, Any]] = {}
    for t in p4["trials"]:
        r = agg4.setdefault((t["model"], t["variant"]), {"n": 0, "tu": 0, "ok": 0, "stops": set()})
        r["n"] += 1
        r["tu"] += bool(t["emitted_tool_use"])
        r["ok"] += bool(t["tool_input_valid"])
        r["stops"].add(str(t["stop_reason"]))
    for key in sorted(agg4):
        r = agg4[key]
        a(
            f"<tr><td><code>{esc(key[0])}</code></td><td><code>{esc(key[1])}</code></td>"
            f"<td class='num'>{r['n']}</td><td class='num'>{r['tu']}/{r['n']}</td>"
            f"<td class='num'>{r['ok']}/{r['n']}</td><td>{esc(', '.join(sorted(r['stops'])))}</td></tr>"
        )
    a("</table></div>")
    for t in p4["trials"]:
        if t["model"] == "Qwen/Qwen3.5-9B" and t["variant"] == "forced_named_tool" and t["i"] == 0:
            a(payload_block(
                "Anthropic endpoint, tool_choice pinned to a named tool — Qwen/Qwen3.5-9B",
                t["request"],
                f"stop_reason={t['stop_reason']}  blocks={t['block_types']}\n"
                f"emitted_tool_use={t['emitted_tool_use']}\n\n{t['text']}",
            ))
    a(
        """<div class="note">A forced named tool that the model is free to decline is a request,
not a constraint. Part&nbsp;3 measures what using it costs: on this task it is <b>strictly worse
than plain prompting on all three models</b>, because the tool framing pulls the Qwen models into
conversational prose. Do not adopt it.</div>"""
    )

    a("<h2>Part 2 &mdash; does anything constrain, or merely nudge?</h2>")
    a(
        f"""<p>Every mechanism that could plausibly constrain, run {p2['meta']['n']} times per
model at <b>temperature 1.0</b> against the fence-inviting prompt. A real constrained decode shows
0% fences and 100% strict JSON. The <code>none</code> row is the control: <b>every mechanism
matches the control exactly</b>, which is the cleanest possible statement that the parameter does
nothing.</p>"""
    )
    agg2 = rate_rows(p2["samples"])
    a("<div class='scroll'><table><tr><th>model</th><th>mechanism</th><th>n</th>"
      "<th>fence emitted</th><th>strict JSON</th><th>schema-valid (lenient)</th></tr>")
    for key in sorted(agg2):
        r = agg2[key]
        a(
            f"<tr><td><code>{esc(key[0])}</code></td><td><code>{esc(key[1])}</code></td>"
            f"<td class='num'>{r['n']}</td><td class='num'>{pct(r['fence'], r['n'])}</td>"
            f"<td class='num'>{pct(r['strict_json'], r['n'])}</td>"
            f"<td class='num'>{pct(r['schema_valid'], r['n'])}</td></tr>"
        )
    a("</table></div>")
    a("<h3>A fence, emitted while <code>response_format</code> asked for JSON</h3>")
    shown = 0
    for s in p2["samples"]:
        if shown >= 2:
            break
        if (s.get("analysis") or {}).get("has_fence") and s["variant"] in ("json_object", "json_schema_strict"):
            a(
                f"<div class='lab'>{esc(s['model'])} &middot; <code>{esc(s['variant'])}</code> "
                f"&middot; temperature 1.0 &middot; sample {s['i']}</div>"
                f"<pre class='light'>{truncate(s.get('analyzed_text') or s['response'].get('content', ''), 1100)}</pre>"
            )
            shown += 1

    a("<h2>Part 3 &mdash; measured rates at the study's real settings</h2>")
    m3 = p3["meta"]
    a(
        f"""<p>CUAD-shaped output (12 categories, <code>extractions</code> + <code>absent</code>,
each decision carrying <code>principles_cited</code>) at the study's actual sampling settings:
<b>temperature {esc(m3['temperature'])}</b>, <code>max_tokens</code> {esc(m3['max_tokens'])},
<b>n={esc(m3['n'])}</b> per cell. Critically, the prompt here <b>mirrors
<code>harness/prompts.py</code></b> &mdash; same system block, same
&ldquo;OUTPUT FORMAT / must validate against this JSON Schema&rdquo; header with the schema
serialised into the prompt, same document block. That is what makes these the study's rates
rather than a probe's.</p>"""
    )
    agg3 = rate_rows(p3["samples"])
    a("<div class='scroll'><table><tr><th>model</th><th>mechanism</th><th>n</th>"
      "<th>valid JSON<br>(no repair)</th><th>valid JSON<br>(brace repair)</th>"
      "<th>schema-valid</th><th>coverage-valid</th><th>schema &amp; coverage</th></tr>")
    for key in sorted(agg3):
        r = agg3[key]
        a(
            f"<tr><td><code>{esc(key[0])}</code></td><td><code>{esc(key[1])}</code></td>"
            f"<td class='num'>{r['n']}</td><td class='num'>{pct(r['strict_json'], r['n'])}</td>"
            f"<td class='num'>{pct(r['lenient_json'], r['n'])}</td>"
            f"<td class='num'>{pct(r['schema_valid'], r['n'])}</td>"
            f"<td class='num'>{pct(r['covered'], r['n'])}</td>"
            f"<td class='num'>{pct(r['sv_cov'], r['n'])}</td></tr>"
        )
    a("</table></div>")
    a(
        """<div class="note warn"><b>Limitations you must read before quoting these numbers.</b>
<ul>
<li>One document. It is a short synthetic distribution agreement (~350 words), not a real CUAD
contract. Real instances run 8k&ndash;82k tokens. Conformance under length is
<b>not measured here</b> and is exactly where these models are most likely to degrade &mdash;
truncation, dropped categories, and reasoning overflow all scale with input length.</li>
<li>One prompt, one condition. No principle block (C2/C3) is present, so the longer, more
demanding prompts are untested.</li>
<li>n=20 per cell. A 20/20 result has a 95% CI of roughly 84&ndash;100%; it cannot distinguish a
truly perfect model from one that fails 1 time in 25.</li>
<li><code>json_object</code> and <code>none</code> produce statistically identical rows. That is
the point of including <code>none</code> &mdash; it is the third independent confirmation that
<code>response_format</code> is inert, this time under the realistic prompt.</li>
</ul></div>"""
    )
    a("<h3>Failure modes, counted</h3>")
    a("<div class='scroll'><table><tr><th>model</th><th>mechanism</th><th>n</th><th>markdown fence</th>"
      "<th>prose before JSON</th><th>empty content</th><th>finish_reason=length</th>"
      "<th>emitted tool call</th></tr>")
    for key in sorted(agg3):
        r = agg3[key]
        a(
            f"<tr><td><code>{esc(key[0])}</code></td><td><code>{esc(key[1])}</code></td>"
            f"<td class='num'>{r['n']}</td><td class='num'>{r['fence']}</td>"
            f"<td class='num'>{r['prose']}</td><td class='num'>{r['empty']}</td>"
            f"<td class='num'>{r['truncated']}</td><td class='num'>{r['toolcall']}</td></tr>"
        )
    a("</table></div>")

    a("<h3>Verbatim samples &mdash; one clean pass and every distinct failure</h3>")
    for s in p3["samples"]:
        if s["variant"] == "json_object" and (s.get("analysis") or {}).get("schema_valid") and (s.get("coverage") or {}).get("covered"):
            a(
                f"<div class='lab'>PASS &middot; {esc(s['model'])} &middot; "
                f"<code>{esc(s['variant'])}</code> &middot; sample {s['i']}</div>"
                f"<pre class='light'>{truncate(s.get('analyzed_text') or '', 1600)}</pre>"
            )
            break
    seen_modes: set[str] = set()
    for s in p3["samples"]:
        an = s.get("analysis") or {}
        cv = s.get("coverage") or {}
        if an.get("empty_content"):
            mode = "empty content"
        elif an.get("has_fence"):
            mode = "markdown fence"
        elif not an.get("strict_json"):
            mode = "not strict JSON without repair"
        elif not an.get("schema_valid"):
            mode = f"schema invalid — {an.get('schema_detail')}"
        elif not cv.get("covered"):
            mode = (
                f"coverage violation — missing={cv.get('missing')} "
                f"duplicated={cv.get('duplicated')} unknown={cv.get('unknown')}"
            )
        else:
            continue
        key = f"{s['model']}|{s['variant']}|{mode.split(' — ')[0]}"
        if key in seen_modes:
            continue
        seen_modes.add(key)
        r = s["response"]
        a(
            f"<div class='lab'>FAIL &middot; {esc(s['model'])} &middot; <code>{esc(s['variant'])}</code>"
            f" &middot; sample {s['i']} &middot; finish_reason={esc(r.get('finish_reason'))}"
            f" &middot; completion_tokens={esc((r.get('usage') or {}).get('completion_tokens'))}"
            f" &middot; <b>{esc(mode)}</b></div>"
            f"<pre class='light'>{truncate(s.get('analyzed_text') or r.get('content') or '[EMPTY CONTENT]', 1300)}</pre>"
        )

    a(coverage)
    a("</div>")
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    for name in ("phase1", "phase2", "phase3", "phase4", "verdicts"):
        ap.add_argument(f"--{name}", type=Path, required=True)
    ap.add_argument("--coverage-note", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    page = build(
        json.loads(args.phase1.read_text()),
        json.loads(args.phase2.read_text()),
        json.loads(args.phase3.read_text()),
        json.loads(args.phase4.read_text()),
        json.loads(args.verdicts.read_text()),
        args.coverage_note.read_text(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page)
    print(f"wrote {args.out} ({len(page)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
