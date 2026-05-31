# Inv 005 upstream shim patches

Two patches against the inv 003/004 shim at
`/home/tlifke/inv003_shim/`. Applied to **both** copies of the shim
(`shim_pkg/claude_agent_sdk/` and `scripts/claude_agent_sdk_shim/`),
which ship byte-identical code.

## `client_py.diff`

Fixes the two bugs documented in inv 005 Methods:

1. **`_build_tool_index` duck-types `mcp_servers` entries** instead of
   `isinstance(server, SdkMcpServer)`. The shim ships two parallel
   package copies whose `SdkMcpServer` classes have distinct identity;
   any caller that imports `create_builtin_tools_server` from one
   package while the agent loop checks against the other's class
   silently loses every tool. Duck-typing on `.tools` (dict) makes the
   identity irrelevant.

2. **`OLLAMA_ANTHROPIC_BASE_URL` resolved per-call**, not at module
   import. The previous module-level `DEFAULT_BASE_URL = os.getenv(...)`
   captured the value at first import and never re-read; setting the
   env var from Python after `import claude_agent_sdk` had no effect.
   The new `_resolve_default_base_url()` function reads the env on
   each `ClaudeSDKClient.__aenter__`. The module-level
   `DEFAULT_BASE_URL` constant is kept as a back-compat alias.

## `builtins_py.diff`

Inv 005 debug instrumentation: when `BASH_DEBUG_LOG_DIR` is set in the
subprocess env (passed via `bash_env`), every Bash subprocess
invocation dumps `command / cwd / timeout / elapsed / exit_code /
stdout / stderr` to `${BASH_DEBUG_LOG_DIR}/bash_NNNN.log`. No-op when
unset. Strictly additive — handler return shape is unchanged.

The agent's session log (in `<run_dir>/logs/session_NNN.log`) only
captures `AssistantMessage` content (the model's `tool_use` blocks),
not the `tool_result` content returned by the handler. Without this
patch we'd have no ground-truth record of what each subprocess
actually did — exactly the gap that hid the isinstance bug for the
whole of inv 004.

## `builtins_summary.diff`

Refactors `_make_bash_tool` to return a structured summary instead of
raw stdout/stderr. The body is small (~1,500 chars regardless of
subprocess output size) and includes:

- exit_code, elapsed
- stdout/stderr byte counts
- path to the full log on disk (set by `BASH_DEBUG_LOG_DIR`)
- detected event markers via regex (e.g. `LORA_ADAPTER_WRITTEN`,
  `EVAL_PREDICTIONS_WRITTEN`, `CUDA_OOM`, `VLLM_INIT_FAIL`)
- the last N lines of stdout (default 40, override via
  `BASH_RESULT_TAIL_LINES`)

Anthropic-style "tools return references, big artifacts live on disk"
pattern. See inv 005 Methods finding 6 and the
`handoff-artifact-design.md` doc in this investigation.

Verified in isolation (markers detect correctly; summary length
~1,500 chars on 31K-byte stdout). **NOT verified to unblock the
turn-1 post-tool-result hang** — the same hang reproduces with both
the raw-stdout and the small-summary payloads, indicating the hang is
not payload-size-related.

## `client_thinking.diff` + `types_thinking.diff` + `init_thinking.diff`

Adds a `thinking` branch to the shim's response handler so thinking
blocks emitted by reasoning models (nemotron-3-nano, qwen3.5,
qwen3) are preserved in `blocks_out` and
`assistant_content_for_history` instead of being silently dropped.
Adds `ThinkingBlock` to `types.py` and re-exports from `__init__.py`.

Motivation: nemotron's first turn returns `[ThinkingBlock,
ToolUseBlock]`. The prior loop had no branch for `thinking`, so the
thinking block was discarded; the next turn's POST then carried
`tool_use` without its required thinking sibling. Theory was that
the anthropic SDK's client-side validation rejects/hangs on the
malformed history. **Patch applied, hang did NOT resolve.** The
real root cause of the turn-1 hang is still open — likely something
else (httpx connection pool, anthropic SDK 0.78 beta-header
requirement for thinking, or a content-block shape issue in
Ollama's Anthropic-compat output). Tracked as the next debug
priority.

## How to apply

The shim is not in this repo's git tree. To apply on a fresh checkout
of the shim:

```bash
cd /home/tlifke/inv003_shim
patch -p2 -d shim_pkg/claude_agent_sdk         < .../client_py.diff
patch -p2 -d scripts/claude_agent_sdk_shim     < .../client_py.diff
patch -p2 -d shim_pkg/claude_agent_sdk         < .../builtins_py.diff
patch -p2 -d scripts/claude_agent_sdk_shim     < .../builtins_py.diff
```

The diffs target the `shim_pkg/` paths in their headers; `-p2` strips
the leading components so the same diff applies cleanly to either copy.
