from dataclasses import replace
import pytest
from argrepair.smoke import fixture,diagnostic_pool
from argrepair.schema import Graph,Scores,Relation as R,Component as C
from argrepair.io import save_pool,save_scores
from argrepair.analysis import analyze,calibration_metrics
from argrepair.legacy import select_initial,repair_legacy,LegacyConfig


def test_calibration_endpoints_and_empty_data_are_reported():
    out=calibration_metrics([0.,1.,.25,.75],[0,1,1,0],2)
    assert out['observations']==4 and out['brier']==pytest.approx(.28125)
    assert out['ece']==pytest.approx(.375)
    assert calibration_metrics([],[])['ece'] is None
    with pytest.raises(ValueError):calibration_metrics([float('nan')],[1])


def test_analysis_reports_real_counts_missing_q_and_initial_tp_loss():
    d=fixture();pool=diagnostic_pool(d)
    q=Scores({c:.8 for c in pool.components},{r:None for r in pool.relations})
    pred=Graph(d.gold.components,())
    report,rows=analyze([d],[{'doc_id':d.doc_id,'status':'ok','pool':save_pool(pool),'scores':save_scores(pool,q)}],
                        [{'doc_id':d.doc_id,'status':'ok','graph':pred.to_dict(),'repair_elapsed_seconds':.2}])
    assert report['initial_true_relation_retention']['loss_rate']==1.
    assert report['calibration']['relation']['missing_scores']==len(pool.relations)
    assert report['calibration']['relation']['ece'] is None
    assert report['repair_cpu_wall_seconds']['mean']==.2
    assert report['strict']['metrics']['cdcp']['relation']['fn']==1


def test_i0_is_executed_legacy_repair_instead_of_g0_alias():
    d=fixture('aaec');a,b,c=d.gold.components;bad=R((b,),a,'attacks')
    initial=Graph(d.gold.components,(*d.gold.relations,bad))
    judge=lambda doc,r:float(r!=bad)
    g0,rank=select_initial(d.input,[initial],judge)
    final,ledger,meta=repair_legacy(d.input,g0,[initial],judge,None)
    assert g0==initial and bad not in final.relations
    assert any(l['action']=='RemoveEdge' and l['accepted'] for l in ledger)
    assert meta['identity']=='I0_NATIVE_BR_O_REIMPLEMENTATION'
    assert meta['historical_checkpoint_reproduction'] is False


def test_legacy_missing_semantic_judgment_fails_explicitly():
    d=fixture()
    with pytest.raises(ValueError,match='missing semantic'):select_initial(d.input,[d.gold],lambda d,r:None)
