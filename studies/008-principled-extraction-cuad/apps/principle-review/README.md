# principle-review

A local-only adjudication queue: load proposed records from YAML, work through
them one at a time, record a decision plus a mandatory written rationale, and
write the reviewed set back out to YAML.

Two record types ship today:

| `--record-type` | records | decisions | used by |
|---|---|---|---|
| `principle` (default) | candidate `Principle` records | accept / edit / reject / defer / unclear | inv 002 |
| `gold_audit` | one CUAD gold span | the gold-defect taxonomy + defer | D-15 noise floor |

The record schema is a declaration, not a hardcode — see "Reusing this app".

## Launch

```
uv run --project studies/008-principled-extraction-cuad/apps/principle-review \
  principle-review <path/to/candidates.yaml>
```

Run from the repo root; a browser tab opens at `http://127.0.0.1:8823/`.
With no path argument it loads the sample fixture in `fixtures/`.

Options:

| flag | default | meaning |
|---|---|---|
| `--reviewer` | `tyler` | stamped into every review block |
| `--db` | `<app>/state/review.sqlite3` | decision store |
| `--export` | `<source>.reviewed.yaml` next to the source | export target |
| `--port` | `8823` | |
| `--record-type` | `principle` | key in `review_app/record_types.py` |
| `--pairs` | auto-discovered next to the source | mined contrastive pairs, for inline evidence |
| `--footprint` | auto-discovered next to the source | empirical footprint artifact |
| `--no-browser` | | do not auto-open a tab |

Both sidecar files are optional and are re-read whenever their mtime changes, so
a footprint that lands mid-session appears on the next record switch without a
restart. Auto-discovery looks in the source file's directory for
`mined_pairs.jsonl` / `pairs.jsonl`, and for `footprint.{yaml,yml,json}`,
`footprints.*`, `principle_footprint*.*`.

Nothing leaves the machine: no auth, no CDN, no fonts, no outbound requests.
The whole UI is one inlined HTML file.

## Reviewing

Each record shows statement, trigger guidance, checker sketch, evidence
pointers, type, scope, provenance, and the proposer's model id / prompt
version / batch — everything needed to judge "is this rule real and
checkable" without scrolling around. Any field the record type doesn't declare
is still shown (in an "other fields" card) and still exported.

- **rationale is required on every decision, including accept.** The save
  button stays disabled until one is typed.
- **edit** opens the editable fields; saving stamps the verbatim prior value of
  *every* changed field into `review.edited_from`, as a map keyed by field
  name:

  ```yaml
  review:
    decision: edit
    edited_from:
      statement: "verbatim prior value"
      checker_sketch: "verbatim prior value"
  ```

  Unchanged fields are omitted, and the key is absent entirely when the
  decision is not `edit`. Per-field keys are what keep "sound rule, infeasible
  checker" distinguishable from "wrong rule" in the edit-rate analysis. An
  `edit` that changes nothing is rejected. When a field has been edited, the
  record view shows the model's original value directly beneath the reviewer's
  version.
  A legacy bare-string `edited_from` in an input file is accepted and coerced
  to `{statement: <value>}` on import.
- **reject** keeps the record in the file. Nothing is ever deleted.
- **defer** is a first-class decision (`d`, then a one-line reason): *the
  statement is understood, but it is not rulable yet* — more evidence, a
  footprint, or a decision made elsewhere is missing.
- **unclear** (`x`) is a separate first-class decision, added after round 1
  produced a record Tyler could only describe as "I have no idea what this
  means". It means *the statement itself is not comprehensible*, so there is
  nothing for evidence to bear on. That is a defect in the proposer, not a gap
  in the data, and the two must not be pooled: a high defer rate says the
  evidence pipeline is thin, a high unclear rate says the proposer prompt emits
  unreadable rules. `unclear` requires a rationale like every other decision,
  and the rationale should name the unreadable part.

  Mechanically it is kept separate everywhere:
  `pending_decisions` lists `defer` and `unclear` as two independent names (that
  tuple only governs the progress bar, which counts neither as resolved), the
  header breakdown prints every decision with its own count, and
  `/api/export` returns a `counts` map seeded with *every* declared decision, so
  `unclear` and `reject` appear as explicit `0` rather than being absent and
  read as unmeasured. `tests/test_roundtrip.py` pins that separation.
