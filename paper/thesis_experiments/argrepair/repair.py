"""Actual dependency-closed repair using SciPy/HiGHS MILP, not result simulation.

No reference labels are accepted. G0 is the common initial graph; this module
never silently calls it the inherited I0/BR-O algorithm. Utilities are frozen
full-object probabilities. A feasible timed-out incumbent is always rechecked.
"""
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass, field, replace
from itertools import combinations
from math import isfinite
from time import monotonic
from types import SimpleNamespace
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csc_matrix

from .schema import (Component, Relation, Graph, CandidatePool, Scores,
                     digest, graph_errors, relation_errors, component_errors, overlap)


@dataclass(frozen=True)
class RepairConfig:
    kappa_c: float = 1.0
    kappa_r: float = 1.0
    weight_c: float = 1.0
    weight_r: float = 1.0
    delta: float = 0.01
    numeric_tol: float = 1e-9
    component_budget: int = 24
    relation_budget: int = 96
    max_transaction_components: int = 3
    attempts: int = 128
    accepts: int = 12
    rounds: int = 4
    round_attempts: int = 32
    round_accepts: int = 3
    batch_size: int = 8
    global_variable_limit: int = 2500
    time_limit: float = 5.0
    total_time_limit: float = 120.0
    lex_call_limit: int = 64
    global_tie_break: str = 'initial_state'
    local_tie_break: str = 'graph_key'
    queue_limit: int = 10000
    acyclic: bool = False
    one_outgoing: bool = False
    allow_set_actions: bool = False
    presolve: bool = True

    def __post_init__(self):
        if not (0 < self.kappa_c < 2 and 0 < self.kappa_r < 2):
            raise ValueError('kappa must be in (0, 2)')
        if self.delta <= 0 or self.numeric_tol <= 0 or self.weight_c <= 0 or self.weight_r <= 0:
            raise ValueError('positive utility weights, delta and tolerance required')
        if self.global_tie_break not in {'initial_state','graph_key'} or self.local_tie_break not in {'initial_state','graph_key'}:
            raise ValueError('tie break rule must be initial_state or graph_key')
        if self.batch_size < 1 or self.queue_limit < 1:
            raise ValueError('batch and queue limits must be positive')
        if min(self.component_budget, self.relation_budget, self.attempts, self.accepts,
               self.rounds, self.round_attempts, self.round_accepts, self.lex_call_limit) < 0:
            raise ValueError('budgets must be nonnegative')


@dataclass(frozen=True)
class Proposal:
    add: tuple[Component, ...] = ()
    delete: tuple[Component, ...] = ()
    relation_slots: tuple = ()
    kind: str = 'replace'
    @property
    def key(self):
        return (self.kind, tuple(sorted(self.add)), tuple(sorted(self.delete)), tuple(sorted(self.relation_slots)))


@dataclass
class TransactionResult:
    graph: Graph
    status: str
    accepted: bool = False
    delta_c: float = 0.0
    delta_r: float = 0.0
    edits_c: int = 0
    edits_r: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class RepairResult:
    graph: Graph
    status: str
    ledger: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    def to_dict(self):
        return {'graph': self.graph.to_dict(), 'status': self.status,
                'ledger': self.ledger, 'metadata': self.metadata}


def _valid_score(q):
    return q is not None and isfinite(q) and 0 <= q <= 1


def _score_hash(pool, scores):
    def val(q): return float(q) if _valid_score(q) else None
    return digest({'components': [[c.key, val(scores.components.get(c))] for c in sorted(pool.components)],
                   'relations': [[r.key, val(scores.relations.get(r))] for r in sorted(pool.relations)],
                   'metadata': dict(scores.metadata)})


def _delta(old, new, scores, kappa):
    deleted, added = set(old) - set(new), set(new) - set(old)
    if not all(_valid_score(scores.get(o)) for o in deleted | added): return None
    return sum(2 * scores[o] - kappa for o in added) - sum(2 * scores[o] - kappa for o in deleted)


