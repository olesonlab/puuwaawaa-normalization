# Off-budget check and budget sweep for the Paddock 9 commitment (2026-11-07).
# Uses the published 21-paddock within-paddock model in src/normalization_comparison.py, CBC via PuLP 2.9.0.
# PuLP 4.x removed LpStatus, which the repository imports.
import sys, pathlib
REPO=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
import numpy as np, normalization_comparison as m
inp=m.load_input_data(REPO/'data'/'pww_sdm_input_data.xlsx')
fc=inp['costs'][m.FIXED_PADDOCK_IDX,m.FIXED_ALT_IDX]; print('P9 cost',fc)
def grid(offset):
    sc=m.build_scenarios(); out={}
    for s in sc.values():
        for b in m.BUDGETS:
            r=m.solve_scenario_budget(inp,'within_unit',m.effective_weights(s),b+offset)
            out[(s['label'],b)]=r
    return out
res={}
for name,off in [('on-budget (published)',0.0),('off-budget',fc)]:
    g=grid(off); met=m._symmetry_metrics(g); res[name]=g
    print('\n==',name, {k:(round(v,2) if isinstance(v,float) else v) for k,v in met.items()})
    for lab in ['Conservation priority','Community priority','Rancher-conservation','Balanced']:
        print(lab,[ (round(g[(lab,b)]['sub_scores']['te'],2), round(g[(lab,b)]['sub_scores']['rancher'],2), round((g[(lab,b)]['total_cost'])/1e6,2)) for b in m.BUDGETS])
on,off=res['on-budget (published)'],res['off-budget']
# how many portfolios change at each label
for b in m.BUDGETS:
    print(b/1e6, sum(not np.array_equal(on[(l,b)]['choices'],off[(l,b)]['choices']) for l in [s['label'] for s in m.build_scenarios().values()]),'of 7 scenarios change')
