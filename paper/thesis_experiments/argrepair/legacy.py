"""Native-object port of the existing 0914 BR-O reference implementation.

It is a declared new implementation, not a verified reproduction of historical
published checkpoints. It preserves the dynamic DENS/COH/VAL objective and the
four original action classes. I1 must start from G0, never from this final graph.
"""
from dataclasses import dataclass,asdict
from itertools import chain
from .schema import *

@dataclass
class LegacyConfig:
    density_weight: float=.4
    coherence_weight: float=.4
    validity_weight: float=.2
    root_threshold: float=2.
    other_threshold: float=1.
    rounds: int=3
    accepted_per_round: int=2
    actions_per_error: int=4
    max_attempts: int=24
    acyclic: bool=False

def score_graph(doc,graph,judge,config=None):
    cfg=config or LegacyConfig();judgments=[judge(doc,r) for r in graph.relations]
    if any(p is None for p in judgments):raise ValueError('missing semantic verifier result')
    coverage={}
    conclusion={'Claim'} if doc.corpus=='aaec' else {'policy','value'}
    for c in graph.components:
        if c.label not in conclusion:continue
        threshold=cfg.other_threshold if any(c in r.sources for r in graph.relations) else cfg.root_threshold
        coverage[c]=min(1.,sum(p for r,p in zip(graph.relations,judgments) if r.target==c)/threshold)
    density=sum(coverage.values())/len(coverage) if coverage else 0.
    coherence=sum(judgments)/len(judgments) if judgments else 0.
    valid=float(not graph_errors(doc,graph,acyclic=cfg.acyclic))
    return {'total':cfg.density_weight*density+cfg.coherence_weight*coherence+cfg.validity_weight*valid,'density':density,'coherence':coherence,'validity':valid,'coverage':coverage,'judgments':judgments}

def select_initial(doc,graphs,judge,config=None):
    """Rank complete graphs, then require declared structural validity."""
    if not graphs:raise ValueError('no parsed graphs')
    scored=[score_graph(doc,g,judge,config) for g in graphs]
    winner=max(range(len(graphs)),key=lambda i:(scored[i]['total'],-i));g=graphs[winner]
    if graph_errors(doc,g,acyclic=(config or LegacyConfig()).acyclic):raise ValueError('rank winner needs ambiguous legalization; fail closed')
    return g,{'winner':winner,'scores':[{k:v for k,v in s.items() if k not in ('coverage','judgments')} for s in scored],'legalization':'canonical_dedup_only_no_annotation_or_semantic_edits'}

def _replace_component(g,old,new):
    mapping={c:(new if c==old else c) for c in g.components}
    return Graph(tuple(mapping.values()),tuple(Relation(tuple(mapping[s] for s in r.sources),mapping[r.target],r.label) for r in g.relations))

def repair_legacy(doc,initial,candidates,judge,local_rerun,config=None):
    cfg=config or LegacyConfig();current=initial;ledger=[];visited={current.key};attempted=set();attempts=0
    for round_no in range(cfg.rounds):
        accepted=0
        while accepted<cfg.accepted_per_round and attempts<cfg.max_attempts:
            before=score_graph(doc,current,judge,cfg)
            events=[('edge',r) for r,p in zip(current.relations,before['judgments']) if p==0]
            events += [('node',c) for c,p in sorted(before['coverage'].items(),key=lambda kv:(kv[1],kv[0])) if p<1]
            progressed=False
            for kind,obj in events:
                def proposals():
                    if kind=='edge':
                        yield 'RemoveEdge',Graph(current.components,tuple(r for r in current.relations if r!=obj))
                        if local_rerun:yield 'LocalRerun',local_rerun(doc,current,obj.sources)
                    else:
                        if doc.corpus=='aaec' and obj.label in ('Claim','MajorClaim'):
                            alt=Component(obj.start,obj.end,'MajorClaim' if obj.label=='Claim' else 'Claim')
                            yield 'Promote/Demote',_replace_component(current,obj,alt)
                        for c in sorted({c for g in candidates for c in g.components if overlap(c,obj) and c!=obj}):
                            yield 'Replace',_replace_component(current,obj,c)
                        sources=tuple(c for c in current.components if c!=obj)
                        if local_rerun and sources:yield 'LocalRerun',local_rerun(doc,current,sources)
                iterator=iter(proposals())
                for _ in range(cfg.actions_per_error):
                    if attempts>=cfg.max_attempts:break
                    try:name,candidate=next(iterator)
                    except StopIteration:break
                    except (ValueError,RuntimeError) as exc:
                        attempts+=1;ledger.append({'attempt':attempts,'action':'LocalRerun','accepted':False,'reason':str(exc)});break
                    attempts+=1;key=(current.key,candidate.key)
                    entry={'attempt':attempts,'round':round_no,'action':name,'before':current.to_dict(),'after':candidate.to_dict(),'accepted':False}
                    ledger.append(entry)
                    if key in attempted or candidate.key in visited:entry['reason']='visited';continue
                    attempted.add(key)
                    if graph_errors(doc,candidate,acyclic=cfg.acyclic):entry['reason']='invalid';continue
                    after=score_graph(doc,candidate,judge,cfg)
                    entry.update(before_score=before['total'],after_score=after['total'])
                    if after['total']+1e-12<before['total']:entry['reason']='decreased';continue
                    entry.update(accepted=True,reason='nondecreasing_BR_O')
                    current=candidate;visited.add(current.key);accepted+=1;progressed=True;break
                if progressed:break
            if not progressed:break
        if not accepted:break
    return current,ledger,{'identity':'I0_NATIVE_BR_O_REIMPLEMENTATION','historical_checkpoint_reproduction':False,'attempts':attempts,'configuration':asdict(cfg)}

def rerun_callback(backend):
    from .chat import json_response
    def rerun(doc,current,sources):
        data=current.to_dict();ids={c:'c'+str(i) for i,c in enumerate(current.components)};allowed={ids[c] for c in sources}
        prompt='Given the text and FIXED predicted components below, predict outgoing relations only for the supplied source component IDs. Output JSON {"relations":[{"sources":["c0"],"target":"c1","type":"..."}]}. Do not change components. Use complete joint source sets for CDCP; sources must be within allowed_source_ids, targets can be any other component; use only native labels '+str(LABELS[doc.corpus])+'.\n'+canonical_json({'text':doc.text,'components':data['components'],'allowed_source_ids':sorted(allowed)})
        new=json_response(backend(prompt));parsed=Graph.from_dict({'components':data['components'],'relations':new['relations']})
        if any(not set(r.sources)<=set(sources) for r in parsed.relations):raise ValueError('LocalRerun changed sources outside scope')
        # Whole hyperedges touching an allowed source are replaced as indivisible objects.
        return Graph(current.components,tuple(r for r in current.relations if not set(r.sources)&set(sources))+parsed.relations)
    return rerun
