"""Evaluate frozen real solver runs and independently audit feasible outputs."""
from pathlib import Path
from collections import defaultdict,Counter
import importlib.util,json,statistics,hashlib,sys
R=Path(__file__).resolve().parent;W=R.parent
sp=importlib.util.spec_from_file_location('v10eval',W/'research_1011_v10/evaluate.py');ev=importlib.util.module_from_spec(sp);sp.loader.exec_module(ev)
read=ev.read;sha=ev.sha
def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def percentile(xs,q):
 xs=sorted(xs)
 if not xs:return None
 at=(len(xs)-1)*q;i=int(at);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(at-i)
def main():
 run=R/'solver/results/run_001'
 for p,h in read(run/'input_freeze.json')['hashes'].items():assert sha(W/p)==h
 for p,h in read(run/'output_freeze.json')['hashes'].items():assert sha(run/p)==h
 pools={};gold={};roots={};native=[]
 for family in ['new_corpora','cdcp_scoring']:
  root=W/'research_1011_v10'/family
  for d in read(root/'candidate_pools.json')['documents']:pools[d['id']]=d;roots[d['id']]=root
  for p in (root/'evaluation').glob('*_gold.json'):
   for g in read(p)['documents']:gold[g['id']]=g;native.append(ev.independent_native(g))
 rows=[];audits=[];group=defaultdict(list);results={}
 for meta in read(run/'summary.json')['runs']:
  ident=meta['id'];cond=meta['score_condition'];mode=meta['mode'];budget=meta['budget_seconds'];d=pools[ident];g=gold[ident]
  res=read(run/f'{ident}__{cond}__{mode}__{budget:g}.json');q,_=ev.qload(roots[ident],d,cond);GC,GR=ev.gold_keys(g)
  if res['status']=='completed':
   if mode!='GlobalILP-lite':
    au=ev.old.audit_trace(d,res,q)
    if mode=='SingleObject':assert all(len(x['proposal']['D'])<=1 and len(x['proposal']['B'])<=1 for x in res['attempts'])
   else:
    C=set(res['final']['C']);E=set(res['final']['R']);C0=set(res['initial']['C']);E0=set(res['initial']['R']);ev.old.valid(d,C,E)
    def util(v,axis):return sum(2*q[axis][x]-1 for x in sorted(v))
    dc=util(C,'C')-util(C0,'C');dr=util(E,'R')-util(E0,'R')
    assert len(C^C0)<=24 and len(E^E0)<=96 and dc>=-1e-8 and dr>=-1e-8
    if res.get('accepted'):assert dc+dr>.01+1e-8
    else:assert C==C0 and E==E0
    assert abs(sum(res['phi_final'])-util(C,'C')-util(E,'R'))<1e-6
    au={'id':ident,'mode':mode,'status':'PASS_GLOBAL_FEASIBILITY','delta_C':dc,'delta_R':dr,'net_edits_C':len(C^C0),'net_edits_R':len(E^E0)}
  else:
   assert res['status']=='initial_failure' and not res['final']['C'] and not res['final']['R'];au={'id':ident,'mode':mode,'status':'PASS_FAILURE_RETAINED'}
  au.update(condition=cond,budget=budget);audits.append(au)
  C,E=ev.object_sets(d,res['final']);C0,E0=ev.object_sets(d,res['initial'])
  row={'id':ident,'corpus':d['corpus'],'condition':cond,'mode':mode,'budget':budget,'status':res['status'],'C':ev.stats(C,GC),'R':ev.stats(E,GR),'initial_C':ev.stats(C0,GC),'initial_R':ev.stats(E0,GR),'changes_C':ev.changes(C0,C,GC),'changes_R':ev.changes(E0,E,GR),'solver_seconds':res.get('solver_seconds',0.),'wall_seconds':res['total_run_wall_seconds'],'construction_seconds':res.get('construction_seconds',None),'commits':len(res.get('accepted_attempts',[])) if mode!='GlobalILP-lite' else int(res.get('accepted',False)),'primary_optimal':res.get('primary_optimal'),'tie_status':res.get('tie_status'),'solver_statuses':dict(Counter(str(c['status']) for c in res.get('solver_calls',[])))}
  rows.append(row);group[(d['corpus'],cond,budget,mode)].append(row);results[(ident,cond,budget,mode)]=res
 # Any certified global optimum must bound all local feasible terminal utilities.
 bounds=0
 for (ident,cond,budget,mode),res in results.items():
  if mode!='GlobalILP-lite' or res['status']!='completed' or not res.get('primary_optimal'):continue
  for local in ['RelationOnly','SingleObject','BRJ-lite']:
   x=results[ident,cond,budget,local]
   assert sum(x['phi_final'])<=sum(res['phi_final'])+1e-5,(ident,cond,budget,local)
   bounds+=1
 aggregates=[]
 for key,rs in sorted(group.items()):
  corpus,cond,budget,mode=key;obj={'corpus':corpus,'condition':cond,'budget':budget,'mode':mode,'documents':len(rs),'failures':sum(x['status']!='completed' for x in rs)}
  for axis in ['C','R','initial_C','initial_R']:
   z={k:sum(x[axis][k] for x in rs) for k in ['TP','FP','FN']};obj[axis]=ev.from_counts(z['TP'],z['FP'],z['FN'])
  for axis in ['changes_C','changes_R']:obj[axis]={k:sum(x[axis][k] for x in rs) for k in rs[0][axis]}
  for cost in ['solver_seconds','wall_seconds']:obj[cost]={'total':sum(x[cost] for x in rs),'mean':statistics.mean(x[cost] for x in rs),'P95':percentile([x[cost] for x in rs],.95),'max':max(x[cost] for x in rs)}
  obj['relation_outcomes']=dict(Counter('improved' if x['R']['F1']>x['initial_R']['F1'] else ('harmed' if x['R']['F1']<x['initial_R']['F1'] else 'unchanged') for x in rs))
  obj['global_primary_optimal']=sum(x['primary_optimal'] is True for x in rs);aggregates.append(obj)
 out=R/'solver/evaluation';out.mkdir(exist_ok=False)
 write(out/'metrics.json',{'runs':len(rows),'unique_documents':len(gold),'aggregates':aggregates,'by_document':rows})
 write(out/'audit.json',{'status':'PASS','native_sources':native,'traces':audits,'global_upper_bound_checks':bounds,'solver_output_freeze_sha256':sha(run/'output_freeze.json')})
 print(json.dumps([{'corpus':a['corpus'],'score':a['condition'],'mode':a['mode'],'budget':a['budget'],'C_F1':round(a['C']['F1']*100,2),'R_F1':round(a['R']['F1']*100,2),'time_ms':round(a['wall_seconds']['mean']*1000,2)} for a in aggregates if a['budget']==5],indent=2))
if __name__=='__main__':main()
