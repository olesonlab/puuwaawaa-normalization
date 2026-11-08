"""Scaling experiment for MS 1: value-specification pairs plus scaling diagnostics.

Extends combined_simulation.py (v4). Landscapes, costs, community draws, budgets,
weights and the solver are imported from it unchanged, so the standardized pair
reproduces combined_results.csv.

Conservation value functions (a = abundance share, e = effectiveness, r = within-site range,
z = within-site min-max of e, which equals within-site min-max of a*e because a > 0):
  E   = z / I                  equal swing (within-site min-max)
  A_s = a * z                  abundance x standardized effectiveness (isolates abundance)
  A_r = a * e / sum(a * r)     abundance x raw effectiveness, criterion-wide scaling;
                               the score an applied model gets by scaling N*e across the
                               whole criterion (global min-max or whole-matrix vector),
                               swing-calibrated to the same total range as E and A_s
Each function sums to 1 over sitewise attainable ranges.

Pairs (each compared at the same nominal weight):
  standardized : E vs A_s   (v4 primary pair)
  applied      : E vs A_r   (within-site against criterion-wide scaling of the same N*e)

Diagnostics on the applied abundance score A_r. Each is a portfolio compared with the A_r portfolio:
  D1 scale10_compensated   10*A_r, conservation coefficient divided by 10, community coefficient
                           unchanged. Expected: identical (criterion-wide units).
  D2 scale10_nominal       10*A_r at the nominal weight. Expected: changes (effective weight).
  D3 vector_whole_cal      a*e divided by its whole-matrix Frobenius norm, then swing-calibrated.
                           Expected: identical (criterion-wide).
  D4 vector_column_cal     each action column of a*e divided by its own norm across sites, then
                           swing-calibrated. Expected: changes (alternative-specific).
                           Convention: the no-action column is all zero and stays zero.
A diagnostic portfolio counts as "same" if it is identical or ties the A_r objective
within a relative tolerance of 1e-6 (MILP gap is 1e-8; near-ties occur at 50 sites).

Outcomes: every portfolio in a pair is evaluated on both value functions as a share of that
function's budget-feasible maximum (community ignored), and on the community score.

Effectiveness designs (--effect):
  baseline  v4 draws: intermediate U(0.25, 0.70), intensive U(0.75, 1.00). Site range r varies 0.75-1.0.
  wide      intensive U(0.20, 1.00); intermediate = intensive x U(0.10, 0.90). Site range varies
            fivefold. Drawn from a separate stream, SeedSequence([20261026, n, ci, ri, rep, 55]),
            so abundance, costs and community draws are identical to baseline and results pair.

Run:  python -u scaling_experiment.py --sites 12 22 50 --reps 20 --workers 4 --effect baseline wide
Outputs (in --out, default ./scaling_out): scaling_results.csv, scaling_summary.csv,
scaling_diagnostics_summary.csv, run_info.json. A checkpoint is written after each site count.
"""
import argparse
import itertools
import json
import platform
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import combined_simulation as base  # noqa: E402

TIE_TOL = 1e-6


def value_functions(a, e):
    n = len(a)
    r = np.ptp(e, axis=1)
    if np.any(r <= 0):
        raise ValueError("zero effectiveness range at a site; declare a convention first")
    z = (e - e.min(axis=1, keepdims=True)) / r[:, None]
    E = z / n
    A_s = a[:, None] * z / a.sum()
    raw = a[:, None] * e
    A_r = raw / np.dot(a, r)
    return E, A_s, A_r, raw


def swing_calibrate(v):
    return v / np.ptp(v, axis=1).sum()


def column_vector(raw):
    norms = np.linalg.norm(raw, axis=0)
    out = np.zeros_like(raw)
    nz = norms > 0
    out[:, nz] = raw[:, nz] / norms[nz]
    return out