def _verify(pool, scores, old, new, cfg, budget_c, budget_r):
    if not set(new.components) <= set(pool.components) or not set(new.relations) <= set(pool.relations):
        return 'outside_frozen_pool', 0, 0, 0, 0
    errs = graph_errors(pool.doc, new, cfg.acyclic, cfg.one_outgoing)
    if errs: return 'illegal_graph:' + ','.join(errs), 0, 0, 0, 0
    ec = len(set(old.components) ^ set(new.components)); er = len(set(old.relations) ^ set(new.relations))
    dc = _delta(old.components, new.components, scores.components, cfg.kappa_c)
    dr = _delta(old.relations, new.relations, scores.relations, cfg.kappa_r)
    if dc is None or dr is None: return 'missing_scores', 0, 0, ec, er
    if ec > budget_c or er > budget_r: return 'edit_budget_exceeded', dc, dr, ec, er
    if dc < -cfg.numeric_tol or dr < -cfg.numeric_tol: return 'component_or_relation_gate_failed', dc, dr, ec, er
    if cfg.weight_c * dc + cfg.weight_r * dr <= cfg.delta + cfg.numeric_tol:
        return 'no_strict_gain', dc, dr, ec, er
    return 'accepted', dc, dr, ec, er


class _Rows:
    def __init__(self, n): self.n=n; self.rows=[]; self.lower=[]; self.upper=[]
    def add(self, row, lo=-np.inf, hi=np.inf):
        self.rows.append({k:float(v) for k,v in row.items() if v}); self.lower.append(lo); self.upper.append(hi)
    def constraint(self):
        rr=[]; cc=[]; vv=[]
        for i,row in enumerate(self.rows):
            for j,v in row.items(): rr.append(i);cc.append(j);vv.append(v)
        a=csc_matrix((vv,(rr,cc)),shape=(len(self.rows),self.n),dtype=float)
        return LinearConstraint(a,np.asarray(self.lower),np.asarray(self.upper))


