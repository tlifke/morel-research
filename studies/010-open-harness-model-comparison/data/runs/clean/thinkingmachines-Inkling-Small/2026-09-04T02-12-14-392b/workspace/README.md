# Contract Visualization App

A self-contained HTML application that shows all 510 contracts and highlights every ground-truth span by category.

## How to use

1. Open `index.html` in any modern web browser (Chrome, Firefox, Safari, Edge).
2. No server, install, or network access is required.
3. Use the dropdown to pick any contract from the 510.
4. The page displays the contract ID, a list of present categories, and the full text with highlights matching the ground-truth spans.

## Verification done

- All 510 contracts loaded into `DATA_TEXTS`; all 41 categories loaded into `DATA_TRUTH`.
- Rendered a sample contract end-to-end and confirmed `inner_text` exactly matches the source file.
- Confirmed highlight counts and category badges align with ground truth.
- Screenshot saved as `contract_screenshot.png`.

## Files

- `index.html` — the full application (embedded data, ~29 MB)
- `build_app.py` — script that rebuilds `index.html` from `contract_text/` and `contract_ground_truth`
- `README.md` — this file
