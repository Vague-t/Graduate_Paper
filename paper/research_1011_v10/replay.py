"""Replay frozen scores; never invoke a model and never replace original traces."""
from pathlib import Path
import importlib.util,json,sys
root=Path(sys.argv[1]).resolve();base=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('frozen_runner',base/'run_experiment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
read=m.read;repair=m.repair
docs=read(root/'candidate_pools.json')['documents'];main=root/'results/run_001'
for p,h in read(main/'input_freeze.json')['hashes'].items():assert m.sha(root/p)==h
for p,h in read(main/'output_freeze.json')['hashes'].items():assert m.sha(main/p)==h
common=read(main/'common_initial_states.json');original_tx=repair.transaction
out=root/'results/replay_001';out.mkdir(exist_ok=False)
results=[]
for d in docs:
    repair.initial=lambda doc,_q:(common[doc['id']]['graph'],common[doc['id']]['ranks'])
    for cond in (['sparse','dense_native'] if root.name=='cdcp_scoring' else ['sparse']):
        q,unknown=(repair.score_load(d),{'C':[],'R':[]}) if cond=='sparse' else m.dense_load(d)
        repair.transaction=original_tx if cond=='sparse' else m.guarded_transaction(original_tx,unknown)
        for mode in ['BRJ-lite','RelationOnly']:
            r=repair.run_doc(d,q,mode);p=main/f"{d['id']}__{cond}__{mode}.json";old=read(p)
            if d.get('construction_failure'):r['status']='construction_failure'
            same=r['status']==old['status'] and r.get('final')==old.get('final') and r.get('initial')==old.get('initial')
            path_same=r.get('accepted_attempts')==old.get('accepted_attempts')
            entry={'id':d['id'],'condition':cond,'mode':mode,'status':r['status'],'terminal_match':same,'commit_indices_match':path_same}
            m.write(out/p.name,r);results.append(entry)
            print(json.dumps(entry),flush=True)
m.write(out/'audit.json',{'status':'PASS' if all(r['terminal_match'] and r['commit_indices_match'] for r in results) else 'DIFFERENCES_RETAINED','runs':results,'model_calls':0,'source_output_freeze_sha256':m.sha(main/'output_freeze.json')})
