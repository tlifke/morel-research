"""Reproducer testing whether dropping thinking blocks from assistant history
causes the turn-1 hang documented in inv 005 finding 7.

Three variants on the same connected client:
  A) full history with thinking block + tool_use + tool_result  (current fix)
  B) history with thinking block DROPPED (the buggy pre-fix shape)
  C) history with thinking block dropped, fresh client (control for stickiness)

If (B) hangs and (A) succeeds, the original hang trigger was the malformed
assistant turn (tool_use without paired thinking), not the connection pool
or SDK gating.

Run on desktop:
    /home/tlifke/Projects/automated-w2s-research/.venv/bin/python repro_hang.py
"""
import asyncio
import time

import anthropic


TOOLS = [
    {
        "name": "Bash",
        "description": "Run a bash command",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    }
]


def history(with_thinking: bool):
    asst = []
    if with_thinking:
        asst.append({"type": "thinking", "thinking": "I should call Bash."})
    asst.append(
        {"type": "tool_use", "id": "toolu_01", "name": "Bash", "input": {"command": "ls"}}
    )
    return [
        {"role": "user", "content": "Run ls then tell me the result."},
        {"role": "assistant", "content": asst},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01",
                    "content": [{"type": "text", "text": "file1\nfile2"}],
                }
            ],
        },
    ]


async def one_call(client, label, with_thinking, timeout=45):
    t0 = time.time()
    print(f"[{label}] sending (with_thinking={with_thinking})...", flush=True)
    try:
        resp = await asyncio.wait_for(
            client.messages.create(
                model="nemotron-3-nano:4b",
                max_tokens=200,
                messages=history(with_thinking),
                tools=TOOLS,
            ),
            timeout=timeout,
        )
        print(f"[{label}] OK {time.time()-t0:.1f}s stop={resp.stop_reason}", flush=True)
    except asyncio.TimeoutError:
        print(f"[{label}] TIMEOUT {time.time()-t0:.1f}s -- HANG REPRODUCED", flush=True)
    except Exception as e:
        print(f"[{label}] ERROR {time.time()-t0:.1f}s: {type(e).__name__}: {e}", flush=True)


async def main():
    c1 = anthropic.AsyncAnthropic(base_url="http://100.106.241.33:11434", api_key="ollama")
    await one_call(c1, "A_with_thinking", with_thinking=True)
    await one_call(c1, "B_no_thinking_same_client", with_thinking=False)
    await c1.close()

    c2 = anthropic.AsyncAnthropic(base_url="http://100.106.241.33:11434", api_key="ollama")
    await one_call(c2, "C_no_thinking_fresh_client", with_thinking=False)
    await c2.close()


if __name__ == "__main__":
    asyncio.run(main())
