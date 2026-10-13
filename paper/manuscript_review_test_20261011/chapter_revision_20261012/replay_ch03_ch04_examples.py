"""Recompute explicitly constructed teaching examples, not model experiments."""
from pathlib import Path
import json
from itertools import product
from fractions import Fraction as F

B = Path(__file__).resolve().parent
OUT = B/'ch03_ch04_revision_v1'
OUT.mkdir(exist_ok=True)

texts = {
 'a': 'Teamwork helps children learn social skills.',
 'b': 'Working together teaches children to communicate.',
 'c': 'Team tasks require children to listen to others.',
 'd': 'Competition can improve efficiency.',
}
new_texts = dict(texts, a='Cooperation helps children develop social skills.',
                 b='Children learn to communicate by working together.')
types = {'a':'Claim','b':'Premise','c':'Premise','d':'Claim'}
def coordinates(parts, docid):
 pos=0; rows={}
 for k,t in parts.items():
  rows[k]={'key':[docid,pos,pos+len(t),types[k]],'text':t}
  pos+=len(t)+1
 return rows
old=coordinates(texts,'demo_aug');new=coordinates(new_texts,'demo_aug_v1')
for text,rows in [(' '.join(texts.values()),old),(' '.join(new_texts.values()),new)]:
 for r in rows.values(): assert text[r['key'][1]:r['key'][2]]==r['text']
aug={'evidence_type':'CONSTRUCTED_TEACHING_EXAMPLE','model_run':False,
 'original_text':' '.join(texts.values()),'rewritten_text':' '.join(new_texts.values()),
 'A':['a','b'],'old':old,'new':new,'phi':{k:[old[k]['key'],new[k]['key']] for k in old},
 'relations_original':[['b','a','supports'],['c','b','supports']],
 'finite_teaching_factor_universe':[['b','a','supports'],['c','b','supports'],['b','d','NONE'],['c','d','NONE']],
 'not_full_AAEC_factor_enumeration':True,
 'audited_factors':[
  {'ends':['b','a'],'label':'supports','status':'stable','mR':1},
  {'ends':['c','b'],'label':'supports','status':'undecided','mR':0},
  {'ends':['b','d'],'label':'NONE','status':'stable','mR':1}],
 'component_masks':dict.fromkeys(old,1),'component_alignment':['a','b','c'],
 'accepted_views':1,'head_supervision_view_weight':'1/2',
 'component_alignment_factor_weight_before_lambda':'1/3',
 'relation_alignment_group_weights_before_lambda':{'positive':'1/2','NONE':'1/2'},
 'full_generation_target':'original_only',
 'rejected_attempt':{'replacement_a':'Teamwork does not help children learn social skills.',
  'reason':'negation changes meaning','enters_training':False,'increments_accepted_views':False}}
aligned=set(aug['A'])
for src,dst,_ in aug['relations_original']:
 if {src,dst}&set(aug['A']):aligned.update([src,dst])
assert aligned==set(aug['component_alignment'])=={'a','b','c'}
affected=[r[:2] for r in aug['finite_teaching_factor_universe'] if set(r[:2])&set(aug['A'])]
assert affected==[r['ends'] for r in aug['audited_factors']]
assert all(aug['component_masks'][c]==1 for c in aligned)
reliable=[r for r in aug['audited_factors'] if r['mR']==1]
assert len(reliable)==2 and {r['label'] for r in reliable}=={'supports','NONE'}
assert F(aug['head_supervision_view_weight'])*(1+aug['accepted_views'])==1
assert F(aug['component_alignment_factor_weight_before_lambda'])*len(aligned)==1
assert sum(F(v) for v in aug['relation_alignment_group_weights_before_lambda'].values())==1
assert not aug['rejected_attempt']['enters_training'] and not aug['rejected_attempt']['increments_accepted_views']
aug['arithmetic_checks']={'coordinate_roundtrip':True,'alignment_membership':True,'head_weights_sum_to_one':True,
 'factor_and_group_weights_sum_to_one':True,'rejected_view_excluded':True}

def utility(q,k=F(1)): return 2*q-k
def counts(pred,gold): return {'TP':len(pred&gold),'FP':len(pred-gold),'FN':len(gold-pred)}
keys={'a':['demo_tx',0,8,'Claim'],'b':['demo_tx',10,20,'Premise'],
      'b_new':['demo_tx',10,21,'Premise'],'c':['demo_tx',22,32,'Premise']}
