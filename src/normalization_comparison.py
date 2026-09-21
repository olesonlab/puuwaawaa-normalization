"""
Normalization comparison for Puʻuwaʻawaʻa
=========================================

Compares three ways of normalizing conservation scores across:
  1. the real Puʻuwaʻawaʻa dataset
  2. simulated landscapes with varying ecological skewness

The three methods:
    global linear  min-max across all paddocks and alternatives
    vector         divide by the Euclidean norm of the score matrix
    within-unit    min-max within each paddock

For the empirical comparison the optimizer runs across scenarios and budgets
under each method, and the results record which alternatives are selected and
whether the optimizer can tell alternatives apart inside low-value paddocks.

Model structure matches pww_sdm_optimizer.py: paddocks choose among the ten
paddock-level alternatives, and the roadside fuelbreak (Alternative 2) is a
single landscape decision, built once for the reserve at a shared cost and
lowering fire probability in every paddock. Every scenario and budget is solved
with and without it, and the better solution is kept.

Usage:
    python normalization_comparison.py <input.xlsx> <output_dir> [--parts 1,3]
"""

import argparse
import json
import os
import warnings

import numpy as np
import pandas as pd
import pulp
from pulp import LpMaximize, LpProblem, LpStatus, LpVariable, lpSum, value

warnings.filterwarnings("ignore")

# ============================================================
# CONSTANTS
# ============================================================

FIXED_PADDOCK_IDX = 8   # paddock 9, pre-assigned
FIXED_ALT_IDX = 6       # alternative 7, full restoration

ROADSIDE_ALT_IDX = 1
ROADSIDE_COST = 137677.06
ROADSIDE_REDUCTION = 0.20

DIRECT_BENEFIT = np.array([1, 1, -1, 2, 3, 3, 6, 1, 2, 1, 1], dtype=float)
BUDGETS = [5_000_000, 10_000_000, 20_000_000, 40_000_000, 60_000_000]

N_PADDOCKS, N_ALTS = 22, 11
PADDOCK_ALTS = [j for j in range(N_ALTS) if j != ROADSIDE_ALT_IDX]
METHODS = ["global_linear", "vector", "within_unit"]


# ============================================================
# DATA
# ============================================================

def load_input_data(filepath):
    xls = pd.ExcelFile(filepath)
    sheet = "paddock_data" if "paddock_data" in xls.sheet_names else "data (2)"
    data = pd.read_excel(xls, sheet, header=None)

    costs = np.zeros((N_PADDOCKS, N_ALTS))
    for i in range(N_PADDOCKS):
        for j in range(N_ALTS):
            val = data.iloc[i + 2, 5 + j]
            costs[i, j] = val if pd.notna(val) else 0.0
    costs[:, ROADSIDE_ALT_IDX] = 0.0  # charged once, outside the paddock loop

    area_km2 = np.array([data.iloc[i + 2, 3] for i in range(N_PADDOCKS)], dtype=float) / 1e6

    rp = pd.read_excel(xls, "native_rareplants", header=None)
    te_count = np.array([rp.iloc[i + 4, 2] for i in range(N_PADDOCKS)], dtype=float)
    native_cover = np.array([rp.iloc[i + 4, 1] for i in range(N_PADDOCKS)], dtype=float)

    ppl = pd.read_excel(xls, "People", header=None)
    community_raw = np.zeros((N_PADDOCKS, N_ALTS))
    hunter_raw = np.zeros((N_PADDOCKS, N_ALTS))
    rancher_raw = np.zeros((N_PADDOCKS, N_ALTS))
    for i in range(N_PADDOCKS):
        for j in range(N_ALTS):
            for arr, col in ((community_raw, 2), (hunter_raw, 15), (rancher_raw, 28)):
                v = ppl.iloc[i + 2, col + j]
                arr[i, j] = v if pd.notna(v) else 0.0

    flam = pd.read_excel(xls, "flammability", header=None)
    fire_prob_baseline = np.zeros(N_PADDOCKS)
    fire_prob = np.zeros((N_PADDOCKS, N_ALTS))
    for i in range(N_PADDOCKS):
        fire_prob_baseline[i] = flam.iloc[i + 4, 1]
        for j in range(N_ALTS):
            fire_prob[i, j] = flam.iloc[i + 4, 5 + j]
    fire_prob[:, ROADSIDE_ALT_IDX] = fire_prob_baseline

    return {
        "costs": costs, "te_count": te_count, "native_cover": native_cover,
        "area_km2": area_km2,
        "community_raw": community_raw, "hunter_raw": hunter_raw,
        "rancher_raw": rancher_raw, "fire_prob_baseline": fire_prob_baseline,
        "fire_prob": fire_prob,
    }


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_global_linear(scores):
    smin, smax = scores.min(), scores.max()
    if smax == smin:
        return np.zeros_like(scores)
    return (scores - smin) / (smax - smin)


