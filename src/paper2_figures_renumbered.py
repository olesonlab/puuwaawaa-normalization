"""
Paper 2 Figures: SDM at Puʻuwwaʻawaʻa — RENUMBERED FOR CSP SUBMISSION
======================================================================
Main text figures: 2, 3, 4
Supporting Information figures: S2, S3

Figure assignments (post-renumbering):
    Figure 2  — Asymmetric tradeoffs at $20M (bar chart of score changes)
    Figure 3  — Sub-objective scores across budgets (line plots)
    Figure 4  — Management portfolios heatmap at $20M
    Figure S2 — Conservation–rancher tradeoff scatter at $20M
    Figure S3 — Restoration progression under Conservation Priority

Usage:
    python paper2_figures_renumbered.py
    python paper2_figures_renumbered.py --data-dir /path/to/data --out-dir /path/to/output
"""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap, BoundaryNorm

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__)) or "."
INPUT_DIR  = OUTPUT_DIR

def set_dirs(data_dir, out_dir):
    global INPUT_DIR, OUTPUT_DIR
    INPUT_DIR  = str(data_dir)
    OUTPUT_DIR = str(out_dir)

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10,
    "axes.titlesize": 11, "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "legend.fontsize": 9, "figure.dpi": 300,
    "savefig.dpi": 300, "savefig.bbox": "tight",
})

SCENARIO_COLORS = {
    "Balanced": "#2196F3", "Conservation priority": "#388E3C",
    "T&E emphasis": "#1B5E20", "Habitat emphasis": "#66BB6A",
    "Community priority": "#D32F2F", "Rancher-conservation": "#F57C00",
    "Hunter-recreationist": "#7B1FA2",
}
SCENARIO_ORDER = [
    "Balanced", "Conservation priority", "T&E emphasis",
    "Habitat emphasis", "Community priority",
    "Rancher-conservation", "Hunter-recreationist",
]
ALT_COLORS = {
    1: "#4CAF50", 2: "#BBDEFB", 3: "#F44336", 4: "#81C784",
    5: "#2E7D32", 6: "#1B5E20", 7: "#004D40", 8: "#90A4AE",
    9: "#78909C", 10: "#B0BEC5", 11: "#ECEFF1",
}
ALT_SHORT = {
    1: "Fence+fuel", 2: "Fuelbreak", 3: "Graze+",
    4: "Fence-cattle", 5: "Fence-ungul", 6: "Alt5+weed",
    7: "Full restore", 8: "Fence+weed", 9: "F-cattle+weed",
    10: "Fence+plant", 11: "No change",
}


