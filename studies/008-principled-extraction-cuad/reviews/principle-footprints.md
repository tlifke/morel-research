# Principle footprints — 16 pilot candidates on harness_val

> **Split names.** Renamed on 2026-08-16 (`../plans/splits.md`); membership did
> not change, so `harness_val` here is exactly the old `dev` and `test` the old
> `holdout`. Where `model_train` is mentioned it means the pre-carve
> 364-contract training pool, not today's 264-contract `model_train`
> (INV1-D8 carved `principle_train` and `principle_val` out of it).

Empirical footprint for every candidate in `principles/pilot/candidates_pilot.reviewed.yaml`,
computed by `principles/pilot/checkers/` over the **harness_val** split only (40 contracts × 12
categories = **480 decisions**). `model_train` was read twice, for two named confirmations only
(g02's marker, d07's furniture rate); `test` was never opened.
Date: 2026-08-15. AI Assistant Used: Claude Code.

This report answers a different question from round 1. Round 1 asked whether each principle is
**true**, and the honest answer from a non-expert was "I can't disprove it" eleven times. This
report asks whether each principle's checker **discriminates** — whether it fires on a
non-trivial, non-tautological slice of the decisions the study will actually score. A principle
can be perfectly true and still be worth nothing here.

---

## Headline table

`rate` is applicability over all 480 decisions. `in scope` is over the decisions the principle
could conceivably govern (its scope categories, or for g01 the nine yes/no categories).
`phi` is the correlation between applicability and gold presence over in-scope decisions.
**taut** means applicability is computed from gold itself, so phi is arithmetic, not evidence.

| id | rate | in scope | contracts | phi | taut | verdict | why |
|---|---|---|---|---|---|---|---|
| **g04** | 4.4% | 52.5% | 21/40 | **0.40** | no | **discriminating** | venue language present in half of contracts, and it predicts a Governing Law clause exists |
| **d04** | 2.9% | 35.0% | 14/40 | 0.21 → **0.47** widened | no | **discriminating after widening** | as written it misses half the gold-present contracts; widening the verb lexicon fixes it |
| **d03** | 2.5% | 15.0% | 6/40 | **0.47** | yes | **discriminating** | strongest gold association in the set, but read off gold span text |
| **g05** | 4.8% | 57.5% | 23/40 | 0.27 | no | **applicability fine, proxy failed** | span-level compliance proxy fails its own pre-registered audit; see §4 |
| **g06** | 1.0% | 12.5% | 5/40 | 0.38 | no | **discriminating but rare** | 6 trigger sentences in all of harness_val, 2 of 6 are not administration at all |
| **g08** | 1.0% | 12.5% | 5/40 | 0.09 | no | **discriminating but rare** | 5 firings, all on gold-present contracts; a narrow real subcase, low phi only because the base rate is 95% |
| **g03** | 2.5% | 2.5% | 6/40 | 0.18 | yes | **rare, and duplicated by d02** | identical firing set to d02 |
| **d02** | 2.5% | 2.5% | 6/40 | 0.18 | yes | **rare, and duplicates g03** | identical firing set to g03 |
| **d05** | 12.5% | **75.0%** | 30/40 | 0.29 | no | **near-degenerate** | fires on 100% of contracts over 4k tokens; a quantity plus a bound cue is ambient legalese |
| **d08** | 4.6% | 55.0% | 22/40 | −0.72 | yes | **degenerate by construction** | fires only where gold is already absent; the phi is the definition, not a finding |
| **g01** | 22.5% | **30.0%** | 33/40 | **1.00** | yes | **degenerate** | fires on 100% of yes/no extractions and 0% of absences — exactly the presence call, restated |
| **g07** | 7.9% | **95.0%** | 38/40 | 1.00 | yes | **degenerate** | applicability *is* gold presence for Agreement Date |
| **d01** | 5.8% | 70.0% | 28/40 | 0.35 | yes | **degenerate** | applicability is "gold already has the clipped shape", so the checker is the answer restated |
| **d06** | **0.2%** | 2.5% | 1/40 | −0.70 | yes | **degenerate** | one firing in 480 decisions |
| **d07** | **0.0%** | 0.0% | 0/40 | — | yes | **degenerate** | zero firings; 10 qualifying spans exist in the whole 404-contract harness_val+model_train pool |
| **g02** | **0.0%** | 0.0% | 0/40 | — | — | **unimplementable** | the `<omitted>` marker does not exist in CUAD v1 |

Ordering above is by how much the footprint tells us, not by rate.

---

## 1. The two zero-rate findings

