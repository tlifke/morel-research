# principle-review

A local-only adjudication queue: load proposed records from YAML, work through
them one at a time, record a decision plus a mandatory written rationale, and
write the reviewed set back out to YAML.

Two record types ship today:

| `--record-type` | records | decisions | used by |
|---|---|---|---|
| `principle` (default) | candidate `Principle` records | accept / edit / reject / defer | inv 002 |
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
| `--no-browser` | | do not auto-open a tab |

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
- **defer** is a first-class decision (`d`, then a one-line reason).
- `reviewer` and `date` are stamped automatically.
- Any already-reviewed record can be reopened and changed; every save is also
  appended to a `review_history` table, so decision churn is recoverable.

Keyboard: `j`/`k` prev/next, `u` next unreviewed, `i` focus rationale,
`ctrl+enter` save, `ctrl+e` export, `/` search, `esc` unfocus. Decision
hotkeys come from the record type and are listed in the sidebar
(`a`/`e`/`r`/`d` for principles; `c`/`m`/`n`/`s`/`b`/`x`/`o`/`d` for the gold
audit).

Filters: decision state, plus one dropdown per declared facet (principles:
provenance, type, proposer model; gold audit: category, split, stratum) and a free-text search. Header shows
`n reviewed / n total` with an accept/edit/reject/defer breakdown; the bar
tracks *resolved* records, so defers correctly read as not-done.

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
`annotated`, `not_annotated`, `marked_absent`, or `category_not_in_subset`.
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

**The census stratum.** Measured over the whole dev+holdout population: 48 of
1288 gold spans (3.7%) have an exact-passage counterpart, and only **4** of
those show label disagreement — about 0.3% of spans. A random sample of 120
would be expected to contain 0.4 of them, so this class is invisible to random
sampling. The sampler therefore also emits an exhaustive **census** of every
span whose passage recurs under an opposite label, tagged
`sample.draw: duplicate_census` (disable with `--no-duplicate-census`). The
census is a targeted enumeration of suspected defects, not a draw: the
aggregator counts it in its own section and excludes it from every rate, since
pooling it would bias the noise floor upward. Random-draw records are tagged
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
  list of mappings as a table; `config.columns` picks the columns), and `span`
  (a highlighted substring shown inside surrounding context named by
  `config.before` / `config.after`)
- `facets` — which fields become filter dropdowns
- `list_keys` — which fields label a row in the queue list
- `decisions` — `Decision(name, hotkey, tone, hint)`; tone is one of
  `ok | warn | bad | info | alt | neutral` and drives colour
- `pending_decisions` — decisions that count as touched but not resolved
  (`defer`), which is what the progress bar and the aggregator exclude
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
up new records.

`tests/test_gold_audit.py` covers the gold-audit type end to end against the
fixture: schema conformance, lossless round-trip, defect decisions exported
and re-imported, vocabulary enforcement, edits being inert when the type
declares no `edit_decision`, persistence across a restart, and the aggregation
artifact's counts, denominator, provenance and absence of any F1 quantity.

## Sample data

- `fixtures/candidates.sample.yaml` — six fabricated CUAD-flavoured principles
  for demoing the app. Not real candidates; never copy into `principles/`.
- `fixtures/gold_audit.sample.yaml` — six real CUAD gold spans drawn by
  `scripts/sample_gold.py` (seed 20260815, n=6, context 400) so the
  `gold_audit` type has something to run against. Not the audit sample.

`audits/` (gitignored) is where the sampler and aggregator write by default.
