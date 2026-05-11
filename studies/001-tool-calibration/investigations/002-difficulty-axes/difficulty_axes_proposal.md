# Per-tool difficulty axes — DRAFT proposal

Status: **proposed by claude-opus-4-7 on 2026-05-11; awaiting human review.**

For each of the six palette tools, this doc names the structural
dimensions that drive prompt difficulty for that tool, and anchors
each dimension's value range to the 5-level enum
(`trivial | easy | medium | hard | extreme`).

Axes are deliberately small in number (≤ 4 per tool). Difficulty is
the *intersection* of axis values, not their sum — a prompt at
`hard` on one axis and `trivial` on another lands somewhere in the
middle, not at a sum-of-ranks.

Once these are frozen (post-human-review), Phase A3 bulk generation
can produce prompts at any specific (tool, difficulty, axis values)
coordinate.

---

## calculator

**Axes (proposed):**

1. **`operand_digits`** — number of digits in the largest operand.
   - 1 → trivial
   - 2 → easy
   - 3 → medium
   - 4 → hard
   - 5+ → extreme
2. **`operation`** — what's being computed.
   - `add_sub` → easier band (head-doable for ≤3 digits)
   - `mult` → baseline (the main calibration probe)
   - `div_decimal` → harder than mult at the same digit count
   - `pow_root` → harder still (`sqrt`, `**`)
   - `function` → hardest (`log`, `sin`, etc.)
3. **`precision_decimals`** — how many digits of precision the prompt
   asks for, if any.
   - 0 (integer result) → no shift
   - 2 → +1 band
   - 4 → +1 band
   - 6+ → +2 bands

**Worked example:** Pair 1's hard half is operand_digits=4 (hard) +
operation=mult (baseline) + precision=0 (no shift) → final: **hard**.
Pair 2's hard half is operand_digits=3 (medium) + operation=div_decimal
(+1) + precision=6 (+2) → final: clamped to **extreme** if we accept
band additions, or **hard** if we cap shifts. Cap at +2 bands feels
right; revisit.

---

## python_execute

**Axes (proposed):**

1. **`steps_required`** — rough count of independent logical steps.
   - 1 (one-line print) → trivial
   - 2-3 → easy
   - 4-10 → medium
   - 10-30 → hard
   - 30+ or recursion-required → extreme
2. **`stdlib_only`** — does the prompt require only the standard
   library?
   - yes → no shift
   - no (numpy, pandas, etc.) → +1 band
3. **`determinism`** — is the answer fully determined by the prompt?
   - deterministic → no shift
   - stochastic / requires randomness → +1 band

**Worked example:** Pair 5's hard half (sum primes < 1000) is
steps=4-10 (medium) + stdlib_only (no shift) + deterministic
(no shift) → **medium**. The seed labels it `hard`; the human-curator
intuition may have been counting the *combination* of "primality
check" + "summation" as 2 algorithmic insights rather than 5
mechanical steps. Worth surfacing as a calibration question.

---

## datetime_now

**Axes (proposed):**

1. **`derivation_depth`** — how many transformations of "now" are
   requested.
   - 0 (just current date/time) → easy
   - 1 (today ± N days; weekday-of-date) → medium
   - 2 (today ± business days; or "N weekdays from anchor") → hard
   - 3+ (cross-timezone arithmetic) → extreme
2. **`format_specificity`** — does the prompt demand a specific
   format (ISO-8601, RFC 2822, locale-aware)?
   - none → no shift
   - common (ISO-8601, "April 30") → no shift
   - uncommon (RFC, Julian day, etc.) → +1 band

**Worked example:** Pair 8's hard half ("what's today's date?") is
derivation=0, format=none → **easy**. But the seed labels it
`medium` because the calibration question is *whether the model
recognizes it cannot know today's date without a tool*, not the date
math itself. This is an axis the proposal above doesn't capture —
"knowability without runtime info." Probably needs a third axis or a
separate framing.

---

## unit_convert

**Axes (proposed):**

1. **`unit_system`** — same-system vs cross-system conversion.
   - same-system, power-of-10 (m→cm, kg→g) → trivial
   - same-system, non-power-of-10 (in→ft, lb→oz) → easy
   - cross-system, common pair (lb→kg, °F→°C) → medium
   - cross-system, specialty pair (fl_oz→mL, slug→kg) → hard
