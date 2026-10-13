import copy
from dataclasses import replace
import pytest
from argrepair.schema import Component as C,Relation as R,Graph,InputDocument,Document,digest
from argrepair.io import write_jsonl,load_inputs
from argrepair.data import split_roles
from argrepair.evaluation import evaluate,paired_bootstrap,counts
from argrepair.smoke import fixture


def test_inference_files_reject_all_annotation_fields(tmp_path):
    path=tmp_path/'inputs.jsonl';d=fixture()
    write_jsonl(path,[d.to_dict()])
    with pytest.raises(ValueError,match='undeclared'):load_inputs(path)
    write_jsonl(path,[d.input.to_dict()]);assert load_inputs(path)==[d.input]


def test_roles_and_folds_are_source_group_disjoint_and_preserve_test():
    docs=[]
    for corpus in ('aaec','cdcp'):
        docs.extend(fixture(corpus,'train',f'{corpus}-g{i}') for i in range(30))
        docs.append(fixture(corpus,'test',f'{corpus}-test'))
    role,splits=split_roles(docs)
    assert len(role)==len(docs)
    for corpus in ('aaec','cdcp'):
        rr=[d for d in role if d.corpus==corpus]
        assert {r:sum(d.split==r for d in rr) for r in ('fit','calibration','policy','test')}==dict(fit=24,calibration=3,policy=3,test=1)
        groups=[{d.source_group for d in rr if d.split==r} for r in ('fit','calibration','policy','test')]
        assert all(not groups[i]&groups[j] for i in range(4) for j in range(i))
        for fold in range(3):
            held={d.source_group for d in rr if splits['documents'][d.doc_id]['oof_fold']==fold}
            train={d.source_group for d in rr if d.split!='test' and splits['documents'][d.doc_id]['oof_fold']!=fold}
            assert held and train and not held&train


def test_failed_predictions_stay_in_denominator_and_fp_fn_not_forced_equal():
    d=fixture(); empty={'doc_id':d.doc_id,'status':'generation_failed','graph':Graph().to_dict()}
    summary,rows=evaluate([d],[empty],'I0',17)
    relation=summary['metrics']['cdcp']['relation']
    assert (relation['fp'],relation['fn'],relation['n_pred'],relation['n_gold'])==(0,1,0,1)
    assert summary['failures']=={'generation_failed':1}
    with pytest.raises(ValueError,match='match exactly'):evaluate([d],[],'I0',17)


def test_native_cdcp_partial_sources_are_one_wrong_full_object():
    d=fixture();gold=d.gold.relations[0]
    p=R((gold.sources[0],),gold.target,gold.label)
    assert counts([p],[gold])=={'tp':0,'fp':1,'fn':1}
    assert counts([], [gold])=={'tp':0,'fp':0,'fn':1}
    # FP=FN follows equal predicted/gold cardinality, never an evaluation rule.
    assert counts([p,R((gold.sources[1],),gold.target,gold.label)],[gold])=={'tp':0,'fp':2,'fn':1}


def test_strict_native_types_offsets_direction_and_hash():
    d=fixture('aaec');a,b,c=d.gold.components
    wrong=Graph((replace(a,start=1),b,c),())
    _,rows=evaluate([d],[{'doc_id':d.doc_id,'status':'ok','graph':wrong.to_dict()}],'x',17)
    assert rows[0]['tp']==2 and rows[0]['fp']==1 and rows[0]['fn']==1
    with pytest.raises(ValueError,match='identity'):
        evaluate([d],[{'doc_id':d.doc_id,'status':'ok','graph':d.gold.to_dict(),'input_sha256':'bad'}],'x',17)


def bootstrap_fixture():
    out=[]
    for corpus in ('aaec','cdcp'):
        for seed in (17,29):
            for i in range(3):
                d=fixture(corpus,'test',f'{corpus}-{i}')
                for method,graph in [('A',d.gold),('B',Graph(d.gold.components,()))]:
                    _,rows=evaluate([d],[{'doc_id':d.doc_id,'status':'ok','graph':graph.to_dict()}],method,seed);out.extend(rows)
    return out


def test_paired_bootstrap_resamples_sources_seeds_and_holm_family():
    rows=bootstrap_fixture();contrast=[{'a':'A','b':'B','role':'primary'}]
    result=paired_bootstrap(rows,contrast,100,17)
    assert result==paired_bootstrap(rows,contrast,100,17)
    assert result['primary_family_size']==2
    for r in result['contrasts']:
        assert r['difference_pp']==100 and r['ci95']==[100,100]
        assert 0<r['p']<=r['holm_p']<=1
    broken=copy.deepcopy(rows);broken.pop()
    with pytest.raises(ValueError,match='unpaired'):paired_bootstrap(broken,contrast,100,17)


def test_bootstrap_rejects_duplicate_or_missing_predeclared_comparison():
    rows=bootstrap_fixture()
    with pytest.raises(ValueError,match='duplicate'):paired_bootstrap(rows+[rows[1]],[{'a':'A','b':'B'}],20)
    with pytest.raises(ValueError,match='missing'):paired_bootstrap(rows,[{'a':'A','b':'unrun'}],20)


def test_bootstrap_rejects_impossible_counts_and_unverified_regeneration():
    rows=bootstrap_fixture();bad=copy.deepcopy(rows);bad[0]['fn']=-1
    with pytest.raises(ValueError,match='nonnegative'):paired_bootstrap(bad,[{'a':'A','b':'B'}],20)
    bad=copy.deepcopy(rows);bad[0]['n_gold']=200
    with pytest.raises(ValueError,match='denominator'):paired_bootstrap(bad,[{'a':'A','b':'B'}],20)
    bad=copy.deepcopy(rows);bad[0]['method']='Regenerate'
    with pytest.raises(ValueError,match='matching budget'):paired_bootstrap(bad,[{'a':'A','b':'B'}],20)


def test_formal_evaluation_requires_input_hash():
    d=fixture();row={'doc_id':d.doc_id,'status':'ok','graph':d.gold.to_dict()}
    with pytest.raises(ValueError,match='input identity'):evaluate([d],[row],'x',17,require_input_hash=True)


def test_snapshot_hash_binds_protected_candidate_protocol():
    from argrepair.smoke import diagnostic_pool
    pool=diagnostic_pool(fixture())
    assert replace(pool,protected_components=frozenset()).key!=pool.key
