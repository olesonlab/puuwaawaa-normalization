"""Add incremental outcome columns to p9_budget_portfolios.csv and rebuild
p9_budget_headline_comparisons.csv.

Written 2026-11-07 to replace the lost original post-processing step. It
recomputes the reference outcome from the model (Alternative 11 in every
paddock, no roadside fuelbreak) instead of reading the archived columns.
Run after p9_budget_audit.py, in the same folder.
"""
import pathlib, sys, types, importlib.util
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT.parent  # repository root
stub = types.ModuleType('pulp')
for k in ['LpMaximize', 'LpProblem', 'LpStatus', 'LpVariable', 'lpSum', 'value']:
    setattr(stub, k, None)
sys.modules.setdefault('pulp', stub)
spec = importlib.util.spec_from_file_location('norm', SRC / 'src/normalization_comparison.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
inp = m.load_input_data(SRC / 'data/pww_sdm_input_data.xlsx')
A = m.PADDOCK_ALTS
P9 = 8  # zero-based row of Paddock 9

def action(road):
    fire = m.apply_roadside(inp['fire_prob'], road)
    return m.compute_action_effectiveness(inp['fire_prob_baseline'], fire)[:, A]

j11 = A.index(10)                      # Alternative 11 (no new action)
ref = action(False)[:, j11]
te_ref = float((ref * inp['te_count']).sum())
hab_ref = float((ref * inp['native_cover']).sum())
p9_ref = float(ref[P9] * inp['te_count'][P9])

df = pd.read_csv(ROOT / 'p9_budget_portfolios.csv')
ok = df.status == 'optimal'
df['te_incremental_index'] = np.where(ok, df.te_index - te_ref, np.nan)
df['habitat_incremental_index'] = np.where(ok, df.habitat_index - hab_ref, np.nan)
p9 = []
for _, r in df.iterrows():
    if r.status != 'optimal':
        p9.append(np.nan); continue
    j = A.index(int(r.p9_alt) - 1)
    p9.append(float(action(bool(r.roadside))[P9, j] * inp['te_count'][P9]) - p9_ref)
df['p9_incremental_te_index'] = p9
df.to_csv(ROOT / 'p9_budget_portfolios.csv', index=False)

rows = []
for (alpha, fixed, b), z in df[ok].groupby(['alpha', 'p9_fixed', 'budget_M']):
    cp = z[z.scenario == 'Conservation priority']
    if cp.empty:
        continue
    cp = cp.iloc[0]
    for label in ('Rancher-conservation', 'Hunter-recreationist', 'Community priority'):
        s = z[z.scenario == label]
        if s.empty:
            continue
        s = s.iloc[0]
        rows.append({'alpha': alpha, 'p9_fixed': fixed, 'budget_M': b,
                     'comparison': f'{label} vs Conservation priority',
                     'te_incremental_index_change': s.te_incremental_index - cp.te_incremental_index,
                     'habitat_incremental_index_change': s.habitat_incremental_index - cp.habitat_incremental_index,
                     'rancher_change': s.rancher - cp.rancher, 'hunter_change': s.hunter - cp.hunter,
                     'p9_alt_cp': cp.p9_alt, 'p9_alt_comparison': s.p9_alt})
pd.DataFrame(rows).to_csv(ROOT / 'p9_budget_headline_comparisons.csv', index=False)
print(f'reference: te {te_ref:.3f}, habitat {hab_ref:.3f}, P9 te {p9_ref:.3f}; {len(rows)} comparisons')
