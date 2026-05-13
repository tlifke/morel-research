# One-pager template

Single-page LaTeX writeup for a study or investigation. Fixed structure —
deviating defeats the purpose of the format.

## Structure

1. **Title block** — title, author(s), date.
2. **Summary** — one paragraph: question, what you did, what you found.
3. **Figure** — exactly one. It carries the message.
4. **Recommendations and Limitations** — 3 to 5 bullets:
   - at least one tied to the figure,
   - at least one on key limitations,
   - any remaining bullets for results that didn't fit the figure.

Code for replication lives in the repo and is linked from the title block.
Deeper work goes in a separate venue (paper, blog post, etc.) — not here.

## Using the template

1. Copy `one-pager.tex`, `refs.bib`, and `Makefile` to wherever the paper
   lives (typically `studies/NNN-.../one-pagers/` or
   `studies/NNN-.../investigations/NNN-.../one-pagers/`).
2. Fill in `\paperTitle`, `\paperAuthors`, `\paperDate`,
   `\paperStudyRef` at the top of `one-pager.tex`.
3. Drop the figure file alongside `one-pager.tex` and uncomment the
   `\includegraphics{...}` line.
4. Write the prose. The human writes the prose.
5. Compile:

   ```bash
   make            # builds one-pager.pdf
   make watch      # rebuild on change (latexmk -pvc)
   make clean      # remove build artifacts
   ```

## Claude's role

**Claude does not write the prose.** Claude may:

- scaffold the file from this template,
- propose figure choices and structure,
- give feedback and questions during drafting,
- check that the fixed structure is preserved.

The human decides which feedback to incorporate.

## Compilation requirements

Requires a TeX distribution with `latexmk`. Install:

- Debian / Ubuntu: `sudo apt install texlive-latex-extra latexmk`
- macOS (brew): `brew install --cask mactex-no-gui`
- Or use Overleaf, which compiles `one-pager.tex` directly.

## Notes

The template uses standard packages (`geometry`, `graphicx`, `enumitem`,
`titlesec`, `hyperref`, `microtype`, `parskip`). No exotic dependencies.

If the page overflows, prefer trimming prose over shrinking the figure or
changing margins. The format is the discipline.
