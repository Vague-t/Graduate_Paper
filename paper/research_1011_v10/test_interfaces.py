"""Behavioral checks for native arity and missing-assessment transaction closure."""
import importlib.util, json, sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.argv=[__file__,str(BASE/'cdcp_scoring')]
spec=importlib.util.spec_from_file_location('runner',BASE/'run_experiment.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from graph_core import parse_graph

def main():
    checks=[]
    for corpus,typ,label in [('argunsc','claim','support'),('casimedicos','Claim','Support')]:
        graph={'components':[{'id':x,'quote':x,'type':typ} for x in ['A','B','C']], 'relations':[{'sources':['A','B'],'target':'C','type':label}]}
        try:parse_graph('A B C',corpus,graph)
        except ValueError as e:assert 'nonbinary' in str(e)
        else:raise AssertionError('native binary arity not enforced')
        graph['relations'][0]['sources']=['A'];assert len(parse_graph('A B C',corpus,graph)[1])==1
        checks.append(corpus+'_binary_arity')
    calls=[]
    def delegate(*args):calls.append(True);return {'delegated':True}
    doc={'corpus':'cdcp','components':{k:{'start':i*2,'end':i*2+1,'type':'fact'} for i,k in enumerate('abcd')},'relations':{'r0':{'sources':['a','c'],'target':'d','type':'reason'},'r1':{'sources':['a','c'],'target':'d','type':'evidence'},'r2':{'sources':['b'],'target':'d','type':'reason'}}}
    # Inserting b breaks source-set consecutiveness for an outside a,c -> d edge.
    # Its full competing-label slot must enter the transaction and unknown r1 blocks it.
    p={'D':[],'B':['b'],'S_R':[]}
    guard=m.guarded_transaction(delegate,{'C':[],'R':['r1']})
    got=guard(doc,{'a','c','d'},{'r0'},p,{},24,96,None)
    assert got['reason']=='unassessed_object_guard' and got['unknown_transaction_relations']==['r1'] and not calls
    checks.append('unknown_expanded_dependency_slot_blocks_without_solver')
    guard=m.guarded_transaction(delegate,{'C':[],'R':['r2']})
    got=guard(doc,{'a','c','d'},{'r0'},p,{},24,96,None)
    assert got['reason']=='unassessed_object_guard' and not calls
    checks.append('unknown_new_component_incident_relation_blocks')
    p={'D':[],'B':[],'S_R':['r0','r1']}
    guard=m.guarded_transaction(delegate,{'C':['b'],'R':['r2']})
    assert guard(doc,{'a','c','d'},{'r0'},p,{},24,96,None)=={'delegated':True}
    checks.append('unrelated_unknown_object_does_not_block')
    guard=m.guarded_transaction(delegate,{'C':['b'],'R':[]})
    assert guard(doc,{'a','c','d'},{'r0'},{'D':[],'B':['b'],'S_R':[]},{},24,96,None)['reason']=='unassessed_object_guard'
    checks.append('unknown_changed_component_blocks')
    result={'status':'PASS','checks':checks}
    print(json.dumps(result,indent=2))
    out=BASE/'interface_test_results.json'
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')

if __name__=='__main__':main()
