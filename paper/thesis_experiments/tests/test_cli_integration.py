"""Real subprocess CLI training/scoring tests plus boundary regression tests.

Tiny models and constructed documents validate software behavior only. The
chat-group protocol test uses an explicit fake backend, not a model result.
"""
import argparse
import gc
import os
from pathlib import Path
import subprocess
import sys
import weakref
from dataclasses import replace

import pytest
import torch
from argrepair.schema import Component as C, Relation as R, Graph, InputDocument, Document, CandidatePool, digest
from argrepair.candidates import build_candidates, CandidateConfig
from argrepair.io import write_json, write_jsonl, read_json, read_jsonl, save_pool, load_pool, load_scores
from argrepair.cli import _examples, _input_files, main

ROOT=Path(__file__).resolve().parents[1]
torch.set_num_threads(2)


def run_cli(*args):
    result=subprocess.run([sys.executable,'-m','argrepair',*map(str,args)],cwd=ROOT,
        env={**os.environ,'OMP_NUM_THREADS':'2','TOKENIZERS_PARALLELISM':'false'},
        text=True,capture_output=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    return result


def configuration(tmp_path):
    cfg={'encoder':{'backend':'tiny','hidden_size':8,'seed':17},'head':{'hidden':8,'dropout':0},
         'score_training':{'epochs':2,'lr':.02,'batch_size':32},
         'span_training':{'epochs':1,'lr':.01},
         'candidates':{'supplement_slots':2,'preflight_slot_limit':100,'supplement_spans':1,'max_span_tokens':1},
         'model':{'backend':'tiny','hidden_size':16,'layers':1,'attention_heads':2,'head_hidden':8,
                  'lora_rank':2,'device':'cpu','max_context':2048,'max_input_tokens':1024,'max_output_tokens':512},
         'training':{'epochs':1,'max_steps':1,'microbatch_sources':1,'accumulation':1,'max_factors':100},
         'generation':{'candidates':3,'max_new_tokens':4,'temperature':.7},
         'chat':{'device':'cpu','load_in_4bit':False}}
    path=tmp_path/'config.json';write_json(path,cfg)
    return path,cfg


def fixture_document(split,corpus='aaec'):
    doc=InputDocument('d-'+split,corpus,'one two three','group-'+split,split)
    types=('Claim','Premise','Premise') if corpus=='aaec' else ('fact','value','policy')
    a,b,c=C(0,3,types[0]),C(4,7,types[1]),C(8,13,types[2])
    relation=R((b,),a,'supports' if corpus=='aaec' else 'reason')
    return Document(doc,Graph((a,b,c),(relation,)))


def fixture_pool(document):
    initial=document.gold
    wrong=C(0,3,'Premise') if document.corpus=='aaec' else C(0,3,'value')
    alternatives=Graph((wrong,*initial.components[1:]),())
    pool=build_candidates(document.input,initial,(initial,alternatives),config=CandidateConfig(supplement_slots=100))
    metadata={**pool.metadata,'oof':{'held_out_source_group':document.source_group,
                 'trained_source_groups':['excluded-training-group'],
                 'span_trained_source_groups':['excluded-training-group']},
              'natural_distribution':True,'candidate_scope':'unpruned_oof_training_side'}
    return replace(pool,metadata=metadata)


def pool_files(tmp_path,docs):
    files=[]
    for name in ('T0','T1'):
        path=tmp_path/f'{name}-pools.jsonl'
        write_jsonl(path,[{'doc_id':d.doc_id,'status':'ok','pool':save_pool(fixture_pool(d))} for d in docs])
        files.append(path)
    return files


def test_cli_actual_fit_calibration_scoring_keeps_deployment_pool(tmp_path):
    cfg,_=configuration(tmp_path)
    fit,cal,policy=[fixture_document(s) for s in ('fit','calibration','policy')]
    files=pool_files(tmp_path,[fit,cal,policy])
    fit_path=tmp_path/'fit.jsonl';cal_path=tmp_path/'cal.jsonl'
    write_jsonl(fit_path,[fit.to_dict()]);write_jsonl(cal_path,[cal.to_dict()])
    run_cli('scorer-train','--config',cfg,'--data',fit_path,'--pools',*files,'--corpus','aaec','--out',tmp_path/'fit-run')
    run_cli('calibrate','--config',cfg,'--data',cal_path,'--pools',*files,'--scorer',tmp_path/'fit-run/scorer','--out',tmp_path/'cal-run')
    observations=read_jsonl(tmp_path/'cal-run/calibration_pools.jsonl')
    assert len(observations)==2  # T0 and T1 are retained as deployment occurrences.
    assert all(len({r.slot for r in load_pool(row['pool']).relations})==3 for row in observations)
    manifest=read_json(tmp_path/'cal-run/manifest.json')
    assert manifest['documents']==1 and manifest['candidate_observations']==2
    policy_file=tmp_path/'policy-pool.jsonl'
    write_jsonl(policy_file,[{'doc_id':policy.doc_id,'status':'ok','pool':save_pool(fixture_pool(policy))}])
    run_cli('score','--config',cfg,'--pools',policy_file,'--scorer',tmp_path/'cal-run/scorer','--out',tmp_path/'score-run')
    row=read_jsonl(tmp_path/'score-run/scored.jsonl')[0]
    pool=load_pool(row['pool']);scores=load_scores(pool,row['scores'])
    assert len({r.slot for r in pool.relations})==3
    assert pool.metadata['candidate_scope']=='deployment_pruned'
    assert row['scores']['pool_key']==pool.key
    assert scores.metadata['calibrated']
    assert read_json(tmp_path/'score-run/manifest.json')['status']=='completed'


def test_cli_actual_generator_training_identity_seeds_and_manifest(tmp_path):
    cfg,_=configuration(tmp_path)
    document=fixture_document('train');data=tmp_path/'train.jsonl';inputs=tmp_path/'inputs.jsonl'
    write_jsonl(data,[document.to_dict()]);write_jsonl(inputs,[document.input.to_dict()])
    run_cli('train','--config',cfg,'--data',data,'--variant','T0','--seed','29','--out',tmp_path/'training')
    identity=tmp_path/'training/adapter/training_identity.json'
    assert read_json(identity)['source_groups']==[document.source_group]
    checkpoint=tmp_path/'training/adapter/checkpoint'
    run_cli('generate','--config',cfg,'--inputs',inputs,'--adapter',checkpoint,'--out',tmp_path/'generation')
    row=read_jsonl(tmp_path/'generation/generations.jsonl')[0]
    assert len({sample['seed'] for sample in row['samples']})==3
    assert all(sample['usage']['seed']==sample['seed'] for sample in row['samples'])
    manifest=read_json(tmp_path/'generation/manifest.json')
    assert str(checkpoint/'adapter.pt') in manifest['inputs']
    assert str(identity) in manifest['inputs']
    assert manifest['model']['backend']=='tiny'
    assert read_json(tmp_path/'generation/training_identity.json')['seed']==29


def test_examples_preserve_generator_frequency_and_validate_all_sources(tmp_path):
    doc=fixture_document('calibration');data=tmp_path/'data.jsonl';write_jsonl(data,[doc.to_dict()])
    files=pool_files(tmp_path,[doc])
    assert len(_examples(data,files,merge=False))==2
    assert len(_examples(data,files,merge=True))==1
    rows=read_jsonl(files[1]);rows[0]['pool']['metadata']['oof']['span_trained_source_groups']=[doc.source_group]
    write_jsonl(files[1],rows)
    with pytest.raises(ValueError,match='OOF'):_examples(data,files,merge=True)


def test_examples_reject_full_identity_mismatch_and_biased_calibration(tmp_path):
    doc=fixture_document('calibration');data=tmp_path/'data.jsonl';write_jsonl(data,[doc.to_dict()])
    file=pool_files(tmp_path,[doc])[0];rows=read_jsonl(file)
    pool=load_pool(rows[0]['pool'])
    mismatched=replace(pool,doc=replace(pool.doc,source_group='wrong-group'))
    rows[0]['pool']=save_pool(mismatched);write_jsonl(file,rows)
    with pytest.raises(ValueError,match='full input'):_examples(data,[file])
    rows[0]['pool']=save_pool(pool);rows[0]['pool']['metadata']['natural_distribution']=False;write_jsonl(file,rows)
    with pytest.raises(ValueError,match='natural'):_examples(data,[file],merge=False)
    assert not _examples(data,[file],merge=True)[0].natural_distribution


def test_failed_pool_rows_are_bound_and_preserved(tmp_path):
    doc=fixture_document('fit');data=tmp_path/'data.jsonl';write_jsonl(data,[doc.to_dict()])
    file=tmp_path/'failed.jsonl';metadata=fixture_pool(doc).metadata
    row={'doc_id':doc.doc_id,'status':'candidate_failed','input_sha256':digest(doc.input.to_dict()),'metadata':metadata}
    write_jsonl(file,[row]);examples=_examples(data,[file],merge=False)
    assert len(examples)==1 and examples[0].pool.components==()
    row['input_sha256']='incorrect';write_jsonl(file,[row])
    with pytest.raises(ValueError,match='failed candidate input'):_examples(data,[file])


def test_rank_manifest_includes_generation_and_training_identity(tmp_path):
    generations=tmp_path/'generations.jsonl';identity=tmp_path/'training_identity.json'
    write_jsonl(generations,[]);write_json(identity,{'source_groups':['fit']})
    files=_input_files(argparse.Namespace(generations=str(generations)))
    assert generations in files and identity in files


def test_groups_catalog_uses_actual_span_head_before_chat_loading(tmp_path,monkeypatch):
    from argrepair import cli,chat
    from argrepair.proposals import SpanProposer,fit_span_proposer
    from argrepair.scoring import TinyTextEncoder
    cfg,_=configuration(tmp_path);doc=fixture_document('train','cdcp')
    encoder=TinyTextEncoder(8,seed=17);span=SpanProposer(encoder,'cdcp',hidden=8,dropout=0)
    fit_span_proposer(span,[doc],epochs=1);span.save(tmp_path/'span')
    inputs=tmp_path/'inputs.jsonl';ranked=tmp_path/'ranked.jsonl'
    write_jsonl(inputs,[doc.input.to_dict()]);write_jsonl(ranked,[{'doc_id':doc.doc_id,'status':'ok',
        'input_sha256':digest(doc.input.to_dict()),'initial':doc.gold.to_dict(),'candidates':[doc.gold.to_dict()]}])
    references=[];real_encoder=cli._encoder
    def tracked_encoder(config):
        value=real_encoder(config);references.append(weakref.ref(value));return value
    class ExplicitFakeChat:
        def __init__(self,config):
            gc.collect()
            assert references and references[0]() is None  # released before chat residency
            self.records=[];self.identity={'kind':'test_protocol_stub'}
        def __call__(self,prompt):
            assert 'predicted_components' in prompt
            return '{"groups":[]}'
    monkeypatch.setattr(cli,'_encoder',tracked_encoder);monkeypatch.setattr(chat,'HFChatBackend',ExplicitFakeChat)
    monkeypatch.setattr(sys,'argv',['argrepair','groups','--config',str(cfg),'--inputs',str(inputs),
        '--ranked',str(ranked),'--span',str(tmp_path/'span'),'--out',str(tmp_path/'groups')])
    main()
    row=read_jsonl(tmp_path/'groups/groups.jsonl')[0]
    assert row['status']=='ok'
    assert len(row['component_catalog'])>len(doc.gold.components)
    assert row['input_sha256']==digest(doc.input.to_dict())


def test_generate_failure_cannot_reuse_previous_raw_or_usage(tmp_path,monkeypatch):
    from argrepair import modeling
    cfg,_=configuration(tmp_path);doc=fixture_document('test');inputs=tmp_path/'inputs.jsonl'
    write_jsonl(inputs,[doc.input.to_dict()])
    checkpoint=tmp_path/'adapter/checkpoint';checkpoint.mkdir(parents=True)
    write_json(checkpoint.parent/'training_identity.json',{'source_groups':['fit'],'seed':17})
    class ExplicitFailingModel:
        last_generation={}
        calls=0
        def generate(self,document,**kwargs):
            self.calls+=1
            if self.calls==2:raise RuntimeError('injected before generation')
            self.last_generation={'seed':kwargs['seed'],'output_tokens':1}
            return 'unparseable-'+str(self.calls)
        def parameter_manifest(self):return {'backend':'explicit_failure_stub'}
    model=ExplicitFailingModel()
    monkeypatch.setattr(modeling.ExtractionModel,'from_adapter',lambda *args,**kwargs:model)
    monkeypatch.setattr(sys,'argv',['argrepair','generate','--config',str(cfg),'--inputs',str(inputs),
        '--adapter',str(checkpoint),'--out',str(tmp_path/'generated')])
    main()
    samples=read_jsonl(tmp_path/'generated/generations.jsonl')[0]['samples']
    assert samples[0]['raw']=='unparseable-1'
    assert samples[1]['raw']=='' and samples[1]['usage']=={}
    assert samples[2]['raw']=='unparseable-3'


def test_cli_norisk_executes_despite_disabled_policy(tmp_path):
    from argrepair.schema import Scores
    from argrepair.io import save_scores
    doc=fixture_document('test');pool=fixture_pool(doc)
    scores=Scores({c:.9 for c in pool.components},{r:.1 for r in pool.relations},{'fixture':'explicit_constructed_utilities'})
    source=tmp_path/'scores.jsonl';policy=tmp_path/'policy.json'
    write_jsonl(source,[{'doc_id':doc.doc_id,'status':'ok','pool':save_pool(pool),'scores':save_scores(pool,scores)}])
    write_json(policy,{'enabled':False,'repair_config':{'delta':.2,'attempts':2,'lex_call_limit':1,'time_limit':1.}})
    run_cli('repair','--scores',source,'--policy',policy,'--method','NoRisk','--out',tmp_path/'norisk')
    row=read_jsonl(tmp_path/'norisk/predictions.jsonl')[0]
    assert row['repair_status']!='policy_no_repair'
    assert row['metadata']['development_retention_gate'] is False
    assert row['metadata']['requested_method']=='NoRisk'


def test_zero_candidate_fit_fails_explicitly(tmp_path):
    from argrepair.scoring import ObjectScorer,TinyTextEncoder,ScoringExample,fit_scorer
    doc=fixture_document('fit');pool=CandidatePool(doc.input,(),(),Graph())
    with pytest.raises(ValueError,match='no candidate objects'):
        fit_scorer(ObjectScorer(TinyTextEncoder(8),'aaec',hidden=8),[ScoringExample(doc,pool)])
