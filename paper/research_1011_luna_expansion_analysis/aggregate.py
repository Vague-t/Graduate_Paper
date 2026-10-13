"""Independent object recount and complete cross-wave descriptive aggregation."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,hashlib,sys

ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
def counts(pred,gold):
    tp=len(pred&gold);fp=len(pred-gold);fn=len(gold-pred)
    return {'TP':tp,'FP':fp,'FN':fn,'F1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.}
def ckey(c):return (c['start'],c['end'],c['type'])
def rkey(d,r):return (tuple(sorted(ckey(d['components'][c]) for c in r['sources'])),ckey(d['components'][r['target']]),r['type'])
def objects(d,state):
    return {'C':{ckey(d['components'][c]) for c in state['C']},'R':{rkey(d,d['relations'][r]) for r in state['R']}}
def gold_objects(g):
    c=[(x['char_start'],x['char_end'],x['type']) for x in g['components']]
    return {'C':set(c),'R':{(tuple(sorted(c[i] for i in r['sources'])),c[r['target']],r['type']) for r in g['relations']}}
def diff(old,new,gold):
    return {'TP_recovered':len((new-old)&gold),'TP_lost':len((old-new)&gold),'FP_removed':len((old-new)-gold),'FP_added':len((new-old)-gold),'initial_TP':len(old&gold),'initial_TP_retained':len(old&new&gold)}
def aggregate(rows):
    out={}
    for corpus in sorted({d['corpus'] for d in rows}):
        rr=[d for d in rows if d['corpus']==corpus];a={'documents':len(rr),'metrics':{},'changes':{},'coverage':{},'outcomes':dict(Counter(d['relation_outcome'] for d in rr))}
        for method in ['g0','g1','MCR-only','RelationOnly','BRJ-lite']:
            a['metrics'][method]={}
            for kind in ['C','R']:
                co={key:sum(d['metrics'][method][kind][key] for d in rr) for key in ['TP','FP','FN']};den=2*co['TP']+co['FP']+co['FN'];co['F1']=2*co['TP']/den if den else 0.
                a['metrics'][method][kind]=co
        for method in ['RelationOnly','BRJ-lite']:
            a['changes'][method]={k:{name:sum(d['changes'][method][k][name] for d in rr) for name in rr[0]['changes'][method][k]} for k in ['C','R']}
        a['coverage']={k:sum(d['coverage'][k] for d in rr) for k in rr[0]['coverage']}
        a['positive_ids']=[d['id'] for d in rr if d['relation_outcome']=='improvement']
        a['recovered_TP_positive_ids']=[d['id'] for d in rr if d['relation_outcome']=='improvement' and d['changes']['BRJ-lite']['R']['TP_recovered']>0]
        a['positive_beyond_RelationOnly_ids']=[d['id'] for d in rr if d['relation_outcome']=='improvement' and d['metrics']['BRJ-lite']['R']['F1']>d['metrics']['RelationOnly']['R']['F1']+1e-10]
        a['failure_ids']=[d['id'] for d in rr if d['relation_outcome']=='failure']
        a['component_improvement_ids']=[d['id'] for d in rr if d['run_status']['BRJ-lite']=='completed' and d['metrics']['BRJ-lite']['C']['F1']>d['metrics']['MCR-only']['C']['F1']+1e-10]
        out[corpus]=a
    return out

def main():
    roots=[WORK/'research_1010_v7_luna',WORK/'research_1011_luna_expanded']+sorted(WORK.glob('research_1011_luna_expanded_w[0-9][0-9]'))
    assert all((r/'results/evaluation_001/metrics.json').exists() for r in roots),'unfinished wave'
    rows=[];detail={};seen=set();seen_texts=set();verified={};native_audits=0;trace_audits=0;costs=[];origins=Counter()
    for wi,root in enumerate(roots):
        m=read(root/'results/evaluation_001/metrics.json');mr={d['id']:d for d in m['documents']}
        frozen=read(root/'results/run_001/input_freeze.json');of=read(root/'results/run_001/output_freeze.json')
        for name,h in frozen['hashes'].items():assert sha(root/name)==h,(root,name)
        for name,h in of['hashes'].items():assert sha(root/'results/run_001'/name)==h,(root,name)
        if wi:
            for name,h in read(root/'analysis_freeze_before_run.json')['hashes'].items():assert sha(root/name)==h,(root,name)
            for name,h in read(root/'source_freeze.json')['old_files'].items():assert sha(WORK/name)==h,(root,name)
        audit=read(root/'results/evaluation_001/audit.json');assert audit['status']=='PASS'
        native_audits+=len(audit['native_archive_checks']);trace_audits+=len(audit['trace_checks'])
        docs=read(root/'candidate_pools.json')['documents'];gm={g['id']:g for p in (root/'evaluation').glob('*_gold.json') for g in read(p)['documents']}
        costs.append({'wave':wi,'root':root.name,'costs':m['costs'],'solver_status_counts':m['solver_status_counts'],'committed_shape_counts':m['committed_shape_counts']})
        for d in docs:
            ident=d['id'];assert ident not in seen;seen.add(ident)
            th=hashlib.sha256(d['text'].encode()).hexdigest();assert th not in seen_texts;seen_texts.add(th);assert th==gm[ident]['text_sha256']
            row=mr[ident];G=gold_objects(gm[ident]);br=read(root/'results/run_001'/f'{ident}__BRJ-lite.json');ro=read(root/'results/run_001'/f'{ident}__RelationOnly.json')
            rank=min(br['ranks'],key=lambda q:(-q['rank'],q['slot'])) if br['ranks'] else None
            g=d['graphs'][rank['slot']] if rank else None
            initial=objects(d,{'C':g['components'],'R':g['relations']}) if g else {'C':set(),'R':set()}
            states={'MCR-only':initial,'g0':{'C':set(),'R':set()},'g1':{'C':set(),'R':set()}}
            for method,res in [('BRJ-lite',br),('RelationOnly',ro)]:
                states[method]=objects(d,res['final']) if res['status']=='completed' else {'C':set(),'R':set()}
            for graph in d['graphs']:states[graph['candidate_id']]=objects(d,{'C':graph['components'],'R':graph['relations']})
            for method,O in states.items():
                for kind in ['C','R']:
                    actual=counts(O[kind],G[kind]);expected=row['metrics'][method][kind]
                    assert all(actual[k]==expected[k] for k in ['TP','FP','FN']) and abs(actual['F1']-expected['F1'])<1e-12,(ident,method,kind)
                    if method in ['BRJ-lite','RelationOnly']:assert diff(initial[kind],O[kind],G[kind])==row['changes'][method][kind]
            allC={ckey(c) for c in d['components'].values()};allR={rkey(d,r) for r in d['relations'].values()}
            assert len(allC&G['C'])==row['coverage']['C_hits'] and len(allR&G['R'])==row['coverage']['R_hits']
            row={**row,'wave':wi,'source_root':root.name,'text_sha256':th,'run_status':{method:res['status'] for method,res in [('BRJ-lite',br),('RelationOnly',ro)]}}
            row['relation_outcome']='failure' if br['status']!='completed' else ('improvement' if row['relation_F1_delta']>1e-10 else ('harm' if row['relation_F1_delta']<-1e-10 else 'unchanged'))
            recovered=[]
            if br['status']=='completed':
                newkeys=(states['BRJ-lite']['R']-initial['R'])&G['R']
                for rid in br['final']['R']:
                    rr=d['relations'][rid]
                    if rkey(d,rr) not in newkeys:continue
                    entries=[a for a in br['attempts'] if a['committed'] and rid in a['after']['R'] and rid not in a['before']['R']]
                    assert entries
                    endpoints={cid:d['components'][cid] for cid in rr['sources']+[rr['target']]}
                    recovered.append({'relation_id':rid,'relation':rr,'endpoints':endpoints,'last_entry_attempt':entries[-1]['attempt'],'proposal':entries[-1]['proposal'],'delta_phi_C':entries[-1]['delta_phi_C'],'delta_phi_R':entries[-1]['delta_phi_R'],'all_endpoints_generated':all(c['origin']=='generated' for c in endpoints.values())})
                for cid in br['final']['C']:
                    c=d['components'][cid]
                    if ckey(c) in (states['BRJ-lite']['C']-initial['C'])&G['C']:origins[(d['corpus'],c['origin'])]+=1
            detail[ident]={'root':root.name,'gold':gm[ident],'pool':d,'runs':{'BRJ-lite':br,'RelationOnly':ro},'recovered_relations':recovered}
            row['recovered_relations']=recovered;rows.append(row)
        verified[root.name]={'input_freeze_sha256':sha(root/'results/run_001/input_freeze.json'),'output_freeze_sha256':sha(root/'results/run_001/output_freeze.json'),'evaluation_sha256':sha(root/'results/evaluation_001/metrics.json'),'native_archive_audit_sha256':sha(root/'results/evaluation_001/audit.json')}
    rows.sort(key=lambda d:d['id']);agg=aggregate(rows);bywave={str(i):aggregate([d for d in rows if d['wave']==i]) for i in sorted({d['wave'] for d in rows})}
    result={'created_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS','independent_document_object_recounts':len(rows),'document_method_recounts':2*len(rows),'native_archive_audits':native_audits,'trace_or_expected_failure_audits':trace_audits,'unique_texts':len(seen_texts),'aggregate':agg,'by_wave':bywave,'documents':rows,'costs':costs,'recovered_component_origins':{corpus:{origin:n for (c,origin),n in origins.items() if c==corpus} for corpus in agg},'verified_wave_hashes':verified}
    write(ROOT/'combined_metrics.json',result)
    write(ROOT/'case_source_objects.json',detail)
    print(json.dumps({'documents':len(rows),'aggregate':agg,'recovered_component_origins':result['recovered_component_origins']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
