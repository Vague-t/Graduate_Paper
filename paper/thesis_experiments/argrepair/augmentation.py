"""Chapter 3: exact character transport and label-blind factor review.

A review callback is a classifier, not a function receiving the expected label.
Its failures/unknowns never become negative labels. Gold stays in training only.
"""
from dataclasses import dataclass, field, replace
from itertools import combinations
import hashlib
from typing import Callable
from .schema import Component, Relation, Graph, Document, InputDocument, TYPES, LABELS, graph_errors, digest


@dataclass(frozen=True)
class SlotFactor:
    sources: tuple[Component, ...]
    target: Component
    label: str | None  # None = semantic unknown, distinct from NONE
    def __post_init__(self): object.__setattr__(self, 'sources', tuple(sorted(self.sources)))
    @property
    def slot(self): return (self.sources, self.target)
    @property
    def endpoints(self): return frozenset((*self.sources, self.target))
    def map(self, phi): return SlotFactor(tuple(phi[c] for c in self.sources), phi[self.target], self.label)


@dataclass(frozen=True)
class FactorUniverse:
    factors: tuple[SlotFactor, ...]
    @property
    def auditable(self): return tuple(f for f in self.factors if f.label is not None)
    @property
    def unknown(self): return tuple(f for f in self.factors if f.label is None)


def _hash(*parts): return hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()

def factor_universe(doc: Document, max_sources: int = 3, max_factors: int = 50000) -> FactorUniverse:
    """All AAEC pairs or CDCP contiguous source intervals <= k plus every gold slot.

    Unannotated nonempty proper subsets of known joint sources are semantic
    unknown, if they occur in the declared finite universe. Explicit positives
    take priority. Resource overflow raises; it never silently clips the domain.
    """
    if max_sources < 1: raise ValueError('max_sources must be positive')
    errors = graph_errors(doc.input, doc.gold)
    if errors: raise ValueError(f'invalid training graph: {errors}')
    cs = doc.gold.components
    slots = set()
    if doc.corpus == 'aaec':
        if len(cs) * max(len(cs)-1,0)>max_factors: raise ValueError('factor_universe_resource_limit')
        slots = {((s,),t) for s in cs for t in cs if s!=t}
    else:
        for i in range(len(cs)):
            for k in range(1, min(max_sources,len(cs)-i)+1):
                sources = tuple(cs[i:i+k])
                for target in cs:
                    if target not in sources:
                        slots.add((sources,target))
                        if len(slots)>max_factors: raise ValueError('factor_universe_resource_limit')
    positives = {}
    for r in doc.gold.relations:
        if r.slot in positives and positives[r.slot]!=r.label:
            raise ValueError('multiple relation states per slot are unsupported by this corpus contract')
        positives[r.slot]=r.label; slots.add(r.slot)
    if len(slots)>max_factors: raise ValueError('factor_universe_resource_limit')
    factors=[]
    for sources,target in sorted(slots):
        label=positives.get((sources,target),'NONE')
        if doc.corpus=='cdcp' and label=='NONE':
            if any(r.target==target and set(sources)<set(r.sources) for r in doc.gold.relations): label=None
        factors.append(SlotFactor(sources,target,label))
    return FactorUniverse(tuple(factors))


def select_rewrite_set(doc: Document, seed: int = 17):
    """Fixed center then full incoming sources, never recursively expanded."""
    cs=doc.gold.components
    if not cs: return frozenset(), {'center':None,'fallback':False}
    preferred={'Claim','MajorClaim'} if doc.corpus=='aaec' else {'policy','value'}
    choices=[c for c in cs if c.label in preferred] or list(cs)
    # Stable canonical IDs are assigned from native object order.
    ids={c:f'c{i}' for i,c in enumerate(cs)}
    center=min(choices,key=lambda c:(_hash(seed,doc.corpus,doc.doc_id,ids[c],'center')[:16],c.key))
    selected={center}
    for r in doc.gold.relations:
        if r.target==center: selected.update(r.sources)
    return frozenset(selected), {'center':ids[center],'fallback':not any(c.label in preferred for c in cs)}



