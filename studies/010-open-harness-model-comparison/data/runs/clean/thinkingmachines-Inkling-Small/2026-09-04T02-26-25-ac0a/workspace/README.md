# Contract Visualization App

## How to use (no setup needed)

Open `app/index.html` in any modern web browser (Chrome, Firefox, Safari, Edge).

- The page loads all 510 contracts and ground-truth spans locally (no network).
- Use the dropdown to pick a contract.
- The contract text appears with every span highlighted by category color.
- Present categories are shown as chips on the right; click a chip to filter highlights to that category (click again to show all).

## What was verified

- All 510 contracts load.
- Highlights reconstructed from ground-truth character spans; reconstruction equals original text exactly.
- Screenshot of `2ThemartComInc_19990826...` rendered with 19 present categories and 30 spans shown.

## Files

- `app/index.html` — standalone application (27 MB embedded data, works offline).
- `build_app.py` — script that rebuilt the app from `contract_text/` and `contract_ground_truth`.
- `app/verify_screenshot.png` — sample render.
