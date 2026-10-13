import math
import pytest
import torch
from argrepair.schema import Component as C, Relation as R, Graph, InputDocument, Document, CandidatePool
from argrepair.scoring import (TinyTextEncoder, TextEncoding, ObjectScorer, ScoringExample,
    component_target, relation_target, fit_scorer, fit_calibrators, PlattCalibrator)

torch.set_num_threads(2)


def example(split='fit', group='g1', corpus='cdcp'):
    doc=InputDocument('d-'+group,corpus,'alpha beta gamma',group,split)
    a,b,c=C(0,5,'fact'),C(6,10,'value'),C(11,16,'policy')
    h=R((a,b),c,'reason')
    wrong=C(1,5,'fact'); badtype=C(0,5,'value')
    cs=(a,b,c,wrong,badtype)
    rs=(h,R((a,),c,'reason'),R((a,b),c,'evidence'),R((wrong,b),c,'reason'),R((badtype,b),c,'reason'))
    gold=Graph((a,b,c),(h,))
    pool=CandidatePool(doc,cs,rs,gold)
    return ScoringExample(Document(doc,gold),pool)


def test_complete_identity_labels_and_semantic_subset():
    ex=example(); gold=ex.document.gold
    assert component_target((0,5),gold,'cdcp')==3
    assert component_target((1,5),gold,'cdcp')==0
    assert [relation_target(r,gold) for r in ex.pool.relations]==[1,0,0,0,0]


def test_native_word_internal_offsets_are_not_merged():
    enc=TextEncoding(torch.tensor([[1.,2.],[3.,4.]]),((0,5),(6,10)),'alpha beta')
    assert enc.span_indices(1,4)==[0]
    assert not torch.equal(enc.span(1,4),enc.span(0,5))
    with pytest.raises(ValueError): enc.span(5,6)


def test_input_encoder_rejects_annotated_document():
    with pytest.raises(TypeError): TinyTextEncoder().encode(example().document)


def test_fitting_is_real_and_encoder_stays_frozen():
    ex=example(); enc=TinyTextEncoder(12); scorer=ObjectScorer(enc,'cdcp',hidden=16,dropout=0)
    before=scorer.relation_head[0].weight.detach().clone()
    encoded_before=enc.embedding.weight.detach().clone()
    history=fit_scorer(scorer,[ex],epochs=5,lr=.03)
    assert all(math.isfinite(row['loss']) for row in history)
    assert history[-1]['loss']<history[0]['loss']
    assert not torch.equal(before,scorer.relation_head[0].weight)
    assert torch.equal(encoded_before,enc.embedding.weight)
    assert all(p.grad is None for p in enc.parameters())


@pytest.mark.parametrize('split',['test','calibration','policy','dev',''])
def test_fitting_rejects_forbidden_labels(split):
    with pytest.raises(ValueError,match='forbidden'):
        fit_scorer(ObjectScorer(TinyTextEncoder(8),'cdcp',hidden=8),[example(split)])


def test_oof_provenance_is_checked():
    scorer=ObjectScorer(TinyTextEncoder(8),'cdcp',hidden=8)
    ex=example()
    with pytest.raises(ValueError,match='provenance'): fit_scorer(scorer,[ex],require_oof=True)
    ex.pool.metadata['oof']={'held_out_source_group':'g1','trained_source_groups':['g1']}
    with pytest.raises(ValueError,match='held-out'): fit_scorer(scorer,[ex],require_oof=True)


def test_calibration_has_disjoint_natural_examples():
    scorer=ObjectScorer(TinyTextEncoder(8),'cdcp',hidden=8)
    fit_scorer(scorer,[example()],epochs=1)
    with pytest.raises(ValueError,match='overlap'): fit_calibrators(scorer,[example('calibration','g1')])
    with pytest.raises(ValueError,match='forbidden'): fit_calibrators(scorer,[example('test','g2')])
    ex=example('calibration','g2')
    biased=ScoringExample(ex.document,ex.pool,natural_distribution=False)
    with pytest.raises(ValueError,match='natural'): fit_calibrators(scorer,[biased])
    result=fit_calibrators(scorer,[ex])
    assert all(v['fitted'] for v in result.values())
    assert result['component']['observations']==5
    assert result['relation']['observations']==5


def test_missing_preserved_and_cache_immutable():
    ex=example(); invalid=C(100,101,'fact')
    pool=CandidatePool(ex.pool.doc,(*ex.pool.components,invalid),ex.pool.relations,ex.pool.initial)
    scorer=ObjectScorer(TinyTextEncoder(8),'cdcp',hidden=8)
    scores=scorer.score(pool)
    assert scores.components[invalid] is None
    assert scores is scorer.score(pool)
    with pytest.raises(TypeError): scores.components[invalid]=0.
    with pytest.raises(TypeError): scores.metadata['changed']=True
    assert all(0<v<1 for v in scores.relations.values())
    assert not scores.metadata['calibrated']


def test_nonfinite_raw_score_remains_missing():
    ex=example(); scorer=ObjectScorer(TinyTextEncoder(8),'cdcp',hidden=8)
    with torch.no_grad(): scorer.relation_head[-1].bias.fill_(float('nan'))
    assert all(x is None for x in scorer.score(ex.pool).relations.values())