**g02 is unimplementable, and this is a disqualifying finding under the study's own rule.**
The Handbook genuinely prescribes the `<omitted>` convention, and the checker sketch is a
faithful reading of it. But the literal string `<omitted>` occurs in **0 of 404** harness_val+model_train
contract texts and **0 of 4,052** gold spans in the 12-category subset. The convention was a labelling-tool convention that
did not survive into the released CUAD v1 JSON: non-contiguous responsive material appears there
as *multiple separate spans*, not one marked-up span. Applicability is therefore identically
zero and no model behaviour can ever move it. Per component-contracts.md — "a principle without
a feasible checker does not enter the scored set" — g02 is out. Note what this cost: g02 was
accepted in round 1 as "another clear principle direct from the guidelines", and it is. Being
true was never the issue.

**d07 fires zero times on harness_val.** Widening the furniture regex to catch bare page numbers and
looser confidential-treatment legends raises it to exactly 1 of 480. Across the whole
12-category harness_val+model_train pool there are **10** gold spans with furniture strictly inside — about
0.025 per contract. Combined with D-20's finding that d07's *main clause is refuted* (splitting
at furniture outnumbers swallowing it 5:1 corpus-wide), there is nothing left: the half that is
true is too rare to measure and the half that is measurable is wrong.

---

## 2. The tautology problem — six principles that restate the gold label

Six checkers compute applicability from the gold answer itself, which makes their phi arithmetic
rather than evidence. The footprint still tells us something, but only about **rate**.

- **g01** fires on 108 decisions — every single yes/no category that gold marks present, and
  nothing else. In-scope rate 30%, but *conditional on the decision being an extraction the rate
  is 100%*. Tyler predicted exactly this in round 1 ("this will likely trigger on every span").
  He was right, and that is the argument against it: a principle cited on every extraction
  cannot appear in an H4 confusion matrix as anything but background.
- **g07** fires on 38 of 40 Agreement Date decisions for the same reason.
- **d01** fires on 28 of 40 — and its applicability test is "gold is already a short clipped date
  string", so it can only ever be applicable where the model has nothing to learn. On the g01
  clash Tyler flagged: it is not a real contradiction. g01's own trigger_guidance exempts the
  date categories, which is exactly d01's scope, and the parallel cross-source check
  (`reviews/`, commit 7ffe250) confirms the split in gold — yes/no-category spans are
  sentence-shaped 80.9% of the time against 1.3% for Agreement Date. So the objection to d01 is
  not that it is wrong but that its checker cannot be scored: applicability is the answer.
- **d08** fires on 22 of 40 Minimum Commitment decisions, **all 22 gold-absent**, because
  applicability requires `is_impossible`. Its phi of −0.72 is definitional. What the footprint
  does show: 22 of the 28 MC-absent contracts (79%) contain an unquantified undertaking, so the
  *trap* d08 describes is real and common. That makes it a candidate for rewriting as an
  instance-only checker, not for keeping as written.
- **d06** fires **once in 480 decisions**. Its evidence base was already n=1 (the proposer said
  so); harness_val does not enlarge it.
- **g03 / d02** fire on the identical 12 decisions in 6 contracts. They are the same principle
  arrived at from the Handbook and from mining. Keeping both double-counts the source-agreement
  claim the study wants to make. Keep one; record the agreement as a finding about the two
  derivation arms.

---

## 3. d04 as written vs widened — the cost of the narrow regex