cq={'a':F('0.9'),'b':F('0.55'),'b_new':F('0.80'),'c':F('0.85')}
rel={'r1':['b','a','supports'],'r2':['c','b','supports'],
     'r3':['b_new','a','supports'],'r4':['c','b_new','supports']}
rq={'r1':F('0.55'),'r2':F('0.45'),'r3':F('0.80'),'r4':F('0.70')}
c0={'a','b','c'};c1={'a','b_new','c'};r0={'r1','r2'}
deltaC=sum(utility(cq[o]) for o in c1-c0)-sum(utility(cq[o]) for o in c0-c1)
def enumerate_case(scores):
 if any(v is None for v in scores.values()):return {'status':'REJECT_MISSING_SCORE','committed':False}
 choices=[]
 for bits in product([0,1],repeat=4):
  selected={k for k,b in zip(rel,bits) if b}
  if any(not set(rel[r][:2])<=c1 for r in selected):continue
  dr=len(selected^r0)
  dR=sum(utility(scores[r]) for r in selected)-sum(utility(scores[r]) for r in r0)
  total=deltaC+dR
  choices.append((total,dR,dr,tuple(sorted(selected))))
  # All selected relations form a directed chain in this teaching universe.
 best=max(choices,key=lambda v:(v[0],-v[2],v[3]))
 acceptable=[v for v in choices if deltaC>=0 and v[1]>=0 and v[0]>F('.20') and 2<=4 and v[2]<=8]
 if not acceptable:
  return {'status':'REJECT_COMPONENT_OR_RELATION_GATE','committed':False,
    'best_without_part_gate':{'deltaC':str(deltaC),'deltaR':str(best[1]),'total':str(best[0]),'selected':best[3]}}
 best=max(acceptable,key=lambda v:(v[0],-v[2],v[3]))
 return {'status':'ENUMERATED_OPTIMUM_FOR_TEACHING_ONLY','committed':True,
  'deltaC':str(deltaC),'deltaR':str(best[1]),'total':str(best[0]),
  'dC':2,'dR':best[2],'selected':best[3],
  'budget_before':{'C':4,'R':8},'budget_after':{'C':2,'R':8-best[2]}}
accepted=enumerate_case(rq)
missing=enumerate_case(dict(rq,r4=None))
negative=enumerate_case({'r1':F('.60'),'r2':F('.60'),'r3':F('.60'),'r4':F('.40')})
assert accepted['committed'] and accepted['total']=='3/2' and accepted['dR']==4
assert not missing['committed'] and not negative['committed']
assert negative['best_without_part_gate']['total']=='3/10'
goldC=c1;goldR={'r3','r4'}
tx={'evidence_type':'CONSTRUCTED_TEACHING_EXAMPLE','model_run':False,'ILP_solver_run':False,
 'solver':'exhaustive enumeration of 16 binary relation choices',
 'component_keys':keys,'component_scores':{k:float(v) for k,v in cq.items()},
 'relations':rel,'relation_scores':{k:float(v) for k,v in rq.items()},
 'initial_C':sorted(c0),'initial_R':sorted(r0),'proposed_B':['b_new'],'D0':[],
 'D_after_conflict_closure':['b'],'Ptx':list(rel),'delta':'.20',
 'accepted':accepted,'missing_score':missing,'negative_part':negative,
 'constructed_gold_posthoc_only':{
  'component_before':counts(c0,goldC),'component_after':counts(c1,goldC),
  'relation_before':counts(r0,goldR),'relation_after':counts(set(accepted['selected']),goldR)}}
reach={'evidence_type':'CONSTRUCTED_COUNTEREXAMPLE','old_intervals':[[0,4],[4,8]],
 'new_interval':[0,8],'old_scores':[.65,.65],'new_score':.95,'kappa':1,
 'old_utility':'0.60','new_utility':'0.90','delta_utility':'0.30','threshold':'0.20',
 'dC':3,'dR':0,'single_deletion_delta':'-0.30','conflict_closure_requires_two_deletions':True}
assert utility(F('.95'))-2*utility(F('.65'))>F('.20')
for name,data in [('augmentation_example',aug),('transaction_examples',tx),('reachability_counterexample',reach)]:
 (OUT/f'{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'passed','scope':'teaching arithmetic and finite enumeration only','outputs':3},ensure_ascii=False))
