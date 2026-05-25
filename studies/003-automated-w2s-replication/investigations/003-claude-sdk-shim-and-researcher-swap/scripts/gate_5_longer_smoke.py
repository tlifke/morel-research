import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_5_matrix import run_cell


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-runtime-sec", type=int, default=2400)
    args = ap.parse_args()

    out_path = (
        Path(__file__).resolve().parent.parent
        / "logs"
        / f"gate_5_longer_smoke_{args.model.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    res = run_cell(args.model, True, max_runtime_sec=args.max_runtime_sec)
    out_path.write_text(json.dumps(res, indent=2))
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
