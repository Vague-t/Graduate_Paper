"""Independent object counts from frozen runs; no primary evaluator imports."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, sys

root=Path(sys.argv[1]).resolve()
read=lambda p:json.loads(p.read_text())
met=read(root/'results/evaluation_001/metrics.json')
gold={d['id']:d for p in (root/'evaluation').glob('*_gold.json') for d in read(p)['documents']}
docs=read(root/'candidate_pools.json')['documents']
per={d['id']:d for d in met['documents']}
common=read(root/'results/run_001/common_initial_states.json')

def gold_objects(d):
    c=[(x['char_start'],x['char_end'],x['type']) for x in d['components']]
    r={(tuple(sorted(c[i] for i in x['sources'])),c[x['target']],x['type']) for x in d['relations']}
    return {'C':set(c),'R':r}

def predicted(d,state):
    c={k:(x['start'],x['end'],x['type']) for k,x in d['components'].items()}
    r=d['relations']
    return {'C':{c[k] for k in state['C']},'R':{(tuple(sorted(c[i] for i in r[k]['sources'])),c[r[k]['target']],r[k]['type']) for k in state['R']}}

aggregate=defaultdict(Counter);checked=0
for d in docs:
    ident=d['id'];g=gold_objects(gold[ident]);chosen=common[ident]['graph']
    base=predicted(d,{'C':chosen['components'],'R':chosen['relations']}) if chosen and chosen['structurally_valid'] else {'C':set(),'R':set()}
    methods={'MCR-only':base}
    for label in ['g0','g1']:
        graph=next((x for x in d['graphs'] if x['candidate_id']==label and x['structurally_valid']),None)
        methods[label]=predicted(d,{'C':graph['components'],'R':graph['relations']}) if graph else {'C':set(),'R':set()}
    for path in sorted((root/'results/run_001').glob(ident+'__*.json')):
        r=read(path);key=r['score_condition']+'__'+r['mode'];checked+=1
        methods[key]=predicted(d,r['final']) if r['status']=='completed' else {'C':set(),'R':set()}
        if r['status']=='completed':
            assert predicted(d,r['initial'])==base
            assert len(r['accepted_attempts'])==sum(a['committed'] for a in r['attempts'])
    for method,objs in methods.items():
        for axis in ['C','R']:
            p=objs[axis];gg=g[axis];count={'TP':len(p&gg),'FP':len(p-gg),'FN':len(gg-p)}
            expect=per[ident]['metrics'][method][axis]
            assert all(count[n]==expect[n] for n in count),(ident,method,axis)
            denom=2*count['TP']+count['FP']+count['FN']
            assert abs(expect['F1']-(2*count['TP']/denom if denom else 0))<1e-12
            aggregate[(d['corpus'],method,axis)].update(count)
            if '__' in method:
                b=base[axis]
                delta={'TP_recovered':len((p-b)&gg),'TP_lost':len((b-p)&gg),'FP_added':len((p-b)-gg),'FP_removed':len((b-p)-gg)}
                assert all(v==per[ident]['changes'][method][axis][k] for k,v in delta.items())
    pool=predicted(d,{'C':list(d['components']),'R':list(d['relations'])})
    for axis in ['C','R']:assert len(pool[axis]&g[axis])==per[ident]['coverage'][axis+'_hits']
for (corpus,method,axis),count in aggregate.items():
    expect=met['aggregate'][corpus]['metrics'][method][axis]
    assert all(count[n]==expect[n] for n in count)
out={'status':'PASS','documents':len(docs),'document_condition_strategy_runs':checked,'primary_evaluator_imported':False,'metrics_sha256':hashlib.sha256((root/'results/evaluation_001/metrics.json').read_bytes()).hexdigest(),'independent_checks':['all per-document object counts','all micro-aggregate counts','all per-document F1 values','every recovered/lost TP and added/removed FP','strict candidate pool coverage','common initialization across score conditions']}
with (root/'results/evaluation_001/independent_recount.json').open('x') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps(out,ensure_ascii=False))
