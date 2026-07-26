# Writeups

Publishing artifacts. The human writes the prose here — Claude scaffolds files
and gives feedback only (see `CLAUDE.md`, "Claude's role boundaries").

```
one-pagers/       # LaTeX, single page, fixed structure. Template: ../one-pagers/template/
blog/             # long-form prose
claude-authored/  # written end-to-end by an LLM — see below
```

Scaffold a one-pager with the `scaffold-one-pager` skill.

## `claude-authored/` — the one exception to the rule above

Everything outside `claude-authored/` is the human's prose. Everything inside it
was written end-to-end by an LLM, on request, and is segregated so the boundary
is unambiguous rather than inferred.

Those pieces are **not** the repository's position. The human has not revised
them and does not necessarily agree with their framing or conclusions; where
they disagree with a human-authored artifact, the human-authored artifact wins.
They are kept for two reasons: they are labelled, so a reader never has to guess
which sentences were the model's; and in a repository studying autoresearchers,
a model's synthesis of the corpus is itself a sample of the capability under
study.

Every artifact in there states its authoring model, exact model identifier,
date, and the human-authored evidence it drew on. See
[`claude-authored/README.md`](claude-authored/README.md) for the standing and
the provenance table.

Current contents:

- `claude-authored/technical-reports/framework-drift/` — TR-000-01-C, on
  metadata drift in an agent-legible research repo (`claude-opus-5[1m]`).
- `claude-authored/blog/the-map-that-lied.md` — layman-facing version of the
  same argument (`claude-opus-5[1m]`).

## Open question — not yet decided

Existing writeups still live next to their studies:

- `studies/001-tool-calibration/writeups/onepager/001-curator-prediction-mismatch/`
- `studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor/one-pagers/`
- `drafts/desktop-setup-blogpost.md`

Whether those migrate here, or whether this directory is only for cross-cutting
pieces that don't belong to a single study, is undecided. Resolve it once there
are enough writeups for the answer to be obvious.

## Reference points

- `framework-v1` tag — the v1 framework as it actually stood, immutable.
- `studies/000-research-organization/framework-drift-evidence.md` — evidence pack
  on where the framework held and where it went ceremonial, with its assumptions
  flagged for rejection.
