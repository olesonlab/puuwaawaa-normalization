# The Normalization Trap in MCDA Conservation Planning

Code for:

> Oleson, K.L.L., Trauernicht, C., Lonsdorf, E., and Parsons, E.W.
> **"The normalization trap: how score scaling undermines multi-criteria
> decision analysis in conservation planning"**
> *Methods in Ecology and Evolution* (submitted)

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
1. `normalization_methods.py` — all three normalization methods + the concentration ratio diagnostic
2. `tradeoff_frontier.py` — tradeoff frontier analysis comparing methods across ecological weights
3. The worked example scripts from the paper

---

## Repository structure

```
puuwaawaa-normalization/
├── src/
│   ├── normalization_methods.py  # Core normalization functions + concentration ratio
│   └── tradeoff_frontier.py      # Tradeoff frontier figure (requires puuwaawaa-sdm data)
├── data/
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

Data archive: **[Zenodo DOI — add before publication]**

---

## Citation

```bibtex
@article{oleson2024normalization_trap,
  title   = {The normalization trap: how score scaling undermines multi-criteria
             decision analysis in conservation planning},
  author  = {Oleson, Kirsten L.L. and Trauernicht, Clay and
             Lonsdorf, Eric and Parsons, Elliott W.},
  journal = {Methods in Ecology and Evolution},
  year    = {submitted}
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
