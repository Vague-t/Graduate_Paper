"""Validate explicit scores and execute the fixed CasiMedicos diagnostic."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,math,time,itertools
R=Path(__file__).resolve().parent;W=R.parent;O=R/'casimedicos'
sys.path.insert(0,str(W/'research_1011_v11'));import solver_compare as solve
repair=solve.repair;core=sys.modules['graph_core']
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):
 p.parent.mkdir(exist_ok=True,parents=True)
 with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
def component_initial(d,q):
 """Exact weighted interval scheduling, deterministic objective/edit/lex ties."""
 order=sorted(d['components'],key=lambda c:(d['components'][c]['end'],d['components'][c]['start'],c));dp=[(0.,())]
 def best(a,b):return min([a,b],key=lambda x:(-round(x[0],12),len(x[1]),x[1]))
 for i,c in enumerate(order):
  prev=max([-1]+[j for j in range(i) if d['components'][order[j]]['end']<=d['components'][c]['start']])+1
  val,seq=dp[prev];dp.append(best(dp[-1],(val+2*q['C'][c]-1,tuple(sorted((*seq,c))))))
 C=set(dp[-1][1]);slots={}
 for r,obj in d['relations'].items():
  if core.relation_legal(d,obj,C):slots.setdefault(core.slot(obj),[]).append(r)
 E={min(rr,key=lambda r:(-q['R'][r],r)) for rr in slots.values()}
 E={r for r in E if q['R'][r]>.5}
 assert not core.legal(d,C,E)
 return {'candidate_id':'score_component_then_relation','components':sorted(C),'relations':sorted(E),'structurally_valid':True}
def main():
 protocol=read(O/'protocol.json')
 for p,h in protocol['hashes'].items():assert sha(W/p)==h
 docs=read(O/'candidate_pools.json')['documents'];qs={d['id']:{'C':{},'R':{}} for d in docs};rawpaths=[]
 for name in protocol['batches']:
  ip=O/'inputs'/f'{name}.json';p=O/'raw_scores'/f'{name}.json';b=read(ip);s=read(p);rawpaths.append(p)
  assert s['id']==b['id'] and s['batch']==b['batch'] and s['model_requested']=='gpt-5.6-luna'
  assert set(s['component_scores'])==(set(b['components']) if b['score_components'] else set())
  assert [x[0] for x in s['slot_scores']]==[x['id'] for x in b['slots']]
  assert all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in s['component_scores'].values())
  q=qs[b['id']];q['C'].update(s['component_scores'])
  for slot,score in zip(b['slots'],s['slot_scores']):
   assert len(score)==3 and all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in score[1:]) and sum(score[1:])<=1+1e-9
   for lab,v in zip(['Attack','Support'],score[1:]):q['R'][slot['relation_ids'][lab]]=v
 for d in docs:assert set(qs[d['id']]['C'])==set(d['components']) and set(qs[d['id']]['R'])==set(d['relations'])
 write(O/'validated_scores.json',qs)
 out=O/'results';out.mkdir(exist_ok=False)
 write(out/'input_freeze.json',{'at':datetime.now(timezone.utc).isoformat(),'gold_read':False,'hashes':{str(p.relative_to(W)):sha(p) for p in rawpaths+[O/'validated_scores.json',O/'protocol.json',O/'candidate_pools.json',Path(__file__),W/'research_1011_v11/solver_compare.py',W/'research_1011_v10/cdcp_scoring/repair.py']}})
 oldinit,oldqueues=repair.initial,repair.queues;summary=[]
 for d in docs:
  raw=qs[d['id']]
  for tau in protocol['thresholds']:
   q={a:{k:max(0,min(1,v-(tau-.5))) for k,v in z.items()} for a,z in raw.items()}
   init=component_initial(d,q)
   for mode in protocol['methods']:
    if mode=='component-then-relation initialization':res={'id':d['id'],'mode':mode,'status':'completed','initial':{'C':init['components'],'R':[]},'final':{'C':init['components'],'R':init['relations']},'solver_seconds':0}
    elif mode=='GlobalILP-lite':res=solve.solve_global(d,q,init,5.)
    else:
     def queues(doc,C,which):
      z=oldqueues(doc,C,'BRJ-lite' if which=='SingleObject' else which)
      if which=='SingleObject':z['split']=[];z['merge']=[]
      return z
     repair.initial=lambda _d,_q:(init,[]);repair.queues=queues
     res=repair.run_doc(d,q,mode)
    res['threshold']=tau;res['score_condition']='explicit_dense_native_C';assert not core.legal(d,set(res['final']['C']),set(res['final']['R']))
    name=f'{d["id"]}__{tau:.2f}__{mode.replace(" ","_")}.json';write(out/name,res);summary.append({'file':name,'id':d['id'],'mode':mode,'threshold':tau,'status':res['status']})
  print(d['id'],flush=True)
 repair.initial=oldinit;repair.queues=oldqueues
 write(out/'summary.json',summary)
 write(out/'output_freeze.json',{'at':datetime.now(timezone.utc).isoformat(),'gold_read':False,'hashes':{p.name:sha(p) for p in out.glob('*.json')}})
 print('PASS',len(summary),'runs')
if __name__=='__main__':main()
