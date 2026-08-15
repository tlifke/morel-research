#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
uv run --quiet python "$HERE/fetch_raw.py"
uv run --quiet --with transformers --with tokenizers python "$HERE/build_dataset.py"
