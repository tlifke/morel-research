import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
top = int(sys.argv[2]) if len(sys.argv) > 2 else 3

nb = json.loads((out / "nbest_predictions_.json").read_text())
null_odds = json.loads((out / "null_odds_.json").read_text())

print("questions", len(nb))
print("nbest_depths", sorted({len(v) for v in nb.values()}))
for k, v in nb.items():
    print("==", k)
    print("   null_odds", round(null_odds[k], 4))
    for e in v[:top]:
        print("   {:.4f}  {}".format(e["probability"], repr(e["text"])[:200]))
