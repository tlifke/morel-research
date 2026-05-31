import asyncio
import os
import sys
import anthropic

BASE = os.getenv("MAC_OLLAMA", "http://100.106.241.33:11434")
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


async def turn0(client):
    print("[turn0] POST", flush=True)
    r = await client.messages.create(
        model=MODEL,
        max_tokens=512,
        system="You can call Bash. Use it once to print hello.",
        tools=TOOLS,
        messages=[{"role": "user", "content": "Use Bash to echo hello"}],
    )
    print(f"[turn0] stop={r.stop_reason} blocks={[b.type for b in r.content]}", flush=True)
    for b in r.content:
        print(f"  {b.type}: {getattr(b,'thinking',None) or getattr(b,'text',None) or getattr(b,'input',None)} sig={getattr(b,'signature',None)!r}", flush=True)
    return r


async def turn1(client, r):
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

    messages = [
        {"role": "user", "content": "Use Bash to echo hello"},
        {"role": "assistant", "content": hist_assistant},
        {"role": "user", "content": [{
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": [{"type": "text", "text": "hello"}],
            "is_error": False,
        }]},
    ]
    print(f"[turn1] history assistant blocks: {hist_assistant}", flush=True)
    print("[turn1] POST", flush=True)
    try:
        r2 = await asyncio.wait_for(
            client.messages.create(
                model=MODEL, max_tokens=256, system="You can call Bash.",
                tools=TOOLS, messages=messages,
            ),
            timeout=60,
        )
        print(f"[turn1] stop={r2.stop_reason}", flush=True)
    except asyncio.TimeoutError:
        print("[turn1] TIMEOUT after 60s (HANG REPRODUCED)", flush=True)


async def main():
    client = anthropic.AsyncAnthropic(base_url=BASE, api_key="ollama")
    try:
        r = await turn0(client)
        await turn1(client, r)
    finally:
        await client.close()


asyncio.run(main())
