# Capability map

A running figure of where research tasks in this repo fall on two axes:

- **LLM capability** (x) — how well current LLMs do this task autonomously.
- **Human capability** (y) — how well a skilled human does it autonomously.

Each point is a *research task we do*, not a prompt under study. Status
markers distinguish completed work, hypotheses, and human-only territory.

## Regenerate

```bash
pip install plotly kaleido pyyaml
plotly_get_chrome -y    # one-time; kaleido v1 needs Chrome for PNG export
python3 capability-map/plot.py
```

Outputs:

- `capability-map.html` — interactive view (open in a browser; hover for
  task details).
- `capability-map.png` — static export, suitable for embedding in
  one-pagers and Markdown.

Both regenerate from `tasks.yaml` on every run.

## Editing the map

Edit `tasks.yaml` directly. Each entry has:

```yaml
- id: short-stable-id
  label: Display label
  study: NNN-slug                  # null if not yet scoped
  investigation: NNN-slug          # null if not yet scoped
  llm_capability: 0.0-1.0
  human_capability: 0.0-1.0
  status: done | in-progress | hypothesized | human-only | blocked
  notes: free-form
```

Bumping a task from `hypothesized` to `done` is a meaningful signal —
update the coordinates if reality differs from the prior, and add a note.

## Caveats

- Coordinates are rough. We have no calibrated capability scale; positions
  are priors revised by evidence.
- "LLM capability" is harness-dependent. When a major harness change shifts
  task feasibility, log the shift in the relevant `notes` field rather
  than silently moving the point.
- The map shows what we've tried in *this* repo. It is not a general claim
  about LLM capabilities.