def normalize_vector(scores):
    norm = np.sqrt(np.sum(scores ** 2))
    if norm == 0:
        return np.zeros_like(scores)
    return scores / norm


def normalize_within_unit(scores):
    out = np.zeros_like(scores)
    for i in range(scores.shape[0]):
        row = scores[i, :]
        rmin, rmax = row.min(), row.max()
        if rmax > rmin:
            out[i, :] = (row - rmin) / (rmax - rmin)
    return out


# ============================================================
# SCORING
# ============================================================

def apply_roadside(fire_prob, roadside_built):
    if not roadside_built:
        return fire_prob
    return fire_prob * (1.0 - ROADSIDE_REDUCTION)


def compute_action_effectiveness(fire_prob_baseline, fire_prob):
    fire_reduction = fire_prob_baseline[:, None] - fire_prob
    max_reduction = fire_reduction.max()
    scaled = fire_reduction / max_reduction * 6.0 if max_reduction > 0 else np.zeros_like(fire_reduction)
    return DIRECT_BENEFIT[None, :] + scaled


def prepare_scores_method(input_data, method, roadside_built=False,
                          comm_method="global_linear"):
    """Normalized score matrices (21 x 10).

    `method` normalizes the two conservation sub-objectives, `comm_method` the
    three community ones, so the two choices can be crossed.
    """
    opt_indices = [i for i in range(N_PADDOCKS) if i != FIXED_PADDOCK_IDX]

    fire_prob = apply_roadside(input_data["fire_prob"], roadside_built)
    action_raw = compute_action_effectiveness(input_data["fire_prob_baseline"], fire_prob)
    action = action_raw[np.ix_(opt_indices, PADDOCK_ALTS)]

    if method in ("global_linear", "vector"):
        # The standard approach: scale action effectiveness by the paddock's
        # ecological metric, then normalize across the whole matrix.
        f = normalize_global_linear if method == "global_linear" else normalize_vector
        te_scores = f(action * input_data["te_count"][opt_indices, None])
        habitat_scores = f(action * input_data["native_cover"][opt_indices, None])
    elif method == "within_unit":
        within = normalize_within_unit(action)
        te_scores = within.copy()
        for idx, orig_i in enumerate(opt_indices):
            if input_data["te_count"][orig_i] == 0:
                te_scores[idx, :] = 0.0
        habitat_scores = within.copy()
    else:
        raise ValueError(f"unknown method: {method}")

    g = {"global_linear": normalize_global_linear, "vector": normalize_vector,
         "within_unit": normalize_within_unit}[comm_method]
    scores = {
        "te": te_scores,
        "habitat": habitat_scores,
        "recreationist": g(input_data["community_raw"][np.ix_(opt_indices, PADDOCK_ALTS)]),
        "hunter": g(input_data["hunter_raw"][np.ix_(opt_indices, PADDOCK_ALTS)]),
        "rancher": g(input_data["rancher_raw"][np.ix_(opt_indices, PADDOCK_ALTS)]),
    }
    return scores, opt_indices


