from pathlib import Path
import sys,collections
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'research_1011_v13'))
from common import *
U={d['id']:d for d in load_jsonl(ROOT/'simulation/object_universes.jsonl')};out={}
for g in load_jsonl(ROOT/'simulation/prediction_graphs.jsonl'):
 if g['method'] not in ['t0_i0','t1_i0','t0_i1','t1_i1']:continue
 d=U[g['id']];C=set(g['C']);Rr=set(g['R']);row=out.setdefault((g['corpus'],g['method']),collections.Counter())
 for r in d['gold_R']:
  row['gold_R']+=1
  if r in Rr:row['selected_TP']+=1;continue
  rr=d['relations'][r];missing=(set(rr['sources'])|{rr['target']})-C
  if missing:
   row['endpoint_blocked']+=1
   kinds=set()
   for c in missing:
    options=[x for x in C if d['components'][x]['origin_index']==d['components'][c]['origin_index']]
    kinds.add(d['components'][options[0]]['origin'] if options else 'absent')
   row['endpoint_'+('absent' if 'absent' in kinds else 'type' if 'constructed_type_error' in kinds else 'boundary')]+=1
  else:row['endpoints_ready_but_unselected']+=1
rows=[dict(corpus=k[0],method=k[1],**v) for k,v in out.items()]
for x in rows:assert x['gold_R']==x['selected_TP']+x['endpoint_blocked']+x['endpoints_ready_but_unselected']
dump(ROOT/'simulation/error_chain.json',{'identity':'OBSERVED_COUNTS_OF_CONSTRUCTED_GRAPHS','rows':rows,'gold_used_in_construction':True,'attribution':'endpoint availability versus final selection only; not trained score or solver causality'})
print(rows)
