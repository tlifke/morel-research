# Framework drift — evidence pack

_Assembled 2026-07-20 by Claude Code, at Tyler's request, as raw material for a
writeup. **This is evidence and observation, not prose.** The argument and the
words are Tyler's to write._

State captured **before** any status corrections were applied, so the numbers
below describe the framework as it actually stood after ~7 weeks of work and
~5 weeks of absence. Machine-readable snapshot: `scripts/../drift-snapshot.tsv`
(regenerable; see "How this was measured").

---

## 1. The claim

The repo's organizing promise is in `CLAUDE.md`: every `study.md` and
`investigation.md` carries frontmatter declaring `status`, and `lineage.yaml` is
**derived** from that frontmatter by `scripts/update_lineage.py`. The intent is
that a fresh session — human or agent — can read the derived index and know
where everything stands.

That promise failed. Not partially: the index was confidently wrong about the
majority of the corpus.

## 2. The measurement

28 documents carry frontmatter (6 studies, 22 investigations).

| Metric | Count | Share |
|---|---|---|
| Documents whose declared `status` did not match their own contents | 13 | 46% |
| Documents marked `planned` that contained completed, analyzed experiments | 5 | 18% |
| Documents whose `updated:` predated their own newest dated content | 10 | 36% |
| Documents ever marked `complete` | 4 | 14% |
| Documents whose true state was **undecidable from the text** | 7 | 25% |

The five filed as `planned` while holding finished work:

| Path | Declared | Actually contained |
|---|---|---|
| `studies/002-principle-bootstrapped-difficulty` | `planned` | a 4,392-call full-corpus experiment |
| `studies/003-automated-w2s-replication` | `planned` | 6 investigations; a 3-dataset replication; real PGR |
| `003/investigations/005-split-host-researcher` | `planned` | 984 lines, 13 findings, 3 formal Decisions |
| `005/investigations/002-rich-harness` | `planned` | a 120-run 6-arm factorial, analyzed twice |
| `005/investigations/003-process-judges` | `planned` | two judge-validation rounds |

Worst single case: `studies/003-automated-w2s-replication/study.md` declared
`updated: 2026-05-23` while its own body referenced investigation 004/005
outcomes and a 2026-06-15 date — roughly three weeks of drift inside one file.

## 3. Drift was not only in frontmatter

The prose bodies drifted independently, which matters because it removes the
easy fix ("just lint the YAML"):

- `studies/003/study.md` listed investigation 001 as "**Planned (next up).**"
  That child's own document says "**Verdict: GREEN.**" and is marked `complete`.
- `studies/000/study.md` described both children as "In-progress" when 002 was
  `complete`.
- `studies/005/study.md` listed inv 003 as "real-W2S desktop transfer." The
  actual inv 003 is process-judges. Inv 004 was not listed at all.
- `003/inv-002` still carries the live subheading "### Phase 2 — three datasets
  at epochs=5 (in progress)" directly above a line reading "**Status:** Phase 2
  complete".
- `001/inv-006` has its `## Forward-looking`, `## Things to flag`, and
  `## Limitations` sections duplicated verbatim (lines ~357–424).

So three layers — frontmatter, derived index, and prose — disagreed with each
other and with the data on disk.

## 4. The structural cause, as far as the artifacts show it

`000/investigations/001-initial-scaffold` **predicted this failure on day one**,
in its own Limitations section:

> "No CI / hooks wired up — humans must remember to run `update_lineage.py` and
> `plot.py` after edits."

and listed as a follow-on: "frontmatter validator (lint) … pre-commit hook to
run `update_lineage.py` automatically."

A `scripts/hooks/pre-commit` exists on disk. No frontmatter validator does. The
mechanism that would have caught the drift was scoped, written down, and never
built — while the ceremony it was meant to protect was performed 28 times.

**And it is itself an instance of the drift** (Tyler, 2026-07-20): every artifact
`000/inv-001` set out to build was in fact delivered, and the investigation was
finished. It simply was never marked `complete` — it sat at `in-progress` from
2026-05-11 until 2026-07-20, its `updated:` never moving, closed out only during
this reconciliation. The investigation that *created* the status convention, and
that *predicted in writing* the failure to maintain it, was the first document to
exhibit it. If the writeup wants one example that carries the whole argument,
this is the candidate.

Observation worth testing against your own memory: **status is the one field
that must be written at a moment when there is no reason to write it.** Every
other part of the framework is updated as a side effect of doing the work —
you add results because you have results, you add a log entry because something
happened. Closing out a status happens *after* the interesting part is over,
usually at the same moment a successor investigation is becoming interesting.
The five `planned`-but-done documents are all cases where a successor existed.

