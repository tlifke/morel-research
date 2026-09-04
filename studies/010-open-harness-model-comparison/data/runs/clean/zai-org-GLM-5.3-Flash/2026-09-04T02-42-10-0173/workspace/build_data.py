#!/usr/bin/env python3
"""Regenerate data.js from contract_text/ and contract_ground_truth.

Run:  python3 build_data.py
Only needed if the source data changes; data.js is already built.
"""
import json
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))

contracts = []
gold = {}
with open(os.path.join(HERE, "contract_ground_truth"), encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        gold[rec["contract_id"]] = rec["gold"]

for path in sorted(glob.glob(os.path.join(HERE, "contract_text", "*.txt"))):
    cid = os.path.basename(path)[: -len(".txt")]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    contracts.append({"id": cid, "text": text})

payload = json.dumps(
    {"contracts": contracts, "gold": gold},
    ensure_ascii=False,
    separators=(",", ":"),
)
# Make safe to embed inside a <script src=...> JS file.
payload = payload.replace("</", "<\\/")

out = os.path.join(HERE, "data.js")
with open(out, "w", encoding="utf-8") as f:
    f.write("window.CONTRACT_DATA=" + payload + ";")

print(f"Wrote {out}: {len(contracts)} contracts, "
      f"{os.path.getsize(out) / 1e6:.1f} MB")
