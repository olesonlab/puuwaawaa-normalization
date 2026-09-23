# The Normalization Trap in MCDA Conservation Planning

Code for:

> Oleson, K.L.L., Trauernicht, C., Lonsdorf, E., and Parsons, E.W.
> **"The normalization trap: how score scaling undermines multi-criteria
> decision analysis in conservation planning"**
> *Ecological Solutions and Evidence* (in review)

Preprint: https://doi.org/10.2139/ssrn.7485898

The applied analysis using the recommended within-unit normalization method is at:
[github.com/olesonlab/puuwaawaa-sdm](https://github.com/olesonlab/puuwaawaa-sdm)

---

## Overview

Multi-criteria decision analysis (MCDA) requires normalizing raw scores onto
a common scale before weighting and optimization. This paper shows that the
two most common approaches — global linear and vector (Euclidean) normalization
— systematically compress the scores of spatially concentrated objectives
(e.g., threatened plant populations) relative to broadly distributed objectives
(e.g., community preferences). In conservation optimization, this causes the
optimizer to undervalue the objectives practitioners care most about.

This repository contains:
1. `normalization_methods.py` — all three normalization methods and the concentration ratio diagnostic
2. `normalization_comparison.py` — the empirical comparison on the Puʻuwaʻawaʻa data, the crossed eco/community symmetry metrics, the simulated-landscape experiment, and the score spread diagnostics
3. `tradeoff_frontier.py` — tradeoff frontier analysis comparing methods across ecological weights

The model structure matches `pww_sdm_optimizer.py` in the companion repository:
paddocks choose among the ten paddock-level alternatives, and the roadside
fuelbreak is a single landscape decision built once for the reserve or not at
all.

---

## Repository structure

```
puuwaawaa-normalization/
├── src/
│   ├── normalization_methods.py     # Core normalization functions + concentration ratio
│   ├── normalization_comparison.py  # Empirical, simulation and diagnostic runs
│   ├── tradeoff_frontier.py         # Tradeoff frontier figure (requires puuwaawaa-sdm)
│   └── csp_appendix_figures.py      # Figures S10, S11 and Tables S8 to S10 of the CSP paper
├── data/
│   ├── pww_sdm_input_data.xlsx
│   ├── empirical_normalization_comparison.csv
│   ├── appendix_score_spread.csv
│   ├── appendix_normalization_portfolios.csv
│   ├── normalization_symmetry.csv
│   ├── simulation_normalization_comparison.csv
│   └── README_data.md
├── figures/                      # Generated figures
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

---

## Usage

### Concentration ratio diagnostic

```python
from src.normalization_methods import concentration_ratio, gini_coefficient

# Your raw T&E counts per spatial unit
te_counts = [580, 216, 94, 47, 28, ...]   # example: Puʻuwaʻawaʻa paddocks

cr = concentration_ratio(te_counts, top_k=3)
g  = gini_coefficient(te_counts)

print(f"Concentration ratio (top-3): {cr:.2f}")
# > 0.6 → within-unit normalization strongly recommended
# 0.4–0.6 → worth comparing methods
# < 0.4 → method choice has minimal impact

print(f"Gini coefficient: {g:.2f}")
```

### Compare normalization methods

```python
import numpy as np
from src.normalization_methods import compare_normalization_methods

# raw_scores: dict of {objective: array(n_paddocks, n_alternatives)}
results = compare_normalization_methods(
    raw_scores={"te": te_matrix, "rancher": rancher_matrix},
    weights=[0.8, 0.2],   # conservation-priority weights
)

# results["global_linear"], results["vector"], results["within_unit"]
# each is a (n_paddocks x n_alternatives) weighted score matrix
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

### Appendix S1 of the Conservation Science and Practice paper

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

## The three normalization methods

| Method | Formula | Behaviour |
|---|---|---|
| Global linear | `(x - global_min) / (global_max - global_min)` | Preserves absolute differences across all units |
| Vector (Euclidean) | `x / ‖x‖₂` per alternative | Column-wise scaling; sensitive to extreme values |
| **Within-unit** (recommended) | `(x - unit_min) / (unit_max - unit_min)` per paddock | Scores relative best/worst within each unit; decouples spatial priority from action effectiveness |

---

## Data

The Puʻuwaʻawaʻa case-study data are shared with the companion repository.
See `data/README_data.md` and [github.com/olesonlab/puuwaawaa-sdm](https://github.com/olesonlab/puuwaawaa-sdm).

A copy of the input workbook is committed in `data/`, byte-identical to the
archived record: **https://doi.org/10.5281/zenodo.20369405**

---

## Citation

See `CITATION.cff`, or:

```bibtex
@article{oleson_normalization_trap,
  title   = {The normalization trap: how score scaling undermines multi-criteria
             decision analysis in conservation planning},
  author  = {Oleson, Kirsten L.L. and Trauernicht, Clay and
             Lonsdorf, Eric and Parsons, Elliott W.},
  journal = {Ecological Solutions and Evidence},
  note    = {In review},
  doi     = {10.2139/ssrn.7485898}
}
```

---

## License

Code: MIT License  
Data: CC BY 4.0

---

## Contact

Kirsten Oleson — koleson@hawaii.edu  
Department of Natural Resources and Environmental Management  
University of Hawaiʻi at Mānoa