def _solve(pool, scores, current, cfg, budget_c, budget_r, fixed_components=None, tx_relations=None):
    """Lexicographic MILP; freezes each proven previous objective, never epsilon weights."""
    started=monotonic()
    cs=tuple(sorted(pool.components)); rs=tuple(sorted(pool.relations)); nc=len(cs); nr=len(rs); no=nc if cfg.acyclic else 0
    n=nc+nr+no; ci={c:i for i,c in enumerate(cs)}; ri={r:nc+i for i,r in enumerate(rs)}
    if n == 0:
        return current, {'solver_status':'empty_problem','primary_optimal':True,'tie_break_complete':True,'solver_calls':0,'elapsed_seconds':0.0}
    is_local=fixed_components is not None
    oldc=set(current.components); oldr=set(current.relations)
    newc=set(fixed_components) if is_local else None
    changed_c=oldc ^ newc if is_local else set(cs)
    required_r=set(tx_relations) if is_local else set(rs)
    if (any(not _valid_score(scores.components.get(c)) for c in changed_c)
        or any(not _valid_score(scores.relations.get(r)) for r in required_r)):
        return None, {'solver_status':'missing_scores','solver_calls':0}
    # Unknown unchanged coefficients cancel in differences and stay fixed.
    uc=np.array([2*scores.components[c]-cfg.kappa_c if _valid_score(scores.components.get(c)) else 0.0 for c in cs])
    ur=np.array([2*scores.relations[r]-cfg.kappa_r if _valid_score(scores.relations.get(r)) else 0.0 for r in rs])
    utility=np.zeros(n);utility[:nc]=cfg.weight_c*uc;utility[nc:nc+nr]=cfg.weight_r*ur
    init=np.array([float(c in oldc) for c in cs]+[float(r in oldr) for r in rs]+[0.0]*no)
    edit_c=np.zeros(n);edit_c[:nc]=[(-1 if c in oldc else 1) for c in cs]
    edit_r=np.zeros(n);edit_r[nc:nc+nr]=[(-1 if r in oldr else 1) for r in rs]
    edit=edit_c+edit_r
    lb=np.zeros(n);ub=np.ones(n);integrality=np.ones(n)
    if no: ub[nc+nr:]=max(nc-1,0);integrality[nc+nr:]=0
    if is_local:
        for c,i in ci.items(): lb[i]=ub[i]=float(c in newc)
        for r,i in ri.items():
            if r not in required_r: lb[i]=ub[i]=float(r in oldr)
            if relation_errors(pool.doc,r,newc): ub[i]=0.0
            if lb[i] > ub[i]: return None, {'solver_status':'fixed_external_relation_invalid','solver_calls':0}
    rows=_Rows(n)
    for a,b in combinations(cs,2):
        if overlap(a,b): rows.add({ci[a]:1,ci[b]:1},hi=1)
    slots=defaultdict(list)
    outgoing=defaultdict(list)
    for r,i in ri.items():
        slots[r.slot].append(i)
        for c in r.endpoints: rows.add({i:1,ci[c]:-1},hi=0)
        for source in r.sources: outgoing[source].append(i)
        if pool.doc.corpus=='cdcp' and len(r.sources)>1:
            lo=min(c.start for c in r.sources); hi=max(c.start for c in r.sources)
            for c in cs:
                if c not in r.sources and lo<c.start<hi: rows.add({i:1,ci[c]:1},hi=1)
        if cfg.acyclic:
            for source in r.sources:
                rows.add({nc+nr+ci[source]:1,nc+nr+ci[r.target]:-1,i:nc},hi=nc-1)
    for ids in slots.values(): rows.add(dict.fromkeys(ids,1),hi=1)
    if cfg.one_outgoing:
        for ids in outgoing.values(): rows.add(dict.fromkeys(ids,1),hi=1)
    rows.add(dict(enumerate(edit_c)),hi=budget_c-len(oldc))
    rows.add(dict(enumerate(edit_r)),hi=budget_r-len(oldr))
    rows.add({i:uc[i] for i in range(nc)},lo=float(uc@init[:nc])-cfg.numeric_tol)
    rows.add({nc+i:ur[i] for i in range(nr)},lo=float(ur@init[nc:nc+nr])-cfg.numeric_tol)
    if is_local:
        # Necessary closed inequality; final verification enforces strict >delta.
        rows.add(dict(enumerate(utility)),lo=float(utility@init)+cfg.delta)
    calls=0
    def call(objective):
        nonlocal calls
        remaining=cfg.time_limit-(monotonic()-started)
        if remaining<=0: return None
        calls+=1
        try:
            return milp(objective,integrality=integrality,bounds=Bounds(lb,ub),constraints=rows.constraint(),
                        options={'time_limit':remaining,'mip_rel_gap':0.0,'presolve':cfg.presolve})
        except Exception as exc:
            return SimpleNamespace(x=None,status=4,message=type(exc).__name__+': '+str(exc))
    def integer_candidate(result):
        if result is None or getattr(result,'x',None) is None: return None
        x=np.asarray(result.x,dtype=float)
        if x.shape!=(n,) or not np.all(np.isfinite(x)): return None
        binary=np.rint(x[:nc+nr])
        if np.max(np.abs(x[:nc+nr]-binary),initial=0)>1e-5: return None
        x[:nc+nr]=binary
        # Independent solver-feasibility check, including all frozen tie objectives.
        a=rows.constraint(); ax=a.A@x;tol=max(cfg.numeric_tol,1e-7)
        if np.any(x<lb-tol) or np.any(x>ub+tol) or np.any(ax<a.lb-tol) or np.any(ax>a.ub+tol): return None
        return x
    first=call(-utility)
    status=getattr(first,'status',1); best=integer_candidate(first)
    meta={'solver_status': {0:'optimal',1:'time_limit',2:'infeasible',3:'unbounded',4:'solver_error'}.get(status,'solver_error'),
          'primary_optimal':status==0,'secondary_optimal':False,'tie_break_complete':False,
          'raw_message':str(getattr(first,'message','time limit before solver call')),
          'mip_gap':float(first.mip_gap) if first is not None and getattr(first,'mip_gap',None) is not None and isfinite(first.mip_gap) else None,
          'solver_calls':calls}
    if best is None:
        if first is not None and getattr(first,'x',None) is not None:
            meta['solver_status']='invalid_incumbent'
        elif status==0:
            meta['solver_status']='solver_no_incumbent'
        meta['elapsed_seconds']=monotonic()-started
        return None,meta
    if status==0:
        primary=float(utility@best)
        rows.add(dict(enumerate(utility)),lo=primary-cfg.numeric_tol)
        second=call(edit); second_x=integer_candidate(second)
        if second_x is not None: best=second_x
        if second is not None and second.status==0 and second_x is not None:
            meta['secondary_optimal']=True
            minedit=round(float(edit@best))
            rows.add(dict(enumerate(edit)),hi=minedit+cfg.numeric_tol)
            complete=True;lexcalls=0
            rule=cfg.local_tie_break if is_local else cfg.global_tie_break
            meta['tie_break_rule']=rule
            def prefer(fixes):
                nonlocal best,lexcalls
                if all(best[i]==value for i,value in fixes.items()):
                    for i,value in fixes.items():lb[i]=ub[i]=value
                    return True
                if lexcalls>=cfg.lex_call_limit:return None
                old_bounds={i:(lb[i],ub[i]) for i in fixes}
                for i,value in fixes.items():lb[i]=ub[i]=value
                result=call(np.zeros(n));lexcalls+=1
                candidate=integer_candidate(result)
                if candidate is not None:
                    best=candidate
                    return True
                for i,(lower,upper) in old_bounds.items():lb[i],ub[i]=lower,upper
                if result is not None and result.status==2:return False
                return None
            if rule=='initial_state':
                # B0690: lexicographic preference for retaining each G0 bit.
                # This is intentionally different from variable-length Graph.key.
                for i in range(nc+nr):
                    if lb[i]==ub[i]:continue
                    outcome=prefer({i:init[i]})
                    if outcome is None:complete=False;break
                    if outcome is False:lb[i]=ub[i]=1-init[i]
            else:
                # Graph.key compares selected-object tuples: an empty or shorter
                # prefix sorts before its extension. Binary zero-first ordering
                # would instead favor *later* objects, so it is incorrect here.
                for family in (range(nc),range(nc,nc+nr)):
                    remaining=list(family)
                    while remaining:
                        # End the tuple now if feasible (short-prefix priority).
                        if not any(lb[i]==1 for i in remaining):
                            outcome=prefer({i:0.0 for i in remaining})
                            if outcome is None:complete=False;break
                            if outcome is True:break
                        # Otherwise select the smallest feasible next object.
                        selected=False
                        for position,i in enumerate(remaining):
                            if ub[i]==0:continue
                            outcome=prefer({i:1.0})
                            if outcome is None:complete=False;break
                            if outcome is True:
                                remaining=remaining[position+1:];selected=True;break
                            lb[i]=ub[i]=0.0
                        if not complete:break
                        if not selected:break
                    if not complete:break
            meta['tie_break_complete']=complete
            meta['lex_calls']=lexcalls
    meta['solver_calls']=calls;meta['elapsed_seconds']=monotonic()-started
    graph=Graph(tuple(c for c,i in ci.items() if best[i]>0.5),tuple(r for r,i in ri.items() if best[i]>0.5))
    return graph,meta


