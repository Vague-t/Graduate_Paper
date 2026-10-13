import json
import pytest
import torch
from argrepair.schema import Component,Relation,Graph,InputDocument,Document,digest
from argrepair.modeling import ModelConfig,ExtractionModel,prefix_gate,serialize_graph,parse_generated_graph
from argrepair.augmentation import transport,AugmentedView,factor_universe
from argrepair.training import (TrainingConfig,compute_source_loss,factor_predictions,supervised_factors,
                                js_divergence,nonempty_group_mean,train)

@pytest.fixture(autouse=True)
def small_threads():
    previous=torch.get_num_threads();torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def source():
    a=Component(0,4,'Claim');b=Component(6,10,'Premise')
    return Document(InputDocument('toy','aaec','Good. Why.','g','train'),Graph((a,b),(Relation((b,),a,'supports'),)))


def model():
    return ExtractionModel(ModelConfig(hidden_size=16,layers=1,attention_heads=2,head_hidden=16,lora_rank=2,
                                       lora_dropout=0,head_dropout=0,max_input_tokens=512,max_output_tokens=512,max_context=1024))


def view_for(doc):
    A=frozenset(doc.gold.components);new,phi=transport(doc,{c:doc.text[c.start:c.end]+' yes' for c in A})
    factors=factor_universe(doc).factors
    return AugmentedView(doc.doc_id,new,phi,A,{c:True for c in A},{f:True for f in factors},factors,A,
                         {'accepted':True,'source_hash':digest(doc.to_dict()),'augmented_hash':digest(new.to_dict()),'reviewer_id':'test-fixture'})


def test_gate_uses_closed_visible_type_and_resets_on_component_end():
    p='{"components":[{"id":"c0","type":"Claim'
    assert not prefix_gate(p,'aaec')
    assert prefix_gate(p+'"','aaec')
    assert prefix_gate(p+'","span":[0,3]','aaec')
    assert not prefix_gate(p+'","span":[0,3]}','aaec')
    assert not prefix_gate(p+'","span":[0,3]}],"relations":[','aaec')
    assert not prefix_gate('{"components":[{"id":"Claim","type":"Premise","span":[','aaec')
    assert prefix_gate('{"components":[{"id":"c","type":"policy","span":[','cdcp')


def test_parse_generation_preserves_native_hyperedge_and_rejects_bad_keys():
    d=source();assert parse_generated_graph(serialize_graph(d.gold),d.input)==d.gold
    broken=serialize_graph(d.gold).replace('"span":[0,4]','"span":[0,40]')
    with pytest.raises(ValueError,match='invalid generated graph'):parse_generated_graph(broken,d.input)
    with pytest.raises(ValueError):parse_generated_graph(serialize_graph(d.gold)+'junk',d.input)


def test_input_representation_is_answer_independent_and_input_conclusion_grad_zero():
    m=model();d=source();m.eval()
    h,offsets,end=m.input_hidden(d.text,d.corpus)
    # Explicit teacher-forced continuations do not change any preceding input
    # representation, and input-only API has no answer argument at all.
    encoded=m.encode_input(d.text,d.corpus)
    a=m.tokenizer.encode('totally different answer')
    result,prefix=m._forward(encoded,a)
    assert torch.allclose(h,result.hidden_states[-1][0,prefix:prefix+len(encoded.ids)],atol=1e-6)
    assert len(offsets)==len(h)
    pred=factor_predictions(m,d,factor_universe(d).auditable)
    supervised_factors(pred,d.corpus,d.gold.components,factor_universe(d).auditable).backward()
    assert any(p.grad is not None and p.grad.abs().sum()>0 for n,p in m.named_parameters() if 'global_B' in n)
    assert all(p.grad is None or p.grad.abs().sum()==0 for n,p in m.named_parameters() if 'conclusion_' in n)
    assert all(p.grad is None for p in m.backbone.parameters() if not p.requires_grad)


def test_generation_updates_conclusion_branch_with_frozen_base():
    m=model();loss,_=m.generation_loss(source());loss.backward()
    assert any(p.grad is not None and p.grad.abs().sum()>0 for n,p in m.named_parameters() if 'conclusion_B' in n)
    assert all(p.grad is None for p in m.backbone.parameters() if not p.requires_grad)


def test_js_has_gradients_on_both_sides_and_group_normalization_is_nonempty():
    a=torch.tensor([.8,-.2],requires_grad=True);b=torch.tensor([-.3,.4],requires_grad=True)
    js_divergence(a,b).backward();assert a.grad.abs().sum()>0 and b.grad.abs().sum()>0
    zero=torch.tensor(0.)
    assert nonempty_group_mean([torch.tensor(4.)],[],zero)==4
    assert nonempty_group_mean([torch.tensor(4.)],[torch.tensor(2.),torch.tensor(2.)],zero)==3
    assert nonempty_group_mean([],[],zero)==0


def test_source_normalization_duplicate_view_does_not_double_pair_weight():
    m=model();m.eval();d=source();v=view_for(d)
    _,one=compute_source_loss(m,d,[v],TrainingConfig())
    _,two=compute_source_loss(m,d,[v,v],TrainingConfig())
    assert one['component_js']==pytest.approx(two['component_js'])
    assert one['relation_js']==pytest.approx(two['relation_js'])
    original=factor_predictions(m,d,factor_universe(d).auditable)
    old=supervised_factors(original,d.corpus,d.gold.components,factor_universe(d).auditable).item()
    assert two['head_supervision']==pytest.approx((4*one['head_supervision']-old)/3,rel=1e-5)


