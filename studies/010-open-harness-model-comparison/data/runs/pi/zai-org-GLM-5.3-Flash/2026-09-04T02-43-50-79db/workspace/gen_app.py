#!/usr/bin/env python3
"""Generate the self-contained contract visualization app (index.html).

Reads contract_text/ and contract_ground_truth, embeds everything into a
single HTML file so the app runs by simply opening it in a browser —
no server, no network, no setup.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- load ground truth ----------
gold = {}
order = []
with open(os.path.join(HERE, "contract_ground_truth"), encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        cid = rec["contract_id"]
        gold[cid] = rec["gold"]
        order.append(cid)

categories = sorted({c for g in gold.values() for c in g})

# ---------- load contract texts ----------
contracts = []
missing = []
for cid in order:
    path = os.path.join(HERE, "contract_text", cid + ".txt")
    if not os.path.exists(path):
        missing.append(cid)
        continue
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # sanity: all spans in bounds
    for cat, info in gold[cid].items():
        if info.get("is_impossible"):
            assert info["spans"] == [], (cid, cat)
        else:
            for s, e in info["spans"]:
                assert 0 <= s < e <= len(text), (cid, cat, s, e, len(text))
    contracts.append({"id": cid, "text": text})

assert not missing, missing
assert len(contracts) == 510, len(contracts)

data = {
    "categories": categories,
    "contracts": contracts,
    "gold": gold,
}

with open(os.path.join(HERE, "app_template.html"), encoding="utf-8") as f:
    template = f.read()

payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
html = template.replace("/*__DATA__*/", payload)

out = os.path.join(HERE, "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Wrote {out}: {len(contracts)} contracts, {len(categories)} categories, "
      f"{os.path.getsize(out)/1e6:.1f} MB")
