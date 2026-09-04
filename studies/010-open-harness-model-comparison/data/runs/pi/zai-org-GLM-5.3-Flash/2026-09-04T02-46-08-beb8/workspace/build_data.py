#!/usr/bin/env python3
"""Generate data.js: embeds all contract texts + ground-truth spans into one
JS file so the app runs offline from file:// with no server."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

records = []
with open(os.path.join(HERE, "contract_ground_truth"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

contracts = []
all_categories = set()
for rec in records:
    cid = rec["contract_id"]
    path = os.path.join(HERE, "contract_text", cid + ".txt")
    with open(path, encoding="utf-8") as tf:
        text = tf.read()
    cats = {}
    for cat, info in rec["gold"].items():
        all_categories.add(cat)
        if info.get("is_impossible"):
            continue
        spans = []
        for s in info.get("spans", []):
            # accept either [start, end] pairs or literal strings
            if isinstance(s, (list, tuple)) and len(s) == 2:
                start, end = int(s[0]), int(s[1])
            else:
                start = text.find(str(s))
                end = -1 if start < 0 else start + len(str(s))
            if 0 <= start < end <= len(text):
                spans.append([start, end])
        if spans:
            spans.sort()
            cats[cat] = spans
    contracts.append({"id": cid, "text": text, "cats": cats})

contracts.sort(key=lambda c: c["id"])
categories = sorted(all_categories)

with open(os.path.join(HERE, "data.js"), "w", encoding="utf-8") as out:
    out.write("window.CUAD_DATA = ")
    out.write(json.dumps({"categories": categories, "contracts": contracts},
                         ensure_ascii=False, separators=(",", ":")))
    out.write(";")

print(f"Wrote data.js: {len(contracts)} contracts, {len(categories)} categories")