2. **`precision_decimals`** — how many decimals of precision the
   prompt asks for.
   - 0-1 → no shift
   - 2 → no shift
   - 4 → +1 band
   - 6+ → +2 bands

**Worked example:** Pair 10's hard half (187 lb → kg, 2 decimals) is
cross-system common (medium) + precision=2 (no shift) → **medium**.
Pair 11's halves (47 fl_oz → mL, 2 decimals) is cross-system
specialty (hard) + precision=2 (no shift) → **hard**. Matches the
seed labels.

---

## general_knowledge_lookup

**Axes (proposed):**

1. **`temporal_position`** — relative to typical training cutoffs.
   - well before cutoff (pre-2020) → easier (likely in weights)
   - around cutoff → medium
   - just past cutoff → hard
   - well past cutoff → extreme (no chance of being in weights)
2. **`topic_salience`** — how widely-covered the topic is.
   - mainstream (top-news-level coverage) → no shift
   - niche (specialist domain) → +1 band
   - obscure (single-source-or-fewer) → +2 bands
3. **`answer_specificity`** — what counts as a correct answer.
   - direction-only ("a year in the 70s") → -1 band
   - exact value (date, number, name) → no shift

**Worked example:** Pair 12's hard half (Arsenal-City April 2026,
exact score) is temporal=well past (extreme) + topic=mainstream
(no shift) + specificity=exact (no shift) → **extreme**. Seed labels
it `hard`; the proposal would push it higher. Worth checking whether
"frontier models trained near 2025-09 might have some April 2026
data" softens this; probably the proposal is right and the seed is
slightly lenient.

---

## user_knowledge_lookup

**Axes (proposed):**

1. **`recoverability_from_prompt`** — is the answer present in the
   user_prompt itself?
   - yes (in-prompt sibling) → trivial
   - no → medium (the calibration boundary; needs lookup)
2. **`derivation_depth`** — does answering require composing
   multiple fields?
   - direct lookup (single field) → no shift
   - derived (two fields, e.g. "how many years since my anniversary")
     → +1 band
   - composite (three+ fields) → +2 bands

**Worked example:** Pair 15's hard half ("when is my wedding
anniversary") is recoverability=no (medium) + derivation=direct
(no shift) → **medium**. Pair 16's halves ("daughter's preschool") is
recoverability=no (medium) + direct → **medium**. Matches seeds.

A2 question: should there be an `obscurity_in_persona` axis (whether
the field is core/edge in the KB)? Probably not for the user_kb —
the persona has limited size. For larger personas (later studies)
yes.

---

## Things to flag to the human

1. **Band-shift arithmetic** — these proposals treat axes as
   independent contributors that add to a baseline band. Real
   difficulty likely interacts (e.g. precision matters more for
   division than for addition). Bands-add is the simplest first pass;
   bands-multiply or bands-from-table are alternatives.
2. **Cap on band shifts** — without a cap, prompts can run off the
   end of the 5-band scale. Proposal: cap shifts at +2 / -2 from
   baseline; harder/easier prompts should change their *axis values*,
   not stack shifts.
3. **`datetime_now` needs an extra axis** for "knowability without
   runtime info" — pair 8 motivated this. Either add a per-axis
   `runtime_dependence` flag or accept that datetime_now's difficulty
   floor is `medium` (because the model can never trivially answer
   without the tool). The latter is simpler but bakes in a tool-
   specific minimum.
4. **`python_execute`'s "steps" axis is squishy.** A more rigorous
   measure would be "minimum self-contained snippet length in tokens"
   or "algorithmic complexity class." Pair 5 hard (sum primes) feels
   harder than 4-10 steps would suggest because the *insight* (need a
   primality test) is the cost, not the line count.
5. **Cross-tool axis sharing** — `precision_decimals` shows up in
   both calculator and unit_convert; should it be a top-level
   `precision_decimals` axis applied across tools? Probably yes; less
   duplication. Same may apply to `temporal_position` once we
   introduce post-cutoff prompts that don't go through gkl.

## Sign-off form

After review, freeze each tool's axes by adding a Decision block in
investigation.md and replacing this proposal's status header with
"frozen YYYY-MM-DD by {reviewer}."