- `reviewer` and `date` are stamped automatically.
- Any already-reviewed record can be reopened and changed; every save is also
  appended to a `review_history` table, so decision churn is recoverable.

Keyboard: `j`/`k` prev/next, `u` next unreviewed, `i` focus rationale,
`ctrl+enter` save, `ctrl+e` export, `/` search, `esc` unfocus. Decision
hotkeys come from the record type and are listed in the sidebar
(`a`/`e`/`r`/`d`/`x` for principles; `c`/`m`/`n`/`s`/`b`/`x`/`o`/`d` for the
gold audit).

### Inline evidence

Round 1 rendered `evidence` as a chip reading `pair-0014` and nothing else, so
the evidence was unreadable without leaving the app. The `evidence` field kind
now resolves each cited id against the pairs sidecar and renders the pair in
place: a header line (`pair_id`, `kind`, similarity, same/different contract,
and a plain-English statement of what the contrast *is*), then the two sides
side by side. Each side shows its gold category as a badge, whether it is an
annotated span or a contract where the category is ruled absent, the contract
id and character offsets, and the span text. The differing label is what is
made prominent, because the contrast is the entire evidential content of a pair:

| `kind` | what differs | how it renders |
|---|---|---|
| `cross_label` | the gold **category** | both category badges outlined in accent |
| `present_absent` | the gold **status** | the absent side's badge is red and reads `category marked ABSENT in this contract` |

Where the miner expanded a short span before matching (`context_expanded`), the
matched window is shown underneath the span text and labelled as such, so a
match driven by surrounding boilerplate is visible rather than hidden.

Evidence entries that are not pair ids — the Atticus Handbook citations carried
by the `atticus_guidelines` principles — render as plain citations, unchanged.
A `pair-NNNN` that does not resolve renders as a red "not in the pairs index"
line naming the file that was searched, rather than silently disappearing.

Pairs file format: JSONL (or a JSON/YAML list, or a mapping keyed by id), one
object per line, indexed on `pair_id`. Each object carries `kind`, `similarity`,
`same_contract`, and `left`/`right` blocks with `contract_id`, `category`,
`span_index`, `start`, `end`, `text`, `match_text`, `context_expanded`,
`gold_status`. Everything is optional; missing keys degrade to `—`.

### Field help

Round 1 also produced "I don't know what a checker sketch is or what I'm being
asked to judge about it". A `Field` may now declare `help`: longer text behind a
`what is this?` button next to the field label, open/closed state persisted in
`localStorage` so it can be read once and dismissed for the rest of the session.
`checker_sketch`, `evidence` and `footprint` carry one. The checker-sketch help
states what a sketch *is* (a programmatic test computed from the contract plus
its gold annotations, no human judgement at scoring time) and names the only two
questions being asked of it — is it implementable against the offsets we already
have, and is it faithful to the statement — plus the rule that a sound rule with
a broken checker is an `edit`, not a `reject`.

### Empirical footprint

The footprint is the round-2 primary evidence: measurements from actually
implementing a principle's checker and running it over a split. It renders as a
full-width, visually weighted block directly under the statement and above every
other card — headline numbers as large stat tiles, then a distribution bar
chart, then examples. Applicability at or beyond 2%/98% and an absolute
discrimination lift under 0.05 are flagged amber in place, because "fires on
nothing" and "fires on everything" are the two ways a principle can read well
and measure worthless.

It is **not** a record field: it is read from a sidecar keyed by principle id,
so the artifact can be regenerated without touching the candidates file. If a
record happens to carry its own `footprint` key, that wins. When neither exists
the block still renders, greyed, saying which principle has no measurement and
which file was searched — absence is stated, not hidden.

**The contract.** YAML or JSON, same shape either way:

