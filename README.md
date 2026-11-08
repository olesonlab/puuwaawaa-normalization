# When scaling changes conservation priorities

Simulation code and results for:

> Oleson, K. L. L., Trauernicht, C., Parsons, E. W., and Lonsdorf, E. When scaling changes conservation priorities: evaluating normalization choices in spatial decision analysis. Submitted to *Ecological Solutions and Evidence*.

The paper asks when rescaling a conservation criterion changes the portfolio chosen by a budgeted integer program that assigns one action to each site. Rescaling a whole criterion with a compensating coefficient, or normalizing the whole site–action matrix by its vector norm, leaves the portfolio unchanged. Rescaling at a fixed nominal weight, normalizing each action column separately, or switching between equal-swing and abundance-weighted conservation scores changes it. Equal-swing and abundance-weighted scoring are treated as alternative value specifications. Neither is presented as the correct one.

All results come from simulated landscapes. No field data are analysed. The Puʻuwaʻawaʻa Forest Reserve decision model that motivated the study is archived separately at [olesonlab/puuwaawaa-sdm](https://github.com/olesonlab/puuwaawaa-sdm).

## Contents

- `src/combined_simulation.py` generates landscapes (abundance concentration, cost–abundance relation, community response, budget, conservation weight) and solves the budgeted site–action program with SciPy's `milp`. It raises an error unless the solver reports an optimal solution. The other scripts import it.
- `src/scaling_experiment.py` runs the standardized and applied pairs and diagnostics D1–D4 under the baseline and wide effectiveness designs.
- `src/effectiveness_sensitivity.py` runs the raw-effectiveness pair reported in Appendix S1.
- `src/make_exhibits.py` rebuilds the tables and figures from the archived results.
- `results/scaling_experiment/` holds the output of `scaling_experiment.py` for both effectiveness designs (17,280 comparisons; the 8,640 baseline rows are those used in the main-text exhibits), with `run_info.json` recording the software versions and platform.
- `results/effectiveness_sensitivity/` holds the output of `effectiveness_sensitivity.py` (8,640 comparisons).
- `exhibits/` holds the tables (CSV) and figures (PNG) written by `make_exhibits.py`.

## Reproducing the results

```
pip install -r requirements.txt

# Standardized and applied pairs, diagnostics D1–D4, both effectiveness designs (about 3 minutes with 4 workers)
python -u src/scaling_experiment.py --sites 12 22 50 --reps 20 --workers 4 --effect baseline wide --out scaling_out

# Raw-effectiveness pair (Appendix S1); writes its outputs next to the script
python -u src/effectiveness_sensitivity.py --sites 12 22 50 --reps 20

# Tables and figures from the archived results
python src/make_exhibits.py
```

Every landscape is drawn from a deterministic seed. The archived scaling results were produced on macOS 15.5 with Python 3.13, NumPy 2.4 and SciPy 1.17. Reruns on Linux with Python 3.13 or 3.14 and SciPy 1.18 gave the following:

- Baseline design: near-tied alternative optima in 3 of 8,640 comparisons, all at 50 sites, with relative objective differences below 10⁻⁶.
- Wide design: a different portfolio in 3 of 8,640 comparisons, all at 50 sites, at one or two sites each. Eight 22-site rows differed by less than 10⁻⁶ in a continuous outcome, which is floating-point noise; their portfolios were identical. Every wide-design value quoted in the manuscript is the same in the rerun.
- Raw-effectiveness pair: 8,636 of 8,640 records matched; the four that differed were near-tied 50-site comparisons.

No pooled mean reported in the manuscript changes at the precision given.

## Exhibits

| Manuscript | File in `exhibits/` | Source |
| --- | --- | --- |
| Figure 1, Table S2 | `figure1_disagreement_by_concentration.png`, `tableS2_disagreement_by_sites_concentration.csv` | Standardized pair, baseline design |
| Table 1 | `table1_disagreement_by_sites_community.csv` | Standardized pair, baseline design |
| Figure 2, Table S3 | `figure2_community_by_weight.png`, `tableS3_concentrated_generous_by_weight.csv` | Standardized pair, baseline design, concentrated abundance, generous budget |
| Figure 3 | `figure3_two_way_coverage.png`, `figure3_coverage_forgone_data.csv` | Applied pair, baseline design |
| Table 2 | `table2_diagnostics_by_weight.csv` | Diagnostics D1–D4, baseline design |
| Figure S1, Table S1 | `figureS1_standardized_vs_raw.png`, `tableS1_standardized_vs_raw.csv` | `results/effectiveness_sensitivity/` |

Wide-design results quoted in the text are in the rows of `results/scaling_experiment/scaling_results.csv` with `effect_design == "wide"`.

## Earlier versions

Versions 1.0.0 and 1.1.0 of this repository hold code for an earlier, superseded manuscript on normalization in conservation MCDA. That code, including the concentration-ratio diagnostic and the Puʻuwaʻawaʻa normalization comparison, is not used in this paper. The Puʻuwaʻawaʻa normalization comparison now lives in [olesonlab/puuwaawaa-sdm](https://github.com/olesonlab/puuwaawaa-sdm). The earlier versions remain available from Zenodo.

## License

MIT. See `LICENSE`.
