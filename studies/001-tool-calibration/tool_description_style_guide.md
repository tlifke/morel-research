# Tool description style guide

Distilled from the 005 single-tool A/B experiments and the 006
temperature × prompt 2×2 (both against Gemma 3 4B IT, QAT Q4_0).
These are empirically-grounded patterns for writing tool
descriptions intended to be invoked correctly by weak-to-mid-size
instruction-tuned models.

The guide is provisional — current evidence is one model family
(Gemma 3 4B IT) on the 18-pair A1 seed corpus. Expect revisions as
12B and other model results come in.

---

## Why these patterns matter

A tool description does two things at once:
1. **Tells the model what the tool does** (the obvious job).
2. **Adjudicates competing decision rules** the model has already
   learned: refusal vs. tool use, calculator vs. python, trivial-
   mental-math vs. tool-offload, "broad historical fact" vs.
   "specific value."

Most calibration failures come from (2), not (1). The 4B IT pilot
showed the model knew what each tool does — it failed at choosing
among them, or chose not to call at all when refusal was a stronger
prior. Description authoring is mostly competing-prior arbitration.

---

## Core principles

### 1. Use strict imperative when you want a call

`REQUIRED`, `MUST` — these work. Softer language (`Use`,
`Use whenever`, `If you need to...`) collapses the prompt-engineering
effect.

| 4B IT response on `user_knowledge_lookup` hard halves: |
|---|
| **"REQUIRED whenever..."** — 73% target invocations |
| **"Use whenever..."** — 27% target invocations |
| **baseline ("search the current user's...")** — 0% |

Calibration finding: the model has a strong prior on refusal
("I can't access personal info"); only a stronger directive prior
overrides it. Soft language doesn't reach the threshold.

### 2. Pair directives with explicit skip clauses

This is the biggest finding from 006. Adding "REQUIRED whenever..."
fixed under-calls but introduced *over-calls* on the matched-pair's
trivial halves. The model overgeneralizes a strict imperative to
contexts the imperative didn't intend.

**Always write the negative case alongside the positive:**

> `tool_x(...)` — REQUIRED whenever {positive condition}. Do NOT call
> when {trivial / in-prompt / known-direct condition} — answer
> directly in those cases.

The two halves of the description carry equal authorial weight. The
"REQUIRED" line is half the description; the "Do NOT call" line is
the other half.

### 3. Address known refusal/avoidance modes explicitly

When a tool exists *because* the model has a known refusal mode
(e.g. `user_knowledge_lookup` exists because the model would
otherwise say "I can't access personal info"), name the refusal
pattern in the description and counter it directly.

Example that won: v1a_antirefusal for `user_knowledge_lookup` —
> "REQUIRED whenever the user asks about themselves. Do NOT respond
> with 'I don't have access to personal information' — use this
> tool to get the access."

The anti-refusal clause moved success from 73% (`v1_directive`) to
87% (`v1a_antirefusal`) on a previously-zero-success record set.

### 4. Boundaries between similar tools must be explicit

For palettes with overlapping capabilities (`calculator` vs.
`python_execute`, or any "compute" tools), name the boundary in
*both* tools' descriptions. The model defaults to whichever tool's
description reads more permissively.

Working pattern from `vP1_boundary`:
- calculator: "Use **ONLY** for arithmetic — **NOT** for hashing,
  list/string operations, iteration, library calls, lambda/filter/
  sum constructs."
- python_execute: "**REQUIRED** for any computation calculator
  cannot do: hashing, list/string manipulation, iteration, library
  calls, lambda expressions."

The two descriptions reinforce each other. Either alone is weaker
than both together.

Partial coverage caveat: this pattern fixed SHA-256 (0% → 80%
target) but not sum-of-primes (still 0%). The "sum" keyword
maintained a strong calc prior even against the explicit ban. May
need an additional rule like "computations involving iteration over
a set MUST use python_execute" specifically.

### 5. For lookup tools, anchor on time and specificity

Lookup-style tools that probe external knowledge benefit from
explicit cues about *when* to invoke:

- **Temporal**: "REQUIRED for facts about events after early 2025
  — your training data may not cover these."
- **Specificity**: "REQUIRED for specific values (date, price,
  score, name); broad historical facts can be answered directly."

`vG1_temporal` for `general_knowledge_lookup` got 90% overall (vs
70% neutral at temp=1.0) using both cues. The cues address two
distinct failure modes — under-calling on post-cutoff (specificity
+ temporal) and over-calling on well-known broad facts
(specificity).

### 6. Naming alone doesn't move calibration

