"""Independent exhaustive small-state checks of the added global MILP."""
import itertools,json
from pathlib import Path
import solver_compare as s
def subsets(xs):
 xs=list(xs)
 for bits in itertools.product([0,1],repeat=len(xs)):yield {x for x,b in zip(xs,bits) if b}
def valid(d,C,R):
 c=d['components'];r=d['relations'];slots=set()
 for a,b in itertools.combinations(C,2):
  if max(c[a]['start'],c[b]['start'])<min(c[a]['end'],c[b]['end']):return False
 ordered=sorted(C,key=lambda x:(c[x]['start'],c[x]['end'],c[x]['type']))
 for rid in R:
  rr=r[rid];src=set(rr['sources']);target=rr['target'];key=(tuple(rr['sources']),target)
  if not src or not src|{target}<=C or target in src or key in slots:return False
  slots.add(key)
  if d['corpus']=='cdcp':
   pos=sorted(ordered.index(x) for x in src)
   if pos!=list(range(pos[0],pos[-1]+1)):return False
 return True
def utility(C,R,q):return sum(2*q['C'][x]-1 for x in C),sum(2*q['R'][x]-1 for x in R)
def check(d,q,g):
 initialC=set(g['components']);initialR=set(g['relations']);pc,pr=utility(initialC,initialR,q)
 possibilities=[]
 for C in subsets(d['components']):
  for R in subsets(d['relations']):
   cc,rr=utility(C,R,q)
   if valid(d,C,R) and cc>=pc-1e-8 and rr>=pr-1e-8 and cc+rr>pc+pr+.01+1e-8 and len(C^initialC)<=24 and len(R^initialR)<=96:possibilities.append((cc+rr,len(C^initialC)+len(R^initialR),C,R))
 out=s.solve_global(d,q,g,5.)
 if possibilities:
  expected=min(possibilities,key=lambda x:(-x[0],x[1]));C=set(out['final']['C']);R=set(out['final']['R']);actual=sum(utility(C,R,q))
  assert out['accepted'] and abs(actual-expected[0])<1e-6 and len(C^initialC)+len(R^initialR)==expected[1],(d['id'],out,expected)
 else:assert out['final']=={'C':sorted(initialC),'R':sorted(initialR)} and not out.get('accepted',False)
 return {'case':d['id'],'legal_improving_states':len(possibilities),'passed':True,'primary_optimal':out.get('primary_optimal')}
def main():
 def comp(a,b,t='fact'):return {'start':a,'end':b,'type':t}
 d={'id':'binary_overlap_and_label','corpus':'argunsc','components':{'a':comp(0,2),'a_alt':comp(0,3),'b':comp(5,8),'c':comp(10,13)},'relations':{'r0':{'sources':['a'],'target':'b','type':'support'},'r1':{'sources':['a'],'target':'b','type':'attack'},'r2':{'sources':['a_alt'],'target':'c','type':'support'},'r3':{'sources':['c'],'target':'b','type':'support'}}}
 q={'C':{'a':.6,'a_alt':.9,'b':.8,'c':.75},'R':{'r0':.6,'r1':.8,'r2':.9,'r3':.2}};out=[check(d,q,{'components':['a','b'],'relations':['r0']})]
 d={'id':'cdcp_intermediate_selection','corpus':'cdcp','components':{'a':comp(0,2),'middle':comp(3,4),'b':comp(5,6),'target':comp(8,10)},'relations':{'joint':{'sources':['a','b'],'target':'target','type':'reason'},'single':{'sources':['middle'],'target':'target','type':'reason'}}}
 q={'C':{'a':.8,'middle':.45,'b':.8,'target':.8},'R':{'joint':.95,'single':.1}};out.append(check(d,q,{'components':['a','middle','b','target'],'relations':[]}))
 q2={'C':{x:.9 for x in d['components']},'R':q['R']};out.append(check({**d,'id':'component_gate_prevents_joint_gain'},q2,{'components':list(d['components']),'relations':[]}))
 q3={'C':{x:.2 for x in d['components']},'R':{x:.2 for x in d['relations']}};out.append(check({**d,'id':'strict_no_improvement_fallback'},q3,{'components':[],'relations':[]}))
 doc={'components':{'a':comp(0,5),'b':comp(5,10),'merged':comp(0,10)},'relations':{},'corpus':'argunsc'}
 p=s.repair.closed_proposal(doc,{'a','b'},['a'],['merged']);assert p['kind']=='merge' and p['D']==['a','b']
 qs=s.repair.queues(doc,{'a','b'},'BRJ-lite');allowed=[p for kind,ps in qs.items() if kind not in ['split','merge'] for p in ps];assert all(len(p['D'])<=1 and len(p['B'])<=1 for p in allowed)
 out.append({'case':'single_object_rejects_conflict_closed_merge','passed':True})
 (Path(__file__).parent/'solver_interface_tests.json').write_text(json.dumps({'passed':all(x['passed'] for x in out),'tests':out},indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
