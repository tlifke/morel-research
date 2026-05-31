# Upstream w2s patches (inv 005)

Patches applied to `/home/tlifke/Projects/automated-w2s-research/` to
enable inv 005's experimental flows. These are *upstream* to the w2s
repo (not the shim), distinct from `../upstream_shim_patches/`.

## `agent_handoff_wiring.diff`

Wires `handoff_writer.py` (the Anthropic-style context-reset pattern
from inv 005 finding 6) into `w2s_research/research_loop/agent.py`'s
`AutonomousAgentLoop`.

### What it does

1. Adds `self.last_messages: List[Any] = []` to `BaseAgent.__init__`
   and assigns `self.last_messages = messages` at the end of
   `BaseAgent.execute`. This exposes the per-session message list so
   the outer loop can extract iteration state from it.
2. After each `_run_session()` returns, calls
   `handoff_writer.extract_iteration_state(agent.last_messages,
   server_acks)` where `server_acks` is parsed from any
   `evaluate_predictions` tool_result JSON found in the messages.
3. Writes the handoff YAML to `<workspace>/.agent_handoff/iteration_NN.yaml`.
4. Sets `self._prompt = handoff_writer.make_bootstrap_message(path, N)`
   so the next session's `_get_prompt()` returns the bootstrap
   referencing the prior iteration's artifact instead of the cached
   original prompt template.

### Activation

Gated on `HANDOFF_ENABLE=1` env var. When unset, behavior is
byte-identical to upstream. When set, handoff runs after every
session.

### Required setup

The patch imports `handoff_writer` from the inv 005 scripts dir, so
the launcher must add that path to `PYTHONPATH`:

```bash
export PYTHONPATH=".../005-split-host-researcher/scripts:$PYTHONPATH"
```

The smoke launcher (`run_smoke_v2.sh`) adds this when
`HANDOFF_ENABLE=1` is set.

### How to apply

```bash
cd /home/tlifke/Projects/automated-w2s-research
patch -p1 < .../agent_handoff_wiring.diff
```

To revert:
```bash
patch -p1 -R < .../agent_handoff_wiring.diff
```

### Things to flag

- The `server_acks` extraction parses the orchestrator's JSON response
  out of the `evaluate_predictions` tool_result text. The shape of that
  text depends on the MCP `server-api-tools` implementation; if it
  changes upstream, the regex needs updating.
- `handoff_writer.make_bootstrap_message` returns a generic
  "decide whether to iterate" prompt. For inv 005's specific case
  (session 0 ran Bash but didn't submit) the bootstrap may need to be
  augmented with a more pointed instruction like "the eval_output.json
  is at X; call evaluate_predictions next." Not in this patch — see
  forward-looking notes in `investigation.md`.