Renaming `user_knowledge_lookup` to `lookup_user_info` produced
**zero** improvement at baseline (0% → 0%) and didn't help even
when combined with other cues. Don't lean on tool naming as a
calibration lever; lean on the description.

### 7. Beware of over-cueing

Combining multiple winning patterns can be *worse* than any single
pattern. `v4_combined` (rename + directive + epistemic) scored
27% — worse than the simple `v1_directive` at 73%. More cues
introduce more interpretation surfaces; the model can latch onto
the wrong one.

When iterating, change one dimension at a time. Stop adding clauses
once a target metric is reached.

### 8. Sampling regime matters

The model's tool-call behavior shifts with temperature. At
temperature=0 (greedy), some directives produce deterministic
behavior that contradicts what the same prompt produces at
temperature=1.0. The 006 2x2 found:

- temperature=0 baselines understate per-record success_rate
  relative to temperature=1.0 — many "deterministic failures" at
  temp=0 are partial successes at temp=1.0.
- Directive prompts benefit slightly more at temperature=1.0
  (interaction +2.5 pp).

Author and evaluate descriptions at the sampling regime you'll
deploy at. The methodological default in this repo is
temperature=1.0, top_p=0.95.

---

## Anti-patterns

These were tested and don't work:

| Pattern | What it is | Outcome |
|---------|-----------|---------|
| Renaming | `user_knowledge_lookup` → `lookup_user_info` | 0% → 0% |
| Pure epistemic framing | "the tool DOES give you access" without prescription | 0% → 7% |
| Softer imperatives | "Use whenever..." vs "REQUIRED whenever..." | 73% → 27% |
| Over-stacking cues | rename + directive + epistemic combined | 73% → 27% |

## Known limitations / open questions

- **Socratic-deflection escape route**: closing "I can't access X"
  with v1a (anti-refusal) caused the model to start asking the
  user clarifying questions instead ("Could you please tell me who
  Aunt Nina is?"). This is a *favorable* failure (honest, not
  confabulating) but still a missed tool call. The optimization
  landscape may have multiple escape routes; closing one surfaces
  the next. A "Do NOT ask the user for clarifying info; use the
  tool" clause is a candidate v1a+ variant — untested.

- **Format brittleness under directive**: 4B IT dropped the
  ```` ``` ```` fences around `tool_code` blocks ~11% of the time
  under directive prompts. Whether this is a 4B-specific quirk or
  a feature of directive-style descriptions generally needs more
  models tested. Parser should accept both fenced and bare forms
  regardless.

- **Generality across models**: every finding here is from Gemma 3
  4B IT at QAT Q4_0. 12B IT escalation is queued. Other model
  families (Llama, Qwen, OpenAI) may respond differently to the
  same prescriptive patterns. Verify on the target model before
  trusting the style guide.

- **"Skip when trivial" specificity**: vT1_skip_trivial used
  per-tool examples (single-digit arithmetic, in-prompt dates,
  power-of-10 conversions). General phrasing like "skip when
  trivial" might not work without concrete anchors. Untested.

---

## Template

Use this as a starting point for new tool descriptions:

```
- tool_name(arg: type, ...) — {what the tool does in one sentence}.
  REQUIRED whenever {positive condition: the situation where you
  must invoke this tool}. Do NOT call when {negative condition:
  trivial / in-prompt / answerable-directly cases}. {If applicable:
  Boundary with sibling tool — "Use foo for X, this for Y"}. {If
  applicable: Anti-refusal clause — "Do NOT respond with 'I cannot
  X'; use this tool to do X."}. Returns {output shape}.
```

Single-tool example (a hypothetical `database_query` tool):

```
- database_query(sql: str) — execute a read-only SQL query against
  the user's analytics database. REQUIRED whenever the user asks
  about their own data, metrics, or historical records. Do NOT
  call for general SQL syntax questions or example queries where
  the user is just learning — answer those directly. Do NOT
  respond with "I don't have access to your database" — this tool
  gives you read-only access. Returns the query result as a
  newline-delimited list of rows.
```

---

## Provenance

Findings backing this guide:

- `investigations/005-tool-spec-optimization/investigation.md`
  Results section — ukl variant sweep (v0–v4 + followup v1a/v1b/v1c),
  python_boundary, gkl_temporal, trivial_skip.
- `investigations/006-temperature-prompt/investigation.md`
  Results section — 2x2 directive-vs-neutral × temp=0 vs temp=1.0,
  including the directive-induced regression analysis.

When in doubt, defer to the latest empirical run rather than the
patterns codified here.
