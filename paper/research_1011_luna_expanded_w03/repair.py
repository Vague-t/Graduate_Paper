"""Gold-free, finite-universe BR-J mechanism pilot. No evaluation imports."""
import sys, json, time, itertools, warnings, math, platform
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from graph_core import ROOT, ck, overlap, slot, endpoints, legal, relation_legal, state_key, sha, dump_new
sys.path.insert(0,str(ROOT.parent/'research_0920/vendor'))
import numpy as np
import scipy
from scipy.optimize import milp, Bounds, LinearConstraint

TOL=1e-8
def now():return datetime.now(timezone.utc).isoformat()
def phi(C,R,q):return (sum(2*q['C'][c]-1 for c in C),sum(2*q['R'][r]-1 for r in R))
def score_load(doc):
    raw=json.loads((ROOT/'scores'/f"{doc['id']}.json").read_text())
    assert raw['id']==doc['id'] and raw['model_requested']=='gpt-5.6-luna'
    assert raw['default_relation_score']==.05
    assert set(raw['component_scores'])==set(doc['components'])
    assert set(raw['relation_score_overrides'])<=set(doc['relations'])
    assert all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in raw['component_scores'].values())
    assert all(isinstance(v,(int,float)) and math.isfinite(v) and .05<v<=1 for v in raw['relation_score_overrides'].values())
    return {'C':raw['component_scores'],'R':{r:raw['relation_score_overrides'].get(r,.05) for r in doc['relations']}}

def initial(doc,q):
    ranked=[]
    for i,g in enumerate(doc['graphs']):
        C=set(g['components']);R=set(g['relations']);rs=doc['relations'];cs=doc['components']
        Q=[c for c in C if cs[c]['type'] in (('Claim',) if doc['corpus']=='aaec' else ('policy','value'))]
        verified={r for r in R if q['R'][r]>=.5}
        dens=sum(min(sum(rs[r]['target']==c for r in verified)/(1 if any(c in rs[r]['sources'] for r in R) else 2),1) for c in Q)/len(Q) if Q else 0
        coh=len(verified)/len(R) if R else 0
        val=int(not legal(doc,C,R));rank=.4*dens+.4*coh+.2*val
        ranked.append({'candidate_id':g['candidate_id'],'slot':i,'density':dens,'coherence':coh,'validity':val,'rank':rank})
    if not ranked:return None,ranked
    idx=min(range(len(ranked)),key=lambda i:(-ranked[i]['rank'],i))
    g=doc['graphs'][idx]
    return g,ranked

def closed_proposal(doc,C,D0,B0):
    cs=doc['components'];B=set(B0)-C;D=set(D0)
    D|={c for c in C if any(overlap(cs[c],cs[b]) for b in B)}
    if D-C or not (D or B) or len(D)+len(B)>3:return None
    if any(overlap(cs[a],cs[b]) for a,b in itertools.combinations(B,2)):return None
    shape=(len(D),len(B));kind={(0,1):'insert',(1,0):'delete',(1,1):'replace',(1,2):'split',(2,1):'merge'}.get(shape)
    if not kind:return None
    if kind in ('split','merge'):
        single=cs[next(iter(D if kind=='split' else B))]
        pair=[cs[c] for c in (B if kind=='split' else D)]
        if min(c['start'] for c in pair)!=single['start'] or max(c['end'] for c in pair)!=single['end']:return None
        if any(c['start']<single['start'] or c['end']>single['end'] for c in pair):return None
    return {'kind':kind,'D':sorted(D),'B':sorted(B),'S_R':[]}

def queues(doc,C,mode):
    allq={k:[] for k in ('relation','insert','delete','replace','split','merge')};seen=set();rs=doc['relations']
    sm=defaultdict(list)
    for rid,r in rs.items():
        if relation_legal(doc,r,C):sm[slot(r)].append(rid)
    for s in sorted(sm):
        ss={s}
        if len(s[0])==1:
            rev=((s[1],),s[0][0])
            if rev in sm:ss.add(rev)
        R=tuple(sorted(r for x in ss for r in sm[x]))
        if R in seen:continue
        seen.add(R);allq['relation'].append({'kind':'relation','D':[],'B':[],'S_R':list(R)})
    if mode=='RelationOnly':return allq
    seen=set();other=sorted(set(doc['components'])-C)
    def add(D,B):
        p=closed_proposal(doc,C,D,B)
        if p is None:return
        k=(tuple(p['D']),tuple(p['B']))
        if k not in seen:seen.add(k);allq[p['kind']].append(p)
    for c in other:add([], [c])
    for c in sorted(C):add([c],[])
    for a in sorted(C):
        for b in other:add([a],[b])
        for bb in itertools.combinations(other,2):add([a],bb)
    for aa in itertools.combinations(sorted(C),2):
        for b in other:add(aa,[b])
    for k in allq:allq[k].sort(key=lambda p:(p['D'],p['B'],p['S_R']))
    return allq

