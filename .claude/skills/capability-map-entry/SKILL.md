---
name: capability-map-entry
description: Add a new task entry or update an existing entry in capability-map/tasks.yaml, then regenerate capability-map.png so the plotted figure stays in sync. Use this whenever the user wants to log a research task on the LLM-vs-human capability map — phrasings include "add to the capability map", "log this as a capability-map task", "mark task X as done", "update the map", "I just did Y, add it to the map", "plot task Z", or when wrapping up a piece of work that should be tracked on the map (even without an explicit "map" mention). The map plots research activities, not the prompts under study; trigger accordingly.
---

# capability-map-entry

Add or update a task on the capability map and re-render the figure.

## When to use

A new research task is worth tracking, or an existing task's status /
coordinates need updating. The map plots **research activities we do**
(e.g. "design tool palette", "curate seed prompts"), not the prompts
or artifacts those activities produce.

## Inputs to capture

For each task entry:

| Field | Notes |
|-------|-------|
| `id` | Short, stable, lowercase kebab. e.g. `curate-seed-prompts`. |
| `label` | Short display label for the plot, e.g. "Curate seed prompts". |
| `study` | `NNN-slug` of the parent study, or `null` if cross-cutting. |
| `investigation` | `NNN-slug` of the parent investigation, or `null`. |
| `llm_capability` | `0.0`–`1.0`. 0 = infeasible for LLM, 1 = trivial. |
| `human_capability` | `0.0`–`1.0`. Same scale. |
| `status` | One of `done`, `in-progress`, `hypothesized`, `human-only`, `blocked`. |
| `notes` | Free-form. Use to capture *why* a coordinate moved, harness caveats, or links to evidence. |

Coordinates are intentionally rough — they are priors revised by
evidence. Don't pretend to a calibrated scale. If the user gives
"medium / high" qualitative labels, map them as approximately:
`low ≈ 0.25`, `medium ≈ 0.55`, `high ≈ 0.85`. Adjust based on
context.

## Procedure

1. Read `capability-map/tasks.yaml`.

2. If updating an existing task, locate it by `id` and modify fields
   in place. Add a note explaining what changed (e.g. "bumped to
   `done` after 2026-05-11 work" or "LLM cap revised from 0.7 to
   0.85 after gemma3-12b results").

3. If adding a new task, append it under the appropriate study group.
   Keep the file roughly grouped by study with comment headers.

4. Run `python3 capability-map/plot.py` to regenerate
   `capability-map.html` (interactive) and `capability-map.png`
   (static). If dependencies are missing, run
   `pip install plotly kaleido pyyaml` and `plotly_get_chrome -y`
   (one-time, Chrome is required for kaleido PNG export).

5. Eyeball the rendered HTML or PNG. If labels overlap, coordinates
   look wrong, or hover text is missing context, adjust and re-render.

6. Tell the user what was added/changed and where it landed on the
   plot.

## Schema reminder

```yaml
- id: short-stable-id
  label: Display label
  study: NNN-slug          # or null
  investigation: NNN-slug  # or null
  llm_capability: 0.0-1.0
  human_capability: 0.0-1.0
  status: done | in-progress | hypothesized | human-only | blocked
  notes: free-form
```

## Don't

- Don't invent coordinates the user didn't authorize for a `done`
  task. If reality is uncertain, leave it `hypothesized` and ask.
- Don't silently delete entries. Demote to a different status, or
  ask before removing.
- Don't try to make every task fit on the diagonal — the whole point
  of the map is to surface asymmetries between LLM and human capability.