def _closed_components(current, proposal, cfg):
    current_c=set(current.components);add=set(proposal.add);delete=set(proposal.delete)
    if not delete<=current_c:return None,None,'deletion_not_in_current'
    unchanged=add&current_c;add-=unchanged;delete-=unchanged
    if any(overlap(a,b) for a,b in combinations(add,2)):return None,None,'incompatible_additions'
    delete|={c for c in current_c if any(overlap(c,b) for b in add)}
    shape=(len(delete),len(add))
    valid={(0,0),(0,1),(1,0),(1,1)}
    if cfg.allow_set_actions:valid|={(1,2),(2,1)}
    if shape not in valid:return None,None,'action_shape_outside_neighborhood'
    if sum(shape)>cfg.max_transaction_components:return None,None,'transaction_component_limit'
    if shape in {(1,2),(2,1)}:
        whole=next(iter(delete if shape==(1,2) else add));parts=add if shape==(1,2) else delete
        if (min(c.start for c in parts)!=whole.start or max(c.end for c in parts)!=whole.end
            or any(not whole.start<=c.start<c.end<=whole.end for c in parts)):
            return None,None,'invalid_split_merge_envelope'
    return add,delete,None


def evaluate_proposal(pool:CandidatePool,scores:Scores,current:Graph,proposal:Proposal,
                      config:RepairConfig|None=None,remaining_components=None,remaining_relations=None):
    cfg=config or RepairConfig();bc=cfg.component_budget if remaining_components is None else remaining_components
    br=cfg.relation_budget if remaining_relations is None else remaining_relations
    reject=lambda status,meta=None:TransactionResult(current,status,metadata=meta or {})
    if graph_errors(pool.doc,current,cfg.acyclic,cfg.one_outgoing): return reject('invalid_current_graph')
    if not set(proposal.add)<=set(pool.components):return reject('outside_frozen_pool')
    add,delete,error=_closed_components(current,proposal,cfg)
    if error:return reject(error)
    if len(add)+len(delete)>bc:return reject('component_budget_exceeded')
    newc=(set(current.components)-delete)|add
    if any(overlap(a,b) for a,b in combinations(newc,2)):return reject('unclosed_conflict')
    slots={r.slot for r in pool.relations}
    if not set(proposal.relation_slots)<=slots:return reject('outside_frozen_slot_pool')
    tx={r for r in pool.relations if r.endpoints&(add|delete) or r.slot in proposal.relation_slots}
    expanded=set()
    # Only selected OLD external slots that became invalid expand the domain.
    # Newly legal unselected non-contact slots remain fixed until another proposal.
    for r in current.relations:
        if r not in tx and relation_errors(pool.doc,r,newc):expanded.add(r.slot)
    tx|={r for r in pool.relations if r.slot in expanded}
    metadata={'affected_components':[c.key for c in sorted(add|delete)],
              'transaction_relations':[r.key for r in sorted(tx)],
              'expanded_slots':len(expanded),'actual_shape':[len(delete),len(add)]}
    new,solver=_solve(pool,scores,current,cfg,bc,br,newc,tx)
    metadata.update(solver)
    if new is None:return reject(solver['solver_status'],metadata)
    status,dc,dr,ec,er=_verify(pool,scores,current,new,cfg,bc,br)
    return TransactionResult(new if status=='accepted' else current,status,status=='accepted',dc,dr,ec,er,metadata)