def test_save_load_binds_exact_encoder_and_scores(tmp_path):
    ex=example(); scorer=ObjectScorer(TinyTextEncoder(8,seed=2),'cdcp',hidden=8,dropout=0)
    fit_scorer(scorer,[ex],epochs=1)
    fit_calibrators(scorer,[example('calibration','g2')])
    path=tmp_path/'scorer.pt'; scorer.save(path)
    loaded=ObjectScorer.load(path,TinyTextEncoder(8,seed=2))
    assert dict(loaded.score(ex.pool).relations)==dict(scorer.score(ex.pool).relations)
    assert loaded.model_identity()==scorer.model_identity()
    with pytest.raises(ValueError,match='identity'): ObjectScorer.load(path,TinyTextEncoder(8,seed=3))


def test_platt_requires_both_classes_and_preserves_order():
    with pytest.raises(ValueError,match='both'): PlattCalibrator().fit([0,1],[1,1])
    fitted=PlattCalibrator().fit([-2,-1,1,2],[0,0,1,1])
    assert fitted(-2)<fitted(2)


def test_hf_local_encoder_uses_real_transformer_and_native_offsets(tmp_path):
    from transformers import BertConfig, BertModel, BertTokenizerFast
    from argrepair.scoring import HFTextEncoder
    vocab=tmp_path/'vocab.txt'
    vocab.write_text('[PAD]\n[UNK]\n[CLS]\n[SEP]\n[MASK]\nalpha\nbeta\ngamma\n')
    tokenizer=BertTokenizerFast(vocab_file=str(vocab),do_lower_case=False)
    tokenizer.save_pretrained(tmp_path)
    with torch.random.fork_rng():
        torch.manual_seed(4)
        BertModel(BertConfig(vocab_size=len(tokenizer),hidden_size=16,num_hidden_layers=1,
                             num_attention_heads=2,intermediate_size=32)).save_pretrained(tmp_path)
    encoder=HFTextEncoder(str(tmp_path),local_files_only=True,max_tokens=32)
    document=InputDocument('hf-debug','aaec','alpha beta',split='test')
    encoded=encoder.encode(document)
    assert encoded.hidden.shape[-1]==16
    assert encoded.span_indices(1,4)==encoded.span_indices(0,5)
    assert not torch.equal(encoded.span(1,4),encoded.span(0,5))
    assert encoder.identity['local_weights_sha256']
    assert all(not p.requires_grad for p in encoder.parameters())
    scorer=ObjectScorer(encoder,'aaec',hidden=8,dropout=0)
    c=C(1,4,'Claim')
    scores=scorer.score(CandidatePool(document,(c,),(),Graph()))
    assert 0<scores.components[c]<1


def test_calibration_pruning_matches_deployment_and_is_calibration_invariant():
    from argrepair.candidates import build_candidates, CandidateConfig
    from argrepair.scoring import prune_pool_for_calibration
    doc=InputDocument('p','aaec','one two three','pg','calibration')
    a,b,c=C(0,3,'Claim'),C(4,7,'Premise'),C(8,13,'Premise')
    initial=Graph((a,b,c),(R((b,),a,'supports'),))
    raw=build_candidates(doc,initial,(initial,),config=CandidateConfig(supplement_slots=100))
    scorer=ObjectScorer(TinyTextEncoder(8),'aaec',hidden=8)
    before=scorer.model_identity(False)
    pruned=prune_pool_for_calibration(scorer,raw,supplement_slots=2)
    scorer.calibrators={'component':PlattCalibrator(20,50,True),'relation':PlattCalibrator(50,100,True)}
    assert scorer.model_identity(False)==before
    callback=lambda rels:scorer.score_relations_for_pruning(doc,raw.components,rels)
    deployed=build_candidates(doc,initial,(initial,),config=CandidateConfig(supplement_slots=2),relation_score_fn=callback)
    assert pruned.components==deployed.components
    assert pruned.relations==deployed.relations
    assert set(initial.relations)<=set(pruned.relations)
    assert len({r.slot for r in pruned.relations})==3  # protected 1 + supplementary 2
    assert pruned.metadata['calibration_pruning']['labels_accessed'] is False


def test_calibration_rejects_unpruned_or_biased_metadata():
    scorer=ObjectScorer(TinyTextEncoder(8),'cdcp',hidden=8)
    ex=example('calibration','g2')
    ex.pool.metadata['candidate_scope']='unpruned_oof_training_side'
    with pytest.raises(ValueError,match='deployment pruning'): fit_calibrators(scorer,[ex])
    ex.pool.metadata['candidate_scope']='deployment_pruned'
    ex.pool.metadata['natural_distribution']=False
    with pytest.raises(ValueError,match='natural'): fit_calibrators(scorer,[ex])


def test_oof_checks_every_generator_and_span_source():
    scorer=ObjectScorer(TinyTextEncoder(8),'cdcp',hidden=8)
    ex=example()
    ex.pool.metadata['oof_sources']=[
        {'held_out_source_group':'g1','trained_source_groups':['g2']},
        {'held_out_source_group':'g1','trained_source_groups':['g3'],'span_trained_source_groups':['g1']}]
    with pytest.raises(ValueError,match='span fitting'): fit_scorer(scorer,[ex],require_oof=True)
