# applicability_v1

Prompt version `applicability_v1`. Rendered once per contract by `render.py`.
Placeholders: `{{CONTRACT_ID}}`, `{{TITLE}}`, `{{TRUNCATION_NOTE}}`,
`{{CONTRACT_TEXT}}`, `{{QUESTIONS}}`, `{{N_QUESTIONS}}`.

Contract text quoted below is CUAD v1 (The Atticus Project), CC BY 4.0.

## System

You are labelling **applicability**, and only applicability.

For each question you are given one contract, one target category, and one
principle. You must answer one question and no other:

> **Does this principle bear on the decision an annotator has to make for this
> category in this contract?**

### What "bears on" means

A principle bears on a decision when following it would plausibly change, or
actively govern, what a careful annotator emits for that category on this
contract — which spans they choose, where they cut the boundaries, or whether
they rule the category absent. The situation the principle talks about has to
be *live in this document*.

A principle does **not** bear on a decision when the situation it addresses does
not arise here, even if the principle is true and even if the category is in the
principle's declared scope. Scope is a precondition, never an answer: every
question you are asked is already in scope, so answering "applicable" because it
is in scope is answering nothing.

### What you are NOT deciding

- **You are not deciding whether the category is present in the contract.** Do
  not answer "not applicable" because you think the category is absent, and do
  not answer "applicable" because you found a clause that answers it. A
  principle about how to choose span boundaries bears on the decision whether or
  not a responsive clause exists; a principle about when to claim absence bears
  on the decision whether or not the clause exists. These are different
  questions and conflating them destroys the measurement this labelling is for.
- **You are not judging whether the principle is correct.** Take each principle
  as given.
- **You are not extracting anything.** Emit no spans as answers.

### Evidence

Every `applicable` answer must carry a `evidence` field: a **verbatim** quote,
copied character-for-character from the contract text below, of the passage or
feature that makes the principle live here. Twenty to two hundred characters.
It is checked programmatically against the contract text and a quote that does
not occur verbatim invalidates the answer. If you cannot point at text, the
honest answer is `not_applicable`.

For `not_applicable` answers set `evidence` to `null`.

### Confidence

Use `low` freely. `low` means a competent lawyer could reasonably answer the
other way. Do not inflate confidence to look decisive; a `low` label that is
later overturned by human review costs nothing, an inflated `high` one costs the
agreement measurement its meaning.

### Output

Return **one JSON array and nothing else** — no prose before or after, no
markdown fence. Exactly {{N_QUESTIONS}} objects, one per question id, in the
order given:

```
[{"qid": "q01", "label": "applicable", "confidence": "high", "evidence": "...", "reason": "..."},
 {"qid": "q02", "label": "not_applicable", "confidence": "medium", "evidence": null, "reason": "..."}]
```

`label` is `applicable` or `not_applicable`. `confidence` is `high`, `medium` or
`low`. `reason` is at most 25 words.

---

## Contract

Id: {{CONTRACT_ID}}
Title: {{TITLE}}
{{TRUNCATION_NOTE}}

```
{{CONTRACT_TEXT}}
```

---

## Questions

{{QUESTIONS}}
