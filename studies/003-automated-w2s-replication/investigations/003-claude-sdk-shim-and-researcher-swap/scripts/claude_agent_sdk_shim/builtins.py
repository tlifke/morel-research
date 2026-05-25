import asyncio
import fnmatch
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .tools import SdkMcpServer, SdkTool, create_sdk_mcp_server


DEFAULT_BASH_TIMEOUT_SEC = 1800


def _ok(text: str) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _err(text: str) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "is_error": True}


def _resolve(path: str, cwd: Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (cwd / p).resolve()
    return p


def _make_bash_tool(
    cwd: Path,
    default_timeout: int,
    extra_env: Optional[Dict[str, str]] = None,
) -> SdkTool:
    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        command = args.get("command")
        if not command or not isinstance(command, str):
            return _err("Bash: missing 'command'")
        timeout = int(args.get("timeout", default_timeout))
        run_cwd = args.get("cwd")
        wd = _resolve(run_cwd, cwd) if run_cwd else cwd
        env = None
        if extra_env:
            env = dict(os.environ)
            env.update(extra_env)
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(wd),
                env=env,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return _err(f"Bash: timed out after {timeout}s")
        except Exception as e:
            return _err(f"Bash error: {e}")
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        body = f"exit_code: {proc.returncode}\n\n--- stdout ---\n{out}"
        if err.strip():
            body += f"\n--- stderr ---\n{err}"
        if proc.returncode != 0:
            return {"content": [{"type": "text", "text": body}], "is_error": False}
        return _ok(body)

    return SdkTool(
        name="Bash",
        description=(
            "Execute a bash command. Returns stdout, stderr, and exit code. "
            "Optional 'cwd' to override working directory; optional 'timeout' in seconds."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["command"],
        },
        handler=handler,
    )


def _make_read_tool(cwd: Path) -> SdkTool:
    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        file_path = args.get("file_path")
        if not file_path:
            return _err("Read: missing 'file_path'")
        p = _resolve(file_path, cwd)
        try:
            offset = int(args.get("offset", 0))
            limit = args.get("limit")
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if offset:
                lines = lines[offset:]
            if limit:
                lines = lines[: int(limit)]
            return _ok("".join(lines))
        except FileNotFoundError:
            return _err(f"Read: file not found: {p}")
        except Exception as e:
            return _err(f"Read error: {e}")

    return SdkTool(
        name="Read",
        description="Read a file from the local filesystem. Optional offset/limit for line ranges.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "offset": {"type": "integer"},
                "limit": {"type": "integer"},
            },
            "required": ["file_path"],
        },
        handler=handler,
    )


def _make_write_tool(cwd: Path) -> SdkTool:
    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        file_path = args.get("file_path")
        content = args.get("content")
        if not file_path:
            return _err("Write: missing 'file_path'")
        if content is None:
            return _err("Write: missing 'content'")
        p = _resolve(file_path, cwd)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content if isinstance(content, str) else str(content))
            return _ok(f"Wrote {len(content)} chars to {p}")
        except Exception as e:
            return _err(f"Write error: {e}")

    return SdkTool(
        name="Write",
        description="Write content to a file. Creates parent directories. Overwrites existing files.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["file_path", "content"],
        },
        handler=handler,
    )


def _make_edit_tool(cwd: Path) -> SdkTool:
    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        file_path = args.get("file_path")
        old_string = args.get("old_string")
        new_string = args.get("new_string")
        replace_all = bool(args.get("replace_all", False))
        if not file_path:
            return _err("Edit: missing 'file_path'")
        if old_string is None or new_string is None:
            return _err("Edit: missing old_string/new_string")
        p = _resolve(file_path, cwd)
        try:
            text = p.read_text(encoding="utf-8")
            count = text.count(old_string)
            if count == 0:
                return _err("Edit: old_string not found")
            if count > 1 and not replace_all:
                return _err(f"Edit: old_string occurs {count} times; pass replace_all=true")
            new_text = text.replace(old_string, new_string) if replace_all else text.replace(old_string, new_string, 1)
            p.write_text(new_text, encoding="utf-8")
            return _ok(f"Edited {p} ({count if replace_all else 1} replacement(s))")
        except Exception as e:
            return _err(f"Edit error: {e}")

    return SdkTool(
        name="Edit",
        description="Edit a file by replacing old_string with new_string. Use replace_all for multiple matches.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            "required": ["file_path", "old_string", "new_string"],
        },
        handler=handler,
    )


def _make_glob_tool(cwd: Path) -> SdkTool:
    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        pattern = args.get("pattern")
        if not pattern:
            return _err("Glob: missing 'pattern'")
        base = _resolve(args.get("path", "."), cwd)
        try:
            matches = sorted(str(p) for p in base.glob(pattern))
            return _ok("\n".join(matches) if matches else "(no matches)")
        except Exception as e:
            return _err(f"Glob error: {e}")

    return SdkTool(
        name="Glob",
        description="Glob for files matching a pattern. Optional 'path' to root the search.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern"],
        },
        handler=handler,
    )


def _make_grep_tool(cwd: Path) -> SdkTool:
    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        pattern = args.get("pattern")
        if not pattern:
            return _err("Grep: missing 'pattern'")
        base = _resolve(args.get("path", "."), cwd)
        glob_pat = args.get("glob") or "**/*"
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return _err(f"Grep: bad regex: {e}")
        max_matches = int(args.get("max_matches", 200))
        results: List[str] = []
        try:
            iterator = base.rglob(glob_pat) if "**" in glob_pat else base.glob(glob_pat)
            for path in iterator:
                if not path.is_file():
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append(f"{path}:{i}:{line.rstrip()}")
                                if len(results) >= max_matches:
                                    break
                except Exception:
                    continue
                if len(results) >= max_matches:
                    break
            return _ok("\n".join(results) if results else "(no matches)")
        except Exception as e:
            return _err(f"Grep error: {e}")

    return SdkTool(
        name="Grep",
        description="Search file contents with a regex. Optional 'path' root and 'glob' filter.",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "glob": {"type": "string"},
                "max_matches": {"type": "integer"},
            },
            "required": ["pattern"],
        },
        handler=handler,
    )


def _make_stub_tool(name: str) -> SdkTool:
    async def handler(args: Dict[str, Any]) -> Dict[str, Any]:
        return _err(f"{name} is not implemented in the local shim; skip and continue.")

    return SdkTool(
        name=name,
        description=f"{name} (stub — not implemented in shim, returns an error).",
        input_schema={"type": "object", "properties": {}, "required": []},
        handler=handler,
    )


def create_builtin_tools_server(
    cwd: Optional[str] = None,
    bash_timeout: int = DEFAULT_BASH_TIMEOUT_SEC,
    include_stubs: bool = True,
    bash_cwd: Optional[str] = None,
    bash_env: Optional[Dict[str, str]] = None,
) -> SdkMcpServer:
    base = Path(cwd).resolve() if cwd else Path.cwd()
    bash_base = Path(bash_cwd).resolve() if bash_cwd else base
    tools = [
        _make_bash_tool(bash_base, bash_timeout, extra_env=bash_env),
        _make_read_tool(base),
        _make_write_tool(base),
        _make_edit_tool(base),
        _make_glob_tool(base),
        _make_grep_tool(base),
    ]
    if include_stubs:
        tools.append(_make_stub_tool("WebSearch"))
        tools.append(_make_stub_tool("WebFetch"))
    return create_sdk_mcp_server(name="builtin", version="1.0.0", tools=tools)
