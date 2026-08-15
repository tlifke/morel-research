import csv
import hashlib
import json
import random
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
import yaml
from scipy.sparse import csr_matrix
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mine_contrastive_pairs import WS_RE, terms

STUDY = Path(__file__).resolve().parent.parent
RAW = STUDY / "data" / "raw"
OUT = STUDY / "data" / "processed"
CONFIG = Path(__file__).resolve().parent / "config"

ATTRIBUTION = (
    "Derived from the Contract Understanding Atticus Dataset (CUAD) v1, "
    "The Atticus Project, licensed CC BY 4.0."
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_category_descriptions():
    rows = list(csv.DictReader(open(RAW / "category_descriptions.csv", encoding="utf-8-sig")))
    out = {}
    for row in rows:
        name = row["Category (incl. context and answer)"].split(": ", 1)[1].strip()
        out[name.lower()] = {
            "csv_name": name,
            "description": row["Description"].split(": ", 1)[1].strip(),
            "answer_format": row["Answer Format"].split(": ", 1)[1].strip()
            if ": " in row["Answer Format"]
            else row["Answer Format"].strip(),
            "group": row["Group"].split(": ", 1)[1].strip(),
        }
    return out


def parse_articles(path):
    data = json.load(open(path))["data"]
    parsed = {}
    for article in data:
        assert len(article["paragraphs"]) == 1, article["title"]
        para = article["paragraphs"][0]
        context = para["context"]
        gold = {}
        for qa in para["qas"]:
            category = qa["id"].split("__", 1)[1]
            spans = []
            for ans in qa["answers"]:
                start = ans["answer_start"]
                end = start + len(ans["text"])
                assert context[start:end] == ans["text"], (article["title"], category)
                spans.append([start, end])
            spans.sort()
            gold[category] = {"is_impossible": bool(qa["is_impossible"]), "spans": spans}
            assert bool(spans) != gold[category]["is_impossible"], (article["title"], category)
        parsed[article["title"]] = {"context": context, "gold": gold}
    return parsed


def bucket_of(n_tokens, edges, labels):
    for edge, label in zip(edges, labels):
        if n_tokens <= edge:
            return label
    return labels[-1]


def tercile_edges(values):
    ordered = sorted(values)
    n = len(ordered)
    return ordered[n // 3], ordered[2 * n // 3]


def largest_remainder(weights, n_target, capacities):
    keys = sorted(weights)
    total = sum(weights.values())
    if total == 0:
        return {k: 0 for k in keys}
    exact = {k: n_target * weights[k] / total for k in keys}
    alloc = {k: min(int(exact[k]), capacities[k]) for k in keys}
    for k in sorted(keys, key=lambda k: (-(exact[k] - alloc[k]), k)):
        if sum(alloc.values()) >= n_target:
            break
        if alloc[k] < capacities[k]:
            alloc[k] += 1
    while sum(alloc.values()) < n_target:
        headroom = [k for k in keys if alloc[k] < capacities[k]]
        if not headroom:
            break
        alloc[max(headroom, key=lambda k: (capacities[k] - alloc[k], k))] += 1
    return alloc


def stratified_sample(pool_by_bucket, bucket_targets, seed):
    rng = random.Random(seed)
    picked = []
    allocation = {}
    for bucket in sorted(bucket_targets):
        cells = pool_by_bucket.get(bucket, {})
        weights = {t: len(cells.get(t, [])) for t in sorted(cells)}
        alloc = largest_remainder(weights, bucket_targets[bucket], weights)
        for tercile in sorted(alloc):
            chosen = rng.sample(sorted(cells[tercile]), alloc[tercile])
            picked.extend(chosen)
            allocation[f"{bucket}|{tercile}"] = alloc[tercile]
    return sorted(picked), allocation


def assert_no_cross_split_duplicates(texts, split_of, cfg):
    ids = sorted(split_of)
    norm_hash = {}
    for cid in ids:
        norm = WS_RE.sub(" ", unicodedata.normalize("NFKC", texts[cid])).strip()
        norm_hash[cid] = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    by_hash = defaultdict(list)
    for cid in ids:
        by_hash[norm_hash[cid]].append(cid)
    for group in by_hash.values():
        splits = {split_of[c] for c in group}
        if len(group) > 1 and len(splits) > 1:
            raise AssertionError(
                "cross-split identical content: "
                + " | ".join(f"{c} [{split_of[c]}]" for c in sorted(group))
            )

    vocab = {}
    indptr = [0]
    indices = []
    for cid in ids:
        row = {vocab.setdefault(sh, len(vocab)) for sh in terms(texts[cid], [cfg["shingle_n"]])}
        indices.extend(sorted(row))
        indptr.append(len(indices))
    matrix = csr_matrix(
        (np.ones(len(indices), dtype=np.float32), np.array(indices), np.array(indptr)),
        shape=(len(ids), len(vocab)),
    )
    sizes = np.asarray(matrix.sum(axis=1)).ravel()
    inter = (matrix @ matrix.T).toarray()

    worst = None
    violations = []
    for i, j in combinations(range(len(ids)), 2):
        if split_of[ids[i]] == split_of[ids[j]]:
            continue
        overlap = inter[i, j]
        if overlap == 0:
            continue
        union = sizes[i] + sizes[j] - overlap
        jac = float(overlap / union) if union else 0.0
        cont = float(overlap / min(sizes[i], sizes[j])) if min(sizes[i], sizes[j]) else 0.0
        if worst is None or cont > worst[0]:
            worst = (cont, jac, ids[i], ids[j])
        if jac >= cfg["jaccard_threshold"] or cont >= cfg["containment_threshold"]:
            violations.append((cont, jac, ids[i], ids[j]))
    if violations:
        violations.sort(reverse=True)
        lines = [
            f"  containment={c:.3f} jaccard={j:.3f}  {a} [{split_of[a]}]  <->  {b} [{split_of[b]}]"
            for c, j, a, b in violations
        ]
        raise AssertionError(
            f"{len(violations)} cross-split near-duplicate pair(s) exceed the contamination "
            f"thresholds (jaccard>={cfg['jaccard_threshold']} or "
            f"containment>={cfg['containment_threshold']}). Splits are disjoint by contract_id "
            "but not by content; see reviews/split-contamination-check.md.\n" + "\n".join(lines)
        )
    return {
        "max_cross_split_containment": round(worst[0], 4) if worst else 0.0,
        "max_cross_split_jaccard": round(worst[1], 4) if worst else 0.0,
        "thresholds": {
            "jaccard": cfg["jaccard_threshold"],
            "containment": cfg["containment_threshold"],
        },
        "shingle_n": cfg["shingle_n"],
    }


def main():
    dataset_cfg = yaml.safe_load(open(CONFIG / "dataset.yaml"))
    subset_cfg = yaml.safe_load(open(CONFIG / "category_subset.yaml"))
    subset = [c["name"] for c in subset_cfg["categories"]]

    descriptions = load_category_descriptions()
    full = parse_articles(RAW / "CUADv1.json")
    test = parse_articles(RAW / "test.json")

    categories = list(next(iter(full.values()))["gold"])
    for cid, rec in full.items():
        assert list(rec["gold"]) == categories, cid
    missing = [c for c in categories if c.lower() not in descriptions]
    assert not missing, missing
    missing_subset = [c for c in subset if c not in categories]
    assert not missing_subset, missing_subset

    for cid, rec in test.items():
        assert full[cid]["context"] == rec["context"], cid
        assert full[cid]["gold"] == rec["gold"], cid

    tok = AutoTokenizer.from_pretrained(dataset_cfg["tokenizer"]["id"])
    add_special = dataset_cfg["tokenizer"]["add_special_tokens"]

    edges = dataset_cfg["length_buckets"]["edges"]
    labels = dataset_cfg["length_buckets"]["labels"]

    instances = {}
    for cid in sorted(full):
        context = full[cid]["context"]
        gold = full[cid]["gold"]
        n_tokens = len(tok.encode(context, add_special_tokens=add_special))
        instances[cid] = {
            "contract_id": cid,
            "title": cid,
            "n_chars": len(context),
            "n_tokens": n_tokens,
            "length_bucket": bucket_of(n_tokens, edges, labels),
            "n_positive_all": sum(1 for g in gold.values() if not g["is_impossible"]),
            "n_positive_subset": sum(1 for c in subset if not gold[c]["is_impossible"]),
            "text_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
            "gold": gold,
        }

    holdout = sorted(test)
    train_pool = sorted(set(full) - set(test))
    lo, hi = tercile_edges([instances[c]["n_positive_all"] for c in train_pool])

    def tercile(n):
        return "T1" if n < lo else ("T2" if n < hi else "T3")

    pool_by_bucket = defaultdict(lambda: defaultdict(list))
    for cid in train_pool:
        pool_by_bucket[instances[cid]["length_bucket"]][tercile(instances[cid]["n_positive_all"])].append(cid)
    pool_by_bucket = {b: dict(v) for b, v in pool_by_bucket.items()}
    stratum_sizes = {f"{b}|{t}": len(v) for b, cells in pool_by_bucket.items() for t, v in cells.items()}

    n_dev = dataset_cfg["splits"]["dev"]["n"]
    holdout_bucket_counts = Counter(instances[c]["length_bucket"] for c in holdout)
    pool_bucket_capacity = {lab: sum(len(v) for v in pool_by_bucket.get(lab, {}).values()) for lab in labels}
    bucket_targets = largest_remainder(
        {lab: holdout_bucket_counts.get(lab, 0) for lab in labels}, n_dev, pool_bucket_capacity
    )
    bucket_shortfall = {
        lab: {"target": bucket_targets[lab], "pool": pool_bucket_capacity[lab]}
        for lab in labels
        if bucket_targets[lab] > pool_bucket_capacity[lab]
    }

    seed = dataset_cfg["splits"]["seed"]
    dev, alloc = stratified_sample(pool_by_bucket, bucket_targets, seed)

    exclusions = {e["id"]: e for e in dataset_cfg["exclusions"]["contract_ids"]}
    unknown = [cid for cid in exclusions if cid not in full]
    assert not unknown, unknown
    assert not (set(exclusions) & set(holdout)), "exclusion targets holdout"
    assert not (set(exclusions) & set(dev)), "exclusion targets dev"
    excluded = sorted(exclusions)
    ft_train = sorted(set(train_pool) - set(dev) - set(exclusions))

    assert len(holdout) == dataset_cfg["splits"]["holdout"]["n"]
    assert len(dev) == dataset_cfg["splits"]["dev"]["n"]
    assert not (set(holdout) & set(dev))
    assert not (set(holdout) & set(ft_train))
    assert not (set(dev) & set(ft_train))
    assert set(holdout) | set(dev) | set(ft_train) | set(excluded) == set(full)
    assert len(holdout) + len(dev) + len(ft_train) + len(excluded) == len(full)

    split_of = {}
    for cid in holdout:
        split_of[cid] = "holdout"
    for cid in dev:
        split_of[cid] = "dev"
    for cid in ft_train:
        split_of[cid] = "ft_train"
    for cid in excluded:
        split_of[cid] = "excluded"

    guard = assert_no_cross_split_duplicates(
        {cid: full[cid]["context"] for cid in split_of if split_of[cid] != "excluded"},
        {cid: s for cid, s in split_of.items() if s != "excluded"},
        dataset_cfg["contamination_guard"],
    )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stats").mkdir(exist_ok=True)
    (OUT / "splits").mkdir(exist_ok=True)

    with open(OUT / "instances.jsonl", "w") as fh:
        for cid in sorted(instances):
            row = dict(instances[cid])
            row["split"] = split_of[cid]
            if cid in exclusions:
                row["exclusion_reason"] = exclusions[cid]["reason"]
                row["exclusion_twin_split"] = exclusions[cid]["twin_split"]
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    for name, members in (("dev", dev), ("holdout", holdout), ("ft_train", ft_train), ("excluded", excluded)):
        (OUT / "splits" / f"{name}.txt").write_text("\n".join(members) + "\n")

    with open(OUT / "categories.json", "w") as fh:
        json.dump(
            {
                "attribution": ATTRIBUTION,
                "all": categories,
                "subset_version": subset_cfg["version"],
                "subset": subset,
                "definitions": {
                    c: {
                        "description": descriptions[c.lower()]["description"],
                        "answer_format": descriptions[c.lower()]["answer_format"],
                        "group": descriptions[c.lower()]["group"],
                    }
                    for c in categories
                },
            },
            fh,
            indent=2,
            sort_keys=True,
        )

    length_rows = []
    for split, members in (("dev", dev), ("holdout", holdout), ("ft_train", ft_train), ("excluded", excluded), ("all", sorted(full))):
        toks = sorted(instances[c]["n_tokens"] for c in members)
        chars = sorted(instances[c]["n_chars"] for c in members)
        length_rows.append(
            {
                "split": split,
                "n": len(members),
                "median_chars": int(statistics.median(chars)),
                "median_tokens": int(statistics.median(toks)),
                "max_tokens": max(toks),
                "min_tokens": min(toks),
                "n_le_4k_tokens": sum(1 for t in toks if t <= 4000),
                "n_le_8k_tokens": sum(1 for t in toks if t <= 8000),
                "n_le_16k_tokens": sum(1 for t in toks if t <= 16000),
                "n_gt_16k_tokens": sum(1 for t in toks if t > 16000),
                "chars_per_token": round(sum(chars) / sum(toks), 3),
            }
        )
    with open(OUT / "stats" / "length_distribution.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(length_rows[0]))
        writer.writeheader()
        writer.writerows(length_rows)

    bucket_rows = []
    for split, members in (("dev", dev), ("holdout", holdout), ("ft_train", ft_train), ("excluded", excluded), ("all", sorted(full))):
        counts = Counter(instances[c]["length_bucket"] for c in members)
        bucket_rows.append({"split": split, **{lab: counts.get(lab, 0) for lab in labels}})
    with open(OUT / "stats" / "length_buckets.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(bucket_rows[0]))
        writer.writeheader()
        writer.writerows(bucket_rows)

    cat_rows = []
    for cat in categories:
        row = {"category": cat, "in_subset": cat in subset}
        for split, members in (("dev", dev), ("holdout", holdout), ("ft_train", ft_train), ("excluded", excluded), ("all", sorted(full))):
            pos = sum(1 for c in members if not instances[c]["gold"][cat]["is_impossible"])
            spans = sum(len(instances[c]["gold"][cat]["spans"]) for c in members)
            row[f"n_positive_{split}"] = pos
            row[f"n_spans_{split}"] = spans
        cat_rows.append(row)
    with open(OUT / "stats" / "category_counts.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(cat_rows[0]))
        writer.writeheader()
        writer.writerows(cat_rows)

    dev_bucket_counts = Counter(instances[c]["length_bucket"] for c in dev)
    length_profile_match = {
        lab: {
            "holdout_n": holdout_bucket_counts.get(lab, 0),
            "holdout_pct": round(100 * holdout_bucket_counts.get(lab, 0) / len(holdout), 1),
            "dev_target": bucket_targets[lab],
            "dev_n": dev_bucket_counts.get(lab, 0),
            "dev_pct": round(100 * dev_bucket_counts.get(lab, 0) / len(dev), 1),
            "train_pool_n": pool_bucket_capacity[lab],
        }
        for lab in labels
    }
    with open(OUT / "stats" / "dev_strata.json", "w") as fh:
        json.dump(
            {
                "stratification": "length_bucket primary (matched to holdout), positive_count_tercile secondary within bucket; see plans/decisions.md D-13",
                "positive_count_tercile_edges": {"lo": lo, "hi": hi},
                "stratum_pool_sizes": stratum_sizes,
                "stratum_allocation": alloc,
                "length_profile_match": length_profile_match,
                "bucket_shortfall": bucket_shortfall,
            },
            fh,
            indent=2,
            sort_keys=True,
        )

    manifest = {
        "attribution": ATTRIBUTION,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_config_version": dataset_cfg["version"],
        "category_subset_version": subset_cfg["version"],
        "source": {
            "repo": "https://github.com/TheAtticusProject/cuad",
            "files": {
                name: {"sha256": sha256_file(RAW / name), "bytes": (RAW / name).stat().st_size}
                for name in [
                    "data.zip",
                    "CUADv1.json",
                    "test.json",
                    "train_separate_questions.json",
                    "category_descriptions.csv",
                    "evaluate.py",
                ]
            },
        },
        "tokenizer": {
            "id": dataset_cfg["tokenizer"]["id"],
            "class": type(tok).__name__,
            "vocab_size": tok.vocab_size,
            "add_special_tokens": add_special,
        },
        "n_contracts": len(full),
        "n_categories": len(categories),
        "splits": {
            "seed": seed,
            "dev_stratification": "length_bucket primary matched to holdout; positive_count_tercile secondary within bucket (D-13)",
            "sizes": {
                "dev": len(dev),
                "holdout": len(holdout),
                "ft_train": len(ft_train),
                "excluded": len(excluded),
            },
            "dev_length_profile_match": length_profile_match,
            "dev_bucket_shortfall": bucket_shortfall,
        },
        "exclusions": {
            "applied_after_dev_sampling": True,
            "contracts": [
                {"contract_id": cid, "reason": exclusions[cid]["reason"], "twin_split": exclusions[cid]["twin_split"]}
                for cid in excluded
            ],
        },
        "contamination_guard": guard,
        "length_distribution": length_rows,
    }
    with open(OUT / "manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)

    print(json.dumps({"splits": manifest["splits"]["sizes"], "length": length_rows}, indent=2))


if __name__ == "__main__":
    main()
