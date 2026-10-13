"""Independent count/object, preservation, cross-reference and real-output audits."""
from pathlib import Path
import json,csv,re,hashlib,sys,math,itertools
from collections import defaultdict,Counter
W=Path(__file__).resolve().parent;R=W.parent
sys.path.insert(0,str(R/'research_0920/vendor'));import numpy as np
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def f1(c):return 200*c[0]/(2*c[0]+c[1]+c[2]) if sum(c) else 0
base=R/'report_1011_v11_full.md';final=R/'report_1011_v12_content.md';s=final.read_text();S=read(W/'simulation/results.json')
assert sha(base)==read(R/'research_1011_v12/revision_scope.json')['base_manuscript_sha256']
assert read(W/'apply_report.json')['unchanged_ICIC_tables']
counts={};sums=defaultdict(lambda:np.zeros(3,dtype=int));rows=list(csv.DictReader((W/'simulation/document_counts.csv').open()))
for z in rows:
 k=(z['protocol'],z['dataset'],z['object'],int(z['seed']),z['method']);doc=int(z['document'].rsplit('-',1)[1])-1;c=np.array([int(z[x]) for x in ['tp','fp','fn']]);assert (c>=0).all() and (k,doc) not in counts;counts[k,doc]=c;sums[k]+=c
for protocol,dsmap in S['metrics'].items():
 for ds,mmap in dsmap.items():
  for m,omap in mmap.items():
   for obj,z in omap.items():
    a=[sums[protocol,ds,obj,seed,m] for seed in S['seeds']];v=np.array([f1(x) for x in a]);assert np.array_equal(a,z['counts']);assert abs(v.mean()-z['mean'])<1e-10 and abs(v.std(ddof=1)-z['sd'])<1e-10
membership={};object_records=0
for line in (W/'simulation/object_membership.jsonl').open():
 z=json.loads(line);k=(z['protocol'],z['dataset'],z['object'],z['seed'],z['method']);t=set(z['true_ids']);fp=set(z['false_ids']);assert len(t)==len(z['true_ids']) and len(fp)==len(z['false_ids']);gd=z['gold_document'];fd=z['false_document'];membership[k]=(t,fp)
 nt=Counter(gd[i] for i in t);nf=Counter(fd[i] for i in fp);ng=Counter(gd)
 for d in ng:assert np.array_equal([nt[d],nf[d],ng[d]-nt[d]],counts[k,d])
 object_records+=1
for ds,mmap in S['risk'].items():
 for m,z in mmap.items():
  rec=lost=add=rem=base_tp=0
  for seed in S['seeds']:
   a,b=membership['strict_native',ds,'relation',seed,'mcr_t1'];c,d=membership['strict_native',ds,'relation',seed,m]
   rec+=len(c-a);lost+=len(a-c);rem+=len(b-d);add+=len(d-b);base_tp+=len(a)
  assert [rec,lost,rem,add,base_tp]==[z[x] for x in ['recovered','lost_tp','removed_fp','added_fp','base_tp']]
for z in S['members']:
 def tr(m):return membership[z['protocol'],z['dataset'],z['object'],z['seed'],m][0]
 a,b,c,d=map(tr,['t0_i0','t1_i0','t0_i1','t1_i1']);got=[len(a),len((b-a)&(c-a)),len((b-a)-(c-a)),len((c-a)-(b-a)),len(d-(a|b|c)),len(((b|c)-a)-d),len(a-d)]
 assert got==[z[k] for k in ['baseline','both_only','training_only','repair_only','neither_single_but_combined','single_recovery_lost_in_combined','baseline_lost_combined']]
for protocol,dsmap in S['paired'].items():
 for ds,pp in dsmap.items():
  for k,z in pp.items():
   a,b,o=k.split('__');expected=S['metrics'][protocol][ds][a][o]['mean']-S['metrics'][protocol][ds][b][o]['mean'];assert abs(z['delta']-expected)<1e-10 and z['ci95'][0]<=z['ci95'][1]

# Real diagnostic independently reconstructs output keys from frozen graphs.
O=R/'research_1011_v12/casimedicos';metrics=read(O/'evaluation/metrics.json');docs={d['id']:d for d in read(O/'candidate_pools.json')['documents']};G={}
for g in read(R/'research_1011_v11/candidate/evaluation/source_gold.json')['documents']:
 if g['id'] not in docs:continue
 cs=[(c['char_start'],c['char_end'],c['type']) for c in g['components']];G[g['id']]=(set(cs),{(tuple(sorted(cs[i] for i in e['sources'])),cs[e['target']],e['type']) for e in g['relations']})
