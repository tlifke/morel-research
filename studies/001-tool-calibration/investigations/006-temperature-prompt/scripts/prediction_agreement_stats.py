"""Quantify how far Opus' predicted difficulty is from random, per model.

For each model (Gemma 3 4B IT, 12B IT) we have, per record:
  - curator (Opus) predicted bucket: trivial/easy/medium/hard/extreme
  - empirical success rate on n trials, and the bucket it falls into

Per model we report two flavours of agreement statistic:

  Bucketed (predicted bucket × empirical bucket):
    - quadratic-weighted Cohen's kappa
    - Kendall τ-b, Spearman ρ on bucket indices

  Continuous (predicted bucket × empirical success rate, no empirical
  bucketing — the natural fix for empirical-side range restriction):
    - Kendall τ-b, Spearman ρ
    - Jonckheere-Terpstra trend test: does empirical SR monotonically
      order across Opus's ordered prediction buckets?

We also print the marginal distributions of predicted and empirical
buckets per model, plus mean empirical SR per predicted bucket, so the
shape of any range restriction is visible directly.

Each statistic gets a 95% percentile bootstrap CI and a one-sided p-value
that it exceeds zero (better than random). The 12B − 4B difference is
estimated via paired bootstrap over records (predictions are shared, so
the per-record observation is (pred, sr_4b, sr_12b)).

Output: prints a table; writes a JSON sibling for citation.

Run from repo root with:
  CORPUS=a3_bulk uv run studies/001-tool-calibration/investigations/006-temperature-prompt/scripts/prediction_agreement_stats.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
INVESTIGATION_ROOT = HERE.parent
STUDY_ROOT = INVESTIGATION_ROOT.parent.parent
RESULTS_ROOT = STUDY_ROOT / "results"

sys.path.insert(0, str(STUDY_ROOT))
sys.path.insert(0, str(INVESTIGATION_ROOT / "figures"))
from harness.parser import classify_trial  # noqa: E402
from corpus_config import select_corpus  # noqa: E402

CORPUS = select_corpus()
SEEDS_PATH = STUDY_ROOT / CORPUS.seeds_filename

DATE = "2026-05-12"
BUCKETS = ["trivial", "easy", "medium", "hard", "extreme"]
BUCKET_IDX = {b: i for i, b in enumerate(BUCKETS)}
N_BOOT = 10_000
RNG = np.random.default_rng(20260522)


def _bucket_of(sr: float) -> str:
    if sr < 0.05: return "extreme"
    if sr < 0.30: return "hard"
    if sr < 0.70: return "medium"
    if sr < 0.95: return "easy"
    return "trivial"


def _safe(m: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", m)


def _per_record(model: str) -> dict[str, float]:
    path = RESULTS_ROOT / _safe(model) / CORPUS.results_filename_fmt.format(date=DATE)
    rows = [json.loads(l) for l in path.read_text().splitlines() if l]
    by = defaultdict(list)
    for r in rows:
        ok, _ = classify_trial(
            {"tool_target": r["tool_target"], "expected_tool_call": r["expected_tool_call"]},
            r.get("output") or r.get("output_preview", ""),
        )
        by[r["record_id"]].append(ok)
    return {k: sum(v) / len(v) for k, v in by.items()}


def quadratic_weighted_kappa(y_pred: np.ndarray, y_emp: np.ndarray, k: int = 5) -> float:
    """Quadratic-weighted Cohen's kappa over ordinal categories 0..k-1."""
    O = np.zeros((k, k), dtype=float)
    for a, b in zip(y_pred, y_emp):
        O[a, b] += 1
    O /= O.sum()
    row_marg = O.sum(axis=1, keepdims=True)
    col_marg = O.sum(axis=0, keepdims=True)
    E = row_marg @ col_marg
    i, j = np.indices((k, k))
    W = ((i - j) ** 2) / ((k - 1) ** 2)
    num = (W * O).sum()
    den = (W * E).sum()
    if den == 0:
        return 0.0
    return 1.0 - num / den


def _stats_bucketed(y_pred: np.ndarray, y_emp_bucket: np.ndarray) -> dict[str, float]:
    return {
        "kappa_qw": float(quadratic_weighted_kappa(y_pred, y_emp_bucket)),
        "tau_b_bucket": float(stats.kendalltau(y_pred, y_emp_bucket, variant="b").statistic),
        "rho_bucket": float(stats.spearmanr(y_pred, y_emp_bucket).statistic),
    }


