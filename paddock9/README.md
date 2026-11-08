# Paddock 9 structural sensitivity and budget sweep

Code and output for the Paddock 9 structural sensitivity (Methods and final Results section) and Tables S11 and S12 of Appendix S1 in:

> Oleson, K. L. L., Trauernicht, C., Lonsdorf, E., Parsons, E. W., and Adkins, E. Structured Decision Making reveals asymmetric tradeoffs between conservation and community objectives at Puʻuwaʻawaʻa Forest Reserve, Hawaiʻi. *Conservation Science and Practice* (in review).

The main analysis fixes full restoration of Paddock 9 (Alternative 7) as a standing commitment and optimizes the other 21 paddocks. These scripts ask what changes if Paddock 9 competes like any other paddock, and how that answer depends on the way conservation value is specified. The free-Paddock-9 runs are counterfactuals for understanding the model. They are not advice to stop conservation management in Paddock 9, which continues.

## Scripts

Run from the repository root after `pip install -r requirements.txt`.

| Script | What it does | Solver | Output |
|---|---|---|---|
| `p9_budget_audit.py` | All 22 paddocks; Paddock 9 fixed or free; α = 0, 0.5, 1; seven weighting scenarios; budgets $0.5–60M; roadside fuelbreak built or not | SciPy `milp` (HiGHS) | `p9_budget_portfolios.csv`, `p9_budget_headline_comparisons.csv` |
| `p9_budget_incremental.py` | Adds `te_incremental_index`, `habitat_incremental_index` and `p9_incremental_te_index`, measured against the no-new-action reference, and rebuilds the comparisons | none | overwrites both CSVs |
| `p9_offbudget_check.py` | Published 21-paddock within-paddock model with the Paddock 9 cost counted inside or outside the budget | CBC via PuLP 2.9.0 | `p9_offbudget_check.txt` (stdout) |
| `p9_ratio_budget_sweep.py` | Rancher-points-per-T&E-point exchange ratios for Rancher-conservation (S6) and Community priority (S5) at totals of $5–60M that include the Paddock 9 commitment (Table S12) | CBC via PuLP 2.9.0 | `p9_ratio_budget_sweep.txt` (stdout) |

```bash
python paddock9/p9_budget_audit.py
python paddock9/p9_budget_incremental.py
python paddock9/p9_offbudget_check.py   > paddock9/p9_offbudget_check.txt
python paddock9/p9_ratio_budget_sweep.py > paddock9/p9_ratio_budget_sweep.txt
```

The first two scripts take about 12 s together. All four import the model from `src/normalization_comparison.py`.

## Conservation value specifications

- α = 0: within-paddock action ranges, as in the main analysis. Each paddock's best and worst actions span the same score range regardless of how many T&E individuals or how much native cover it holds.
- α = 0.5 and α = 1: the within-paddock range multiplied by the paddock's T&E count or native cover, normalized to the maximum and raised to the power α. Scores are rescaled so their aggregate attainable swing matches α = 0.

Community scores use global linear scaling throughout. These are alternative specifications of conservation value, not a correct and an incorrect calculation.

## Indices

`te_index` is the sum over paddocks of the recorded T&E count times the unnormalized action effectiveness of the chosen action (direct benefit plus 6 × fire reduction / maximum reduction). Alternative 11 everywhere with no roadside fuelbreak scores 1,013, the reserve's T&E count; the incremental columns subtract that reference, and `p9_incremental_te_index` subtracts Paddock 9's 580. Global linear scaling is an affine transform of this index, so it maximizes it exactly, and α = 1 maximizes a close variant. Use the index to compare fixed and free Paddock 9 within one α, not to rank the specifications.

## Provenance and reproduction check

`p9_budget_audit.py` was first written with OpenAI ChatGPT. `p9_budget_incremental.py` replaces a post-processing step from that session that was not preserved. `p9_offbudget_check.py` and `p9_ratio_budget_sweep.py` were written with Perplexity Computer. The authors specified and checked all four.

On 2026-11-07 the scripts were rerun from this repository (Linux, Python 3.14, SciPy 1.18.1, NumPy 2.5, pandas 3.1, PuLP 2.9.0):

- Solver status matched in all 336 rows of `p9_budget_portfolios.csv` (273 optimal, 63 infeasible; every infeasible row is fixed Paddock 9 at $0.5–2M), and the MIP gap was 0 in every solved row.
- Paddock assignments matched in 272 of 273 solved rows. The exception (α = 1, Paddock 9 free, Hunter-recreationist, $10M) is a tie with the same objective, indices, community scores and Paddock 9 choice; cost differs by $6,557.
- Indices and community scores matched to 2 × 10⁻¹², and all 117 comparisons matched.
- `p9_ratio_budget_sweep.txt` reproduced exactly. At $20M the on-budget run in `p9_offbudget_check.txt` reproduces the published asymmetry ratio 1.75 and exchange ratios 3.31 (S6) and 0.59 (S5).