class Solver:
    def __init__(self,seconds):self.limit=seconds;self.elapsed=0.;self.calls=[]
    def solve(self,c,rows,lower,upper,stage):
        rem=self.limit-self.elapsed
        if rem<=1e-5:return None
        n=len(c);mat=np.asarray(rows,float).reshape((-1,n))
        st=time.perf_counter()
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always')
            r=milp(np.array(c,float),integrality=np.ones(n),bounds=Bounds(np.zeros(n),np.ones(n)),
                   constraints=LinearConstraint(mat,np.asarray(lower),np.asarray(upper)),
                   options={'time_limit':min(.25,rem),'mip_rel_gap':0.,'threads':1})
        elapsed=time.perf_counter()-st;self.elapsed+=elapsed
        def number(name):
            v=getattr(r,name,None)
            return float(v) if v is not None and np.isfinite(v) else None
        record={'index':len(self.calls),'stage':stage,'seconds':elapsed,'time_limit':min(.25,rem),'status':int(r.status),
                'message':r.message,'objective':number('fun'),'minimization_dual_bound':number('mip_dual_bound'),
                'gap':number('mip_gap'),'nodes':number('mip_node_count'),
                'warnings':[str(w.message) for w in ws],'has_incumbent':r.x is not None}
        self.calls.append(record)
        x=None
        if r.x is not None and np.all(np.isfinite(r.x)) and np.max(np.abs(r.x-np.rint(r.x)))<1e-5:
            v=np.rint(r.x).astype(int);mv=mat@v
            if np.all(mv>=np.asarray(lower)-TOL) and np.all(mv<=np.asarray(upper)+TOL):x=v
        return (x,int(r.status),record)

