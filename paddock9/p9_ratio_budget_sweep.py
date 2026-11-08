# Off-budget check and budget sweep for the Paddock 9 commitment (2026-11-07).
# Uses the published 21-paddock within-paddock model in src/normalization_comparison.py, CBC via PuLP 2.9.0.
# PuLP 4.x removed LpStatus, which the repository imports.
import sys, pathlib
REPO=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
import numpy as np, normalization_comparison as m
inp=m.load_input_data(REPO/'data'/'pww_sdm_input_data.xlsx')
fc=inp['costs'][m.FIXED_PADDOCK_IDX,m.FIXED_ALT_IDX]
sc=m.build_scenarios()
def run(total):
    return {s['label']:m.solve_scenario_budget(inp,'within_unit',m.effective_weights(s),total) for s in sc.values()}
def ex(g,lab,key):
    b=g['Balanced']['sub_scores']; r=g[lab]['sub_scores']; loss=b['te']-r['te']; gain=r[key]-b[key]
    return (gain,loss, gain/loss if loss>1e-9 else float('inf'))
print('total_M discr_M | S6 gain,loss,ratio | S5 gain,loss,ratio | S6/S5')
for tot in [5,7.5,10,12.5,15,17.5,20,22.5,23.9,25,30,40,60]:
    g=run(tot*1e6); s6=ex(g,'Rancher-conservation','rancher'); s5=ex(g,'Community priority','rancher')
    q=s6[2]/s5[2] if np.isfinite(s6[2]) and s5[2]>0 else float('nan')
    print(f"{tot:5} {tot-fc/1e6:6.2f} | {s6[0]:.2f},{s6[1]:.2f},{s6[2]:.2f} | {s5[0]:.2f},{s5[1]:.2f},{s5[2]:.2f} | {q:.2f}")
