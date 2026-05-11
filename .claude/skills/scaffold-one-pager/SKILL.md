---
name: scaffold-one-pager
description: Scaffold a one-page LaTeX writeup for a study or investigation in the morel-research repo by copying one-pagers/template/ into the target location and pre-filling the title-block macros. Use this whenever the user says "scaffold a one-pager", "set up a one-pager", "start a one-pager", "create a one-pager for X", "draft a one-pager template", or otherwise indicates they want to begin a one-page writeup. Trigger ALSO when the user is wrapping up an investigation and signals they want to publish a result — that's the right moment to scaffold the paper. CRITICAL: this skill never writes prose. It only sets up the file. The human writes the prose; Claude may give feedback only.
---

# scaffold-one-pager

Copy the one-pager template into a study or investigation directory and
pre-fill its title-block macros. **Do not write any prose.** The human
writes the prose; Claude scaffolds and may give feedback during
drafting.

## When to use

The user is ready to publish a result and needs the file set up. This
is the right moment to start so they can drop in their figure and
start writing.

## Where it lives

| Case | Target |
|------|--------|
| Investigation publishes its own paper | `studies/<S>/investigations/<I>/one-pagers/` |
| Study aggregates multiple investigations | `studies/<S>/one-pagers/` |

Ask the user which case applies if it's ambiguous.

## Inputs to capture

1. **Target location** (per the table above).
2. **Title**: short, declarative. Ask.
3. **Author(s)**: comma-separated. Default to the repo's primary
   researcher if the user has told us in a prior session; otherwise
   ask.
4. **Date**: today, unless told otherwise.
5. **Study/investigation reference**: the path, e.g.
   `studies/001-tool-calibration/investigations/001-foundations`.
   Derive from the target location.

## Procedure

1. Confirm `one-pagers/template/one-pager.tex`,
   `one-pagers/template/refs.bib`, and `one-pagers/template/Makefile`
   exist. If not, abort and tell the user the template is missing.

2. Create the target directory if it doesn't exist:
   ```bash
   mkdir -p <target>
   ```

3. Copy template files into the target:
   ```bash
   cp one-pagers/template/one-pager.tex <target>/
   cp one-pagers/template/refs.bib <target>/
   cp one-pagers/template/Makefile <target>/
   ```

4. Open the copied `one-pager.tex` and update **only** these macros
   near the top:
   - `\paperTitle{...}` → user's title
   - `\paperAuthors{...}` → user's author list
   - `\paperDate{...}` → today's date (`YYYY-MM-DD`)
   - `\paperStudyRef{...}` → derived path

   Leave every `PROSE GOES HERE` / `TAKEAWAY ...` / figure-placeholder
   line untouched. Those are the human's to fill in.

5. Tell the user:
   - where the file was scaffolded,
   - how to compile (`make` in the target directory),
   - that you'll give feedback if asked but won't write the prose.

## Don't

- **Don't write prose.** Not in "Research question", not in "Methods",
  not in "Results", not in "Forward-looking", not in "Takeaways", not
  in figure captions. The human writes those.
- Don't replace `FIGURE PLACEHOLDER` with a fabricated figure or
  caption. Leave it for the human to swap in.
- Don't add packages or change the document class.
- Don't change the section order or count. The fixed structure is the
  discipline of the format.
- Don't compile the paper unless the user explicitly asks — and even
  then, compiling a paper full of placeholders just produces noise.

## What you can do

- Offer to suggest figure candidates after the human starts drafting.
- Offer feedback on prose drafts when shown them.
- Flag structural drift (e.g. four sections that look like results,
  no takeaways, missing limitation bullet).
- Check that the takeaway bullets satisfy the format requirements:
  at least one tied to the figure, at least one on key limitations.

These are services offered on request, not unsolicited rewrites.