def landscape_rows(task):
    n, ci, ri, rep, diagnostics, effect = task
    concentration, shape = list(base.SHAPES.items())[ci]
    corr = base.CORRS[ri]
    solve = base.solver(n)
    ix = np.arange(n)
    rng, a, e, c = base.create(n, shape, corr, rep, ci, ri)
    if effect == "wide":
        erng = np.random.default_rng(np.random.SeedSequence([20261026, n, ci, ri, rep, 55]))
        hi = erng.uniform(.20, 1.00, n)
        e = np.column_stack([np.zeros(n), hi * erng.uniform(.10, .90, n), hi])
    elif effect != "baseline":
        raise ValueError(effect)
    E, A_s, A_r, raw = value_functions(a, e)
    zero = np.zeros_like(E)
    if diagnostics:
        V_whole = swing_calibrate(raw / np.linalg.norm(raw))
        V_col = swing_calibrate(column_vector(raw))
    # budget-feasible maxima of each value function alone
    maxima = {}
    for bn, b in base.BUDGETS.items():
        maxima[bn] = {name: v[ix, solve(v, zero, c, b, 1.0)].sum() for name, v in (("E", E), ("A_s", A_s), ("A_r", A_r))}
    rows = []
    for mode in base.COMM:
        crng = np.random.default_rng(np.random.SeedSequence([20261026, n, ci, ri, rep, base.COMM.index(mode), 987]))
        s = base.community(crng, n, mode)
        for bn, b in base.BUDGETS.items():
            mx = maxima[bn]
            for w in base.WEIGHTS:
                xE = solve(E, s, c, b, w)
                xS = solve(A_s, s, c, b, w)
                xR = solve(A_r, s, c, b, w)
                row = dict(effect_design=effect, n_sites=n, concentration=concentration, cost_relation=corr, trial=rep,
                           community_structure=mode, budget=bn, weight=w, abundance_hhi=float(np.dot(a, a)))
                for pair, xA, VA, key in (("standardized", xS, A_s, "A_s"), ("applied", xR, A_r, "A_r")):
                    row[f"{pair}_different_fraction"] = float(np.mean(xE != xA))
                    covE_E = E[ix, xE].sum() / mx["E"]
                    covE_A = E[ix, xA].sum() / mx["E"]
                    covA_E = VA[ix, xE].sum() / mx[key]
                    covA_A = VA[ix, xA].sum() / mx[key]
                    row[f"{pair}_equal_cov_of_equal"] = covE_E
                    row[f"{pair}_equal_cov_of_abund"] = covE_A
                    row[f"{pair}_abund_cov_of_equal"] = covA_E
                    row[f"{pair}_abund_cov_of_abund"] = covA_A
                    # positive = coverage given up by the other specification's portfolio
                    row[f"{pair}_equal_cov_forgone_by_abund"] = covE_E - covE_A
                    row[f"{pair}_abund_cov_forgone_by_equal"] = covA_A - covA_E
                    row[f"{pair}_community_abund_minus_equal"] = float(s[ix, xA].sum() - s[ix, xE].sum())
                    row[f"{pair}_portfolio_idle_abund"] = int(np.all(xA == 0))
                    row[f"{pair}_sites_no_action_abund"] = float(np.mean(xA == 0))
                row["portfolio_idle_equal"] = int(np.all(xE == 0))
                row["sites_no_action_equal"] = float(np.mean(xE == 0))
                if diagnostics:
                    f_ref = w * A_r[ix, xR].sum() + (1 - w) * s[ix, xR].sum()
                    w_comp = w / (10 - 9 * w)  # w'*10/(1-w') = w/(1-w)
                    cand = {
                        "d1_scale10_compensated": solve(10 * A_r, s, c, b, w_comp),
                        "d2_scale10_nominal": solve(10 * A_r, s, c, b, w),
                        "d3_vector_whole_cal": solve(V_whole, s, c, b, w),
                        "d4_vector_column_cal": solve(V_col, s, c, b, w),
                    }
                    for name, x in cand.items():
                        frac = float(np.mean(x != xR))
                        f_x = w * A_r[ix, x].sum() + (1 - w) * s[ix, x].sum()
                        tied = abs(f_ref - f_x) <= TIE_TOL * max(abs(f_ref), 1e-12)
                        row[f"{name}_changed_fraction"] = frac
                        row[f"{name}_same"] = int(frac == 0 or tied)
                rows.append(row)
    return rows


