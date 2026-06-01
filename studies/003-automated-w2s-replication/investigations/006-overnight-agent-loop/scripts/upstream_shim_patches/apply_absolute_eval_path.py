#!/usr/bin/env python3
"""inv 006: resolve eval_output_path to ABSOLUTE in the Bash tool summary.

Overnight Run 2 failure mode: train.py prints the predictions file as
a RELATIVE path (`results/.../eval_output.json`). The Bash tool's
summary line echoes that as-is. The handoff writes it relative. When
the agent later constructs the absolute path for the
`evaluate_predictions` tool arg, it hallucinates an incorrect prefix
(observed: `/home/tlifke/.../data/eval_output.json` instead of
`.../results/eval_output.json`), and the tool rejects with
\"predictions_file not found\".

Same principle as yesterday's `predictions_file` change: don't make
the LLM reconstruct a path the system already knows. The shim's Bash
handler knows the subprocess `cwd` and can resolve absolute itself.

Fix:
1. Thread `cwd` into `_summarize_bash_result`.
2. After regex-extracting the relative path, resolve against `cwd`
   if it isn't already absolute.

Applied to both shim_v1 and shim_v2 builtins.py.
Idempotent.
"""
from __future__ import annotations
import os
from pathlib import Path

SHIM_V1 = Path("/home/tlifke/inv003_shim/shim_pkg/claude_agent_sdk/builtins.py")
SHIM_V2 = Path("/home/tlifke/inv003_shim/shim_v2_pkg/claude_agent_sdk/builtins.py")


def patch(p: Path) -> bool:
    src = p.read_text()
    if 'cwd=str(wd)' in src and 'os.path.isabs(_path)' in src:
        print(f"[{p.parent.parent.name}/{p.name}] already patched")
        return False

    # 1. Update signature
    old_sig = "def _summarize_bash_result(*, command, out, err, exit_code, elapsed, stdout_path):"
    new_sig = "def _summarize_bash_result(*, command, out, err, exit_code, elapsed, stdout_path, cwd=None):"
    if old_sig not in src:
        print(f"[{p.parent.parent.name}/{p.name}] signature anchor missing")
        return False
    src = src.replace(old_sig, new_sig)

    # 2. Resolve path if relative
    old_extract = (
        "                _path = _ep.group(1)\n"
        "                # train.py emits `eval_output_json=<path>`; strip that prefix\n"
        "                if \"eval_output_json=\" in _path:\n"
        "                    _path = _path.split(\"eval_output_json=\", 1)[1]\n"
        "                lines.append(f\"eval_output_path: {_path}\")\n"
    )
    new_extract = (
        "                _path = _ep.group(1)\n"
        "                # train.py emits `eval_output_json=<path>`; strip that prefix\n"
        "                if \"eval_output_json=\" in _path:\n"
        "                    _path = _path.split(\"eval_output_json=\", 1)[1]\n"
        "                # inv 006: resolve to absolute against Bash cwd so the\n"
        "                # downstream agent never has to construct it itself.\n"
        "                if cwd is not None and not os.path.isabs(_path):\n"
        "                    _path = os.path.normpath(os.path.join(str(cwd), _path))\n"
        "                lines.append(f\"eval_output_path: {_path}\")\n"
    )
    if old_extract not in src:
        print(f"[{p.parent.parent.name}/{p.name}] extract block missing")
        return False
    src = src.replace(old_extract, new_extract)

    # 3. Update the call site to pass cwd. Insert before the final `)` line.
    if "cwd=str(wd)" not in src:
        old_call_tail = (
            "            stdout_path=debug_path,\n"
            "        )"
        )
        new_call_tail = (
            "            stdout_path=debug_path,\n"
            "            cwd=str(wd),\n"
            "        )"
        )
        if old_call_tail not in src:
            print(f"[{p.parent.parent.name}/{p.name}] call site tail anchor missing")
            return False
        src = src.replace(old_call_tail, new_call_tail)

    p.write_text(src)
    print(f"[{p.parent.parent.name}/{p.name}] patched: eval_output_path now absolute")
    return True


def main():
    for p in (SHIM_V1, SHIM_V2):
        patch(p)


if __name__ == "__main__":
    main()
