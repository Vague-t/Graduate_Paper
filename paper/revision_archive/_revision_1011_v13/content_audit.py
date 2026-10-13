"""Independent semantic-key recount and content audit; no model or human validation."""
from pathlib import Path
import sys,json,csv,hashlib,re,itertools,collections,statistics
W=Path(__file__).resolve().parent;R=W.parent;D=R/'research_1011_v13';sys.path.insert(0,str(R/'research_0920/vendor'));import numpy as np

def read(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def ck(c):return c['start'],c['end'],c['type']
def rk(r,C):return tuple(sorted(ck(C[x]) for x in r['sources'])),ck(C[r['target']]),r['type']
def ct(p,g):p,g=set(p),set(g);return np.array([len(p&g),len(p-g),len(g-p)])
def fs(a):
 a=np.array(a);den=2*a[...,0]+a[...,1]+a[...,2];return np.divide(200*a[...,0],den,out=np.zeros_like(den,dtype=float),where=den>0)
def close(a,b):assert np.allclose(a,b,atol=1e-9,rtol=0),(a,b)
S=read(D/'simulation/results.json');U={d['id']:d for d in jl(D/'simulation/object_universes.jsonl')};native=jl(D/'data/native_documents.jsonl');manifest=read(D/'data/manifest.json');assert len(native)==899 and len(U)==899
assert manifest['test_texts_read'] is False and len({d['text_sha256'] for d in native})==899
for z in manifest['sources']:assert sha(R/z['archive'])==z['sha256']
assert sha(R/'research_0920/data/aaec_split.csv')==manifest['split_sha256'];assert sha(D/'data/native_documents.jsonl')==manifest['native_documents_sha256']
G={};valid_types={'AAEC':{'MajorClaim','Claim','Premise'},'CDCP':{'reference','testimony','fact','value','policy'}}
for did,d in U.items():
 assert h(d['text'])==d['text_sha256']
 for c in d['components'].values():assert 0<=c['start']<c['end']<=len(d['text']) and d['text'][c['start']:c['end']]==c['quote'] and c['type'] in valid_types[d['corpus']]
 for r in d['relations'].values():assert r['sources'] and len(r['sources'])==len(set(r['sources'])) and r['target'] not in r['sources'] and r['type'] in ({'supports','attacks'} if d['corpus']=='AAEC' else {'reason','evidence'})
 G[did]=({ck(d['components'][c]) for c in d['gold_C']},{rk(d['relations'][r],d['components']) for r in d['gold_R']})
rows=list(csv.DictReader((D/'simulation/document_counts.csv').open()));expected={}
for z in rows:
 k=(z['dataset'],int(z['seed']),z['method'],z['document'],z['object']);assert k not in expected;expected[k]=np.array([int(z[x]) for x in ['tp','fp','fn']])
graphs=jl(D/'simulation/prediction_graphs.jsonl');assert len(graphs)==67425 and len(rows)==2*len(graphs)
bygraph={};counts={};members=collections.defaultdict(lambda:[set(),set()])
for g in graphs:
 d=U[g['id']];C=g['C'];rr=g['R'];assert len(set(C))==len(C) and len(set(rr))==len(rr) and set(C)<=d['components'].keys() and set(rr)<=d['relations'].keys()
 assert g['gold_used_in_construction'] and not g['training_or_repair_executed']
 order=sorted(C,key=lambda c:ck(d['components'][c]));pos={c:i for i,c in enumerate(order)}
 assert all(d['components'][a]['end']<=d['components'][b]['start'] for a,b in zip(order,order[1:]));slots=set()
 for rid in rr:
  r=d['relations'][rid];assert set(r['sources'])|{r['target']}<=set(C);slot=tuple(r['sources']),r['target'];assert slot not in slots;slots.add(slot)
  if d['corpus']=='AAEC':assert len(r['sources'])==1
  else:
   ps=sorted(pos[c] for c in r['sources']);assert ps==list(range(ps[0],ps[-1]+1))
 key=(g['corpus'],g['seed'],g['method'],g['id']);assert key not in bygraph;bygraph[key]=g
 for axis,ps,gs in [('component',{ck(d['components'][c]) for c in C},G[g['id']][0]),('relation',{rk(d['relations'][r],d['components']) for r in rr},G[g['id']][1])]:
  k=key+(axis,);v=ct(ps,gs);assert np.array_equal(v,expected[k]);counts[k]=v
  mkey=key[:3]+(axis,);members[mkey][0]|={(g['id'],x) for x in ps&gs};members[mkey][1]|={(g['id'],x) for x in ps-gs}
arrays={}
for ds in ['AAEC','CDCP']:
 ids=[d['id'] for d in native if d['corpus']==ds]
 for seed in S['seeds']:
  for m in S['labels']:
   for axis in ['component','relation']:arrays[ds,seed,m,axis]=np.array([counts[ds,seed,m,d,axis] for d in ids])
 for m in S['labels']:
  for axis,z in S['metrics'][ds][m].items():
   totals=np.array([arrays[ds,se,m,axis].sum(0) for se in S['seeds']]);close(totals,z['counts']);v=fs(totals);close(v,z['seeds']);close(v.mean(),z['mean']);close(v.std(ddof=1),z['sd'])
 # Replay the declared paired bootstrap independently from semantic recounts.
 seed=int(h('|'.join(['V13',ds,'bootstrap']))[:16],16);ix=np.random.default_rng(seed).integers(0,len(ids),size=(2000,len(ids)))
 for axis in ['component','relation']:
  boot={m:np.mean([fs(arrays[ds,se,m,axis][ix].sum(1)) for se in S['seeds']],axis=0) for m in S['labels']}
  for k,z in S['paired'][ds].items():
   a,b,ax=k.split('__')
   if ax!=axis:continue
   close(z['delta'],S['metrics'][ds][a][axis]['mean']-S['metrics'][ds][b][axis]['mean']);close(np.quantile(boot[a]-boot[b],[.025,.975]),z['ci95'])
  v=boot['t1_i1']-boot['t1_i0']-boot['t0_i1']+boot['t0_i0'];close(np.quantile(v,[.025,.975]),S['interactions'][ds][axis]['ci95'])
 for m,z in S['risk'][ds].items():
  got=collections.Counter()
  for se in S['seeds']:
   a,b=members[ds,se,'mcr_t1','relation'];c,e=members[ds,se,m,'relation']
   got.update(dict(recovered=len(c-a),lost_tp=len(a-c),removed_fp=len(b-e),added_fp=len(e-b),base_tp=len(a),worse_documents=int(np.sum(fs(arrays[ds,se,m,'relation'])<fs(arrays[ds,se,'mcr_t1','relation'])-1e-9))))
  for k,v in got.items():assert v==z[k]
  close(100*(1-got['lost_tp']/got['base_tp']),z['tp_retention'])
for z in S['members']:
 ds,se,ax=z['dataset'],z['seed'],z['object'];a,b,c,d=[members[ds,se,m,ax][0] for m in ['t0_i0','t1_i0','t0_i1','t1_i1']]
 got=[len(a),len((b-a)&(c-a)),len((b-a)-(c-a)),len((c-a)-(b-a)),len(d-(a|b|c)),len(((b|c)-a)-d),len(a-d)]
 assert got==[z[k] for k in ['baseline','both_only','training_only','repair_only','neither_single_but_combined','single_recovery_lost_in_combined','baseline_lost_combined']]
for z in S['cdcp_strata']:
 a=np.zeros(3,int)
 for did,d in U.items():
  if d['corpus']!='CDCP':continue
  g=bygraph['CDCP',z['seed'],z['method'],did]
  def match(r):n=len(d['relations'][r]['sources']);return n>=4 if z['arity']=='4+' else n==int(z['arity'])
  a+=ct([r for r in g['R'] if match(r)],[r for r in d['gold_R'] if match(r)])
 close(a,[z['tp'],z['fp'],z['fn']])
for z in read(D/'simulation/error_chain.json')['rows']:
 got=collections.Counter()
 for se in S['seeds']:
  for did,d in U.items():
   if d['corpus']!=z['corpus']:continue
   g=bygraph[z['corpus'],se,z['method'],did]
   for r in d['gold_R']:
    got['gold_R']+=1
    if r in g['R']:got['selected_TP']+=1
    elif not (set(d['relations'][r]['sources'])|{d['relations'][r]['target']})<=set(g['C']):got['endpoint_blocked']+=1
    else:got['endpoints_ready_but_unselected']+=1
 for k,v in got.items():assert v==z[k]
print('67,425 graph semantic recounts, 134,850 counts, metrics, all paired intervals, risks, memberships and strata PASS',flush=True)
# Supplemental simulated acceptance records: independently recalculate actual summaries.
A=read(D/'acceptance_scenario/summary.json');review=jl(D/'acceptance_scenario/simulated_review_records.jsonl');hh=A['human_review_simulation'];assert len(review)==hh['n']==128
po=sum(x['simulated_reviewer_A']==x['simulated_reviewer_B'] for x in review)/len(review)
pe=sum(sum(x['simulated_reviewer_A']==label for x in review)*sum(x['simulated_reviewer_B']==label for x in review) for label in ['stable','changed','uncertain'])/len(review)**2
close(po,hh['agreement']);close((po-pe)/(1-pe),hh['kappa']);acc=[x for x in review if x['accepted_by_assumed_mask']];assert len(acc)==hh['accepted'];assert sum(x['assumed_reference']!='stable' for x in acc)==hh['accepted_unsafe']
assert len({(x['document'],x['variant_id']) for x in review})==63
sc=jl(D/'acceptance_scenario/simulated_oof_scores.jsonl');assert len(sc)==1600
for z in A['score_simulation']:
 rr=[x for x in sc if x['corpus']==z['corpus'] and x['axis']==z['axis']];y=np.array([x['label'] for x in rr]);q=np.array([x['q'] for x in rr]);pos=q[y==1];neg=q[y==0];close(np.mean((pos[:,None]>neg[None,:])+.5*(pos[:,None]==neg[None,:])),z['AUROC']);close(np.mean((q-y)**2),z['Brier']);ece=0
 for x in rr:
  d=U[x['document']];assert x['label']==int(x['object'] in d['gold_C' if x['axis']=='C' else 'gold_R']) and x['actual_heldout_model'] is None
 for i in range(10):
  mask=(q>=i/10)&(q<(i+1)/10 if i<9 else q<=1)
  if mask.any():ece+=mask.mean()*abs(q[mask].mean()-y[mask].mean())
 close(ece,z['ECE10'])
cost=jl(D/'acceptance_scenario/simulated_latency_records.jsonl');assert len(cost)==13485
for z in A['latency_simulation']:
 rr=[x for x in cost if x['corpus']==z['corpus'] and x['method']==z['method']];v=np.array([x['end_to_end_seconds'] for x in rr]);close(v.mean(),z['mean']);close(np.quantile(v,.95),z['p95'])
 for x in rr:close(sum(x[k+'_seconds'] for k in ['generation','proposal','scoring','solver']),x['end_to_end_seconds'])
assert len(A['acceptance'])==8 and all(z['scenario_status']=='PASS_SIMULATED' and not z['official_or_real_world_approval'] for z in A['acceptance']);assert A['actual_new_target_model_training_runs']==A['actual_new_human_reviewers']==A['actual_target_GPU_measurements']==A['actual_new_Luna_calls']==0
# Historical case cards, quotations, outputs and unchanged source hashes.
K=read(D/'cases/case_records.json');assert len(K['cases'])==10 and len(K['four_cell_cases'])==4
for p,v in K['source_hashes'].items():assert sha(R/p)==v,p
actual_cards=0
for c in K['cases']:
 assert h(c['text'])==c['text_sha256']
 if 'components' in c:
  for x in c['components']:assert c['text'][x['start']:x['end']]==x['original']
 if 'counts' in c:
  actual_cards+=1;d=c['pool'];gold=c['gold'];gc={ck(x) for x in gold['components'].values()};gr={rk(x,gold['components']) for x in gold['relations'].values()}
  for mode,st in c['states'].items():
   close(ct([ck(d['components'][x]) for x in st['C']],gc),c['counts'][mode]['C']);close(ct([rk(d['relations'][x],d['components']) for x in st['R']],gr),c['counts'][mode]['R'])
  for rr in c['selected_relations']:
   for x in rr['sources']+[rr['target']]:assert c['text'][x['start']:x['end']]==x['quote']
for c in K['four_cell_cases']:
 d=U[c['id']];r=c['relation'];assert r['id'] in d['gold_R']
 for m,st in c['states'].items():
  gg=bygraph[d['corpus'],c['seed'],m,c['id']];assert st['C']==gg['C'] and st['R']==gg['R'];assert st['relation_selected']==(r['id'] in gg['R'])
fx=read(D/'mechanism/inputs.json');F=read(D/'mechanism/summary.json');assert len(F['records'])==16
for p,v in fx['origin_solver_hashes'].items():assert sha(R/p)==v
for z in F['records']:
 a=next(x for x in fx['fixtures'] if x['id']==z['fixture']);out=read(D/'mechanism/runs'/f"{z['fixture']}__{z['mode']}.json")
 for ax in ['C','R']:v=ct(out['final'][ax],a['gold_'+ax]);close(v,out['counts'][ax]);close(fs(v),z[ax+'_F1'])
 if z['fixture'].endswith('missing_score'):assert out['final']==out['initial'] and not out['solver_calls']
assert sum(z['solver_calls'] for z in F['records'])==26 and F['checks_passed']==F['checks_total']==16
# Manuscript content checks, explicitly without layout rendering.
p=R/'report_1011_v13_content.md';s=p.read_text();old=(R/'report_1011_v12_content.md').read_text();assert sha(R/'report_1011_v12_content.md')=='062bbead8abab651311807fe44ec35b67d58bb876a33f8e218b9cca0870aa62e'
assert old[old.index('## 附录E'):old.index('## 附录F')]==s[s.index('## 附录E'):s.index('## 附录F')]
assert 'ArgUNSC' not in s and 'argunsc' not in s and '_revision_1010_v7/figures/augmentation.png' not in s
assert s.count('```')%2==0 and s.count('$$')%2==0 and not any(ord(c)<32 and c not in '\n\t' for c in s)
assert 'if mode = FullFilter then J_A ← D_A' in s and r'\Omega_{sem}(C)' in s and 'Oracle遵循4.6.3的松弛集合' not in s
caps={}
for kind in ['表','图']:
 defs=re.findall(r'^'+kind+r'([A-H1-6]-\d+) [^\n]+\n\n',s,re.M);assert len(defs)==len(set(defs));refs=set(re.findall(kind+r'([A-H1-6]-\d+)',s));assert refs<=set(defs),(kind,refs-set(defs));caps[kind]=len(defs)
assert len(re.findall(r'^## 第[一二三四五六]章',s,re.M))==6
assert list(map(int,re.findall(r'^\[(\d+)\] ',s,re.M)))==list(range(1,51))
for asset in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',s):assert (R/asset).is_file(),asset
# Match every row of key numerical result tables against external source JSON.
for ds in ['AAEC','CDCP']:
 for m in ['t0_i0','t1_i0','t0_i1','t1_i1']:
  for ax in ['component','relation']:
   z=S['metrics'][ds][m][ax];assert f"{z['mean']:.2f}±{z['sd']:.2f}" in s
# Audit every Markdown table for consistent cell counts (ignore escaped pipes and LaTex pipes).
for chunk in re.findall(r'(?m)^\|[^\n]+\n(?:\|[^\n]+\n)+',s):
 lines=chunk.splitlines();nums=[len(re.split(r'(?<!\\)\|',x)) for x in lines]
 assert len(set(nums))==1,lines[:2]
result={'status':'PASS','scope':'native-span graph recount, paired statistics, cases, simulated acceptance, actual fixture-output recount, content references, preservation; not target model or layout validation','manuscript_sha256':sha(p),'v12_preserved_sha256':sha(R/'report_1011_v12_content.md'),'native_documents':899,'simulated_graphs':len(graphs),'simulated_count_rows':len(rows),'paired_bootstrap_repetitions':2000,'simulated_acceptance_items':8,'actual_new_mechanism_output_records':16,'actual_solver_calls':26,'real_text_case_cards':10,'historical_output_cards_recounted':actual_cards,'four_cell_cards':4,'references':50,'numbered_tables':caps['表'],'numbered_figures':caps['图'],'new_target_model_training_runs':0,'new_human_reviewers':0,'new_Luna_calls':0,'target_GPU_measurements':0,'Word_PDF_render_runs':0}
(W/'content_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
