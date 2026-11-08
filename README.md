# Score scaling in the Puʻuwaʻawaʻa spatial portfolio model

Code for the normalization comparison (Appendix S1) and the Paddock 9 structural sensitivity in:

> Oleson, K. L. L., Trauernicht, C., Lonsdorf, E., Parsons, E. W., and Adkins, E.
> **Structured Decision Making reveals asymmetric tradeoffs between conservation and community objectives at Puʻuwaʻawaʻa Forest Reserve, Hawaiʻi.**
> *Conservation Science and Practice* (in review).

The optimizer and the main analyses are in the companion repository
[olesonlab/puuwaawaa-sdm](https://github.com/olesonlab/puuwaawaa-sdm).

---

## Overview

The Puʻuwaʻawaʻa model chooses one management alternative per paddock under a budget, maximizing a weighted sum of ecological and community scores. Before weighting, each criterion's raw scores have to be put on a common scale, and the way that is done is a choice about value, not a neutral numerical step. This repository compares three scalings of the same data:

| Scaling | Formula | What it expresses |
|---|---|---|
| Global linear (criterion-wide) | `(x - min) / (max - min)` over all paddocks and alternatives | Score differences keep their size across paddocks, so a paddock with larger raw differences (for T&E, more recorded individuals) contributes more |
| Vector (alternative-specific) | `x / ‖x‖₂` for each alternative | Each alternative's column is scaled to unit length |
| Within-unit (site-specific) | `(x - unit min) / (unit max - unit min)` for each paddock | Every paddock's best and worst actions span the same range, so each paddock carries an equal swing |

Within-unit scaling, used in the main analysis, and abundance-weighted scaling are alternative specifications of conservation value; neither is the more accurate calculation. Here "global" means one range for a criterion across all paddocks and alternatives in the model. It is not the global scale of Monat (2009), whose endpoints are set by the plausible range of a criterion rather than by the options being compared.

The repository contains:

1. `src/normalization_methods.py`: the three scaling functions and two descriptive statistics of how concentrated a criterion is across paddocks (top-k share and Gini coefficient)
2. `src/normalization_comparison.py`: the empirical comparison on the Puʻuwaʻawaʻa data, the crossed eco/community symmetry metrics, the simulated-landscape experiment and the within-paddock score spreads
3. `src/csp_appendix_figures.py`: Figures S10 and S11 and Tables S8 to S10 of Appendix S1
4. `src/tradeoff_frontier.py`: tradeoff frontiers across ecological weights
5. `paddock9/`: the Paddock 9 structural sensitivity and budget sweep (Tables S11 and S12); see `paddock9/README.md`

The model structure matches `pww_sdm_optimizer.py` in the companion repository: paddocks choose among the ten paddock-level alternatives, and the roadside fuelbreak is a single landscape decision built once for the reserve or not at all.

Some docstrings, plot labels and output column names in `src/` (for example "recommended" and `compressed_units`) date from an earlier framing of this analysis. They are kept unchanged so the archived outputs reproduce; the papers do not treat within-unit scaling as the correct default or a 0.05 spread as a threshold.

---

## Repository structure

```
puuwaawaa-normalization/
├── src/
│   ├── normalization_methods.py
│   ├── normalization_comparison.py
│   ├── tradeoff_frontier.py         # requires puuwaawaa-sdm
│   └── csp_appendix_figures.py
├── paddock9/
│   ├── p9_budget_audit.py
│   ├── p9_budget_incremental.py
│   ├── p9_offbudget_check.py
│   ├── p9_ratio_budget_sweep.py
│   ├── p9_budget_portfolios.csv
│   ├── p9_budget_headline_comparisons.csv
│   ├── p9_offbudget_check.txt
│   ├── p9_ratio_budget_sweep.txt
│   └── README.md
├── data/
│   ├── pww_sdm_input_data.xlsx
│   ├── empirical_normalization_comparison.csv
│   ├── appendix_score_spread.csv
│   ├── appendix_normalization_portfolios.csv
│   ├── normalization_symmetry.csv
│   ├── simulation_normalization_comparison.csv
│   └── README_data.md
├── figures/
├── requirements.txt
└── README.md
```

---

## Setup

```bash
git clone https://github.com/olesonlab/puuwaawaa-normalization.git
cd puuwaawaa-normalization
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

PuLP is pinned at 2.9.0 because the code imports `LpStatus`, which PuLP 4 removed. SciPy 1.9 or later provides the HiGHS `milp` solver used in `paddock9/`.

---

## Usage

### Paddock 9 structural sensitivity (Tables S11 and S12)

```bash
python paddock9/p9_budget_audit.py
python paddock9/p9_budget_incremental.py
python paddock9/p9_offbudget_check.py   > paddock9/p9_offbudget_check.txt
python paddock9/p9_ratio_budget_sweep.py > paddock9/p9_ratio_budget_sweep.txt
```

### Empirical comparison, simulation and diagnostics

```bash
python src/normalization_comparison.py data/pww_sdm_input_data.xlsx ./out
```

`--parts` selects the stages: 1 the empirical comparison, the appendix portfolios
and the crossed symmetry metrics, 2 the simulated landscapes, 3 the score spread
diagnostics. All five output CSVs are committed under `data/`, so the figures
reproduce without rerunning the solver.

The symmetry stage crosses the conservation and community normalizations over
four pairings and records the exchange ratios at $20M. Under the
within-unit/global-linear pairing used in the paper it reproduces the companion
repository's sensitivity baseline to fifteen significant figures: asymmetry
ratio 1.7528, and 3.3132, 0.5851 and 0.4042 rancher or hunter points per T&E
point lost for S6, S5 and S7.

### Appendix S1 figures and tables

The normalization comparison reported in Appendix S1 of the companion paper
(puuwaawaa-sdm) reads the committed CSVs, so it needs no solver:

```bash
python src/csp_appendix_figures.py data/pww_sdm_input_data.xlsx data figures
```

It writes Figures S10 and S11 as PDF and 600 dpi PNG, and Tables S8 to S10 as CSV.

### Tradeoff frontier (requires Puʻuwaʻawaʻa input data)

```bash
# Clone companion repo alongside this one
git clone https://github.com/olesonlab/puuwaawaa-sdm.git

python src/tradeoff_frontier.py \
    --data ../puuwaawaa-sdm/data/pww_sdm_input_data.xlsx \
    --budget 20000000 \
    --output_dir ./figures
```

---

## Data

The Puʻuwaʻawaʻa case-study data are shared with the companion repository.
See `data/README_data.md` and [github.com/olesonlab/puuwaawaa-sdm](https://github.com/olesonlab/puuwaawaa-sdm).

A copy of the input workbook is committed in `data/`, byte-identical to the
archived record: **https://doi.org/10.5281/zenodo.20369405**

---

## Citation

See `CITATION.cff`. An earlier version of this analysis was posted as a preprint (https://doi.org/10.2139/ssrn.7485898) under a framing the current papers no longer use.

---

## License

Code: MIT License  
Data: CC BY 4.0

---

## Contact

Kirsten Oleson — koleson@hawaii.edu  
Department of Natural Resources and Environmental Management  
University of Hawaiʻi at Mānoa
