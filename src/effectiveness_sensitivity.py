"""Paired sensitivity audit: within-site standardized versus raw effectiveness.
Uses the exact landscape/community generator in combined_simulation.py.
Run: python -u effectiveness_sensitivity.py --sites 12 22 50 --reps 20
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import combined_simulation as base

OUT=Path(__file__).resolve().parent

def formulations(a,e):
    r=np.ptp(e,axis=1)
    if np.any(r<=0): raise ValueError('Zero effectiveness range')
    z=(e-e.min(axis=1,keepdims=True))/r[:,None]
    # Within-site normalization, isolate spatial weighting.
    standardized=(z/len(a),a[:,None]*z/a.sum())
    # Original factorial design: retain site-to-site effectiveness range differences.
    raw=(e/r.sum(),a[:,None]*e/np.dot(a,r))
    return {'standardized':standardized,'raw_effectiveness':raw}

def run(site_counts,reps):
    rows=[]
    for n in site_counts:
        solve=base.solver(n); ix=np.arange(n)
        for ci,(concentration,shape) in enumerate(base.SHAPES.items()):
            for ri,corr in enumerate(base.CORRS):
                for trial in range(reps):
                    rng,a,e,c=base.create(n,shape,corr,trial,ci,ri)
                    defs=formulations(a,e)
                    for mode in base.COMM:
                        crng=np.random.default_rng(np.random.SeedSequence([20261026,n,ci,ri,trial,base.COMM.index(mode),987]))
                        s=base.community(crng,n,mode)
                        for bn,b in base.BUDGETS.items():
                            for w in base.WEIGHTS:
                                item={'n_sites':n,'concentration':concentration,'cost_relation':corr,'trial':trial,'community_structure':mode,'budget':bn,'weight':w,'abundance_hhi':float(np.dot(a,a))}
                                portfolios={}
                                for name,(v0,v1) in defs.items():
                                    x0=solve(v0,s,c,b,w);x1=solve(v1,s,c,b,w)
                                    portfolios[name]=(x0,x1)
                                    item[name+'_different_sites']=int(np.count_nonzero(x0!=x1))
                                    item[name+'_different_fraction']=float(np.mean(x0!=x1))
                                    item[name+'_community_difference']=float(s[ix,x1].sum()-s[ix,x0].sum())
                                    # Both objective-specific conservation outcomes are evaluated on their own feasible scale.
                                    item[name+'_equal_score_difference']=float(v0[ix,x0].sum()-v0[ix,x1].sum())
                                    item[name+'_abundance_score_difference']=float(v1[ix,x1].sum()-v1[ix,x0].sum())
                                (x0,x1)=portfolios['standardized'];(y0,y1)=portfolios['raw_effectiveness']
                                item['equal_portfolio_changed_between_formulations']=int(np.count_nonzero(x0!=y0))
                                item['abundance_portfolio_changed_between_formulations']=int(np.count_nonzero(x1!=y1))
                                item['difference_in_disagreement']=item['raw_effectiveness_different_sites']-item['standardized_different_sites']
                                rows.append(item)
        pd.DataFrame(rows).to_csv(OUT/'effectiveness_sensitivity_checkpoint.csv',index=False)
        print('completed',n,'sites; records',len(rows),'(checkpoint saved)',flush=True)
    df=pd.DataFrame(rows)
    df.to_csv(OUT/'effectiveness_sensitivity_results.csv',index=False)
    keys=['n_sites','concentration','community_structure','budget','weight']
    metrics=['standardized_different_fraction','raw_effectiveness_different_fraction','difference_in_disagreement','equal_portfolio_changed_between_formulations','abundance_portfolio_changed_between_formulations']
    # Stratified paired bootstrap over the 20 replicates within each cost-relationship stratum.
    bootrng=np.random.default_rng(20261028)
    summary=[]
    for k,g in df.groupby(keys,sort=True):
        row=dict(zip(keys,k));row['n_landscapes']=len(g)
        for m in metrics:row[m]=g[m].mean()
        vals=[h[metrics].to_numpy() for _,h in g.groupby('cost_relation',sort=True)]
        draws=[]
        for _ in range(1000):
            sampled=np.concatenate([v[bootrng.integers(len(v),size=len(v))] for v in vals],axis=0)
            draws.append(sampled.mean(axis=0))
        q=np.quantile(draws,[.025,.975],axis=0)
        for j,m in enumerate(metrics):row[m+'_lo']=q[0,j];row[m+'_hi']=q[1,j]
        summary.append(row)
    pd.DataFrame(summary).to_csv(OUT/'effectiveness_sensitivity_summary.csv',index=False)
    print('Saved',len(df),'paired records and',len(summary),'summary groups',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sites',type=int,nargs='+',default=[12,22,50]);p.add_argument('--reps',type=int,default=20)
    args=p.parse_args();run(args.sites,args.reps)
