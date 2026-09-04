# Contract Visualization

## How to run

Open a terminal in this directory and run:

```bash
python3 serve.py
```

This will:
- Build `contracts.json` and `data.json` from the local files
- Start a local web server on a free port
- Open your browser to the application automatically

No network access or additional setup is needed.

## How to use

- **Left sidebar**: Search and select any of the 510 contracts.
- **Contract text**: The full text is shown with every span highlighted.
- **Category badges**: Click any category to filter highlights to only that category; click "All" to see all present categories.
- **Highlights**: Each span is colored by category; hovering shows the category name(s).

All data is served from this directory (`contract_text/` and `contract_ground_truth`).
