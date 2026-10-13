"""Independent recomputation of synthetic records and manuscript identity only."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,json,hashlib,re,math,statistics,sys
import numpy as np
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v3'
SEEDS=[17,29,43];DS=['AAEC','CDCP'];IDENTITY='SIM-1010-V4'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda n:json.loads((W/n).read_text())
def rows(n):
    with (W/n).open() as f:return list(csv.DictReader(f))
def close(a,b):assert np.allclose(a,b,atol=1e-10,rtol=0),(a,b)
def score(c):
    a=np.asarray(c);return 200*a[...,0]/(2*a[...,0]+a[...,1]+a[...,2])
def counts(x):return [int(x[k]) for k in ['tp','fp','fn']]
def total(xs):return np.array([counts(x) for x in xs]).sum(axis=0)
def metrics(xs):
    values=[float(score(total([x for x in xs if int(x['seed'])==seed]))) for seed in SEEDS]
    return statistics.mean(values),statistics.stdev(values)
old={(x['dataset'],int(x['seed']),x['method'],x['object'],x['document']):counts(x) for x in rows('document_counts.csv')}
s=read('supplement_results.json');manifest=read('supplement_manifest.json');legacy=read('scenario_results.json')
assert s['identity']==IDENTITY and s['real_model_runs']==s['real_human_judgements']==s['real_solver_runs']==0
assert sha(W/'generate_supplement.py')==manifest['generator_sha256']
for n,h in manifest['files'].items():assert sha(W/n)==h,n
raw=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
portable='--portable' in sys.argv
if not portable:
    for n in raw:assert sha(W/n)==sha(P/n),n
    for p in (P/'figures').glob('*.png'):
        if not p.name.endswith('.preview.png'):assert sha(W/'figures'/p.name)==sha(p),p.name
# Shared text pool, actual token edit distance, quotas and all denominators.
variants=read('augmentation_text_pairs.json');screen=rows('augmentation_screening.csv')
assert len(variants)==320 and len(screen)==960
def lev(a,b):
    matrix=np.zeros((len(a)+1,len(b)+1),dtype=int)
    matrix[:,0]=np.arange(len(a)+1);matrix[0,:]=np.arange(len(b)+1)
    for i in range(1,len(a)+1):
        for j in range(1,len(b)+1):matrix[i,j]=min(matrix[i-1,j]+1,matrix[i,j-1]+1,matrix[i-1,j-1]+(a[i-1]!=b[j-1]))
    return int(matrix[-1,-1])
vmap={}
for v in variants:
    key=(v['dataset'],v['source'],v['attempt']);assert key not in vmap;vmap[key]=v
    a=re.findall(r'[A-Za-z]+|\d+|[^\w\s]',v['original_slot']);b=re.findall(r'[A-Za-z]+|\d+|[^\w\s]',v['variant_slot'])
    close(lev(a,b)/max(len(a),len(b)),v['edit_distance'])
    assert v['noncopy']==(v['original_slot']!=v['variant_slot'])
    assert v['factor_count']==len(v['synthetic_factor_drift'])==(4 if v['group']=='low' else 12)
seen=Counter();caps=Counter()
for x in screen:
    key=x['dataset'],x['source'],int(x['attempt']);v=vmap[key];seen[key]+=1
    assert int(x['drift_variant'])==int(any(v['synthetic_factor_drift']))
    assert int(x['drift_factors'])==sum(v['synthetic_factor_drift'])
    close(float(x['edit_distance']),v['edit_distance'])
    assert sum(int(x[k]) for k in ['accepted','rejected_screen','quota_only'])==1
    caps[x['dataset'],x['source'],x['method']]+=int(x['accepted'])
assert set(seen.values())=={3} and max(caps.values())==2
for q in s['augmentation']:
    xs=[x for x in screen if x['dataset']==q['dataset'] and x['method']==q['method']];a=[x for x in xs if int(x['accepted'])]
    assert len(xs)==q['attempts']==160 and len(a)==q['accepted']
    for out,col in [('noncopy','noncopy'),('drift_variants','drift_variant'),('factor_drift','drift_factors'),('factor_denominator','factors')]:assert sum(int(x[col]) for x in a)==q[out]
    close(100*q['noncopy']/len(a),q['noncopy_pct']);close(100*q['drift_variants']/len(a),q['drift_pct'])
    close(np.quantile([float(x['edit_distance']) for x in a],[.25,.5,.75]),[q['edit_q1'],q['edit_median'],q['edit_q3']])
    for group in ['low','high']:assert len({x['source'] for x in a if x['group']==group})==q[group+'_covered']
    assert len({x['source'] for x in a})==q['source_coverage']
# Candidate counts, precheck denominator, assigned resource cost and all outcomes.
rr=rows('resource_envelope.csv');bb=rows('budget_outcomes.csv');rm={(x['dataset'],x['document']):x for x in rr}
assert len(rr)==228 and len(bb)==8208
for x in rr:
    ds=x['dataset'];doc=x['document'];gold=old[ds,17,'t1_i0','component',doc];m=gold[0]+gold[2]+8
    upper=m*(m-1)*4 if ds=='AAEC' else sum(math.comb(m,k)*(m-k)*2**(k+1) for k in [1,2,3])
    slots=int(.6*upper);labels=slots*2
    assert [int(x[k]) for k in ['candidate_spans','typed_components','preprune_slots','scored_label_objects','postprune_slots']]==[m,2*m,slots,labels,min(slots,4096)]
    close(float(x['generation_s']),(1 if ds=='AAEC' else 1.35)*(9+.09*(m-8)))
    close(float(x['enumeration_s']),slots*(.0003 if ds=='AAEC' else .000003));close(float(x['scoring_s']),labels*(.00048 if ds=='AAEC' else .000018))
    close(float(x['preparation_s']),sum(float(x[k]) for k in ['generation_s','enumeration_s','scoring_s']))
    assert int(x['precheck_failed'])==int(slots>int(x['precheck_limit']))
    assert int(x['gold_relations'])==sum(old[ds,17,'t1_i0','relation',doc][::2])
bmap={};status_counter=Counter()
for x in bb:
    ds=x['dataset'];seed=int(x['seed']);method=x['method'];doc=x['document'];ob=x['object'];mult=float(x['budget_multiplier'])
    key=ds,seed,method,doc,ob,mult;assert key not in bmap;bmap[key]=x
    r=rm[ds,doc];base=old[ds,seed,'t1_i0',ob,doc];end=old[ds,seed,'t1_i1' if method=='local' else 'global_equal',ob,doc]
    f=float(x['incumbent_fraction']);deadline=(24 if ds=='AAEC' else 36)*mult;prep=float(r['preparation_s']);rem=max(0,deadline-prep)
    assert 0<=f<=1 and min(counts(x))>=0
    assert counts(x)==[round(base[0]+f*(end[0]-base[0])),round(base[1]+f*(end[1]-base[1])),base[0]+base[2]-round(base[0]+f*(end[0]-base[0]))]
    close(float(x['deadline_s']),deadline);assert float(x['elapsed_s'])<=deadline+1e-12
    assert int(x['fallback'])==int(f==0) and x['solver_certificate']=='NOT_EXECUTED' and x['global_gap']==''
    status=x['status'];status_counter[status]+=1
    if int(r['precheck_failed']):
        assert status=='PRECHECK_FAIL' and f==0;close(float(x['elapsed_s']),min(deadline,float(r['generation_s'])+float(r['enumeration_s'])))
    elif rem==0:assert status=='PREPARATION_TIMEOUT' and f==0
    elif status=='NO_INCUMBENT_TIMEOUT':assert f==0
    elif status=='FEASIBLE_TIMEOUT':assert .2<=f<1
    else:assert status=='COMPLETE_SCENARIO' and f==1
    if 'TIMEOUT' in status:close(float(x['elapsed_s']),deadline)
    if f==0:assert counts(x)==base
for q in s['resources']:
    xs=[x for x in rr if x['dataset']==q['dataset'] and (q['group']=='all' or x['group']==q['group'])]
    assert len(xs)==q['docs'];close(np.median([int(x['preprune_slots']) for x in xs]),q['slots_median'])
    assert max(int(x['preprune_slots']) for x in xs)==q['slots_max'];close(np.quantile([float(x['preparation_s']) for x in xs],.95),q['preparation_p95'])
    bad=[x for x in xs if int(x['precheck_failed'])];assert len(bad)==q['precheck_fail']
    assert sum(int(x['gold_relations']) for x in bad)==q['precheck_gold_relations'];assert sum(int(x['gold_relations']) for x in xs)==q['gold_relations']
for q in s['budget']:
    xs=[x for x in bb if x['dataset']==q['dataset'] and x['object']=='relation' and x['method']==q['method'] and float(x['budget_multiplier'])==q['multiplier'] and (q['group']=='all' or x['group']==q['group'])]
    assert len(xs)==q['doc_seed_rows'];close(metrics(xs),[q['mean_f1'],q['sd_f1']])
    close(statistics.mean(float(x['elapsed_s']) for x in xs),q['mean_s']);close(np.quantile([float(x['elapsed_s']) for x in xs],.95),q['p95_s'])
    close(100*sum('TIMEOUT' in x['status'] for x in xs)/len(xs),q['timeout_pct']);close(100*sum(int(x['fallback']) for x in xs)/len(xs),q['fallback_pct'])
    for out,status in [('precheck_pct','PRECHECK_FAIL'),('complete_pct','COMPLETE_SCENARIO')]:close(100*sum(x['status']==status for x in xs)/len(xs),q[out])
for q in s['budget_pairs']:
    ds,group,mult=q['dataset'],q['group'],q['multiplier'];docs=[x['document'] for x in rr if x['dataset']==ds and (group=='all' or x['group']==group)]
    ix=np.random.default_rng(int(hashlib.sha256(f'{IDENTITY}|{ds}|{group}|{mult}'.encode()).hexdigest()[:16],16)).integers(0,len(docs),size=(2000,len(docs)))
    data={method:np.array([[[int(bmap[ds,seed,method,d,'relation',mult][k]) for k in ['tp','fp','fn']] for d in docs] for seed in SEEDS]) for method in ['local','global']}
    delta=np.mean(score(data['local'][:,ix,:].sum(axis=2))-score(data['global'][:,ix,:].sum(axis=2)),axis=0)
    close(np.quantile(delta,[.025,.975]),q['ci95']);close(np.mean(score(data['local'].sum(axis=1))-score(data['global'].sum(axis=1))),q['local_minus_global'])
# External method identities are placeholders; recompute every summary from raw counts.
ext=rows('external_placeholders.csv');assert len(ext)==2736
for x in ext:
    assert x['evidence_type']=='EXTERNAL_METHOD_PLACEHOLDER_SIMULATION' and x['not_author_reported']=='True'
    base=old[x['dataset'],int(x['seed']),'t1_i0',x['object'],x['document']];assert int(x['tp'])+int(x['fn'])==base[0]+base[2] and min(counts(x))>=0
for q in s['external']:
    for ob in ['component','relation']:close(metrics([x for x in ext if x['dataset']==q['dataset'] and x['method']==q['method'] and x['object']==ob]),[q[ob]['mean'],q[ob]['sd']])
# Complete relation memberships must match ALL previous per-document TP/FP/FN.
members=read('object_memberships.json');trans=rows('object_transitions.csv');assert len(members)==len(trans)==684
tr={(x['dataset'],int(x['seed']),x['document']):x for x in trans};totals=defaultdict(Counter);mm={}
for x in members:
    ds,seed,doc=x['dataset'],x['seed'],x['document'];mm[ds,seed,doc]=x;g=set(x['gold']);p={m:set(v) for m,v in x['predictions'].items()}
    assert len(g)==len(x['gold'])
    for m,vals in p.items():
        assert len(vals)==len(x['predictions'][m]);assert [len(vals&g),len(vals-g),len(g-vals)]==old[ds,seed,m,'relation',doc]
        for key in vals:assert json.loads(key)[0]==doc
    good={m:v&g for m,v in p.items()};base=good['t0_i0'];rt=good['t1_i0']-base;ri=good['t0_i1']-base;j=good['t1_i1'];t=good['t1_i0']
    f={'training_only':len(rt-ri),'repair_only':len(ri-rt),'common':len(rt&ri),'combination_new':len(j-base-rt-ri),'base_destroyed':len(base-j),'t1_destroyed':len(t-j),'remaining_fn':len(g-j),'recovered_t1':len(j-t),'fp_removed':len((p['t1_i0']-g)-(p['t1_i1']-g)),'fp_added':len((p['t1_i1']-g)-(p['t1_i0']-g))}
    for k,v in f.items():assert int(tr[ds,seed,doc][k])==v,(ds,doc,k)
    totals[ds].update(f)
for q in s['objects']:
    ds=q['dataset']
    for k,v in totals[ds].items():assert q[k]==v
    risk=legacy['risk'][ds]['t1_i1']['relation']
    for a,b in [('recovered_t1','recovered'),('t1_destroyed','lost_tp'),('fp_removed','removed_fp'),('fp_added','added_fp')]:assert q[a]==risk[b]
for c in read('synthetic_object_cases.json'):
    x=mm[c['dataset'],c['seed'],c['document']];key=c['synthetic_object_key'];assert key in x['gold']
    assert c['presence']=={m:int(key in v) for m,v in x['predictions'].items()}
    assert list(c['presence'].values())==({'common':[0,1,1,1],'combination_new':[0,0,0,1],'damage':[0,1,0,0]}[c['category']])
# Preserve historical tables and math; only table 5 numbering changes with insertion.
source=(R/'report_1010_v4_full.md').read_text();before=(R/'report_1010_v3_full.md').read_text()
def tables(text):
    out={};pending=None
    for line in text.splitlines():
        m=re.match(r'^(表[A-H0-9]+-\d+) ',line)
        if m:pending=m.group(1)
        elif line.startswith('|') and pending:out.setdefault(pending,[]).append(line)
        elif line.strip() and pending and pending in out:pending=None
    return out
newtab=tables(source);oldtab=tables(before);mapping={'表5-3':'表5-3','表5-4':'表5-6','表5-5':'表5-7'}
renum=lambda t:re.sub(r'表5-[345](?!\d)',lambda m:mapping[m.group(0)],t)
assert len(newtab)==50 and len(oldtab)==44
for k,v in oldtab.items():assert newtab[mapping.get(k,k)]==[renum(z) for z in v],k
for kind in ['表','图']:
    for ch in ['1','2','3','4','5','6','A','B','C','D','E','F','G','H']:
        nums=[int(z) for z in re.findall(r'^'+kind+ch+r'-(\d+) ',source,re.M)]
        assert nums==list(range(1,len(nums)+1)),(kind,ch,nums)
assert re.findall(r'\$\$(.*?)\$\$',source,re.S)==re.findall(r'\$\$(.*?)\$\$',before,re.S)
assert source[source.index('# 附录E'):source.index('# 附录F')]==before[before.index('# 附录E'):before.index('# 附录F')]
assert re.findall(r'^\[\d+\] .+$',source,re.M)==re.findall(r'^\[\d+\] .+$',before,re.M)
assert len(re.findall(r'^!\[',source,re.M))==12
# Check new table data directly against recomputed summaries.
for q in s['augmentation']:
    vals=[f"{q['accepted']}/160",f"{q['noncopy']}/{q['accepted']}",f"{q['edit_median']:.2f}",f"{q['drift_variants']}/{q['accepted']}",f"{q['low_covered']}/20；{q['high_covered']}/20"]
    assert any('|'.join(vals) in line for line in newtab['表3-10'])
for q in s['external']:
    for ob in ['component','relation']:assert f"{q[ob]['mean']:.2f}±{q[ob]['sd']:.2f}" in '\n'.join(newtab['表4-10'])
for q in s['resources']:
    if q['group']=='all':continue
    vals=[str(q['docs']),str(int(q['slots_median'])),str(q['slots_max']),f"{q['preparation_p95']:.2f}",f"{q['precheck_fail']}/{q['docs']}"]
    assert any('|'.join(vals) in line for line in newtab['表4-11'])
for ds in DS:
    for mult in [.5,1,2]:
        q=[next(x for x in s['budget'] if x['dataset']==ds and x['group']=='all' and x['multiplier']==mult and x['method']==m) for m in ['local','global']]
        vals=[f"{x['mean_f1']:.2f}±{x['sd_f1']:.2f}" for x in q]+[f"{q[0]['p95_s']:.2f}／{q[1]['p95_s']:.2f}",f"{q[0]['fallback_pct']:.2f}／{q[1]['fallback_pct']:.2f}",f"{q[1]['timeout_pct']:.2f}"]
        assert any('|'.join(vals) in line for line in newtab['表4-12'])
for q in s['objects']:
    vals=[q['dataset']]+[str(q[k]) for k in ['training_only','repair_only','common','combination_new','t1_destroyed','remaining_fn']]
    assert '|'.join(vals) in '\n'.join(newtab['表5-4'])
cfg=read('reference_config.json');assert cfg['configuration_id']=='1010-v1-global-review' and cfg['manuscript_version']=='1010-v4'
result={'passed':True,'source_sha256':sha(R/'report_1010_v4_full.md'),'scope':'SYNTHETIC_ARITHMETIC_MEMBERSHIP_AND_DOCUMENT_IDENTITY','real_model_runs':0,'real_solver_runs':0,'real_human_judgements':0,'augmentation_texts':len(variants),'screening_decisions':len(screen),'resource_documents':len(rr),'budget_outcome_rows':len(bb),'budget_summary_rows':len(s['budget']),'budget_paired_intervals':len(s['budget_pairs']),'external_placeholder_rows':len(ext),'object_document_seed_records':len(members),'preserved_relation_metric_cells':len(members)*4,'case_records':3,'preserved_raw_files':raw,'preserved_legacy_pngs':11,'preserved_table_payloads':44,'new_tables':6,'total_tables':50,'display_formulas_unchanged':32,'references_unchanged':49,'chapter5_table_renumbering':mapping,'status_rows':dict(status_counter),'limitations':'No real corpus output, model training, optimizer trace, author implementation, empirical effect or empirical confidence interval verified.'}
if portable:
    result['preserved_raw_files']=None;result['preserved_legacy_pngs']=None
    result['baseline_asset_comparison']='SKIPPED in portable mode; workspace full audit recorded separately'
(W/('portable_audit.json' if portable else 'supplement_audit.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