def build_generation_payload(doc: Document, rewrite_set, max_sources: int = 3, max_factors: int = 50000):
    """Lossless training-only conditions for slot paraphrasing, never review input.

    Positive slots and semantic-unknown exceptions are explicit. The remaining
    finite universe is specified by a deterministic recipe, so every auditable
    NONE factor and the full influence domain can be reconstructed without an
    O(n^2) listing of negative labels in the language-model prompt.
    """
    if doc.split not in {'train','training'}:raise ValueError('augmentation generation conditions are train-only')
    A=frozenset(rewrite_set)
    if not A or not A<=set(doc.gold.components):raise ValueError('invalid fixed rewrite set')
    universe=factor_universe(doc,max_sources,max_factors)
    ids={c:f'c{i}' for i,c in enumerate(doc.gold.components)}
    def endpoint(c):
        item={**c.to_dict(),'text':doc.text[c.start:c.end]}
        annotations=[{k:v for k,v in row.items() if k!='component'} for row in getattr(doc,'annotations',()) if row['component']==c.to_dict()]
        if annotations:item['native_attributes']=annotations
        return item
    def slot(f):return {'sources':[ids[c] for c in f.sources],'target':ids[f.target]}
    domain=[f for f in universe.auditable if f.endpoints&A]
    positives=[{**slot(f),'type':f.label} for f in universe.auditable if f.label!='NONE']
    return {'corpus':doc.corpus,'text':doc.text,'component_order':[ids[c] for c in doc.gold.components],
            'slots':{ids[c]:endpoint(c) for c in doc.gold.components if c in A},
            'read_only_endpoints':{ids[c]:endpoint(c) for c in doc.gold.components if c not in A},
            'positive_relations':positives,
            'semantic_unknown_exceptions':[slot(f) for f in universe.unknown],
            'factor_universe':{
                'rule':'all_ordered_single_source_pairs' if doc.corpus=='aaec' else 'all_contiguous_source_intervals_up_to_k_plus_all_positive_slots',
                'max_new_sources':1 if doc.corpus=='aaec' else max_sources,
                'source_order':'component_order', 'nonempty_sources':True,'target_must_not_be_source':True,
                'positive_annotation_takes_precedence':True,'all_gold_hyperedges_preserved_regardless_of_arity':True,
                'none_definition':'Every slot in the declared finite universe absent from positive_relations and semantic_unknown_exceptions has state NONE.',
                'semantic_unknown_is_not_none':True,'total_factors':len(universe.factors),'auditable_factors':len(universe.auditable)},
            'influence_domain':{'rule':'auditable factors with at least one endpoint in slots',
                                'internal_rule':'all endpoints are in slots','boundary_rule':'some but not all endpoints are in slots',
                                'factors':len(domain),'internal':sum(f.endpoints<=A for f in domain),
                                'boundary':sum(not f.endpoints<=A for f in domain)},
            'output_contract':'Return replacement text for every ID in slots only; preserve every type, native attribute and auditable relation state. Do not relabel UNKNOWN as NONE, modify read_only_endpoints, add components, or generate a new graph.'}