# ============================================================
# SCENARIOS
# ============================================================

def build_scenarios():
    return {
        "S1_balanced": {"label": "Balanced", "eco_weight": 0.50,
                        "eco_split": (0.50, 0.50), "soc_split": (0.33, 0.33, 0.34)},
        "S2_conservation": {"label": "Conservation priority", "eco_weight": 0.80,
                            "eco_split": (0.50, 0.50), "soc_split": (0.33, 0.33, 0.34)},
        "S3_te_emphasis": {"label": "T&E emphasis", "eco_weight": 0.80,
                           "eco_split": (0.75, 0.25), "soc_split": (0.33, 0.33, 0.34)},
        "S4_habitat_emphasis": {"label": "Habitat emphasis", "eco_weight": 0.80,
                                "eco_split": (0.25, 0.75), "soc_split": (0.33, 0.33, 0.34)},
        "S5_community": {"label": "Community priority", "eco_weight": 0.20,
                         "eco_split": (0.50, 0.50), "soc_split": (0.33, 0.33, 0.34)},
        "S6_rancher_conservation": {"label": "Rancher-conservation", "eco_weight": 0.50,
                                    "eco_split": (0.50, 0.50), "soc_split": (0.70, 0.15, 0.15)},
        "S7_hunter_recreationist": {"label": "Hunter-recreationist", "eco_weight": 0.20,
                                    "eco_split": (0.50, 0.50), "soc_split": (0.10, 0.45, 0.45)},
    }


def effective_weights(scenario):
    eco = scenario["eco_weight"]
    soc = 1.0 - eco
    te_share, hab_share = scenario["eco_split"]
    ranch, hunt, rec = scenario["soc_split"]
    return {"te": eco * te_share, "habitat": eco * hab_share,
            "rancher": soc * ranch, "hunter": soc * hunt, "recreationist": soc * rec}


# ============================================================
# OPTIMIZER
# ============================================================

def optimize(scores, costs, budget, weights):
    """One paddock-level alternative per paddock, subject to a budget."""
    n_paddocks, n_alts = costs.shape
    prob = LpProblem("PWW", LpMaximize)
    x = [[LpVariable(f"x_{i}_{j}", cat="Binary") for j in range(n_alts)]
         for i in range(n_paddocks)]

    prob += lpSum(w * scores[key][i, j] * x[i][j]
                  for key, w in weights.items() if w
                  for i in range(n_paddocks) for j in range(n_alts))
    for i in range(n_paddocks):
        prob += lpSum(x[i]) == 1
    prob += lpSum(costs[i, j] * x[i][j]
                  for i in range(n_paddocks) for j in range(n_alts)) <= budget

    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    if LpStatus[prob.status] != "Optimal":
        return None

    choices = np.array([next(j for j in range(n_alts) if value(x[i][j]) > 0.5)
                        for i in range(n_paddocks)])
    return {
        "choices": choices,
        "total_cost": float(sum(costs[i, choices[i]] for i in range(n_paddocks))),
        "objective_value": float(value(prob.objective)),
        "sub_scores": {k: float(sum(scores[k][i, choices[i]] for i in range(n_paddocks)))
                       for k in scores},
    }


def solve_scenario_budget(input_data, method, weights, budget,
                          comm_method="global_linear"):
    """Solve with and without the roadside fuelbreak; keep the better solution."""
    fixed_cost = input_data["costs"][FIXED_PADDOCK_IDX, FIXED_ALT_IDX]
    best = None
    for roadside_built in (False, True):
        scores, opt_indices = prepare_scores_method(
            input_data, method, roadside_built, comm_method)
        available = budget - fixed_cost - (ROADSIDE_COST if roadside_built else 0.0)
        if available < 0:
            continue
        costs_opt = input_data["costs"][np.ix_(opt_indices, PADDOCK_ALTS)]
        res = optimize(scores, costs_opt, available, weights)
        if res is None:
            continue
        res["roadside_built"] = roadside_built
        res["total_cost"] += fixed_cost + (ROADSIDE_COST if roadside_built else 0.0)
        if best is None or res["objective_value"] > best["objective_value"] + 1e-9:
            best = res
    return best


