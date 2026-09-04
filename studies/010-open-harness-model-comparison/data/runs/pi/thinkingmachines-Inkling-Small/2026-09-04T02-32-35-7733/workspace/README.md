# Contract Visualization App

Run locally with Python 3 (no network needed, no extra packages):

```bash
python3 visualizer.py
```

What it does:
- Loads all 510 contracts from `contract_text/` and ground truth from `contract_ground_truth`.
- Shows a selectable list of contracts.
- Displays the full text with every ground-truth span highlighted by category color.
- Shows present categories and how many highlights each has.

Verification performed:
- All 510 contracts load without error.
- For `GOOSEHEADINSURANCE,INC_04_02_2018-EX-10.6-Franchise Agreement` (97 spans), all 97 spans are highlighted correctly.
- Span text matches ground truth exactly (e.g., Agreement Date `[114,127]` → `June 21, 1999`).
