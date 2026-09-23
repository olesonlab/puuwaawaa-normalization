"""
Normalization comparison in Appendix S1 of the companion Conservation Science and
Practice paper (CSP2-26-0352, puuwaawaa-sdm): Figures S10 and S11 and Tables S8 to S10.

Reads the output of normalization_comparison.py (appendix_score_spread.csv,
appendix_normalization_portfolios.csv, normalization_symmetry.csv) and the input
workbook for T&E counts, and writes PDF + 600 dpi PNG figures and CSV tables.

    python src/csp_appendix_figures.py data/pww_sdm_input_data.xlsx data figures
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

XLSX, IN, OUT = (sys.argv[1:4] + [None] * 3)[:3]
XLSX = XLSX or "pww_sdm_input_data.xlsx"; IN = IN or "normalization_check"; OUT = OUT or "figures"
os.makedirs(OUT, exist_ok=True)
MM = 1 / 25.4
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.linewidth": 0.7, "pdf.fonttype": 42, "savefig.bbox": "tight",
})
METHOD = {  # key: (label, color, marker, linestyle)
    "within_unit": ("Within-unit (main analysis)", "#08306b", "o", "-"),
    "global_linear": ("Global linear", "#D55E00", "s", "--"),
    "vector": ("Vector", "#8c8c8c", "^", ":"),
}
SCEN = {"Balanced": "Balanced", "Conservation priority": "Conservation Priority",
        "T&E emphasis": "T&E Emphasis", "Habitat emphasis": "Habitat Emphasis",
        "Community priority": "Community Priority", "Rancher-conservation": "Rancher-Conservation",
        "Hunter-recreationist": "Hunter-Recreationist"}
FIXED = 8                     # paddock 9 (0-based), pre-assigned to full restoration
CONS_ALTS = (4, 5, 6, 7)

rp = pd.read_excel(XLSX, "native_rareplants", header=None)
te = np.array([rp.iloc[i + 4, 2] for i in range(22)], dtype=float)
opt = [i for i in range(22) if i != FIXED]


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.pdf"); fig.savefig(f"{OUT}/{name}.png", dpi=600); plt.close(fig)
    print("wrote", name)


def te_protected(choices):
    c = np.array(str(choices).split(","), dtype=int)
    return int(te[FIXED] + sum(te[opt[k]] for k in range(21) if c[k] in CONS_ALTS))


# ------------------------------------------------ Table S8 and Figure S10: score spread
sp = pd.read_csv(f"{IN}/appendix_score_spread.csv")
sp = sp[~sp.roadside_built.astype(bool)]
rows = []
for m in ["global_linear", "vector", "within_unit"]:
    s = sp[sp.method == m].spread
    rows.append({"Normalization": METHOD[m][0], "Spread < 0.01": int((s < 0.01).sum()),
                 "Spread < 0.05": int((s < 0.05).sum()), "Spread < 0.10": int((s < 0.10).sum())})
pd.DataFrame(rows).to_csv(f"{OUT}/TableS8_score_spread.csv", index=False)

piv = sp.pivot(index="paddock", columns="method", values="spread")
piv["te"] = [te[p - 1] for p in piv.index]
piv = piv[piv.te > 0].sort_values("te")
fig, ax = plt.subplots(figsize=(120 * MM, 105 * MM))
y = np.arange(len(piv))
for m, (lab, col, mk, _) in METHOD.items():
    ax.scatter(piv[m], y, color=col, marker=mk, s=22, label=lab, zorder=3,
               edgecolor="white", linewidth=0.4)
for yi, (_, r) in zip(y, piv.iterrows()):
    ax.plot([r.vector, r.within_unit], [yi, yi], color="#e4e3df", lw=0.8, zorder=1)
ax.axvline(0.05, color="#52514e", lw=0.7, ls="--")
ax.text(0.052, len(piv) - 0.4, "0.05", fontsize=7, color="#52514e", va="top")
ax.set_xscale("log"); ax.set_xlim(1e-3, 1.5)
ax.set_yticks(y, [f"Paddock {p} ({int(t)})" for p, t in zip(piv.index, piv.te)])
ax.set_xlabel("Within-paddock spread of T&E scores (best minus worst alternative, log scale)")
ax.xaxis.grid(True, color="#e4e3df", lw=0.5); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.45, 1.0), ncol=3)
save(fig, "Figure_S10_score_spread")

# ------------------------------------------------ Table S9 and Figure S11: portfolios
pf = pd.read_csv(f"{IN}/appendix_normalization_portfolios.csv")
pf = pf[pf.method_comm == "global_linear"].copy()
pf["te_protected"] = pf.choices.apply(te_protected)
pf["spend_share"] = pf.total_cost / pf.budget
t9 = []
for s, lab in SCEN.items():
    row = {"Scenario": lab}
    for m in ["within_unit", "global_linear", "vector"]:
        r = pf[(pf.scenario == s) & (pf.method_eco == m) & (pf.budget == 20e6)].iloc[0]
        short = {"within_unit": "Within-unit", "global_linear": "Global linear", "vector": "Vector"}[m]
        row[f"{short}: conservation actions"] = int(r.n_conservation_alts)
        row[f"{short}: grazing intensification"] = int(r.n_alt3)
        row[f"{short}: T&E under conservation actions"] = int(r.te_protected)
    t9.append(row)
pd.DataFrame(t9).to_csv(f"{OUT}/TableS9_portfolios_20M_by_normalization.csv", index=False)

cp = pf[pf.scenario == "Conservation priority"]
fig, axes = plt.subplots(1, 2, figsize=(170 * MM, 65 * MM))
for m, (lab, col, mk, ls) in METHOD.items():
    d = cp[cp.method_eco == m].sort_values("budget_M")
    axes[0].plot(d.budget_M, d.te_protected, color=col, marker=mk, ls=ls, lw=1.4, ms=4.5, label=lab)
    axes[1].plot(d.budget_M, d.n_alt3, color=col, marker=mk, ls=ls, lw=1.4, ms=4.5, label=lab)
axes[0].axhline(te.sum(), color="#bdbdbd", lw=0.7, ls=":")
axes[0].text(5, te.sum() + 8, f"All {int(te.sum()):,} T&E individuals", fontsize=7, color="#52514e")
axes[0].set_ylabel("T&E individuals in paddocks under\nremoval or restoration (Alts 4 to 7)")
axes[1].set_ylabel("Paddocks assigned grazing\nintensification (Alt 3)")
for ax, letter in zip(axes, "AB"):
    ax.set_xscale("log"); ax.set_xticks([5, 10, 20, 40, 60], ["$5M", "$10M", "$20M", "$40M", "$60M"])
    ax.minorticks_off(); ax.set_xlabel("Budget (log scale)")
    ax.yaxis.grid(True, color="#e4e3df", lw=0.5); ax.set_axisbelow(True)
    ax.text(-0.14, 1.03, letter, transform=ax.transAxes, fontsize=10, fontweight="bold")
axes[0].set_ylim(500, 1060); axes[1].set_ylim(-0.5, 21)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.1))
fig.tight_layout(w_pad=3)
save(fig, "Figure_S11_conservation_priority_by_normalization")

# ------------------------------------------------ Table S10: crossed normalization
sy = pd.read_csv(f"{IN}/normalization_symmetry.csv")
name = {"within_unit": "Within-unit", "global_linear": "Global linear"}


def ratio(v):
    return "No T&E lost" if not np.isfinite(v) else f"{v:.2f}"


t10 = []
for _, r in sy.iterrows():
    t10.append({"Conservation objectives": name[r.eco], "Community objectives": name[r.comm],
                "Asymmetry ratio": f"{r.asym_ratio:.2f}",
                "S6 rancher pts per T&E pt lost": ratio(r.S6_rancher_per_te),
                "S5 rancher pts per T&E pt lost": ratio(r.S5_rancher_per_te),
                "S7 hunter pts per T&E pt lost": ratio(r.S7_hunter_per_te),
                "S6 change in T&E": f"{r.S6_te_change:+.2f}",
                "S6 change in rancher": f"{r.S6_rancher_change:+.2f}"})
pd.DataFrame(t10).to_csv(f"{OUT}/TableS10_crossed_normalization.csv", index=False)
print(pd.DataFrame(t10).to_string())