TERTIARY = ["trivial", "middle", "impossible"]


def _to_tertiary(bucket_idx: np.ndarray) -> np.ndarray:
    """Map 5-bucket index → 3-class index: trivial(0) / middle(1) / impossible(2).
    Original buckets: trivial=0, easy=1, medium=2, hard=3, extreme=4.
    """
    out = np.where(bucket_idx == 0, 0, np.where(bucket_idx == 4, 2, 1))
    return out.astype(int)


def _stats_tertiary(pred_t: np.ndarray, emp_t: np.ndarray) -> dict[str, float]:
    """Stats on the 3-class collapse, plus the two endpoint binaries."""
    s: dict[str, float] = {}
    s["kappa_qw_3"] = float(quadratic_weighted_kappa(pred_t, emp_t, k=3))
    s["tau_b_3"] = float(stats.kendalltau(pred_t, emp_t, variant="b").statistic)

    pt_triv = (pred_t == 0).astype(int)
    et_triv = (emp_t == 0).astype(int)
    s["phi_trivial"] = _phi(pt_triv, et_triv)
    s["precision_trivial"] = _safe_div((pt_triv & et_triv).sum(), pt_triv.sum())
    s["recall_trivial"] = _safe_div((pt_triv & et_triv).sum(), et_triv.sum())

    pt_imp = (pred_t == 2).astype(int)
    et_imp = (emp_t == 2).astype(int)
    s["phi_impossible"] = _phi(pt_imp, et_imp)
    s["precision_impossible"] = _safe_div((pt_imp & et_imp).sum(), pt_imp.sum())
    s["recall_impossible"] = _safe_div((pt_imp & et_imp).sum(), et_imp.sum())
    return s


def _phi(x: np.ndarray, y: np.ndarray) -> float:
    """Phi coefficient for two binary vectors (= Pearson r for 0/1 data)."""
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _safe_div(num: float | int, den: float | int) -> float:
    return float(num) / float(den) if den else float("nan")


def _stats_continuous(y_pred: np.ndarray, sr: np.ndarray) -> dict[str, float]:
    return {
        "tau_b_sr": float(stats.kendalltau(y_pred, sr, variant="b").statistic),
        "rho_sr": float(stats.spearmanr(y_pred, sr).statistic),
        "jt_z": float(_jonckheere_z(y_pred, sr)),
    }


def _jonckheere_z(groups: np.ndarray, values: np.ndarray) -> float:
    """Jonckheere-Terpstra trend test z-statistic.

    H0: distribution of `values` is identical across ordered `groups`.
    HA: values stochastically increase with group index.
    Tests for a monotonic trend without assuming linearity or any
    particular within-group distribution. We return a signed z so that
    positive z = empirical SR increases with predicted-difficulty index
    (the "wrong" direction here — easier predicted ⇒ higher SR would
    give negative z). Bootstrap CIs over the raw z give a non-parametric
    confidence interval on the trend strength.
    """
    unique_groups = np.unique(groups)
    if unique_groups.size < 2:
        return 0.0
    J = 0
    for i in range(unique_groups.size):
        for j in range(i + 1, unique_groups.size):
            vi = values[groups == unique_groups[i]]
            vj = values[groups == unique_groups[j]]
            diff = vj[:, None] - vi[None, :]
            J += float(np.sum(diff > 0) + 0.5 * np.sum(diff == 0))
    ns = np.array([(groups == g).sum() for g in unique_groups], dtype=float)
    N = ns.sum()
    mean_J = (N * N - np.sum(ns * ns)) / 4.0
    var_J = (N * N * (2 * N + 3) - np.sum(ns * ns * (2 * ns + 3))) / 72.0
    if var_J <= 0:
        return 0.0
    return (J - mean_J) / np.sqrt(var_J)