# ============================================================
# PART 1: EMPIRICAL COMPARISON
# ============================================================

def run_empirical_comparison(filepath, output_dir):
    print("=" * 70)
    print("PART 1: EMPIRICAL COMPARISON AT PUʻUWAʻAWAʻA")
    print("=" * 70)

    input_data = load_input_data(filepath)
    scenarios = build_scenarios()
    rows = []

    for method in METHODS:
        print(f"\n--- Method: {method} ---")
        scores, _ = prepare_scores_method(input_data, method, roadside_built=False)
        te = scores["te"]
        spreads = te.max(axis=1) - te.min(axis=1)
        print(f"  T&E score range across the matrix: {te.max() - te.min():.4f}")
        print(f"  Paddocks with T&E spread < 0.05: {int((spreads < 0.05).sum())}/21")

        for sdef in scenarios.values():
            w = effective_weights(sdef)
            for budget in BUDGETS:
                res = solve_scenario_budget(input_data, method, w, budget)
                if res is None:
                    continue
                choices = res["choices"]
                alts = [PADDOCK_ALTS[c] + 1 for c in choices]
                counts = {a: alts.count(a) for a in sorted(set(alts))}
                rows.append({
                    "method": method,
                    "scenario": sdef["label"],
                    "budget": budget,
                    "budget_M": budget / 1e6,
                    "roadside_built": res["roadside_built"],
                    "total_cost": res["total_cost"],
                    "n_conservation_alts": sum(1 for a in alts if a in (4, 5, 6, 7)),
                    "n_alt3": alts.count(3),
                    "n_unique_alts": len(counts),
                    **{f"{k}_score": res["sub_scores"][k] for k in res["sub_scores"]},
                    "alt_distribution": json.dumps(counts),
                })

    df = pd.DataFrame(rows)
    out = os.path.join(output_dir, "empirical_normalization_comparison.csv")
    df.to_csv(out, index=False)
    print(f"\nSaved {out}")

    print("\n--- Conservation Priority at $20M ---")
    for method in METHODS:
        r = df[(df.method == method) & (df.scenario == "Conservation priority")
               & (df.budget == 20_000_000)]
        if r.empty:
            continue
        r = r.iloc[0]
        print(f"  {method:<14s}: conservation alts={r.n_conservation_alts}, "
              f"Alt 3={r.n_alt3}, unique={r.n_unique_alts}, T&E={r.te_score:.2f}")
    return df


# ============================================================
# PART 3: SCORE DISTRIBUTION DIAGNOSTICS
# ============================================================

def compute_score_diagnostics(filepath, output_dir):
    """Per-paddock T&E score spread under each normalization method."""
    print("\n" + "=" * 70)
    print("PART 3: SCORE DISTRIBUTION DIAGNOSTICS")
    print("=" * 70)

    input_data = load_input_data(filepath)
    rows = []
    for method in METHODS:
        for roadside_built in (False, True):
            scores, opt_indices = prepare_scores_method(input_data, method, roadside_built)
            te = scores["te"]
            for idx, orig_i in enumerate(opt_indices):
                row = te[idx, :]
                rows.append({
                    "method": method,
                    "paddock": orig_i + 1,
                    "te_count": input_data["te_count"][orig_i],
                    "size_km2": round(float(input_data["area_km2"][orig_i]), 2),
                    "spread": float(row.max() - row.min()),
                    "roadside_built": roadside_built,
                })

    df = pd.DataFrame(rows)
    out = os.path.join(output_dir, "appendix_score_spread.csv")
    df.to_csv(out, index=False)
    print(f"Saved {out}\n")

    print("  Paddocks (of 21) with T&E spread below each threshold:")
    print(f"  {'method':<14s} {'roadside':>9s} {'<0.01':>6s} {'<0.05':>6s} {'<0.10':>6s}")
    for built in (False, True):
        for method in METHODS:
            sp = df[(df.method == method) & (df.roadside_built == built)].spread
            print(f"  {method:<14s} {str(built):>9s} {int((sp < 0.01).sum()):>6d} "
                  f"{int((sp < 0.05).sum()):>6d} {int((sp < 0.10).sum()):>6d}")
    return df


