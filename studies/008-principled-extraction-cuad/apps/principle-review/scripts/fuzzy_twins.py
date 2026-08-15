from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

APP_DIR = Path(__file__).resolve().parent.parent
STUDY_DIR = APP_DIR.parent.parent
sys.path.insert(0, str(STUDY_DIR / "scripts"))

from mine_contrastive_pairs import Space, chunk_text, jaccard_block, terms

MINING_CONFIG = STUDY_DIR / "principles" / "pilot" / "mining_config.yaml"
DETECTOR = "fuzzy_idf_jaccard"


def load_config(path: Path | None = None) -> dict:
    return yaml.safe_load((path or MINING_CONFIG).read_text())


class FuzzyTwins:
    def __init__(self, dataset, categories, config: dict, threshold: float | None = None):
        self.dataset = dataset
        self.categories = list(categories)
        self.config = config
        self.ngrams = tuple(config["features"]["ngrams"])
        self.min_terms = config["similarity"]["min_terms_per_unit"]
        self.ctx = config["context_expansion"]
        self.threshold = (
            threshold
            if threshold is not None
            else config["pair_kinds"]["present_absent"]["threshold"]
        )
        self.top_k = config["pair_kinds"]["present_absent"]["top_k_per_query"]
        self.version = config["version"]

    def match_text(self, text: str, start: int, end: int) -> tuple[str, bool]:
        if end - start >= self.ctx["min_span_chars"]:
            return text[start:end], False
        window = self.ctx["window_chars"]
        return text[max(0, start - window):min(len(text), end + window)], True

    def _build_chunks(self, texts: dict[str, str]):
        chunks = []
        absent_by_cat = defaultdict(list)
        cfg = self.config["chunking"]
        for contract_id in sorted(texts):
            record = self.dataset._records.get(contract_id)
            if not record:
                continue
            absent_here = [
                category
                for category in self.categories
                if not record["gold"].get(category, {}).get("spans")
            ]
            if not absent_here:
                continue
            base = len(chunks)
            for start, end in chunk_text(texts[contract_id], cfg):
                chunks.append(
                    {
                        "contract_id": contract_id,
                        "start": start,
                        "end": end,
                        "text": texts[contract_id][start:end],
                    }
                )
            for category in absent_here:
                absent_by_cat[category].extend(range(base, len(chunks)))
        return chunks, absent_by_cat

    def run(
        self,
        population: list[dict],
        texts: dict[str, str],
        corpus=None,
        min_containment: float = 0.0,
    ) -> dict[tuple, list[dict]]:
        queries = []
        for item in population:
            text = texts[item["contract_id"]]
            match, expanded = self.match_text(text, item["start"], item["end"])
            queries.append({"item": item, "match_text": match, "expanded": expanded})

        chunks, absent_by_cat = self._build_chunks(texts)
        query_terms = [terms(q["match_text"], self.ngrams) for q in queries]
        chunk_terms = [terms(c["text"], self.ngrams) for c in chunks]

        space = Space(
            query_terms + chunk_terms,
            self.config["features"]["vocabulary_min_df"],
            self.config["features"]["vocabulary_max_df_fraction"],
        )
        qb, qw = space.encode(query_terms)
        cb, cw = space.encode(chunk_terms)
        qmass = np.asarray(qw.sum(axis=1)).ravel()
        cmass = np.asarray(cw.sum(axis=1)).ravel()
        qn = np.asarray(qb.sum(axis=1)).ravel()
        cn = np.asarray(cb.sum(axis=1)).ravel()

        by_cat = defaultdict(list)
        for index, query in enumerate(queries):
            if qn[index] >= self.min_terms:
                by_cat[query["item"]["category"]].append(index)

        out: dict[tuple, list[dict]] = defaultdict(list)
        for category in sorted(by_cat):
            candidates = np.array(
                sorted(
                    i for i in absent_by_cat.get(category, [])
                    if cn[i] >= self.min_terms
                ),
                dtype=np.int64,
            )
            if not len(candidates):
                continue
            query_ids = np.array(by_cat[category], dtype=np.int64)
            for start in range(0, len(query_ids), 64):
                block = query_ids[start:start + 64]
                rows, cols, scores = jaccard_block(
                    qw[block], qmass[block], cb[candidates], cmass[candidates],
                    self.threshold,
                )
                best = defaultdict(list)
                for row, col, score in zip(rows, cols, scores):
                    best[int(row)].append((float(score), int(col)))
                for row, hits in best.items():
                    query = queries[int(block[row])]
                    item = query["item"]
                    key = (item["contract_id"], item["category"], item["span_index"])
                    eligible = []
                    for score, col in hits:
                        chunk = chunks[int(candidates[col])]
                        containment = (
                            corpus.containment(item["contract_id"], chunk["contract_id"])
                            if corpus is not None
                            else None
                        )
                        if containment is not None and containment < min_containment:
                            continue
                        eligible.append((score, col, containment))
                    for score, col, containment in sorted(
                        eligible, key=lambda x: (-x[0], x[1])
                    )[:self.top_k]:
                        chunk = chunks[int(candidates[col])]
                        record = self.dataset._records.get(chunk["contract_id"], {})
                        gold = record.get("gold", {}).get(category, {})
                        label = (
                            "marked_absent"
                            if gold.get("is_impossible")
                            else "not_annotated"
                        )
                        out[key].append(
                            {
                                "contract_id": chunk["contract_id"],
                                "split": (record or {}).get("split", "unassigned"),
                                "detector": DETECTOR,
                                "similarity": round(score, 4),
                                "doc_containment": (
                                    round(containment, 4) if containment is not None else None
                                ),
                                "twin_label": label,
                                "offsets": f"{chunk['start']}-{chunk['end']}",
                                "context_expanded": query["expanded"],
                                "passage": chunk["text"],
                            }
                        )
        return dict(out)
