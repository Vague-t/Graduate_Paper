from pathlib import Path
import sys
import pytest
from argrepair import workflow
from argrepair.io import read_json,write_json,write_jsonl,read_jsonl,save_pool,file_hash
from argrepair.schema import InputDocument,Document,Graph,Component,CandidatePool


def setup_plan(tmp_path,config=None):
    data=tmp_path/'data';data.mkdir();write_json(data/'split_manifest.json',{'split':'test fixture'})
    config_file=tmp_path/'config.json';write_json(config_file,config or {})
    path=Path(workflow.make_plan(data,config_file,tmp_path/'run',corpus='aaec',seeds=(17,)))
    return path,read_json(path)


def test_policy_has_only_three_t1_oof_pools_and_shared_frozen_policy(tmp_path):
    path,plan=setup_plan(tmp_path)
    job=next(j for j in plan['jobs'] if j.get('internal')=='select_policy_pools')
    assert job['policy_generator']=='T1' and len(job['pools'])==3
    assert all('/T1/pools/' in p for p in job['pools'])
    fit=next(j for j in plan['jobs'] if j['id'].endswith('/scorer-fit'))
    assert len([p for p in fit['inputs'] if p.endswith('pools.jsonl')])==6
    policies=[j['argv'][j['argv'].index('--policy')+1] for j in plan['jobs'] if j.get('argv') and '--policy' in j['argv']]
    assert len(set(policies))==1
    assert plan['primary_comparisons_per_corpus']==6
    with pytest.raises(FileExistsError):workflow.make_plan(path.parent.parent/'data',path.parent.parent/'config.json',path.parent)


def test_every_generated_main_cli_argv_parses_without_execution(tmp_path,monkeypatch):
    from argrepair import cli
    _,plan=setup_plan(tmp_path);parsed=[]
    monkeypatch.setattr(cli,'execute',lambda args:parsed.append(args))
    for job in plan['jobs']:
        if 'argv' not in job or job['argv'][1]!='argrepair':continue
        monkeypatch.setattr(sys,'argv',['argrepair',*job['argv'][2:]])
        cli.main()
    assert len(parsed)==len([j for j in plan['jobs'] if 'argv' in j and j['argv'][1]=='argrepair'])


def test_policy_preserves_initial_and_failed_denominators_without_union(tmp_path):
    d=InputDocument('d','aaec','text','source','policy');gold=Graph((Component(0,4,'Claim'),))
    data=tmp_path/'policy.jsonl';write_jsonl(data,[Document(d,gold).to_dict()])
    pool=CandidatePool(d,gold.components,(),gold,metadata={'oof':{'held_out_source_group':'source','trained_source_groups':['other']}})
    source=tmp_path/'t1.jsonl';write_jsonl(source,[{'doc_id':'d','status':'ok','pool':save_pool(pool)}])
    job={'policy_generator':'T1','data':str(data),'pools':[str(source)]}
    rows=workflow._policy_rows(job)
    assert rows[0]['pool']['initial']==gold.to_dict()
    assert rows[0]['pool']['metadata']['policy_scope']=='single_T1_oof_pool_no_family_union'
    with pytest.raises(ValueError,match='multiple policy pools'):workflow._policy_rows({**job,'pools':[str(source),str(source)]})
    write_jsonl(source,[{'doc_id':'d','status':'candidate_failed','initial':gold.to_dict(),'metadata':pool.metadata}])
    rows=workflow._policy_rows(job)
    assert len(rows)==1 and rows[0]['status']=='candidate_failed' and rows[0]['initial']==gold.to_dict()


def one_internal_plan(tmp_path):
    path,plan=setup_plan(tmp_path)
    docs=tmp_path/'docs.jsonl';views=tmp_path/'views.jsonl';target=path.parent/'filtered.jsonl'
    write_jsonl(docs,[{'doc_id':'d'}]);write_jsonl(views,[{'source_doc_id':'d','v':1}])
    plan['jobs']=[{'id':'filter','internal':'filter_views','data':str(docs),'views':str(views),
                   'inputs':[str(docs),str(views)],'output_file':str(target)}]
    write_json(path,plan)
    return path,plan,views,target


def test_resume_verifies_input_and_output_hashes(tmp_path):
    path,plan,views,target=one_internal_plan(tmp_path)
    assert workflow.run_plan(path)==['filter']
    assert workflow.run_plan(path,resume=True)==['filter']
    write_jsonl(views,[{'source_doc_id':'d','v':2}])
    with pytest.raises(ValueError,match='inputs/config/code/plan drift'):workflow.run_plan(path,resume=True)
    write_jsonl(views,[{'source_doc_id':'d','v':1}]);write_jsonl(target,[{'tampered':True}])
    with pytest.raises(ValueError,match='output drift'):workflow.run_plan(path,resume=True)


