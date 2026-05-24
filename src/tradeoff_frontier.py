"""
Tradeoff frontier analysis for Paper 1.

Sweeps ecological weight from 0 to 1 and runs the optimizer under each
normalization method to produce Figure X (tradeoff frontier) showing that
within-unit normalization tracks stated preferences more faithfully than
global linear or vector normalization.

Usage:
    python tradeoff_frontier.py --data path/to/pww_sdm_input_data.xlsx \\
                                --output_dir ./figures --budget 20000000

Requires pww_sdm_optimizer.py in the same directory (or on PYTHONPATH).
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Allow importing from the same directory or from puuwaawaa-sdm/src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../puuwaawaa-sdm/src"))
sys.path.insert(0, os.path.dirname(__file__))

from normalization_methods import (
    normalize_global_linear,
    normalize_vector,
    normalize_within_unit,
    concentration_ratio,
    gini_coefficient,
)

try:
    from pww_sdm_optimizer import (
        load_input_data,
        compute_action_effectiveness,
        normalize_to_01,
        optimize,
        FIXED_PADDOCK_IDX,
        FIXED_ALT_IDX,
        BUDGETS,
    )
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False
    print("Warning: pww_sdm_optimizer.py not found. "
          "Frontier plots require the optimizer.")


def build_scores_with_method(input_data, norm_method):
    """
    Build (21 x 11) score matrices using a specified normalization method
    for conservation objectives. Community scores always use global min-max.

    norm_method: one of 'global_linear', 'vector', 'within_unit'
    """
    n_paddocks = input_data["costs"].shape[0]
    opt_indices = [i for i in range(n_paddocks) if i != FIXED_PADDOCK_IDX]

    action_raw = compute_action_effectiveness(
        input_data["fire_prob_baseline"],
        input_data["fire_prob"],
    )
    action_21 = action_raw[opt_indices, :]

    # Apply chosen normalization to conservation scores
    if norm_method == "global_linear":
        action_normed = normalize_global_linear(action_21)
    elif norm_method == "vector":
        action_normed = normalize_vector(action_21)
    elif norm_method == "within_unit":
        action_normed = normalize_within_unit(action_21)
    else:
        raise ValueError(f"Unknown norm_method: {norm_method}")

    # Zero out T&E for paddocks with no T&E plants
    te_scores = action_normed.copy()
    for idx, orig_i in enumerate(opt_indices):
        if input_data["te_count"][orig_i] == 0:
            te_scores[idx, :] = 0.0

    scores = {
        "te": te_scores,
        "habitat": action_normed.copy(),
        "recreationist": normalize_to_01(input_data["community_raw"][opt_indices, :]),
        "hunter": normalize_to_01(input_data["hunter_raw"][opt_indices, :]),
        "rancher": normalize_to_01(input_data["rancher_raw"][opt_indices, :]),
    }
    return scores, opt_indices


def run_frontier(input_data, budget, eco_weights, norm_method):
    """
    Sweep ecological weight from 0 to 1, run optimizer, return
    (te_scores, rancher_scores) for each weight level.
    """
    scores, opt_indices = build_scores_with_method(input_data, norm_method)
    costs_opt = input_data["costs"][opt_indices, :]
    fixed_cost = input_data["costs"][FIXED_PADDOCK_IDX, FIXED_ALT_IDX]
    available = budget - fixed_cost

    te_scores = []
    rancher_scores = []

    for eco_w in eco_weights:
        soc_w = 1.0 - eco_w
        weights = {
            "te":            eco_w * 0.50,
            "habitat":       eco_w * 0.50,
            "rancher":       soc_w * 0.33,
            "hunter":        soc_w * 0.33,
            "recreationist": soc_w * 0.34,
        }
        result = optimize(scores, costs_opt, available, weights,
                          input_data["shared_firebreak_cost"])
        if result["status"] == "Optimal":
            te_scores.append(result["sub_scores"]["te"])
            rancher_scores.append(result["sub_scores"]["rancher"])
        else:
            te_scores.append(np.nan)
            rancher_scores.append(np.nan)

    return np.array(te_scores), np.array(rancher_scores)


def fig_tradeoff_frontier(input_data, budget=20_000_000,
                          n_steps=21, output_dir="."):
    """
    Generate the tradeoff frontier figure comparing normalization methods.
    """
    eco_weights = np.linspace(0, 1, n_steps)

    method_styles = {
        "global_linear": {"color": "#d73027", "label": "Global linear",
                          "linestyle": "--"},
        "vector":         {"color": "#fc8d59", "label": "Vector (Euclidean)",
                           "linestyle": "-."},
        "within_unit":    {"color": "#1a9641", "label": "Within-unit (recommended)",
                           "linestyle": "-"},
    }

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle(
        f"Tradeoff frontier at ${budget/1e6:.0f}M — comparison of normalization methods",
        fontsize=10, fontweight="bold",
    )

    ax_te, ax_ranch = axes
    ax_te.set_xlabel("Ecological weight", fontsize=9)
    ax_te.set_ylabel("Total T&E score", fontsize=9)
    ax_te.set_title("T&E score vs. ecological weight", fontsize=9)

    ax_ranch.set_xlabel("Total T&E score", fontsize=9)
    ax_ranch.set_ylabel("Total rancher score", fontsize=9)
    ax_ranch.set_title("T&E vs. rancher tradeoff frontier", fontsize=9)

    for method, style in method_styles.items():
        te, ranch = run_frontier(input_data, budget, eco_weights, method)
        # Left panel: T&E score vs eco weight
        ax_te.plot(eco_weights, te,
                   color=style["color"], linestyle=style["linestyle"],
                   linewidth=2, label=style["label"])
        # Right panel: T&E vs rancher tradeoff frontier
        ax_ranch.plot(te, ranch,
                      color=style["color"], linestyle=style["linestyle"],
                      linewidth=2, label=style["label"])

    for ax in axes:
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, "fig_tradeoff_frontier.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {path}")


def print_concentration_diagnostics(input_data):
    """
    Print concentration ratio and Gini for each sub-objective.
    Helps identify when the normalization trap is likely to be severe.
    """
    action_raw = compute_action_effectiveness(
        input_data["fire_prob_baseline"],
        input_data["fire_prob"],
    )
    opt_indices = [i for i in range(22) if i != FIXED_PADDOCK_IDX]

    print("\nConcentration diagnostics (21 optimized paddocks):")
    print(f"{'Objective':<20} {'CR(top-3)':>10} {'Gini':>8}  Interpretation")
    print("-" * 65)

    objectives = {
        "T&E (max action)": np.array([
            action_raw[i, :].max() * input_data["te_count"][i]
            for i in opt_indices
        ]),
        "Habitat (max action)": np.array([
            action_raw[i, :].max() for i in opt_indices
        ]),
        "Rancher (max raw)": input_data["rancher_raw"][opt_indices, :].max(axis=1),
        "Hunter (max raw)":  input_data["hunter_raw"][opt_indices, :].max(axis=1),
        "Recreationist":     input_data["community_raw"][opt_indices, :].max(axis=1),
    }

    for name, vals in objectives.items():
        cr = concentration_ratio(vals, top_k=3)
        g = gini_coefficient(vals)
        if cr > 0.6:
            interp = "HIGH — within-unit strongly recommended"
        elif cr > 0.4:
            interp = "MODERATE — compare methods"
        else:
            interp = "low — method choice has minimal impact"
        print(f"  {name:<18} {cr:>10.2f} {g:>8.2f}  {interp}")


def main():
    parser = argparse.ArgumentParser(
        description="Tradeoff frontier analysis for Oleson et al. Paper 1")
    parser.add_argument("--data", required=True,
                        help="Path to pww_sdm_input_data.xlsx")
    parser.add_argument("--budget", type=int, default=20_000_000,
                        help="Budget in dollars (default: 20000000)")
    parser.add_argument("--n_steps", type=int, default=21,
                        help="Number of eco-weight steps (default: 21)")
    parser.add_argument("--output_dir", default="./figures")
    args = parser.parse_args()

    if not OPTIMIZER_AVAILABLE:
        print("Error: pww_sdm_optimizer.py is required. "
              "Add puuwaawaa-sdm/src to your PYTHONPATH.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    print("Loading input data...")
    input_data = load_input_data(args.data)

    print_concentration_diagnostics(input_data)

    print(f"\nRunning tradeoff frontier at ${args.budget/1e6:.0f}M "
          f"({args.n_steps} steps)...")
    fig_tradeoff_frontier(input_data, args.budget, args.n_steps, args.output_dir)
    print("Done.")


if __name__ == "__main__":
    main()
