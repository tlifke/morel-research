"""Generate the paper's synthetic datasets with Claude (off-policy for the studied model).

Kinds:
  stories              emotion x topic -> n stories (paper: 171 emotions x 100 topics x 12)
  neutral_dialogues    topic -> n emotionless Human/Assistant dialogues (used for the
                       confound-PCA projection)
  emotional_dialogues  (person_emotion, ai_emotion, topic) -> n dialogues (present- vs
                       other-speaker probes)

The output is append-only JSONL, one record per story/dialogue, so runs resume:
already-completed (kind, emotion(s), topic) cells are skipped.

PILOT FIRST. Repo policy (CLAUDE.md): bulk synthetic generation only after a human
approves seeds. Run with --pilot (a few emotions x few topics), have the human read
the output, then run the full grid.

Usage:
  python generate_dataset.py stories --out data/stories.jsonl --pilot
  python generate_dataset.py stories --out data/stories.jsonl --emotions-subset core12
  python generate_dataset.py neutral_dialogues --out data/neutral.jsonl --n-per-call 12
  python generate_dataset.py emotional_dialogues --out data/dialogues.jsonl --n-pairs 2000

Requires `pip install anthropic` and credentials (ANTHROPIC_API_KEY or `ant auth login`).
"""

from __future__ import annotations

import argparse
import json
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
import yaml

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
MODEL = "claude-opus-5-5"

# The 12 emotions the paper features in its tables/figures; a sensible small-model starting set.
CORE12 = ["happy", "inspired", "loving", "proud", "calm", "desperate", "angry", "guilty",
          "sad", "afraid", "nervous", "surprised"]

_lock = threading.Lock()


def load_lines(p: Path) -> list[str]:
    return [l.strip() for l in p.read_text().splitlines() if l.strip()]


def split_items(text: str, kind: str) -> list[str]:
    """Split '[story 1] ... [story 2] ...' (or [dialogue N]) into items."""
    tag = "story" if kind == "stories" else "dialogue"
    parts = re.split(rf"^\s*\[{tag}\s*\d+\]\s*$", text, flags=re.M | re.I)
    items = [p.strip() for p in parts if p.strip()]
    if kind != "stories":
        # Paper: post-hoc convert Person:/AI: to Human:/Assistant:.
        items = [re.sub(r"^Person:", "Human:", re.sub(r"^AI:", "Assistant:", it, flags=re.M), flags=re.M)
                 for it in items]
    return items


def call_claude(client: anthropic.Anthropic, prompt: str) -> str:
    # Opus 5.5: thinking is always on; effort is the depth control (default medium).
    # No temperature (removed on current models). Server-side fallback in case of a
    # classifier refusal (unlikely for this content).
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError("refused")
    return "".join(b.text for b in msg.content if b.type == "text")


def done_cells(out: Path) -> set[str]:
    if not out.exists():
        return set()
    return {json.loads(l)["cell"] for l in out.open() if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["stories", "neutral_dialogues", "emotional_dialogues"])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--n-per-call", type=int, default=12, help="paper: 12 stories per topic per emotion")
    ap.add_argument("--emotions-subset", default="all", help="all | core12 | comma-separated list")
    ap.add_argument("--topics-limit", type=int, default=100)
    ap.add_argument("--n-pairs", type=int, default=1000, help="emotional_dialogues: number of (emotion pair, topic) cells")
    ap.add_argument("--pilot", action="store_true", help="3 emotions x 2 topics (or 4 cells) for human review")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    templates = yaml.safe_load((DATA / "generation_prompts.yaml").read_text())
    all_emotions = load_lines(DATA / "emotions.txt")
    topics = load_lines(DATA / "topics.txt")[: args.topics_limit]
    if args.emotions_subset == "all":
        emotions = all_emotions
    else:  # comma list; the token "core12" expands to the paper's 12 featured emotions
        emotions = []
        for e in (x.strip() for x in args.emotions_subset.split(",")):
            for x in (CORE12 if e == "core12" else [e]):
                if x not in emotions:
                    emotions.append(x)
        unknown = set(emotions) - set(all_emotions)
        if unknown:
            print(f"warning: not in the paper's 171-emotion list: {sorted(unknown)}")

    rng = random.Random(args.seed)
    cells: list[dict] = []
    if args.kind == "stories":
        if args.pilot:
            emotions, topics = ["desperate", "calm", "happy"], topics[:2]
        for e in emotions:
            for t in topics:
                cells.append({"cell": f"stories|{e}|{t}", "emotion": e, "topic": t,
                              "prompt": templates["stories"].format(n_stories=args.n_per_call, topic=t, emotion=e)})
    elif args.kind == "neutral_dialogues":
        for t in topics[:2] if args.pilot else topics:
            cells.append({"cell": f"neutral|{t}", "topic": t,
                          "prompt": templates["neutral_dialogues"].format(n_stories=args.n_per_call, topic=t)})
    else:
        n = 4 if args.pilot else args.n_pairs
        for _ in range(n):
            pe, ae, t = rng.choice(emotions), rng.choice(emotions), rng.choice(topics)
            cells.append({"cell": f"dialogue|{pe}|{ae}|{t}", "person_emotion": pe, "ai_emotion": ae, "topic": t,
                          "prompt": templates["emotional_dialogues"].format(
                              n_stories=args.n_per_call, topic=t, person_emotion=pe, ai_emotion=ae)})

    seen = done_cells(args.out)
    todo = [c for c in cells if c["cell"] not in seen]
    print(f"{len(cells)} cells, {len(todo)} to do -> {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic()

    def work(c):
        text = call_claude(client, c["prompt"])
        items = split_items(text, args.kind)
        meta = {k: v for k, v in c.items() if k != "prompt"}
        with _lock, args.out.open("a") as f:
            for i, it in enumerate(items):
                f.write(json.dumps({**meta, "i": i, "text": it, "generator": MODEL}) + "\n")
        return c["cell"], len(items)

    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(work, c) for c in todo]
        for fut in as_completed(futs):
            try:
                cell, n = fut.result()
                if n != args.n_per_call:
                    print(f"  {cell}: got {n} items (asked {args.n_per_call}) -- check parsing")
            except Exception as exc:  # keep going; rerun to retry failed cells
                print(f"  failed: {exc!r}")


if __name__ == "__main__":
    main()
