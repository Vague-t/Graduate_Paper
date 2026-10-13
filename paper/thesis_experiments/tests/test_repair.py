from dataclasses import replace
from types import SimpleNamespace
import copy
import numpy as np
import pytest
from argrepair.schema import InputDocument, Component as C, Relation as R, Graph, CandidatePool, Scores, graph_errors
from argrepair.repair import RepairConfig, Proposal, evaluate_proposal, global_repair, repair, replay_ledger


def example():
    doc=InputDocument('demo_tx','aaec','x'*40)
    a=C(0,8,'Claim');b=C(10,20,'Premise');c=C(22,32,'Premise');bp=C(10,21,'Premise')
    r1=R((b,),a,'supports');r2=R((c,),b,'supports');r3=R((bp,),a,'supports');r4=R((c,),bp,'supports')
    old=Graph((a,b,c),(r1,r2))
    pool=CandidatePool(doc,tuple(sorted((a,b,c,bp))),tuple(sorted((r1,r2,r3,r4))),old)
    scores=Scores({a:.9,b:.55,c:.85,bp:.8},{r1:.55,r2:.45,r3:.8,r4:.7})
    return pool,scores,(a,b,c,bp),(r1,r2,r3,r4)


def test_chapter_four_b_to_bprime_exact_transaction_and_replay():
    pool,scores,(a,b,c,bp),(r1,r2,r3,r4)=example()
    cfg=RepairConfig(delta=.2,component_budget=4,relation_budget=8,acyclic=True)
    tx=evaluate_proposal(pool,scores,pool.initial,Proposal(add=(bp,)),cfg)
    assert tx.accepted
    assert tx.graph==Graph((a,bp,c),(r3,r4))
    assert tx.delta_c==pytest.approx(.5);assert tx.delta_r==pytest.approx(1)
    assert (tx.edits_c,tx.edits_r)==(2,4)
    result=global_repair(pool,scores,cfg)
    assert result.status=='accepted'
    assert replay_ledger(pool,scores,result.ledger,cfg)==result.graph
    damaged=copy.deepcopy(result.ledger);damaged[0]['delta_c']+=1
    with pytest.raises(ValueError,match='hash'):replay_ledger(pool,scores,damaged,cfg)


def test_chapter_four_relation_decline_is_rejected_despite_total_gain():
    pool,scores,(_,_,_,bp),(r1,r2,r3,r4)=example()
    scores=Scores(scores.components,{r1:.6,r2:.6,r3:.6,r4:.4})
    tx=evaluate_proposal(pool,scores,pool.initial,Proposal(add=(bp,)),RepairConfig(delta=.2))
    assert not tx.accepted
    assert tx.graph==pool.initial
    assert tx.metadata['solver_status']=='infeasible'


def test_missing_scores_fail_closed_even_for_unselected_domain_object():
    pool,scores,(_,_,_,bp),(_,_,_,r4)=example()
    scores=Scores(scores.components,{r:q for r,q in scores.relations.items() if r!=r4})
    tx=evaluate_proposal(pool,scores,pool.initial,Proposal(add=(bp,)))
    assert tx.status=='missing_scores' and tx.graph==pool.initial
    assert global_repair(pool,scores).status=='missing_scores'


def test_unchanged_external_missing_score_can_cancel():
    pool,scores,(a,b,c,bp),_=example()
    scores=Scores({k:v for k,v in scores.components.items() if k!=a},scores.relations)
    tx=evaluate_proposal(pool,scores,pool.initial,Proposal(add=(bp,)))
    assert tx.accepted


def test_noncontact_cdcp_invalid_old_edge_expands_domain():
    doc=InputDocument('d','cdcp','x'*30)
    a=C(0,1,'fact');b=C(3,4,'fact');c=C(6,7,'fact');t=C(9,10,'policy');h=R((a,c),t,'reason')
    initial=Graph((a,c,t),(h,));pool=CandidatePool(doc,(a,b,c,t),(h,),initial)
    scores=Scores({a:.9,b:.9,c:.9,t:.9},{h:.2})
    tx=evaluate_proposal(pool,scores,initial,Proposal(add=(b,),kind='insert'))
    assert tx.accepted and tx.metadata['expanded_slots']==1
    assert not tx.graph.relations and b in tx.graph.components
    assert not graph_errors(doc,tx.graph)
    missing=Scores(scores.components,{})
    assert evaluate_proposal(pool,missing,initial,Proposal(add=(b,))).status=='missing_scores'


