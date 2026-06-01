# Lessons for agent-designed harnesses

Written 2026-05-31, end of the inv 005 day. The thread that ran:
**"agents will design their own harnesses soon — what should they have to
prove before we let them?"** What we learned debugging this harness, that
generalizes.

## What we discovered, condensed

Inv 005 found at least 13 distinct bugs across one investigation. Eight
were silent contract failures between layers we'd written ourselves: the
shim assumed one thing about the agent loop, the handoff_writer assumed
another about the shim, the smoke runner's `sys.path` overrode the
launcher's `PYTHONPATH`, and the Bash tool's output format didn't match
the regex that was supposed to parse it. Each bug had the same shape:
*"every component compiles, the individual tests pass, but end-to-end
something is broken in a way nobody can see from inside their own
layer."*

The fix that made the sprint productive — not "look harder at each layer"
but **"build a fake peer for each boundary, then test the wiring."** Three
patterns landed:

1. **Fake-peer-driven integration tests** (`harness_tests/`). A
   deterministic `fake_model_server` plays scripted scenarios at the
   `/v1/chat/completions` endpoint; the real shim and real
   handoff_writer run against it; assertions check that the boundary
   contracts hold. We caught the `UserMessage`-not-defined bug, the
   regex format mismatch, and the dispatch ordering all in one
   debugging session.
2. **Runtime contract validation** (`extract_iteration_state`'s
   `ToolUseBlock`-without-`ToolResultBlock` check). The handoff_writer
   now actively warns when its expectations aren't met. Documenting
   the contract in a comment wasn't enough — anyone could violate it
   silently. *Validating* the contract at runtime makes the failure
   loud.
3. **Eliminate identity-by-coincidence** (sprint 2 collapse of the dual
   shim package). Two packages with byte-identical code presenting
   distinct class identity is a footgun; we removed the second copy.

## What this means for agents designing harnesses

When an agent is given freedom to assemble its own tools, framework, and
glue code, the failure mode we just lived through becomes much more
common. The agent picks layer A, picks layer B, doesn't know the silent
contract between them, ships. Bugs appear at runtime, far from the line
that introduced them.

The guarantees worth requiring before letting an agent declare a harness
"done":

### 1. Every boundary has a fake peer

For each layer the agent's harness consumes (model server, tool result
format, orchestrator API, etc.), the agent must produce a tiny
deterministic substitute that replays scripted behavior. The substitute
exists for testing only. The tests run against it, not against the live
peer.

Why this matters: live peer testing is slow, non-deterministic, and
expensive. It also obscures *which boundary* failed when something
breaks. A fake peer turns each boundary into a contract observable
without external dependencies.

For inv 005: `fake_model_server` is the model-side fake. A future
harness should also have a fake orchestrator (we mocked this one inline)
and a fake tool subprocess (we relied on the live `vanilla_w2s.run`).

### 2. Every contract has runtime validation

When layer A consumes data from layer B, A must validate that the data
matches the expected shape *at the point of consumption,* not in
documentation. The validation should:

- Warn loudly when violated (stderr, log)
- Optionally promote to a hard fail under a `STRICT` env var
- Name the contract violated, the layer it expected from, and the
  shape it received

Why this matters: silent shape mismatches are the most common failure
mode we saw. Writing "expects `ToolResultBlock` in messages" in a
docstring was insufficient — `extract_iteration_state` happily returned
half-empty state when no `ToolResultBlock`s were present. The
sprint-3 validation turned that into a one-line warning that names the
exact bug.

For inv 005: handoff_writer's contract validation is the prototype.
Future harnesses should declare contracts at every layer boundary and
check them at first use.

### 3. The integration test exists *before* the integration

The agent should write a failing integration test that describes the
behavior its harness must produce, then build until it passes. Not
write the harness, then write a test that documents what the harness
happens to do.

Why this matters: TDD is the standard answer to "your tests cover the
wrong things." When the test is written from the *outside* — from the
research question's perspective, not from the implementation's
perspective — the implementation has to satisfy the actual contract,
not its own internal logic.

