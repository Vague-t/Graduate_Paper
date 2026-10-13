import json
from dataclasses import asdict
import pytest
from argrepair.schema import InputDocument,Component,Relation,Graph,digest
from argrepair.io import write_json,file_hash
from argrepair.regeneration import (BudgetLimits,UsageLedger,BudgetExhausted,RegenerationConfig,
                                    regenerate,validate_reference,verify_matched_predictions)


def case():
    doc=InputDocument('r','aaec','claim premise','group','test')
    a=Component(0,5,'Claim');b=Component(6,13,'Premise')
    initial=Graph((a,b));improved=Graph((a,b),(Relation((b,),a,'supports'),))
    return doc,initial,improved


def reference(tmp_path,doc,limits,checkpoint='weights'):
    records=[{'calls':1,'input_tokens':5,'output_tokens':2,'status':'completed','doc_id':doc.doc_id}]
    actual=tmp_path/'calls.json';write_json(actual,records)
    evidence={'doc_id':doc.doc_id,'input_sha256':digest(doc.to_dict()),'checkpoint_sha256':checkpoint,
              'reference_method':'I1','limits':asdict(limits),'accounting_complete':True,
              'evidence_type':'EXECUTED_CODE_OUTPUT_NOT_HISTORICAL_THESIS_RESULTS',
              'usage_records':records,'source_artifacts':[{'path':str(actual),'sha256':file_hash(actual)}]}
    file=tmp_path/'reference.json';write_json(file,evidence)
    return {**evidence,'evidence_file':str(file),'evidence_sha256':file_hash(file)}


class FakeGenerator:
    def __init__(self,graph,raw=None,fail=False):self.graph=graph;self.raw=raw;self.fail=fail;self.calls=[]
    def input_tokens(self,doc):return 8
    def __call__(self,doc,**kwargs):
        self.calls.append(kwargs)
        if self.fail:raise RuntimeError('injected runtime failure')
        return self.raw if self.raw is not None else json.dumps(self.graph.to_dict()),{'input_tokens':8,'output_tokens':2}


def judge(doc,relation,ledger):
    return ledger.invoke('semantic_verification',5,2,lambda allowed:(1.,{'input_tokens':5,'output_tokens':1}))


def test_real_callbacks_and_same_ceiling_receipt_enable_comparison(tmp_path):
    doc,initial,improved=case();limits=BudgetLimits(4,100,30);ref=reference(tmp_path,doc,limits)
    generator=FakeGenerator(improved)
    row=regenerate(doc,initial,generator,judge,limits,'weights',ref,RegenerationConfig(generation_calls=1))
    assert Graph.from_dict(row['graph'])==improved
    assert row['metadata']['usage']['calls']==2
    assert row['metadata']['usage']['input_tokens']==13
    assert row['metadata']['matched_budget'] and verify_matched_predictions([row])
    assert len(generator.calls)==1


def test_diagnostic_without_reference_is_not_matched():
    doc,initial,improved=case();limits=BudgetLimits(4,100,30)
    row=regenerate(doc,initial,FakeGenerator(improved),judge,limits,'weights',config=RegenerationConfig(generation_calls=1))
    assert not row['metadata']['matched_budget']
    with pytest.raises(ValueError,match='not a verified'):verify_matched_predictions([row])


def test_parse_failure_keeps_document_and_known_costs(tmp_path):
    doc,initial,improved=case();limits=BudgetLimits(4,100,30);ref=reference(tmp_path,doc,limits)
    row=regenerate(doc,initial,FakeGenerator(improved,raw='bad JSON'),judge,limits,'weights',ref,RegenerationConfig(generation_calls=1))
    assert row['status']=='ok' and Graph.from_dict(row['graph'])==initial
    assert row['regeneration_status']=='no_valid_regeneration_retained_G0'
    assert row['metadata']['usage']['calls']==1 and row['metadata']['matched_budget']


def test_model_runtime_failure_has_unknown_usage_not_zero(tmp_path):
    doc,initial,improved=case();limits=BudgetLimits(4,100,30);ref=reference(tmp_path,doc,limits)
    row=regenerate(doc,initial,FakeGenerator(improved,fail=True),judge,limits,'weights',ref,RegenerationConfig(generation_calls=1))
    assert Graph.from_dict(row['graph'])==initial
    assert not row['metadata']['matched_budget']
    assert row['metadata']['usage']['records'][0]['output_tokens'] is None
    assert row['metadata']['usage']['output_tokens']>0


def test_reranking_model_calls_share_the_same_budget(tmp_path):
    doc,initial,improved=case();limits=BudgetLimits(1,100,30);ref=reference(tmp_path,doc,limits)
    row=regenerate(doc,initial,FakeGenerator(improved),judge,limits,'weights',ref,RegenerationConfig(generation_calls=1))
    assert Graph.from_dict(row['graph'])==initial
    assert row['regeneration_status']=='reranking_failed_retained_G0'
    assert row['metadata']['usage']['calls']==1
    assert row['metadata']['matched_budget'] # failed strategy within verified caps, not omitted denominator


def test_budget_preflight_refuses_calls_before_execution():
    ledger=UsageLedger(BudgetLimits(1,3,4));called=[]
    with pytest.raises(BudgetExhausted):ledger.invoke('too_large',4,2,lambda allowed:called.append(allowed))
    assert not called and ledger.calls==0
    assert ledger.invoke('ok',3,9,lambda allowed:('x',{'input_tokens':3,'output_tokens':allowed}))=='x'
    assert ledger.output_tokens==4
    with pytest.raises(BudgetExhausted):ledger.invoke('again',0,1,lambda allowed:None)


def test_reference_must_reproduce_hashed_source_receipts(tmp_path):
    doc,_,_=case();limits=BudgetLimits(4,100,30);ref=reference(tmp_path,doc,limits)
    assert validate_reference(ref,doc,'weights',limits)
    with pytest.raises(ValueError,match='identity/limits'):validate_reference(ref,doc,'different',limits)
    write_json(ref['source_artifacts'][0]['path'],[])
    with pytest.raises(ValueError,match='source artifact drift'):validate_reference(ref,doc,'weights',limits)
