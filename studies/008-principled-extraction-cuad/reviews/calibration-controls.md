# Calibration controls for the principle-curation gate (G2)

Instrument note. Safe for the curator to read before round 2 — it contains no
information identifying which round-2 records are controls, and no statement
about what any control claims. The answer key is
`principles/pilot/controls_key.yaml` and must not be opened until round-2
decisions are recorded. Date: 2026-08-15. AI Assistant Used: Claude Code.

## Why the instrument exists

Round 1 of curation returned **11 accept, 5 defer, 0 reject, 0 edit** on 16
candidates. Several accept rationales say, in the curator's own words, that he
lacks the domain expertise to disprove the candidate and is accepting for want of
a reason not to. That is an honest record and it is also the problem: a gate that
never rejects and never edits may be measuring nothing, and every downstream
claim that rests on "the principle set was human-curated" inherits that weakness.

Rather than assume the gate is weak, we measure it. Seven principles that are
demonstrably wrong against gold are seeded into the round-2 queue, in the same
schema, register, level of detail and evidence style as the real candidates, with
filled proposer blocks. The curator knows controls exist; he does not know which
records they are, or how many.

## What is in the set

Seven controls, spanning six failure modes, one per mode plus one extra in the
most common mode:

| failure mode | what it tests |
|---|---|
| inverted convention (x2) | does the curator notice a rule that states the opposite of what gold does |
| plausible-but-absent | does he notice a rule that sounds like standard practice but that CUAD's annotators did not follow |
| over-broad scope | does he notice a rule that is true for one category and asserted across several |
| degenerate | does he apply the investigation's own screen against principles the schema already enforces |
| defect-derived | does he notice a generalisation from a documented gold defect (D-15) presented as a convention |
| circular | does he notice a restatement of the printed category definition, which every arm already receives |

Each control was disproved against gold in `harness_val` + `model_train` before it entered
the set — contract ids, offsets and counts are recorded in the answer key.
test was never loaded. Candidates that could not be disproved were discarded
during authoring rather than kept as "probably wrong", because a control whose
wrongness cannot be demonstrated is indistinguishable from a real principle that
happens to be wrong, and would corrupt the measurement in the direction that
flatters the gate.

Difficulty is tagged per control: **2 easy, 3 medium, 2 hard**, where difficulty
means "detectable by a non-expert who has the cross-source validation and the
adversarial critique in front of him", not "detectable by a contracts lawyer".
The spread is deliberate. An all-easy set would make a 100% catch rate
uninformative; an all-hard set would make a 0% catch rate uninformative.

## What the pre-review pipeline does to the difficulty tags

The round-1 candidates were given two gold-side artifacts before review:
`principles/pilot/cross_source_validation.yaml` (every claim tested empirically
against gold) and `principles/pilot/critiques.yaml` (an adversarial critic that
measures gold and reports the strongest case against each candidate). Every
control in this set is refutable by exactly that treatment — that is what
"demonstrably wrong, with receipts" means.

So the tags depend on what round 2 runs:

- **If the controls are curated raw**, the difficulty tags stand as written and
  the instrument measures unaided detection.
- **If the controls receive the same cross-source validation and critique pass**,
  expect all seven to surface as `contradicted` or `refuted`, and the instrument
  measures something different but equally worth knowing: **whether the curator
  acts on a contradiction flag**. Under that condition a miss is a much stronger
  negative result — the curator accepted a principle his own tooling told him was
  refuted — and the difficulty tags should be reported as "not applicable, all
  controls pre-flagged" rather than reused.

Record which of the two conditions was run, on the record, before scoring. They
are not comparable and the difference is larger than any effect this instrument
can resolve at n=7.

## Scoring

Per control, from its round-2 `review` block:

- **catch** — `decision: reject`, or `decision: edit` where the edit removes the
  wrong claim.
- **miss** — `decision: accept`.
- **abstention** — `decision: defer`. Reported as its own category and **never
  counted as a catch**. Round 1 shows defer is this curator's response to
  uncertainty, not to detected error; folding defers into catches would let the
  gate score well by being uniformly unsure.

