# Model registry — claude_agent_sdk_shim

The shim works against any Ollama model whose Anthropic-compatibility surface
emits text and `tool_use` blocks (and optionally `thinking` blocks). The
registry is a small lookup table that captures *per-model* knobs we've
learned the hard way: max-token budgets, thinking-surface shape, and the
prompt-patch text the model wants to see, so swapping researcher models is
a one-line config change.

## Why a registry

Before this module, switching from `qwen3.5:4b` to `nemotron-3-nano:4b` or
`gemma4:e4b` required changing the `model` string *and* knowing per-model
quirks (token budget, whether the prompt patch helps or hurts, whether
thinking arrives as a sidecar field vs. an explicit block). The registry
collapses that to one place.

Investigations (gate-5 matrix, smokes, the main loop) should reference
models by their registry key and call `ClaudeAgentOptions.from_registry(...)`
instead of constructing options with raw Ollama tags.

## How to use it

```python
from claude_agent_sdk_shim import ClaudeAgentOptions, ClaudeSDKClient

opts = ClaudeAgentOptions.from_registry(
    "qwen3.5:4b",
    system_prompt="...",
    mcp_servers={"calc": calc_server},
    allowed_tools=["mcp__calc__add"],
)
async with ClaudeSDKClient(opts) as client:
    ...
```

Caller-set kwargs always win over registry defaults. Anything you do not
pass picks up the registry value.

If you construct `ClaudeAgentOptions(model="...")` directly without
`from_registry`, the `__post_init__` populates the metadata fields
(`model_family`, `thinking_mode`, `model_notes`) from the registry when the
model string matches a known key, but it intentionally **does not** apply
the `recommended_hint` implicitly — hint application is reserved for the
explicit `from_registry` path to keep `tool_invocation_hint` semantics
untouched for callers that have not opted in.

## Adding a new model

Edit `model_registry.py`:

```python
"my-new-model:tag": ModelEntry(
    ollama_tag="my-new-model:tag",
    family="my-family",
    max_tokens_default=8192,
    thinking_mode="block",          # or "sidecar" or "none"
    recommended_hint=None,           # or a short directive string
    notes="...",
),
```

Then add a test case in `tests/test_model_registry.py` asserting the new
entry's fields, and a row to the seeded gate-3 / gate-5 matrix runners if
you want it included in sweeps.

## Field reference

- `ollama_tag` — the exact tag Ollama serves the model under. Used directly
  as the `model` field of the Anthropic-compat request.
- `family` — coarse grouping (`qwen3`, `qwen3.5`, `nemotron`, `gemma4`, ...).
  Useful for branching post-processing logic that varies by lineage.
- `max_tokens_default` — token budget for completions. Tuned by hand from
  smoke runs; 8192 is the floor for thinking-mode models in this repo.
- `thinking_mode` — how the model surfaces reasoning content through the
  Ollama Anthropic-compat layer:
  - `"block"` — explicit `thinking` block in the response content array
    (Gemma 4 E4B).
  - `"sidecar"` — `thinking` field on a separate non-text block (Nemotron 3
    Nano 4B; observed on Qwen 3.5 4B as well).
  - `"none"` — model does not produce surfaced reasoning.
- `recommended_hint` — short directive appended to the system prompt when
  the caller uses `from_registry`. The wire-format is unchanged from
  pre-registry; this field merely picks the *text* per model.
- `notes` — free text. Things future-you needs to know but couldn't have
  guessed from the tag alone.

## Sources

Initial entries seeded from:

- `studies/003-.../investigations/003-claude-sdk-shim-and-researcher-swap/investigation.md`
  (gate-5 matrix; qwen3.5:4b + hint as the only PASSing cell).
- `studies/003-.../model-derisk-nemotron-gemma4.md` (Nemotron / Gemma 4 E4B
  derisk; observed thinking-surface shapes).
