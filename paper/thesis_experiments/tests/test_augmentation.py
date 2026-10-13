import pytest
from argrepair.schema import Component,Relation,Graph,InputDocument,Document
from argrepair.augmentation import (factor_universe,select_rewrite_set,transport,review_view,
                                     ViewRejected,AugmentedView)


def aaec():
    text='Claim. Reason one. Reason two. Other.'
    a=Component(0,6,'Claim');b=Component(7,18,'Premise');c=Component(19,30,'Premise');d=Component(31,37,'Premise')
    return Document(InputDocument('a','aaec',text,'g','train'),Graph((a,b,c,d),(Relation((b,),a,'supports'),Relation((c,),b,'supports'))))


def test_native_transport_moves_read_only_offsets_and_preserves_complete_relation():
    # Also checks non-ASCII character offsets and boundaries inside a token.
    text='中abc def.';a=Component(1,3,'Claim');b=Component(5,8,'Premise')
    doc=Document(InputDocument('unicode','aaec',text,'g','train'),Graph((a,b),(Relation((b,),a,'supports'),)))
    changed,phi=transport(doc,{a:'longer'})
    assert changed.text=='中longerc def.'
    assert phi[a].key==(1,7,'Claim') and phi[b].key==(9,12,'Premise')
    assert changed.text[phi[b].start:phi[b].end]=='def'
    assert changed.gold.relations[0].sources==(phi[b],)
    assert changed.gold.relations[0].target==phi[a]


def test_semantic_unknown_is_true_subset_only_and_gold_positive_wins():
    a=Component(0,1,'fact');b=Component(2,3,'fact');c=Component(4,5,'policy')
    graph=Graph((a,b,c),(Relation((a,b),c,'reason'),Relation((a,),c,'evidence')))
    doc=Document(InputDocument('cdcp','cdcp','A B C','g','train'),graph)
    universe=factor_universe(doc)
    assert {(f.sources,f.target) for f in universe.unknown}=={((b,),c)}
    assert any(f.sources==(a,) and f.target==c and f.label=='evidence' for f in universe.auditable)
    assert any(f.sources==(a,b) and f.target==c and f.label=='reason' for f in universe.auditable)


def test_long_gold_hyperedge_not_cut_by_none_budget():
    cs=tuple(Component(i*2,i*2+1,'fact') for i in range(5));target=Component(10,11,'policy')
    doc=Document(InputDocument('long','cdcp','A B C D E T','g','train'),Graph((*cs,target),(Relation(cs,target,'reason'),)))
    u=factor_universe(doc,max_sources=3)
    assert any(f.sources==cs and f.label=='reason' for f in u.auditable)
    selected,metadata=select_rewrite_set(doc)
    assert selected==frozenset((*cs,target))


def _reviewer_for(doc,changed,phi,unknown_relation=False):
    """Deterministic *test fixture* classifier, never used for real acceptance."""
    mapping={doc.text:doc,changed.text:changed}
    def review(request):
        assert 'expected_label' not in request and 'graph' not in request
        if request['task']=='component_meaning':return 'SAME'
        d=mapping[request['text']]
        if request['task']=='component_type':
            assert set(request['span'])=={'start','end'}
            return next(c.label for c in d.gold.components if c.start==request['span']['start'] and c.end==request['span']['end'])
        assert all(set(s)=={'start','end'} for s in request['sources'])
        if unknown_relation:return 'UNKNOWN'
        sources=tuple((s['start'],s['end']) for s in request['sources']);target=(request['target']['start'],request['target']['end'])
        return next((r.label for r in d.gold.relations if tuple((c.start,c.end) for c in r.sources)==sources and (r.target.start,r.target.end)==target),'NONE')
    return review


def test_factor_unknown_masks_relation_without_losing_components_or_relabeling():
    doc=aaec();A=frozenset(doc.gold.components[:2]);replacement={c:doc.text[c.start:c.end]+'!' for c in A}
    changed,phi=transport(doc,replacement)
    reviewer=_reviewer_for(doc,changed,phi,unknown_relation=True)
    view=review_view(doc,replacement,reviewer,rewrite_set=A,reviewer_id='fixture-only')
    assert view.audit['accepted'] and all(view.component_mask.values())
    assert not any(view.relation_mask.values())
    assert any(f.label=='supports' for f in view.factors)  # UNKNOWN never -> NONE
    assert view.alignment_components==frozenset(doc.gold.components[:3])
    with pytest.raises(ViewRejected,match='full_filter_relation'):
        review_view(doc,replacement,reviewer,rewrite_set=A,mode='full')
    assert AugmentedView.from_dict(view.to_dict()).to_dict()==view.to_dict()


