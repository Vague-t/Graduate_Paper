"""Freeze completed model tasks, run unchanged repair, then evaluate one wave."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,subprocess

root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
import repair
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
    with p.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')

docs=read(root/'candidate_pools.json')['documents'];bad=[]
for d in docs:
    q=repair.score_load(d);g,ranks=repair.initial(d,q)
    if g is None or not g['structurally_valid']:bad.append({'id':d['id'],'candidate_id':g['candidate_id'] if g else None,'issues':g['issues'] if g else ['no_parsed_graph']})
write(root/'evaluation_conventions.json',{'registered_at_utc':datetime.now(timezone.utc).isoformat(),'before_new_gold_evaluation':True,'convention_source':'research_1011_luna_expanded/evaluation_conventions.json','known_gold_free_initial_failures':bad,'convention':'Absent failed output is evaluated as empty, with every gold object FN. Raw MCR state remains separately scored and flagged; do not describe failure as an executed deletion. Failed document stays in total denominator and a separate failure outcome. Failure-stage duration remains missing.','evaluator_sha256':sha(root/'evaluate.py')})
calls=[]
for b in read(root/'sample_manifest.json')['prediction_batches']:
    p=root/'prompts'/('dispatch_predict_'+Path(b['input']).stem+'.txt')
    assert (root/b['output']).exists()
    calls.append({'task':b['task'],'documents':b['documents'],'role':'prediction','model':'gpt-5.6-luna','reasoning_effort':'low','fork_turns':'none','prompt_file':str(p.relative_to(root)),'prompt_sha256':sha(p),'status':'completed'})
for p in sorted((root/'score_batches').glob('*.json')):
    b=read(p);assert all((root/'scores'/f'{i}.json').exists() for i in b['documents']);calls.append({**b,'role':'scoring','status':'completed'})
write(root/'model_dispatch_manifest.json',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'calls':calls,'model_tasks':len(calls),'api_call_count':'not exposed','sampling_parameters':'not exposed','blinding':'Fresh no-history context and instructional whitelist; shared filesystem is not OS isolation; child file access not independently verified'})
files=[root/x for x in ['protocol.json','scoring_protocol.json','evaluation_conventions.json','evaluate.py','source_freeze.json','sample_manifest.json','model_dispatch_manifest.json','pipeline.py']]+list((root/'prompts').glob('*'))
write(root/'analysis_freeze_before_run.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'before_new_gold_evaluation':True,'driver_path':str(Path(__file__).resolve()),'driver_sha256':sha(Path(__file__)),'hashes':{str(p.relative_to(root)):sha(p) for p in files}})
for script,log in [('test_repair.py','preflight_tests.txt'),('repair.py','repair_run_001.txt'),('evaluate.py','evaluation_001.txt')]:
    with (root/'logs'/log).open('x') as f:
        r=subprocess.run([sys.executable,str(root/script)],stdout=f,stderr=subprocess.STDOUT,timeout=120)
    if r.returncode:raise RuntimeError(f'{script} failed with exit {r.returncode}; inspect {root/"logs"/log}; no automatic retry')
m=read(root/'results/evaluation_001/metrics.json')
print(json.dumps({'wave':root.name,'initial_failures':bad,'aggregate':{k:{'documents':v['documents'],'metrics':{m:v['metrics'][m] for m in ['MCR-only','RelationOnly','BRJ-lite']},'outcomes':v['document_relation_outcomes'],'coverage':v['coverage']} for k,v in m['aggregate'].items()},'cases':m['case_selection']},ensure_ascii=False,indent=2))
