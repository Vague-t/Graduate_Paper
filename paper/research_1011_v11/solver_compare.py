"""Real, gold-free comparisons on frozen v10 candidate universes and scores."""
from pathlib import Path
import sys,json,time,itertools,hashlib,platform,warnings
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
sys.path.insert(0,str(WORK/'research_1011_v10/cdcp_scoring'))
import repair
from graph_core import ck,overlap,slot,legal,sha
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
TOL=1e-8
def read(p):return json.loads(Path(p).read_text())
def write(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
def constraint_system(doc,q,initial,strict=True):
 C0=set(initial['components']);R0=set(initial['relations']);cs=doc['components'];rs=doc['relations']
 C=sorted(cs);R=sorted(rs);names=[('C',x) for x in C]+[('R',x) for x in R];idx={x:i for i,x in enumerate(names)};n=len(names)
 rows=[];lo=[];hi=[]
 def add(row,l=-np.inf,u=np.inf):rows.append(row);lo.append(l);hi.append(u)
 for a,b in itertools.combinations(C,2):
  if overlap(cs[a],cs[b]):add({idx['C',a]:1,idx['C',b]:1},u=1)
 slots={}
 for r in R:
  obj=rs[r];ri=idx['R',r]
  for c in set(obj['sources'])|{obj['target']}:add({ri:1,idx['C',c]:-1},u=0)
  slots.setdefault(slot(obj),[]).append(ri)
  if doc['corpus']=='cdcp' and len(obj['sources'])>1:
   src=set(obj['sources']);left=min(ck(cs[c]) for c in src);right=max(ck(cs[c]) for c in src)
   for c in C:
    if c not in src and left<ck(cs[c])<right:add({ri:1,idx['C',c]:1},u=1)
 for values in slots.values():add({i:1 for i in values},u=1)
 a=np.array([2*q[axis][ident]-1 for axis,ident in names]);ac={idx['C',c]:2*q['C'][c]-1 for c in C};ar={idx['R',r]:2*q['R'][r]-1 for r in R}
 pc,pr=repair.phi(C0,R0,q)
 ec={idx['C',c]:(-1 if c in C0 else 1) for c in C};er={idx['R',r]:(-1 if r in R0 else 1) for r in R}
 add(ec,u=24-len(C0));add(er,u=96-len(R0));add(ac,l=pc-TOL);add(ar,l=pr-TOL)
 if strict:add({i:float(x) for i,x in enumerate(a)},l=pc+pr+.010001)
 return names,a,rows,lo,hi,np.array([ec.get(i,0)+er.get(i,0) for i in range(n)])
def solve_global(doc,q,initial,budget):
 start=time.perf_counter();C0=set(initial['components']);R0=set(initial['relations'])
 result={'id':doc['id'],'corpus':doc['corpus'],'mode':'GlobalILP-lite','budget_seconds':budget,'initial':{'C':sorted(C0),'R':sorted(R0)},'final':{'C':sorted(C0),'R':sorted(R0)},'status':'completed','scope':'same finite universe, objective, legality, nondecrease gates; net edit bound, not cumulative path bound','solver_calls':[],'tie_status':'not_started'}
 names,a,rows,lo,hi,edit=constraint_system(doc,q,initial);n=len(names);result['construction_seconds']=time.perf_counter()-start;used=0.
 def call(c,stage):
  nonlocal used
  remaining=budget-used
  if remaining<=1e-5:return None
  rr=[];cc=[];vv=[]
  for i,row in enumerate(rows):
   for j,v in row.items():
    if v:rr.append(i);cc.append(j);vv.append(v)
  matrix=coo_matrix((vv,(rr,cc)),shape=(len(rows),n)).tocsc()
  st=time.perf_counter()
  with warnings.catch_warnings(record=True) as ws:
   warnings.simplefilter('always')
   z=milp(c,integrality=np.ones(n),bounds=Bounds(np.zeros(n),np.ones(n)),constraints=LinearConstraint(matrix,np.array(lo),np.array(hi)),options={'time_limit':remaining,'mip_rel_gap':0.,'threads':1})
  dt=time.perf_counter()-st;used+=dt
  def finite(k):
   v=getattr(z,k,None);return float(v) if v is not None and np.isfinite(v) else None
  rec={'stage':stage,'status':int(z.status),'message':str(z.message),'seconds':dt,'time_limit':remaining,'objective':finite('fun'),'minimization_dual_bound':finite('mip_dual_bound'),'gap':finite('mip_gap'),'nodes':finite('mip_node_count'),'has_incumbent':z.x is not None,'warnings':[str(x.message) for x in ws]};result['solver_calls'].append(rec)
  x=None
  if z.x is not None and np.all(np.isfinite(z.x)) and np.max(abs(z.x-np.rint(z.x)))<1e-5:
   xx=np.rint(z.x).astype(int);val=matrix@xx
   if np.all(val>=np.array(lo)-TOL) and np.all(val<=np.array(hi)+TOL):x=xx
  return x,int(z.status),rec
 if n==0:result['stop_reason']='empty_universe'
 else:
  primary=call(-a,'maximize_phi');best=primary[0] if primary else None
  result['primary_optimal']=bool(primary and primary[1]==0)
  if primary and primary[2]['minimization_dual_bound'] is not None:result['total_phi_upper_bound']=-primary[2]['minimization_dual_bound']
  if best is not None and result['primary_optimal']:
   optimum=float(a@best);rows.append({i:float(v) for i,v in enumerate(a)});lo.append(optimum-TOL);hi.append(optimum+TOL)
   secondary=call(edit,'minimize_net_edits');result['tie_status']='primary_optimal_secondary_incomplete'
   if secondary and secondary[0] is not None:
    best=secondary[0]
    if secondary[1]==0:result['tie_status']='primary_and_min_edits_optimal_lex_not_solved'
  elif best is not None:result['tie_status']='primary_incumbent'
  if best is not None:
   C={ident for (axis,ident),x in zip(names,best) if axis=='C' and x};R={ident for (axis,ident),x in zip(names,best) if axis=='R' and x}
   pc,pr=repair.phi(C0,R0,q);nc,nr=repair.phi(C,R,q)
   assert not legal(doc,C,R) and len(C^C0)<=24 and len(R^R0)<=96
   assert nc>=pc-TOL and nr>=pr-TOL and nc+nr>pc+pr+.01+TOL
   result['final']={'C':sorted(C),'R':sorted(R)};result['stop_reason']='accepted_global_solution';result['accepted']=True
  else:result['stop_reason']='no_eligible_improvement' if primary and primary[1]==2 else 'no_valid_incumbent';result['accepted']=False
 result['solver_seconds']=used;result['wall_seconds']=time.perf_counter()-start
 result['component_edits_net']=len(set(result['final']['C'])^C0);result['relation_edits_net']=len(set(result['final']['R'])^R0)
 result['phi_initial']=repair.phi(C0,R0,q);result['phi_final']=repair.phi(set(result['final']['C']),set(result['final']['R']),q)
 return result
def sparse_q(root,d):
 x=read(root/'scores'/f"{d['id']}.json");assert x['default_relation_score']==.05
 return {'C':x['component_scores'],'R':{r:x['relation_score_overrides'].get(r,.05) for r in d['relations']}}
def main():
 out=ROOT/'solver/results/run_001';out.mkdir(parents=True,exist_ok=False)
 original_solver=repair.Solver;original_queues=repair.queues;original_initial=repair.initial
 frozen=[];sources=[]
 for family in ['new_corpora','cdcp_scoring']:
  root=WORK/'research_1011_v10'/family;docs=read(root/'candidate_pools.json')['documents'];common=read(root/'results/run_001/common_initial_states.json')
  frozen+=[root/'candidate_pools.json',root/'results/run_001/common_initial_states.json'];frozen+=list((root/'scores').glob('*.json'))+list((root/'scores_dense').glob('*.json'))
  for d in docs:
   conditions=['sparse','dense_native'] if family=='cdcp_scoring' else ['sparse']
   for cond in conditions:
    if cond=='sparse':q=sparse_q(root,d)
    else:
     x=read(root/'scores_dense'/f"{d['id']}.json");q={'C':x['component_scores'],'R':x['relation_scores']};assert all(v is not None for m in q.values() for v in m.values())
    sources.append((family,d,cond,q,common[d['id']]))
 write(out/'input_freeze.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'code_sha256':sha(__file__),'gold_read':False,'hashes':{str(p.relative_to(WORK)):sha(p) for p in frozen},'python':sys.version,'numpy':np.__version__,'scipy':repair.scipy.__version__,'platform':platform.platform()})
 rows=[]
 for family,d,cond,q,init in sources:
  for budget in [.25,1.,5.]:
   for mode in ['RelationOnly','SingleObject','BRJ-lite','GlobalILP-lite']:
    g=init['graph'];st=time.perf_counter()
    if g is None or not g['structurally_valid']:res={'id':d['id'],'corpus':d['corpus'],'status':'initial_failure','mode':mode,'final':{'C':[],'R':[]},'initial':{'C':[],'R':[]}}
    elif mode=='GlobalILP-lite':res=solve_global(d,q,g,budget)
    else:
     class LimitedSolver(original_solver):
      def __init__(self,_seconds):super().__init__(budget)
     def queues(doc,C,which):
      z=original_queues(doc,C,'BRJ-lite' if which=='SingleObject' else which)
      if which=='SingleObject':z['split']=[];z['merge']=[]
      return z
     repair.Solver=LimitedSolver;repair.queues=queues;repair.initial=lambda _d,_q:(g,init['ranks'])
     res=repair.run_doc(d,q,mode)
    res.update(score_condition=cond,budget_seconds=budget,source_family=family,total_run_wall_seconds=time.perf_counter()-st)
    name=f"{d['id']}__{cond}__{mode}__{budget:g}.json";write(out/name,res)
    row={k:res.get(k) for k in ['id','corpus','score_condition','budget_seconds','mode','status','solver_seconds','total_run_wall_seconds','stop_reason','primary_optimal','tie_status']};rows.append(row)
   print(json.dumps({'id':d['id'],'condition':cond,'budget':budget,'done':len(rows)}),flush=True)
 repair.Solver=original_solver;repair.queues=original_queues;repair.initial=original_initial
 write(out/'summary.json',{'runs':rows,'count':len(rows)})
 write(out/'output_freeze.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'gold_read':False,'hashes':{p.name:sha(p) for p in out.glob('*.json')}})
if __name__=='__main__':main()
