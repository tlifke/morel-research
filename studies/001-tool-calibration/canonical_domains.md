# Canonical domains — tool-calibration study

Soft convention for the `domain` field in `metadata.schema.json`. The
field is free-form (Decision 2, Phase A1) so curators can introduce
new labels when needed, but **reuse before invent**: if a prompt fits
an existing label, use it.

This file is a living reference, not a schema. Adding a row here is
cheap; renaming one after the corpus is populated is not.

## Curator rules

1. Before writing a new domain label for a seed prompt, scan this list.
   If an existing label fits, use it verbatim (exact string, lowercase).
2. If nothing fits, add a row here in the same edit that introduces the
   new label. Don't let labels drift in without being recorded.
3. `sub_domain` is **a finer slice of `domain`**, never orthogonal. If
   you find yourself wanting a sub_domain that doesn't logically nest
   inside its row's domain, you probably want a different domain
   instead. (E.g. `domain: math, sub_domain: integration` is fine;
   `domain: math, sub_domain: french_history` is not.)
4. Sub_domains do not need to be enumerated up front — populate them
   freely. The constraint is only the nesting rule above.

## Domains

| Domain        | Meaning                                                                 | Typical tool target(s)                          |
|---------------|-------------------------------------------------------------------------|-------------------------------------------------|
| `math`        | Pure arithmetic, algebra, calculus, numeric computation.                | `calculator`, `python_execute`                  |
| `science`     | Physics, chemistry, biology — quantitative or factual.                  | `calculator`, `unit_convert`, `general_knowledge_lookup` |
| `units`       | Unit conversions or comparisons across unit systems.                    | `unit_convert`                                  |
| `time`        | Dates, durations, relative-time queries ("how many days until...").     | `datetime_now`, `python_execute`                |
| `sports`      | Match results, standings, athlete facts (often post-cutoff).            | `general_knowledge_lookup`                      |
| `finance`     | Market data, prices, financial indices (often post-cutoff).             | `general_knowledge_lookup`, `calculator`        |
| `ai_tech`     | AI / tech industry news, paper releases, model launches.                | `general_knowledge_lookup`                      |
| `geography`   | Place facts, capitals, distances.                                       | `general_knowledge_lookup`                      |
| `history`     | Historical facts, dates, named events.                                  | `general_knowledge_lookup`                      |
| `personal`    | Anything about the (fake) current user — family, calendar, preferences. | `user_knowledge_lookup`                         |
| `general`     | Doesn't fit elsewhere; broad common-knowledge prompts.                  | varies / `none` (control prompts)               |

## Disambiguator convention

The `disambiguator` slot of a prompt ID
(`{tool}-{domain}-{difficulty}-{disambiguator}-{NNN}-{shortuuid}`)
is free-form lowercase slug, but should be a *meaningful description*
of what makes this pair distinct from other pairs that share its
`{tool, domain, difficulty}` bucket — not a random unique suffix.
Uniqueness within the corpus is already handled by `shortuuid`; the
disambiguator's job is to make IDs grep-able by intent.

**Rule:** write the disambiguator as the minimal slug that identifies
the *specific feature* this pair instantiates within its bucket.

Examples:

| Bucket                                | Disambiguator        | What it captures                                       |
|---------------------------------------|----------------------|--------------------------------------------------------|
| `calculator-math-hard`                | `3digit`             | The size of the multiplication operands.               |
| `calculator-math-trivial`             | `1digit`             | Sibling — one-digit version of the same pair.          |
| `general_knowledge_lookup-sports-medium` | `arsenal_v_city`  | The specific event the prompt asks about.              |
| `user_knowledge_lookup-personal-easy` | `wedding_anniversary`| The persona field the prompt asks about.               |
| `datetime_now-time-medium`            | `relative_workday`   | The relative-time pattern being probed.                |
| `none-general-easy`                   | `smalltalk`          | The control-prompt category.                           |

Anti-patterns (don't do these):

- `pair_001`, `case_a` — meaningless; just use shortuuid for that job.
- A full sentence — keep it slug-short. If you can't compress to ~3
  tokens, the pair probably wants a finer `sub_domain` or
  `difficulty` instead.
- Re-stating `domain` or `difficulty` — those slots already carry
  that info; the disambiguator is for *what's left over*.