## 5. The re-entry cost (Tyler's account, 2026-07-20)

> "The actual status of experiments, meant to be obvious on starting up a new
> Claude Code session, instead were unreliable. Coming back after a month away
> I'm genuinely far away from understanding of where we left things."

Worth noting what *did* survive the month, since the contrast is the finding:

- **Held up:** the dated log entries inside investigations; the numeric results;
  the rendered run/trace reports (`report.html`, judge reports); `HANDOFF.md`,
  which was written specifically as a re-entry document and was accurate.
- **Failed:** frontmatter `status`, `updated:`, the derived `lineage.yaml`, and
  the "Investigations" lists inside `study.md` files.

The pattern: **artifacts generated as a byproduct of doing the work stayed
true; artifacts requiring a separate act of bookkeeping went stale.** Every
failed item is in the second category. `HANDOFF.md` is the interesting
exception — a bookkeeping artifact that survived, plausibly because it was
written once under real pressure (context exhaustion) rather than maintained
continuously.

## 6. The sharper version of the claim

"We didn't keep the metadata updated" is a discipline story and is not very
interesting. The more defensible reading, which the evidence supports:

The framework was designed to make research state **legible to a fresh agent**.
It instead produced state that was *plausibly formatted and wrong* — which is
worse than absent, because a fresh session (and, in fact, this one) will read
`lineage.yaml` and believe it. An empty field prompts a question; a stale field
suppresses one. The 7 undecidable documents are the second-order cost: by the
time anyone went back to reconcile, the information needed to close them out no
longer existed in the artifacts and had to be reconstructed by a human from
memory.

Possible framing for the writeup, unverified: this is the same failure the
research itself keeps finding — study 005's finding that rich scaffolding helps
a 4B and hurts an Opus-class model, and the recurring "the harness, not the
model" diagnosis. The framework here was the harness, the researcher was the
strong agent, and the scaffolding cost more than it returned. Do not assert
this without checking whether it actually holds; it is a tempting analogy and
tempting analogies are how one-pagers get wrong.

## 6b. The lineage graph was not actually a tree (Tyler, 2026-07-20)

> "The graphical nature of studies and investigations made actually showing the
> lineage complicated. We need better automated documentation practices."

The taxonomy assumes work nests: study → investigation. Real work crossed those
boundaries constantly, and the frontmatter had no good way to say so. Concrete
cases found while reconciling:

- `004/inv-002-judge-comparison` finished its question, but its stated
  follow-on ("test mid-tier judges") was executed by
  `005/inv-003-process-judges` — **a different study**. Nothing in either
  document's `status` can express "complete, because a sibling under another
  parent absorbed the remainder." That's precisely why it read as ambiguous.
- `001/inv-004-calibration-pilot`'s open items were satisfied by
  `001/inv-006`'s Cell C, but inv 004 never says so — the reader has to hold
  both documents at once to notice.
- `001/inv-007-axes-performativity` pivoted mid-flight and handed its
  reformulation to **study 002**, which did not yet exist as its parent.
- `003/inv-003` → `003/inv-004` → `003/inv-005` is a chain where each link's
  *failure* is the next link's scope.

The `related:` field exists but is untyped — it cannot distinguish "superseded
by," "absorbed remainder of," "failed into," or "see also." So the DAG was real
but unrepresentable, and the rendering problem follows from that: you cannot
draw a graph whose edges you never recorded. Note the asymmetry with §7 — the
*prose* handoffs were accurate in all 7 reconciled cases. The information
existed; the schema had nowhere to put it.

## 7. What the framework did buy

`003/inv-004-qwen-researcher-floor` is the strongest counterexample to the
drift story and should be in the writeup as such. Its stopping rule was
pre-registered with an explicit either-way clause:

> "iterate until the agent completes one end-to-end iteration with a valid
> `evaluate_predictions` submission … **OR** until 5 distinct patches have been
> tried without progress on that specific gate. **Either outcome is the
> result.**"

It stopped at patch 4, on protocol — "Per inv 4 protocol the budget is 5
patches max … A patch 5 would only re-test prompt variants on the same broken
substrate" — and handed a sharp, correct diagnosis to inv 005: prompt induction
at 4B is solved; substrate contention is the residual wall.

Why this matters for the argument: the bookkeeping that was **load-bearing at
the moment of doing the work** held perfectly. The pre-registered budget was
consulted, obeyed, and cited *while the work was live*. The same investigation's
`status` field, consulted by nobody at that moment, went stale. Same document,
same author, same week — the difference is whether the field had a job to do
during the work or only after it.

Also worth crediting:

Stated for balance; a writeup that only indicts is less credible.

