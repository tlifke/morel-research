# model-pricing skill

Fetches and maintains per-token pricing for HuggingFace-hosted models, stored
locally in `assets/model-pricing.json`.

## Usage

```bash
# Show the current pricing table
python .claude/skills/model-pricing/fetch_pricing.py show

# Set / update prices for one model
python .claude/skills/model-pricing/fetch_pricing.py set glm-5.3-flash \
    --input-per-1m 0.10 --output-per-1m 0.40

# Pull prices from HF hub metadata (where published)
python .claude/skills/model-pricing/fetch_pricing.py from-hf glm-5.3-flash inkling-small
```

## Asset format

`assets/model-pricing.json` maps model id → `{input_per_1m_usd, output_per_1m_usd,
context, updated, source}`. Entries are merged (not overwritten) on each run, so
prices you set manually persist until explicitly changed.

## Notes

- Prices are per **1M tokens**, USD, as published by HF / the model provider.
- `context` is the model's max context window in tokens.
- The `set` subcommand upserts; fields you omit are left unchanged.
- If HF does not publish pricing for a model (common for smaller/community
  models), fetch it manually and add it with `set`.