def transport(doc: Document, replacements: dict[Component,str], variant_id: str = 'v1'):
    """Transport *all* components and complete hyperedges via native offsets."""
    if not replacements: raise ValueError('empty replacement mapping')
    if not set(replacements)<=set(doc.gold.components): raise ValueError('unknown replacement slot')
    if any(not isinstance(v,str) or not v.strip() for v in replacements.values()): raise ValueError('empty or nontext replacement')
    if graph_errors(doc.input,doc.gold): raise ValueError('invalid source graph')
    cs=doc.gold.components; phi={}; pieces=[]; cursor=0; shift=0
    for c in cs:
        if c.start<cursor: raise ValueError('overlapping source slots')
        old=doc.text[c.start:c.end]; replacement=replacements.get(c,old)
        pieces.extend([doc.text[cursor:c.start],replacement])
        new=Component(c.start+shift,c.start+shift+len(replacement),c.label)
        phi[c]=new; shift+=len(replacement)-len(old); cursor=c.end
    pieces.append(doc.text[cursor:]); text=''.join(pieces)
    new_input=InputDocument(f'{doc.doc_id}::{variant_id}',doc.corpus,text,doc.source_group,doc.split)
    graph=Graph(tuple(phi.values()),tuple(Relation(tuple(phi[c] for c in r.sources),phi[r.target],r.label) for r in doc.gold.relations))
    for c,new in phi.items():
        if text[new.start:new.end]!=replacements.get(c,doc.text[c.start:c.end]): raise ValueError('coordinate_roundtrip_failed')
    if len(set(phi.values()))!=len(cs) or graph_errors(new_input,graph): raise ValueError('lossless_transport_failed')
    annotations=[]
    for annotation in getattr(doc,'annotations',()):
        native=annotation['component']
        old=Component(native['start'],native['end'],native['type'])
        if old not in phi:raise ValueError('native_attribute_endpoint_not_found')
        annotations.append({**annotation,'component':phi[old].to_dict()})
    return replace(doc,input=new_input,gold=graph,annotations=tuple(annotations)),phi


def _span(c): return {'start':c.start,'end':c.end}

def _blind_component(doc,c):
    return {'task':'component_type','corpus':doc.corpus,'text':doc.text,'span':_span(c),'allowed_labels':list(TYPES[doc.corpus]),'unknown_label':'UNKNOWN'}

def _blind_relation(doc,f):
    return {'task':'relation_state','corpus':doc.corpus,'text':doc.text,'sources':[_span(c) for c in f.sources],
            'target':_span(f.target),'allowed_labels':[ *LABELS[doc.corpus], 'NONE'],'unknown_label':'UNKNOWN'}

def _result(value):
    if isinstance(value,str): return value
    return value.get('label','UNKNOWN') if isinstance(value,dict) else 'UNKNOWN'


@dataclass
class AugmentedView:
    source_doc_id: str
    document: Document
    correspondence: dict[Component,Component]
    rewrite_set: frozenset[Component]
    component_mask: dict[Component,bool]
    relation_mask: dict[SlotFactor,bool]
    factors: tuple[SlotFactor,...]
    alignment_components: frozenset[Component]
    audit: dict = field(default_factory=dict)
    def to_dict(self):
        cs=sorted(self.correspondence); ids={c:i for i,c in enumerate(cs)}
        return {'source_doc_id':self.source_doc_id,'document':self.document.to_dict(),
                'correspondence':[{'old':c.to_dict(),'new':self.correspondence[c].to_dict(),'mask':bool(self.component_mask.get(c,False))} for c in cs],
                'rewrite_set':[ids[c] for c in sorted(self.rewrite_set)],
                'alignment_components':[ids[c] for c in sorted(self.alignment_components)],
                'factors':[{'sources':[ids[c] for c in f.sources],'target':ids[f.target],'label':f.label,'mask':bool(self.relation_mask.get(f,False))} for f in self.factors],
                'audit':self.audit}
    @classmethod
    def from_dict(cls,d):
        def component(v): return Component(v['start'],v['end'],v['type'])
        cs=[component(v['old']) for v in d['correspondence']]
        phi={c:component(v['new']) for c,v in zip(cs,d['correspondence'])}
        fs=tuple(SlotFactor(tuple(cs[i] for i in v['sources']),cs[v['target']],v['label']) for v in d['factors'])
        return cls(d['source_doc_id'],Document.from_dict(d['document']),phi,
                   frozenset(cs[i] for i in d['rewrite_set']),{c:bool(v['mask']) for c,v in zip(cs,d['correspondence'])},
                   {f:bool(v['mask']) for f,v in zip(fs,d['factors'])},fs,frozenset(cs[i] for i in d['alignment_components']),d.get('audit',{}))


class ViewRejected(ValueError):
    def __init__(self, reason, audit=None): super().__init__(reason); self.reason=reason; self.audit=audit or {}


