"""Replay frozen scores locally; no model calls or gold reads. Preserve run_001."""
import json
from datetime import datetime, timezone
from repair import ROOT, score_load, run_doc, sha, dump_new
def main():
    run=ROOT/'results/run_001';freeze=json.loads((run/'input_freeze.json').read_text())
    for p,h in freeze['hashes'].items():assert sha(ROOT/p)==h,p
    docs=json.loads((ROOT/'candidate_pools.json').read_text())['documents'];checks=[]
    for d in docs:
        q=score_load(d)
        for mode in ('BRJ-lite','RelationOnly'):
            old=json.loads((run/f"{d['id']}__{mode}.json").read_text());new=run_doc(d,q,mode)
            assert new['initial']==old['initial'] and new['final']==old['final'],(d['id'],mode)
            assert new['accepted_attempts']==old['accepted_attempts'],(d['id'],mode)
            checks.append({'id':d['id'],'mode':mode,'same_final_objects':True,'same_accepted_attempts':True})
    result={'status':'PASS','at_utc':datetime.now(timezone.utc).isoformat(),'model_calls':0,'gold_read':False,'checks':checks}
    dest=ROOT/'results'/('replay_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
    dump_new(dest,result);print(str(dest));print('PASS: 32/32 final graphs and accepted-attempt identities match.')
if __name__=='__main__':main()