def transaction(doc,C,R,p,q,remainingC,remainingR,solver):
    D=set(p['D']);B=set(p['B']);Cp=(C-D)|B;start=time.perf_counter();call0=len(solver.calls)
    rec={'proposal':p,'before':{'C':sorted(C),'R':sorted(R)},'candidate_C':sorted(Cp),'accepted_candidate':False}
    def done(reason,Cnew=None,Rnew=None):
        rec.update(reason=reason,solver_calls=[x['index'] for x in solver.calls[call0:]],evaluation_seconds=time.perf_counter()-start)
        if Cnew is not None:rec['after']={'C':sorted(Cnew),'R':sorted(Rnew)}
        return rec
    dC=len(C^Cp);pc,pr=phi(C,R,q);pcc,_=phi(Cp,set(),q);dc=pcc-pc
    rec.update(component_edits=dC,delta_phi_C=dc)
    if dC>remainingC:return done('component_budget')
    if dc<-TOL:return done('component_gate')
    if legal(doc,Cp,set()):return done('component_illegal')
    A=D|B;rs=doc['relations'];P={r for r,v in rs.items() if endpoints(v)&A}|set(p['S_R'])
    expanded={slot(rs[r]) for r in R-P if not relation_legal(doc,rs[r],Cp)}
    P|={r for r,v in rs.items() if slot(v) in expanded}
    outside=R-P
    rec.update(transaction_relations=sorted(P),expanded_slots=[list(s) for s in sorted(expanded)],fixed_relations=sorted(outside))
    if legal(doc,Cp,outside):return done('fixed_relations_illegal')
    vars=sorted(r for r in P if relation_legal(doc,rs[r],Cp))
    rec['variables']=vars;current=R&P;fixedphi=phi(set(),outside,q)[1]
    a=np.asarray([2*q['R'][r]-1 for r in vars]);edit=np.asarray([-1 if r in current else 1 for r in vars]);constedit=len(current)
    required=pr+max(0.,.01-dc+1e-6)-fixedphi
    if not vars:
        Rnew=outside;rec['tie_status']='trivial_unique';rec['primary_optimal']=True
    else:
        rows=[];lo=[];hi=[]
        for s in sorted({slot(rs[r]) for r in vars}):
            rows.append([int(slot(rs[r])==s) for r in vars]);lo.append(-np.inf);hi.append(1-sum(slot(rs[r])==s for r in outside))
        rows.append(edit.tolist());lo.append(-np.inf);hi.append(remainingR-constedit)
        rows.append(a.tolist());lo.append(required);hi.append(np.inf)
        out=solver.solve(-a,rows,lo,hi,'maximize_phi')
        if out is None:return done('solver_budget')
        best,status,log=out;rec['primary_optimal']=status==0
        if log['minimization_dual_bound'] is not None:rec['total_phi_upper_bound']=pcc+fixedphi-log['minimization_dual_bound']
        if best is None:return done('infeasible' if status==2 else 'no_valid_incumbent')
        rec['tie_status']='primary_incomplete'
        if status==0:
            optimum=float(a@best);rows.append(a.tolist());lo.append(optimum-TOL);hi.append(optimum+TOL)
            sec=solver.solve(edit,rows,lo,hi,'minimize_edits')
            rec['tie_status']='edit_stage_incomplete'
            if sec is not None and sec[0] is not None:
                best=sec[0]
                if sec[1]==0:
                    cost=float(edit@best);rows.append(edit.tolist());lo.append(cost);hi.append(cost)
                    # Uniqueness certificate at fixed primary objective and edit count.
                    cut=np.where(best==1,-1,1);bound=1-int(best.sum())
                    uniq=solver.solve(np.zeros(len(vars)),rows+[cut.tolist()],lo+[bound],hi+[np.inf],'test_uniqueness')
                    rec['tie_status']='lex_stage_incomplete'
                    if uniq is not None and uniq[1]==2:rec['tie_status']='unique_optimum_and_min_edits'
                    elif uniq is not None and uniq[0] is not None:
                        # Lexicographically smallest tuple of selected relation IDs: an empty
                        # suffix precedes any extension, then choose the earliest feasible next ID.
                        lr=list(rows);ll=list(lo);lh=list(hi);pos=0;complete=True
                        while pos<len(vars):
                            tail=[int(i>=pos) for i in range(len(vars))]
                            end=solver.solve(np.zeros(len(vars)),lr+[tail],ll+[0],lh+[0],'lex_shorter_suffix')
                            if end is None:complete=False;break
                            if end[0] is not None:best=end[0];break
                            if end[1]!=2:complete=False;break
                            found=False
                            for j in range(pos,len(vars)):
                                prefix=[int(pos<=i<j) for i in range(len(vars))];one=[int(i==j) for i in range(len(vars))]
                                t=solver.solve(np.zeros(len(vars)),lr+[prefix,one],ll+[0,1],lh+[0,1],'lex_next_id')
                                if t is None:complete=False;break
                                if t[0] is not None:
                                    best=t[0];lr.extend([prefix,one]);ll.extend([0,1]);lh.extend([0,1]);pos=j+1;found=True;break
                                if t[1]!=2:complete=False;break
                            if not complete or not found:break
                        if complete:rec['tie_status']='lexicographic_complete'
        Rnew=outside|{r for r,x in zip(vars,best) if x}
    issues=legal(doc,Cp,Rnew);newc,newr=phi(Cp,Rnew,q);dR=len(R^Rnew);dr=newr-pr
    rec.update(relation_edits=dR,delta_phi_R=dr,delta_phi=dc+dr,phi_before=[pc,pr],phi_after=[newc,newr],issues=issues)
    if issues:return done('whole_graph_illegal')
    if dR>remainingR:return done('relation_budget')
    if dc<-TOL or dr<-TOL or dc+dr<=.01+TOL:return done('acceptance_gate')
    assert Rnew-P==R-P
    rec['accepted_candidate']=True
    return done('eligible',Cp,Rnew)