For inv 005: had `test_handoff_writer_parses_real_bash_summary` existed
*before* `handoff_writer.py`, the regex format mismatch (finding 13)
would have surfaced on commit zero, not after a 25-minute live smoke.

### 4. Diagnostics are not optional

Every long-running operation must produce telemetry that a human can
read after the fact to reconstruct what happened. The cheapest version
is "write everything to a log file." Inv 005's `BASH_DEBUG_LOG_DIR`
(every Bash subprocess produces a `bash_NNNN.log`) and the trace I
added to `BaseAgent.execute` ("write `[ts] {type}` for every message
that arrives") both proved decisive.

Without these, we spent hours inferring runtime behavior from
side-effects. With them, we read what happened directly.

For inv 005: structured Bash logging is in. The next iteration should
also have structured shim trace and structured agent-loop trace
(possibly all writing to a single per-run `events.jsonl`).

### 5. Single source of truth for every shared definition

When two pieces of code share a definition (a dataclass, a tool name,
a wire format), it must be defined in exactly one place. If it's
defined in two places that look the same, isinstance checks across
the boundary will silently fail (inv 005 bug 1). If it's defined in
two places with slightly different shapes, parsing will silently
return half-state (inv 005 finding 13).

For inv 005: sprint 2 collapsed `claude_agent_sdk_shim` into a thin
re-export of `claude_agent_sdk`. Future harnesses should refuse to
ship if the same name resolves to distinct class objects.

## Concrete proposal for the agent-designed-harness guard rails

Before an agent can declare a harness "ready to research with," it
must satisfy a *fixed* checklist that you (the human researcher)
provide. Suggested checklist:

- [ ] Every external service the harness depends on has a fake peer
      that can be swapped in via env var
- [ ] At least one integration test exists that runs the harness
      end-to-end against the fake peers and asserts on the research
      output (not on internal call shapes)
- [ ] Every cross-layer data dependency has a runtime validation
      that emits a warning when violated and a `STRICT` env var
      that promotes the warning to a failure
- [ ] Every long-running operation produces a structured log
      readable after the fact
- [ ] No name shared across modules resolves to distinct class
      identities (specific defense against inv 005 bug 1)
- [ ] The integration test was written *before* the corresponding
      production code (verified by commit order or by an explicit
      "TDD" tag in the task description)

If the agent's harness passes that checklist, it gets freedom to
grab whatever it needs. If it doesn't, it stays in pre-research
state and the checklist items become tasks.

The checklist is the contract. The agent has freedom inside it, not
in spite of it.

## Risks I can see

- **Checklist becomes performative.** An agent that wants to ship
  will write fake peers that don't actually exercise the contracts
  (e.g., a fake orchestrator that always returns 200 OK). The
  checklist needs human spot-checks on the *content* of the tests,
  not just their existence. One human-readable assertion per test
  is a minimum.
- **Time-to-first-research penalty.** Writing fake peers and
  integration tests before code feels like overhead. The compounding
  return (catching bugs in seconds instead of hours) is invisible
  at the start. The first time the harness ships a regression that
  the integration tests would have caught, the return becomes
  visible. Until then, it costs time.
- **Agents may rebuild the wrong primitives.** If each agent
  designing a harness builds its own fake peer for the same external
  service, we accumulate inconsistent test infrastructure. A library
  of standard fakes (model server, orchestrator, GPU-bound
  subprocess) maintained at the study or repo level reduces this.

## TL;DR

Inv 005 cost ~a day in iterative bug-fixing that a fake-peer
integration test would have collapsed to ~an hour. The structural
pattern was silent cross-layer contracts. The fix is: fake peers,
runtime validation, TDD ordering, structured diagnostics, single
source of truth.

For agent-designed harnesses, codify the above as a checklist.
Pass the checklist → research freedom. Fail it → keep building
the harness.

## Related artifacts in this investigation

- `harness_tests/` — the fake-peer integration framework. The
  `fake_model_server.py` is reusable as a model-side fake for
  any future inv that uses an OpenAI-compat endpoint.
- `scripts/handoff_writer.py` — sprint 3 contract validation
  example.
- `investigation.md` finding 13 meta-section — the pattern
  recognition that motivated this doc.
