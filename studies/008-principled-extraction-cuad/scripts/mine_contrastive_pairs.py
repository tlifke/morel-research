import json
import math
import random
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cuad_dataset import CuadDataset

STUDY = Path(__file__).resolve().parent.parent
PILOT = STUDY / "principles" / "pilot"
CONFIG = PILOT / "mining_config.yaml"

TOKEN_RE = re.compile(r"[a-z]+|<num>|<redacted>")
DIGITS_RE = re.compile(r"\d+")
STARS_RE = re.compile(r"\*{3,}")
WS_RE = re.compile(r"\s+")
PARA_RE = re.compile(r"\n\s*\n")
SENT_RE = re.compile(r"(?<=[.;:?!])\s{2,}")


def normalize(text):
    text = unicodedata.normalize("NFKC", text).lower()
    text = STARS_RE.sub(" <redacted> ", text)
    text = DIGITS_RE.sub(" <num> ", text)
    return WS_RE.sub(" ", text).strip()


def terms(text, ngrams):
    toks = TOKEN_RE.findall(normalize(text))
    out = set()
    for n in ngrams:
        for i in range(len(toks) - n + 1):
            out.add(" ".join(toks[i : i + n]))
    return out


def paragraphs(text):
    parts = []
    pos = 0
    for m in PARA_RE.finditer(text):
        parts.append((pos, m.start()))
        pos = m.end()
    parts.append((pos, len(text)))
    return [(a, b) for a, b in parts if b > a]


def chunk_text(text, cfg):
    lo, hi = cfg["target_chars"]
    pieces = []
    for start, end in paragraphs(text):
        if end - start <= hi:
            pieces.append((start, end))
            continue
        cursor = start
        for m in SENT_RE.finditer(text[start:end]):
            abs_end = start + m.start()
            if abs_end - cursor >= lo:
                pieces.append((cursor, abs_end))
                cursor = start + m.end()
        if cursor < end:
            pieces.append((cursor, end))

    merged = []
    for start, end in pieces:
        if merged and (end - start) < cfg["merge_below"]:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return [(a, b) for a, b in merged if b - a >= cfg["min_chars"]]


class Space:
    def __init__(self, unit_terms, min_df, max_df_fraction):
        n = len(unit_terms)
        df = defaultdict(int)
        for ts in unit_terms:
            for t in ts:
                df[t] += 1
        max_df = max_df_fraction * n
        vocab = {
            t: i
            for i, t in enumerate(
                sorted(t for t, c in df.items() if c >= min_df and c <= max_df)
            )
        }
        self.vocab = vocab
        self.idf = np.array(
            [math.log(n / df[t]) + 1.0 for t in sorted(vocab, key=vocab.get)],
            dtype=np.float64,
        )

    def encode(self, unit_terms):
        indptr = [0]
        indices = []
        for ts in unit_terms:
            cols = sorted({self.vocab[t] for t in ts if t in self.vocab})
            indices.extend(cols)
            indptr.append(len(indices))
        indices = np.array(indices, dtype=np.int32)
        binary = sparse.csr_matrix(
            (np.ones(len(indices), dtype=np.float64), indices, np.array(indptr)),
            shape=(len(unit_terms), len(self.vocab)),
        )
        weighted = binary.multiply(self.idf[None, :]).tocsr()
        return binary, weighted


def jaccard_block(w_a, mass_a, b_b, mass_b, threshold):
    inter = (w_a @ b_b.T).tocoo()
    union = mass_a[inter.row] + mass_b[inter.col] - inter.data
    with np.errstate(divide="ignore", invalid="ignore"):
        score = np.where(union > 0, inter.data / union, 0.0)
    keep = score >= threshold
    return inter.row[keep], inter.col[keep], score[keep]


def build_units(dataset, cats, cfg):
    ctx = cfg["context_expansion"]
    spans = []
    chunks = []
    absent_by_cat = defaultdict(list)
    for cid in dataset.contract_ids("model_train"):
        inst = dataset.get_instance(cid)
        text = inst.text
        absent_here = []
        for c in cats:
            g = inst.gold[c]
            if g.is_impossible:
                absent_here.append(c)
                continue
            for k, s in enumerate(g.spans):
                if len(s.text) < ctx["min_span_chars"]:
                    a = max(0, s.start - ctx["window_chars"])
                    b = min(len(text), s.end + ctx["window_chars"])
                    match_text = text[a:b]
                    expanded = True
                else:
                    match_text = s.text
                    expanded = False
                spans.append(
                    {
                        "contract_id": cid,
                        "category": c,
                        "span_index": k,
                        "start": s.start,
                        "end": s.end,
                        "text": s.text,
                        "match_text": match_text,
                        "context_expanded": expanded,
                    }
                )
        if absent_here:
            base = len(chunks)
            for a, b in chunk_text(text, cfg["chunking"]):
                chunks.append(
                    {"contract_id": cid, "start": a, "end": b, "text": text[a:b]}
                )
            for c in absent_here:
                absent_by_cat[c].extend(range(base, len(chunks)))
    return spans, chunks, absent_by_cat


