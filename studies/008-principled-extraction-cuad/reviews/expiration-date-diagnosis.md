# Why Expiration Date is the worst cell in the study

**Run:** `data/traces/2026-08-16-c2c3-harness-val/` (240 trials, `harness_val`,
Qwen3.5-9B, C2/C3, seeds 0/1/2). `test`, `principle_train`, `principle_val` and
`model_train` were not touched. Read-only throughout; nothing in `harness/`,
`principles/`, `apps/` or `plans/` was modified.

---

## Verdict

**It is a principle, not a task-definition defect. Do not patch the prompt.**

The model is not confused about what Expiration Date is. In every single
false-absent decision I read, it **locates the correct clause, quotes it
verbatim, and frequently computes the correct expiry date** — and then rules
absent anyway, on the explicit ground that the contract states the term as a
duration rather than as a calendar date. That is a correctly-understood target
plus a wrong call on a hard case, which is the study's own definition of
business logic.

The split is total and it is the whole story:

| gold Expiration Date span contains… | contracts | decisions | TP | FN | recall |
|---|---|---|---|---|---|
| an explicit calendar date | 7 | 31 | **31** | 0 | **1.00** |
| a duration ("three years", "fifth anniversary") | 18 | 95 | 0 | 95 | **0.00** |
| an event / until-terminated / perpetual | 3 | 18 | 1 | 17 | 0.06 |
| other (multi-limb, conditional) | 4 | 20 | 0 | 20 | 0.00 |

**Presence recall is 100% when the gold span names a calendar date and 0.8%
when it does not.** All 132 false-absents live in the bottom three rows. There
are **zero false-presents** for this category in either arm — the model never
over-claims here, it only declines.

Two further facts make the verdict harder to argue with:

