"""Executable specification checks on constructed objects, not corpus experiments.

Standard library only. Coordinates are half-open. Scores are supplied fixture
inputs, never learned predictions. The finite-state oracle is exhaustive on its
declared four-component universe, not a solver for the full AAEC/CDCP corpus.
"""
from __future__ import annotations
import hashlib
import itertools as it
import json
from collections import Counter, deque
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def stable_key(seed, doc, obj):
    raw = json.dumps([seed, doc, obj], ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest(), obj

def center_and_region(components, relations, corpus, seed=17, doc='fixture', max_chars=1000):
    if not components:
        return None, (), 'no_components'
    roles = {'Claim', 'MajorClaim'} if corpus == 'AAEC' else {'Policy', 'Value'}
    pool = [c for c in components if c[2] in roles]
    origin = 'conclusion' if pool else 'fallback'
    center = min(pool or components, key=lambda c: stable_key(seed, doc, c))
    region = {center}
    for sources, target, _ in relations:
        if target == center:
            region.update(sources)
    ordered = tuple(sorted(region))
    if sum(c[1]-c[0] for c in ordered) > max_chars:
        return center, (), 'region_budget'
    if any(a[0] < b[1] and b[0] < a[1] for a,b in it.combinations(ordered,2)):
        return center, (), 'overlapping_slots'
    return center, ordered, origin

def transport(text, components, replacements):
    cs = sorted(components)
    if any(a[1] > b[0] for a,b in zip(cs,cs[1:])):
        raise ValueError('overlapping_slots')
    out, cursor, mapping = '', 0, {}
    for c in cs:
        start,end,typ = c
        out += text[cursor:start]
        newstart = len(out)
        out += replacements.get(c, text[start:end])
        mapping[c] = (newstart,len(out),typ)
        cursor = end
    return out + text[cursor:], mapping

def region_classes(components, relations, region):
    positives = {(sources,target) for sources,target,_ in relations}
    ans = Counter()
    for u,v in it.permutations(components,2):
        if u in region or v in region:
            ans[('internal' if u in region and v in region else 'boundary',
                 'positive' if ((u,),v) in positives else 'NONE')] += 1
    return ans

def protect_and_clip(protected, supplements, limit):
    if not protected.keys() <= supplements.keys():
        supplements = {**supplements, **protected}
    extra = sorted((k for k in supplements if k not in protected), key=lambda k:(-supplements[k],k))
    return set(protected) | set(extra[:limit])

def round_robin(queues, batch=6):
    queues = [deque(q) for q in queues]
    result = []
    while len(result)<batch and any(queues):
        for q in queues:
            if q and len(result)<batch:
                result.append(q.popleft())
    return result

def counts(pred, gold):
    p,g=Counter(pred),Counter(gold)
    if any(v!=1 for v in g.values()):
        raise ValueError('duplicate_gold')
    tp=sum(min(p[k],g[k]) for k in g)
    return tp,sum(p.values())-tp,sum(g.values())-tp

def micro(count_list):
    tp,fp,fn = map(sum,zip(*count_list))
    return Fraction(2*tp,2*tp+fp+fn) if 2*tp+fp+fn else Fraction(0)

def subset(xs):
    xs=tuple(sorted(xs))
    for n in range(len(xs)+1):
        for group in it.combinations(xs,n):
            yield frozenset(group)

# Finite, constructed CDCP-style range legality; no claim about trained models.
COMP = frozenset('abct')
RELS = frozenset([(('a',),'t','Reason'), (('c',),'t','Reason'), (('a','c'),'t','Reason')])
POS = dict(zip('abct',range(4)))
G0 = (COMP, frozenset([(('a',),'t','Reason')]))
GOLD = frozenset([(('a',),'t','Reason'), (('a','c'),'t','Reason')])

def legal(state):
    c,rs=state
    if not c <= COMP or not rs <= RELS:
        return False
    for ss,t,_ in rs:
        if not set(ss)|{t} <= c or t in ss:
            return False
        low,high=min(POS[s] for s in ss),max(POS[s] for s in ss)
        if any(low<POS[x]<high and x not in ss for x in c):
            return False
    return True

STATES = tuple((c,r) for c in subset(COMP) for r in subset(RELS) if legal((c,r)))

def cost(g,h):
    return len(g[0]^h[0]),len(g[1]^h[1])

def neighbors(g):
    c,r=g
    for h in STATES:
        nc,nr=h
        removed,added=c-nc,nc-c
        shape=(len(removed),len(added))
        if shape==(0,0):
            # A pure-relation proposal operates one complete slot here.
            if len(r^nr)<=1:
                yield h
            continue
        if shape not in {(0,1),(1,0),(1,1),(1,2),(2,1)}:
            continue
        changed=removed|added
        domain={e for e in RELS if changed & (set(e[0])|{e[1]})}
        # Minimal legality expansion of invalid selected outside slots only.
        domain |= {e for e in r if not legal((nc,frozenset([e])))}
        if r-domain == nr-domain:
            yield h

def reachable(steps, cb=3, rb=3):
    frontier={(G0,0,0)}
    seen={G0}
    for _ in range(steps):
        new=set()
        for g,cc,rr in frontier:
            for h in neighbors(g):
                dc,dr=cost(g,h)
                if cc+dc<=cb and rr+dr<=rb:
                    new.add((h,cc+dc,rr+dr)); seen.add(h)
        frontier=new
    return seen

def oracle(gs):
    return max(micro([counts(g[1],GOLD)]) for g in gs)

def run():
    checks=[]
    def check(name, condition, evidence):
        if not condition: raise AssertionError(name)
        checks.append(dict(id=name,status='PASS',evidence=evidence))
    claim=(10,11,'Claim'); p=(0,1,'Premise'); q=(3,4,'Premise')
    c2=(15,16,'MajorClaim')
    x=center_and_region([claim,p,q,c2],[], 'AAEC')
    y=center_and_region([q,c2,p,claim],[], 'AAEC')
    check('center_determinism',x==y, {'center':x[0]})
    check('empty_and_fallback',center_and_region([],[],'AAEC')[2]=='no_components' and center_and_region([p],[],'AAEC')[2]=='fallback',{})
    sources=tuple((i*2,i*2+1,'Fact') for i in range(4)); policy=(12,13,'Policy')
    a=center_and_region([*sources,policy],[(sources,policy,'Reason')],'CDCP')
    check('long_gold_hyperedge',len(a[1])==5, {'source_members':4,'region_components':len(a[1])})
    check('region_budget_no_truncation',center_and_region([*sources,policy],[(sources,policy,'Reason')],'CDCP',max_chars=4)[2]=='region_budget',{'original_gold_preserved':True})
    text='aa bb cc'; cs=[(0,2,'Claim'),(3,5,'Premise'),(6,8,'Claim')]
    new,m=transport(text,cs,{cs[0]:'aaaa',cs[1]:'b'})
    check('coordinate_transport',new=='aaaa b cc' and m[cs[2]]==(7,9,'Claim') and len(set(m.values()))==3, {'text':new,'mapping':[[c,m[c]] for c in cs]})
    cc=region_classes([claim,p,q],[((p,),claim,'Support'),((p,),q,'Support')],{claim,p})
    check('four_factor_classes',len(cc)==4 and sum(cc.values())==6, {str(k):v for k,v in cc.items()})
    weights={str(n):([1]+[1/n]*n if n else [1]) for n in (0,1,2)}
    check('source_weights',list(map(sum,weights.values()))==[1,2,2],weights)
    kept=protect_and_clip({'protected':-100},{'high':1,'low':0},1)
    check('protected_candidates',kept=={'protected','high'},{'retained':sorted(kept)})
    rr=round_robin([[f'{i}-{j}' for j in range(3)] for i in range(6)])
    check('queue_category_coverage',len({s.split('-')[0] for s in rr})==6,{'queue':rr})
    a,b,c=(0,2),(1,3),(2,4)
    overlap=lambda x,y:x[0]<y[1] and y[0]<x[1]
    check('pairwise_conflict',overlap(a,b) and overlap(b,c) and not overlap(a,c),{'compatible_endpoints':['a','c']})
    h=(('a','c'),'t','Reason'); reduced=(frozenset('act'),G0[1])
    check('nonincident_new_slot',not legal((COMP,frozenset([h]))) and legal((reduced[0],frozenset([h]))) and (reduced[0],GOLD) not in set(neighbors(G0)),{})
    restored=(COMP,G0[1])
    check('invalid_old_hyperedge_expansion',restored in set(neighbors((reduced[0],GOLD))),{'removed_hyperedge':h})
    # Same supplied object scores and proposal; actual sequential decisions.
    old_c,new_c,old_r,new_r=Fraction(1,5),Fraction(4,5),Fraction(9,10),Fraction(1,5)
    delta_c,delta_r=new_c-old_c,new_r-old_r
    joint_accept=delta_c>=0 and delta_r>=0 and delta_c+delta_r>Fraction(1,100)
    stage1=delta_c>Fraction(1,100)
    sequential_intermediate=(new_c,Fraction(0)) if stage1 else (old_c,old_r)
    sequential_final=(new_c,new_r) if new_r>Fraction(1,100) else sequential_intermediate
    check('sequential_vs_joint',stage1 and not joint_accept and sum(sequential_final)<old_c+old_r,
          {'delta_component':float(delta_c),'delta_relation':float(delta_r),'delta_total':float(delta_c+delta_r),'joint_accept':joint_accept,'stage1_accept':stage1,'stage2_accept':True,'sequential_cost_C':2,'sequential_cost_R':2})
    timeout_output=sequential_intermediate
    check('stage2_failure_keeps_intermediate',timeout_output==(new_c,Fraction(0)),{'relation_count_on_timeout':0,'deleted_old_relation_cost':1})
    one,multi_=reachable(1),reachable(3)
    global_=set(g for g in STATES if cost(G0,g)[0]<=3 and cost(G0,g)[1]<=3)
    check('oracle_set_inclusions',G0 in one and one<=multi_<=global_,{'all_legal':len(STATES),'one':len(one),'multi':len(multi_),'global':len(global_)})
    vals={'initial':float(micro([counts(G0[1],GOLD)]))*100,'one':float(oracle(one))*100,'multi':float(oracle(multi_))*100,'global':float(oracle(global_))*100}
    check('oracle_exact_values',oracle(one)==Fraction(2,3) and oracle(multi_)==oracle(global_)==1,vals)
    cycle=[G0,reduced,G0]
    cumulative=tuple(sum(cost(x,y)[i] for x,y in zip(cycle,cycle[1:])) for i in (0,1))
    check('cumulative_vs_net',cumulative==(2,0) and cost(cycle[0],cycle[-1])==(0,0),{'cumulative':cumulative,'net':[0,0]})
    check('duplicate_and_empty_evaluation',counts(['r','r'],['r'])==(1,1,0) and counts([],['r'])==(0,0,1),{})
    # Exact counterexample: document-wise F1 optima differ from corpus optimum.
    doc_a=[(1,0,999),(0,0,1000)]
    doc_b=[(1,0,9),(9,81,1)]
    perdoc=[max(xs,key=lambda x:micro([x])) for xs in (doc_a,doc_b)]
    corpus=max(it.product(doc_a,doc_b),key=micro)
    check('micro_oracle_counterexample',micro(perdoc)<micro(corpus),{'per_document_choice':perdoc,'per_document_micro':float(micro(perdoc))*100,'corpus_choice':corpus,'corpus_micro':float(micro(corpus))*100})
    output={'evidence_type':'CONSTRUCTED_EXECUTION_NOT_CORPUS_EXPERIMENT','checks':checks,'passed':len(checks),'oracle':vals,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT/'mechanism_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':len(checks),'oracle':vals},ensure_ascii=False))
    return output

if __name__=='__main__':run()