def test_newly_legal_noncontact_slot_needs_later_proposal():
    doc=InputDocument('d','cdcp','x'*30)
    a=C(0,1,'fact');b=C(3,4,'fact');c=C(6,7,'fact');t=C(9,10,'policy');h=R((a,c),t,'reason')
    initial=Graph((a,b,c,t));pool=CandidatePool(doc,(a,b,c,t),(h,),initial)
    scores=Scores({a:.9,b:.1,c:.9,t:.9},{h:.9})
    tx=evaluate_proposal(pool,scores,initial,Proposal(delete=(b,),kind='delete'))
    assert tx.accepted and h not in tx.graph.relations
    tx2=evaluate_proposal(pool,scores,tx.graph,Proposal(relation_slots=(h.slot,),kind='relation'))
    assert tx2.accepted and h in tx2.graph.relations
    global_result=global_repair(pool,scores)
    assert h in global_result.graph.relations and b not in global_result.graph.components


def test_cdcp_global_continuity_and_no_implicit_acyclic_rule():
    doc=InputDocument('d','cdcp','x'*30)
    a=C(0,1,'fact');b=C(3,4,'fact');c=C(6,7,'fact');t=C(9,10,'policy');h=R((a,c),t,'reason')
    initial=Graph((a,b,c,t));pool=CandidatePool(doc,(a,b,c,t),(h,),initial)
    scores=Scores({a:.9,b:.95,c:.9,t:.9},{h:.9})
    assert h not in global_repair(pool,scores).graph.relations
    aa=InputDocument('a','aaec','x'*10);x=C(0,1,'Claim');y=C(3,4,'Premise')
    r1=R((x,),y,'supports');r2=R((y,),x,'supports')
    cyclic=CandidatePool(aa,(x,y),(r1,r2),Graph((x,y)))
    qs=Scores({x:.9,y:.9},{r1:.9,r2:.9})
    assert len(global_repair(cyclic,qs).graph.relations)==2
    assert len(global_repair(cyclic,qs,RepairConfig(acyclic=True)).graph.relations)==1


def test_split_merge_envelope_and_single_rejects_hidden_merge():
    doc=InputDocument('d','aaec','x'*20);whole=C(0,10,'Claim');a=C(0,4,'Premise');b=C(6,10,'Premise')
    pool=CandidatePool(doc,(whole,a,b),(),Graph((whole,)))
    scores=Scores({whole:.4,a:.9,b:.9},{})
    prop=Proposal(add=(a,b),delete=(whole,),kind='split')
    assert not evaluate_proposal(pool,scores,pool.initial,prop).accepted
    tx=evaluate_proposal(pool,scores,pool.initial,prop,RepairConfig(allow_set_actions=True))
    assert tx.accepted and tx.edits_c==3
    merged=replace(pool,initial=tx.graph)
    merge_scores=Scores({whole:.95,a:.55,b:.55},{})
    nominal_insert=Proposal(add=(whole,),kind='insert')
    assert evaluate_proposal(merged,merge_scores,tx.graph,nominal_insert).status=='action_shape_outside_neighborhood'
    assert evaluate_proposal(merged,merge_scores,tx.graph,nominal_insert,RepairConfig(allow_set_actions=True)).accepted


def test_budget_and_atomic_commit_failure_keep_baseline():
    pool,scores,(_,_,_,bp),_=example()
    tx=evaluate_proposal(pool,scores,pool.initial,Proposal(add=(bp,)),remaining_components=1)
    assert tx.status=='component_budget_exceeded'
    def fail(record):raise OSError('injected commit failure')
    result=global_repair(pool,scores,commit_hook=fail)
    assert result.status=='commit_failure' and result.graph==pool.initial and result.ledger==[]


def test_timeout_no_incumbent_and_valid_incumbent(monkeypatch):
    import importlib
    mod=importlib.import_module('argrepair.repair')
    pool,scores,(a,b,c,bp),(r1,r2,r3,r4)=example()
    zero=global_repair(pool,scores,RepairConfig(time_limit=0))
    assert zero.status=='time_limit' and zero.graph==pool.initial
    desired=Graph((a,c,bp),(r3,r4))
    x=np.array([float(c in desired.components) for c in pool.components]+[float(r in desired.relations) for r in pool.relations])
    monkeypatch.setattr(mod,'milp',lambda *a,**kw:SimpleNamespace(x=x.copy(),status=1,message='injected time limit',mip_gap=.4))
    result=global_repair(pool,scores)
    assert result.status=='accepted' and result.graph==desired
    assert result.metadata['primary_optimal'] is False
    assert result.metadata['tie_break_complete'] is False