def test_all_affected_positives_required_before_any_relation_supervision():
    doc=aaec();A=frozenset(doc.gold.components[:2]);replacement={c:doc.text[c.start:c.end]+'!' for c in A}
    changed,phi=transport(doc,replacement);reviewer=_reviewer_for(doc,changed,phi)
    view=review_view(doc,replacement,reviewer,rewrite_set=A,max_relation_reviews=1)
    assert view.audit['relation_skip']=='positive_coverage_resource_limit'
    assert not any(view.relation_mask.values())
    assert not any(row['request']['task']=='relation_state' for row in view.audit['raw'])
    with pytest.raises(ViewRejected,match='full_domain_review_resource_limit'):
        review_view(doc,replacement,reviewer,rewrite_set=A,mode='full',max_relation_reviews=1)


def test_rewritten_unknown_rejects_and_test_data_never_augmented():
    doc=aaec();A=select_rewrite_set(doc)[0];replacements={c:doc.text[c.start:c.end] for c in A}
    with pytest.raises(ViewRejected,match='component_changed_or_unknown'):
        review_view(doc,replacements,lambda request:'UNKNOWN')
    held=Document(InputDocument('a','aaec',doc.text,'g','test'),doc.gold)
    with pytest.raises(ValueError,match='train-only'):
        review_view(held,replacements,lambda request:'SAME')


def test_finite_universe_refuses_resource_clipping():
    with pytest.raises(ValueError,match='resource_limit'):factor_universe(aaec(),max_factors=2)


def test_read_only_component_semantic_drift_rejects_whole_view():
    doc=aaec();A=frozenset(doc.gold.components[:1]);replacement={c:doc.text[c.start:c.end]+'!' for c in A}
    changed,phi=transport(doc,replacement);base=_reviewer_for(doc,changed,phi)
    readonly=doc.gold.components[1]
    def reviewer(request):
        if request['task']=='component_meaning' and request['original_span']['start']==readonly.start:return 'CHANGED'
        return base(request)
    with pytest.raises(ViewRejected,match='component_changed_or_unknown'):
        review_view(doc,replacement,reviewer,rewrite_set=A)


def test_generation_conditions_are_lossless_and_not_reused_for_blind_review():
    from argrepair.augmentation import build_generation_payload
    a=Component(0,1,'fact');b=Component(2,3,'fact');c=Component(4,5,'policy');d=Component(6,7,'value')
    doc=Document(InputDocument('conditions','cdcp','A B C D','g','train'),Graph((a,b,c,d),(Relation((a,b),c,'reason'),)))
    A=frozenset((a,c));payload=build_generation_payload(doc,A)
    assert set(payload['slots'])=={'c0','c2'}
    assert set(payload['read_only_endpoints'])=={'c1','c3'}
    assert payload['read_only_endpoints']['c1']['type']=='fact'
    assert payload['positive_relations']==[{'sources':['c0','c1'],'target':'c2','type':'reason'}]
    unknown={(tuple(x['sources']),x['target']) for x in payload['semantic_unknown_exceptions']}
    assert unknown=={(('c0',),'c2'),(('c1',),'c2')}
    cs=doc.gold.components;u=factor_universe(doc)
    slots={(tuple(f'c{cs.index(c)}' for c in f.sources),f'c{cs.index(f.target)}') for f in u.factors}
    positive={(tuple(x['sources']),x['target']) for x in payload['positive_relations']}
    none=slots-positive-unknown
    assert len(none)==sum(f.label=='NONE' for f in u.factors)
    assert payload['influence_domain']['factors']==sum(bool(f.endpoints&A) for f in u.auditable)
    replacements={component:doc.text[component.start:component.end]+'!' for component in A}
    changed,phi=transport(doc,replacements);classifier=_reviewer_for(doc,changed,phi)
    requests=[]
    def review(request):
        requests.append(request)
        assert not ({'positive_relations','semantic_unknown_exceptions','slots','read_only_endpoints','native_attributes'}&set(request))
        return classifier(request)
    view=review_view(doc,replacements,review,rewrite_set=A)
    assert view.audit['accepted'] and requests
    assert doc.gold.to_dict() not in requests


def test_transport_preserves_native_attributes_without_training_a_new_label():
    from argrepair.augmentation import build_generation_payload
    doc=aaec();old=doc.gold.components[1]
    attribute={'component':old.to_dict(),'name':'Stance','value':'For'}
    doc=Document(doc.input,doc.gold,(attribute,))
    changed,phi=transport(doc,{doc.gold.components[0]:'Longer claim.'})
    assert doc.annotations==(attribute,)
    assert changed.annotations==({'component':phi[old].to_dict(),'name':'Stance','value':'For'},)
    assert changed.gold.components[1].label=='Premise'
    assert Document.from_dict(changed.to_dict()).annotations==changed.annotations
    payload=build_generation_payload(doc,frozenset((doc.gold.components[0],)))
    assert payload['read_only_endpoints']['c1']['native_attributes']==[{'name':'Stance','value':'For'}]
