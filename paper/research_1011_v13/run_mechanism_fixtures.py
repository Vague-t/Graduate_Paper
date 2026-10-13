"""Actually run existing finite solvers on declared synthetic scores/native texts.

These are mechanism tests, not trained-model performance or blind extraction.
"""
from common import *
import copy,time,sys
sys.path.insert(0,str(WORK/'research_1011_v11'))
import solver_compare as solve
repair=solve.repair
core=sys.modules['graph_core']

def main():
 ds={d['id']:d for d in load_jsonl(ROOT/'data/native_documents.jsonl')};fixtures=[]
 def component(d,c):
  o=d['components'][c];return {k:o[k] for k in ['start','end','type','quote']}
 # A wrong span must be replaced before the exact relation becomes available.
 d=ds['aaec_essay001'];gr=d['relations'][d['gold_R'][0]];s=gr['sources'][0];t=gr['target'];b='b'+s[1:]
 assert b in d['components']
 doc={'id':'native_aaec_boundary','corpus':'aaec','source_doc_id':d['id'],'text':d['text'],'components':{x:component(d,x) for x in [s,t,b]},'relations':{'gold':{'sources':[s],'target':t,'type':gr['type']},'wrong':{'sources':[b],'target':t,'type':gr['type']}}}
 fixtures.append({'id':doc['id'],'doc':doc,'q':{'C':{s:.83,t:.90,b:.62},'R':{'gold':.88,'wrong':.55}},'initial':{'components':[b,t],'relations':['wrong'],'structurally_valid':True},'gold_C':[s,t],'gold_R':['gold'],'scenario':'constructed boundary error and favorable explicit scores on native text'})
 # Joint-source split needs both new spans to clear the component gate.
 d=ds['cdcp_00662'];gr=next(d['relations'][x] for x in d['gold_R'] if len(d['relations'][x]['sources'])==2);a,b=gr['sources'];t=gr['target']
 C={x:component(d,x) for x in [a,b,t]};s0=min(C[a]['start'],C[b]['start']);e0=max(C[a]['end'],C[b]['end']);C['merged']={'start':s0,'end':e0,'type':'value','quote':d['text'][s0:e0]}
 doc={'id':'native_cdcp_collective_split','corpus':'cdcp','source_doc_id':d['id'],'text':d['text'],'components':C,'relations':{'gold':{'sources':[a,b],'target':t,'type':'reason'},'wrong':{'sources':['merged'],'target':t,'type':'reason'}}}
 fx={'id':doc['id'],'doc':doc,'q':{'C':{a:.74,b:.74,t:.90,'merged':.84},'R':{'gold':.90,'wrong':.65}},'initial':{'components':['merged',t],'relations':['wrong'],'structurally_valid':True},'gold_C':[a,b,t],'gold_R':['gold'],'scenario':'constructed merged component; only two-span split clears nondecrease gate'};fixtures.append(fx)
 bad=copy.deepcopy(fx);bad['id']=bad['doc']['id']='native_cdcp_score_failure';bad['q']['C'].update({a:.60,b:.60,'merged':.99});bad['scenario']='same native graph, wrong merged component has excessive score';fixtures.append(bad)
 miss=copy.deepcopy(fx);miss['id']=miss['doc']['id']='native_cdcp_missing_score';miss['q']['R']['gold']=None;miss['scenario']='missing required assessment protects initial state';fixtures.append(miss)
 for fx in fixtures:fx['initial']['candidate_id']='constructed_initial'
 out=ROOT/'mechanism';out.mkdir(exist_ok=True);dump(out/'inputs.json',{'evidence_type':'CONSTRUCTED_INPUTS_WITH_NATIVE_TEXT','gold_used_to_construct':True,'fixtures':fixtures,'origin_solver_hashes':{str(p.relative_to(WORK)):sha(p) for p in [WORK/'research_1011_v11/solver_compare.py',WORK/'research_1011_v10/cdcp_scoring/repair.py']}})
 oldinit,oldqueues=repair.initial,repair.queues;records=[]
 for fx in fixtures:
  d=fx['doc'];q=fx['q'];initial=fx['initial'];assert not core.legal(d,set(initial['components']),set(initial['relations']))
  for mode in ['RelationOnly','SingleObject','BRJ-lite','GlobalILP-lite']:
   st=time.perf_counter()
   if any(v is None for family in q.values() for v in family.values()):
    res={'id':d['id'],'mode':mode,'status':'score_missing_protected','initial':{'C':initial['components'],'R':initial['relations']},'final':{'C':initial['components'],'R':initial['relations']},'solver_seconds':0.,'solver_calls':[]}
   elif mode=='GlobalILP-lite':res=solve.solve_global(d,q,initial,1.)
   else:
    repair.initial=lambda _d,_q:(initial,[])
    def queues(doc,C,m):
     v=oldqueues(doc,C,'BRJ-lite' if m=='SingleObject' else m)
     if m=='SingleObject':v['split']=[];v['merge']=[]
     return v
    repair.queues=queues;res=repair.run_doc(d,q,mode)
   assert not core.legal(d,set(res['final']['C']),set(res['final']['R']))
   res['evidence_type']='ACTUAL_SOLVER_EXECUTION_ON_CONSTRUCTED_INPUT';res['source_doc_id']=d['source_doc_id'];res['total_seconds']=time.perf_counter()-st
   res['counts']={'C':counts(res['final']['C'],fx['gold_C']),'R':counts(res['final']['R'],fx['gold_R'])};res['initial_counts']={'C':counts(initial['components'],fx['gold_C']),'R':counts(initial['relations'],fx['gold_R'])}
   dump(out/'runs'/f'{fx["id"]}__{mode}.json',res);records.append({'fixture':fx['id'],'source_doc_id':d['source_doc_id'],'mode':mode,'status':res['status'],'C_F1':float(f1(res['counts']['C'])),'R_F1':float(f1(res['counts']['R'])),'initial_R_F1':float(f1(res['initial_counts']['R'])),'seconds':res['total_seconds'],'solver_calls':len(res.get('solver_calls',[])),'final':res['final']})
 repair.initial,repair.queues=oldinit,oldqueues
 expected={}
 for row in records:
  ident=row['fixture'];m=row['mode'];value=row['R_F1']
  ok=(value==100 if (ident=='native_aaec_boundary' and m!='RelationOnly') or (ident=='native_cdcp_collective_split' and m in ['BRJ-lite','GlobalILP-lite']) else value==0)
  expected[ident+'__'+m]=bool(ok)
 assert all(expected.values()),records
 dump(out/'summary.json',{'records':records,'expected_behavior_checks':expected,'checks_passed':sum(expected.values()),'checks_total':len(expected),'input_source': 'native training text + constructed candidates, initialization and scores','new_model_calls':0,'new_target_model_training_runs':0,'scope':'boundary recovery, finite collective escape, score failure, missing-score protection; no general superiority claim'})
 print(json.dumps({'records':len(records),'checks':expected,'solver_calls':sum(x['solver_calls'] for x in records)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
