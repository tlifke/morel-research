---
name: new-study
description: Scaffold a new study in the morel-research repo. Creates the studies/NNN-slug/ directory with the standard subdirectories (investigations/, assets/, data/, scripts/), writes study.md with proper YAML frontmatter, optionally scaffolds the first investigation, and rebuilds lineage.yaml. Use this whenever the user says "new study", "create a study", "scaffold study", "start a study on X", "open a new line of inquiry", or otherwise indicates they want a new top-level research thread. Trigger even when the user describes the topic without the word "study" — if it's clearly a long-lived research question, this is the right scaffolder.
---

# new-study

Scaffold a new top-level study.

## When to use

The user is starting a long-lived line of inquiry — broader than a
single experiment and likely to spawn multiple investigations over
time. If the work is one bounded unit inside an existing study, use
`new-investigation` instead.

## Inputs to capture

1. **Slug**: lowercase kebab, e.g. `tool-calibration`. Derive from the
   user's wording if a phrase is given.
2. **Title**: human-readable, e.g. "Tool calibration (matched-pair)".
3. **Research question**: one or two sentences. The user should provide
   this — don't invent it. If they're vague, ask.
4. **Rough axes**: `llm_capability` and `human_capability` as
   `low | medium | high`.
5. **First investigation?** Ask whether to also scaffold an initial
   investigation under this study, and if so, capture its slug + title
   (delegate the rest to `new-investigation`'s flow).
6. **Repository policy notes** (optional): per-study decisions about
   what's in git (data sizes, model output exclusions, etc.). Capture
   if the user has opinions.

## Procedure

1. Find the next study number:
   ```bash
   ls studies/ | grep -E '^[0-9]{3}-' | sort | tail -1
   ```
   Add 1, zero-pad to three digits.

2. Create the directory tree:
   ```
   studies/<NNN>-<slug>/
     ├── investigations/
     ├── assets/
     ├── data/
     └── scripts/
   ```
   (Empty subdirs are fine. Add `.gitkeep` files if you want them in
   git before contents appear.)

3. Write `study.md` from the template below.

4. If the user wanted a first investigation, follow the
   `new-investigation` flow to scaffold it now. Add its ID to the
   study's `children:` list.

5. Run `python3 scripts/update_lineage.py`. Fix frontmatter on any
   error; don't bypass.

6. Tell the user what was created. Remind them: the research question
   in `study.md` is the human's to write — the scaffold leaves it as
   a placeholder.

## study.md template

```markdown
---
id: studies/<NNN>-<SLUG>
title: <TITLE>
status: planned
parents: []
children: []
related: []
axes:
  llm_capability: <medium|low|high>
  human_capability: <medium|low|high>
tags: []
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
---

# Study N — <TITLE>

## Question

<USER'S RESEARCH QUESTION HERE — IF THEY HAVEN'T WRITTEN IT, LEAVE
THE PLACEHOLDER AND TELL THEM TO FILL IT IN.>

## Why this study

_To be populated by the human._

## Investigations

_Populated as investigations are added. Each entry should be a single
line referencing the investigation directory and its status._

## Repository policy

_Document per-study decisions about what goes in git (data sizes,
output logs, large binaries). If no deviations, say so explicitly._

## Forward-looking

_To be populated._

## Open questions

_To be populated._
```

## Don't

- Don't write the research question yourself. It's the heart of the
  study and is the human's call.
- Don't skip the `Repository policy` section — even "default applies"
  is a useful explicit statement.
- Don't edit `lineage.yaml` directly.
