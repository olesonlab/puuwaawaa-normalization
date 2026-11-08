"""Crossed sensitivity experiment. Reproducible independent landscape seeds.
Outcomes are evaluated against each value function's own budget-feasible maximum,
not against an asserted 'true' conservation objective.
"""
import numpy as np, pandas as pd, argparse, time
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
from pathlib import Path
P=Path(__file__).resolve().parent
SHAPES={'diffuse':5.,'moderate':1.,'concentrated':.12}
CORRS=('independent','aligned','opposed')
COMM=('potential_alignment','consistent_conflict')
WEIGHTS=(.2,.4,.6,.8)
BUDGETS={'tight':.22,'generous':.48}
def solver(n):
 A=lil_matrix((n+1,3*n));
 for i in range(n):A[i,3*i:3*i+3]=1
 A=A.tocsr(); B=Bounds(np.zeros(3*n),np.ones(3*n)); integ=np.ones(3*n)
 def solve(v,s,c,b,w):
  mat=A.tolil();mat[n,:]=c.ravel();constraints=LinearConstraint(mat.tocsr(),np.r_[np.ones(n),-np.inf],np.r_[np.ones(n),b]);u=w*v+(1-w)*s
  r=milp(-u.ravel(),integrality=integ,bounds=B,constraints=constraints,options={'mip_rel_gap':1e-8,'time_limit':15})
  if r.status!=0 or r.x is None:raise RuntimeError(f'solver failed: status={r.status}, {r.message}')
  return r.x.reshape(n,3).argmax(axis=1)
 return solve
def seed_for(n,ci,ri,rep):return np.random.SeedSequence([20261026,n,ci,ri,rep])
def create(n,shape,corr,rep,ci,ri):
 rng=np.random.default_rng(seed_for(n,ci,ri,rep));a=rng.dirichlet(np.full(n,shape));e=np.column_stack([np.zeros(n),rng.uniform(.25,.7,n),rng.uniform(.75,1,n)])
 base=rng.uniform(.025,.065,n)*12/n; intensive=rng.uniform(.07,.13,n)*12/n
 if corr!='independent':
  order=np.argsort(a);v=np.sort(base);v2=np.sort(intensive)
  if corr=='opposed':v=v[::-1];v2=v2[::-1]
  t=np.empty(n);t2=np.empty(n);t[order]=v;t2[order]=v2;base=.8*t+.2*base;intensive=.8*t2+.2*intensive
 c=np.column_stack([np.zeros(n),base,intensive]);return rng,a,e,c

def community(rng,n,mode):
 if mode=='potential_alignment':
  s=np.column_stack([rng.uniform(.4,.8,n),rng.uniform(.3,1,n),rng.uniform(0,.65,n)])
 else:
  baseline=rng.uniform(.65,1.,n);middle=baseline-rng.uniform(.08,.30,n);intense=middle-rng.uniform(.10,.35,n);s=np.column_stack([baseline,middle,intense])
 return s/np.ptp(s,axis=1).sum()
def scores(a,e):
 r=np.ptp(e,axis=1);z=(e-e.min(axis=1)[:,None])/r[:,None]
 # Equal-swing: within-site min-max. Abundance: same effectiveness profile, weighted by abundance.
 return z/np.ptp(z,axis=1).sum(), (a[:,None]*z)/a.sum() # denominator sum abundance * within-site swing (=1)
def main(reps,site_counts):
 rows=[];start=time.time();count=0
 for n in site_counts:
  solve=solver(n);ix=np.arange(n)
  for ci,(concentration,shape) in enumerate(SHAPES.items()):
   for ri,corr in enumerate(CORRS):
    for rep in range(reps):
     rng,a,e,c=create(n,shape,corr,rep,ci,ri);v0,v1=scores(a,e)
     maxima={bn:(solve(v0,np.zeros_like(v0),c,b,1.),solve(v1,np.zeros_like(v1),c,b,1.)) for bn,b in BUDGETS.items()}
     for mode in COMM:
      # deterministic independent draws for both modes, conditional on landscape
      crng=np.random.default_rng(np.random.SeedSequence([20261026,n,ci,ri,rep,COMM.index(mode),987]))
      s=community(crng,n,mode)
      for bn,b in BUDGETS.items():
       for w in WEIGHTS:
        x0=solve(v0,s,c,b,w);x1=solve(v1,s,c,b,w)
        # maximum feasible ecological benefit under each conservation value definition
        m0,m1=maxima[bn]
        den0=v0[ix,m0].sum();den1=v1[ix,m1].sum()
        cov00=v0[ix,x0].sum()/den0;cov01=v0[ix,x1].sum()/den0
        cov10=v1[ix,x0].sum()/den1;cov11=v1[ix,x1].sum()/den1
        rows.append(dict(n_sites=n,concentration=concentration,cost_relation=corr,trial=rep,community_structure=mode,budget=bn,weight=w,abundance_hhi=(a*a).sum(),different_sites=int((x0!=x1).sum()),different_fraction=np.mean(x0!=x1),equal_coverage_equal=cov00,equal_coverage_abundance=cov01,abundance_coverage_equal=cov10,abundance_coverage_abundance=cov11,coverage_cost_of_abundance=cov00-cov01,abundance_cost_of_equal=cov11-cov10,community_equal=s[ix,x0].sum(),community_abundance=s[ix,x1].sum(),community_difference=s[ix,x1].sum()-s[ix,x0].sum(),managed_equal=int((x0>0).sum()),managed_abundance=int((x1>0).sum()),idle_equal=float(np.mean(x0==0)),idle_abundance=float(np.mean(x1==0))))
        count+=2
  print('finished n=',n,'solves=',count,'seconds=',round(time.time()-start,1),flush=True)
 df=pd.DataFrame(rows);df.to_csv(P/'combined_results.csv',index=False)
 # Paired bootstrap by landscape; report paired outcome contrasts and portfolio differences.
 group=['n_sites','concentration','community_structure','budget','weight'];metrics=['different_sites','different_fraction','coverage_cost_of_abundance','abundance_cost_of_equal','community_difference','idle_equal','idle_abundance']
 rng=np.random.default_rng(20261027);out=[]
 for keys,g in df.groupby(group,sort=True):
  values=g[metrics].to_numpy();m=len(g);idx=rng.integers(0,m,size=(1200,m));boots=values[idx].mean(axis=1);row=dict(zip(group,keys));row['n_landscapes']=m
  for j,key in enumerate(metrics):row[key]=values[:,j].mean();row[key+'_lo'],row[key+'_hi']=np.quantile(boots[:,j],[.025,.975])
  out.append(row)
 pd.DataFrame(out).to_csv(P/'combined_summary.csv',index=False)
 print('rows',len(df),'solves',count,'time',round(time.time()-start,1))
 print(pd.DataFrame(out).query("n_sites==12 and concentration=='concentrated' and budget=='generous'")[['community_structure','weight','different_sites','coverage_cost_of_abundance','abundance_cost_of_equal']].to_string(index=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reps',type=int,default=20);p.add_argument('--sites',type=int,nargs='+',default=[12,22,50]);args=p.parse_args();main(args.reps,args.sites)