# ============================================================
# PART 4: CROSSED NORMALIZATION AND HEADLINE METRICS
# ============================================================

ECO_COMM_PAIRS = [("within_unit", "global_linear"), ("global_linear", "within_unit"),
                  ("global_linear", "global_linear"), ("within_unit", "within_unit")]
B20 = 20_000_000


def _grid(input_data, eco, comm):
    """All scenarios and budgets under one pair of normalization methods."""
    scenarios = build_scenarios()
    out = {}
    for sid, sdef in scenarios.items():
        w = effective_weights(sdef)
        for budget in BUDGETS:
            res = solve_scenario_budget(input_data, eco, w, budget, comm)
            if res is not None:
                out[(sdef["label"], budget)] = res
    return out


def _symmetry_metrics(grid):
    """Exchange ratios and the findings they support, at $20M against Balanced."""
    base = grid.get(("Balanced", B20))
    if base is None:
        return {}
    keys = ["te", "habitat", "rancher", "hunter", "recreationist"]

    def delta(label, key):
        r = grid.get((label, B20))
        return np.nan if r is None else r["sub_scores"][key] - base["sub_scores"][key]

    def exchange(label, key):
        loss = -delta(label, "te")
        gained = delta(label, key)
        if not np.isfinite(loss) or loss <= 1e-9:
            return np.inf if gained > 0 else np.nan
        return gained / loss

    gain = delta("Conservation priority", "te")
    asym = -delta("Community priority", "te") / gain if gain > 1e-9 else np.inf
    s6 = exchange("Rancher-conservation", "rancher")
    s5 = exchange("Community priority", "rancher")
    s7 = exchange("Hunter-recreationist", "hunter")

    spend = [grid[("Conservation priority", b)]["total_cost"] / b
             for b in BUDGETS if ("Conservation priority", b) in grid]
    s5_60 = grid.get(("Community priority", 60_000_000))

    return {
        "asym_ratio": asym,
        "S6_rancher_per_te": s6,
        "S5_rancher_per_te": s5,
        "S7_hunter_per_te": s7,
        "S6_te_change": delta("Rancher-conservation", "te"),
        "S6_rancher_change": delta("Rancher-conservation", "rancher"),
        "S2_spend_min_share": min(spend) if spend else np.nan,
        "S5_spend_share_60M": s5_60["total_cost"] / 60e6 if s5_60 else np.nan,
        "S6_beats_S5": bool(np.nan_to_num(s6, nan=-1) > np.nan_to_num(s5, nan=-1)),
        "asym_holds": bool(asym > 1),
        "hunter_weaker": bool(np.nan_to_num(s7, nan=-1) < np.nan_to_num(s6, nan=-1)),
    }