def run_doc(doc,q,mode):
    begin=now();start=time.perf_counter();g,ranks=initial(doc,q)
    if g is None or not g['structurally_valid']:return {'id':doc['id'],'mode':mode,'status':'initial_failure','ranks':ranks}
    C=set(g['components']);R=set(g['relations']);initial_state={'C':sorted(C),'R':sorted(R)}
    solver=Solver(3. if doc['corpus']=='aaec' else 5.);attempts=[];accepted=[];rounds=[];ec=er=0;seen={state_key(C,R)}
    queue=None;positions=None;cursor=0;exhausted=False
    for roundno in range(4):
        tries=accepts=0
        while tries<32 and accepts<3 and solver.elapsed<solver.limit and not exhausted:
            if queue is None:queue=queues(doc,C,mode);positions={k:0 for k in queue};cursor=0
            batch=[];ks=list(queue)
            for _ in range(min(6,32-tries)):
                p=None
                for shift in range(len(ks)):
                    idx=(cursor+shift)%len(ks);k=ks[idx]
                    if positions[k]<len(queue[k]):p=queue[k][positions[k]];positions[k]+=1;cursor=(idx+1)%len(ks);break
                if p is None:break
                rec=transaction(doc,C,R,p,q,24-ec,96-er,solver)
                rec.update(attempt=len(attempts),round=roundno+1,committed=False)
                attempts.append(rec);tries+=1
                if rec['accepted_candidate']:batch.append(rec)
                if solver.elapsed>=solver.limit:break
            if batch:
                best=min(batch,key=lambda x:(-sum(x['phi_after']),x['component_edits']+x['relation_edits'],tuple(x['after']['C']),tuple(x['after']['R'])))
                best['committed']=True;C=set(best['after']['C']);R=set(best['after']['R'])
                assert state_key(C,R) not in seen;seen.add(state_key(C,R))
                ec+=best['component_edits'];er+=best['relation_edits'];accepts+=1;accepted.append(best['attempt']);queue=None
            elif p is None or all(positions[k]>=len(queue[k]) for k in queue):exhausted=True
        rounds.append({'round':roundno+1,'attempts':tries,'accepts':accepts})
        if exhausted or solver.elapsed>=solver.limit:break
    assert not legal(doc,C,R) and ec<=24 and er<=96
    return {'id':doc['id'],'corpus':doc['corpus'],'mode':mode,'status':'completed','started_at_utc':begin,'ended_at_utc':now(),
            'wall_seconds':time.perf_counter()-start,'initial_candidate':g['candidate_id'],'ranks':ranks,'initial':initial_state,
            'final':{'C':sorted(C),'R':sorted(R)},'phi_initial':phi(set(initial_state['C']),set(initial_state['R']),q),'phi_final':phi(C,R,q),
            'component_edits_total':ec,'relation_edits_total':er,'attempts':attempts,'accepted_attempts':accepted,'rounds':rounds,
            'solver_seconds':solver.elapsed,'solver_limit_seconds':solver.limit,'solver_calls':solver.calls,
            'stop_reason':'queue_exhausted' if exhausted else ('solver_budget' if solver.elapsed>=solver.limit else 'outer_budget')}

def main():
    path=ROOT/'results/run_001';path.mkdir(exist_ok=False)
    docs=json.loads((ROOT/'candidate_pools.json').read_text())['documents']
    qs={d['id']:score_load(d) for d in docs}
    frozen=[ROOT/x for x in ('protocol.json','scoring_protocol.json','candidate_pools.json','graph_core.py','repair.py','test_repair.py')]
    frozen+=list((ROOT/'scores').glob('*.json'))+list((ROOT/'raw_predictions').glob('*.json'))+list((ROOT/'blind_inputs').glob('*.json'))
    dump_new(path/'input_freeze.json',{'frozen_at_utc':now(),'before_gold_evaluation':True,'python':sys.version,'platform':platform.platform(),
        'scipy':scipy.__version__,'numpy':np.__version__,'hashes':{str(p.relative_to(ROOT)):sha(p) for p in sorted(frozen)}})
    summary=[]
    for doc in docs:
        for mode in ('BRJ-lite','RelationOnly'):
            result=run_doc(doc,qs[doc['id']],mode);dump_new(path/f"{doc['id']}__{mode}.json",result)
            row={k:result.get(k) for k in ('id','mode','status','wall_seconds','solver_seconds','component_edits_total','relation_edits_total','stop_reason')}
            row['attempts']=len(result.get('attempts',[]));row['accepts']=len(result.get('accepted_attempts',[]));summary.append(row)
            print(json.dumps(row),flush=True)
    dump_new(path/'summary.json',{'completed_at_utc':now(),'runs':summary})
    dump_new(path/'output_freeze.json',{'frozen_at_utc':now(),'before_gold_evaluation':True,'hashes':{p.name:sha(p) for p in sorted(path.glob('*.json'))}})

if __name__=='__main__':main()
