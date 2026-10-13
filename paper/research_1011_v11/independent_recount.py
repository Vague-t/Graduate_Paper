"""Second implementation of exact count and candidate checks; imports no evaluator."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parent;W=R.parent
read=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
gold={};pools={}
for family,corpora in [('new_corpora',['argunsc','casimedicos']),('cdcp_scoring',['cdcp'])]:
 root=W/'research_1011_v10'/family
 for corpus in corpora:
  for d in read(root/'evaluation'/f'{corpus}_gold.json')['documents']:
   C=[(c['char_start'],c['char_end'],c['type']) for c in d['components']]
   G={(tuple(sorted(C[i] for i in r['sources'])),C[r['target']],r['type']) for r in d['relations']};gold[d['id']]=(set(C),G)
 for d in read(root/'candidate_pools.json')['documents']:pools[d['id']]=d
def count(pred,g):return {'TP':len(pred&g),'FP':len(pred-g),'FN':len(g-pred)}
def obj(d,ids):
 C={i:(c['start'],c['end'],c['type']) for i,c in d['components'].items()}
 return set(C[i] for i in ids['C']),{(tuple(sorted(C[i] for i in d['relations'][r]['sources'])),C[d['relations'][r]['target']],d['relations'][r]['type']) for r in ids['R']}
metrics=read(R/'solver/evaluation/metrics.json');checked=0
for a in metrics['by_document']:
 path=R/'solver/results/run_001'/f"{a['id']}__{a['condition']}__{a['mode']}__{a['budget']:g}.json"
 x=read(path);g=gold[a['id']];p=obj(pools[a['id']],x['final']);initial=obj(pools[a['id']],x['initial'])
 for k,v,y in [('C',p[0],g[0]),('R',p[1],g[1]),('initial_C',initial[0],g[0]),('initial_R',initial[1],g[1])]:
  c=count(v,y)
  assert all(a[k][kk]==vv for kk,vv in c.items()),(path,k,c,a[k])
 checked+=1
candidate=read(R/'candidate/evaluation/coverage.json');candchecked=0;transitions=[]
for p in sorted((R/'candidate/constructed').glob('*.json')):
 d=read(p)
 if 'layers' not in d:continue
 cg,rg=gold[d['id']];last=None
 for layer in d['layers']:
  C=set(tuple(c) for c in layer['components']);G={(tuple(sorted(tuple(c) for c in r[0])),tuple(r[1]),r[2]) for r in layer['relations']}
  row=next(x for x in candidate['by_document'] if x['id']==d['id'] and x['layer']==layer['layer'])
  assert len(C&cg)==row['C_hit'] and len(G&rg)==row['R_hit']
  if last is not None:transitions.append({'id':d['id'],'to':layer['layer'],'gold_R_added':len((G&rg)-last[1]),'gold_R_lost':len(last[1]-(G&rg))})
  last=(C&cg,G&rg);candchecked+=1
hashchecks=0
for p,base in [(R/'pre_model_freeze.json',R),(R/'solver/results/run_001/input_freeze.json',W),(R/'solver/results/run_001/output_freeze.json',R/'solver/results/run_001'),(R/'candidate/constructed/input_freeze.json',W)]:
 for name,h in read(p)['hashes'].items():assert sha(base/name)==h,(p,name);hashchecks+=1
assert checked==1536 and candchecked==96
out={'status':'PASS','independent_solver_recounts':checked,'independent_candidate_recounts':candchecked,'frozen_hash_checks':hashchecks,'candidate_gold_hit_transitions':transitions,'limitations':'No new model calls or semantic re-adjudication; native source authority comes from separately saved evaluation audit.'}
(R/'independent_recount.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
# Post-run accounting of already completed model tasks, with all unavailable fields explicit.
tasks=[]
for p in sorted((R/'dispatch').glob('*.txt')):
 name=p.stem
 if 'drift_judge' in name:
  m=re.fullmatch(r'v11_drift_judge_(\d+)_(filter|audit)',name);num,role=m.groups();stem='drift_judge_'+num
  inp=R/'drift/judge_inputs'/f'{stem}.json';ins=R/'drift'/f'{role}_instruction.md';output=R/'drift'/f'{role}_outputs'/f'{stem}.json'
  freeze=read(R/'drift/freezes'/f'{stem}.json');assert sha(inp)==freeze['input_sha256'] and sha(ins)==freeze['instruction_hashes'][role]
 else:
  stem=name.removeprefix('v11_');category='candidate_extract' if 'candidate_extract' in name else 'drift_generate';inp=R/category/'inputs'/f'{stem}.json';ins=R/category/'instruction.md';output=R/category/'raw'/f'{stem}.json'
 assert output.is_file(),output
 tasks.append({'task':name,'model_requested':'gpt-5.6-luna','reasoning_effort_requested':'low','context':'fresh fork none','dispatch_sha256':sha(p),'input':str(inp.relative_to(R)),'input_sha256':sha(inp),'instruction':str(ins.relative_to(R)),'instruction_sha256':sha(ins),'output':str(output.relative_to(R)),'output_sha256':sha(output),'snapshot':None,'temperature':None,'api_tokens':None,'unavailable_reason':'not exposed by task interface'})
assert len(tasks)==30
(R/'model_execution_manifest.json').write_text(json.dumps({'kind':'POST_RUN_ACCOUNTING','tasks':tasks,'count':len(tasks),'training_runs':0},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='candidate_gold_hit_transitions'},ensure_ascii=False));print('model task accounting:',len(tasks))
