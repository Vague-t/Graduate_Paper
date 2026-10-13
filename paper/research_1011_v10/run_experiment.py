"""Freeze and run real solver outputs without opening any gold file."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math,platform,sys,time

ROOT=Path(sys.argv[1]).resolve();sys.path.insert(0,str(ROOT))
import repair
from graph_core import endpoints,slot,relation_legal
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')

def dense_load(doc):
    raw=read(ROOT/'scores_dense'/f"{doc['id']}.json")
    assert raw['id']==doc['id'] and raw['model_requested']=='gpt-5.6-luna'
    assert set(raw['component_scores'])==set(doc['components'])
    assert set(raw['relation_scores'])==set(doc['relations'])
    out={};unknown={}
    for axis,key in [('C','component_scores'),('R','relation_scores')]:
        values=raw[key];assert all(v is None or isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in values.values())
        unknown[axis]=sorted(k for k,v in values.items() if v is None)
        # Neutral values cancel for unchanged objects. Any attempted assessment/change
        # touching unknown objects is rejected by the guard below.
        out[axis]={k:.5 if v is None else v for k,v in values.items()}
    return out,unknown

def guarded_transaction(original,unknown):
    def inner(doc,C,R,p,q,remainingC,remainingR,solver):
        D=set(p['D']);B=set(p['B']);Cp=(C-D)|B;rs=doc['relations']
        P={r for r,v in rs.items() if endpoints(v)&(D|B)}|set(p['S_R'])
        expanded={slot(rs[r]) for r in R-P if not relation_legal(doc,rs[r],Cp)}
        P|={r for r,v in rs.items() if slot(v) in expanded}
        if (D|B)&set(unknown['C']) or P&set(unknown['R']):
            return {'proposal':p,'before':{'C':sorted(C),'R':sorted(R)},'candidate_C':sorted(Cp),'accepted_candidate':False,'component_edits':len(C^Cp),'reason':'unassessed_object_guard','solver_calls':[],'evaluation_seconds':0.,'unknown_changed_components':sorted((D|B)&set(unknown['C'])),'unknown_transaction_relations':sorted(P&set(unknown['R']))}
        return original(doc,C,R,p,q,remainingC,remainingR,solver)
    return inner

def run():
    docs=read(ROOT/'candidate_pools.json')['documents']
    baseline={d['id']:repair.score_load(d) for d in docs}
    dense={d['id']:dense_load(d) for d in docs} if ROOT.name=='cdcp_scoring' else {}
    initial_fn=repair.initial;tx_fn=repair.transaction
    common={d['id']:initial_fn(d,baseline[d['id']]) for d in docs}
    output=ROOT/'results/run_001';output.mkdir(exist_ok=False)
    files=[ROOT/x for x in ['protocol.json','protocol_addendum.json','model_execution_manifest.json','sample_manifest.json','pre_prediction_freeze.json','graph_core.py','repair.py','candidate_pools.json']]
    files+=list((ROOT/'scores').glob('*.json'))+list((ROOT/'scores_dense').glob('*.json'))+list((ROOT/'raw_predictions').glob('*.json'))+list((ROOT/'prompts').glob('*'))+list((ROOT/'scoring_inputs').glob('*.json'))
    write(output/'input_freeze.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'before_gold_evaluation':True,'python':sys.version,'platform':platform.platform(),'numpy':repair.np.__version__,'scipy':repair.scipy.__version__,'runner_sha256':sha(Path(__file__)),'hashes':{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}})
    write(output/'common_initial_states.json',{ident:{'graph':g,'ranks':ranks} for ident,(g,ranks) in common.items()})
    summaries=[]
    for d in docs:
        for kind in (['sparse','dense_native'] if dense else ['sparse']):
            q,unknown=(baseline[d['id']],{'C':[],'R':[]}) if kind=='sparse' else dense[d['id']]
            # Reuse precisely the baseline MCR decision, including failure. Dense
            # scoring never gets to choose a more favorable initial graph.
            repair.initial=lambda doc,_q:common[doc['id']]
            repair.transaction=guarded_transaction(tx_fn,unknown) if kind!='sparse' else tx_fn
            for mode in ['BRJ-lite','RelationOnly']:
                st=time.perf_counter();res=repair.run_doc(d,q,mode)
                res.update(score_condition=kind,common_initial_source='baseline_sparse_MCR',unassessed=unknown,total_run_wall_seconds=time.perf_counter()-st)
                if 'corpus' not in res:res['corpus']=d['corpus']
                if d.get('construction_failure'):res['status']='construction_failure';res['construction_failure']=d['construction_failure']
                write(output/f"{d['id']}__{kind}__{mode}.json",res)
                summary={k:res.get(k) for k in ['id','corpus','score_condition','mode','status','solver_seconds','total_run_wall_seconds','component_edits_total','relation_edits_total','stop_reason']}
                summary['commits']=len(res.get('accepted_attempts',[]));summaries.append(summary)
                print(json.dumps(summary),flush=True)
    repair.initial=initial_fn;repair.transaction=tx_fn
    write(output/'summary.json',{'runs':summaries,'ended_at_utc':datetime.now(timezone.utc).isoformat()})
    write(output/'output_freeze.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'before_gold_evaluation':True,'hashes':{p.name:sha(p) for p in sorted(output.glob('*.json'))}})

if __name__=='__main__':run()
