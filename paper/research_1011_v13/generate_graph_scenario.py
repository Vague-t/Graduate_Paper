"""Gold-informed authoring scenarios on actual native graphs, NOT model inference.

Method names label assumed output distributions. No training/repair execution is
claimed for these targets. All counts derive from concrete endpoint-linked graphs.
"""
from common import *
import csv,math,heapq,itertools,time
OUT=ROOT/'simulation'
SEEDS=[17,29,43]
old=read(WORK/'_revision_1011_v12/simulation/results.json')
TARGETS=old['assumed_targets']['strict_native'];LABELS=old['labels']
LABELS={k:v.replace('ICIC继承配置','ICIC继承参照情景') for k,v in LABELS.items()}
FOUR=['t0_i0','t1_i0','t0_i1','t1_i1']

def numbers(N,target):
 f=target/100.;t=int(round(N*(f-.012)))
 p=max(0,int(round(2*t/f-t-N)))
 return t,p

def effect_key(method):
 if method in ['br_c','relation_only']:return 'mcr_t1'
 return method

def method_noise(seed,method,doc,c,axis):
 if method=='t0_i0':return 0.
 if method=='t1_i0':return .035*(uniform('train',seed,doc,c,axis)-.5)
 if method=='t0_i1':return .035*(uniform('repair',seed,doc,c,axis)-.5)
 if method=='t1_i1':return .0175*(uniform('train',seed,doc,c,axis)+uniform('repair',seed,doc,c,axis)-1)
 scale=.17 if method=='no_risk_guard' else .035
 return scale*(uniform('method',seed,method,doc,c,axis)-.5)

def false_relations(d,C,true_ids,seed,method):
 """Bounded enumerated false proposals on the chosen spans; all gold use explicit."""
 cs=d['components'];order=sorted(C,key=lambda c:ckey(cs[c]));labs=['supports','attacks'] if d['corpus']=='AAEC' else ['reason','evidence']
 used={(tuple(d['relations'][r]['sources']),d['relations'][r]['target']) for r in true_ids}
 gold=set(d['gold_R']);n=len(order);rows=[]
 max_k=1 if d['corpus']=='AAEC' else 3
 for k in range(1,max_k+1):
  for a in range(n-k+1):
   src=order[a:a+k]
   for t in order:
    if t in src or (tuple(src),t) in used:continue
    raw={'sources':src,'target':t,'type':labs[int(uniform('label',seed,d['id'],*src,t)*2)]}
    ident=rid(raw)
    if ident in gold:
     raw={**raw,'type':labs[1-labs.index(raw['type'])]};ident=rid(raw)
    assert ident not in gold
    base=uniform('FP-R',seed,d['id'],ident)
    key=base+method_noise(seed,method,d['id'],ident,'R-FP')
    rows.append((key,ident,raw))
 # Longer native groups may appear among false labels too.
 for gr in d['gold_R']:
  r=d['relations'][gr]
  if len(r['sources'])<=3:continue
  source=[]
  for c in r['sources']:
   ix=cs[c]['origin_index'];matches=[x for x in C if cs[x]['origin_index']==ix]
   if not matches:break
   source.append(matches[0])
  target=[x for x in C if cs[x]['origin_index']==cs[r['target']]['origin_index']]
  if len(source)!=len(r['sources']) or not target or (tuple(source),target[0]) in used:continue
  raw={'sources':source,'target':target[0],'type':labs[1-labs.index(r['type'])]};ident=rid(raw)
  rows.append((uniform('FP-R',seed,d['id'],ident)+method_noise(seed,method,d['id'],ident,'R-FP'),ident,raw))
 # Keep enough low-ranked proposals per document for all global FP targets.
 return heapq.nsmallest(max(12,4*len(d['gold_R'])),rows,key=lambda x:(x[0],x[1]))

