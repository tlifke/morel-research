#!/usr/bin/env python3
"""Build index.html: a fully self-contained contract visualization app.

Embeds all 510 contract texts and their ground-truth category spans
from contract_ground_truth into a single HTML file that runs offline
(just open it in a browser -- no server, no network needed).
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

# Canonical 41-category order taken from the data.
categories: list[str] = []

contracts = []
with open(HERE / "contract_ground_truth", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        cid = rec["contract_id"]
        text = (HERE / "contract_text" / f"{cid}.txt").read_text(encoding="utf-8")
        cats = {}
        for cat, val in sorted(rec["gold"].items()):
            if cat not in categories:
                categories.append(cat)
            if not val["is_impossible"]:
                spans = [[int(s), int(e)] for s, e in val["spans"]]
                if spans:
                    cats[cat] = spans
        contracts.append({"id": cid, "text": text, "cats": cats})

data = {"categories": {c: 1 for c in categories}, "contracts": contracts}
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
# Prevent "</script>" from breaking out of the JSON script block.
payload = payload.replace("<", "\\u003c")

template = (HERE / "app_template.html").read_text(encoding="utf-8")
html = template.replace("__DATA__", payload)
out = HERE / "index.html"
out.write_text(html, encoding="utf-8")

n_spans = sum(len(c["cats"]) and sum(len(v) for v in c["cats"].values()) for c in contracts)
print(f"Wrote {out} ({out.stat().st_size/1e6:.1f} MB)")
print(f"{len(contracts)} contracts, {len(categories)} categories, {n_spans} spans embedded")