```yaml
schema_version: 1
generated: '2026-08-16'          # optional
generator: {script: ..., version: ...}   # optional, free-form
split: dev                        # optional; population these numbers cover
population:                       # optional
  unit: gold span                 # what one unit is
  n_units: 732
  n_contracts: 61
principles:                       # required key; maps principle id -> footprint
  d05:
    status: ok                    # ok | not_implementable | error   (default ok)
    note: free text, one or two lines          # optional
    applicability:                # optional
      n_applicable: 143
      n_units: 732
      rate: 0.1954                # optional; derived from the counts if absent
    distribution:                 # optional
      by: category                # label for what the rows are keyed on
      rows:
        - {key: Governing Law, n_applicable: 40, n_units: 55, rate: 0.7273}
      concentration:              # optional; any scalar keys, rendered as chips
        n_contracts_with_any: 48
        n_contracts: 61
        max_per_contract: 12
        median_per_contract: 2
    discrimination:               # optional
      metric: pass rate on gold spans vs sampled distractors
      pass_rate_positive: 0.86
      pass_rate_negative: 0.21
      lift: 0.65                  # optional; derived as positive - negative
      n_positive: 143
      n_negative: 401
    examples:                     # optional; any keys, rendered as a table
      - {verdict: applies, contract_id: ..., category: ..., text: ..., note: ...}
```

Rules the producer can rely on:

- Every key except the top-level `principles` map is optional, and every
  principle entry may carry any subset of the three blocks. A principle that
  could not be implemented is a legitimate footprint: `{status:
  not_implementable, note: ...}` renders as a red status pill plus the note.
- Rates are fractions in `[0, 1]`, not percentages; the UI formats them.
- Ids must match the candidates file exactly. Unmatched ids are ignored
  silently; principles with no entry render the "none measured" block.
- Unrecognised keys inside a principle entry are dumped verbatim under
  "other keys" rather than dropped, so an extra measurement is visible before
  the renderer knows about it.
- A top-level mapping of `id -> footprint` with no `principles:` wrapper is also
  accepted and normalised on load.

`fixtures/footprint.yaml` and `fixtures/mined_pairs.jsonl` are demo sidecars for
`fixtures/candidates.sample.yaml`; they are auto-discovered when the app is
launched with no source argument.

Filters: decision state, plus one dropdown per declared facet (principles:
provenance, type, proposer model; gold audit: category, split, stratum) and a free-text search. Header shows
`n reviewed / n total` with an accept/edit/reject/defer breakdown; the bar
tracks *resolved* records, so defers and unclears correctly read as not-done.

### Accept-by-default

Round 1 closed at 11 accept / 5 defer / 0 edit / 0 reject over 16 records. That
is a rate worth watching but not one the tool should try to move: an interface
that pushes toward rejection is as much a measurement error as one that pushes
toward acceptance, and it corrupts the same number. Only direction-neutral
changes are implemented.

- **The decision breakdown always shows every decision, including zeros.**
  It previously hid decisions with a count of 0 once a record type declared more
  than four, which would have hidden exactly the `reject 0` that makes the
  pattern visible. Showing all counts is symmetric — it surfaces a run of
  rejects as readily as a run of accepts.
- **`rationale first`** (header checkbox, **off by default**, remembered in
  `localStorage`). With it on, the decision buttons stay disabled until a
  rationale has been typed, so the reason is written before the verdict is
  picked rather than justified after it. This is direction-neutral: it applies
  identically to all five decisions and reorders two steps that were both
  already mandatory. It is off by default because it is a real change to the
  reviewer's flow and that is the reviewer's call, not the tool's.
- **`unclear`** removes the pressure to accept a statement one cannot parse.

Deliberately **not** implemented, as biased or unmeasurable:

- *Surfacing the strongest counter-evidence next to the accept button.* Nothing
  in the record marks any evidence as counter-evidence, so the app would have to
  pick — and any heuristic for "strongest counter-evidence" is the tool arguing
  for rejection with a mechanism the writeup cannot describe. Side-by-side pair
  rendering already puts the disconfirming half of every contrast on screen; the
  footprint block is the honest version of this, because it can contradict the
  proposer's argument with a measurement rather than with emphasis.
- *A running accept-rate readout framed as a rate.* The raw counts are already
  in the header. Rendering them as "you have accepted 92%" adds no information
  and converts a tally into a target — the reviewer starts managing the number.
  Counts inform; a rate with an implied acceptable value nudges.
- *Making accept harder than the other decisions* (extra confirmation, a longer
  minimum rationale, cooling-off). Asymmetric friction manufactures the result
  it is trying to detect.

## Export