1. **A principle already in the set is causing the failure, by name.** `w06`
   ("claim absence when the document does not state the specific fact the target
   asks for") is quoted by id in the reasoning of **43 of the 63** C3 Expiration
   Date false-absents. `w06` is scoped to *Agreement Date* and the prompt says
   so; the model applies it to Expiration Date anyway.
2. **The pattern already has a named precedent in the working set.** `w07`
   exists because the printed Minimum Commitment definition reads narrower than
   annotation practice, and "a model applying the printed definition literally
   under-extracts." That is verbatim what is happening here. `w07` is a
   principle. So is `w03`, which is a pure target-extension rule ("venue and
   arbitration clauses are not responsive"). Category-boundary rules are already
   this set's core business.

Patching the task definition would repeat exactly the error **D-25** identified
and **D-1/D-22** exist to prevent: the `Answer Format` column was stripped from
the prompt precisely so that granularity would be `w01`'s job rather than the
prompt's, and adding "duration clauses count" to the Expiration Date line is the
same move being made again one category to the right. It would also hide `w06`'s
damage, inflate any later C2−C1 gain by having the prompt do the principle's
work, and remove the largest single measurable target inv 006 has.

**Volume Restriction is a different animal and is not the same verdict** — see
§4. It is a genuine annotation-boundary dispute at n=9 present decisions, too
thin to select a principle on from `harness_val`.

---

## 1. The evidence

### 1.1 The gold spans the model missed are durations, not dates

Contract-level, all 32 gold-present Expiration Date contracts in `harness_val`
that produced scored trials. Every contract whose gold span carries a calendar
date is mostly-TP; every contract whose gold span does not is mostly-FN. There
are no exceptions in either direction except one seed on NEXSTAR.

Representative misses, with the gold span the model had in front of it:

- `TURNKEYCAPITAL,INC_07_20_2017-EX-1.1-Strategic Alliance Agreement` —
  gold: *"The term of this Agreement is twenty-four (24) months."*
- `ULTRAGENYXPHARMACEUTICALINC_12_23_2013-EX-10.9-SUPPLY AGREEMENT` —
  gold: *"This Agreement shall become effective on the date of its execution and
  shall remain in force for three years (the \"Initial Term\")."*
- `HOLIDAYRVSUPERSTORESINC_04_15_2002-EX-10.13-ENDORSEMENT AGREEMENT` —
  gold: *"…the term of this Agreement shall be three years, commencing on the
  date of this Agreement and expiring on the third anniversary date of this
  Agreement (the \"Termination Date\")."*
- `MPLXLP_06_17_2015-EX-10.1-TRANSPORTATION SERVICES AGREEMENT` —
  gold: *"The Agreement shall continue through the project's in-service date and
  for a period of fifteen (15) years after the project's in-service date
  (\"Initial Term\")."*

And the hits, for contrast — same shape of sentence, one calendar date inside:

- `ADUROBIOTECH,INC_06_02_2020-EX-10.7-CONSULTING AGREEMENT(1)` —
  *"This Agreement shall begin on the Effective Date and shall continue until
  December 31, 2020, unless extended or earlier terminated."* → extracted, 6/6.
- `KINGPHARMACEUTICALSINC_08_09_2006-EX-10.1-PROMOTION AGREEMENT`, 36,199
  contract tokens, the longest in the split — *"…shall continue … until June 27,
  2011 (the \"Term\")."* → extracted, 5/5.

**78% of gold-present Expiration Date contracts in `harness_val` (25 of 32)
express the term without a calendar date.** That is the convention the model is
not following, and it is why a constant "present" beats the model 0.895 to
0.317.

### 1.2 The model says why, in its own words

The reasoning traces are unambiguous and nearly formulaic. Every quote below is
verbatim from `reasoning_content` in the trace store.

`MPLXLP…TRANSPORTATION SERVICES AGREEMENT`, C2 seed 0 — the model finds the
clause, then reaches for `w06`:

> "The initial term expires 'fifteen (15) years after the project's in-service
> date'. … There is no specific calendar date for the expiration of the initial
> term, only a duration relative to the in-service date. — Principle [w06]:
> Claim absence when the document does not state the specific fact the target
> asks for. — The target asks 'On what date will the contract's initial term
> expire?'. … Since the in-service date is not a fixed date in the document, I
> cannot extract a specific date."

`HOLIDAYRVSUPERSTORES…`, C2 seed 1 — it computes the right answer and rules
absent anyway:

> "It says 'third anniversary date'. — Agreement Date: March 20, 2002. —
> Expiration Date: March 20, 2005. — The text says 'expiring on the third
> anniversary date'. It does not explicitly state 'March 20, 2005'. … Principle
> w06: 'Claim absence when the document does not state the specific fact…'. Does
> the document state the specific fact (the date)? It says 'expiring on the
> third anniversary date'. It does not calculate the date."

`CORIOINC_07_20_2000-EX-10.5-LICENSE AND HOSTING AGREEMENT`, C2 seed 1:

> "Effective Date: October 29, 1999. — Calculation: 5 years from Oct 29, 1999 =
> October 29, 2004. — Does the text explicitly state the expiration date? No, it
> states the term length ('five (5) years') and the start date. — Principle w06:
> Claim absence when the document does not state the specific fact the target
> asks for, even where it states a neighbouring fact that plausibly stands in
> for it."

`ORBSATCORP_08_17_2007-EX-7.3-STRATEGIC ALLIANCE AGREEMENT`, C2 seed 0 — the
clearest statement of the rule the model has invented:

> "If only a duration is given, often it's classified as Absence of specific
> Expiration Date… If the text says '12 months', I cannot extract a specific
> date. Is it Absence? … Principle [w06] says 'Claim absence when the document
> does not state the specific fact the target asks for…'. A duration is not a
> specific date. So Expiration Date should likely be Absence."

`NEXSTARFINANCEHOLDINGS…`, C2 seed 0:

> "It gives a formula ('seventh anniversary'). … Since the text does not
> explicitly state the calendar date … but relies on calculation ('seventh
> anniversary'), strictly speaking, the *date* is not explicitly verbatim…"

This is not a model that has failed to understand Expiration Date. It is a model
resolving a genuine ambiguity — *is a clause that fixes the date by computation
responsive to a target that asks for the date?* — the wrong way, consistently,
and citing a principle while doing it.

### 1.3 `w06` is the proximate cause, and it is out of scope

`w06` declares `scope: [Agreement Date]`, and `render_principles` prints
`(absence; applies to: Agreement Date)` in the prompt. C3 citation counts by
target:

| target | decisions citing `w06` (of 120) |
|---|---|
| **Expiration Date** | **57** |
| Most Favored Nation | 42 |
| Source Code Escrow | 41 |
| Minimum Commitment | 39 |
| Volume Restriction | 37 |
| … | … |
| **Agreement Date** (its actual scope) | **9** |

`w06` is cited **six times more often outside its scope than inside it**, and
its single largest firing target is the one category it demonstrably damages.
On the 63 C3 Expiration Date false-absents the citation distribution is
`w06` 43 · `w01` 12 · `w10` 3 · `w04` 1.

Two things follow, both for inv 006:

- **Declared scope in the prompt does not constrain citation.** This is a
  harness-level finding independent of Expiration Date and it bears directly on
  H4: a confusion matrix over cited ids will be contaminated by out-of-scope
  citation unless scope is enforced rather than announced.
- **`w06` should be measured as a candidate for removal, not only for
  addition.** It already carries `provenance_axis: sources_contradict`, a
  `critic: drop` verdict, gold contradicting it at 151/160, an applicability
  checker that fires on 1 of 480 decisions, and Tyler's own note "seems right,
  but doesn't appear very often." It appears constantly. It is just doing so
  where nobody measured it.

### 1.4 The alternatives, tested and rejected

**Position — rejected.** Relative offset of the first gold Expiration Date span
in the contract text does not separate hits from misses once span kind is fixed.
Calendar-date contracts that were extracted sit at relative offsets 0.039 to
0.663; duration contracts that were missed sit at 0.015 to 0.797. The
false-absent at offset 0.015 (`BLACKSTONEGSO…`, first 2% of the document) and
the true-positive at 0.663 (`NETGROCERINC…`) are decisive on their own. The
group medians differ (0.127 vs 0.482) only because the two populations differ.

**Length — rejected.** False-absent rate over gold-present decisions, by
contract-token quartile:

| quartile | tokens | n | FN rate |
|---|---|---|---|
| q1 | 715–3,650 | 41 | 0.83 |
| q2 | 3,650–6,428 | 41 | 0.73 |
| q3 | 6,428–11,822 | 41 | 0.80 |
| q4 | 11,822–36,199 | 41 | 0.85 |

Flat. The **shortest** contract in the split (`NETZEEINC…`, 715 tokens) is a
false-absent, and the **longest** (`KINGPHARMACEUTICALS…`, 36,199 tokens) is a
true-positive. This is the same flatness §8 of the C2/C3 review reports for
presence F1 across a 100× length range.

**Confusion — rejected.** I checked all 519 non-Expiration-Date decisions on the
25 false-absent contracts for a predicted span overlapping the gold Expiration
Date text. **Zero overlaps.** The model does not re-file the term sentence under
Agreement Date or anything else; it simply emits nothing. (Note that Renewal
Term and Effective Date are not in the 12-category subset, so the two most
natural confusion sinks were not available to it — but the sentence did not go
anywhere else either.) With FP = 0 for the category, this is pure under-claiming,
not misrouting.

---

## 2. Why this is a principle and not a description fix

The study's line: the task definition says *what decisions over what targets*;
principles govern *how hard calls get made*. Three tests, all pointing the same
way.

**Does the model understand the target?** Yes, demonstrably. It finds the term
clause on every miss, quotes it, and in most cases computes the correct expiry
date before ruling absent. A model that misunderstood the target would look for
the wrong text or find nothing; this one narrates the right text and then
declines it.

**Is the printed definition wrong?** No. "On what date will the contract's
initial term expire?" is CUAD's own verbatim Description (D-8), and it is
accurate. What it omits is not a fact about the target but a **convention about
how far the annotators went to answer it** — they mark the clause that fixes the
date, and let the date follow. That is annotation practice diverging from
documented definition, which is precisely the cell D-23 built the provenance axis
to hold, and precisely `w07`'s situation ("the documentation is NARROWER than
practice … a model applying the printed definition literally under-extracts").

**Does the set already treat rules of this shape as principles?** Yes. `w03`
("Governing Law covers only a clause designating the substantive law; venue,
forum, jurisdiction-consent and arbitration clauses are not responsive") is a
pure statement about the extension of a target, is grounded in the Handbook, and
is the *one* record in the working set with `checker_status: usable`. If `w03`
is a principle, "a term stated as a duration answers the Expiration Date target"
is a principle.

And the cost of getting it wrong is asymmetric and known. **D-25** removed the
`Answer Format` hint from the prompt with an explicit rationale — *"answer
granularity is business logic and belongs to a principle (w01), not to the task
definition. The task definition stays neutral on granularity so w01 has
something real to do."* That rationale is recorded in `harness/envs/cuad_env.py`
in the code that drops the column. Writing the duration convention into the
Expiration Date description would be the same hint reinstated under a different
name, would pre-solve the hard call before `w06` and its replacement can be
compared, and would move ~132 decisions of headroom out of inv 006's reach and
into C1's baseline.

### The one task-definition change that would be defensible, and why I recommend against it now

There is a real framing tension, and it is worth stating so it is not
rediscovered later. `FRAMING` asks the model to "extract every verbatim span of
the contract that the category covers," while each target line is an
**interrogative asking for a value** ("On what date…"). The model reads the
question form literally — "the question asks for the date; I cannot produce a
date; therefore absence" — and nine of the twelve targets are Yes/No questions
where the same literal reading would be nonsense.

The content-free fix would be a single global sentence: *the target definitions
are questions that identify a class of clause, and a decision is an extraction
whenever the contract contains a clause responsive to that question, even where
the literal answer must be inferred from it.*

I do not recommend making it before inv 006, for one reason: that sentence
resolves this hard call, `w06`'s hard call, and part of `w01`'s, for all twelve
targets at once. It is a strictly larger intervention than the principle, in the
same direction, and it would make the principle unmeasurable. If Tyler wants it,
it should be run as its own recorded prompt version with a before/after on C1 —
not slipped in as a wording repair.

---

## 3. Proposal — candidate record, **not** added to `working_set.yaml`

Proposed for Tyler's review and for empirical selection under D-22. Id `w11` is
a placeholder.

```yaml
- id: w11
  statement: >
    A target that asks for a date is answered by the clause that fixes that
    date, whether the clause states it as a calendar date or fixes it as a
    duration, an anniversary, or an offset from a named event — "three years
    from the Effective Date" answers an expiration target as fully as
    "December 31, 2020" does. Absence is claimed only where the contract fixes
    no such point at all, not where it fixes the point by a computation the
    contract leaves unperformed.
  trigger_guidance: >
    Consider whenever you have found the clause that governs a target's date and
    are about to rule absent because the clause names a period rather than a
    date. Ask whether the contract determines the date — not whether it prints
    it. If you can say what the date depends on, the clause is responsive; if
    you cannot say even that, the target is absent.
  type: disambiguation
  scope: [Expiration Date]
  provenance: [data_mined]
  provenance_axis: data_only
  provenance_axis_note: >
    Corroborated in gold, not in the printed definition. The CUAD Description
    reads "On what date will the contract's initial term expire?" and the
    Answer Format column reads "Date (mm/dd/yyyy) / Perpetual", so a literal
    reading of the documentation supports the OPPOSITE rule. Practice does not:
    25 of 32 gold-present Expiration Date contracts in harness_val (78%) carry
    no calendar date in the gold span, and the median gold span is 199
    characters — a term sentence, not a date. Whether the Atticus Handbook's
    Term chapter documents this is not yet checked and should be, since it would
    move the axis from data_only to both. This is w07's situation with the sign
    unchanged: documentation narrower than practice, model under-extracts.
  conflicts_with: [w06]
  conflict_note: >
    w06 as written directs the opposite call and the model follows it: 43 of the
    63 C3 Expiration Date false-absents cite w06 by id, despite w06 declaring
    scope [Agreement Date]. w06 and w11 must be selected against each other, not
    added independently.
```

### Checker sketch (D-21 separable, D-24 compliant)

**Applicability — instance-only, reads no gold.** The decision's target is
Expiration Date, **and** the contract contains at least one clause that fixes
the end of the agreement's term by duration, anniversary, or named event without
stating a calendar date. Nothing here reads the decision's own gold, its
`is_impossible` flag, or any other category's gold, so it cannot fail D-21 by
the mechanism that sank 13 of 23 pilot checkers.

This is a **semantic** condition and D-24 says a regex should not be asked to
carry it, so it belongs in the LLM-assisted applicability lane already built at
`principles/applicability/` under D-27 (`gold_visibility: none`, labeler pinned,
frozen to file, spot-checked). I ran a deliberately naive regex proxy as a floor,
and it behaves exactly as D-24 predicts:

| pre-model 2×2 (regex proxy, 40 Expiration Date decisions) | gold present | gold absent |
|---|---|---|
| applicable | 18 | 1 |
| not applicable | 15 | 6 |

Separability is technically satisfied — the off-diagonal is non-empty — but at
n=1 it is thin, and the proxy misses 7 of the 25 target contracts (recall
~72%) while the LLM labeler would be reading for the actual condition. **Use the
LLM lane; report the regex comparison alongside it, as `compare_regex.py`
already does for w01–w10.**

**Compliance — decision-scoped, programmatic, no judge.** On an applicable
decision, the record FAILS if `decision_kind == "absence"`. That is a function of
model output only and needs no LLM, so it stays inside D-4. Note that this makes
compliance *close to* correctness on the applicable subset, which is the honest
reading: the principle's whole content is "do not claim absence here." It still
passes D-21, because applicability is decided without gold and a model can fail
the checker while gold is absent (the off-diagonal cell above) and pass it while
producing a wrong span. Flag it in the record rather than hide it — this is a
record whose compliance signal is weak and whose *answer* signal is strong, which
is exactly the case D-22's two-tier split was written for.

### Footprint estimate on `harness_val`

- **Applicability:** ~19–26 of 480 decisions (4.0%–5.4%), all inside a single
  category. Comparable to `w03` (21/480) and better-founded.
- **Decisions it would touch in this run:** **133** scored Expiration Date
  decisions across 26 contracts — every one of them currently a false-absent.
- **Ceiling if fully effective:** Expiration Date presence recall 0.195 → ~1.00
  with precision unchanged (FP = 0 today), i.e. presence F1 0.317/0.337 → ~1.0,
  and micro presence F1 across all twelve categories roughly 0.81 → ~0.90 from
  this record alone. **That ceiling will not be reached** — see the caveat below
  — but it is by a wide margin the largest single lever visible in the study.

### Caveat that must travel with the proposal: `w01` will fight it

Fixing the presence call exposes a span-shape problem immediately. `w01`'s
exception clips "the date and party categories" to the minimal value. On
`harness_val` the median gold **Agreement Date** span is 17 characters — the
exception is right there. The median gold **Expiration Date** span is **199
characters** (min 54, max 1,243) — it is a sentence, and the exception is wrong
there. The `w01` judgement-call note already flags that the exception's
membership was decided by drafting rather than measurement ("Flagged for Tyler:
if he meant jurisdictions to be exempted, this limb needs re-deciding against
that evidence"); Expiration Date is the second member that needs re-deciding,
with the measurement now in hand.

So the honest prediction is: `w11` converts ~132 false-absents into true
positives with poor span F1, unless `w01`'s exception is simultaneously narrowed
to Agreement Date (and Parties, when in subset). **Test them as a pair.** This
is a second, independent argument for the principle route — a task-definition
patch fixes the presence call and leaves this landmine buried.

---

## 4. Volume Restriction, briefly — and it is *not* the same verdict

Much smaller and much messier: 9 gold-present decisions across 4 contracts,
1 TP (C2) / 0 TP (C3), plus 10 false-presents across 5 contracts in each arm.
Both error directions are live, so no single rule fixes it.

**The gold is idiosyncratic.** The four present contracts:

- `CHINARECYCLINGENERGYCORP…` — a two-tier energy fee schedule (0.40 RMB/KWH up
  to 800M KWH, 0.20 above). The model **extracted both spans exactly** and still
  scored 4 FN / 1 TP across seeds, i.e. it is inconsistent across seeds, not
  wrong about the clause.
- `GOCALLINC…` — *"shall provide a minimum of 100,000 up to 500,000 pagers…"* —
  a supply band, which under `w08`'s direction test reads as a floor
  (Minimum Commitment) at least as much as a ceiling.
- `PharmagenInc…` — *"In the event the Production Session exceeds eight (8)
  hours … will negotiate in good faith additional compensation"* — a
  renegotiation trigger, not a fee increase.
- `MPLXLP…` — a prepaid-credit mechanism and a 90% expansion-capacity cap.

**The false-presents read as more faithful to the printed definition than gold
does.** The definition is *"Is there a fee increase or consent requirement, etc.
if one party's use of the product/services exceeds certain threshold?"* The model
offered, and gold rejected:

- `BLACKSTONEGSO…` — *"Additional fees will apply if the annual allowances below
  are exceeded"* — a textbook match, gold-absent.
- `XLITECHNOLOGIES…` — *"Special pricing for large orders and/or custom orders
  will need written approval (email) from BOSCH"* — a consent requirement above a
  size threshold, gold-absent.
- `NETGROCERINC…` — per-click fees "in excess of [*]" — gold-absent.
- `ArtaraTherapeuticsInc…` — tiered royalties and sales-milestone payments above
  Net Sales thresholds — gold-absent (and correctly Revenue/Profit Sharing).

**Diagnosis:** this is a boundary dispute between the printed definition and
annotation practice running in *both* directions at once, on a category with **no
Handbook chapter at all** (0 of 95 pages, per `w08`'s cross-source entry). It is
the failure mode the study pre-registered when it took the Savelka trio, and
`w08` already scopes to exactly this pair — but `w08`'s checker fires on 75% of
in-scope decisions and cannot localise anything.

**Recommendation:** do **not** propose a principle for Volume Restriction off
this run. n = 9 present decisions on `harness_val`, one of the four contracts is
a seed-instability case rather than a comprehension case, and the false-present
side would need a rule that contradicts CUAD's own printed definition — which
needs corpus evidence at `principle_train` scale before anyone writes it down.
The right next step is the `w08` checker tightening D-24 already calls for, run
on `principle_train`, not a new record. Expiration Date is where the return is.

---

## 5. What I would do next, in order

1. **Take the verdict to Tyler**; `w11` is a proposal, nothing was written to
   `principles/working_set.yaml`.
2. **Pair `w11` against `w06` in the first inv 006 A/B on `principle_train`.**
   They contradict each other on the same decisions and `w06` currently wins by
   default. Selecting them independently would measure noise.
3. **Narrow `w01`'s date-category exception to Agreement Date** as a second arm,
   because `w11` alone converts presence errors into span errors.
4. **Report the out-of-scope citation finding (§1.3) as a harness result.**
   Declared scope does not constrain what the model cites; H4's confusion matrix
   needs scope enforced, not announced.
5. **Check the Atticus Handbook's Term chapter for a documented duration rule.**
   If it exists, `w11` moves from `data_only` to `both` and becomes the
   strongest-provenance record in the set.

---

*Written by Claude Code. Every number is recomputed from
`data/traces/2026-08-16-c2c3-harness-val/` (`trials.jsonl`, `decisions.jsonl`,
and the gzipped trace store), gold from `data/raw/CUADv1.json` restricted to
`data/processed/splits/harness_val.txt`. All reasoning quotes are verbatim from
`reasoning_content`. No file outside this one was created or modified.*
