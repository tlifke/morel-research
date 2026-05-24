"""Dump token-length distributions per (dataset, split) using the Qwen tokenizer.

Runs on the desktop inside the upstream repo's venv where transformers + the
Qwen tokenizer are already available.

Output: a JSON file at /tmp/prompt_lengths.json with structure:
    {
      "tokenizer": "Qwen/Qwen3-4B-Base",
      "splits": {
        "math": {"train_unlabel": [n1, n2, ...], "test": [...], "train_label": [...]},
        "chat": {...},
        "code": {...}
      }
    }
"""
import json
import sys
from pathlib import Path

from transformers import AutoTokenizer

REPO = Path("/home/tlifke/Projects/automated-w2s-research")
LABELED = REPO / "labeled_data"
DATASETS = ["math", "chat", "code"]
SPLITS = ["train_label", "train_unlabel", "test"]
TOKENIZER_NAME = "Qwen/Qwen3-4B-Base"


def extract_prompt(record: dict) -> str:
    if "question" in record:
        q = record.get("question", "")
        c = record.get("choice", "")
        return f"{q}\n{c}" if c else q
    if "prompt" in record:
        prompt = record.get("prompt", "")
        first = record.get("first", "")
        second = record.get("second", "")
        return f"{prompt}\n{first}\n{second}"
    return json.dumps(record)


def main() -> None:
    tok = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
    out = {"tokenizer": TOKENIZER_NAME, "splits": {}}
    for ds in DATASETS:
        out["splits"][ds] = {}
        for split in SPLITS:
            path = LABELED / ds / f"{split}.jsonl"
            if not path.exists():
                continue
            lengths = []
            with path.open() as f:
                for line in f:
                    rec = json.loads(line)
                    text = extract_prompt(rec)
                    lengths.append(len(tok.encode(text, add_special_tokens=False)))
            out["splits"][ds][split] = lengths
            print(f"{ds}/{split}: n={len(lengths)} min={min(lengths)} median={sorted(lengths)[len(lengths)//2]} max={max(lengths)}", file=sys.stderr)
    Path("/tmp/prompt_lengths.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main()