`export yaml` (or `ctrl+e`) writes every record — reviewed or not — to the
export path in the schema investigation 002 specifies, top-level keys in
`id, statement, trigger_guidance, type, scope, provenance, proposer, evidence,
checker_sketch, review` order. Export is a full rewrite of a separate file; the
source candidates file is never modified. Locking (the accepted + edited subset
→ `principles/locked-YYYY-MM-DD.yaml`) is deliberately **not** in this app:
Claude proposes, Claude does not lock, and neither does this tool.

Round-tripping is lossless: import → export with no decisions reproduces the
input content exactly, modulo key order and YAML line wrapping. Unknown fields
are preserved verbatim.

## Storage

SQLite at `state/review.sqlite3` (WAL). SQLite rather than writing YAML on
every keystroke because a half-finished session must never corrupt the
candidates file, and because a crash mid-typing must not lose a rationale:

- `queues` — one row per imported source file
- `records` — `source_json` (verbatim as imported) + `edits_json` (per-field
  overrides). The source is never mutated, so `edited_from` is derived at
  export time by diffing edits against the source, not stored as its own
  truth.
- `reviews` — current decision per record
- `review_history` — append-only, every save ever made
- `drafts` — rationale/edits autosaved ~400 ms after typing stops, and again
  on tab close. Cleared once the decision is saved. Unsaved drafts show a
  `draft` pill in the queue list and reload with the record.

Re-running the app against an updated candidates file re-imports it: new
records appear, existing decisions survive, changed source text is refreshed.
Decisions are keyed on the record `id`, so ids must be stable.

## Gold-span audit (`gold_audit`)

Implements D-15: CUAD gold is left uncorrected and its defect rate is measured
and reported as a limitation.

**Draw the sample.**

```
uv run --project $APP $APP/scripts/sample_gold.py --n 120 --seed 20260815
```

Writes `audits/gold_audit_sample.yaml` (override with `--out`). The record
unit is **one gold span**, not one contract-category: every defect in the
taxonomy is a property of an individual span, and the reported rate needs a
span denominator. Relational defects stay judgeable because each record also
carries its sibling spans in the same category (where artifact-split shows up)
and any spans of *other* categories that are identical to, nested in, or
overlapping it.

Sampling design: population is every gold span of the 12 subset categories in
**dev + holdout only** — the splits whose scores the noise floor bounds; the
script refuses any other split. Allocation is equal-per-category, capped by
availability, with the remainder redistributed to categories that still have
spans, so rare categories (Most Favored Nation has 7 spans in the population,
Source Code Escrow 12) are represented rather than drowned. Draws use
`random.Random(seed)` over a deterministically sorted population, so
`--seed` reproduces the sample exactly. The output header records seed,
sampler version, splits, a hash of each split file, requested vs drawn n,
population size, per-category allocation and availability, and the CUAD
attribution; every record repeats the seed, sampler version and stratum in its
own `sample` block, so provenance survives export.

**Review it.**

```
uv run --project $APP principle-review audits/gold_audit_sample.yaml \
  --record-type gold_audit
```

The span is shown in place, highlighted inside its surrounding contract text
(`--context` chars each side, default 700) — a span cannot be judged without
what sits around it. Decisions are the defect taxonomy: `clean`,
`mislabeled`, `labeled_by_neighbourhood`, `artifact_split`, `boundary_jitter`,
`redaction_dependent`, `cross_category_overlap`,
`inconsistent_across_duplicates`, plus `defer`. Rationale is
required as always. Nothing is editable: gold is not corrected, only
characterized.

**Near-duplicate inconsistency.** CUAD contains near-twin contracts — an
agreement and its amendment, two filings of substantially the same document —
where an identical clause is annotated in one and left unannotated in the
other. The span is fine; the corpus disagrees with itself, usually in the
*absence* labels. To make that adjudicable, the sampler searches all 510 CUAD
contracts (including ft_train, since a twin can live anywhere) for the gold
span's passage, whitespace-normalized and exact, and attaches every contract
where it recurs together with that contract's label for the same category:

| twin_label | meaning |
|---|---|
| `annotated` | the twin annotates this passage too — no disagreement |
| `marked_absent` | the twin rules the whole category absent (`is_impossible`) |
| `category_annotated_elsewhere` | the twin annotates the category, but not this passage — a **missing span**, not a missing category |
| `not_annotated` | the twin has no spans for the category and no absence ruling |
| `category_not_in_subset` | outside the 12-category subset |

