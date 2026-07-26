# Claude-authored writeups

Everything under this directory was **written end-to-end by an LLM**, not by the
human researcher. It is segregated here so the boundary is unambiguous.

## Standing

These are not the repository's position. The human researcher has not revised
the prose and does not necessarily agree with the framing, emphasis, or
conclusions. Where a Claude-authored piece and a human-authored artifact
disagree, the human-authored artifact is authoritative.

They are published rather than discarded for two reasons:

1. **They are labelled artifacts.** A reader can see exactly what an LLM
   produced from this corpus without having to guess which sentences were the
   model's.
2. **They are data.** This repository studies autoresearchers and their limits.
   An LLM's synthesis of a research corpus — what it foregrounds, what it
   over-claims, which analogies it reaches for, where its confidence outruns the
   evidence — is a sample of the capability under study, not just a byproduct of
   it. That makes these documents part of the experimental record.

Read them accordingly: as a model's output about the work, alongside the human's
own account of the same work, with the comparison itself being of interest.

## Attribution requirements

Every piece here must state, in the artifact itself:

- the authoring model and exact model identifier,
- the date,
- that the human researcher did not write or endorse it,
- a pointer to the human-authored source evidence it drew on.

## Contents

```
technical-reports/
  framework-drift/          TR-000-01-C — metadata drift in an agent-legible
                            research repo. LaTeX + compiled PDF + regenerable
                            Plotly figures.
blog/
  the-map-that-lied.md      Layman-facing version of the same argument.
literature-orientation-2026-07.md
                            Survey of the autoresearcher / harness / LLM-HPO
                            literature and where this repo's work sits in it.
                            Orientation material for the next phase.
```

Both draw on `studies/000-research-organization/framework-drift-evidence.md`
(the human-commissioned evidence pack) and `drift-snapshot.tsv`. Figures
regenerate from the snapshot; see
`technical-reports/framework-drift/figures/`.

## Provenance

| Artifact | Model | Date |
|---|---|---|
| `technical-reports/framework-drift/` | `claude-opus-5[1m]` | 2026-07-25 |
| `blog/the-map-that-lied.md` | `claude-opus-5[1m]` | 2026-07-25 |
| `literature-orientation-2026-07.md` | `claude-opus-5[1m]` | 2026-07-25 |
