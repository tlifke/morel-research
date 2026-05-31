import asyncio
import os
import sys
import logging
import anthropic

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
for noisy in ("httpcore.http11", "httpcore.connection"):
    logging.getLogger(noisy).setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

BASE = "http://100.106.241.33:11434"
MODEL = "nemotron-3-nano:4b"

TOOLS = [{
    "name": "Bash",
    "description": "run bash",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]
SLEEP_S = int(os.environ.get("SLEEP_S", "95"))


async def main():
    client = anthropic.AsyncAnthropic(base_url=BASE, api_key="ollama")
    try:
        print("[turn0] POST", flush=True)
        r = await client.messages.create(
            model=MODEL, max_tokens=512,
            system="You can call Bash. Use it once to print hello.",
            tools=TOOLS,
            messages=[{"role": "user", "content": "Use Bash to echo hello"}],
        )
        print(f"[turn0] stop={r.stop_reason} blocks={[b.type for b in r.content]}", flush=True)
        hist_assistant = []
        tool_use_id = None
        for b in r.content:
            if b.type == "thinking":
                entry = {"type": "thinking", "thinking": b.thinking}
                sig = getattr(b, "signature", None)
                if sig:
                    entry["signature"] = sig
                hist_assistant.append(entry)
            elif b.type == "text":
                hist_assistant.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                hist_assistant.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
                tool_use_id = b.id

        print(f"[between] sleeping {SLEEP_S}s to mimic Bash subprocess", flush=True)
        await asyncio.sleep(SLEEP_S)

        messages = [
            {"role": "user", "content": "Use Bash to echo hello"},
            {"role": "assistant", "content": hist_assistant},
            {"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": [{"type": "text", "text": "hello\n" * 200}],
                "is_error": False,
            }]},
        ]
        print("[turn1] POST", flush=True)
        try:
            r2 = await asyncio.wait_for(
                client.messages.create(
                    model=MODEL, max_tokens=256,
                    system="You can call Bash.",
                    tools=TOOLS, messages=messages,
                ),
                timeout=90,
            )
            print(f"[turn1] stop={r2.stop_reason}", flush=True)
        except asyncio.TimeoutError:
            print("[turn1] TIMEOUT after 90s (HANG REPRODUCED)", flush=True)
    finally:
        await client.close()


asyncio.run(main())
