"""Risk-selection acceptance and evidence-isolation regression tests.

Scores and documents below are explicit constructed decision fixtures; the
solver itself is actually run, with no claimed benchmark performance.
"""
from copy import deepcopy
from dataclasses import replace
import pytest
from argrepair.schema import Component as C,Relation as R,Graph,InputDocument,Document,Scores
from argrepair.candidates import build_candidates,CandidateConfig
from argrepair.io import save_pool,save_scores
from argrepair.policy import select_policy


def policy_fixture(group='policy-one',favor_truth=True):
    doc=InputDocument(group,'aaec','One. Two. Three.',group,'policy')
    a,b,c=C(0,4,'Claim'),C(5,9,'Premise'),C(10,16,'Premise')
    truth=R((b,),a,'supports');wrong=R((c,),a,'attacks')
    gold=Graph((a,b,c),(truth,));initial=Graph((a,b,c),(truth,wrong))
    pool=build_candidates(doc,initial,(initial,),config=CandidateConfig(supplement_slots=100))
    metadata={**pool.metadata,'candidate_scope':'deployment_pruned',
              'oof':{'held_out_source_group':group,'trained_source_groups':['gen-fit'],
                     'span_trained_source_groups':['gen-fit']}}
    pool=replace(pool,metadata=metadata)
    q={r:.1 for r in pool.relations};q[truth]=.9 if favor_truth else .1;q[wrong]=.1 if favor_truth else .9
    scores=Scores({x:.9 for x in pool.components},q,
        {'calibrated':True,'scorer_identity':'explicit-fixture-scorer',
         'fit_source_groups':['scorer-fit'],'calibration_source_groups':['scorer-calibration']})
    row={'doc_id':group,'status':'ok','pool':save_pool(pool),'scores':save_scores(pool,scores)}
    return Document(doc,gold),row


def test_actual_policy_solver_selects_tp_preserving_improvement():
    doc,row=policy_fixture()
    result=select_policy([doc],[row],{'time_limit':1.,'total_time_limit':3.,'lex_call_limit':1},min_documents=1)
    assert result['enabled']
    assert len(result['trials'])==4
    assert all(t['loss_rate']==0 and t['eligible'] for t in result['trials'])
    assert result['selected']['relation']['f1']==100.
    assert result['selected']['kappa_r']==1.


def test_actual_policy_solver_disables_all_tp_losing_options():
    doc,row=policy_fixture(favor_truth=False)
    result=select_policy([doc],[row],{'time_limit':1.,'total_time_limit':3.,'lex_call_limit':1},min_documents=1)
    assert not result['enabled']
    assert result['reason']=='no_configuration_met_development_tp_retention'
    assert len(result['trials'])==8
    assert all(t['loss_rate']==1. for t in result['trials'])


@pytest.mark.parametrize('leak',['generator','span','scorer','calibration'])
def test_policy_rejects_training_exposure_for_each_module(leak):
    doc,row=policy_fixture()
    if leak in ('generator','span'):
        key='trained_source_groups' if leak=='generator' else 'span_trained_source_groups'
        row['pool']['metadata']['oof'][key]=[doc.source_group]
    else:
        key='fit_source_groups' if leak=='scorer' else 'calibration_source_groups'
        row['scores']['metadata'][key]=[doc.source_group]
    with pytest.raises(ValueError,match='used'):
        select_policy([doc],[row],min_documents=100)


@pytest.mark.parametrize('missing',['fit_source_groups','calibration_source_groups'])
def test_policy_requires_nonempty_scorer_source_manifests(missing):
    doc,row=policy_fixture();row['scores']['metadata'].pop(missing)
    with pytest.raises(ValueError,match='source|provenance|identity'):
        select_policy([doc],[row],min_documents=100)


def test_policy_rejects_fit_calibration_overlap_and_test_labels():
    doc,row=policy_fixture()
    row['scores']['metadata']['calibration_source_groups']=['scorer-fit']
    with pytest.raises(ValueError,match='overlap|disjoint|source'):
        select_policy([doc],[row],min_documents=100)
    with pytest.raises(ValueError,match='policy-only'):
        select_policy([replace(doc,input=replace(doc.input,split='test'))],[row],min_documents=100)


def test_policy_rejects_changed_input_and_mixed_scorers():
    doc,row=policy_fixture()
    # Native key cache alone cannot replace matching the complete labeled input.
    with pytest.raises(ValueError,match='identity'):
        select_policy([replace(doc,input=replace(doc.input,text='Changed text'))],[row],min_documents=100)
    other,second=policy_fixture('policy-two');second['scores']['metadata']['scorer_identity']='other-scorer'
    with pytest.raises(ValueError,match='single frozen scorer'):
        select_policy([doc,other],[row,second],min_documents=100)
