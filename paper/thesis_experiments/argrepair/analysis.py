"""Post-inference calibration, risk and cost analysis. Gold is read only here."""
from collections import Counter
import argparse,math
import numpy as np
from .schema import Graph,digest
from .io import load_documents,read_jsonl,load_pool,load_scores,write_json,write_jsonl,Run
from .evaluation import evaluate


def calibration_metrics(probabilities,labels,bins=10):
    if len(probabilities)!=len(labels) or bins<1:raise ValueError('invalid calibration inputs')
    if any(not math.isfinite(q) or not 0<=q<=1 for q in probabilities):raise ValueError('invalid probabilities')
    if not probabilities:return {'observations':0,'brier':None,'ece':None,'bins':[]}
    q=np.asarray(probabilities,dtype=float);y=np.asarray(labels,dtype=float)
    if not np.isin(y,[0,1]).all():raise ValueError('binary labels required')
    index=np.minimum((q*bins).astype(int),bins-1);rows=[];ece=0.
    for i in range(bins):
        m=index==i;n=int(m.sum())
        conf=float(q[m].mean()) if n else None;accuracy=float(y[m].mean()) if n else None
        if n:ece+=n/len(q)*abs(conf-accuracy)
        rows.append({'left':i/bins,'right':(i+1)/bins,'count':n,'mean_probability':conf,'accuracy':accuracy})
    return {'observations':len(q),'brier':float(np.mean((q-y)**2)),'ece':ece,'bins':rows,
            'binning':'ten_equal_width_intervals_last_includes_1' if bins==10 else 'equal_width_last_includes_1'}


def analyze(documents,scored_rows,predictions,method='I1',seed=17):
    summary,counts=evaluate(documents,predictions,method,seed)
    docs={d.doc_id:d for d in documents};pp={p['doc_id']:p for p in predictions};ss={r['doc_id']:r for r in scored_rows}
    if len(ss)!=len(scored_rows) or set(ss)!=set(docs):raise ValueError('scored ids differ from evaluation set')
    probabilities={'component':[],'relation':[]};labels={'component':[],'relation':[]};missing=Counter();rows=[];statuses=Counter()
    for ident,d in sorted(docs.items()):
        r=ss[ident];p=pp[ident];statuses[p.get('repair_status',p.get('status','unknown'))]+=1
        # Use the same invalid-graph handling as the strict evaluator.
        valid_status=next(x['status'] for x in counts if x['doc_id']==ident)
        final=Graph.from_dict(p['graph']) if valid_status not in ('invalid_graph',) and p.get('status','ok') in ('ok','optimal','feasible','no_change','policy_no_repair') else Graph()
        if r['status']=='ok':
            pool=load_pool(r['pool']);scores=load_scores(pool,r['scores'])
            if pool.doc!=d.input:raise ValueError('analysis pool input differs')
            initial=pool.initial;metadata=pool.metadata
            for family,values,truth in [('component',scores.components,set(d.gold.components)),('relation',scores.relations,set(d.gold.relations))]:
                for obj,q in values.items():
                    if q is None:missing[family]+=1
                    else:probabilities[family].append(q);labels[family].append(int(obj in truth))
            nc,nr=len(pool.components),len(pool.relations)
        else:
            initial=Graph.from_dict(r.get('initial',Graph().to_dict()));metadata={};nc=nr=0
        initial_tp=set(initial.relations)&set(d.gold.relations);final_tp=set(final.relations)&set(d.gold.relations)
        rows.append({'doc_id':ident,'source_group':d.source_group,'corpus':d.corpus,'initial_tp':len(initial_tp),'lost_initial_tp':len(initial_tp-set(final.relations)),
                     'new_true_relations':len(final_tp-set(initial.relations)),'initial_relations':len(initial.relations),'final_relations':len(final.relations),
                     'component_net_edits':len(set(initial.components)^set(final.components)),
                     'relation_net_edits':len(set(initial.relations)^set(final.relations)),
                     'candidate_components':nc,'candidate_relations':nr,'candidate_metadata':metadata,
                     'accepted_transactions':len(p.get('ledger',[])),'repair_seconds':p.get('repair_elapsed_seconds',p.get('metadata',{}).get('elapsed_seconds'))})
    tp=sum(r['initial_tp'] for r in rows);lost=sum(r['lost_initial_tp'] for r in rows)
    timings=[r['repair_seconds'] for r in rows if r['repair_seconds'] is not None]
    return {'strict':summary,'calibration':{f:{**calibration_metrics(probabilities[f],labels[f]),'missing_scores':missing[f]} for f in probabilities},
            'initial_true_relation_retention':{'initial_tp':tp,'lost_initial_tp':lost,'loss_rate':lost/tp if tp else None},
            'repair_statuses':dict(statuses),'repair_cpu_wall_seconds':{'observations':len(timings),'mean':float(np.mean(timings)) if timings else None,'p95':float(np.quantile(timings,.95)) if timings else None},
            'cost_scope':'CPU repair wall time only; model phases have separate manifests and token records. No missing timing is replaced by zero.'},rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('gold','scores','predictions','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--method',default='I1');p.add_argument('--seed',type=int,default=17);a=p.parse_args()
    run=Run(a.out,'post-inference-analysis',inputs=[a.gold,a.scores,a.predictions])
    try:
        summary,rows=analyze(load_documents(a.gold),read_jsonl(a.scores),read_jsonl(a.predictions),a.method,a.seed)
        write_json(run.path/'analysis.json',summary);write_jsonl(run.path/'documents.jsonl',rows);run.finish(documents=len(rows))
    except BaseException as exc:run.fail(exc);raise

if __name__=='__main__':main()
