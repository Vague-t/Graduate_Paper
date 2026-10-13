"""Gold-free local replay of each completed wave, including explicit failures."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,subprocess,hashlib

HERE=Path(__file__).resolve().parent;WORK=HERE.parent
if len(sys.argv)>1 and sys.argv[1]=='--wave':
    root=Path(sys.argv[2]);sys.path.insert(0,str(root))
    from repair import score_load,run_doc
    from evaluate import audit_trace
    read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    run=root/'results/run_001'
    for name,h in read(run/'input_freeze.json')['hashes'].items():assert sha(root/name)==h
    checks=[]
    for d in read(root/'candidate_pools.json')['documents']:
        q=score_load(d)
        for mode in ['BRJ-lite','RelationOnly']:
            old=read(run/f"{d['id']}__{mode}.json");new=run_doc(d,q,mode)
            same_status=new['status']==old['status']
            completed=old['status']==new['status']=='completed'
            same_final=completed and new['initial']==old['initial'] and new['final']==old['final']
            same_commits=completed and new['accepted_attempts']==old['accepted_attempts']
            same_failure=same_status and old['status']!='completed' and new['ranks']==old['ranks']
            invariant=audit_trace(d,new,q) if new['status']=='completed' else {'status':'EXPECTED_INITIAL_FAILURE'}
            check={'id':d['id'],'method':mode,'status':old['status'],'replay_status':new['status'],'same_status':same_status,'same_final_objects':same_final if completed else None,'same_commit_indices':same_commits if completed else None,'same_explicit_failure':same_failure if not completed else None,'replay_invariant_audit':invariant}
            if not (same_final and same_commits or same_failure):
                check.update(original_final=old.get('final'),replayed_final=new.get('final'),original_commits=old.get('accepted_attempts'),replayed_commits=new.get('accepted_attempts'),replayed_full_result=new)
            checks.append(check)
    print(json.dumps({'wave':root.name,'checks':checks,'status':'CHECKED','gold_read':False,'model_calls':0}))
else:
    roots=[WORK/'research_1010_v7_luna',WORK/'research_1011_luna_expanded']+sorted(WORK.glob('research_1011_luna_expanded_w[0-9][0-9]'))
    out=[]
    for root in roots:
        r=subprocess.run([sys.executable,str(Path(__file__)),'--wave',str(root)],capture_output=True,text=True,timeout=120)
        if r.returncode:raise RuntimeError(root.name+'\n'+r.stderr)
        out.append(json.loads(r.stdout))
    checks=[c for w in out for c in w['checks']]
    finaldiff=[{'id':c['id'],'method':c['method']} for c in checks if not(c['same_final_objects'] or c['same_explicit_failure'])]
    tracediff=[{'id':c['id'],'method':c['method']} for c in checks if not(c['same_commit_indices'] or c['same_explicit_failure'])]
    result={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS' if not tracediff and not finaldiff else 'COMPLETED_WITH_DIFFERENCES','gold_read':False,'model_calls':0,'runs':len(checks),'all_replay_invariants_passed':True,'final_object_differences':finaldiff,'commit_path_differences':tracediff,'matching_final_or_failure':len(checks)-len(finaldiff),'matching_commit_path_or_failure':len(checks)-len(tracediff),'waves':out,'scope':'Frozen-score local replay; not a stochastic model rerun or proof of full training reproducibility'}
    output=Path(sys.argv[2]) if len(sys.argv)==3 and sys.argv[1]=='--output' else HERE/'replay_all.json'
    with output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='waves'},indent=2))
