"""Finite constructed interface checks. No tokenizer, autograd, model or ILP.

The sequential harness consumes declared stage outcomes and artificial resource
units; it checks bookkeeping, not solver feasibility or wall-clock performance.
Coordinates are zero-based half-open character intervals.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import hashlib,json,math
from itertools import combinations
from validate_mechanisms import stable_key,center_and_region

W=Path(__file__).resolve().parent
CONFIG=json.loads((W/'reference_config.json').read_text())
def overlap(a,b):return a[0]<b[1] and b[0]<a[1]
def region(c,relations):
    return tuple(sorted({c}|{s for ss,t,_ in relations if t==c for s in ss}))
def match_center(components,relations,corpus='AAEC',doc='fixture',limit=1000):
    ref,rs,status=center_and_region(components,relations,corpus,seed=CONFIG['center']['seed'],doc=doc,max_chars=limit)
    if status not in ('conclusion','fallback'):return {'status':status,'reference':ref}
    length=lambda r:sum(c[1]-c[0] for c in r)
    indegree=lambda c:sum(t==c for _,t,_ in relations)
    base=length(rs);pool=[]
    for c in components:
        rc=region(c,relations)
        if any(overlap(a,b) for a,b in combinations(rc,2)) or length(rc)>limit:continue
        if len(rc)==len(rs) and indegree(c)==indegree(ref) and abs(length(rc)-base)/base<=CONFIG['matching']['max_relative_char_difference']:
            pool.append(c)
    assert ref in pool
    chosen=min(pool,key=lambda c:stable_key(CONFIG['center']['seed'],doc,c))
    return {'status':'matched','reference':ref,'control':chosen,'reference_region':rs,'control_region':region(chosen,relations),'self_match':ref==chosen,'eligible':sorted(pool),'denominator_chars':base,'control_relative_difference':abs(length(region(chosen,relations))-base)/base}

def reverse_status(source,target,pool,current,legal):
    if len(source)!=1:return {'status':'unsupported_multi_source','queue':False}
    forward=(source,target);backward=((target,),source[0])
    if forward not in pool or backward not in pool:return {'status':'missing_frozen_slot','queue':False}
    if any(c not in current for c in source+(target,)) or not legal(forward) or not legal(backward):return {'status':'current_direction_illegal','queue':False}
    return {'status':'queued','queue':True,'objects':sorted([(s,t,l) for s,t in (forward,backward) for l in pool[(s,t)]])}

def proposal(current,deleted,added,single=False,budget=3):
    current,deleted,added=map(set,(current,deleted,added))
    same=deleted&added;deleted-=same;added-=same
    if not deleted<=current:return {'status':'unknown_deleted'}
    added-=current-deleted
    if any(overlap(a,b) for a,b in combinations(added,2)):return {'status':'new_internal_conflict'}
    deleted|={c for c in current-deleted if any(overlap(c,b) for b in added)}
    shape=(len(deleted),len(added));result={'deleted':sorted(deleted),'added':sorted(added),'shape':shape,'component_cost':sum(shape)}
    if shape not in {(0,1),(1,0),(1,1),(1,2),(2,1)}:return {**result,'status':'unsupported_shape'}
    if single and shape not in {(0,1),(1,0),(1,1)}:return {**result,'status':'single_object_reject'}
    if shape in {(1,2),(2,1)}:
        whole=next(iter(deleted if shape==(1,2) else added));parts=sorted(added if shape==(1,2) else deleted)
        if any(p[0]<whole[0] or p[1]>whole[1] for p in parts):return {**result,'status':'outside_envelope'}
        if parts[0][0]!=whole[0] or parts[-1][1]!=whole[1]:return {**result,'status':'incomplete_envelope'}
    if sum(shape)>budget:return {**result,'status':'component_budget'}
    return {**result,'status':'eligible','current':sorted((current-deleted)|added)}

def invalid_relations(relations,new_components):
    ordered=sorted(new_components);present=set(ordered);bad=set()
    for relation in relations:
        sources,target,_=relation
        if target not in present or not set(sources)<=present:bad.add(relation);continue
        ix=sorted(ordered.index(s) for s in sources)
        if ix and ix!=list(range(ix[0],ix[-1]+1)):bad.add(relation)
    return bad

@dataclass
class Ledger:
    outer_attempts:int=0
    outer_accepts:int=0
    component_attempts:int=0
    relation_attempts:int=0
    solver_calls:int=0
    component_commits:int=0
    relation_commits:int=0
    component_edits:int=0
    relation_edits:int=0
    resource_units:int=0

def sequential(stage1=True,stage2='success',pure_relation=False,resources=2,accept_before=0,accept_cap=3,rel_budget=96):
    # a and b are semantic component identifiers in this ledger-only fixture.
    state={'C':{'a'},'R':{'old'}};log=Ledger(outer_accepts=accept_before);events=[]
    def finish(reason):return {'ledger':asdict(log),'state':{k:sorted(v) for k,v in state.items()},'stop':reason,'events':events}
    if log.outer_accepts>=accept_cap:return finish('outer_accept_cap')
    log.outer_attempts+=1
    if not pure_relation:
        log.component_attempts+=1
        if log.resource_units>=resources:return finish('resource_before_stage1')
        log.resource_units+=1
        if not stage1:return finish('stage1_rejected')
        if rel_budget<1:return finish('stage1_relation_budget')
        state={'C':{'b'},'R':set()};log.component_commits+=1
        log.component_edits+=2;log.relation_edits+=1;log.outer_accepts+=1;events.append('stage1_committed')
    # The companion is allowed at the outer accept cap, but not beyond resources.
    if log.resource_units>=resources:return finish('resource_before_stage2')
    log.relation_attempts+=1;log.solver_calls+=1;log.resource_units+=1
    if stage2!='success':return finish(stage2)
    new_rel='new' if not pure_relation else 'extra'
    if log.relation_edits+1>rel_budget:return finish('stage2_relation_budget')
    state['R'].add(new_rel);log.relation_commits+=1;log.relation_edits+=1
    if pure_relation:log.outer_accepts+=1
    events.append('stage2_committed');return finish('completed')

class Queue:
    """Round counters are outside this state-scoped cursor and attempted set."""
    def __init__(self):self.state=None;self.cursor=0;self.tried=set();self.items=[];self.saved={}
    def bind(self,state,items):
        if state!=self.state:
            if self.state is not None:self.saved[self.state]=(self.items,self.cursor,self.tried)
            self.state=state
            self.items,self.cursor,self.tried=self.saved.get(state,(list(items),0,set()))
    def take(self,n):
        out=[]
        while self.cursor<len(self.items) and len(out)<n:
            item=self.items[self.cursor];self.cursor+=1
            if item in self.tried:continue
            self.tried.add(item);out.append(item)
        return out

def solve_tie_reference(candidates):
    if any(not math.isfinite(x['utility']) for x in candidates):raise ValueError('nonfinite_score')
    return min(candidates,key=lambda x:(-x['utility'],x['edits'],x['key']))

def run():
    checks=[]
    def check(name,condition,evidence):
        assert condition,name
        checks.append({'id':name,'passed':True,'evidence':evidence})
    a=(0,5,'Claim');b=(6,11,'Claim');p=(12,17,'Premise')
    m=match_center([a,b],[])
    check('R01_all_conclusion',m['status']=='matched' and len(m['eligible'])==2,m)
    m=match_center([a],[]);check('R01_only_one',m['self_match'] and m['denominator_chars']==5,m)
    m=match_center([a,p],[]);check('R01_nonconclusion_eligible',p in m['eligible'],m)
    m=match_center([a],[],limit=4);check('R01_region_budget',m['status']=='region_budget',m)
    m=match_center([],[]);check('R01_no_components',m['status']=='no_components',m)
    m=match_center([(0,10,'Claim'),(11,23,'Premise')],[])
    check('R01_reference_denominator',len(m['eligible'])==2 and m['denominator_chars']==10,m)
    rows=[match_center([a,p],[],doc=str(i)) for i in range(20)]+[match_center([],[])]
    valid=[r for r in rows if r['status']=='matched'];self_n=sum(r['self_match'] for r in valid)
    stats={'all_documents':len(rows),'valid_reference_documents':len(valid),'self_match_count':self_n,'heterocenter_count':len(valid)-self_n,'self_match_rate':self_n/len(valid)}
    check('R01_statistics',0<self_n<len(valid) and len(valid)==20,stats)
    f=((a,),p);r=((p,),a);pool={f:('support','attack'),r:('support','attack')}
    q=reverse_status((a,),p,pool,{a,p},lambda _:True);check('R02_both_slots',q['queue'] and len(q['objects'])==4,q)
    q=reverse_status((a,),p,{f:pool[f]},{a,p},lambda _:True);check('R02_protected_forward_only',q['status']=='missing_frozen_slot',q)
    clipped={k:v for k,v in pool.items() if k==f}
    q=reverse_status((a,),p,clipped,{a,p},lambda _:True)
    selected={(f[0],f[1],'support')};delete_proposal=selected-{(f[0],f[1],'support')}
    check('R02_inverse_clipped',not q['queue'] and set(clipped)=={f} and not delete_proposal,{'reverse':q,'pure_delete_result':sorted(delete_proposal)})
    q=reverse_status((a,),p,pool,{a,p},lambda x:x==f);check('R02_illegal_direction',q['status']=='current_direction_illegal',q)
    newa=(0,5,'Premise');q=reverse_status((a,),p,pool,{newa,p},lambda _:True);check('R02_type_replaced',q['status']=='current_direction_illegal',q)
    q=reverse_status((a,b),p,pool,{a,b,p},lambda _:True);check('R02_multi_source_undefined',q['status']=='unsupported_multi_source',q)
    for name,kwargs,expected in [
        ('both_success',{},(1,1,1,1,2,2,'completed')),
        ('stage1_failure',{'stage1':False},(1,0,0,0,0,0,'stage1_rejected')),
        ('stage2_no_solution',{'stage2':'infeasible'},(1,1,1,0,2,1,'infeasible')),
        ('stage2_resource_exhausted',{'resources':1},(1,1,1,0,2,1,'resource_before_stage2')),
        ('pure_relation',{'pure_relation':True},(1,1,0,1,0,1,'completed')),
        ('stage2_edit_exhausted',{'rel_budget':1},(1,1,1,0,2,1,'stage2_relation_budget')),
        ('companion_at_accept_cap',{'accept_before':2},(1,3,1,1,2,2,'completed')),
        ('stage2_timeout',{'stage2':'timeout_no_incumbent'},(1,1,1,0,2,1,'timeout_no_incumbent'))]:
        o=sequential(**kwargs);l=o['ledger'];actual=tuple(l[k] for k in ['outer_attempts','outer_accepts','component_commits','relation_commits','component_edits','relation_edits'])+(o['stop'],)
        check('R03_'+name,actual==expected,o)
    o=sequential(stage2='infeasible');check('R03_failure_state_not_rolled_back',o['state']=={'C':['b'],'R':[]} and o['ledger']['solver_calls']==1,o)
    cycle=[{'old'},set(),{'old'}];actual=sum(len(x^y) for x,y in zip(cycle,cycle[1:]));check('R03_delete_readd_charged',actual==2 and len(cycle[0]^cycle[-1])==0,{'cumulative':actual,'net':0})
    candidates=[{'key':'A','utility':.6,'edits':2,'future_relation_gain':.1},{'key':'B','utility':.5,'edits':2,'future_relation_gain':10}]
    winner=solve_tie_reference(candidates);check('R03_batch_first_stage_only',winner['key']=='A',{'candidates':candidates,'winner':winner['key']})
    whole=(0,10,'Claim');left=(0,4,'Premise');right=(5,10,'Claim');external=(12,15,'Claim')
    cases=[('split_legal',[whole],[whole],[left,right],'eligible',{}),('split_outside',[whole],[whole],[left,(5,11,'Claim')],'outside_envelope',{}),('split_overlap',[whole],[whole],[(0,6,'Claim'),(5,10,'Claim')],'new_internal_conflict',{}),('split_incomplete',[whole],[whole],[left,(5,9,'Claim')],'incomplete_envelope',{}),('merge_inverse',[left,right],[left,right],[whole],'eligible',{}),('external_conflict',[whole,external],[whole],[left,(5,15,'Claim')],'unsupported_shape',{}),('nominal_insert_two_delete',[(0,4,'Claim'),(5,10,'Claim')],[],[whole],'single_object_reject',{'single':True}),('split_edit_budget',[whole],[whole],[left,right],'component_budget',{'budget':2})]
    for name,cur,d,a_,expected,kwargs in cases:
        o=proposal(cur,d,a_,**kwargs);check('R04_'+name,o['status']==expected,{'input':{'current':cur,'deleted':d,'added':a_},'result':o})
    src=(-5,-1,'Premise');out=(12,16,'Claim');oldrels={((src,),whole,'support'),((whole,),out,'support'),((whole,src),out,'support')}
    newcs={src,left,right,out};bad=invalid_relations(oldrels,newcs)
    newrels={((src,),left,'support'),((right,),out,'support'),((src,left),out,'support')}
    check('R04_complete_relation_replacement',bad==oldrels and not invalid_relations(newrels,newcs),{'deleted_relations':sorted(bad),'added_relations':sorted(newrels),'actual_relation_edits':len(bad)+len(newrels)})
    # Nonincident old hyperedge loses source contiguity after an insertion.
    x=(0,2,'Premise');y=(6,8,'Premise');t=(10,12,'Claim');z=(3,5,'Premise');h=((x,y),t,'support')
    check('R04_external_hyperedge_legality',invalid_relations({h},{x,y,t})==set() and invalid_relations({h},{x,z,y,t})=={h},{'insert':z,'removed_nonincident_old_relation':h})
    q=Queue();q.bind('s0',list(range(10)));first=q.take(6);later=q.take(6)
    check('R06_later_batch_after_reject',first==list(range(6)) and 7 in later,{'rejected_batch':first,'later_batch':later,'acceptable_fixture_item':7})
    q=Queue();q.bind('s0',list(range(40)));r1=q.take(32);q.bind('s0',list(range(40)));r2=q.take(32)
    check('R06_cursor_across_rounds',r2==list(range(32,40)),{'round1':r1,'round2':r2})
    q.bind('s1',[0,0,1]);r3=q.take(6);check('R06_state_change_reenumerates',r3==[0,1],{'new_state_batch':r3})
    q.bind('s0',list(range(40)));r4=q.take(6);check('R06_return_state_preserves_cache',r4==[],{'restored_state':'s0','remaining':r4})
    c=[{'utility':1,'edits':2,'key':'b'},{'utility':1,'edits':1,'key':'c'},{'utility':1,'edits':1,'key':'a'}]
    check('R06_reference_tie_order',solve_tie_reference(c)['key']=='a',{'candidates':c,'chosen':'a','actual_ILP_test':False})
    rejected=False
    try:solve_tie_reference([{'utility':float('nan'),'edits':0,'key':'a'}])
    except ValueError:rejected=True
    check('R06_nonfinite_rejected',rejected,{'status':'nonfinite_score'})
    result={'evidence_type':'CONSTRUCTED_INTERFACE_EXECUTION_NOT_PRODUCTION','configuration_id':CONFIG['configuration_id'],'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'config_sha256':hashlib.sha256((W/'reference_config.json').read_bytes()).hexdigest(),'passed':len(checks),'checks':checks,'not_executed':['real_tokenizer','autograd','LoRA','candidate_production_path','actual_ILP','atomic_persistence','corpus_experiments']}
    (W/'interface_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'passed':len(checks),'type':result['evidence_type']}))
if __name__=='__main__':run()