def boot_summary(df, metrics, seed, draws=1000):
    keys = ["effect_design", "n_sites", "concentration", "community_structure", "budget", "weight"]
    rng = np.random.default_rng(seed)
    out = []
    for k, g in df.groupby(keys, sort=True):
        row = dict(zip(keys, k)); row["n_landscapes"] = len(g)
        strata = [h[metrics].to_numpy(float) for _, h in g.groupby("cost_relation", sort=True)]
        boots = np.array([np.concatenate([v[rng.integers(len(v), size=len(v))] for v in strata]).mean(axis=0)
                          for _ in range(draws)])
        lo, hi = np.quantile(boots, [.025, .975], axis=0)
        for j, m in enumerate(metrics):
            row[m] = g[m].mean(); row[m + "_lo"] = lo[j]; row[m + "_hi"] = hi[j]
        out.append(row)
    return pd.DataFrame(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sites", type=int, nargs="+", default=[12, 22, 50])
    p.add_argument("--reps", type=int, default=20)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--no-diagnostics", action="store_true")
    p.add_argument("--out", default=str(HERE / "scaling_out"))
    p.add_argument("--effect", nargs="+", default=["baseline"], choices=["baseline", "wide"])
    args = p.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    diag = not args.no_diagnostics
    t0 = time.time(); rows = []
    for n in args.sites:
        tasks = [(n, ci, ri, rep, diag, eff) for eff in args.effect
                 for ci, ri, rep in itertools.product(range(3), range(3), range(args.reps))]
        if args.workers > 1:
            with Pool(args.workers) as pool:
                for r in pool.imap_unordered(landscape_rows, tasks, chunksize=2):
                    rows.extend(r)
        else:
            for t in tasks:
                rows.extend(landscape_rows(t))
        pd.DataFrame(rows).to_csv(out / "scaling_checkpoint.csv", index=False)
        print(f"finished {n} sites: {len(rows)} rows, {time.time() - t0:.0f} s", flush=True)
    order = ["effect_design", "n_sites", "concentration", "cost_relation", "trial", "community_structure", "budget", "weight"]
    df = pd.DataFrame(rows).sort_values(order, kind="mergesort").reset_index(drop=True)
    df.to_csv(out / "scaling_results.csv", index=False)
    pair_metrics = [f"{p}_{m}" for p in ("standardized", "applied") for m in
                    ("different_fraction", "equal_cov_forgone_by_abund", "abund_cov_forgone_by_equal",
                     "community_abund_minus_equal", "portfolio_idle_abund")] + ["portfolio_idle_equal"]
    boot_summary(df, pair_metrics, 20261027).to_csv(out / "scaling_summary.csv", index=False)
    if diag:
        dm = [f"{d}_{k}" for d in ("d1_scale10_compensated", "d2_scale10_nominal", "d3_vector_whole_cal",
                                   "d4_vector_column_cal") for k in ("same", "changed_fraction")]
        boot_summary(df, dm, 20261028).to_csv(out / "scaling_diagnostics_summary.csv", index=False)
    info = dict(effect=args.effect, sites=args.sites, reps=args.reps, workers=args.workers, diagnostics=diag, rows=len(df),
                seconds=round(time.time() - t0, 1), python=platform.python_version(), numpy=np.__version__,
                scipy=scipy.__version__, pandas=pd.__version__, platform=platform.platform(), tie_tol=TIE_TOL)
    (out / "run_info.json").write_text(json.dumps(info, indent=2))
    # console digest
    print(f"\nrows {len(df)}; {info['seconds']} s")
    print("\nShare of sites differing (%), pooled:")
    print((100 * df.groupby(["effect_design", "concentration"])[["standardized_different_fraction", "applied_different_fraction"]].mean()).round(1).to_string())
    if diag:
        print("\nDiagnostics: share of comparisons with the same portfolio (identical or tied), and mean share of sites changed (%):")
        for d in ("d1_scale10_compensated", "d2_scale10_nominal", "d3_vector_whole_cal", "d4_vector_column_cal"):
            print(f"  {d:26s} same {100 * df[d + '_same'].mean():6.2f}%   sites changed {100 * df[d + '_changed_fraction'].mean():5.1f}%")


if __name__ == "__main__":
    main()
