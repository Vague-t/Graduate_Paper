"""Native character identities shared by training, inference and evaluation.

Offsets are half-open Unicode character indices, never tokenizer indices.
Inference receives InputDocument, which has no annotation field.
"""
from dataclasses import dataclass, field
import hashlib
import json
from typing import Mapping

TYPES = {'aaec': ('MajorClaim', 'Claim', 'Premise'),
         'cdcp': ('reference', 'testimony', 'fact', 'value', 'policy')}
LABELS = {'aaec': ('attacks', 'supports'), 'cdcp': ('evidence', 'reason')}

def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()

@dataclass(frozen=True, order=True)
class Component:
    start: int
    end: int
    label: str
    @property
    def key(self): return (self.start, self.end, self.label)
    def to_dict(self): return {'start': self.start, 'end': self.end, 'type': self.label}

@dataclass(frozen=True, order=True)
class Relation:
    sources: tuple[Component, ...]
    target: Component
    label: str
    def __post_init__(self):
        if len(set(self.sources)) != len(self.sources): raise ValueError('duplicate source member')
        object.__setattr__(self, 'sources', tuple(sorted(self.sources)))
    @property
    def slot(self): return (self.sources, self.target)
    @property
    def endpoints(self): return frozenset((*self.sources, self.target))
    @property
    def key(self): return (tuple(c.key for c in self.sources), self.target.key, self.label)

@dataclass(frozen=True)
class Graph:
    components: tuple[Component, ...] = ()
    relations: tuple[Relation, ...] = ()
    def __post_init__(self):
        object.__setattr__(self, 'components', tuple(sorted(set(self.components))))
        object.__setattr__(self, 'relations', tuple(sorted(set(self.relations))))
    @property
    def key(self): return (tuple(c.key for c in self.components), tuple(r.key for r in self.relations))
    def to_dict(self):
        ids={c:f'c{i}' for i,c in enumerate(self.components)}
        return {'components':[{'id':ids[c], **c.to_dict()} for c in self.components],
                'relations':[{'sources':[ids[c] for c in r.sources], 'target':ids[r.target], 'type':r.label} for r in self.relations]}
    @classmethod
    def from_dict(cls, data):
        cs={}
        for item in data['components']:
            ident=str(item['id'])
            if ident in cs: raise ValueError('duplicate component display id')
            if type(item['start']) is not int or type(item['end']) is not int: raise ValueError('non-integer offsets')
            cs[ident]=Component(item['start'],item['end'],item['type'])
        rs=[]
        for item in data.get('relations',[]):
            rs.append(Relation(tuple(cs[str(i)] for i in item['sources']),cs[str(item['target'])],item['type']))
        return cls(tuple(cs.values()),tuple(rs))

@dataclass(frozen=True)
class InputDocument:
    doc_id: str
    corpus: str
    text: str
    source_group: str = ''
    split: str = ''
    def __post_init__(self):
        if self.corpus not in TYPES: raise ValueError('unsupported corpus')
    def to_dict(self):
        return {'doc_id':self.doc_id,'corpus':self.corpus,'text':self.text,
                'source_group':self.source_group,'split':self.split}

@dataclass(frozen=True)
class Document:
    input: InputDocument
    gold: Graph
    annotations: tuple = ()
    @property
    def doc_id(self): return self.input.doc_id
    @property
    def text(self): return self.input.text
    @property
    def corpus(self): return self.input.corpus
    @property
    def source_group(self): return self.input.source_group
    @property
    def split(self): return self.input.split
    def to_dict(self):
        result={**self.input.to_dict(),'graph':self.gold.to_dict()}
        if self.annotations:result['annotations']=list(self.annotations)
        return result
    @classmethod
    def from_dict(cls,d):
        return cls(InputDocument(d['doc_id'],d['corpus'],d['text'],d.get('source_group',''),d.get('split','')),Graph.from_dict(d['graph']),tuple(d.get('annotations',())))

@dataclass(frozen=True)
class CandidatePool:
    doc: InputDocument
    components: tuple[Component, ...]
    relations: tuple[Relation, ...]
    initial: Graph
    protected_components: frozenset[Component] = frozenset()
    protected_relations: frozenset[Relation] = frozenset()
    metadata: dict = field(default_factory=dict)
    @property
    def key(self): return digest({'input':self.doc.to_dict(),'universe':Graph(self.components,self.relations).to_dict(),'initial':self.initial.to_dict(),
                                 'protected_components':[c.key for c in sorted(self.protected_components)],
                                 'protected_relations':[r.key for r in sorted(self.protected_relations)]})

@dataclass(frozen=True)
class Scores:
    components: Mapping[Component, float | None]
    relations: Mapping[Relation, float | None]
    metadata: dict = field(default_factory=dict)

def overlap(a:Component,b:Component):
    return max(a.start,b.start)<min(a.end,b.end)

def component_errors(doc:InputDocument,c:Component):
    errors=[]
    if not 0<=c.start<c.end<=len(doc.text): errors.append('span_out_of_bounds')
    if c.label not in TYPES[doc.corpus]: errors.append('invalid_component_type')
    return errors

def relation_errors(doc:InputDocument,r:Relation,components):
    cs=set(components);errors=[]
    if not r.sources or r.target in r.sources: errors.append('empty_source_or_self_loop')
    if not r.endpoints<=cs: errors.append('missing_endpoint')
    if r.label not in LABELS[doc.corpus]: errors.append('invalid_relation_label')
    if doc.corpus=='aaec' and len(r.sources)!=1: errors.append('nonbinary_aaec')
    if doc.corpus=='cdcp' and r.endpoints<=cs and r.sources:
        ordered=sorted(cs);positions=sorted(ordered.index(c) for c in r.sources)
        if positions!=list(range(min(positions),max(positions)+1)): errors.append('noncontiguous_source_group')
    return errors

def graph_errors(doc:InputDocument,g:Graph,acyclic=False,one_outgoing=False):
    from itertools import combinations
    errors=[e for c in g.components for e in component_errors(doc,c)]
    if any(overlap(a,b) for a,b in combinations(g.components,2)): errors.append('overlapping_components')
    slots=set();outgoing={};adj={c:set() for c in g.components}
    for r in g.relations:
        errors+=relation_errors(doc,r,g.components)
        if r.slot in slots: errors.append('multiple_labels_same_slot')
        slots.add(r.slot)
        for s in r.sources:
            outgoing[s]=outgoing.get(s,0)+1
            if s in adj: adj[s].add(r.target)
    if one_outgoing and any(v>1 for v in outgoing.values()): errors.append('outdegree')
    if acyclic:
        active=set();done=set()
        def visit(v):
            if v in active:return True
            if v in done:return False
            active.add(v)
            if any(visit(w) for w in adj.get(v,())):return True
            active.remove(v);done.add(v);return False
        if any(visit(c) for c in g.components):errors.append('cycle')
    return sorted(set(errors))