def bare(unit):
    return dict(unit, match_text=unit["text"], context_expanded=False,
                gold_status="present")


def mine_cross_label(spans, w, b, mass, live, cfg):
    thr = cfg["pair_kinds"]["cross_label"]["threshold"]
    rows, cols, scores = jaccard_block(w[live], mass[live], b[live], mass[live], thr)
    out = []
    seen = set()
    for r, c, s in zip(rows, cols, scores):
        i, j = live[r], live[c]
        if i >= j:
            continue
        a, bb = spans[i], spans[j]
        if a["category"] == bb["category"]:
            continue
        if a["contract_id"] == bb["contract_id"]:
            if a["start"] < bb["end"] and bb["start"] < a["end"]:
                continue
        key = (
            a["contract_id"], a["start"], a["end"], a["category"],
            bb["contract_id"], bb["start"], bb["end"], bb["category"],
        )
        if key in seen:
            continue
        seen.add(key)
        left, right = (a, bb) if a["category"] < bb["category"] else (bb, a)
        out.append(
            {
                "kind": "cross_label",
                "similarity": round(float(s), 6),
                "category_pair": f"{left['category']} | {right['category']}",
                "same_contract": a["contract_id"] == bb["contract_id"],
                "left": bare(left),
                "right": bare(right),
            }
        )
    return out


def mine_present_absent(spans, chunks, chunk_terms, absent_by_cat, space, w, mass, live, cfg):
    pk = cfg["pair_kinds"]["present_absent"]
    thr, topk = pk["threshold"], pk["top_k_per_query"]
    cb, cw = space.encode(chunk_terms)
    cmass = np.asarray(cw.sum(axis=1)).ravel()
    cn = np.asarray(cb.sum(axis=1)).ravel()

    out = []
    by_cat = defaultdict(list)
    for i in live:
        by_cat[spans[i]["category"]].append(i)

    for cat in sorted(by_cat):
        cand = np.array(
            sorted(i for i in absent_by_cat.get(cat, []) if cn[i] >= cfg["similarity"]["min_terms_per_unit"]),
            dtype=np.int64,
        )
        if not len(cand):
            continue
        qs = np.array(by_cat[cat], dtype=np.int64)
        for start in range(0, len(qs), 64):
            block = qs[start : start + 64]
            rows, cols, scores = jaccard_block(
                w[block], mass[block], cb[cand], cmass[cand], thr
            )
            best = defaultdict(list)
            for r, c, s in zip(rows, cols, scores):
                best[int(r)].append((float(s), int(c)))
            for r, hits in best.items():
                hits.sort(key=lambda h: (-h[0], chunks[cand[h[1]]]["contract_id"], chunks[cand[h[1]]]["start"]))
                q = spans[block[r]]
                for s, c in hits[:topk]:
                    ch = chunks[cand[c]]
                    out.append(
                        {
                            "kind": "present_absent",
                            "similarity": round(s, 6),
                            "category_pair": f"{cat} | {cat} (absent)",
                            "same_contract": False,
                            "left": dict(q, gold_status="present"),
                            "right": {
                                "contract_id": ch["contract_id"],
                                "category": cat,
                                "span_index": None,
                                "start": ch["start"],
                                "end": ch["end"],
                                "text": ch["text"],
                                "match_text": ch["text"],
                                "context_expanded": False,
                                "gold_status": "absent",
                            },
                        }
                    )
    return out


def unit_key(side):
    return (side["contract_id"], side["category"], side["start"], side["end"],
            side["gold_status"])


