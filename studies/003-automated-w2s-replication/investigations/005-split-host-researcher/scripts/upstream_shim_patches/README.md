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
