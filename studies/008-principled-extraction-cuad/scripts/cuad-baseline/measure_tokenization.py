import json
import sys
from transformers import AutoTokenizer

src = json.load(open(sys.argv[1]))
members = set(open(sys.argv[2]).read().split("\n")) - {""}
ckpts = sys.argv[3:]

texts = [
    d["paragraphs"][0]["context"] for d in src["data"] if d["title"] in members
]
chars = sum(len(t) for t in texts)

for c in ckpts:
    tok = AutoTokenizer.from_pretrained(c, use_fast=True)
    n = 0
    windows = 0
    for t in texts:
        ids = tok(t, add_special_tokens=False)["input_ids"]
        n += len(ids)
        windows += max(1, -(-(max(0, len(ids) - 445)) // 256) + 1)
    print(
        json.dumps(
            {
                "ckpt": c,
                "contracts": len(texts),
                "chars": chars,
                "tokens": n,
                "chars_per_token": round(chars / n, 3),
                "windows_per_category": windows,
                "windows_per_contract_mean": round(windows / len(texts), 1),
            }
        )
    )