def run_crossed_comparison(filepath, output_dir):
    print("\n" + "=" * 70)
    print("PART 4: CROSSED NORMALIZATION AND HEADLINE METRICS")
    print("=" * 70)

    input_data = load_input_data(filepath)

    # Portfolios: each conservation normalization against the standard
    # global-linear treatment of community scores.
    rows = []
    for eco in METHODS:
        grid = _grid(input_data, eco, "global_linear")
        for (label, budget), r in grid.items():
            alts = [PADDOCK_ALTS[c] + 1 for c in r["choices"]]
            rows.append({
                "method_eco": eco, "method_comm": "global_linear",
                "scenario": label, "budget": budget, "budget_M": budget / 1e6,
                "roadside_built": r["roadside_built"], "total_cost": r["total_cost"],
                **{k: r["sub_scores"][k] for k in
                   ("te", "habitat", "rancher", "hunter", "recreationist")},
                "n_conservation_alts": sum(1 for a in alts if a in (4, 5, 6, 7)),
                "n_alt3": alts.count(3), "n_alt1": alts.count(1), "n_alt7": alts.count(7),
                "choices": ",".join(str(a) for a in alts),
            })
    portfolios = pd.DataFrame(rows)
    out = os.path.join(output_dir, "appendix_normalization_portfolios.csv")
    portfolios.to_csv(out, index=False)
    print(f"\nSaved {out} ({len(portfolios)} rows)")

    # Headline metrics under crossed eco and community normalization.
    rows = []
    for eco, comm in ECO_COMM_PAIRS:
        grid = _grid(input_data, eco, comm)
        m = _symmetry_metrics(grid)
        m.update(eco=eco, comm=comm)
        rows.append(m)
    symmetry = pd.DataFrame(rows)
    out = os.path.join(output_dir, "normalization_symmetry.csv")
    symmetry.to_csv(out, index=False)
    print(f"Saved {out}\n")
    cols = ["eco", "comm", "asym_ratio", "S6_rancher_per_te",
            "S5_rancher_per_te", "S7_hunter_per_te"]
    print(symmetry[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return portfolios, symmetry


# ============================================================
# PART 2: SIMULATED LANDSCAPES
# ============================================================

def generate_synthetic_landscape(n_units, n_alts, skewness, seed=42):
    rng = np.random.RandomState(seed)
    if skewness == "uniform":
        eco_values = rng.uniform(10, 100, n_units)
    elif skewness == "moderate":
        eco_values = rng.lognormal(mean=3.0, sigma=1.0, size=n_units)
        eco_values = eco_values / eco_values.max() * 100
    elif skewness == "extreme":
        eco_values = rng.uniform(1, 20, n_units)
        eco_values[0] = eco_values.sum()
    elif skewness == "pww_like":
        eco_values = rng.uniform(0, 50, n_units)
        eco_values[2] = 0
        eco_values[7] = 0
        eco_values[0] = 580
        eco_values[1:] = eco_values[1:] / eco_values[1:].sum() * 433
    else:
        raise ValueError(f"unknown skewness: {skewness}")

    base_scores = np.array([-1, 0, 1, 2, 3, 4, 5, 6])[:n_alts]
    action_scores = base_scores[None, :] + rng.uniform(0, 2, (n_units, n_alts))
    costs = np.linspace(100_000, 3_000_000, n_alts)[None, :] * rng.uniform(0.8, 1.2, (n_units, n_alts))
    community_base = np.array([4, 3, 2, 1, 0, -1, -2, -3])[:n_alts]
    community_scores = community_base[None, :] + rng.uniform(-0.5, 0.5, (n_units, n_alts))
    return eco_values, action_scores, costs, community_scores


def run_synthetic_optimization(eco_values, action_scores, costs, community_scores,
                               method, eco_weight=0.80, budget_fraction=0.3):
    n_units, n_alts = action_scores.shape
    budget = costs.max(axis=1).sum() * budget_fraction
    raw = action_scores * eco_values[:, None]

    if method == "global_linear":
        cons = normalize_global_linear(raw)
    elif method == "vector":
        cons = normalize_vector(raw)
    elif method == "within_unit":
        cons = normalize_within_unit(action_scores)
        for i in range(n_units):
            if eco_values[i] == 0:
                cons[i, :] = 0.0
    else:
        raise ValueError(f"unknown method: {method}")

    comm = normalize_global_linear(community_scores)
    soc_weight = 1.0 - eco_weight

    prob = LpProblem("synthetic", LpMaximize)
    x = [[LpVariable(f"x_{i}_{j}", cat="Binary") for j in range(n_alts)]
         for i in range(n_units)]
    prob += lpSum((eco_weight * cons[i, j] + soc_weight * comm[i, j]) * x[i][j]
                  for i in range(n_units) for j in range(n_alts))
    for i in range(n_units):
        prob += lpSum(x[i]) == 1
    prob += lpSum(costs[i, j] * x[i][j]
                  for i in range(n_units) for j in range(n_alts)) <= budget

    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    if LpStatus[prob.status] != "Optimal":
        return None

    choices = np.array([next(j for j in range(n_alts) if value(x[i][j]) > 0.5)
                        for i in range(n_units)])
    spreads = cons.max(axis=1) - cons.min(axis=1)
    return {
        "compressed_units": int((spreads < 0.05).sum()),
        "mean_alt_index": float(choices.mean()),
        "n_cheapest": int((choices == 0).sum()),
        "n_best_conservation": int((choices == n_alts - 1).sum()),
        "n_unique_alts": len(set(choices.tolist())),
    }


def run_simulation_experiment(output_dir, n_reps=20):
    print("\n" + "=" * 70)
    print("PART 2: SIMULATED LANDSCAPES")
    print("=" * 70)

    n_units, n_alts = 22, 8
    skewness_levels = ["uniform", "moderate", "extreme", "pww_like"]
    rows = []

    for skew in skewness_levels:
        for rep in range(n_reps):
            seed = rep * 100 + hash(skew) % 1000
            eco, action, costs, comm = generate_synthetic_landscape(n_units, n_alts, skew, seed)
            srt = np.sort(eco)
            n = len(srt)
            gini = (2 * np.sum(np.arange(1, n + 1) * srt) / (n * srt.sum())) - (n + 1) / n
            concentration = eco.max() / eco.sum() if eco.sum() > 0 else 0
            for method in METHODS:
                for ew in (0.50, 0.80):
                    for bf in (0.15, 0.30, 0.50):
                        r = run_synthetic_optimization(eco, action, costs, comm, method, ew, bf)
                        if r is None:
                            continue
                        rows.append({"skewness": skew, "replicate": rep, "gini": gini,
                                     "concentration": concentration, "method": method,
                                     "eco_weight": ew, "budget_fraction": bf, **r})

    df = pd.DataFrame(rows)
    out = os.path.join(output_dir, "simulation_normalization_comparison.csv")
    df.to_csv(out, index=False)
    print(f"\nSaved {out}")

    print("\n--- Mean conservation actions at eco_weight 0.80, budget fraction 0.30 ---")
    for skew in skewness_levels:
        print(f"\n  {skew}")
        for method in METHODS:
            s = df[(df.skewness == skew) & (df.method == method)
                   & (df.eco_weight == 0.80) & (df.budget_fraction == 0.30)]
            if s.empty:
                continue
            print(f"    {method:<14s}: best_cons={s.n_best_conservation.mean():.1f}, "
                  f"compressed={s.compressed_units.mean():.1f}, "
                  f"mean_alt={s.mean_alt_index.mean():.2f}")
    return df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("outdir")
    ap.add_argument("--parts", default="1,2,3,4",
                    help="comma-separated: 1 empirical, 2 simulation, "
                         "3 score spread, 4 crossed normalization")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    parts = {p.strip() for p in args.parts.split(",")}

    if "1" in parts:
        run_empirical_comparison(args.input, args.outdir)
    if "2" in parts:
        run_simulation_experiment(args.outdir)
    if "3" in parts:
        compute_score_diagnostics(args.input, args.outdir)
    if "4" in parts:
        run_crossed_comparison(args.input, args.outdir)

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