The `category_annotated_elsewhere` label matters: it separates a whole-category
miss from a finer disagreement where both contracts agree the category is
present but only one annotates a given passage. Collapsing the two would have
overstated the severity of half the census.

Contracts excluded from ft_train by the INV1-D7 split-contamination fix are
**not** filtered out of the counterpart search — a twin removed for being a
duplicate is still evidence that the gold disagrees, which is exactly what this
class measures. They render with `split: excluded` and an `excluded_as` column
carrying the exclusion reason and which split the twin sits in.
Counterparts are ranked by document containment over 8-gram sketches, and
`n_contracts_with_passage` is surfaced so common boilerplate is obvious rather
than mistaken for a twin. Passages under 60 normalized characters are not
searched — short spans match by chance.

Document-level twin detection alone does **not** work: the NETGEAR
distributor-agreement / amendment pair that motivated this class has a document
containment of 0.095, well below any sane twin threshold, yet the
governing-law passage is byte-identical and the amendment marks the category
absent. Passage-first, document-similarity-as-context is the design that finds
it.

**Two detectors.** Exact matching is not enough — it can only find passages
that survived copying byte-for-byte, so its yield is a lower bound. The second
detector reuses the study's contrastive-pair miner
(`scripts/mine_contrastive_pairs.py`) by importing `Space`, `jaccard_block`,
`terms` and `chunk_text` directly: idf-weighted Jaccard over unigram+bigram
term sets, NFKC/lowercase/whitespace normalization, digits and redactions
folded to tokens. Its parameters come from `principles/pilot/mining_config.yaml`
and are not re-tuned here: `present_absent` threshold 0.20, `min_terms_per_unit`
8, `top_k_per_query` 1, and context expansion for spans under 120 characters
(which is what makes a bare Agreement Date matchable at all). No third
similarity metric was written.

Different floors govern the two detectors, because they carry different
evidential weight:

