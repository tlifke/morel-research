"""python_execute — run a Python snippet in a subprocess; return stdout.

Minimal sandboxing: subprocess with a hard timeout, no network access
not enforced here (rely on the runtime environment to restrict if
needed). Suitable for the research seed corpus, NOT for untrusted
user input outside this repo.
"""

from __future__ import annotations

import subprocess
import sys

DEFAULT_TIMEOUT_SECONDS = 5


def python_execute(code: str, *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        return f"<python_execute error rc={result.returncode}>\n{result.stderr}"
    return result.stdout
