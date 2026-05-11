---
name: new-investigation
description: Scaffold a new investigation under an existing study in the morel-research repo. Creates the directory, writes investigation.md with proper YAML frontmatter, links it as a child of the parent study, and rebuilds lineage.yaml. Use this whenever the user says "new investigation", "create an investigation", "scaffold investigation NNN-...", "start an investigation under study X", "add an investigation", or otherwise indicates they want a new bounded unit of work added to an existing study. Also trigger if the user is starting a new line of work that's clearly a sub-project of an existing study, even if they don't use the word "investigation".
---

# new-investigation

Scaffold a new investigation directory under an existing study.

## When to use

The user wants a new bounded unit of work added to an existing study.
A study is `studies/NNN-slug/`; an investigation is one level down at
`studies/NNN-slug/investigations/NNN-slug/`.

If there is no parent study yet, use `new-study` instead (it can create
the first investigation as part of the same flow).

## Inputs to capture

Before writing anything:

1. **Parent study**: the `NNN-slug` directory under `studies/`. List
   options with `ls studies/` and ask if unclear.
2. **Slug**: lowercase kebab, e.g. `difficulty-axes`. Reuse the user's
   wording if they gave a phrase; sanitize to kebab.
3. **Title**: human-readable, e.g. "Difficulty axes". Reasonable to
   derive from the slug and confirm.
4. **One-line scope**: what bounded question this investigation answers.
   Ask if not obvious from context.
5. **Status**: usually `planned`. Other valid values:
   `in-progress`, `complete`, `blocked`, `abandoned`.
6. **Rough axes** (optional but encouraged): `llm_capability` and
   `human_capability` as `low | medium | high`. These end up in
   frontmatter and inform later capability-map entries.

## Procedure

1. Determine the next investigation number:
   ```bash
   ls studies/<parent-study>/investigations/ 2>/dev/null \
     | grep -E '^[0-9]{3}-' | sort | tail -1
   ```
   Add 1, zero-pad to three digits. If the directory doesn't exist,
   start at `001`.

2. Create the directory:
   `studies/<parent-study>/investigations/<NNN>-<slug>/`

3. Write `investigation.md` using the template below. Today's date goes
   in both `created` and `updated`.

4. Append the new ID to the parent study's `children:` list in
   `studies/<parent-study>/study.md`. Open the file, find the
   `children:` line in frontmatter, add an entry.

5. Run `python3 scripts/update_lineage.py` to rebuild `lineage.yaml`.
   If it errors, fix the frontmatter and retry — do not bypass.

6. Tell the user what was created and remind them of the next move
   (typically: fill in the investigation's scope/methods sections).

## investigation.md template

```markdown
---
id: studies/<PARENT>/investigations/<NNN>-<SLUG>
title: <TITLE>
status: <STATUS>
parents:
  - studies/<PARENT>
children: []
related: []
axes:
  llm_capability: <medium|low|high>
  human_capability: <medium|low|high>
tags: []
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
---

# Investigation N — <TITLE>

## Scope

<ONE-LINE SCOPE THE USER GAVE>

## Methods

_To be populated._

## Decisions

_Populate as work proceeds. Format:_

> **Decision N — short title** (date)
> What was chosen, alternatives considered, why this won.

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

_Surface assumptions explicitly here when drafting._

## Limitations

_To be populated._
```

Leave commentary in the form of `_italics_` placeholders — the human
will fill them in. Do not invent prose for the substantive sections.

## Don't

- Don't create a new investigation whose number collides with an
  existing one. Always re-check after listing.
- Don't edit `lineage.yaml` directly. It's derived.
- Don't write speculative results or methods. Leave placeholders.
- Don't forget to update the parent study's `children:` list — the
  lineage script will warn if reciprocation is missing.
