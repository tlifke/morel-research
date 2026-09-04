# Contract Span Visualizer

Run the application locally with:

```bash
python3 app.py
```

What it does:
- Starts a local server on `http://localhost:8765`
- Opens your default browser automatically (if it doesn't, go to that URL)
- Loads all 510 contracts from `contract_text/` using `contract_ground_truth`
- Shows the full contract text with every span highlighted by category
- Lists the categories present for the selected contract

No network access, no external dependencies, no setup beyond running the command.
