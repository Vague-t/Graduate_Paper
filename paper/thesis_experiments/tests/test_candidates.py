import pytest
from argrepair.schema import InputDocument, Document, Component as C, Relation as R, Graph
from argrepair.candidates import CandidateConfig, CandidateConstructionError, SpanProposal, GroupProposal, build_candidates


def test_no_gold_interface_and_protection():
    doc=InputDocument('d','aaec','x'*100)
    a=C(0,2,'Claim');b=C(4,6,'Premise');old=R((b,),a,'supports')
    initial=Graph((a,b),(old,))
    pool=build_candidates(doc,initial,span_proposals=[SpanProposal(0,99,{'Claim':.9,'Premise':.8,'MajorClaim':.7},.9,99)],
                          config=CandidateConfig(supplement_spans=0,supplement_slots=0),
                          relation_score_fn=lambda rs:{r:.1 for r in rs})
    assert set(initial.components)<=set(pool.components)
    assert old in pool.relations
    assert R((b,),a,'attacks') in pool.protected_relations
    assert pool.metadata['invalid_span_proposals']==1
    with pytest.raises(TypeError):build_candidates(Document(doc,initial),initial)


def test_span_top_two_and_dedup_before_cap():
    doc=InputDocument('d','aaec','x'*100)
    proposals=[SpanProposal(0,2,{'Claim':.1,'Premise':.9,'MajorClaim':.8},.6),
               SpanProposal(0,2,{'Claim':.99},.7),SpanProposal(4,6,{'Claim':1},.5)]
    pool=build_candidates(doc,Graph(),span_proposals=proposals,config=CandidateConfig(supplement_spans=1))
    assert pool.components==(C(0,2,'Claim'),C(0,2,'Premise'))


def test_parsed_components_survive_bad_relation():
    doc=InputDocument('d','aaec','x'*20)
    a=C(0,2,'Claim');b=C(4,6,'Premise')
    graph=Graph((a,b),(R((b,),a,'invalid'),))
    pool=build_candidates(doc,Graph(),candidate_graphs=[graph])
    assert {a,b}<=pool.protected_components
    assert pool.metadata['invalid_relations']==1
    assert all(r.label!='invalid' for r in pool.relations)


def test_cdcp_long_protection_and_64_256_are_nested_caps():
    doc=InputDocument('d','cdcp','x'*200)
    cs=tuple(C(i*3,i*3+1,'fact') for i in range(12))
    long=R(cs[:4],cs[-1],'reason')
    proposals=[GroupProposal((a,),b,1) for a in cs for b in cs if a!=b]
    pool=build_candidates(doc,Graph(cs,(long,)),group_proposals=proposals)
    assert long in pool.protected_relations
    assert pool.metadata['cdcp_model_groups_after']==64
    assert pool.metadata['cdcp_combined_groups_after']<=256
    assert pool.metadata['final_slots']<=257
    assert all(len(r.sources)<=3 or r.slot==long.slot for r in pool.relations)


def test_preflight_happens_before_scoring_and_supplement_crop():
    doc=InputDocument('d','aaec','x'*30)
    cs=tuple(C(i*3,i*3+1,'Claim') for i in range(6))
    called=[]
    with pytest.raises(CandidateConstructionError) as ex:
        build_candidates(doc,Graph(cs),config=CandidateConfig(preflight_slot_limit=10,supplement_slots=2),
                         relation_score_fn=lambda rs: called.append(rs))
    assert ex.value.status=='preflight_slot_overflow'
    assert not called


def test_whole_slot_pruning_by_frozen_max_label_score():
    doc=InputDocument('d','aaec','x'*20);a=C(0,1,'Claim');b=C(3,4,'Premise')
    with pytest.raises(CandidateConstructionError,match='scoring_required'):
        build_candidates(doc,Graph((a,b)),config=CandidateConfig(supplement_slots=1))
    pool=build_candidates(doc,Graph((a,b)),config=CandidateConfig(supplement_slots=1),
        relation_score_fn=lambda rs:{r:(.9 if r.sources==(b,) and r.label=='supports' else .1) for r in rs})
    assert len(pool.relations)==2
    assert all(r.sources==(b,) for r in pool.relations)


def test_cdcp_continuity_checked_in_selected_graph_not_candidate_universe():
    doc=InputDocument('d','cdcp','x'*30)
    a=C(0,1,'fact');b=C(3,4,'fact');c=C(6,7,'fact');t=C(9,10,'policy')
    pool=build_candidates(doc,Graph((a,b,c,t)),group_proposals=[GroupProposal((a,c),t)])
    assert R((a,c),t,'reason') in pool.relations