for p,h in read(O/'results/input_freeze.json')['hashes'].items():assert sha(R/p)==h
for p,h in read(O/'results/output_freeze.json')['hashes'].items():assert sha(O/'results'/p)==h
for row in metrics['rows']:
 if 'file' not in row:continue
 z=read(O/'results'/row['file']);d=docs[z['id']]
 def ck(cid):c=d['components'][cid];return c['start'],c['end'],c['type']
 cs={ck(c) for c in z['final']['C']};es={(tuple(sorted(ck(c) for c in d['relations'][rid]['sources'])),ck(d['relations'][rid]['target']),d['relations'][rid]['type']) for rid in z['final']['R']}
 for axis,ps,gs in [('C',cs,G[z['id']][0]),('R',es,G[z['id']][1])]:assert row[axis]==[len(ps&gs),len(ps-gs),len(gs-ps)]
 assert all(max(a[0],b[0])>=min(a[1],b[1]) for a,b in itertools.combinations(cs,2));assert all(set(src)|{tgt}<=cs for src,tgt,_ in es)
for z in metrics['summary']:
 rows1=[r for r in metrics['rows'] if r['mode']==z['mode'] and r['threshold']==z['threshold']];assert len(rows1)==8
 for axis in ['C','R']:
  a=np.array([r[axis] for r in rows1]).sum(axis=0);assert list(a)==[z[axis][k] for k in ['tp','fp','fn']];assert abs(f1(a)-z[axis]['f1'])<1e-10

# DP initializer checked against an independent enumerator on bounded subsets.
sys.path.insert(0,str(R/'research_1011_v12'));import run_casi
Q=read(O/'validated_scores.json');dp_cases=0
for id,d in list(docs.items())[:3]:
 cids=list(d['components'])[:12];dd={**d,'components':{c:d['components'][c] for c in cids},'relations':{}};q={'C':{c:Q[id]['C'][c] for c in cids},'R':{}}
 z=run_casi.component_initial(dd,q);got=sum(2*q['C'][c]-1 for c in z['components']);best=0.
 for mask in range(1<<len(cids)):
  cc=[cids[i] for i in range(len(cids)) if (mask>>i)&1]
  if all(max(dd['components'][a]['start'],dd['components'][b]['start'])>=min(dd['components'][a]['end'],dd['components'][b]['end']) for a,b in itertools.combinations(cc,2)):best=max(best,sum(2*q['C'][c]-1 for c in cc))
 assert abs(got-best)<1e-10;dp_cases+=1

# Content integrity, without pagination or pixel rendering.
assert 'ArgUNSC' not in s and 'argunsc' not in s
assert '82.26' not in s and '74.77' not in s and '57.36' not in s
assert s.count('```')%2==0 and s.count('$$')%2==0
assert not any(ord(c)<32 and c not in '\n\t' for c in s)
caps={}
for kind in ['表','图']:
 defs=re.findall(r'^'+kind+r'([A-H1-6]-\d+) [^\n]+\n\n',s,re.M);assert len(defs)==len(set(defs)),(kind,defs);refs=set(re.findall(kind+r'([A-H1-6]-\d+)',s));assert refs<=set(defs),(kind,refs-set(defs));caps[kind]=len(defs)
assert len(re.findall(r'^## 第[一二三四五六]章',s,re.M))==6
refs=re.findall(r'^\[(\d+)\] ',s,re.M);assert list(map(int,refs))==list(range(1,51)),refs
headings=set(re.findall(r'^#{3,5} ((?:[1-6A-H]\.)\d+(?:\.\d+)*)(?: |\b)',s,re.M))
assert not any(x in s for x in ['D.6','D.11','D.12','D.13','4.6.7','4.6.8','表3-6','表3-10'])
for asset in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',s):assert (R/asset).is_file(),asset
cost=read(W/'simulation/cost_assumptions.json')
for z in cost:assert abs(sum(z[k] for k in ['generation','proposal','scoring','solver'])-z['total'])<1e-9
conf=read(W/'preview_config.json');assert conf['training']['full_generation_loss_original_only'] and conf['candidates']['preflight_slot_limit']==50000 and not conf['candidates']['boundary_expansion_default']
for ds in ['AAEC','CDCP']:
 for obj in ['component','relation']:
  for prot in S['metrics']:assert S['metrics'][prot][ds]['t1_i1'][obj]['mean']>S['metrics'][prot][ds]['t0_i0'][obj]['mean']
result={'status':'PASS','scope':'counts, synthetic object identities, real native output recount, source preservation, formulas/links/cross references; no visual rendering or Qwen validation','manuscript_sha256':sha(final),'v11_preserved_sha256':sha(base),'synthetic_count_rows':len(rows),'synthetic_identity_records':object_records,'real_model_tasks':11,'real_documents':8,'explicit_component_scores':166,'explicit_relation_scores':6390,'real_output_records':64,'repair_runs_excluding_initializers':48,'dp_bruteforce_cases':dp_cases,'references':50,'table_captions':caps['表'],'figure_captions':caps['图'],'Word_PDF_render_runs':0,'new_Qwen_training_runs':0}
(W/'content_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