def main():
 OUT.mkdir(parents=True,exist_ok=True);all_docs=load_jsonl(ROOT/'data/native_documents.jsonl')
 graphs=[];raw_counts=[];arr={};sets={};metrics={};paired={};interactions={};risk={};members=[];strata=[];target_checks=[]
 t0=time.perf_counter()
 for di,corpus in enumerate(['AAEC','CDCP']):
  docs=[d for d in all_docs if d['corpus']==corpus];byid={d['id']:d for d in docs};nd=len(docs)
  nc=sum(len(d['gold_C']) for d in docs);nr=sum(len(d['gold_R']) for d in docs)
  for si,seed in enumerate(SEEDS):
   jitter=[-.35,.02,.33][si]
   chosenC_cache={}
   for method,targets in TARGETS.items():
    cm=effect_key(method);cf=TARGETS[cm][di*2]+jitter;rf=targets[di*2+1]+jitter
    tC,pC=numbers(nc,cf);tR,pR=numbers(nr,rf)
    if cm in chosenC_cache:chosenC={k:set(v) for k,v in chosenC_cache[cm].items()}
    else:
     cranks=[]
     for d in docs:
      degree={c:0 for c in d['gold_C']}
      for r in d['gold_R']:
       for c in set(d['relations'][r]['sources'])|{d['relations'][r]['target']}:degree[c]+=1
      for c in d['gold_C']:
       rank=uniform('C-base',seed,d['id'],c)-.16*min(degree[c],6)+method_noise(seed,cm,d['id'],c,'C')
       cranks.append((rank,d['id'],c))
     cranks.sort();selected={(doc,c) for _,doc,c in cranks[:tC]};chosenC={d['id']:{c for c in d['gold_C'] if (d['id'],c) in selected} for d in docs}
     misses=sorted([(uniform('C-false',seed,d['id'],c),d['id'],c) for d in docs for c in d['gold_C'] if (d['id'],c) not in selected])
     for _,doc,c in misses[:pC]:
      d=byid[doc];suffix=c[1:];alternative=('b' if uniform('C-kind',seed,doc,c)<.5 else 't')+suffix
      if alternative not in d['components']:alternative='t'+suffix
      chosenC[doc].add(alternative)
     chosenC_cache[cm]={k:set(v) for k,v in chosenC.items()}
    eligible=[]
    for d in docs:
     for r in d['gold_R']:
      obj=d['relations'][r]
      if set(obj['sources'])|{obj['target']}<=chosenC[d['id']]:
       rank=uniform('R-base',seed,d['id'],r)+.06*(len(obj['sources'])-1)+method_noise(seed,method,d['id'],r,'R')
       eligible.append((rank,d['id'],r))
    eligible.sort()
    assert len(eligible)>=tR,(corpus,seed,method,'insufficient gold endpoint coverage',len(eligible),tR)
    chosenR={d['id']:set() for d in docs}
    for _,doc,r in eligible[:tR]:chosenR[doc].add(r)
    false_pool=[]
    for d in docs:
     for rank,ident,raw in false_relations(d,chosenC[d['id']],chosenR[d['id']],seed,method):false_pool.append((rank,d['id'],ident,raw))
    false_pool.sort(key=lambda x:(x[0],x[1],x[2]));assert len(false_pool)>=pR
    for _,doc,r,obj in false_pool[:pR]:
     old_obj=byid[doc]['relations'].get(r);assert old_obj is None or old_obj==obj
     byid[doc]['relations'][r]=obj;chosenR[doc].add(r)
    crows=[];rrows=[];tc=set();fc=set();tr=set();fr=set()
    for d in docs:
     C=chosenC[d['id']];R=chosenR[d['id']];assert not legal(d,C,R),(method,d['id'])
     c=counts(C,d['gold_C']);rr=counts(R,d['gold_R']);crows.append(c);rrows.append(rr)
     gc=set(d['gold_C']);gr=set(d['gold_R']);tc|={(d['id'],x) for x in C&gc};fc|={(d['id'],x) for x in C-gc};tr|={(d['id'],x) for x in R&gr};fr|={(d['id'],x) for x in R-gr}
     graphs.append({'id':d['id'],'corpus':corpus,'seed':seed,'method':method,'C':sorted(C),'R':sorted(R),'evidence_type':'CONSTRUCTED_PREDICTION_ON_NATIVE_TEXT','gold_used_in_construction':True,'training_or_repair_executed':False})
     for axis,z in [('component',c),('relation',rr)]:raw_counts.append({'protocol':'strict_native_graph_scenario','dataset':corpus,'document':d['id'],'seed':seed,'method':method,'object':axis,'tp':z[0],'fp':z[1],'fn':z[2],'evidence_type':'SIMULATED_ENDPOINT_LINKED_GRAPH'})
    for axis,z,st in [('component',crows,(tc,fc)),('relation',rrows,(tr,fr))]:arr[corpus,seed,method,axis]=np.array(z);sets[corpus,seed,method,axis]=st
    target_checks.append({'corpus':corpus,'seed':seed,'method':method,'C_target':cf,'R_target':rf,'C_actual':float(f1(np.sum(crows,axis=0))),'R_actual':float(f1(np.sum(rrows,axis=0))),'eligible_gold_relations':len(eligible),'gold_relations':nr})
    if corpus=='CDCP' and method in FOUR:
     for k in ['1','2','3','4+']:
      def match(r):n=len(r['sources']);return n>=4 if k=='4+' else n==int(k)
      ac=[0,0,0]
      for d in docs:
       z=counts([r for r in chosenR[d['id']] if match(d['relations'][r])],[r for r in d['gold_R'] if match(d['relations'][r])]);ac=[a+b for a,b in zip(ac,z)]
      strata.append({'method':method,'seed':seed,'arity':k,'tp':ac[0],'fp':ac[1],'fn':ac[2]})
   print(json.dumps({'corpus':corpus,'seed':seed,'graphs':len(graphs),'seconds':round(time.perf_counter()-t0,2)}),flush=True)
  metrics[corpus]={};paired[corpus]={};interactions[corpus]={};risk[corpus]={}
  for m in TARGETS:
   metrics[corpus][m]={}
   for axis in ['component','relation']:
    totals=[arr[corpus,s,m,axis].sum(axis=0).tolist() for s in SEEDS];v=[float(f1(x)) for x in totals]
    metrics[corpus][m][axis]={'mean':float(np.mean(v)),'sd':float(np.std(v,ddof=1)),'seeds':v,'counts':totals}
  # Duplicate texts were removed before document-paired simulation bootstrap.
  indices=rand('V13',corpus,'bootstrap').integers(0,nd,size=(2000,nd))
  for axis in ['component','relation']:
   boot={m:np.mean([f1(arr[corpus,s,m,axis][indices].sum(axis=1)) for s in SEEDS],axis=0) for m in TARGETS}
   pairs=[('t1_i1','t0_i0'),('t1_i0','t0_i0'),('t0_i1','t0_i0'),('t1_i1','t1_i0'),('t1_i1','t0_i1'),('simple_data_i0','qos_i0'),('head_i0','simple_data_i0'),('t1_i0','head_i0'),('full_filter_i0','t1_i0'),('random_i0','t1_i0'),('t1_i1','single_object'),('brj_local','single_object'),('t1_i1','relation_only'),('global_equal','brj_local'),('t1_i1','missing_as_low'),('t1_i1','uncalibrated')]
   for a,b in pairs:
    dif=boot[a]-boot[b];paired[corpus][a+'__'+b+'__'+axis]={'delta':metrics[corpus][a][axis]['mean']-metrics[corpus][b][axis]['mean'],'ci95':np.quantile(dif,[.025,.975]).tolist()}
   dif=boot['t1_i1']-boot['t1_i0']-boot['t0_i1']+boot['t0_i0'];point=metrics[corpus]['t1_i1'][axis]['mean']-metrics[corpus]['t1_i0'][axis]['mean']-metrics[corpus]['t0_i1'][axis]['mean']+metrics[corpus]['t0_i0'][axis]['mean']
   interactions[corpus][axis]={'value':point,'ci95':np.quantile(dif,[.025,.975]).tolist()}
   for seed in SEEDS:
    a,b,c,d=[sets[corpus,seed,m,axis][0] for m in FOUR]
    members.append({'dataset':corpus,'object':axis,'seed':seed,'baseline':len(a),'both_only':len((b-a)&(c-a)),'training_only':len((b-a)-(c-a)),'repair_only':len((c-a)-(b-a)),'neither_single_but_combined':len(d-(a|b|c)),'single_recovery_lost_in_combined':len(((b|c)-a)-d),'baseline_lost_combined':len(a-d)})
  for method in ['sequential','single_object','brj_local','t1_i1','global_equal','no_risk_guard']:
   row={k:0 for k in ['recovered','lost_tp','removed_fp','added_fp','base_tp','worse_documents']};row['document_seed_pairs']=nd*3
   for seed in SEEDS:
    a,b=sets[corpus,seed,'mcr_t1','relation'];c,d=sets[corpus,seed,method,'relation']
    for k,v in [('recovered',len(c-a)),('lost_tp',len(a-c)),('removed_fp',len(b-d)),('added_fp',len(d-b)),('base_tp',len(a))]:row[k]+=v
    row['worse_documents']+=int(np.sum(f1(arr[corpus,seed,method,'relation'])<f1(arr[corpus,seed,'mcr_t1','relation'])-1e-9))
   row['tp_retention']=100*(1-row['lost_tp']/row['base_tp']);risk[corpus][method]=row
 jsonl(OUT/'prediction_graphs.jsonl',graphs);jsonl(OUT/'object_universes.jsonl',all_docs)
 with (OUT/'document_counts.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(raw_counts[0]));w.writeheader();w.writerows(raw_counts)
 results={'evidence_type':'GOLD_INFORMED_NATIVE_GRAPH_AUTHORING_SCENARIO','seeds':SEEDS,'assumed_targets':TARGETS,'labels':LABELS,'metrics':metrics,'paired':paired,'interactions':interactions,'risk':risk,'members':members,'cdcp_strata':strata,'target_checks':target_checks,'native_statistics':read(ROOT/'data/manifest.json')['statistics'],'gold_used_in_construction':True,'true_model_training_runs':0,'main_graph_solver_runs':0,'limitations':['method labels denote constructed outputs, not actual training/repair runs','CI describes this chosen simulation over unique native training texts','all component and relation identities are linked to exact source spans','main object universe contains gold-informed candidates; not measured blind coverage']}
 dump(OUT/'results.json',results)
 dump(OUT/'manifest.json',{'evidence_type':results['evidence_type'],'created_for':'v13 assumed-passing review preview','source_manifest_sha256':sha(ROOT/'data/manifest.json'),'generator_sha256':sha(__file__),'graphs':len(graphs),'count_rows':len(raw_counts),'files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'},'new_model_runs':0,'new_target_model_training_runs':0})
 print(json.dumps({'main':{d:metrics[d]['t1_i1'] for d in metrics},'risk':{d:risk[d]['t1_i1']['tp_retention'] for d in risk},'graphs':len(graphs),'seconds':time.perf_counter()-t0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
