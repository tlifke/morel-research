import asyncio
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SHIM_SCRIPTS = (
    Path(__file__).resolve().parents[3]
    / "003-claude-sdk-shim-and-researcher-swap"
    / "scripts"
)
sys.path.insert(0, str(SHIM_SCRIPTS))

from claude_agent_sdk_shim.builtins import (
    create_builtin_tools_server,
    is_long_bash_command,
    unload_ollama_model,
)
from claude_agent_sdk_shim.types import ClaudeAgentOptions


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


async def _invoke(server, name, args):
    tool = server.tools[name]
    res = tool.handler(args)
    if asyncio.iscoroutine(res):
        res = await res
    return res


def test_detection_heuristic():
    _assert(is_long_bash_command("python -m w2s_research.ideas.vanilla_w2s.run --train-size 64"), "module form")
    _assert(is_long_bash_command("/abs/.venv/bin/python -m w2s_research.core.train_eval"), "absolute interp")
    _assert(is_long_bash_command("uv run python -m w2s_research.ideas.vanilla_w2s.run"), "uv wrapper")
    _assert(not is_long_bash_command("ls -la"), "ls")
    _assert(not is_long_bash_command("python -c 'print(1)'"), "inline python")
    _assert(not is_long_bash_command("python -m pytest tests/"), "pytest")
    _assert(not is_long_bash_command(""), "empty")


def test_option_defaults_off():
    opts = ClaudeAgentOptions()
    _assert(opts.unload_ollama_on_long_bash is False, "default off")
    _assert(opts.ollama_unload_base_url is None, "url default none")


def test_from_registry_accepts_flag():
    opts = ClaudeAgentOptions.from_registry(
        "qwen3:4b", unload_ollama_on_long_bash=True
    )
    _assert(opts.unload_ollama_on_long_bash is True, "flag forwarded")


async def test_unload_fires_on_long_command():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(
            cwd=tmp,
            unload_ollama_on_long_bash=True,
            ollama_model="qwen3.5:4b",
            ollama_unload_base_url="http://stub:11434",
        )
        calls = []

        def fake_unload(model, base_url, timeout=10.0):
            calls.append((model, base_url))
            return {"ok": True}

        with patch("claude_agent_sdk_shim.builtins.unload_ollama_model", fake_unload):
            res = await _invoke(
                server,
                "Bash",
                {"command": "python -m w2s_research.ideas.vanilla_w2s.run --train-size 64"},
            )
        _assert(len(calls) == 1, f"unload should fire once, got {calls}")
        _assert(calls[0] == ("qwen3.5:4b", "http://stub:11434"), calls)
        _assert("exit_code:" in res["content"][0]["text"], res)


async def test_unload_does_not_fire_on_short_command():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(
            cwd=tmp,
            unload_ollama_on_long_bash=True,
            ollama_model="qwen3.5:4b",
        )
        calls = []

        def fake_unload(model, base_url, timeout=10.0):
            calls.append((model, base_url))
            return {"ok": True}

        with patch("claude_agent_sdk_shim.builtins.unload_ollama_model", fake_unload):
            await _invoke(server, "Bash", {"command": "echo hello"})
            await _invoke(server, "Bash", {"command": "ls -la"})
            await _invoke(server, "Bash", {"command": "python -c 'print(1)'"})
        _assert(calls == [], f"unload should never fire, got {calls}")


async def test_unload_disabled_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(
            cwd=tmp,
            ollama_model="qwen3.5:4b",
        )
        calls = []

        def fake_unload(model, base_url, timeout=10.0):
            calls.append((model, base_url))
            return {"ok": True}

        with patch("claude_agent_sdk_shim.builtins.unload_ollama_model", fake_unload):
            await _invoke(
                server,
                "Bash",
                {"command": "python -m w2s_research.ideas.vanilla_w2s.run --train-size 64"},
            )
        _assert(calls == [], f"unload must be opt-in, got {calls}")


async def test_unload_skipped_without_model():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(
            cwd=tmp,
            unload_ollama_on_long_bash=True,
            ollama_model=None,
        )
        calls = []

        def fake_unload(model, base_url, timeout=10.0):
            calls.append((model, base_url))
            return {"ok": True}

        with patch("claude_agent_sdk_shim.builtins.unload_ollama_model", fake_unload):
            await _invoke(
                server,
                "Bash",
                {"command": "python -m w2s_research.ideas.vanilla_w2s.run --train-size 64"},
            )
        _assert(calls == [], "no model => no-op")


async def test_unload_post_payload_shape():
    captured = {}

    class FakeResp:
        status = 200

        def read(self):
            return b'{"response": ""}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = req.data
        captured["headers"] = dict(req.header_items())
        return FakeResp()

    with patch("claude_agent_sdk_shim.builtins.urllib.request.urlopen", fake_urlopen):
        res = unload_ollama_model("qwen3.5:4b", "http://desk:11434")
    _assert(res["ok"], res)
    _assert(captured["url"] == "http://desk:11434/api/generate", captured)
    _assert(captured["method"] == "POST", captured)
    import json as _json
    payload = _json.loads(captured["body"].decode())
    _assert(payload["model"] == "qwen3.5:4b", payload)
    _assert(payload["keep_alive"] == 0, payload)


async def main():
    test_detection_heuristic()
    test_option_defaults_off()
    test_from_registry_accepts_flag()
    await test_unload_fires_on_long_command()
    await test_unload_does_not_fire_on_short_command()
    await test_unload_disabled_by_default()
    await test_unload_skipped_without_model()
    await test_unload_post_payload_shape()


if __name__ == "__main__":
    asyncio.run(main())
