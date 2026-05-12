"""Corpus selector for 006 figures.

Pick which seed corpus + grading run the figure scripts should pull from
via the CORPUS environment variable:

  CORPUS=a1_seed  (default) — n=36 seed pairs, Cell C neutral temp=1.0
  CORPUS=a3_bulk            — n=366 bulk corpus, neutral temp=1.0

Each script imports `select_corpus()` to get the active config and writes
its output PNG/HTML into the corresponding subfolder.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CorpusConfig:
    name: str
    seeds_filename: str
    results_filename_fmt: str  # gets formatted with DATE
    out_subdir: str
    n_records: int             # for figure titles
    trials_per_record: int     # for figure titles


CORPORA: dict[str, CorpusConfig] = {
    "a1_seed": CorpusConfig(
        name="a1_seed",
        seeds_filename="seeds.jsonl",
        results_filename_fmt="006_C_neutral_temp1_{date}.jsonl",
        out_subdir="a1_seed_n36",
        n_records=36,
        trials_per_record=10,
    ),
    "a3_bulk": CorpusConfig(
        name="a3_bulk",
        seeds_filename="bulk_seeds.jsonl",
        results_filename_fmt="007_bulk_neutral_temp1_{date}.jsonl",
        out_subdir="a3_bulk",
        n_records=366,
        trials_per_record=10,
    ),
}


def select_corpus() -> CorpusConfig:
    tag = os.environ.get("CORPUS", "a1_seed")
    if tag not in CORPORA:
        raise SystemExit(f"unknown CORPUS={tag!r}; valid: {list(CORPORA)}")
    return CORPORA[tag]


def out_dir(figures_root: Path) -> Path:
    """Ensure the corpus-specific output subdir exists and return it."""
    cfg = select_corpus()
    d = figures_root / cfg.out_subdir
    d.mkdir(parents=True, exist_ok=True)
    return d
