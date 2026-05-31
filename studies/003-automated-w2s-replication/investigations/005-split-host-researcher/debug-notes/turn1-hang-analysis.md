# Turn-1 hang — investigation 2026-05-31

## TL;DR

**Cannot reproduce the hang.** Three reproducers exercising progressively
more of the real path all complete cleanly:

1. `/tmp/inv005_repro.py` — direct anthropic 0.78 client, turn 0 with
   `[thinking, tool_use]` against Mac Ollama, turn 1 with tool_result.
   PASS, ~6s.
2. `/tmp/inv005_repro2.py` — same plus 95-second `asyncio.sleep` between
   turns (mimics Bash), 1.2KB tool_result body, full httpx/httpcore DEBUG
   logging. PASS, ~108s. httpcore correctly detected the stale keepalive
   and opened a fresh socket for turn 1.
3. `/tmp/inv005_repro3.py` — full shim lifecycle: two `ClaudeSDKClient`
   sessions back-to-back, consumer breaks on `ResultMessage`. PASS — no
   orphan-task or pool-close race observed.

The latest live smoke run
(`q3_smoke_nemotron-3-nano_4b_p4_20260531_140053`) **also progressed past
turn 1**: Bash (3min 9s SFT+eval) → Grep → Read across three turns. Run
ended at 14:04:48 with no `# Ended` line, meaning external kill — not an
in-loop hang. So either the hang is now intermittent / wallclock-dependent,
or one of the recent shim patches already fixed it incidentally.

## Hypotheses, ruled out by evidence

**H1 — extended-thinking beta gating.** The shim's `_run_turn` does
**not forward `options.betas` to `messages.create`** at all
(`client.py:99-114`). So the over-the-wire request never sees any beta
header regardless of what the caller sets. Repro 1 sends thinking blocks
without any beta and gets a 200 back. Falsified.

**H2 — httpx connection pool.** Repro 2 with verbose httpcore logging
shows the pool correctly closes the stale keepalive socket after the
95-second idle gap and opens a fresh one (`close.started` → `close.complete`
→ `connect_tcp.started`). No pool deadlock. Falsified.

**H3 — Ollama Anthropic-compat output shape.** Confirmed: Mac Ollama
returns `{"type":"thinking","thinking":"..."}` with **no `signature`
field** (verified via direct curl). The SDK's `ThinkingBlockParam.signature`
is `Required` per the TypedDict, **but `Required` in `typing_extensions`
is a static type hint only — it is not enforced at runtime**. The shim
forwards the unsigned thinking block to `messages.create`, `maybe_transform`
passes it through, and the wire payload `{"type":"thinking","thinking":"..."}`
is accepted by Ollama on the way back in. Repro 1 confirms the round-trip
works. Falsified as the hang trigger.

## What is still a real bug worth fixing (orthogonal to the hang)

**Orphan `_run_turn` task.** `query()` does `asyncio.create_task(self._run_turn())`
and discards the handle. `__aexit__` does not cancel it before closing the
httpx client. In the current code path this doesn't manifest as a hang
(repro 3 confirms), but it is a lifecycle bug: in edge cases where the
consumer breaks the `async for` early (e.g. an exception in
`message_callback` at `agent.py:212`), the orphan task can attempt to call
`self._client.messages.create()` against a closed `AsyncAnthropic`, producing
a `RuntimeError: Cannot send a request, as the client has been closed.`
that surfaces as a noisy traceback in the session log rather than a clean
shutdown.

## Recommended next step

Since I cannot reproduce on the current state, the best next move is:

1. **Add `repro3`-style isolation tests to the shim's test suite** so this
   class of hang has a regression fence.
2. **Land the orphan-task lifecycle fix** as a defensive correctness patch
   even though it doesn't fix any currently-observed hang.
3. **When the hang next reproduces, capture more state**: `py-spy dump
   --pid <agent>` to see the exact Python stack, and `tcpdump -i tailscale0
   -A port 11434` for 10s on the desktop side to confirm whether the SDK
   ever calls `send()`. Without one of these the hang stays
   black-box.

## Proposed lifecycle patch (not yet applied)

`shim_pkg/claude_agent_sdk/client.py`:

```diff
 class ClaudeSDKClient:
     def __init__(self, options: Optional[ClaudeAgentOptions] = None):
         ...
+        self._run_task: Optional[asyncio.Task] = None

     async def query(self, prompt: str) -> None:
         self._history.append({"role": "user", "content": prompt})
         self._pending_queue = asyncio.Queue()
-        asyncio.create_task(self._run_turn())
+        self._run_task = asyncio.create_task(self._run_turn())

     async def __aexit__(self, exc_type, exc, tb) -> None:
+        if self._run_task is not None and not self._run_task.done():
+            self._run_task.cancel()
+            try:
+                await self._run_task
+            except (asyncio.CancelledError, Exception):
+                pass
         if self._client is not None:
             await self._client.close()
         self._client = None
```

## Things I made up that you should review

- I asserted `Required` in `ThinkingBlockParam` is not enforced at runtime.
  Verified by reading anthropic 0.78 `types/thinking_block_param.py` (it's
  a plain `TypedDict`); repro 1 then confirmed end-to-end. High confidence.
- I assumed "no `# Ended` line" in the 140053 session log means external
  kill rather than in-loop hang. Could be wrong if the agent crashed
  before the `finally:` block in `_run_session` executed — but `finally:`
  always runs unless the process was SIGKILLed.
- The recommendation to add py-spy and tcpdump capture is speculative
  about what would help; depending on harness constraints those may not
  be easy to wire in.

## Reproducer files

- `/tmp/inv005_repro.py` on desktop — minimal turn-0 + turn-1 round trip
- `/tmp/inv005_repro2.py` on desktop — with 95s sleep + httpx DEBUG
- `/tmp/inv005_repro3.py` on desktop — two-session lifecycle test