def review_view(original: Document, replacements: dict[Component,str], reviewer: Callable[[dict],dict|str],
                mode: str = 'factor', max_relation_reviews: int = 10000, none_per_group: int = 4,
                variant_id: str = 'v1', rewrite_set=None, reviewer_id: str = 'unspecified') -> AugmentedView:
    """Classify original/changed factors separately, compare only *after* calls.

    Callback tasks: component_type -> native type; component_meaning -> SAME,
    CHANGED or UNKNOWN; relation_state -> native state or NONE. No request
    contains a gold type/relation or a pass/fail expected answer. All raw answers
    are retained. Resource limits count relation factors (two calls each).
    """
    if original.split not in {'train','training'}: raise ValueError('augmentation is train-only')
    if mode not in {'factor','full'}: raise ValueError('mode must be factor or full')
    if max_relation_reviews<0 or none_per_group<0: raise ValueError('invalid review budgets')
    A=frozenset(rewrite_set) if rewrite_set is not None else select_rewrite_set(original)[0]
    if set(replacements)!=set(A): raise ViewRejected('replacement_set_must_equal_fixed_rewrite_set')
    augmented,phi=transport(original,replacements,variant_id)
    universe=factor_universe(original); domain=tuple(f for f in universe.auditable if f.endpoints&A)
    audit={'reviewer_id':reviewer_id,'mode':mode,'raw':[],'domain_size':len(domain),'semantic_unknown':len(universe.unknown),
           'source_hash':digest(original.to_dict()),'augmented_hash':digest(augmented.to_dict()),'accepted':False}
    def classify(request):
        try: response=reviewer(request)
        except Exception as exc: response={'label':'UNKNOWN','error':type(exc).__name__+': '+str(exc)}
        audit['raw'].append({'request':request,'response':response})
        return _result(response)
    cm={}
    for c in original.gold.components:
        old_label=classify(_blind_component(original,c)); new_label=classify(_blind_component(augmented,phi[c]))
        meaning=classify({'task':'component_meaning','corpus':original.corpus,
                          'original_text':original.text,'original_span':_span(c),
                          'rewritten_text':augmented.text,'rewritten_span':_span(phi[c]),
                          'allowed_labels':['SAME','CHANGED','UNKNOWN']})
        cm[c]=(old_label==c.label and new_label==c.label and meaning=='SAME')
        if meaning!='SAME': raise ViewRejected('component_changed_or_unknown',audit)
        if c in A and not cm[c]: raise ViewRejected('rewritten_component_changed_or_unknown',audit)
    positives=[f for f in domain if f.label!='NONE']
    if mode=='full':
        if len(domain)>max_relation_reviews: raise ViewRejected('full_domain_review_resource_limit',audit)
        selected=list(domain)
    elif len(positives)>max_relation_reviews:
        # No partial positive relation supervision, but component view survives.
        selected=[]; audit['relation_skip']='positive_coverage_resource_limit'
    else:
        selected=list(positives)
        for internal in (True,False):
            choices=[f for f in domain if f.label=='NONE' and (f.endpoints<=A)==internal]
            choices.sort(key=lambda f:(_hash(17,original.doc_id,repr(f.slot),'review'),repr(f.slot)))
            selected.extend(choices[:none_per_group])
        selected=selected[:max_relation_reviews]
    rm={f:False for f in universe.factors}
    for f in selected:
        old_label=classify(_blind_relation(original,f)); new_label=classify(_blind_relation(augmented,f.map(phi)))
        rm[f]=all(cm[c] for c in f.endpoints) and old_label==f.label and new_label==f.label
        if mode=='full' and not rm[f]: raise ViewRejected('full_filter_relation_changed_or_unknown',audit)
    if mode=='full' and not all(cm.values()): raise ViewRejected('full_filter_component_changed_or_unknown',audit)
    align=set(A)
    for f in domain:
        if f.label!='NONE': align.update(f.endpoints)
    align={c for c in align if cm[c]}
    audit.update({'accepted':True,'reviewed_factors':len(selected),'reliable_factors':sum(rm.values()),
                  'component_passes':sum(cm.values()),'review_calls':len(audit['raw'])})
    return AugmentedView(original.doc_id,augmented,phi,A,cm,rm,universe.factors,frozenset(align),audit)
