---
name: agent-trace-report
description: Render an agent/LLM run trace as a self-contained, color-coded HTML report — a move-tagged sequence diagram plus per-step cards showing the model's reasoning and the full input/output of every step. Use whenever the user wants to see "exactly what happened" in an agent iteration or trace, visualize a researcher/agent run, turn a trace JSONL into a readable report, or asks for a transparent step-by-step view of an LLM loop with its tool calls and results. Triggers on phrases like "show me what happened", "visualize this run/trace/iteration", "render the trace", "trace report", "what did the agent do step by step". Built for study 004's researcher harness but works on any trace following the schema below.
---

# agent-trace-report

Turn an agent run into a transparent HTML artifact. This is the report style
Tyler signed off on: color-coded by **research move**, with the agent's private
reasoning shown inline alongside the full I/O of each step.

## What it produces

A single self-contained HTML file (no external assets) with three parts:

1. **Setup** — exactly what the model was given: system prompt, first user
   message, and each tool (description, params, mock/real backend).
2. **Sequence diagram** — an SVG with two lifelines (**Agent** ↔ **Substrate**).
   Reasoning shows as italic ticks on the agent lane; tool calls are rightward
   arrows; results are dashed amber arrows back; final text is a REPORT block.
   This is the at-a-glance "what happened".
3. **Ordered step cards** — every step, move-badged and color-matched to the
   diagram, showing the complete bytes: thinking, tool-call args, tool results,
   prose. Plus an optional "what to notice" box.

Keep this design language. The color-coded moves + inline reasoning + full I/O
is the point — it is what makes the run legible.

## How to run

```bash
uv run --no-project python .claude/skills/agent-trace-report/render_trace.py <trace.jsonl> [--output report.html]
```

Default output is `report.html` next to the trace. The renderer needs no deps
beyond the stdlib.

## Trace JSONL schema

One JSON object per line. An optional **first** line of `kind: "meta"` populates
the setup section and report chrome; without it the report still renders (setup
section is just omitted). Emit it from the harness so every trace is
self-describing.

```jsonc
{"kind":"meta","title":"...","subtitle":"...","model":"nemotron-3-nano:4b",
 "substrate":"mock","scenario":"T1 cold start","system_prompt":"...",
 "first_user":"...","tools":[{"name":"bash","desc":"...","params":"...","backend":"..."}],
 "notes":["bullet for the what-to-notice box", "..."]}
```

Step records (each gets a card; `move` is optional and inferred from tool name
when absent):

| kind | fields | becomes |
|---|---|---|
| `input` | `text` | INPUT |
| `thinking` | `text` | REASON |
| `tool_use` | `name`, `arguments`, `move?` | EXECUTE/MEASURE/… (inferred or explicit) |
| `tool_result` | `tool_use_id`, `text` | SUBSTRATE |
| `assistant_text` | `text` | REPORT |
| `end` | — | END |

## Move taxonomy + palette

The harness should tag `tool_use` records with an explicit `move`. Inference
fallback: `bash→EXECUTE`, `evaluate_predictions→MEASURE`, `read→OBSERVE`,
`glob→ORIENT`, `write→RECORD`, `share_finding→REPORT`, else `TOOL`.

ORIENT · HYPOTHESIZE · DESIGN · EXECUTE · OBSERVE · MEASURE · INTERPRET ·
DECIDE · RECORD · DIAGNOSE · REPORT — plus REASON (thinking), INPUT,
SUBSTRATE (a result), END. Colors are defined in `render_trace.py:MOVE_META`;
the legend only shows moves actually present in the trace.

## Related

- The producer side (how a run emits this trace) lives in
  `studies/004-researcher-diagnostics/investigations/001-mock-substrate-harness/harness/src/slice.ts`
  via `agent.subscribe`.
- For the companion "where is data logged" topology, see `render_data_map.py`
  in that harness — a different diagram, deliberately not merged into this one.
