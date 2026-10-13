"""Verify fixed sampling/stop conditions and describe frozen candidate-score failures."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import json,hashlib

ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
def ck(c):return (c['start'],c['end'],c['type'])
def rk(d,r):return (tuple(sorted(ck(d['components'][i]) for i in r['sources'])),ck(d['components'][r['target']]),r['type'])

m=read(ROOT/'combined_metrics.json');sources=read(ROOT/'case_source_objects.json')
base=WORK/'research_1011_luna_expanded';plan=read(base/'sample_manifest.json')['full_preordered_extension_plan']
roots=[WORK/n for n in m['verified_wave_hashes']]
core={};tasks=[];selected=[]
for wi,r in enumerate(roots):
    manifest=read(r/'sample_manifest.json');ids={d['id'] for d in manifest['selected']}
    if wi==0:
        expected={i for parts in plan.values() for part in parts for i in part[:2]}
    elif wi==1:
        expected={i for parts in plan.values() for part in parts for i in part[2:8]}
    else:
        lo=8+4*(wi-2)
        expected={i for part in plan['cdcp'] for i in part[lo:lo+4]}
        for prev in roots[:wi]:
            assert not read(prev/'results/evaluation_001/metrics.json')['aggregate']['cdcp']['document_relation_outcomes'].get('improvement',0)
    assert ids==expected,(r,'preordered sample mismatch')
    selected+=list(ids)
    for name in ['graph_core.py','repair.py']:
        assert sha(r/name)==sha(roots[0]/name),(r,name,'core changed')
    core[r.name]={name:sha(r/name) for name in ['graph_core.py','repair.py']}
    if wi:
        calls=read(r/'model_dispatch_manifest.json')['calls']
        for role in ['prediction','scoring']:
            chosen=[c for c in calls if c['role']==role]
            assert Counter(i for c in chosen for i in c['documents'])==Counter(ids)
            assert all(c['model']=='gpt-5.6-luna' and c['reasoning_effort']=='low' and c['fork_turns']=='none' and c['status']=='completed' for c in chosen)
        tasks+=calls
assert len(selected)==len(set(selected))==len(m['documents'])
assert set(selected)==set(sources)
seen={c:{r['id'] for r in m['documents'] if r['corpus']==c} for c in plan}
available={c:{i for part in parts for i in part} for c,parts in plan.items()}
positives={c:m['aggregate'][c]['positive_ids'] for c in plan}
both=all(positives.values());exhausted=all(seen[c]==available[c] for c in plan if not positives[c])
assert both or exhausted,'Do not finalize before the preregistered stopping rule'
checks={'status':'PASS','fixed_preordered_sampling_verified':True,'all_input_output_source_hashes_verified_by':'combined_metrics.json','documents':len(selected),'unique_texts':m['unique_texts'],'new_model_tasks':len(tasks),'core_code_sha256':core,'manuscript_hashes':{name:sha(WORK/name) for name in ['report_1011_v9_full.md','report_1011_v9_full.docx']}}
write(ROOT/'integrity_audit.json',checks)
write(ROOT/'stop_decision.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'status':'STOP','reason':'positive_discovered_in_both_corpora' if both else 'preordered_pool_exhausted_for_corpus_without_positive','strict_positive_ids':positives,'analyzed_documents':{c:len(v) for c,v in seen.items()},'available_unique_audit_texts':{c:len(v) for c,v in available.items()},'unexamined_ids':{c:sorted(available[c]-seen[c]) for c in plan},'no_gold_driven_score_or_candidate_changes':True,'inference':'Exploratory adaptive case discovery; not held-out efficacy estimation'})

diag=[];scorecounts={c:Counter() for c in plan}
for row in m['documents']:
    ident=row['id'];src=sources[ident];d=src['pool'];g=src['gold'];br=src['runs']['BRJ-lite'];r=WORK/src['root']
    q=read(r/'scores'/f'{ident}.json');corpus=row['corpus']
    scorecounts[corpus].update({'components':len(d['components']),'relations':len(d['relations']),'relation_overrides':len(q['relation_score_overrides']),'relation_defaults':len(d['relations'])-len(q['relation_score_overrides'])})
    cs=[(c['char_start'],c['char_end'],c['type']) for c in g['components']]
    gold={(tuple(sorted(cs[i] for i in rel['sources'])),cs[rel['target']],rel['type']) for rel in g['relations']}
    for rid,rel in d['relations'].items():
        if rk(d,rel) not in gold:continue
        endpoints=set(rel['sources'])|{rel['target']};score=q['relation_score_overrides'].get(rid,.05)
        initial=br.get('initial');final=br.get('final')
        diag.append({'id':ident,'corpus':corpus,'relation_id':rid,'score':score,'default_score':rid not in q['relation_score_overrides'],'run_status':br['status'],'initial_relation_present':rid in initial['R'] if initial else None,'final_relation_present':rid in final['R'] if final else None,'initial_endpoints_present':endpoints<=set(initial['C']) if initial else None,'final_endpoints_present':endpoints<=set(final['C']) if final else None,'component_scores':{i:q['component_scores'][i] for i in sorted(endpoints)}})
summary={}
for c in plan:
    rr=[d for d in diag if d['corpus']==c]
    summary[c]={'candidate_gold_relation_hits':len(rr),'default_score_hits':sum(d['default_score'] for d in rr),'above_half_hits':sum(d['score']>.5 for d in rr),'high_score_hits_on_failed_documents':sum(d['score']>.5 and d['run_status']!='completed' for d in rr),'final_retained_hits':sum(d['final_relation_present'] is True for d in rr),'scoring_counts':dict(scorecounts[c])}
    assert len(rr)==m['aggregate'][c]['coverage']['R_hits']
write(ROOT/'candidate_score_diagnostics.json',{'status':'PASS','posthoc_descriptive_only':True,'summary':summary,'true_candidate_relations':diag,'limitation':'Scores and endpoint presence describe possible bottlenecks; this is not a counterfactual intervention or score retuning.'})
print(json.dumps({'integrity':checks['status'],'stop':'both_positive' if both else 'pool_exhausted','documents':len(selected),'new_model_tasks':len(tasks),'candidate_score_diagnostics':summary},ensure_ascii=False,indent=2))