def _append_commit(ledger,pool,scores,before,tx,kind,cumulative_c,cumulative_r,commit_hook=None):
    record={'index':len(ledger),'kind':kind,'pool_hash':pool.key,'score_hash':_score_hash(pool,scores),
            'before':before.to_dict(),'after':tx.graph.to_dict(),'before_hash':digest(before.to_dict()),
            'after_hash':digest(tx.graph.to_dict()),'delta_c':tx.delta_c,'delta_r':tx.delta_r,
            'edits_c':tx.edits_c,'edits_r':tx.edits_r,'cumulative_c':cumulative_c+tx.edits_c,
            'cumulative_r':cumulative_r+tx.edits_r,'previous_hash':ledger[-1]['record_hash'] if ledger else None,
            'solver':deepcopy(tx.metadata)}
    record['record_hash']=digest(record)
    if commit_hook is not None:commit_hook(record)
    ledger.append(record)
    return tx.graph


def global_repair(pool:CandidatePool,scores:Scores,config:RepairConfig|None=None,commit_hook=None):
    cfg=config or RepairConfig();initial=pool.initial;ledger=[]
    if graph_errors(pool.doc,initial,cfg.acyclic,cfg.one_outgoing):return RepairResult(initial,'initialization_failed')
    new,meta=_solve(pool,scores,initial,cfg,cfg.component_budget,cfg.relation_budget)
    meta.update(method='Global',budget_semantics='net',pool_hash=pool.key,score_hash=_score_hash(pool,scores))
    if new is None:
        if meta['solver_status']=='infeasible':meta['implementation_or_numeric_failure']=True
        return RepairResult(initial,meta['solver_status'],metadata=meta)
    status,dc,dr,ec,er=_verify(pool,scores,initial,new,cfg,cfg.component_budget,cfg.relation_budget)
    if status!='accepted':return RepairResult(initial,status,metadata=meta)
    tx=TransactionResult(new,status,True,dc,dr,ec,er,meta)
    try:graph=_append_commit(ledger,pool,scores,initial,tx,'global',0,0,commit_hook)
    except Exception as exc:return RepairResult(initial,'commit_failure',metadata={**meta,'error':type(exc).__name__})
    meta.update(net_components=ec,net_relations=er,cumulative_components=ec,cumulative_relations=er)
    return RepairResult(graph,'accepted',ledger,meta)


