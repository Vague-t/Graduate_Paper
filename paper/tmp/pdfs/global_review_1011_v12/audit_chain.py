"""Recount stored candidate-to-output blockers; no new model or solver run."""
from pathlib import Path
import json
from collections import Counter
import audit_review as a

def main():
    data=a.ROOT/'research_1011_v12/casimedicos'
    docs={d['id']:d for d in a.read(data/'candidate_pools.json')['documents']}
    scores=a.read(data/'validated_scores.json')
    gold={d['id']:d for d in a.read(a.ROOT/'research_1011_v11/candidate/evaluation/source_gold.json')['documents'] if d['id'] in docs}
    counts=Counter();details=[];changes=[];gold_n=0
    for ident,d in docs.items():
        g=gold[ident];cs=[(c['char_start'],c['char_end'],c['type']) for c in g['components']]
        gr={(tuple(sorted(cs[i] for i in r['sources'])),cs[r['target']],r['type']) for r in g['relations']}
        gold_n+=len(gr)
        initial=a.read(data/'results'/f'{ident}__0.50__component-then-relation_initialization.json')['final']
        selected=set(initial['C'])
        for rid,r in d['relations'].items():
            key=next(iter(a.predkeys(d,{'C':[],'R':[rid]})[1]))
            if key not in gr:continue
            endpoints=set(r['sources'])|{r['target']}
            category=('endpoint_not_selected' if not endpoints<=selected else
                      'score_at_or_below_threshold' if scores[ident]['R'][rid]<=.5 else
                      'selected_true_relation')
            if category=='selected_true_relation':assert rid in initial['R']
            counts[category]+=1
            details.append({'document':ident,'relation':rid,'score':scores[ident]['R'][rid],
                            'category':category,'endpoint_keys':{c:list(a.ckey(d['components'][c])) for c in sorted(endpoints)},
                            'unselected_endpoints':sorted(endpoints-selected)})
        for mode in ['SingleObject','BRJ-lite','GlobalILP-lite']:
            z=a.read(data/'results'/f'{ident}__0.50__{mode}.json')
            if z['initial']!=z['final']:
                changes.append({'document':ident,'mode':mode,'phi_initial':z['phi_initial'],'phi_final':z['phi_final'],
                                'component_removed':sorted(set(z['initial']['C'])-set(z['final']['C'])),
                                'component_added':sorted(set(z['final']['C'])-set(z['initial']['C'])),
                                'relation_removed':sorted(set(z['initial']['R'])-set(z['final']['R'])),
                                'relation_added':sorted(set(z['final']['R'])-set(z['initial']['R']))})
    output={'scope':'fixed 8 diagnostic docs, threshold .50, stored initialization/output; first-block decomposition, not causal or population estimate',
            'gold_relations':gold_n,'not_in_candidate_pool':gold_n-sum(counts.values()),
            'candidate_relations':sum(counts.values()),'candidate_first_block':dict(counts),
            'details':details,'actual_graph_changes':changes,
            'meaning':'no F1/count gain does not mean no graph modification',
            'new_model_or_solver_runs':0}
    target=Path(__file__).resolve().parent/'candidate_chain_audit.json'
    with target.open('x') as f:json.dump(output,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in output.items() if k not in ['details','actual_graph_changes']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