def fig2_asymmetry():
    df   = pd.read_csv(os.path.join(INPUT_DIR, "sdm_results_summary.csv"))
    df20 = df[df["budget"] == 20_000_000].copy()
    bal  = df20[df20["scenario"] == "Balanced"].iloc[0]
    con  = df20[df20["scenario"] == "Conservation priority"].iloc[0]
    com  = df20[df20["scenario"] == "Community priority"].iloc[0]
    rc   = df20[df20["scenario"] == "Rancher-conservation"].iloc[0]

    metrics = ["te_score","habitat_score","rancher_score","hunter_score","recreationist_score"]
    labels  = ["T&E", "Habitat", "Rancher", "Hunter", "Recreationist"]
    delta_con = [con[m] - bal[m] for m in metrics]
    delta_com = [com[m] - bal[m] for m in metrics]
    delta_rc  = [rc[m]  - bal[m] for m in metrics]

    rc_ranch_gain = rc["rancher_score"] - bal["rancher_score"]
    rc_te_loss    = bal["te_score"]     - rc["te_score"]
    ratio         = rc_ranch_gain / rc_te_loss if rc_te_loss != 0 else float("inf")

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(labels)); width = 0.25
    ax.bar(x - width, delta_con, width, label="Conservation Priority (80% eco)",
           color="#388E3C", edgecolor="white", linewidth=0.5)
    ax.bar(x, delta_com, width, label="Community Priority (80% soc)",
           color="#D32F2F", edgecolor="white", linewidth=0.5)
    ax.bar(x + width, delta_rc, width, label="Rancher-Conservation (50/50, 70% ranch)",
           color="#F57C00", edgecolor="white", linewidth=0.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("Change from Balanced baseline\n(score points)")
    ax.legend(frameon=False, fontsize=8)
    ax.annotate(f"Rancher-Cons:\n{ratio:.2f} rancher pts\nper T&E pt lost",
                xy=(2 + width, delta_rc[2]), xytext=(3.5, delta_rc[2] - 1),
                fontsize=7, color="#F57C00",
                arrowprops=dict(arrowstyle="->", color="#F57C00", lw=0.8))
    ax.set_title("Figure 2. Asymmetric tradeoffs at $20 million:\nscore changes from Balanced baseline",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    for ext in ["png", "svg"]:
        fig.savefig(os.path.join(OUTPUT_DIR, f"paper2_fig2_asymmetry.{ext}"), bbox_inches="tight")
    plt.close()
    print("Figure 2 saved.")


def fig3_budget_curves():
    df = pd.read_csv(os.path.join(INPUT_DIR, "sdm_results_summary.csv"))
    df["budget_M"] = df["budget"] / 1e6
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    for scen in SCENARIO_ORDER:
        sub = df[df["scenario"] == scen].sort_values("budget")
        ax.plot(sub["budget_M"], sub["te_score"], marker="o", markersize=5,
                linewidth=2, color=SCENARIO_COLORS[scen], label=scen)
    ax.set_xlabel("Budget ($ million)"); ax.set_ylabel("Total T&E score\n(sum across 22 paddocks)")
    ax.set_xlim(0, 65); ax.set_title("(a) Conservation outcome", fontweight="bold")

    ax = axes[1]
    for scen in SCENARIO_ORDER:
        sub = df[df["scenario"] == scen].sort_values("budget")
        ax.plot(sub["budget_M"], sub["rancher_score"], marker="s", markersize=5,
                linewidth=2, color=SCENARIO_COLORS[scen], label=scen)
    ax.set_xlabel("Budget ($ million)"); ax.set_ylabel("Total rancher score\n(sum across 22 paddocks)")
    ax.set_xlim(0, 65); ax.set_title("(b) Rancher outcome", fontweight="bold")

    # Shared legend below both panels — avoids overlap with lines
    handles = [plt.Line2D([0],[0], color=SCENARIO_COLORS[s], marker="o",
               linewidth=2, markersize=5, label=s) for s in SCENARIO_ORDER]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
               fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.suptitle("Figure 3. Sub-objective scores across budgets under seven weighting scenarios",
                 fontsize=11, fontweight="bold")
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    for ext in ["png", "svg"]:
        fig.savefig(os.path.join(OUTPUT_DIR, f"paper2_fig3_budget_curves.{ext}"), bbox_inches="tight")
    plt.close()
    print("Figure 3 saved.")


def fig4_heatmap():
    df   = pd.read_csv(os.path.join(INPUT_DIR, "sdm_results_paddock_detail.csv"))
    df20 = df[df["budget"] == 20_000_000].copy()
    n_scen = len(SCENARIO_ORDER); n_paddocks = 22
    matrix = np.zeros((n_scen, n_paddocks), dtype=int)
    for si, scen in enumerate(SCENARIO_ORDER):
        sub = df20[df20["scenario"] == scen].sort_values("paddock")
        for _, row in sub.iterrows():
            matrix[si, int(row["paddock"]) - 1] = int(row["alternative"])

    alt_nums = sorted(ALT_COLORS.keys())
    cmap = ListedColormap([ALT_COLORS[a] for a in alt_nums])
    bounds = [a - 0.5 for a in alt_nums] + [alt_nums[-1] + 0.5]
    norm = BoundaryNorm(bounds, cmap.N)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(n_paddocks))
    ax.set_xticklabels([str(i+1) for i in range(n_paddocks)], fontsize=8)
    ax.set_xlabel("Paddock")
    ax.set_yticks(range(n_scen)); ax.set_yticklabels(SCENARIO_ORDER, fontsize=8)
    for si in range(n_scen):
        for pi in range(n_paddocks):
            alt = matrix[si, pi]
            color = "white" if alt in [3, 5, 6, 7] else "black"
            ax.text(pi, si, str(alt), ha="center", va="center",
                    fontsize=6.5, fontweight="bold", color=color)
    used_alts = sorted(set(matrix.flatten()))
    patches = [mpatches.Patch(color=ALT_COLORS[a], label=f"Alt {a}: {ALT_SHORT[a]}")
               for a in used_alts]
    ax.legend(handles=patches, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=4, frameon=False, fontsize=7.5)
    ax.set_title("Figure 4. Management portfolios at $20 million under seven weighting scenarios",
                 fontsize=11, fontweight="bold", pad=12)
    plt.tight_layout()
    for ext in ["png", "svg"]:
        fig.savefig(os.path.join(OUTPUT_DIR, f"paper2_fig4_heatmap.{ext}"), bbox_inches="tight")
    plt.close()
    print("Figure 4 saved.")


def figS2_tradeoff():
    df   = pd.read_csv(os.path.join(INPUT_DIR, "sdm_results_summary.csv"))
    df20 = df[df["budget"] == 20_000_000].copy()

    bal        = df20[df20["scenario"] == "Balanced"].iloc[0]
    rc         = df20[df20["scenario"] == "Rancher-conservation"].iloc[0]
    ranch_gain = rc["rancher_score"] - bal["rancher_score"]
    te_loss    = bal["te_score"]     - rc["te_score"]
    ratio      = ranch_gain / te_loss if te_loss != 0 else float("inf")

    fig, ax = plt.subplots(figsize=(8, 6))
    for _, row in df20.iterrows():
        scen = row["scenario"]
        ax.scatter(row["rancher_score"], row["te_score"],
                   s=120, color=SCENARIO_COLORS.get(scen, "gray"),
                   edgecolors="black", linewidth=0.8, zorder=5)

    label_cfg = {
        "Conservation priority": dict(
            xytext=(-60, 28), ha="right",
            arrowprops=dict(arrowstyle="-", color=SCENARIO_COLORS["Conservation priority"], lw=0.7)
        ),
        "T&E emphasis": dict(
            xytext=(-60,  8), ha="right",
            arrowprops=dict(arrowstyle="-", color=SCENARIO_COLORS["T&E emphasis"], lw=0.7)
        ),
        "Habitat emphasis": dict(
            xytext=(-60, -12), ha="right",
            arrowprops=dict(arrowstyle="-", color=SCENARIO_COLORS["Habitat emphasis"], lw=0.7)
        ),
        "Community priority": dict(
            xytext=(-14, 20), ha="right",
            arrowprops=dict(arrowstyle="-", color=SCENARIO_COLORS["Community priority"], lw=0.7)
        ),
        "Rancher-conservation": dict(
            xytext=(12, -22), ha="left",
            arrowprops=dict(arrowstyle="-", color=SCENARIO_COLORS["Rancher-conservation"], lw=0.7)
        ),
        "Balanced": dict(
            xytext=(12, 16), ha="left",
            arrowprops=dict(arrowstyle="-", color=SCENARIO_COLORS["Balanced"], lw=0.7)
        ),
        "Hunter-recreationist": dict(
            xytext=(12, -22), ha="left",
            arrowprops=dict(arrowstyle="-", color=SCENARIO_COLORS["Hunter-recreationist"], lw=0.7)
        ),
    }

    for _, row in df20.iterrows():
        scen = row["scenario"]
        cfg  = label_cfg.get(scen, dict(xytext=(10, 10), ha="left", arrowprops=None))
        ax.annotate(
            scen,
            xy=(row["rancher_score"], row["te_score"]),
            xytext=cfg["xytext"],
            textcoords="offset points",
            fontsize=7.5, ha=cfg["ha"],
            color=SCENARIO_COLORS.get(scen, "gray"),
            arrowprops=cfg["arrowprops"],
        )

    ax.axhline(bal["te_score"],      color="gray", linestyle=":", linewidth=0.5, alpha=0.5)
    ax.axvline(bal["rancher_score"], color="gray", linestyle=":", linewidth=0.5, alpha=0.5)
    ax.text(0.98, 0.48,
            f"Rancher-Conservation\n{ratio:.2f}:1 exchange ratio",
            transform=ax.transAxes, fontsize=7.5, color="#F57C00",
            ha="right", va="center", style="italic")
    ax.text(0.02, 0.88, "More conservation,\nless rancher",
            transform=ax.transAxes, fontsize=7, color="gray",
            va="top", ha="left", style="italic")
    ax.text(0.98, 0.13, "More rancher,\nless conservation",
            transform=ax.transAxes, fontsize=7, color="gray",
            va="bottom", ha="right", style="italic")

    ax.set_xlabel("Total rancher score (sum across 22 paddocks)")
    ax.set_ylabel("Total T&E score (sum across 22 paddocks)")
    ax.set_title("Figure S2. Conservation-rancher tradeoff at $20 million",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    for ext in ["png", "svg"]:
        fig.savefig(os.path.join(OUTPUT_DIR, f"paper2_figS2_tradeoff.{ext}"),
                    bbox_inches="tight")
    plt.close()
    print("Figure S2 saved.")


def figS3_restoration_progression():
    df    = pd.read_csv(os.path.join(INPUT_DIR, "sdm_results_paddock_detail.csv"))
    df_cp = df[df["scenario"] == "Conservation priority"].copy()
    budgets = [5_000_000, 10_000_000, 20_000_000, 40_000_000, 60_000_000]
    budget_labels = ["$5M", "$10M", "$20M", "$40M", "$60M"]

    def categorize(alt):
        if alt == 7:             return "Full restoration"
        elif alt in [4, 5, 6]:  return "Conservation (mid)"
        elif alt == 1:           return "Fence + fuelbreaks"
        elif alt == 2:           return "Fuelbreak only"
        elif alt == 3:           return "Grazing intensification"
        else:                    return "Other"

    cat_colors = {
        "Full restoration": "#004D40", "Conservation (mid)": "#2E7D32",
        "Fence + fuelbreaks": "#4CAF50", "Fuelbreak only": "#BBDEFB",
        "Grazing intensification": "#F44336", "Other": "#ECEFF1",
    }
    cat_order = ["Full restoration", "Conservation (mid)", "Fence + fuelbreaks",
                 "Fuelbreak only", "Grazing intensification", "Other"]

    counts_per_budget = []
    for budget in budgets:
        sub = df_cp[df_cp["budget"] == budget]
        cc  = {c: 0 for c in cat_order}
        for alt in sub["alternative"]: cc[categorize(alt)] += 1
        counts_per_budget.append(cc)

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(budgets)); bottoms = np.zeros(len(budgets))
    for cat in cat_order:
        vals = [counts_per_budget[i][cat] for i in range(len(budgets))]
        if sum(vals) == 0: continue
        ax.bar(x, vals, bottom=bottoms, width=0.6, color=cat_colors[cat],
               label=cat, edgecolor="white", linewidth=0.5)
        for i, v in enumerate(vals):
            if v > 0:
                txt_color = "white" if cat in ["Full restoration", "Conservation (mid)"] else "black"
                ax.text(x[i], bottoms[i] + v/2, str(v), ha="center", va="center",
                        fontsize=8, fontweight="bold", color=txt_color)
        bottoms += np.array(vals, dtype=float)

    ax.set_xticks(x); ax.set_xticklabels(budget_labels)
    ax.set_xlabel("Budget"); ax.set_ylabel("Number of paddocks")
    ax.set_ylim(0, 23)
    ax.axhline(22, color="gray", linestyle=":", linewidth=0.5, alpha=0.5)
    ax.text(4.3, 22.3, "22 paddocks", fontsize=7, color="gray", ha="right")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("Figure S3. Progressive landscape restoration under Conservation Priority",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    for ext in ["png", "svg"]:
        fig.savefig(os.path.join(OUTPUT_DIR, f"paper2_figS3_restoration.{ext}"), bbox_inches="tight")
    plt.close()
    print("Figure S3 saved.")


def main():
    parser = argparse.ArgumentParser(description="Generate Paper 2 figures (renumbered for CSP submission).")
    parser.add_argument("--data-dir", default=".", help="Directory containing input CSV files.")
    parser.add_argument("--out-dir",  default=".", help="Directory to write output figures.")
    args = parser.parse_args()
    set_dirs(Path(args.data_dir), Path(args.out_dir))
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    fig2_asymmetry()
    fig3_budget_curves()
    fig4_heatmap()
    figS2_tradeoff()
    figS3_restoration_progression()
    print("\nAll Paper 2 figures generated.")

if __name__ == "__main__":
    main()