D-20 confirmed d04's *claim* and flagged its *regex*: the `supply|deliver|provide|share|allocate|
make available` alternation cannot see performance/effort floors, the second-largest span class
at 16.4%. Both footprints, on the 40 Minimum Commitment decisions in harness_val:

| variant | fires | applicable & MC present | applicable & MC absent | missed MC present | phi |
|---|---|---|---|---|---|
| as written | 14 | 6 | 8 | **6** | 0.21 |
| widened verbs | 18 | 9 | 9 | 3 | 0.39 |
| widened verbs + widened floor cue | 19 | **10** | 9 | **2** | **0.47** |

As written, d04 is blind to **half** the contracts where gold marks Minimum Commitment present.
Widening the verb list (adding spend / pay / maintain / deploy / employ / produce / perform /
sell / generate / achieve / have access to) recovers 4 of those 6 and more than doubles phi;
also widening the floor cue (`not less than`, `no fewer than`, `guarantee`, `floor`) recovers a
fifth. The false-positive count barely moves (8 → 9). This is close to a free win and the widened
lexicon should be adopted. Both variants are stored in `footprints.json` under
`stability.widened_verbs` and `stability.widened_floor_and_verbs` so the two can be compared
in the review app.

Caveat that keeps this honest: the "MC present" column is a **contract-level** association. It
says the widened checker fires more often on contracts that have a minimum commitment, not that
it fires on the right *sentence*. Only model outputs can show that.

---

## 4. g05 and g06 — the hand-scored lexical proxies

Both carried explicit instructions to hand-score ~20 spans before locking, with an abort at
~15%. That audit was run on **all 24** Revenue/Profit Sharing gold spans in harness_val, plus a
false-pass scan over 3,556 sentences in the 27 harness_val contracts where gold rules the category
absent. Labels are checked in at `principles/pilot/checkers/handscore_labels.yaml`; the
arithmetic is `handscore.py`.

**g05's compliance predicate fails the audit decisively, in both directions.**

| measure | as written | repaired |
|---|---|---|
| gold spans it accepts | 15/24 | 20/24 |
| agreement with hand judgement | 66.7% | 87.5% |
| **false-fail rate** (gold span the checker rejects) | **33.3%** | 12.5% |
| candidate false passes in RPS-absent contracts | **140** | 65 |

The false-fails are systematic, not noise. The as-written predicate cannot see: a rate that is
redacted (`[***]% of the Net Sales`, `commission at the rate of [***] on Net Sales` — no digits
before the `%`), a share written as a ratio (`distributed equally - 50/50`), an entitlement
stated without arithmetic (`the parties shall share certain revenues`; `entitled to all revenues
resulting from the sale of advertising`), or a base named with a non-lexicon word
(`according to the income from…`, `0.50% of average daily net assets`).

Worse is what happens on the other side. The 140 candidate false passes are **136 from the
equity branch alone**, and the cause is a one-character regex bug in the sketch itself: `shares?`
matches the *verb* "share". Twenty sampled false passes were inspected by hand and **20 of 20**
were spurious — warranty recitals, insider-trading policies, fuel-cell stacks that "share common
ducting". The remaining 4 are per-unit fees in one distributor agreement that arguably *should*
have been labelled RPS, i.e. a gold disagreement rather than a checker failure.

The (a) percentage-of-revenue branch, taken alone, produced **zero** false passes across all
3,556 negative sentences. So the diagnosis is precise: g05's arithmetic core is sound and its
equity extension is not lexically separable from ordinary corporate boilerplate. Recommended
disposition: keep g05, restrict the compliance predicate to (a) + (b) + the repaired
percentage/ratio/redaction handling, and **drop the equity clause** or move it to hand labelling.
Do not lock the checker as sketched.

**g06 passes on its substance and is starved on volume.** Its trigger fired on exactly **6
sentences in all of harness_val** (5 contracts). Of those 6, 4 are genuinely share-administering
machinery and **0 of 6 fall inside a gold RPS span** — the principle's claim holds 6/6. The 2
misfires are a royalty-*free* licence grant (matched on the word "royalty") and a software
feature list mentioning reports and revenue. Trigger precision 4/6 = 67%.

The sharper problem is a miss. Innoviva span 2 — a quarterly credit/debit true-up with no
entitlement in it — is pure machinery **and is gold-labelled Revenue/Profit Sharing**. g06 says
it should not be. g06's own administration regex does not even fire on it. So the one place in
harness_val where g06 and gold actually disagree is invisible to g06's checker. That is a 1-in-24
compliance-vs-correctness inversion of the kind D-19 checked for on g08 and did not find.

---

## 5. Stability

Every checker was re-run under lexicon and threshold variants (stored per principle under
`stability` in `footprints.json`). Two are worryingly sensitive and one reassuringly is not.

- **g01** — including the value-shaped categories in the "yes/no" list takes it from 108 to 211
  firings, a 95% swing on one lexicon decision. The list is not derivable from the Handbook text
  alone.
- **g05** — see §4; the equity branch alone moves the negative-sentence pass count from 4 to 140.
- **d04** — 14 / 18 / 19 across the three lexicons, and phi 0.21 / 0.39 / 0.47. Sensitive, but
  sensitive in a direction the D-20 hand classification independently predicted, which is the
  good kind of sensitivity.
- **d05** — 60 / 52 / 48 for both-cues / lower-only / upper-only. Stable, but stably huge.
- **g04** (21 → 23), **g06** (5 → 4), **g08** (5 / 5 / 5 across a 2× window change), **d01**
  (28 → 28 at a 50% longer length cap), **d02** (12 → 12 at IoU 0.8), **d06** (1 → 1 at a 2×
  window) are all insensitive. g08's total insensitivity to the search window is the single
  cleanest stability result in the set.
- The sentence segmenter was changed mid-run (trailing-whitespace handling) and **not one
  principle's count moved**, which is a useful negative control on the shared dependency.

---

## 6. What discrimination can and cannot show right now

There are no model outputs yet, so "discrimination" here means only: *does applicability
partition the gold decisions non-trivially?* The 2×2 is applicability × gold-presence, over
in-scope decisions.

It **can** show: a principle that never fires (g02, d07, d06) is dead regardless of truth; a
principle that fires on everything in scope (d05 at 75%, g07 at 95%, g01 at 100% of extractions)
cannot separate anything; and a principle whose applicability is computed from gold (six of the
sixteen) has a phi that is arithmetic and must not be read as evidence.

It **cannot** show: whether firing predicts *compliance* failure, whether a principle helps a
model, or whether a checker fires on the right sentence rather than merely the right contract.
Every phi in the table is a contract-level or decision-level association with the presence label,
not with any behaviour. The strongest positive phi in the set (d03, 0.47) sits on a checker that
reads gold span text, so it is partly circular. Nothing here should be quoted as an effect size.

Denominators are small: 40 contracts, so a scoped principle has at most 40 in-scope decisions and
a 1-contract move is 2.5 points. Volume Restriction has 4 positives in harness_val and Source Code Escrow
has 1; any statement about those categories is anecdote.

---

## 7. My view on what to drop

Tyler decides. On the evidence I would:

**Drop outright (4):**
- **g02** — unimplementable, rate identically 0, and no future model run can change that.
- **d07** — 0 firings, and D-20 already refuted its main clause.
- **d06** — 1 firing in 480; the proposer flagged it as effectively n=1 and harness_val agrees.
- **d01** — tautological applicability, and it adds nothing over g01's own date-category
  exemption. (Tyler deferred this one on the apparent g01 contradiction. The contradiction is
  not real; the tautology is, and it is the better reason to drop it.)

**Merge (1):** **g03 and d02** are the same principle with the same 12-decision footprint. Keep
one — I would keep **g03**, because the Handbook provenance is stronger and d02's own defect
argument concedes its pairs were cross-document. Record the exact agreement as a
source-convergence result.

**Rewrite before locking (3):**
- **d04** — adopt the widened lexicon. As written it is blind to half the positives.
- **g05** — drop or hand-label the equity branch; keep the arithmetic core. It failed its own
  pre-registered audit at 33% false-fail and ~100% false-pass on the sampled equity hits.
- **d08** — rewrite applicability as instance-only (undertaking cue present, no quantity token,
  *without* consulting `is_impossible`). The trap is real in 79% of MC-absent contracts; the
  current checker just cannot see it without peeking at the answer.

**Demote but keep (2):** **g01** and **g07** are true, universal, and informationally empty as
citations. If the point of the principle set is an H4 confusion matrix, a principle cited on
every extraction is background. I would keep them in the *prompt* (they shape spans) and exclude
them from the *scored citation set*, and I think that distinction — prompt-visible vs
scored — may be worth making explicit in the plans as a new decision.

**Keep as is (5):** **g04** (the best footprint in the set), **d03**, **g06**, **g08**, and
**d05** with a warning. d05 is the most strongly evidenced principle in the pilot and its
footprint is the worst kind of near-degenerate: it fires on 100% of contracts over 4k tokens.
It may still be right; it just cannot be cited discriminatively at that rate. If it is kept, its
applicability needs tightening to the *contrastive* case its evidence actually came from — both
cue classes present in one contract — rather than either cue anywhere.

**One meta-observation.** Provenance did not predict quality. Of the eight guidelines-derived
principles, one is unimplementable and two are tautological; of the eight mined ones, one is
refuted, one fires once, and one fires on everything. The two strongest footprints are one from
each arm (g04, d04). Round 1's implicit assumption that Handbook provenance confers authority is
not supported by the footprints.

---

## Reproduction

```
cd studies/008-principled-extraction-cuad/principles/pilot
uv run python -m checkers.handscore        # writes handscore.json
uv run python -m checkers.run_footprints   # writes footprints.json
uv run --with pytest python -m pytest checkers/tests/test_checkers.py -q
```

Two machine-readable artifacts are written, both keyed by principle id:

- `checkers/footprints.json` — the full record: rate over all decisions and in scope,
  per-category and per-length-bucket distribution, the discrimination 2×2 with phi, every
  stability variant with its own 2×2, and the g05/g06 hand-score blocks.
- `checkers/footprint.yaml` — the same measurements shaped to the review app's footprint sidecar
  schema (`status` / `applicability` / `distribution` / `discrimination` / `examples` / `note`),
  so round 2 can be launched with
  `--footprint principles/pilot/checkers/footprint.yaml`. Applicability there is stated over
  **in-scope** decisions, since that is the denominator the app's degeneracy flag reads; the
  all-decision rate is repeated in each note.

Nothing outside
`principles/pilot/checkers/` and this file was written; no dataset was modified; test was not
loaded.
