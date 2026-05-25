import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_5_matrix import run_cell


def main():
    cells = [
        ("qwen3:8b", True),
        ("qwen3.5:9b", True),
    ]
    out_path = (
        Path(__file__).resolve().parent.parent
        / "logs"
        / f"gate_5_matrix_8b_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for model, patch in cells:
        res = run_cell(model, patch, max_runtime_sec=900)
        results.append(res)
        out_path.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
