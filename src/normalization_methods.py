"""
Normalization methods for multi-criteria decision analysis (MCDA).

Implements three normalization approaches and computes the concentration ratio
diagnostic described in:

  Oleson et al. "The normalization trap: how score scaling undermines
  multi-criteria decision analysis in conservation planning"
  Ecological Solutions and Evidence (in review). Preprint: https://doi.org/10.2139/ssrn.7485898

The three methods:
  1. Global linear (min-max across all paddocks and alternatives)
  2. Vector (Euclidean) normalization
  3. Within-unit (per-paddock min-max) — the recommended approach

The concentration ratio measures how unequally distributed an objective's
raw values are across spatial units. High concentration ratio (> 3) indicates
the normalization trap is likely to be severe.

Authors: Kirsten Oleson, Clay Trauernicht, Eric Lonsdorf, Elliott Parsons
"""

import numpy as np


# ── Normalization methods ────────────────────────────────────────────

def normalize_global_linear(scores: np.ndarray) -> np.ndarray:
    """
    Global linear (min-max) normalization.

    Rescales all values in the matrix to [0, 1] using the global
    minimum and maximum across ALL paddocks and ALL alternatives.

    Args:
        scores: array of shape (n_paddocks, n_alternatives) with raw scores

    Returns:
        Normalized array of same shape, values in [0, 1]
    """
    smin = scores.min()
    smax = scores.max()
    if smax == smin:
        return np.zeros_like(scores)
    return (scores - smin) / (smax - smin)


def normalize_vector(scores: np.ndarray) -> np.ndarray:
    """
    Vector (Euclidean) normalization.

    Divides each column (alternative) by its Euclidean norm across paddocks.
    Commonly used in TOPSIS and related methods (Hwang & Yoon 1981).

    Args:
        scores: array of shape (n_paddocks, n_alternatives)

    Returns:
        Normalized array of same shape
    """
    norms = np.sqrt((scores ** 2).sum(axis=0))
    norms[norms == 0] = 1.0
    return scores / norms


def normalize_within_unit(scores: np.ndarray) -> np.ndarray:
    """
    Within-unit (per-paddock) normalization.

    For each paddock independently, rescales the alternatives so that the
    best-performing alternative scores 1.0 and the worst scores 0.0.

    This separates:
      - Action effectiveness (which alternative is relatively best here?)
      - Spatial priority (which paddock is most valuable?) — handled by
        the budget constraint, not by normalization.

    Recommended for spatially explicit conservation optimization where
    objectives may be spatially concentrated.

    Args:
        scores: array of shape (n_paddocks, n_alternatives)

    Returns:
        Normalized array of same shape, each row independently scaled to [0, 1]
    """
    out = np.zeros_like(scores, dtype=float)
    for i in range(scores.shape[0]):
        row = scores[i, :]
        rmin, rmax = row.min(), row.max()
        if rmax > rmin:
            out[i, :] = (row - rmin) / (rmax - rmin)
        # If all alternatives have equal scores, row stays zero
    return out


# ── Concentration ratio ──────────────────────────────────────────

def concentration_ratio(raw_values: np.ndarray, top_k: int = 3) -> float:
    """
    Compute the concentration ratio: fraction of total objective value
    held by the top-k spatial units.

    A ratio > 0.5 (top-3 units hold >50% of total value) indicates
    meaningful spatial concentration. A ratio > 0.75 indicates severe
    concentration and a high risk of the normalization trap.

    Rule of thumb from paper:
        CR(3) < 0.4  → normalization method has minimal impact
        CR(3) 0.4–0.6 → worth comparing methods
        CR(3) > 0.6  → within-unit normalization strongly recommended

    Args:
        raw_values: 1-D array of raw objective values per spatial unit
        top_k: number of top units to include (default: 3)

    Returns:
        float in [0, 1]: share of total held by top-k units
    """
    vals = np.sort(raw_values)[::-1]  # descending
    total = vals.sum()
    if total == 0:
        return 0.0
    return float(vals[:top_k].sum() / total)