def cap(pairs, per_group, total, per_unit):
    groups = defaultdict(int)
    degree = defaultdict(int)
    kept = []
    for p in sorted(
        pairs,
        key=lambda p: (-p["similarity"], p["left"]["contract_id"], p["left"]["start"]),
    ):
        if len(kept) >= total or groups[p["category_pair"]] >= per_group:
            continue
        keys = (unit_key(p["left"]), unit_key(p["right"]))
        if any(degree[k] >= per_unit for k in keys):
            continue
        groups[p["category_pair"]] += 1
        for k in keys:
            degree[k] += 1
        kept.append(p)
    return kept


def main():
    cfg = yaml.safe_load(CONFIG.read_text())
    cats = cfg["pilot_categories"]
    d = CuadDataset(categories=cats)

    spans, chunks, absent_by_cat = build_units(d, cats, cfg)
    ngrams = cfg["features"]["ngrams"]
    min_terms = cfg["similarity"]["min_terms_per_unit"]
    expanded_terms = [terms(s["match_text"], ngrams) for s in spans]
    bare_terms = [terms(s["text"], ngrams) for s in spans]
    chunk_terms = [terms(c["text"], ngrams) for c in chunks]
    space = Space(
        expanded_terms + chunk_terms,
        cfg["features"]["vocabulary_min_df"],
        cfg["features"]["vocabulary_max_df_fraction"],
    )

    def encode_live(unit_terms):
        b, w = space.encode(unit_terms)
        mass = np.asarray(w.sum(axis=1)).ravel()
        n = np.asarray(b.sum(axis=1)).ravel()
        live = np.array(
            [i for i in range(len(unit_terms)) if n[i] >= min_terms], dtype=np.int64
        )
        return b, w, mass, live

    xb, xw, xmass, xlive = encode_live(expanded_terms)
    bb_, bw, bmass, blive = encode_live(bare_terms)

    cross = mine_cross_label(spans, bw, bb_, bmass, blive, cfg)
    pres = mine_present_absent(
        spans, chunks, chunk_terms, absent_by_cat, space, xw, xmass, xlive, cfg
    )

    ck = cfg["pair_kinds"]["cross_label"]
    pk = cfg["pair_kinds"]["present_absent"]
    cross_kept = cap(
        cross, ck["max_pairs_per_category_pair"], ck["max_pairs_total"],
        ck["max_pairs_per_unit"],
    )
    pres_kept = cap(
        pres, pk["max_pairs_per_category"], pk["max_pairs_total"],
        pk["max_pairs_per_unit"],
    )

    ordered = sorted(
        cross_kept + pres_kept,
        key=lambda p: (
            p["kind"],
            p["category_pair"],
            -p["similarity"],
            p["left"]["contract_id"],
            p["left"]["start"],
            p["right"]["contract_id"],
            p["right"]["start"],
        ),
    )
    for n, p in enumerate(ordered, start=1):
        p["pair_id"] = f"pair-{n:04d}"

    groups = defaultdict(list)
    for p in ordered:
        groups[(p["kind"], p["category_pair"])].append(p)
    rng = random.Random(cfg["seed"])
    batch_no = 0
    for key in sorted(groups):
        items = groups[key]
        rng.shuffle(items)
        for i in range(0, len(items), cfg["batching"]["batch_size"]):
            batch_no += 1
            for p in items[i : i + cfg["batching"]["batch_size"]]:
                p["batch_id"] = f"cm-{batch_no:03d}"

    PILOT.mkdir(parents=True, exist_ok=True)
    with open(PILOT / "mined_pairs.jsonl", "w") as fh:
        for p in ordered:
            fh.write(json.dumps({"pair_id": p["pair_id"], **{k: v for k, v in p.items() if k != "pair_id"}}, ensure_ascii=False) + "\n")

    surfaced = defaultdict(int)
    for p in ordered:
        surfaced[p["category_pair"]] += 1
    summary = {
        "mining_version": cfg["version"],
        "split": cfg["split"]["name"],
        "n_contracts": len(d.contract_ids("model_train")),
        "n_gold_spans": len(spans),
        "n_gold_spans_live_bare": int(len(blive)),
        "n_gold_spans_live_context_expanded": int(len(xlive)),
        "n_candidate_chunks": len(chunks),
        "vocabulary_size": len(space.vocab),
        "n_candidates_cross_label": len(cross),
        "n_candidates_present_absent": len(pres),
        "n_surfaced_cross_label": len(cross_kept),
        "n_surfaced_present_absent": len(pres_kept),
        "n_surfaced_total": len(ordered),
        "n_batches": batch_no,
        "surfaced_by_category_pair": dict(sorted(surfaced.items())),
    }
    (PILOT / "mining_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