def test_resume_refuses_config_code_and_failed_state_drift(tmp_path,monkeypatch):
    path,plan,views,target=one_internal_plan(tmp_path)
    write_jsonl(target,[{'existing':'must survive'}])
    with pytest.raises(FileExistsError,match='will not be overwritten'):workflow.run_plan(path,resume=True)
    assert read_jsonl(target)==[{'existing':'must survive'}]
    target.unlink();workflow.run_plan(path)
    original=workflow._code_hashes
    monkeypatch.setattr(workflow,'_code_hashes',lambda:{**original(),'extra.py':'changed'})
    with pytest.raises(ValueError,match='code drift'):workflow.run_plan(path,resume=True)
    monkeypatch.setattr(workflow,'_code_hashes',original)
    write_json(plan['configuration_path'],{'changed':True})
    with pytest.raises(ValueError,match='configuration drift'):workflow.run_plan(path,resume=True)


def test_interrupted_or_failed_internal_job_is_not_overwritten(tmp_path):
    path,plan,views,target=one_internal_plan(tmp_path)
    plan['jobs'][0]['internal']='not_supported';write_json(path,plan)
    with pytest.raises(ValueError,match='unknown internal'):workflow.run_plan(path)
    with pytest.raises(FileExistsError,match='Failed or interrupted'):workflow.run_plan(path,resume=True)


def test_resume_hashes_directory_checkpoint_inputs(tmp_path,monkeypatch):
    path,plan=setup_plan(tmp_path);checkpoint=tmp_path/'adapter';checkpoint.mkdir();weight=checkpoint/'weights.bin';weight.write_bytes(b'first')
    output=path.parent/'stage'
    plan['jobs']=[{'id':'mock','argv':['-m','argrepair','mock'],'output':str(output),'inputs':[str(checkpoint)]}];write_json(path,plan)
    def fake_run(*args,**kwargs):
        output.mkdir();write_json(output/'result.json',{'executed':True})
        write_json(output/'manifest.json',{'status':'completed','outputs':{'result.json':file_hash(output/'result.json')}})
    monkeypatch.setattr(workflow.subprocess,'run',fake_run)
    workflow.run_plan(path);assert workflow.run_plan(path,True)==['mock']
    weight.write_bytes(b'drift')
    with pytest.raises(ValueError,match='inputs/config/code/plan drift'):workflow.run_plan(path,True)


def test_regenerate_is_opt_in_with_pre_statistics_matching_gate(tmp_path):
    path,plan=setup_plan(tmp_path,{'regeneration':{'enabled':True,'reference_budget_manifest':'reference-{corpus}-{seed}.json'}})
    assert plan['primary_comparisons_per_corpus']==7
    job=next(j for j in plan['jobs'] if j.get('internal')=='verify_regeneration')
    assert job['predictions'].endswith('Regenerate/predictions.jsonl')
    assert plan['jobs'].index(job)<next(i for i,j in enumerate(plan['jobs']) if j['id']=='statistics')


def test_generated_analysis_and_regeneration_module_argv_parse(tmp_path,monkeypatch):
    import argparse,importlib
    _,plan=setup_plan(tmp_path,{'regeneration':{'enabled':True,'reference_budget_manifest':'reference-{corpus}-{seed}.json'}})
    original=argparse.ArgumentParser.parse_args
    class Parsed(Exception):pass
    def parse_only(parser,*args,**kwargs):
        original(parser,*args,**kwargs)
        raise Parsed()
    monkeypatch.setattr(argparse.ArgumentParser,'parse_args',parse_only)
    seen=set()
    for job in plan['jobs']:
        if 'argv' not in job or job['argv'][1]=='argrepair':continue
        module=importlib.import_module(job['argv'][1]);seen.add(job['argv'][1])
        monkeypatch.setattr(sys,'argv',[job['argv'][1],*job['argv'][2:]])
        with pytest.raises(Parsed):module.main()
    assert seen=={'argrepair.analysis','argrepair.regeneration'}


def test_experiment_seed_reaches_span_scorer_and_regeneration(tmp_path):
    path,_=setup_plan(tmp_path,{'regeneration':{'enabled':True,'reference_budget_manifest':'reference-{corpus}-{seed}.json'}})
    planned=Path(workflow.make_plan(tmp_path/'data',tmp_path/'config.json',tmp_path/'seed29',corpus='aaec',seeds=(29,)))
    jobs=read_json(planned)['jobs'];checked=[]
    for job in jobs:
        argv=job.get('argv',[])
        if (len(argv)>2 and argv[2] in ('span-train','scorer-train')) or (len(argv)>1 and argv[1]=='argrepair.regeneration'):
            assert '--seed' in argv and argv[argv.index('--seed')+1]=='29'
            checked.append(job['id'])
    assert len(checked)==6 # three fold span heads, final span, scorer, Regenerate
