# Harness integration tests

End-to-end tests that exercise the inv 005 harness (shim_v2 + handoff_writer
+ patched `AutonomousAgentLoop`) **without any live model**. A deterministic
fake "model server" returns scripted `tool_calls`, the real shim/agent loop
runs against it, and assertions check that the loop produces what the
research code is supposed to produce.

If these tests pass, the wiring works regardless of which real model swaps
in. They would have caught findings 1, 7, 8, 12, and 13 of inv 005 in one
run instead of the iterative diagnose-fix-repeat we actually did.

## Files

- `fake_model_server.py` — an `aiohttp` (or `httpx`-served) endpoint at
  `/v1/chat/completions` that returns scripted assistant messages from a
  configurable scenario file. Replaces the live Mac Ollama for testing.
- `scenarios/q1_happy_path.yaml` — the "model behaves perfectly" script:
  turn 0 emits `Bash` with the patch-4 training command; turn 1 reads the
  Bash tool result, sees `EVAL_PREDICTIONS_WRITTEN`, calls
  `evaluate_predictions` with a fake integer array. Asserts: orchestrator
  receives one submission AND handoff yaml has `ran_to_completion: true`.
- `scenarios/q1_handoff_required.yaml` — turn 0 emits Bash, ends without
  submitting. Bootstrap should inline the pointed hint. Turn 0 of session
  1 should call `evaluate_predictions`. Asserts: iteration_01.yaml has
  `ran_to_completion: true`.
- `scenarios/regression_v1_bugs.yaml` — exercise the historical wiring
  failure modes:
    - shim must yield `ToolResultBlock` between AssistantMessages
    - handoff_writer must parse `bash_markers` from real Bash tool output
    - `predictions_file` must be extracted from the Bash tool's summary
- `test_harness.py` — pytest entrypoint that, for each scenario, spins up
  the fake server, runs `run_smoke.py` against it, then asserts on the
  produced artifacts (session logs, handoff YAMLs, orchestrator state).

## Running

```bash
uv run --with pytest --with aiohttp --with pyyaml pytest test_harness.py -v
```

The fake server listens on `127.0.0.1` with an ephemeral port. The smoke
runner is invoked with `MAC_OLLAMA_URL=http://127.0.0.1:<port>` and
`MAX_RUNTIME_SECONDS=60` (real time, no GPU).

## Why this exists

See `investigation.md` finding 13's meta-section. Most inv 005 bugs were
silent contract failures between layers (shim ↔ handoff_writer, runner
↔ PYTHONPATH, Bash output format ↔ regex expectations). A fake-model
loop exercises every contract in one run.

## Scope limits

- No GPU. The fake model never asks for SFT; we don't actually run
  `vanilla_w2s.run`. The Bash tool gets a fake training-command request
  and the test asserts on the *shape* of what the model sent, not the
  result of executing it.
- One session at a time. Multi-iteration handoff scenarios are scripted
  explicitly per scenario YAML.
- The fake model is not adaptive. Each turn returns a pre-scripted
  response regardless of input. Good for catching wiring bugs; not for
  catching model-behavior questions.