def _proposal_queue(pool,current,cfg,method):
    """Round-robin six bounded generators; canonical sorting, no repeated state work."""
    cs=set(current.components);new=tuple(c for c in sorted(pool.components) if c not in cs)
    representatives={r.slot:r for r in pool.relations}
    allslots=sorted(representatives);legal=[]
    for slot in allslots:
        any_r=representatives[slot]
        if not relation_errors(pool.doc,any_r,cs):legal.append(slot)
    legalset=set(legal)
    def relations():
        for slot in legal:yield Proposal(relation_slots=(slot,),kind='relation')
        for sources,target in legal:
            if len(sources)==1:
                rev=((target,),sources[0]);fwd=(sources,target)
                if rev in legalset and fwd<rev:yield Proposal(relation_slots=(fwd,rev),kind='reverse')
    def insert():
        for c in new:yield Proposal(add=(c,),kind='insert')
    def delete():
        for c in sorted(cs):yield Proposal(delete=(c,),kind='delete')
    def substitute():
        for c in sorted(cs):
            for d in new:yield Proposal(add=(d,),delete=(c,),kind='replace')
    def split():
        for c in sorted(cs):
            parts=[v for v in new if c.start<=v.start<v.end<=c.end]
            for a,b in combinations(parts,2):
                if not overlap(a,b) and min(a.start,b.start)==c.start and max(a.end,b.end)==c.end:
                    yield Proposal(add=(a,b),delete=(c,),kind='split')
    def merge():
        for c in new:
            parts=[v for v in sorted(cs) if c.start<=v.start<v.end<=c.end]
            for a,b in combinations(parts,2):
                if min(a.start,b.start)==c.start and max(a.end,b.end)==c.end:
                    yield Proposal(add=(c,),delete=(a,b),kind='merge')
    its=[iter(relations())]
    if method!='RelationOnly':its += [iter(insert()),iter(delete()),iter(substitute())]
    if cfg.allow_set_actions and method not in {'RelationOnly','Sequential'}:its += [iter(split()),iter(merge())]
    active=deque(its);seen=set();output=[];enumerated=0
    # Bound enumeration as well as accepted queue length; rejected forms still cost.
    while active and enumerated<cfg.queue_limit:
        it=active.popleft()
        try:p=next(it)
        except StopIteration:continue
        active.append(it);enumerated+=1
        if p.key in seen:continue
        seen.add(p.key)
        add,delete,error=_closed_components(current,p,cfg)
        if not error:output.append(p)
    return output,{'enumerated':enumerated,'queued':len(output),'truncated':bool(active)}


def _sequential_proposal(pool,scores,current,p,cfg,bc,br):
    """Explicit ablation: commit component decision before relation optimization.

    Stage one accepts by component utility only and removes invalid old edges.
    It may lower relation utility, which is precisely the removed joint gate.
    Both stages are legal and charged; no claim of I1 monotonicity is made.
    """
    if not p.add and not p.delete:
        tx=evaluate_proposal(pool,scores,current,p,cfg,bc,br)
        return [tx] if tx.accepted else [],tx
    add,delete,error=_closed_components(current,p,cfg)
    if error:return [],TransactionResult(current,error)
    cs=(set(current.components)-delete)|add
    kept=tuple(r for r in current.relations if not relation_errors(pool.doc,r,cs))
    middle=Graph(tuple(cs),kept)
    ec=len(add)+len(delete);er=len(set(current.relations)-set(kept))
    dc=_delta(current.components,middle.components,scores.components,cfg.kappa_c)
    dr=_delta(current.relations,middle.relations,scores.relations,cfg.kappa_r)
    if dc is None or dr is None:return [],TransactionResult(current,'missing_scores')
    if ec>bc or er>br:return [],TransactionResult(current,'edit_budget_exceeded')
    if dc<=cfg.delta+cfg.numeric_tol:return [],TransactionResult(current,'no_strict_component_gain')
    if graph_errors(pool.doc,middle,cfg.acyclic,cfg.one_outgoing):return [],TransactionResult(current,'illegal_sequential_stage')
    first=TransactionResult(middle,'accepted',True,dc,dr,ec,er,{'stage':'component_only','joint_gate':False})
    affected={r.slot for r in pool.relations if r.endpoints&(add|delete)}|set(p.relation_slots)
    second=evaluate_proposal(pool,scores,middle,Proposal(relation_slots=tuple(sorted(affected)),kind='relation'),cfg,bc-ec,br-er)
    return [first]+([second] if second.accepted else []),second


