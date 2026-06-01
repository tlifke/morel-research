# Inv 006 upstream w2s patches

Patches to the upstream `automated-w2s-research` repo
(`/home/tlifke/Projects/automated-w2s-research/` on desktop) that this
investigation depends on.

Same `.diff`-style convention inv 005 uses. Apply scripts are idempotent
— re-running on already-patched source is a no-op.

## Patches

- `apply_agent_resume.py` — adds `HANDOFF_RESUME=1` resume mode and a
  SIGTERM handler (clean stop at session boundary) to
  `w2s_research/research_loop/agent.py`. See the script's docstring
  for the contract.

## Architectural note (for future cleanup)

The upstream is currently a sibling clone, not a git submodule of
this repo, so we maintain deltas as Python apply-scripts here rather
than tracking the upstream tree directly. `study.md` already states
the intent to convert to a submodule at `studies/003-.../upstream/`.
Tracking as inv 006 follow-up; not blocking the overnight run.

## Apply

After fetching the latest branch on desktop:

```bash
ssh desktop 'wsl -- bash -c "
    /home/tlifke/Projects/automated-w2s-research/.venv/bin/python \
    /home/tlifke/Projects/morel-research/studies/003-automated-w2s-replication/\
investigations/006-overnight-agent-loop/scripts/upstream_w2s_patches/\
apply_agent_resume.py
"'
```
