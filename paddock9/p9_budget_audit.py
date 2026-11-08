"""Paddock 9 structural sensitivity: all 22 paddocks, Paddock 9 fixed or free,
three conservation value specifications (alpha = 0, 0.5, 1), eight budgets.
Solved with SciPy milp (HiGHS). Writes p9_budget_portfolios.csv and
p9_budget_headline_comparisons.csv in this folder. Run p9_budget_incremental.py
afterwards to add the incremental columns. Archived 21-paddock results in
data/ are not overwritten.
"""
import pathlib, sys, types, importlib.util
import numpy as np, pandas as pd
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
ROOT=pathlib.Path(__file__).resolve().parent
SRC=ROOT.parent  # repository root
p=types.ModuleType('pulp')
for k in ['LpMaximize','LpProblem','LpStatus','LpVariable','lpSum','value']: setattr(p,k,None)
sys.modules['pulp']=p
spec=importlib.util.spec_from_file_location('norm',SRC/'src/normalization_comparison.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
inp=m.load_input_data(SRC/'data/pww_sdm_input_data.xlsx')
N=22; A=m.PADDOCK_ALTS; costs=inp['costs'][:,A]; BUDGETS=[500_000,1_000_000,2_000_000,5_000_000,10_000_000,20_000_000,40_000_000,60_000_000]

def solve(scores,budget,weights,fix9=False):
 n,a=costs.shape
 obj=sum(w*scores[k] for k,w in weights.items()).flatten()
 mat=lil_matrix((n+1+(1 if fix9 else 0),n*a))
 for i in range(n):mat[i,i*a:(i+1)*a]=1
 mat[n,:]=costs.flatten()
 low=np.r_[np.ones(n),-np.inf];high=np.r_[np.ones(n),budget]
 if fix9:
  # Force P9 alternative 7, whose index in A is 6.
  j=A.index(6);mat[n+1,8*a+j]=1
  low=np.r_[low,1];high=np.r_[high,1]
 res=milp(-obj,integrality=np.ones(n*a),bounds=Bounds(0,1),constraints=LinearConstraint(mat.tocsr(),low,high),options={'time_limit':20,'mip_rel_gap':1e-7})
 if res.x is None:return None
 ch=res.x.reshape(n,a).argmax(axis=1)
 return ch,float(costs[np.arange(n),ch].sum()),float(-res.fun),float(getattr(res,'mip_gap',np.nan))

def prepare(alpha,road):
 fire=m.apply_roadside(inp['fire_prob'],road)
 action=m.compute_action_effectiveness(inp['fire_prob_baseline'],fire)[:,A]
 base=m.normalize_within_unit(action)
 te=base.copy();te[inp['te_count']==0,:]=0
 habitat=base.copy()
 scores={'te':te,'habitat':habitat}
 mult={}
 for k,vals in [('te',inp['te_count']),('habitat',inp['native_cover'])]:
  mx=vals.max();f=np.where(vals>0,(vals/mx)**alpha,0)
  scores[k]=scores[k]*f[:,None]
  # Match aggregate feasible score swings to the alpha=0, all-22 reference.
  ref=np.ptp(te if k=='te' else habitat,axis=1).sum()
  swing=np.ptp(scores[k],axis=1).sum()
  mult[k]=ref/swing if swing else 1
  scores[k]*=mult[k]
 for k,raw in [('rancher',inp['rancher_raw']),('hunter',inp['hunter_raw']),('recreationist',inp['community_raw'])]:
  scores[k]=m.normalize_global_linear(raw[:,A])
 return scores,action,mult

rows=[];scenarios=m.build_scenarios()
for alpha in (0,.5,1):
 for fixed in (False,True):
  for scen,s in scenarios.items():
   for b in BUDGETS:
    best=None
    for road in (False,True):
     scores,action,mult=prepare(alpha,road)
     available=b-(m.ROADSIDE_COST if road else 0)
     if available<0:continue
     ans=solve(scores,available,m.effective_weights(s),fixed)
     if ans is None:continue
     ch,cost,objective,gap=ans
     if best is None or objective>best[0]+1e-8:best=(objective,road,ch,cost,gap,action,mult,scores)
    if best is None:
     rows.append({'alpha':alpha,'p9_fixed':fixed,'scenario':s['label'],'budget_M':b/1e6,'status':'infeasible'})
     continue
    obj,road,ch,cost,gap,action,mult,scores=best
    aidx=np.asarray(A)[ch];alt=aidx+1
    r={'alpha':alpha,'p9_fixed':fixed,'scenario':s['label'],'budget_M':b/1e6,'status':'optimal','cost_M':(cost+(m.ROADSIDE_COST if road else 0))/1e6,'roadside':road,'objective':obj,'mip_gap':gap,'p9_alt':int(alt[8]),'p9_cost_M':float(costs[8,ch[8]]/1e6),'n_conservation':int(np.isin(alt,[4,5,6,7]).sum()),'n_grazing':int((alt==3).sum()),'te_index':float((action[np.arange(N),ch]*inp['te_count']).sum()),'habitat_index':float((action[np.arange(N),ch]*inp['native_cover']).sum()),'te_individuals_treated':float(inp['te_count'][np.isin(alt,[4,5,6,7])].sum()),'choices':','.join(map(str,alt))}
    for k in ('rancher','hunter','recreationist'):r[k]=float(scores[k][np.arange(N),ch].sum())
    rows.append(r)
    print(alpha,fixed,s['label'],b/1e6,'P9',r['p9_alt'],'te',round(r['te_index']),flush=True)
df=pd.DataFrame(rows);df.to_csv(ROOT/'p9_budget_portfolios.csv',index=False)
# Pairwise scenario comparisons at common budgets, for each value model and fixed status.
comparisons=[]
for (alpha,fixed,b),z in df[df.status=='optimal'].groupby(['alpha','p9_fixed','budget_M']):
 cp=z[z.scenario=='Conservation priority']
 if cp.empty:continue
 cp=cp.iloc[0]
 for label in ('Rancher-conservation','Hunter-recreationist','Community priority'):
  ss=z[z.scenario==label]
  if ss.empty:continue
  ss=ss.iloc[0]
  comparisons.append({'alpha':alpha,'p9_fixed':fixed,'budget_M':b,'comparison':label+' vs Conservation priority','te_index_change':ss.te_index-cp.te_index,'rancher_change':ss.rancher-cp.rancher,'hunter_change':ss.hunter-cp.hunter,'habitat_index_change':ss.habitat_index-cp.habitat_index,'cost_change_M':ss.cost_M-cp.cost_M,'p9_alt_cp':cp.p9_alt,'p9_alt_comparison':ss.p9_alt})
com=pd.DataFrame(comparisons);com.to_csv(ROOT/'p9_budget_headline_comparisons.csv',index=False)
print('\nDONE',len(df),'rows',len(com),'comparisons')
print('\nP9 alternatives free:')
print(df[(~df.p9_fixed)&(df.status=='optimal')].groupby(['alpha','budget_M','p9_alt']).size().to_string())
print('\n$20m conservation priority:')
print(df[(df.scenario=='Conservation priority')&(df.budget_M==20)][['alpha','p9_fixed','p9_alt','cost_M','te_index','habitat_index','rancher','n_conservation']].to_string(index=False))
