"""Small solver/contract fixtures, created before seeing the selected gold."""
import itertools, unittest, json
from repair import Solver, transaction, run_doc, score_load, queues, phi
from graph_core import ROOT, legal

def fixture():
    return {'id':'fixture','corpus':'aaec','text':'a b c',
            'components':{'a':{'start':0,'end':1,'type':'Claim'},'b':{'start':2,'end':3,'type':'Premise'},'c':{'start':4,'end':5,'type':'Premise'}},
            'relations':{'r0':{'sources':['b'],'target':'a','type':'supports'},'r1':{'sources':['b'],'target':'a','type':'attacks'},
                         'r2':{'sources':['c'],'target':'a','type':'supports'},'r3':{'sources':['c'],'target':'b','type':'supports'}},
            'graphs':[{'candidate_id':'g0','components':['a','b','c'],'relations':['r1'],'structurally_valid':True}]}

class Contracts(unittest.TestCase):
    def test_equal_objective_and_edits_resolve_lexicographically(self):
        d=fixture();C=set(d['components']);q={'C':{c:.9 for c in C},'R':{'r0':.9,'r1':.9,'r2':.1,'r3':.1}}
        out=transaction(d,C,set(),{'kind':'relation','D':[],'B':[],'S_R':['r0','r1']},q,24,1,Solver(5))
        self.assertEqual(out['after']['R'],['r0']);self.assertEqual(out['tie_status'],'lexicographic_complete')

    def test_milp_matches_independent_exhaustive_completion(self):
        d=fixture();C=set(d['components']);R={'r1'};q={'C':{c:.9 for c in C},'R':{'r0':.9,'r1':.1,'r2':.7,'r3':.6}}
        p={'kind':'relation','D':[],'B':[],'S_R':list(d['relations'])}
        out=transaction(d,C,R,p,q,24,3,Solver(5))
        feasible=[]
        for n in range(5):
            for rr in itertools.combinations(d['relations'],n):
                r=set(rr)
                if legal(d,C,r) or len(r^R)>3:continue
                dr=phi(C,r,q)[1]-phi(C,R,q)[1]
                if dr>.01:feasible.append((r,phi(C,r,q)[1],len(r^R)))
        best=min(feasible,key=lambda x:(-x[1],x[2],tuple(sorted(x[0]))))
        self.assertEqual(set(out['after']['R']),best[0]);self.assertTrue(out['primary_optimal'])

    def test_component_gain_cannot_pay_for_relation_loss(self):
        d=fixture();q={'C':{'a':.1,'b':.9,'c':.9},'R':{r:.9 for r in d['relations']}}
        p={'kind':'delete','D':['a'],'B':[],'S_R':[]}
        out=transaction(d,set(d['components']),{'r0'},p,q,24,96,Solver(5))
        self.assertFalse(out['accepted_candidate'])

    def test_native_noncontact_illegal_selected_edge_expands(self):
        d=fixture();d['corpus']='cdcp'
        d['components']['t']={'start':6,'end':7,'type':'policy'}
        d['relations']={'h':{'sources':['a','c'],'target':'t','type':'reason'},'h2':{'sources':['a','c'],'target':'t','type':'evidence'}}
        C={'a','c','t'};q={'C':{c:.9 for c in d['components']},'R':{'h':.9,'h2':.1}}
        out=transaction(d,C,{'h'},{'kind':'insert','D':[],'B':['b'],'S_R':[]},q,24,96,Solver(5))
        self.assertEqual(set(out['transaction_relations']),{'h','h2'})
        self.assertFalse(out['accepted_candidate'])
        out2=transaction(d,C|{'b'},set(),{'kind':'delete','D':['b'],'B':[],'S_R':[]},dict(C={**q['C'],'b':.1},R=q['R']),24,96,Solver(5))
        self.assertTrue(out2['accepted_candidate']);self.assertEqual(out2['after']['R'],[])
        self.assertTrue(any('h' in p['S_R'] for p in queues(d,C,'RelationOnly')['relation']))

    def test_scheduler_auditable_budget_and_fixed_components(self):
        d=fixture();q={'C':{c:.9 for c in d['components']},'R':{'r0':.9,'r1':.1,'r2':.7,'r3':.6}}
        out=run_doc(d,q,'RelationOnly')
        self.assertEqual(out['initial']['C'],out['final']['C']);self.assertGreater(len(out['accepted_attempts']),0)
        self.assertLessEqual(len(out['attempts']),128)
        self.assertTrue(all(r['attempts']<=32 and r['accepts']<=3 for r in out['rounds']))
        self.assertFalse(legal(d,set(out['final']['C']),set(out['final']['R'])))

    def test_all_scores_complete_before_real_run(self):
        docs=json.loads((ROOT/'candidate_pools.json').read_text())['documents']
        self.assertEqual(len(docs),48)
        for d in docs:score_load(d)

if __name__=='__main__':unittest.main(verbosity=2)
