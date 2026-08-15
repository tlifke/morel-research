import hashlib
import json
import sys
import unicodedata
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cuad_dataset import CuadDataset
from mine_contrastive_pairs import WS_RE, terms

STUDY = Path(__file__).resolve().parent.parent
OUT_JSON = STUDY / "reviews" / "split-contamination-check.json"

SHINGLE_N = 5
JACCARD_THRESHOLD = 0.60
CONTAINMENT_THRESHOLD = 0.80
REPORT_FLOOR = 0.30

PAIR_ORDER = [
    ("ft_train", "holdout"),
    ("dev", "holdout"),
    ("dev", "ft_train"),
    ("holdout", "holdout"),
    ("ft_train", "ft_train"),
    ("dev", "dev"),
]


def whitespace_normal(text):
    return WS_RE.sub(" ", unicodedata.normalize("NFKC", text)).strip()


def main():
    d = CuadDataset()
    ids = d.all_contract_ids()
    texts = d.texts
    split_of = {cid: d.record(cid)["split"] for cid in ids}
    n_tokens = {cid: d.record(cid)["n_tokens"] for cid in ids}
    n_chars = {cid: d.record(cid)["n_chars"] for cid in ids}
    cats = d.categories

    raw_hash, norm_hash = {}, {}
    for cid in ids:
        raw = texts[cid]
        raw_hash[cid] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        norm = whitespace_normal(raw)
        norm_hash[cid] = hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def groups(hashes):
        buckets = {}
        for cid in ids:
            buckets.setdefault(hashes[cid], []).append(cid)
        return [sorted(v) for v in buckets.values() if len(v) > 1]

    exact_raw = groups(raw_hash)
    exact_norm = groups(norm_hash)

    vocab = {}
    indptr = [0]
    indices = []
    for cid in ids:
        row = set()
        for sh in terms(texts[cid], [SHINGLE_N]):
            row.add(vocab.setdefault(sh, len(vocab)))
        indices.extend(sorted(row))
        indptr.append(len(indices))
    matrix = csr_matrix(
        (np.ones(len(indices), dtype=np.float32), np.array(indices), np.array(indptr)),
        shape=(len(ids), len(vocab)),
    )
    sizes = np.asarray(matrix.sum(axis=1)).ravel()
    inter = (matrix @ matrix.T).toarray()

    pairs = []
    extremes = {}
    for i, j in combinations(range(len(ids)), 2):
        overlap = inter[i, j]
        if overlap == 0:
            continue
        union = sizes[i] + sizes[j] - overlap
        jac = overlap / union if union else 0.0
        cont = overlap / min(sizes[i], sizes[j]) if min(sizes[i], sizes[j]) else 0.0
        label = "x".join(sorted([split_of[ids[i]], split_of[ids[j]]]))
        best = extremes.setdefault(label, {"max_jaccard": 0.0, "max_containment": 0.0})
        best["max_jaccard"] = max(best["max_jaccard"], round(float(jac), 4))
        best["max_containment"] = max(best["max_containment"], round(float(cont), 4))
        if jac < REPORT_FLOOR and cont < CONTAINMENT_THRESHOLD:
            continue
        a, b = ids[i], ids[j]
        gold_a, gold_b = d.gold(a), d.gold(b)
        disagree = [c for c in cats if gold_a[c].is_impossible != gold_b[c].is_impossible]
        pairs.append(
            {
                "a": a,
                "b": b,
                "split_a": split_of[a],
                "split_b": split_of[b],
                "split_pair": "x".join(sorted([split_of[a], split_of[b]])),
                "cross_split": split_of[a] != split_of[b],
                "jaccard": round(float(jac), 4),
                "containment": round(float(cont), 4),
                "identical_raw": raw_hash[a] == raw_hash[b],
                "identical_normalized": norm_hash[a] == norm_hash[b],
                "n_chars_a": n_chars[a],
                "n_chars_b": n_chars[b],
                "n_tokens_a": n_tokens[a],
                "n_tokens_b": n_tokens[b],
                "gold_agrees_on_subset": not disagree,
                "gold_disagreements": disagree,
                "shorter_is_verbatim_substring": (
                    whitespace_normal(texts[b]) in whitespace_normal(texts[a])
                    if n_chars[a] >= n_chars[b]
                    else whitespace_normal(texts[a]) in whitespace_normal(texts[b])
                ),
                "flagged": bool(jac >= JACCARD_THRESHOLD or cont >= CONTAINMENT_THRESHOLD),
            }
        )
    pairs.sort(key=lambda p: (-p["containment"], -p["jaccard"]))

    report = {
        "method": {
            "exact": "sha256 over NFKC-normalized, whitespace-collapsed text; raw byte-identity reported separately",
            "near": f"{SHINGLE_N}-gram word shingles over the mine_contrastive_pairs.normalize token stream (NFKC, lowercase, digits -> <num>, redaction runs -> <redacted>); exhaustive all-pairs via sparse doc x shingle product",
            "metrics": "jaccard = |A&B|/|A|B|; containment = |A&B|/min(|A|,|B|)",
            "flag_threshold": f"jaccard >= {JACCARD_THRESHOLD} or containment >= {CONTAINMENT_THRESHOLD}",
            "report_floor": f"listed if jaccard >= {REPORT_FLOOR} or containment >= {CONTAINMENT_THRESHOLD}",
            "n_contracts": len(ids),
            "n_pairs_compared": len(ids) * (len(ids) - 1) // 2,
            "n_shingles": len(vocab),
        },
        "max_similarity_by_split_pair": {k: extremes.get(k, {}) for k in ["x".join(sorted(p)) for p in PAIR_ORDER]},
        "exact_groups_raw": exact_raw,
        "exact_groups_normalized": exact_norm,
        "pairs": pairs,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True))

    flagged = [p for p in pairs if p["flagged"]]
    summary = {"flagged_total": len(flagged), "by_split_pair": {}}
    for key in PAIR_ORDER:
        label = "x".join(sorted(key))
        summary["by_split_pair"][label] = sum(1 for p in flagged if p["split_pair"] == label)
    summary["exact_normalized_groups"] = len(exact_norm)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