def test_queue_bounded_deterministic_and_replays():
    pool,scores,_,_=example()
    cfg=RepairConfig(attempts=5,batch_size=5,round_attempts=5,lex_call_limit=8)
    one=repair(pool,scores,cfg,method='Single');two=repair(pool,scores,cfg,method='Single')
    assert one.graph==two.graph
    assert one.metadata['attempts']<=5
    assert replay_ledger(pool,scores,one.ledger,cfg)==one.graph
    assert one.metadata['cumulative_components']>=one.metadata['net_components']
    with pytest.raises(ValueError,match='BR-O'):repair(pool,scores,method='I0')


def test_global_primary_matches_exhaustive_small_problem():
    from itertools import product
    import random
    doc=InputDocument('brute','aaec','x'*12)
    a=C(0,3,'Claim');ap=C(0,4,'Claim');b=C(6,9,'Premise')
    rs=(R((a,),b,'supports'),R((ap,),b,'supports'),R((b,),a,'attacks'),R((b,),ap,'attacks'))
    initial=Graph((a,b),(rs[2],));pool=CandidatePool(doc,(a,ap,b),rs,initial)
    cfg=RepairConfig(component_budget=3,relation_budget=3,lex_call_limit=0)
    for seed in range(4):
        rng=random.Random(seed);scores=Scores({c:rng.uniform(.1,.9) for c in pool.components},
                                           {r:rng.uniform(.1,.9) for r in pool.relations})
        def u(g):
            return (sum(2*scores.components[c]-1 for c in g.components),
                    sum(2*scores.relations[r]-1 for r in g.relations))
        base=u(initial);best=sum(base)
        for bits in product((0,1),repeat=7):
            graph=Graph(tuple(c for c,v in zip(pool.components,bits[:3]) if v),tuple(r for r,v in zip(rs,bits[3:]) if v))
            if graph_errors(doc,graph):continue
            if len(set(graph.components)^set(initial.components))>3 or len(set(graph.relations)^set(initial.relations))>3:continue
            uc,ur=u(graph)
            if uc>=base[0]-cfg.numeric_tol and ur>=base[1]-cfg.numeric_tol:best=max(best,uc+ur)
        result=global_repair(pool,scores,cfg)
        if best-sum(base)>cfg.delta+cfg.numeric_tol:
            assert sum(u(result.graph))==pytest.approx(best,abs=1e-7)
        else:assert result.graph==initial


def test_tertiary_preference_deterministic_without_weight_perturbation():
    doc=InputDocument('tie','aaec','x'*12);a=C(0,3,'Claim');b=C(6,9,'Premise')
    x=R((b,),a,'attacks');y=R((b,),a,'supports')
    pool=CandidatePool(doc,(a,b),(x,y),Graph((a,b)))
    scores=Scores({a:.9,b:.9},{x:.8,y:.8})
    cfg=RepairConfig(lex_call_limit=32)
    result=global_repair(pool,scores,cfg)
    assert len(result.graph.relations)==1
    assert result.metadata['primary_optimal'] and result.metadata['secondary_optimal']
    assert result.metadata['tie_break_complete']
    backwards=replace(pool,components=tuple(reversed(pool.components)),relations=tuple(reversed(pool.relations)))
    assert global_repair(backwards,scores,cfg).graph==result.graph


def test_graph_key_ties_match_variable_length_tuple_exhaustive():
    from itertools import product
    import random
    doc=InputDocument('ties','aaec','x'*12)
    a=C(0,3,'Claim');ap=C(0,4,'Claim');b=C(6,9,'Premise')
    rs=(R((a,),b,'supports'),R((ap,),b,'supports'),R((b,),a,'attacks'),R((b,),ap,'attacks'))
    initial=Graph((a,b),(rs[2],));pool=CandidatePool(doc,(a,ap,b),rs,initial)
    cfg=RepairConfig(component_budget=3,relation_budget=4,lex_call_limit=100,global_tie_break='graph_key')
    for seed in range(24):
        rng=random.Random(seed+100)
        scores=Scores({c:rng.choice((.2,.5,.8)) for c in pool.components},
                      {r:rng.choice((.2,.5,.8)) for r in pool.relations})
        def u(g):return (sum(2*scores.components[c]-1 for c in g.components),sum(2*scores.relations[r]-1 for r in g.relations))
        base=u(initial);feasible=[]
        for bits in product((0,1),repeat=7):
            g=Graph(tuple(c for c,v in zip(pool.components,bits[:3]) if v),tuple(r for r,v in zip(rs,bits[3:]) if v))
            if graph_errors(doc,g):continue
            ec=len(set(g.components)^set(initial.components));er=len(set(g.relations)^set(initial.relations))
            uc,ur=u(g)
            if ec<=3 and er<=4 and uc>=base[0]-cfg.numeric_tol and ur>=base[1]-cfg.numeric_tol:
                feasible.append((g,uc+ur,ec+er))
        primary=max(t[1] for t in feasible)
        best_edit=min(t[2] for t in feasible if t[1]>=primary-cfg.numeric_tol)
        expected=min((t[0] for t in feasible if t[1]>=primary-cfg.numeric_tol and t[2]==best_edit),key=lambda g:g.key)
        result=global_repair(pool,scores,cfg)
        if primary-sum(base)>cfg.delta+cfg.numeric_tol:
            assert result.metadata['tie_break_complete']
            assert result.graph==expected
        else:assert result.graph==initial