def repair(pool:CandidatePool,scores:Scores,config:RepairConfig|None=None,method='I1',commit_hook=None):
    """Route I1: small full pool -> Global, otherwise cumulative-budget Single.

    Other explicit methods: Global, Single, SetLocal, RelationOnly, Sequential,
    G0. No implementation of unspecified inherited BR-O is substituted for I0.
    """
    cfg=config or RepairConfig()
    if method in {'I0','BR-O'}:raise ValueError('I0/BR-O requires its own documented implementation; use G0 explicitly')
    if method=='G0':return RepairResult(pool.initial,'no_repair',metadata={'method':'G0'})
    if method=='I1':
        variable_count=len(pool.components)+len(pool.relations)+(len(pool.components) if cfg.acyclic else 0)
        routed='Global' if variable_count<=cfg.global_variable_limit else 'Single'
        result=repair(pool,scores,cfg,routed,commit_hook)
        result.metadata.update(requested_method='I1',routed_method=routed,routing_variables=variable_count)
        return result
    if method=='Global':return global_repair(pool,scores,cfg,commit_hook)
    if method not in {'Single','SetLocal','RelationOnly','Sequential'}:raise ValueError('unknown repair method')
    cfg=replace(cfg,allow_set_actions=(method=='SetLocal'))
    current=pool.initial;ledger=[];attempts=accepts=cc=cr=0;traces=[];queues={};started=monotonic();stop='round_limit'
    if graph_errors(pool.doc,current,cfg.acyclic,cfg.one_outgoing):return RepairResult(current,'initialization_failed')
    for rnd in range(cfg.rounds):
        ra=rc=0
        while ra<cfg.round_attempts and rc<cfg.round_accepts and attempts<cfg.attempts and accepts<cfg.accepts:
            if monotonic()-started>=cfg.total_time_limit:stop='total_time_limit';break
            state=digest(current.to_dict())
            if state not in queues:
                queue,qmeta=_proposal_queue(pool,current,cfg,method);queues[state]=[queue,0,qmeta]
            queue,cursor,qmeta=queues[state]
            if cursor>=len(queue):stop='queue_exhausted';break
            batch=queue[cursor:cursor+min(cfg.batch_size,cfg.attempts-attempts,cfg.round_attempts-ra)]
            queues[state][1]+=len(batch)
            ready=[]
            for proposal in batch:
                if monotonic()-started>=cfg.total_time_limit:stop='total_time_limit';break
                attempts+=1;ra+=1
                actual_cfg=replace(cfg,time_limit=min(cfg.time_limit,max(0,cfg.total_time_limit-(monotonic()-started))))
                if method=='Sequential':
                    stages,tx=_sequential_proposal(pool,scores,current,proposal,actual_cfg,cfg.component_budget-cc,cfg.relation_budget-cr)
                    if stages:ready.append((stages,proposal))
                else:
                    tx=evaluate_proposal(pool,scores,current,proposal,actual_cfg,cfg.component_budget-cc,cfg.relation_budget-cr)
                    if tx.accepted:ready.append(([tx],proposal))
                traces.append({'attempt':attempts,'round':rnd,'state_hash':state,'kind':proposal.kind,
                               'status':tx.status,'solver':deepcopy(tx.metadata)})
            if ready:
                if monotonic()-started>=cfg.total_time_limit:
                    stop='total_time_limit_before_commit';break
                # All candidates originate in the same state and frozen score snapshot.
                stages,proposal=min(ready,key=lambda item:(
                    -sum(cfg.weight_c*t.delta_c+cfg.weight_r*t.delta_r for t in item[0]),
                    sum(t.edits_c+t.edits_r for t in item[0]),item[0][-1].graph.key))
                if accepts>=cfg.accepts or cc+sum(t.edits_c for t in stages)>cfg.component_budget or cr+sum(t.edits_r for t in stages)>cfg.relation_budget:
                    stop='commit_budget_exceeded';break
                committed=False
                for tx in stages:
                    try:current=_append_commit(ledger,pool,scores,current,tx,proposal.kind,cc,cr,commit_hook)
                    except Exception as exc:
                        traces.append({'status':'commit_failure','error':type(exc).__name__});stop='commit_failure';break
                    cc+=tx.edits_c;cr+=tx.edits_r;committed=True
                if committed:accepts+=1;rc+=1
                if stop=='commit_failure':break
            if stop=='total_time_limit':break
        if stop in {'queue_exhausted','total_time_limit','total_time_limit_before_commit','commit_failure','commit_budget_exceeded'}:break
        if attempts>=cfg.attempts:stop='attempt_limit';break
        if accepts>=cfg.accepts:stop='accept_limit';break
    return RepairResult(current,stop,ledger,{'method':method,'budget_semantics':'cumulative','attempts':attempts,
        'accepts':accepts,'commits':len(ledger),'cumulative_components':cc,'cumulative_relations':cr,
        'net_components':len(set(pool.initial.components)^set(current.components)),
        'net_relations':len(set(pool.initial.relations)^set(current.relations)),
        'elapsed_seconds':monotonic()-started,'pool_hash':pool.key,'score_hash':_score_hash(pool,scores),
        'trace':traces,'state_queues':{k:v[2] for k,v in queues.items()}})