@pytest.mark.parametrize('variant',['T0','Heads','NoPair','CompPair','T1'])
def test_all_variants_real_backward_and_masks(variant):
    m=model();d=source();v=view_for(d)
    # Empty reliable relation set is a legal component-only accepted view.
    v.relation_mask={f:False for f in v.factors}
    loss,log=compute_source_loss(m,d,[v],TrainingConfig(variant=variant));loss.backward()
    assert torch.isfinite(loss) and log['relation_js']==0
    if variant in {'T0','Heads'}:assert log['accepted_views']==0
    if variant=='T0':assert log['head_supervision']==0
    if variant in {'T0','Heads','NoPair'}:assert log['component_js']==0


def test_train_save_reload_actual_update_and_partial_batch(tmp_path):
    m=model();d=source();before={n:p.detach().clone() for n,p in m.named_parameters() if p.requires_grad}
    manifest=train(m,[d],{},TrainingConfig(variant='T0',epochs=1,accumulation=8),tmp_path)
    assert manifest['status']=='COMPLETED' and manifest['steps_completed']==1
    record=json.loads((tmp_path/'training_log.jsonl').read_text());assert record['actual_source_count']==1
    assert any(not torch.equal(before[n],p) for n,p in m.named_parameters() if n in before)
    loaded=ExtractionModel.from_adapter(tmp_path/'checkpoint');m.eval();loaded.eval()
    assert all(torch.equal(v,loaded.state_dict()[k]) for k,v in m.state_dict().items())
    assert loaded.generation_loss(d)[0].item()==pytest.approx(m.generation_loss(d)[0].item())


def test_soft_prompt_only_on_cue_and_native_offsets_unchanged():
    m=model();a=m.encode_input('therefore X','aaec');b=m.encode_input('thereforex X','aaec')
    assert a.prompt_enabled and not b.prompt_enabled
    h,offsets,_=m.input_hidden('因此 therefore X','aaec')
    assert len(h)==len(offsets)
    assert any(start==0 and end==1 for start,end in offsets)


def test_truncation_and_mismatched_view_fail_explicitly():
    m=model()
    with pytest.raises(ValueError,match='overflow'):m.encode_input('x'*1000,'aaec')
    d=source();v=view_for(d);v.audit['source_hash']='bad'
    with pytest.raises(ValueError,match='checksum'):compute_source_loss(m,d,[v],TrainingConfig())


def test_hf_qwen_checkpointed_two_view_backward_save_load_and_generation(tmp_path):
    """Actual local HF architecture execution; randomly initialized, not pretrained."""
    from transformers import Qwen2Config,Qwen2ForCausalLM,PreTrainedTokenizerFast
    from tokenizers import Tokenizer,models,trainers,pre_tokenizers,decoders
    folder=tmp_path/'random-mini-qwen';folder.mkdir()
    tokenizer=Tokenizer(models.BPE(unk_token='<unk>'))
    tokenizer.pre_tokenizer=pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder=decoders.ByteLevel()
    trainer=trainers.BpeTrainer(vocab_size=300,special_tokens=['<pad>','<eos>','<unk>'],initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    tokenizer.train_from_iterator(['Claim Premise Good. Why. Extract argument graph '+serialize_graph(source().gold)],trainer)
    fast=PreTrainedTokenizerFast(tokenizer_object=tokenizer,eos_token='<eos>',pad_token='<pad>',unk_token='<unk>')
    fast.chat_template="{% for message in messages %}{{ message['role'] + ': ' + message['content'] + '\\n' }}{% endfor %}{% if add_generation_prompt %}{{ 'assistant: ' }}{% endif %}"
    fast.save_pretrained(folder)
    backbone=Qwen2ForCausalLM(Qwen2Config(vocab_size=len(fast),hidden_size=16,intermediate_size=32,num_hidden_layers=1,
                                        num_attention_heads=2,num_key_value_heads=1,max_position_embeddings=2048,
                                        eos_token_id=fast.eos_token_id,pad_token_id=fast.pad_token_id))
    backbone.save_pretrained(folder)
    m=ExtractionModel(ModelConfig(backend='hf',model_name=str(folder),local_files_only=True,hidden_size=16,head_hidden=16,
                                  lora_rank=2,head_dropout=0,lora_dropout=0,gradient_checkpointing=True,
                                  max_input_tokens=1536,max_output_tokens=512,max_context=2048))
    d=source();view=view_for(d);loss,log=compute_source_loss(m,d,[view],TrainingConfig())
    loss.backward()
    assert torch.isfinite(loss) and log['accepted_views']==1
    assert any(p.grad is not None and p.grad.abs().sum()>0 for n,p in m.named_parameters() if 'global_B' in n)
    assert any(p.grad is not None and p.grad.abs().sum()>0 for n,p in m.named_parameters() if 'conclusion_B' in n)
    assert all(p.grad is None for p in m.backbone.parameters() if not p.requires_grad)
    m.save_adapter(tmp_path/'adapter');loaded=ExtractionModel.from_adapter(tmp_path/'adapter');m.eval();loaded.eval()
    assert torch.allclose(m.input_hidden(d.text,d.corpus)[0],loaded.input_hidden(d.text,d.corpus)[0],atol=1e-7)
    raw=loaded.generate(d.input,max_new_tokens=3)
    assert isinstance(raw,str) and loaded.last_generation['output_tokens']<=3
    assert loaded.last_generation['stop_reason'] in {'eos','max_new_tokens'}
