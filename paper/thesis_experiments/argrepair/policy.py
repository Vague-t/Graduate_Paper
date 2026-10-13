"""Training-side policy selection; test gold cannot enter this interface."""
from dataclasses import replace,asdict
import time
import numpy as np
from .schema import Graph,digest
from .io import load_pool,load_scores
from .evaluation import counts,metrics
from .repair import RepairConfig,repair

def select_policy(documents,scored_rows,base_config=None,min_documents=10):
    if any(d.split!='policy' for d in documents):raise ValueError('risk selection requires policy-only labels')
    docs={d.doc_id:d for d in documents};rows={r['doc_id']:r for r in scored_rows}
    if len(docs)!=len(documents) or len(rows)!=len(scored_rows) or set(rows)!=set(docs):raise ValueError('policy inputs must match exactly')
    identities=set()
    for row in scored_rows:
        doc=docs[row['doc_id']]
        if row['status']!='ok':
            if row.get('input_sha256') and row['input_sha256']!=digest(doc.input.to_dict()):raise ValueError('policy failed-row input identity differs')
            continue
        pool=load_pool(row['pool']);scores=load_scores(pool,row['scores'])
        if pool.doc!=doc.input:raise ValueError('policy input identity differs')
        sources=pool.metadata.get('oof_sources') or [pool.metadata.get('oof',{})]
        for provenance in sources:
            if (provenance.get('held_out_source_group')!=doc.source_group
                    or not provenance.get('trained_source_groups')
                    or not provenance.get('span_trained_source_groups')):raise ValueError('policy requires complete OOF generator/span provenance')
            if doc.source_group in set(provenance['trained_source_groups'])|set(provenance['span_trained_source_groups']):raise ValueError('policy source used for candidate fitting')
        if pool.metadata.get('candidate_scope')!='deployment_pruned':raise ValueError('policy candidates must match deployment pruning')
        if not scores.metadata.get('calibrated'):raise ValueError('policy selection requires calibrated scores')
        fit=set(scores.metadata.get('fit_source_groups',[]));cal=set(scores.metadata.get('calibration_source_groups',[]))
        if not fit or not cal or fit&cal:raise ValueError('policy requires disjoint nonempty scorer fit/calibration provenance')
        if doc.source_group in fit|cal:raise ValueError('policy labels were used for scorer fitting or calibration')
        identities.add(scores.metadata.get('scorer_identity'))
    if len(identities)>1 or (identities and None in identities):raise ValueError('policy scores must share a single frozen scorer')
    valid=[r for r in scored_rows if r['status']=='ok']
    result={'enabled':False,'reason':'insufficient_policy_data','repair_config':base_config or {},'minimum_documents':min_documents,'documents':len(documents),'source_groups':sorted({d.source_group for d in documents}),'input_digest':digest(scored_rows),'trials':[]}
    if len(valid)<min_documents:return result
    baseline_tp=sum(len(set(load_pool(r['pool']).initial.relations)&set(docs[r['doc_id']].gold.relations)) for r in valid)
    if baseline_tp==0:result['reason']='no_initial_true_positives_for_risk_estimate';return result
    for kappa in (1.,.5):
        eligible=[]
        for delta in (.01,.05,.10,.20):
            cfg=RepairConfig(**{**(base_config or {}),'kappa_r':kappa,'delta':delta});lost=0;aggregate={'tp':0,'fp':0,'fn':0};latencies=[]
            for row in scored_rows:
                doc=docs[row['doc_id']]
                if row['status']!='ok':
                    pred=Graph.from_dict(row.get('initial',Graph().to_dict()))
                else:
                    pool=load_pool(row['pool']);scores=load_scores(pool,row['scores'])
                    start=time.monotonic();out=repair(pool,scores,cfg,'I1');latencies.append(time.monotonic()-start);pred=out.graph
                    original_tp=set(pool.initial.relations)&set(doc.gold.relations);lost+=len(original_tp-set(pred.relations))
                for key,value in counts(pred.relations,doc.gold.relations).items():aggregate[key]+=value
            trial={'kappa_r':kappa,'delta':delta,'initial_tp':baseline_tp,'lost_initial_tp':lost,'loss_rate':lost/baseline_tp,'relation':metrics(aggregate),'p95_seconds':float(np.quantile(latencies,.95)) if latencies else 0.,'eligible':lost/baseline_tp<=.05}
            result['trials'].append(trial)
            if trial['eligible']:eligible.append(trial)
        if eligible:
            selected=max(eligible,key=lambda t:(t['relation']['f1'],-t['p95_seconds'],t['delta']))
            result.update(enabled=True,reason='selected_on_policy_split_only',repair_config={**(base_config or {}),'kappa_r':selected['kappa_r'],'delta':selected['delta']},selected=selected)
            break
    if not result['enabled']:result['reason']='no_configuration_met_development_tp_retention'
    return result
