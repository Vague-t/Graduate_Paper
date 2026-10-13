import json
import pytest
import torch
from argrepair.schema import Component as C, Graph, InputDocument, Document
from argrepair.scoring import TinyTextEncoder, TextEncoding
from argrepair.proposals import (SpanProposer, fit_span_proposer, native_boundary_features,
                                 build_group_prompt, parse_group_proposals, propose_groups)

torch.set_num_threads(2)


def document(split='fit'):
    doc=InputDocument('one','aaec','alpha beta','source-one',split)
    return Document(doc,Graph((C(1,4,'Claim'),C(6,10,'Premise')),()))


def test_native_boundary_residuals_support_word_internal_offsets():
    encoding=TextEncoding(torch.tensor([[1.,2.],[3.,4.]]),((0,5),(6,10)),'alpha beta')
    features,covered=native_boundary_features(encoding)
    assert features.shape==(10,4)
    assert not covered[5]
    assert not torch.equal(features[0],features[1])
    assert torch.equal(features[0,:2],features[1,:2])


def test_span_training_and_prediction_no_gold(tmp_path):
    model=SpanProposer(TinyTextEncoder(8),'aaec',hidden=16,dropout=0)
    before=model.boundary_head.weight.detach().clone()
    history=fit_span_proposer(model,[document()],epochs=5,lr=.03)
    assert history[-1]['loss']<history[0]['loss']
    assert not torch.equal(before,model.boundary_head.weight)
    proposals=model.propose(document().input,max_spans=4,max_tokens=4,types_per_span=2)
    assert len(proposals)==4
    assert all(0<=p.start<p.end<=10 and p.token_count<=4 for p in proposals)
    assert all(len(p.type_scores)==2 for p in proposals)
    with pytest.raises(TypeError): model.propose(document())
    path=tmp_path/'span.pt'; model.save(path)
    loaded=SpanProposer.load(path,TinyTextEncoder(8))
    assert loaded.propose(document().input,max_spans=4,max_tokens=4)==proposals


@pytest.mark.parametrize('split',['test','calibration','policy'])
def test_span_fit_rejects_heldout_labels(split):
    with pytest.raises(ValueError,match='forbidden'):
        fit_span_proposer(SpanProposer(TinyTextEncoder(8),'aaec',hidden=8),[document(split)])


def group_input():
    doc=InputDocument('cd','cdcp','one two three four','cg','test')
    cs=(C(0,3,'fact'),C(4,7,'fact'),C(8,13,'value'),C(14,18,'policy'))
    return doc,cs


def test_group_prompt_only_predicted_components_and_complete_sets():
    doc,cs=group_input()
    prompt=build_group_prompt(doc,cs)
    assert 'predicted_components' in prompt and 'at most 64' in prompt
    raw=json.dumps({'groups':[{'sources':['c1','c0'],'target':'c3'},
                             {'sources':['c0','c1'],'target':'c3'},
                             {'sources':['c0'],'target':'c2'}]})
    output=parse_group_proposals(raw,doc,cs)
    assert len(output)==2
    assert any(len(g.sources)==2 for g in output)
    assert all(g.score==0 for g in output)
    assert len(parse_group_proposals(raw,doc,cs,max_proposals=1))==1
    assert propose_groups(doc,cs,lambda _:raw)==output


@pytest.mark.parametrize('record',[
    {'sources':['c0','c0'],'target':'c3'},
    {'sources':['c0'],'target':'c0'},
    {'sources':['invented'],'target':'c3'},
    {'sources':[],'target':'c3'},
    {'sources':['c0'],'target':'c3','score':float('nan')},
    {'sources':['c0'],'target':'c3','score':True},
])
def test_group_parser_rejects_invalid_model_objects(record):
    doc,cs=group_input()
    with pytest.raises(ValueError): parse_group_proposals({'groups':[record]},doc,cs)