def replay_ledger(pool:CandidatePool,scores:Scores,ledger,config:RepairConfig|None=None):
    """Verify hashes, complete states, deltas, gates and cumulative accounting."""
    cfg=config or RepairConfig();current=pool.initial;previous=None;cc=cr=0
    for index,raw in enumerate(ledger):
        record=dict(raw);stored=record.pop('record_hash',None)
        if digest(record)!=stored:raise ValueError('ledger record hash mismatch')
        if record['index']!=index or record['previous_hash']!=previous:raise ValueError('ledger chain mismatch')
        if record['pool_hash']!=pool.key or record['score_hash']!=_score_hash(pool,scores):raise ValueError('snapshot mismatch')
        if record['before_hash']!=digest(current.to_dict()) or record['before']!=current.to_dict():raise ValueError('before state mismatch')
        after=Graph.from_dict(record['after'])
        if record['after_hash']!=digest(after.to_dict()):raise ValueError('after state mismatch')
        status,dc,dr,ec,er=_verify(pool,scores,current,after,cfg,cfg.component_budget-cc,cfg.relation_budget-cr)
        sequential=record['solver'].get('joint_gate') is False
        if status!='accepted' and not (sequential and status in {'component_or_relation_gate_failed','no_strict_gain'} and dc>cfg.delta+cfg.numeric_tol):
            raise ValueError('invalid ledger transition: '+status)
        if abs(dc-record['delta_c'])>cfg.numeric_tol or abs(dr-record['delta_r'])>cfg.numeric_tol:raise ValueError('utility mismatch')
        if (ec,er)!=(record['edits_c'],record['edits_r']):raise ValueError('edit mismatch')
        cc+=ec;cr+=er
        if (cc,cr)!=(record['cumulative_c'],record['cumulative_r']):raise ValueError('cumulative edit mismatch')
        current=after;previous=stored
    return current


def no_risk_config(config:RepairConfig|None=None):
    """B0715 ablation: preserve frozen costs/constraints, lower only positive delta."""
    cfg=config or RepairConfig()
    return replace(cfg,delta=10*cfg.numeric_tol)


def repair_no_risk(pool:CandidatePool,scores:Scores,config:RepairConfig|None=None):
    result=repair(pool,scores,no_risk_config(config),method='I1')
    result.metadata.update(requested_method='NoRisk',development_retention_gate=False,
                           delta_rule='10 * numeric_tol; all other frozen parameters retained')
    return result
