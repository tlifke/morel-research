# morel-research

Public-facing research repo. Studies probe what LLMs can and can't do, how
that shifts with harness and model changes, and adjacent questions.

## Layout

```
studies/                        # one directory per study
  000-research-organization/    # meta-study: how we organize research
  001-tool-calibration/         # matched-pair tool-use calibration study
one-pagers/template/            # LaTeX template for one-page writeups
capability-map/                 # running figure of tasks vs. LLM/human axes
scripts/                        # repo-wide tooling (lineage generator, etc.)
future-directions.md            # unattached ideas not yet inside a study
lineage.yaml                    # derived index of study/investigation lineage
CLAUDE.md                       # conventions and Claude's role boundaries
```

## Where to start

- New here? Read `CLAUDE.md` first — it defines the taxonomy and conventions.
- Curious about an active study? Open its `study.md`.
- Want to publish a result? Copy `one-pagers/template/` and write a one-pager.
- Want to see what we've done vs. hypothesized? See `capability-map/`.

## Conventions in one paragraph

Studies live at `studies/NNN-slug/study.md`. Investigations inside them live
at `studies/NNN-.../investigations/NNN-slug/investigation.md`. Both files
carry YAML frontmatter declaring `parents`, `children`, `status`, and axis
position; `lineage.yaml` is derived from that frontmatter and should never
be edited by hand. One-pagers are LaTeX, single page, fixed structure, and
are written by humans — Claude scaffolds but does not write prose.

## Regenerating derived artifacts

```bash
python3 scripts/update_lineage.py        # rebuild lineage.yaml from frontmatter
python3 capability-map/plot.py           # rebuild capability-map.png from tasks.yaml
```
