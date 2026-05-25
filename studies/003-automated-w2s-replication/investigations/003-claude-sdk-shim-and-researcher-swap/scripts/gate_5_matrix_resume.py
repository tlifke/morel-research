import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_5_matrix import ssh_run, run_cell, REMOTE_BASE, collect_metrics


CELL_2_RUN_DIR = "/home/tlifke/inv003_shim/logs/gate_5_run_20260524_211821_qwen3.5_4b_nopatch"


def wait_for_cell_2():
    print("[resume] waiting for cell 2 (qwen3.5:4b nopatch) to finish", flush=True)
    while True:
        r = ssh_run("pgrep -f test_gate_5_full_loop.py || echo done")
        if "done" in r.stdout:
            break
        time.sleep(30)
    print("[resume] cell 2 finished", flush=True)


def main():
    matrix_path = Path(__file__).resolve().parent.parent / "logs" / f"gate_5_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    prior_files = sorted(matrix_path.parent.glob("gate_5_matrix_*.json"))
    results = []
    if prior_files:
        try:
            results = json.loads(prior_files[-1].read_text())
        except Exception:
            results = []

    wait_for_cell_2()

    cell_2 = collect_metrics(CELL_2_RUN_DIR)
    cell_2.update({
        "model": "qwen3.5:4b",
        "patch_on": False,
        "elapsed_sec": None,
        "rc": None,
        "run_dir": CELL_2_RUN_DIR,
    })
    print("=== cell 2 metrics ===", flush=True)
    print(json.dumps(cell_2, indent=2), flush=True)
    results.append(cell_2)
    matrix_path.write_text(json.dumps(results, indent=2))

    if cell_2.get("passed_gate_5"):
        print("*** cell 2 PASSED; stopping ***", flush=True)
        return

    print("\n=== running cell 3 (qwen3.5:4b + patch) ===", flush=True)
    cell_3 = run_cell("qwen3.5:4b", True, max_runtime_sec=600)
    results.append(cell_3)
    matrix_path.write_text(json.dumps(results, indent=2))

    print(f"\nwrote {matrix_path}", flush=True)


if __name__ == "__main__":
    main()
