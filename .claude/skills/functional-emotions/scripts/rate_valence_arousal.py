"""Rate each emotion word for valence and arousal (1-7) with Claude.

The paper did this for its 171 emotions and validated against human PAD norms on the
45 overlapping words (r=0.92 valence, r=0.90 arousal). The rating prompt below is OUR
wording (the paper does not print theirs) -- review it. Ratings are model-independent,
so run this once and reuse the YAML for every model you study.

Usage: python rate_valence_arousal.py --out runs/valence_arousal.yaml [--repeats 3]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import anthropic
import numpy as np
import yaml

DATA = Path(__file__).resolve().parent.parent / "data"
MODEL = "claude-opus-5-5"

PROMPT = """Rate each of the following emotion words on two dimensions, using a 1-7 scale:

- valence: how pleasant (7) vs unpleasant (1) the emotion is
- arousal: how activated / high-energy (7) vs deactivated / low-energy (1) the emotion is

Rate the typical meaning of the word as a human emotional state. Respond with ONLY a JSON
object mapping each word to {{"valence": <int>, "arousal": <int>}}, covering every word.

Words:
{words}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--repeats", type=int, default=3, help="average over independent calls")
    args = ap.parse_args()
    words = [l.strip() for l in (DATA / "emotions.txt").read_text().splitlines() if l.strip()]
    client = anthropic.Anthropic()
    runs = []
    for _ in range(args.repeats):
        with client.beta.messages.stream(
            model=MODEL, max_tokens=32000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": PROMPT.format(words="\n".join(words))}],
        ) as s:
            msg = s.get_final_message()
        text = "".join(b.text for b in msg.content if b.type == "text")
        obj = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        runs.append(obj)
    out = {}
    for w in words:
        vals = [r[w] for r in runs if w in r]
        if not vals:
            print(f"missing rating for {w!r}")
            continue
        out[w] = {k: round(float(np.mean([v[k] for v in vals])), 2) for k in ("valence", "arousal")}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(yaml.safe_dump(out, sort_keys=False))
    print(f"wrote {len(out)} ratings to {args.out}")


if __name__ == "__main__":
    main()
