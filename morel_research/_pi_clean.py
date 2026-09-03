"""uv entry point shim: exec the scripts/pi-clean bash wrapper."""

import os
import sys
from pathlib import Path


def main() -> None:
    script = Path(__file__).resolve().parent.parent / "scripts" / "pi-clean"
    os.execvp(str(script), [str(script), *sys.argv[1:]])


if __name__ == "__main__":
    main()