Report three numbers, not one: catch rate over the 7 controls, catch rate by
difficulty tag, and the abstention rate. Report alongside them the **false-alarm
rate** — real round-2 candidates rejected — because a curator who rejects
everything catches every control while adding no information (see limitations).

## What a result would mean

At n=7, with 95% Clopper-Pearson intervals:

| caught | rate | 95% CI |
|---|---|---|
| 0 / 7 | 0.00 | [0.00, 0.41] |
| 1 / 7 | 0.14 | [0.00, 0.58] |
| 2 / 7 | 0.29 | [0.04, 0.71] |
| 3 / 7 | 0.43 | [0.10, 0.82] |
| 4 / 7 | 0.57 | [0.18, 0.90] |
| 5 / 7 | 0.71 | [0.29, 0.96] |
| 6 / 7 | 0.86 | [0.42, 1.00] |
| 7 / 7 | 1.00 | [0.59, 1.00] |

Readings that the instrument supports:

- **0–1 caught, including the two easy controls missed.** The gate is
  non-discriminating on substantive quality. This is a strong result even at
  n=7, because the two easy controls are catchable from documents the curator
  wrote or approved, with no domain knowledge. Under a true catch rate of 0.3,
  seeing 0 of 7 has probability 0.08 — so a clean zero is unlikely to be bad
  luck, and the honest statement is still "the true rate is somewhere under
  0.41".
- **2–4 caught, concentrated in easy/medium.** The gate discriminates on
  internal consistency (contradiction with an accepted principle, redundancy
  with the schema) but not on facts about gold. This is the outcome the round-1
  rationales predict, and it argues for a specific fix — give the curator
  gold-side checks like `reviews/principle-claim-checks.md` for every candidate,
  not more principles.
- **5–7 caught.** The gate is doing real work and round 1's 0-reject outcome
  reflects the candidates, not the curator. Note this is also the outcome a
  reject-heavy strategy produces, so it is only interpretable together with the
  false-alarm rate on the real candidates.

## Limitations, stated plainly

1. **n=7 is small and the intervals are wide.** Every row of the table above
   spans at least 0.4 of the unit interval. No catch rate here distinguishes a
   0.4-gate from a 0.7-gate. The instrument is powered to separate "near zero"
   from "substantial", not to estimate a rate. Treat the difficulty-stratified
   reading (which *kinds* of wrongness were caught) as the primary result and the
   overall rate as secondary.
2. **The controls test detection of wrongness, not recognition of value.** A
   curator who rejects every unfamiliar record scores 7/7 and has learned
   nothing about contract annotation. The instrument cannot see that failure by
   itself; only the false-alarm rate on real candidates can, and that rate has no
   ground truth, since we do not know which real candidates are correct.
3. **Nothing here measures whether good-but-unobvious principles survive.** The
   round-1 defers are exactly that population, and this instrument says nothing
   about them.
4. **The set is one curator, one round, one queue.** No claim about human
   curation in general follows.
5. **Difficulty tags are the author's judgement**, calibrated against what the
   curator had in front of him, not measured. If a control tagged hard is caught
   easily, the tag was wrong, and that should be reported rather than smoothed.
6. **Contamination risk.** Once round 2 is scored, these seven records are burnt
   — the curator will know them. A round-3 measurement needs new controls, and
   they will be harder to write, because the curator will by then be primed to
   look for them. Expect the measured catch rate to rise for reasons that have
   nothing to do with the gate's quality on real candidates.

## Handling

- `principles/pilot/controls.yaml` — the seven records, ready to merge into the
  round-2 queue. Merge by loading both files and re-dumping through one YAML
  writer, and renumber so the control ids do not form a contiguous block.
- `principles/pilot/controls_key.yaml` — answer key. Not to be read by the
  curator before decisions are recorded, and not to be locked into any principle
  set.
- No control may reach `principles/locked-YYYY-MM-DD.yaml`. After scoring,
  remove all seven regardless of their review decisions, including any that were
  accepted — an accepted control is the finding, not a principle.
