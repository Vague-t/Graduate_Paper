"""Read native gold only after score and output freezes; preserve every document."""
from pathlib import Path
import json,hashlib,sys,math
from collections import defaultdict,Counter
R=Path(__file__).resolve().parent;W=R.parent;O=R/'casimedicos'
sys.path.insert(0,str(W/'research_0920/vendor'));import numpy as np
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):
 with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
def counts(pred,gold):return [len(pred&gold),len(pred-gold),len(gold-pred)]
def metric(c):
 t,p,n=c;return {'tp':t,'fp':p,'fn':n,'precision':100*t/(t+p) if t+p else 0.,'recall':100*t/(t+n) if t+n else 0.,'f1':200*t/(2*t+p+n) if 2*t+p+n else 0.}
def ckey(c):return c['start'],c['end'],c['type']
def keys(d,state):
 C={ckey(d['components'][c]) for c in state['C']};E={(tuple(sorted(ckey(d['components'][c]) for c in d['relations'][r]['sources'])),ckey(d['components'][d['relations'][r]['target']]),d['relations'][r]['type']) for r in state['R']};return C,E
def main():
 out=O/'results'
 for p,h in read(out/'input_freeze.json')['hashes'].items():assert sha(W/p)==h
 for p,h in read(out/'output_freeze.json')['hashes'].items():assert sha(out/p)==h
 docs={d['id']:d for d in read(O/'candidate_pools.json')['documents']}
 gold={d['id']:d for d in read(W/'research_1011_v11/candidate/evaluation/source_gold.json')['documents'] if d['id'] in docs}
 assert set(gold)==set(docs)
 G={}
 for id,g in gold.items():
  C=[(c['char_start'],c['char_end'],c['type']) for c in g['components']]
  G[id]=(set(C),{(tuple(sorted(C[i] for i in r['sources'])),C[r['target']],r['type']) for r in g['relations']})
 old={d['id']:d for d in read(W/'research_1011_v10/new_corpora/candidate_pools.json')['documents']};oldinit=read(W/'research_1011_v10/new_corpora/results/run_001/common_initial_states.json')
 rows=[];agg=defaultdict(lambda: {'C':[0,0,0],'R':[0,0,0],'documents':0,'recovered_R':0,'lost_R':0,'added_FP_R':0,'removed_FP_R':0,'improved_docs':0,'worse_docs':0,'equal_docs':0})
 initial={};hist={}
 for id in docs:
  g=oldinit[id]['graph'];state={'C':g['components'],'R':g['relations']} if g and g['structurally_valid'] else {'C':[],'R':[]};hist[id]=keys(old[id],state)
  rows.append({'id':id,'mode':'historical_v10_initial','threshold':None,'C':counts(hist[id][0],G[id][0]),'R':counts(hist[id][1],G[id][1]),'historical_parse_failure':not bool(g and g['structurally_valid'])})
 for entry in read(out/'summary.json'):
  z=read(out/entry['file']);id=z['id'];cs,es=keys(docs[id],z['final']);gc,gr=G[id]
  if entry['mode']=='component-then-relation initialization':initial[id,entry['threshold']]=(cs,es)
  rows.append({'id':id,'mode':entry['mode'],'threshold':entry['threshold'],'C':counts(cs,gc),'R':counts(es,gr),'recovered_R':len((es-hist[id][1])&gr),'lost_R':len((hist[id][1]-es)&gr),'added_FP_R':len((es-hist[id][1])-gr),'removed_FP_R':len((hist[id][1]-es)-gr),'output_component_keys':sorted(cs),'output_relation_keys':sorted(es),'solver_seconds':z.get('solver_seconds',0),'wall_seconds':z.get('wall_seconds'),'file':entry['file']})
 for row in rows:
  a=agg[row['mode'],row['threshold']];a['documents']+=1
  for axis in ['C','R']:a[axis]=[x+y for x,y in zip(a[axis],row[axis])]
  for k in ['recovered_R','lost_R','added_FP_R','removed_FP_R']:a[k]+=row.get(k,0)
  now=metric(row['R'])['f1'];oldf=metric(counts(hist[row['id']][1],G[row['id']][1]))['f1'];a['improved_docs' if now>oldf else 'worse_docs' if now<oldf else 'equal_docs']+=1
  if row['threshold'] is not None:
   base=initial[row['id'],row['threshold']][1];es={ (tuple(tuple(c) for c in x[0]),tuple(x[1]),x[2]) for x in row['output_relation_keys']};gr=G[row['id']][1]
   row['incremental_recovered_R']=len((es-base)&gr);row['incremental_lost_R']=len((base-es)&gr)
 summaries=[{'mode':m,'threshold':t,**a,'C':metric(a['C']),'R':metric(a['R'])} for (m,t),a in agg.items()]
 scores=read(O/'validated_scores.json');score_audit=[]
 for axis in ['C','R']:
  p=[];y=[]
  for id,d in docs.items():
   for ident,v in scores[id][axis].items():
    state={'C':[ident] if axis=='C' else [],'R':[ident] if axis=='R' else []};obj=next(iter(keys(d,state)[axis=='R']));p.append(v);y.append(int(obj in G[id][axis=='R']))
  p=np.array(p);y=np.array(y);n=len(y);rank=np.empty(n,float);order=np.argsort(p);start=0
  while start<n:
   end=start+1
   while end<n and p[order[end]]==p[order[start]]:end+=1
   rank[order[start:end]]=(start+1+end)/2;start=end
  pos=int(y.sum());neg=n-pos;auc=(rank[y==1].sum()-pos*(pos+1)/2)/(pos*neg) if pos and neg else None
  ece=sum(np.mean((p>=a)&(p<(a+.1) if a<.9 else p<=1))*abs(p[(p>=a)&(p<(a+.1) if a<.9 else p<=1)].mean()-y[(p>=a)&(p<(a+.1) if a<.9 else p<=1)].mean()) for a in np.arange(0,1,.1) if np.any((p>=a)&(p<(a+.1) if a<.9 else p<=1)))
  score_audit.append({'object':axis,'n':n,'positive':pos,'AUROC':float(auc) if auc is not None else None,'Brier':float(np.mean((p-y)**2)),'ECE10':float(ece),'mean_score_positive':float(p[y==1].mean()) if pos else None,'mean_score_negative':float(p[y==0].mean()),'positives_ge_05':int(((p>=.5)&(y==1)).sum()),'positives_gt_05':int(((p>.5)&(y==1)).sum()),'negatives_gt_05':int(((p>.5)&(y==0)).sum()),'calibrated':False})
 result={'identity':'V12-CASI-EXPLORATORY-FIXED8','summary':summaries,'score_audit':score_audit,'rows':rows,'gold_C':sum(len(g[0]) for g in G.values()),'gold_R':sum(len(g[1]) for g in G.values()),'new_model_scoring_tasks':11,'solver_records':64,'selection':'fixed reused diagnostic sample; thresholds fixed before scores; no test-based choice','not_done':['Qwen training','independent held-out sample','calibration fitting','full-pipeline attribution to a single module']}
 write(O/'evaluation/metrics.json',result);print(json.dumps({'summary':summaries,'score_audit':score_audit},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
