# Calibration harness

Skeleton for running the A1 seed corpus (and, later, the A3 bulk
corpus) against target models to populate
`difficulty_calibrated[model_id]` per record.

## Architecture

- **Laptop initiates** runs; results are written locally.
- **Desktop (`desktop-dcdbk1s`, Tailscale `100.97.4.17`, Windows + WSL)
  runs Ollama** as an HTTP server bound to the Tailscale interface
  (`OLLAMA_HOST=0.0.0.0:11434`). The laptop POSTs to
  `http://100.97.4.17:11434/api/generate` over Tailscale. No SSH in
  the hot path.
- **One-time SSH** to the desktop for setup (Ollama install, model
  pulls, env config) via the `ssh desktop` alias in `~/.ssh/config`.
- **Fallback / parallel:** Gemini API backend (uses `GEMINI_API_KEY`
  from `morel-primordia/.env.local` — Google AI Studio serves Gemma
  3 4B/12B IT under the same key).

## Files

| File                       | Purpose                                              |
|----------------------------|------------------------------------------------------|
| `inference.py`             | Backend abstractions; `OllamaBackend`, `GeminiBackend` |
| `prompt_format.py`         | Gemma 3 IT chat template + system prompt loading     |
| `parser.py`                | Detect tool calls in Gemma 3 IT output               |
| `runner.py`                | Main trial loop                                      |
| `results_schema.json`      | JSON Schema for per-run results files                |
| `setup_ollama_desktop.sh`  | One-shot setup script to run on desktop WSL          |

## Status

Skeleton only. Each module declares interfaces with stub
implementations marked `# TODO`. Real implementations land once the
user has authorized setup on the desktop and confirmed the target
model list. See `studies/001-tool-calibration/investigations/
002-difficulty-axes/calibration_cost_estimate.md` for cost / hardware
sizing.

## Running (intended once implemented)

```bash
# from laptop:
uv run harness/runner.py --model gemma3:4b-it-qat --backend ollama --n 20
uv run harness/runner.py --model gemma-3-12b-it --backend gemini --n 20
```

Results land under `results/{model_id}/{date}.jsonl` at the study
root. The runner is idempotent — re-runs append, don't overwrite,
and skip records that already have `n` trials for that model.
