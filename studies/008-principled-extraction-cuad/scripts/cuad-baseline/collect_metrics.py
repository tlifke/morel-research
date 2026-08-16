import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for name in sys.argv[2:]:
    log = (root / "out" / name / "run.log").read_text(errors="replace")
    def find(pat, cast=float):
        m = re.search(pat, log)
        return cast(m.group(1)) if m else None
    rows.append(
        {
            "model": name,
            "features": find(r"Num examples = (\d+)", int),
            "gpu_eval_seconds": find(r"Evaluation done in total ([\d.]+) secs"),
            "sec_per_feature": find(r"\(([\d.]+) sec per example\)"),
            "wall_seconds": find(r"WALL_SECONDS ([\d.]+)"),
            "peak_vram_mib": find(r"PEAK_VRAM_MIB (\d+)", int),
        }
    )
print(json.dumps(rows, indent=2))