def _bootstrap_ci(values: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    lo = float(np.quantile(values, alpha / 2))
    hi = float(np.quantile(values, 1 - alpha / 2))
    return lo, hi


def _one_sided_p_gt_zero(boot_values: np.ndarray) -> float:
    """Fraction of bootstrap draws ≤ 0; rough one-sided p that statistic>0."""
    return float((boot_values <= 0).mean())


def _two_sided_p(boot_values: np.ndarray) -> float:
    p_lo = float((boot_values <= 0).mean())
    p_hi = float((boot_values >= 0).mean())
    return float(min(1.0, 2 * min(p_lo, p_hi)))


def _per_model_stats(pred: np.ndarray, sr: np.ndarray, emp_bucket: np.ndarray) -> dict[str, float]:
    """All stats for one model, with sign convention: higher = better
    calibration. JT z is negated because higher predicted-difficulty
    index should correspond to *lower* empirical SR under good calibration.
    """
    s = {}
    s.update(_stats_bucketed(pred, emp_bucket))
    cont = _stats_continuous(pred, sr)
    s["tau_b_sr"] = -cont["tau_b_sr"]
    s["rho_sr"] = -cont["rho_sr"]
    s["jt_z_calibration"] = -cont["jt_z"]
    s.update(_stats_tertiary(_to_tertiary(pred), _to_tertiary(emp_bucket)))
    return s


def _contingency_3x3(pred_t: np.ndarray, emp_t: np.ndarray) -> list[list[int]]:
    M = np.zeros((3, 3), dtype=int)
    for a, b in zip(pred_t, emp_t):
        M[a, b] += 1
    return M.tolist()


def _marginal_counts(arr: np.ndarray) -> list[int]:
    return [int((arr == i).sum()) for i in range(len(BUCKETS))]


def _mean_sr_by_pred(pred: np.ndarray, sr: np.ndarray) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(BUCKETS)):
        mask = pred == i
        out.append(float(sr[mask].mean()) if mask.any() else None)
    return out


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    curator = {s["id"]: s["difficulty_label"]["value"] for s in seeds}

    sr_4b_map = _per_record("gemma3:4b-it-qat")
    sr_12b_map = _per_record("gemma3:12b-it-qat")

    rids = sorted(set(curator) & set(sr_4b_map) & set(sr_12b_map))
    rids = [r for r in rids if curator[r] in BUCKET_IDX]
    n = len(rids)

    pred = np.array([BUCKET_IDX[curator[r]] for r in rids])
    sr_4b = np.array([sr_4b_map[r] for r in rids], dtype=float)
    sr_12b = np.array([sr_12b_map[r] for r in rids], dtype=float)
    emp_4b = np.array([BUCKET_IDX[_bucket_of(s)] for s in sr_4b])
    emp_12b = np.array([BUCKET_IDX[_bucket_of(s)] for s in sr_12b])

    point = {
        "gemma3:4b-it-qat": _per_model_stats(pred, sr_4b, emp_4b),
        "gemma3:12b-it-qat": _per_model_stats(pred, sr_12b, emp_12b),
    }
    stat_names = list(point["gemma3:4b-it-qat"].keys())

    boot_4b = {k: np.empty(N_BOOT) for k in stat_names}
    boot_12b = {k: np.empty(N_BOOT) for k in stat_names}
    boot_diff = {k: np.empty(N_BOOT) for k in stat_names}

    idx_all = np.arange(n)
    for b in range(N_BOOT):
        idx = RNG.choice(idx_all, size=n, replace=True)
        s4 = _per_model_stats(pred[idx], sr_4b[idx], emp_4b[idx])
        s12 = _per_model_stats(pred[idx], sr_12b[idx], emp_12b[idx])
        for k in stat_names:
            boot_4b[k][b] = s4[k]
            boot_12b[k][b] = s12[k]
            boot_diff[k][b] = s12[k] - s4[k]

    pred_marginal = _marginal_counts(pred)
    emp_marginal_4b = _marginal_counts(emp_4b)
    emp_marginal_12b = _marginal_counts(emp_12b)

    pred_t = _to_tertiary(pred)
    emp_t_4b = _to_tertiary(emp_4b)
    emp_t_12b = _to_tertiary(emp_12b)
    cont_4b = _contingency_3x3(pred_t, emp_t_4b)
    cont_12b = _contingency_3x3(pred_t, emp_t_12b)
    mean_sr_by_pred_4b = _mean_sr_by_pred(pred, sr_4b)
    mean_sr_by_pred_12b = _mean_sr_by_pred(pred, sr_12b)

    report = {
        "corpus": CORPUS.name,
        "date": DATE,
        "n_records": n,
        "n_bootstrap": N_BOOT,
        "buckets": BUCKETS,
        "sign_convention": "higher = better calibration (jt/tau/rho_sr are negated)",
        "marginals": {
            "predicted": dict(zip(BUCKETS, pred_marginal)),
            "empirical_4b": dict(zip(BUCKETS, emp_marginal_4b)),
            "empirical_12b": dict(zip(BUCKETS, emp_marginal_12b)),
        },
        "tertiary_contingency_pred_x_emp": {
            "axes": TERTIARY,
            "gemma3:4b-it-qat": cont_4b,
            "gemma3:12b-it-qat": cont_12b,
        },
        "mean_empirical_sr_by_predicted_bucket": {
            "gemma3:4b-it-qat": dict(zip(BUCKETS, mean_sr_by_pred_4b)),
            "gemma3:12b-it-qat": dict(zip(BUCKETS, mean_sr_by_pred_12b)),
        },
        "per_model": {},
        "model_difference_12b_minus_4b": {},
    }

    for model, point_vals, boot_vals in [
        ("gemma3:4b-it-qat", point["gemma3:4b-it-qat"], boot_4b),
        ("gemma3:12b-it-qat", point["gemma3:12b-it-qat"], boot_12b),
    ]:
        block = {}
        for stat_name, v in point_vals.items():
            lo, hi = _bootstrap_ci(boot_vals[stat_name])
            p = _one_sided_p_gt_zero(boot_vals[stat_name])
            block[stat_name] = {"point": v, "ci95": [lo, hi], "p_one_sided_gt_0": p}
        report["per_model"][model] = block

    for stat_name in stat_names:
        diff_point = (
            point["gemma3:12b-it-qat"][stat_name]
            - point["gemma3:4b-it-qat"][stat_name]
        )
        lo, hi = _bootstrap_ci(boot_diff[stat_name])
        p = _two_sided_p(boot_diff[stat_name])
        report["model_difference_12b_minus_4b"][stat_name] = {
            "point": diff_point,
            "ci95": [lo, hi],
            "p_two_sided": p,
        }

    print(f"corpus={CORPUS.name}  n_records={n}  bootstrap={N_BOOT}")
    print()
    print("Marginal bucket counts (out of n):")
    print(f"  {'bucket':<10}" + "".join(f"{b:>10}" for b in BUCKETS))
    print(f"  {'predicted':<10}" + "".join(f"{c:>10}" for c in pred_marginal))
    print(f"  {'emp 4B':<10}" + "".join(f"{c:>10}" for c in emp_marginal_4b))
    print(f"  {'emp 12B':<10}" + "".join(f"{c:>10}" for c in emp_marginal_12b))
    print()
    print("Mean empirical SR within each predicted bucket (good calibration ⇒ monotone ↘):")
    print(f"  {'pred →':<10}" + "".join(f"{b:>10}" for b in BUCKETS))
    print(f"  {'4B':<10}" + "".join(
        f"{(v if v is not None else float('nan')):>10.3f}" for v in mean_sr_by_pred_4b))
    print(f"  {'12B':<10}" + "".join(
        f"{(v if v is not None else float('nan')):>10.3f}" for v in mean_sr_by_pred_12b))
    print()
    for model_label, cont in [("4B", cont_4b), ("12B", cont_12b)]:
        print(f"Tertiary 3×3 contingency ({model_label}) — rows=Opus pred, cols=empirical:")
        print(f"  {'':<12}" + "".join(f"{t:>12}" for t in TERTIARY))
        for i, t in enumerate(TERTIARY):
            print(f"  {t:<12}" + "".join(f"{cont[i][j]:>12}" for j in range(3)))
        print()

    print(f"{'model':<22} {'stat':<22} {'point':>8}  {'95% CI':<20}  {'p (>0)':>8}")
    print("-" * 86)
    for model in ("gemma3:4b-it-qat", "gemma3:12b-it-qat"):
        for stat_name, block in report["per_model"][model].items():
            lo, hi = block["ci95"]
            print(
                f"{model:<22} {stat_name:<22} {block['point']:>8.3f}  "
                f"[{lo:>+.3f}, {hi:>+.3f}]   {block['p_one_sided_gt_0']:>8.4f}"
            )
    print()
    print("Δ (12B − 4B), paired bootstrap over records:")
    print(f"{'stat':<22} {'point':>8}  {'95% CI':<20}  {'p (≠0)':>8}")
    print("-" * 64)
    for stat_name, block in report["model_difference_12b_minus_4b"].items():
        lo, hi = block["ci95"]
        print(
            f"{stat_name:<22} {block['point']:>+8.3f}  "
            f"[{lo:>+.3f}, {hi:>+.3f}]   {block['p_two_sided']:>8.4f}"
        )

    out_dir = INVESTIGATION_ROOT / "results-analysis"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"prediction_agreement_{CORPUS.name}_{DATE}.json"
    out_path.write_text(json.dumps(report, indent=2))
    print()
    print(f"wrote {out_path.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
