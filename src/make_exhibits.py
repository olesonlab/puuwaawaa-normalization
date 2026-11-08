"""Rebuild the tables and figures of the manuscript from the archived results.

Run from the repository root:  python src/make_exhibits.py
Reads results/scaling_experiment/scaling_results.csv and
results/effectiveness_sensitivity/effectiveness_sensitivity_results.csv.
Writes CSV tables and PNG figures to exhibits/.

All values are descriptive means over the simulation design, pooled over the
factors not named in each exhibit. Main-text exhibits and Tables S2-S3 use the
baseline effectiveness design; the wide design is reported in the text only.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
OUT = ROOT / "exhibits"
CONC = ["diffuse", "moderate", "concentrated"]
CONC_LABEL = ["Diffuse", "Moderate", "Concentrated"]
COMM = [("potential_alignment", "Potential alignment"), ("consistent_conflict", "Consistent conflict")]


def pct(s):
    return (100 * s).round(1)


def main():
    OUT.mkdir(exist_ok=True)
    allrows = pd.read_csv(RES / "scaling_experiment" / "scaling_results.csv")
    d = allrows[allrows.effect_design == "baseline"]
    assert len(d) == 8640, len(d)
    e = pd.read_csv(RES / "effectiveness_sensitivity" / "effectiveness_sensitivity_results.csv")
    assert len(e) == 8640, len(e)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

    # Table S2 and Figure 1: disagreement by concentration and site count (standardized pair).
    s2 = pct(d.groupby(["n_sites", "concentration"]).standardized_different_fraction.mean()).unstack()[CONC]
    s2.to_csv(OUT / "tableS2_disagreement_by_sites_concentration.csv")
    fig, ax = plt.subplots(figsize=(4.9, 2.8))
    width = 0.25
    for k, n in enumerate(s2.index):
        ax.bar([i + (k - 1) * width for i in range(3)], s2.loc[n], width, label=f"{n} sites")
    ax.set_xticks(range(3), CONC_LABEL)
    ax.set_ylabel("Sites with different actions (%)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figure1_disagreement_by_concentration.png", dpi=300)
    plt.close(fig)

    # Table 1: disagreement by site count and community structure (standardized pair).
    t1 = pct(d.groupby(["n_sites", "community_structure"]).standardized_different_fraction.mean()).unstack()
    t1[[c for c, _ in COMM]].to_csv(OUT / "table1_disagreement_by_sites_community.csv")

    # Table S3 and Figure 2: concentrated abundance, generous budget, pooled site counts.
    sub = d[(d.concentration == "concentrated") & (d.budget == "generous")]
    s3 = pct(sub.groupby(["weight", "community_structure"]).standardized_different_fraction.mean()).unstack()
    s3 = s3[[c for c, _ in COMM]]
    s3.to_csv(OUT / "tableS3_concentrated_generous_by_weight.csv")
    fig, ax = plt.subplots(figsize=(4.9, 2.8))
    for c, lab in COMM:
        ax.plot(s3.index, s3[c], "-o", label=lab)
    ax.set_xticks(s3.index)
    ax.set_xlabel("Conservation weight")
    ax.set_ylabel("Sites with different actions (%)")
    ax.set_ylim(0, 85)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figure2_community_by_weight.png", dpi=300)
    plt.close(fig)

    # Figure 3: two-way coverage forgone (applied pair).
    cols = ["applied_abund_cov_forgone_by_equal", "applied_equal_cov_forgone_by_abund",
            "portfolio_idle_equal", "applied_portfolio_idle_abund"]
    x = d.groupby(["community_structure", "concentration", "weight"])[cols].mean() * 100
    x.round(2).to_csv(OUT / "figure3_coverage_forgone_data.csv")
    fig, ax = plt.subplots(2, 3, figsize=(7.2, 5.0), sharex=True, sharey=True)
    for i, (r, rl) in enumerate(COMM):
        for j, (c, cl) in enumerate(zip(CONC, CONC_LABEL)):
            a = ax[i, j]
            s = x.loc[(r, c)]
            a.axhline(0, color="0.6", lw=0.7)
            a.plot(s.index, s[cols[0]], "-o", color="#1f5f8b", ms=4,
                   label="Abundance-weighted coverage given up by equal swing")
            a.plot(s.index, s[cols[1]], "--s", color="#c26a1b", ms=4,
                   label="Equal-swing coverage given up by abundance weighting")
            if i == 0:
                a.set_title(cl, fontsize=10)
            if j == 0:
                a.set_ylabel(f"{rl}\n\nPercentage points")
            if i == 1:
                a.set_xlabel("Conservation weight")
                eq, ab = s.loc[0.2, cols[2]], s.loc[0.2, cols[3]]
                abt = f"{ab:.0f}%" if ab >= 1 else "<1%"
                a.text(0.97, 0.04, f"Idle at w = 0.2\nequal swing {eq:.0f}%\nabundance {abt}",
                       transform=a.transAxes, ha="right", va="bottom", fontsize=7.5, color="0.25")
            a.set_xticks([0.2, 0.4, 0.6, 0.8])
            a.set_ylim(-48, 80)
            a.grid(axis="y", color="0.92")
            for sp in ["top", "right"]:
                a.spines[sp].set_visible(False)
    h, lab = ax[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=1, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(OUT / "figure3_two_way_coverage.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Table 2: diagnostics D1-D4 by conservation weight. "All" is the mean over all comparisons.
    def diag(g):
        n = len(g)
        return pd.Series({
            "D1_same": f"{int(g.d1_scale10_compensated_same.sum())}/{n}",
            "D2_changed_pct": round(100 * g.d2_scale10_nominal_changed_fraction.mean(), 1),
            "D3_same": f"{int(g.d3_vector_whole_cal_same.sum())}/{n}",
            "D4_changed_pct": round(100 * g.d4_vector_column_cal_changed_fraction.mean(), 1),
        })
    t2 = d.groupby("weight").apply(diag)
    t2.loc["All"] = diag(d)
    t2.to_csv(OUT / "table2_diagnostics_by_weight.csv")

    # Table S1 and Figure S1: standardized versus raw-effectiveness pair (Appendix S1).
    s1 = pct(e.groupby("concentration")[["standardized_different_fraction",
                                          "raw_effectiveness_different_fraction"]].mean()).loc[CONC]
    s1.to_csv(OUT / "tableS1_standardized_vs_raw.csv")
    fig, ax = plt.subplots(figsize=(4.9, 2.8))
    width = 0.35
    ax.bar([i - width / 2 for i in range(3)], s1.iloc[:, 0], width, label="Standardized effectiveness")
    ax.bar([i + width / 2 for i in range(3)], s1.iloc[:, 1], width, label="Raw effectiveness")
    ax.set_xticks(range(3), CONC_LABEL)
    ax.set_ylabel("Sites with different actions (%)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "figureS1_standardized_vs_raw.png", dpi=300)
    plt.close(fig)

    print("Wrote", ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