| | exact_normalized | fuzzy_idf_jaccard |
|---|---|---|
| match | byte-identical after whitespace normalization | idf-weighted Jaccard >= 0.20 |
| minimum unit | 60 normalized characters | 8 in-vocabulary terms (the miner's rule) |
| document-containment gate | none | >= 0.15 |

**The fuzzy detector needs the containment gate, and this is the tuning risk.**
The miner's threshold answers *"does a passage resembling category C exist
somewhere C is marked absent"* — a broader and different question than *"is
there a near-duplicate document with the opposite label"*. Ungated at 0.20 it
returns 22 candidates over dev+holdout, of which **17 have document containment
0.0**: unrelated contracts sharing legal boilerplate ("This Agreement may not be
assigned without prior written consent" matched against "shall be binding upon
successors and assigns"), and several outright category mismatches (a
Cap-On-Liability span matched to a punitive-damages waiver; a Minimum-Commitment
purchase schedule matched to a termination clause). A census that is ~90% false
positives is worse than no census, so fuzzy hits must also come from documents
that are actually similar. The 0.15 containment floor was set by reading all 22
candidates by hand, not by optimizing a number.

Detector comparison over the full dev+holdout population, emitted into every
sample file under `sampling.detector_comparison`:

| detector | disagreeing spans found |
|---|---|
| exact_normalized | 4 |
| fuzzy_idf_jaccard (gated) | 3 |
| fuzzy_idf_jaccard (ungated) | 22 |
| both | 1 |
| exact only | 3 |
| fuzzy only | 2 |
| union (census size) | 6 |
| discarded by the gate | 19 |

**Neither detector subsumes the other**, which is the argument for keeping both.
Exact-only finds three cases the fuzzy pass misses, including a byte-identical
Minimum Commitment passage across two contracts whose document containment is
0.02 — evidence exact accepts precisely because byte-identity over 60+
characters is strong on its own and needs no document-similarity corroboration.

The two fuzzy-only cases were each checked by hand against the source
contracts, and **one of the two is a false positive**:

- *Confirmed.* Pharmagen (dev) vs EcoScience (ft_train), containment 0.375: two
  companies' endorsement agreements built from the same template. The
  EcoScience document contains a section literally headed `8. Exclusivity.`
  imposing an exclusivity obligation, yet its gold marks Exclusivity
  `is_impossible: true`. A genuine annotation miss that exact matching cannot
  reach, because the parties' names differ.
- *False positive.* WOMENSGOLF endorsement agreement vs its
  "- Intellectual Property Rights..." entry, containment 0.215. That second
  entry is not a twin: it is a **continuation fragment** of the same filing,
  beginning mid-document at page 9 section 11.6, and it contains no signing
  date at all — so `Agreement Date: is_impossible` is correct there. The match
  came from context expansion pulling execution-block boilerplate around a
  25-character date span. Per D-19, gold follows the Atticus Handbook on
  date-shaped constructs, and this case does not contradict it.

So the fuzzy-only confirmation rate is **1 of 2**, and the named failure mode is
CUAD entries that are *fragments of one filing* rather than near-duplicate
documents: they score moderate containment and share boilerplate, but their
absence labels are legitimately correct. Raising the gate to 0.3 would drop this
false positive and keep the confirmed case — but that is fitting a threshold to
two data points, so the gate stays at 0.15 and the fragment mode is documented
instead. The strongest case overall is found by both detectors: two CUAD entries
for the ADURO consulting agreement that are byte-identical (12020 characters
each, one in dev and one in ft_train), where Exclusivity is annotated in one and
`is_impossible` in the other.

Every counterpart row records its `detector`, `similarity` and
`doc_containment`, and every record carries `detected_by`, so the provenance of
each suspected case is visible in the UI and survives export. `--no-fuzzy`
disables the second detector; `--fuzzy-min-containment` moves the gate.

**Convergence with the contamination scan.** The census and the INV1-D7
split-contamination scan are independent methods — one asks "does an identical
passage carry the opposite gold label", the other asks "do two contracts
straddle a split boundary" — and they land on the same contract pairs: all four
contracts INV1-D7 excluded appear here as counterparts. The census is finer,
though. INV1-D7 records that the Ideanomics pair's "gold agrees on all 12"
categories, which is true at category level; the census shows the holdout
contract annotating two Governing Law spans where its twin annotates one and
leaves the other's verbatim text unannotated. Category-level agreement,
span-level disagreement. Both statements are correct at their own granularity.

**The census stratum.** Measured over the whole dev+holdout population: 48 of
1288 gold spans (3.7%) have an exact-passage counterpart, and only **4** of
those show label disagreement — about 0.3% of spans. A random sample of 120
would be expected to contain 0.4 of them, so this class is invisible to random
sampling. The sampler therefore also emits an exhaustive **census** of every
span whose passage recurs under an opposite label, tagged
`sample.draw: duplicate_census` (disable with `--no-duplicate-census`). The
census is the union of both detectors. It is a targeted enumeration of
suspected defects, not a draw: the aggregator counts it in its own section,
broken down by `detected_by` so each matcher's confirmation rate is visible,
and excludes it from every rate, since pooling it would bias the noise floor
upward. Random-draw records are tagged
`sample.draw: random` and are the only input to the headline figures.

**Aggregate.**

```
uv run --project $APP $APP/scripts/aggregate_audit.py <reviewed.yaml>
```

Writes `audits/gold_noise_floor.yaml` (`--out`; `.json` or `--json` for JSON):
overall / per-category / per-split defect rates, per-defect-type counts and
shares, sample size, seeds, sampler versions, reviewers, and an explicit
statement of the denominator — `defect_rate` = spans decided anything other
than `clean`, over spans with a non-pending decision; unreviewed and deferred
spans are excluded from both numerator and denominator, and only
`sample.draw: random` records are counted at all.

Three classes — `redaction_dependent`, `cross_category_overlap`, and
`inconsistent_across_duplicates` — sit on the boundary between "gold is wrong"
and "gold is hard or self-inconsistent", and Tyler has **not** ruled on whether
they count as defects. The report gives both `defect_rate` (includes them) and
`defect_rate_excluding_unruled` (removes all three), and the ruling lives in
exactly two module-level constants, `CLEAN` and `UNRULED`; nothing else in the
aggregator branches on decision identity. The artifact
deliberately does **not** compute a span-F1 ceiling: turning a defect rate
into a ceiling is an analysis step, and the aggregator says so in its own
`note` field.

## Reusing this app for another study

`review_app/record_types.py` holds a `RecordType` registry. A future workflow
adds one entry:

- `id_key`, `headline_key`, `review_key` — which fields identify, headline, and
  carry the review block
- `fields` — label, kind, `editable`, `slot` (`headline | meta | body`), an
  optional hint, and an optional `config` for kind-specific keys. Kinds:
  `text`, `longtext`, `badge`, `list`, `kv` (a mapping as chips), `rows` (a
  list of mappings as a table; `config.columns` picks the columns), `span`
  (a highlighted substring shown inside surrounding context named by
  `config.before` / `config.after`), `evidence` (a list of ids resolved against
  a sidecar named by `config.index` and rendered as contrastive pairs), and
  `footprint` (an external artifact keyed by record id, from the sidecar named
  by `config.index`). Slots are `headline | meta | feature | body`; `feature`
  renders full width between the meta chips and the body grid, and is where the
  footprint lives. A field may also declare `help`, longer prose shown behind a
  `what is this?` toggle next to its label
- `facets` — which fields become filter dropdowns
- `list_keys` — which fields label a row in the queue list
- `decisions` — `Decision(name, hotkey, tone, hint)`; tone is one of
  `ok | warn | bad | info | alt | neutral` and drives colour
- `pending_decisions` — decisions that count as touched but not resolved
  (`defer`, `unclear`), which is what the progress bar excludes. It is a
  progress-bar concern only; membership here never merges two decisions in any
  count or export
- `edit_decision` — the decision that opens the field editor, or `None` for a
  workflow where records are classified but never modified
- `key_order` / `review_key_order` — export key order

Everything else (server, store, YAML round-trip, UI rendering, keyboard,
filters, progress) is driven off that declaration; the front end fetches the
record type from `/api/state` and renders from it. Dotted keys
(`proposer.model`) work for nested fields. If a new record type needs anything
beyond that declaration, the abstraction leaked — say so rather than special-
casing in the UI.

## Tests

```
APP=studies/008-principled-extraction-cuad/apps/principle-review
uv run --project $APP pytest $APP/tests
```

`tests/test_roundtrip.py` covers the principle type: lossless round-trip,
review round-trip and re-import, the rationale-required rule, `edited_from`
per-field maps and the bare-string coercion, persistence across a restart,
decision changes with history, and re-import preserving reviews while picking
up new records. It also covers the round-2 additions: `unclear` surviving
export and re-import as itself, export counts naming every declared decision
including the zeros, the pairs sidecar indexing by `pair_id` and matching the
ids the candidates actually cite, the footprint contract above (including the
bare id-keyed variant and mtime-driven reload), graceful degradation when
neither sidecar is present, and a re-import of the real round-1 file
(`principles/pilot/candidates_pilot.reviewed.yaml`, read-only) reproducing all
16 decisions byte-for-byte.

`tests/test_gold_audit.py` covers the gold-audit type end to end against the
fixture: schema conformance, lossless round-trip, defect decisions exported
and re-imported, vocabulary enforcement, edits being inert when the type
declares no `edit_decision`, persistence across a restart, and the aggregation
artifact's counts, denominator, provenance and absence of any F1 quantity.

## Sample data

- `fixtures/candidates.sample.yaml` — six fabricated CUAD-flavoured principles
  for demoing the app. Not real candidates; never copy into `principles/`.
- `fixtures/mined_pairs.jsonl` — four fabricated contrastive pairs matching the
  ids `candidates.sample.yaml` cites, so the inline-evidence renderer has
  something to resolve. One cited id (`pair-0102`) is deliberately missing, to
  exercise the unresolved case.
- `fixtures/footprint.yaml` — a demo footprint covering three of the six sample
  ids: one healthy, one `not_implementable`, one that fires on 99.5% of units
  and discriminates nothing. The reference implementation of the contract above.
- `fixtures/gold_audit.sample.yaml` — six real CUAD gold spans drawn by
  `scripts/sample_gold.py` (seed 20260815, n=6, context 400) so the
  `gold_audit` type has something to run against. Not the audit sample.

`audits/` (gitignored) is where the sampler and aggregator write by default.