def gini_coefficient(raw_values: np.ndarray) -> float:
    """
    Gini coefficient of spatial concentration.

    0 = perfectly equal distribution across paddocks.
    1 = all value in one paddock.

    Complements the concentration ratio as a continuous measure.
    """
    x = np.sort(np.asarray(raw_values, dtype=float))
    n = len(x)
    if x.sum() == 0:
        return 0.0
    cumx = np.cumsum(x)
    return float((n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n)


# ── Comparison utility ────────────────────────────────────────────

def compare_normalization_methods(
    raw_scores: np.ndarray,
    weights: np.ndarray,
    paddock_names: list = None,
    alt_names: list = None,
) -> dict:
    """
    Compare all three normalization methods on the same raw scores.

    Computes the weighted sum for each paddock x alternative combination
    under each normalization method. Useful for showing how the choice
    of method changes which alternatives are preferred in each paddock.

    Args:
        raw_scores: array (n_paddocks, n_alternatives, n_objectives) or
                    dict of {objective: array (n_paddocks, n_alternatives)}
        weights: array of length n_objectives (must sum to 1)
        paddock_names: optional list of paddock labels
        alt_names: optional list of alternative labels

    Returns:
        dict with keys 'global_linear', 'vector', 'within_unit', each
        containing a (n_paddocks, n_alternatives) array of weighted scores
    """
    if isinstance(raw_scores, dict):
        obj_names = list(raw_scores.keys())
        n_p, n_a = list(raw_scores.values())[0].shape
        n_obj = len(obj_names)
        arr = np.stack([raw_scores[k] for k in obj_names], axis=2)
    else:
        arr = raw_scores
        n_p, n_a, n_obj = arr.shape
        obj_names = [f"obj_{i}" for i in range(n_obj)]

    assert len(weights) == n_obj, "weights length must match number of objectives"
    weights = np.asarray(weights) / np.asarray(weights).sum()

    results = {}
    for method_name, norm_fn in [
        ("global_linear", normalize_global_linear),
        ("vector", normalize_vector),
        ("within_unit", normalize_within_unit),
    ]:
        weighted = np.zeros((n_p, n_a))
        for k in range(n_obj):
            normed = norm_fn(arr[:, :, k])
            weighted += weights[k] * normed
        results[method_name] = weighted

    return results


# ── Quick demo ─────────────────────────────────────────────────

if __name__ == "__main__":
    # Minimal demo: 5 paddocks, 3 alternatives, 2 objectives
    # Objective 1 (T&E) is concentrated in paddock 1
    # Objective 2 (rancher) is distributed evenly
    np.random.seed(42)

    te_raw = np.array([
        [6, 4, 1],   # paddock 1: high T&E value
        [0, 0, 0],   # paddock 2: no T&E plants
        [1, 2, 0],
        [2, 3, 1],
        [0, 1, 0],
    ], dtype=float)

    rancher_raw = np.array([
        [3, 4, 1],
        [3, 4, 1],
        [3, 4, 1],
        [3, 4, 1],
        [3, 4, 1],
    ], dtype=float)

    cr = concentration_ratio(te_raw.max(axis=1), top_k=3)
    gini = gini_coefficient(te_raw.max(axis=1))
    print(f"T&E concentration ratio (top-3): {cr:.2f}")
    print(f"T&E Gini coefficient: {gini:.2f}")

    results = compare_normalization_methods(
        {"te": te_raw, "rancher": rancher_raw},
        weights=[0.8, 0.2],
    )

    print("\nWeighted scores by paddock under conservation priority (w_te=0.8):")
    print(f"{'Paddock':<10} {'Global':>10} {'Vector':>10} {'Within-unit':>12}")
    for i in range(5):
        gl = results["global_linear"][i].max()
        ve = results["vector"][i].max()
        wu = results["within_unit"][i].max()
        print(f"Paddock {i+1:<3} {gl:>10.3f} {ve:>10.3f} {wu:>12.3f}")