def test_local_graph_key_prefers_first_label_not_zero_first_bit_vector():
    doc=InputDocument('localtie','aaec','x'*12);a=C(0,3,'Claim');b=C(6,9,'Premise')
    x=R((b,),a,'attacks');y=R((b,),a,'supports')
    pool=CandidatePool(doc,(a,b),(x,y),Graph((a,b)))
    scores=Scores({a:.9,b:.9},{x:.8,y:.8})
    tx=evaluate_proposal(pool,scores,pool.initial,Proposal(relation_slots=(x.slot,),kind='relation'))
    assert tx.accepted and tx.graph.relations==(x,)
    assert tx.metadata['tie_break_rule']=='graph_key'


def test_missing_initial_negative_probability_never_defaults_to_zero():
    pool,scores,(a,b,c,bp),_=example()
    missing=Scores({a:.9,c:.9,bp:.9},scores.relations)
    assert global_repair(pool,missing).status=='missing_scores'
    negative=Scores({a:.9,b:-.1,c:.9,bp:.9},scores.relations)
    assert global_repair(pool,negative).status=='missing_scores'


def test_nonintegral_incumbent_rejected(monkeypatch):
    import importlib
    mod=importlib.import_module('argrepair.repair')
    pool,scores,_,_=example()
    x=np.full(len(pool.components)+len(pool.relations),.5)
    monkeypatch.setattr(mod,'milp',lambda *a,**kw:SimpleNamespace(x=x,status=1,message='fractional injected',mip_gap=.5))
    result=global_repair(pool,scores)
    assert result.graph==pool.initial and result.status=='invalid_incumbent'


def test_solver_stages_share_one_time_budget(monkeypatch):
    import importlib
    import time
    mod=importlib.import_module('argrepair.repair');original=mod.milp;limits=[]
    def delayed(*args,**kwargs):
        limits.append(kwargs['options']['time_limit'])
        time.sleep(.01)
        return original(*args,**kwargs)
    monkeypatch.setattr(mod,'milp',delayed)
    pool,scores,_,_=example()
    result=global_repair(pool,scores,RepairConfig(time_limit=.8))
    assert result.status=='accepted' and len(limits)>=2
    assert limits[1]<limits[0]-.008
    assert all(later<earlier for earlier,later in zip(limits,limits[1:]))


def test_frozen_mapping_scores_and_no_risk_keep_costs():
    from types import MappingProxyType
    from argrepair.repair import no_risk_config,repair_no_risk
    pool,scores,_,_=example()
    frozen=Scores(MappingProxyType(dict(scores.components)),MappingProxyType(dict(scores.relations)),MappingProxyType({'frozen':True}))
    cfg=RepairConfig(kappa_r=.5,delta=.2)
    assert no_risk_config(cfg).kappa_r==.5
    assert no_risk_config(cfg).delta==10*cfg.numeric_tol
    result=repair_no_risk(pool,frozen,cfg)
    assert result.metadata['requested_method']=='NoRisk'
    assert replay_ledger(pool,frozen,result.ledger,no_risk_config(cfg))==result.graph


def test_actual_object_scorer_to_repair_frozen_metadata():
    from argrepair.scoring import ObjectScorer,TinyTextEncoder
    pool,_,_,_=example()
    model=ObjectScorer(TinyTextEncoder(hidden_size=8),pool.doc.corpus,hidden=12,dropout=0.)
    scores=model.score(pool)
    result=repair(pool,scores,method='I1')
    assert not graph_errors(pool.doc,result.graph)
    assert replay_ledger(pool,scores,result.ledger)==result.graph
