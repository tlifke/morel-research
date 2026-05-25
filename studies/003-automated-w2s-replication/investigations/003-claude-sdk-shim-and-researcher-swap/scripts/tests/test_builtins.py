import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claude_agent_sdk_shim.builtins import create_builtin_tools_server


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)


async def _invoke(server, name, args):
    tool = server.tools[name]
    res = tool.handler(args)
    if asyncio.iscoroutine(res):
        res = await res
    return res


async def test_write_then_read():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(cwd=tmp)
        write_res = await _invoke(server, "Write", {"file_path": "hello.txt", "content": "world\n"})
        _assert(not write_res.get("is_error"), write_res)
        read_res = await _invoke(server, "Read", {"file_path": "hello.txt"})
        _assert(not read_res.get("is_error"), read_res)
        _assert(read_res["content"][0]["text"] == "world\n", read_res)


async def test_glob():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(cwd=tmp)
        for name in ("a.py", "b.py", "c.txt"):
            await _invoke(server, "Write", {"file_path": name, "content": "x"})
        res = await _invoke(server, "Glob", {"pattern": "*.py"})
        _assert(not res.get("is_error"), res)
        text = res["content"][0]["text"]
        _assert("a.py" in text and "b.py" in text and "c.txt" not in text, text)


async def test_grep():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(cwd=tmp)
        await _invoke(server, "Write", {"file_path": "data.txt", "content": "alpha\nbeta\nNEEDLE here\ngamma\n"})
        res = await _invoke(server, "Grep", {"pattern": "NEEDLE"})
        _assert(not res.get("is_error"), res)
        _assert("NEEDLE" in res["content"][0]["text"], res)


async def test_bash_echo():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(cwd=tmp)
        res = await _invoke(server, "Bash", {"command": "echo hello-from-bash"})
        _assert(not res.get("is_error"), res)
        _assert("hello-from-bash" in res["content"][0]["text"], res)
        _assert("exit_code: 0" in res["content"][0]["text"], res)


async def test_bash_timeout():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(cwd=tmp)
        res = await _invoke(server, "Bash", {"command": "sleep 5", "timeout": 1})
        _assert(res.get("is_error"), res)
        _assert("timed out" in res["content"][0]["text"], res)


async def test_bash_nonzero_exit():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(cwd=tmp)
        res = await _invoke(server, "Bash", {"command": "exit 7"})
        _assert("exit_code: 7" in res["content"][0]["text"], res)


async def test_edit():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(cwd=tmp)
        await _invoke(server, "Write", {"file_path": "f.txt", "content": "foo bar foo"})
        res = await _invoke(server, "Edit", {"file_path": "f.txt", "old_string": "foo", "new_string": "BAZ", "replace_all": True})
        _assert(not res.get("is_error"), res)
        read = await _invoke(server, "Read", {"file_path": "f.txt"})
        _assert(read["content"][0]["text"] == "BAZ bar BAZ", read)


async def test_websearch_stub_errors():
    with tempfile.TemporaryDirectory() as tmp:
        server = create_builtin_tools_server(cwd=tmp)
        res = await _invoke(server, "WebSearch", {})
        _assert(res.get("is_error"), res)


async def main():
    tests = [
        test_write_then_read,
        test_glob,
        test_grep,
        test_bash_echo,
        test_bash_timeout,
        test_bash_nonzero_exit,
        test_edit,
        test_websearch_stub_errors,
    ]
    failed = 0
    for t in tests:
        try:
            await t()
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    if failed:
        print(f"{failed}/{len(tests)} failed")
        sys.exit(1)
    print(f"ALL {len(tests)} PASS")


if __name__ == "__main__":
    asyncio.run(main())