- The investigation boundary genuinely worked as a *stopping* device. Study 003
  inv 004's pre-registered "5 patches then stop" budget fired as designed and
  prevented a tar-pit — the document says so explicitly ("Stopping at patch 4.
  Per inv 4 protocol the budget is 5 patches max").
- Successor handoffs are traceable. Every one of the 7 undecidable documents
  handed work to a *named* successor, and those pointers were accurate. The
  lineage was right about **shape** even where it was wrong about **state**.
- Pre-registered hypotheses (`005/inv-002` methods.md, C1–C7) let a negative
  result be reported as a result rather than a failure.

## 8. Forward-looking — design implications (Tyler, 2026-07-20)

Tyler's framing, recorded for the writeup's forward-looking section. These are
directions, not decisions; none has been tried.

**The governing principle**, from §5: bookkeeping that is optional goes stale;
bookkeeping that is mechanically part of doing the work stays true. So any
successor framework should aim to move status out of the "separate act"
category. Three candidate routes, not mutually exclusive:

1. **Tie bookkeeping to the process so it isn't optional.** Make status a
   by-product of an action you already take — e.g. an investigation cannot
   record results without declaring whether the stopping criterion was met.
   §7's evidence supports this: the pre-registered patch budget survived
   precisely because it was consulted mid-work.
2. **Automate the upkeep** — a GitHub Action (or pre-commit hook) that
   regenerates `lineage.yaml`, and, more importantly, *fails* when a document's
   `updated:` predates its own newest dated content, or when a `planned`
   document contains a Results section. Note this exact mechanism was named in
   `000/inv-001`'s follow-ons on day one and never built (§4) — so "we should
   automate it" is not a new insight, and the writeup should say why the second
   attempt would stick where the first didn't.
3. **New primitives rather than new discipline.** Tyler's example: *handoff
   with recursive agents solving subproblems and bubbling results up*. This is
   attractive because `HANDOFF.md` is the one bookkeeping artifact that survived
   (§5), and because bubbling-up makes the parent's state a *computed function*
   of its children rather than a hand-maintained claim — which would have
   prevented all five `planned`-but-done cases and, per §6b, could carry typed
   edges as part of the return value.

**Open question — is Claude Code the right substrate?** Tyler: *"something like
OpenCode which is more modifiable, or a fully custom harness, might be a better
approach."* The pull is that routes 1 and 3 both want control over the agent
loop itself — enforcing "you may not write results without closing status" is a
harness-level constraint, not something a `CLAUDE.md` convention can compel,
since conventions are exactly the optional bookkeeping that failed here. The
counter-pull is that a custom harness is a large build whose failure modes are
unknown, and this study's own repeated finding is that harness complexity has
scale-dependent costs. Unresolved; flagged as the main strategic fork.

Cross-reference: this is the same territory as study 005's harness-vs-training
question, but pointed at the *research process* instead of the researcher agent.
See the caution in §6 before leaning on that parallel.

## How this was measured

```bash
for f in studies/*/study.md studies/*/investigations/*/investigation.md; do
  # declared status + updated: from frontmatter
  # vs. max(YYYY-MM-DD found anywhere in body)
  # vs. git log -1 --format=%ad -- "$f"
done
```

Full table: `drift-snapshot.tsv` in the session scratchpad; regenerate against
any commit to get the drift as of that point.

---

## Things I made up that you should review

1. **The "byproduct vs. bookkeeping" split (§5)** is my framing, not something
   any document says. It fits all 28 cases I looked at, but I chose the
   categories after seeing the data — treat it as a hypothesis you find
   plausible, not a result.
2. **The `HANDOFF.md` explanation** ("survived because written once under
   pressure") is speculation. I did not check whether it was ever revised.
3. **§4's claim that status is structurally the hardest field** is an argument,
   not a measurement. The supporting observation (all 5 `planned`-but-done docs
   had successors) is real and checkable.
4. **§6's analogy to the study-005 harness finding** is the most load-bearing
   and least verified thing in this document. I flagged it inline for that
   reason.
5. **The 46% figure** counts a document as mismatched if the earlier audit
   proposed a different status than declared. That audit was itself an LLM
   reading the docs; the 7 undecidable cases show its judgment is not
   infallible. The 5 `planned`-but-done cases are unambiguous and would survive
   any reasonable recount; the softer 8 might not.
6. ~~I did not verify whether `lineage.yaml` propagated the wrong statuses.~~
   **Verified 2026-07-20 — it does.** `lineage.yaml` carries `status: planned`
   for `002-principle-bootstrapped-difficulty`, `005-split-host-researcher`,
   `002-rich-harness`, and `003-process-judges`. The derived index is wrong in
   exactly the way §1 claims; this one is safe to state as fact.
