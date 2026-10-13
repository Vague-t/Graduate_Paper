"""Finite, annotation-blind candidate construction for chapter 4.

Protected is a *retention* guarantee, not a requirement to select the object.
CDCP groups name complete typed endpoints; no gold field enters this module.
"""
from dataclasses import dataclass
from itertools import combinations
from math import isfinite
from typing import Callable, Mapping

from .schema import (InputDocument, Component, Relation, Graph, CandidatePool,
                     TYPES, LABELS, component_errors, relation_errors, graph_errors, overlap)


@dataclass(frozen=True)
class CandidateConfig:
    supplement_spans: int = 64
    supplement_types_per_span: int = 2
    supplement_slots: int = 4096
    preflight_slot_limit: int = 50000
    cdcp_model_group_proposals: int = 64
    cdcp_total_group_proposals: int = 256
    max_new_sources: int = 3
    max_span_tokens: int = 64
    acyclic: bool = False
    one_outgoing: bool = False


@dataclass(frozen=True)
class SpanProposal:
    start: int
    end: int
    type_scores: Mapping[str, float]
    score: float = 0.0
    token_count: int | None = None


@dataclass(frozen=True)
class GroupProposal:
    sources: tuple[Component, ...]
    target: Component
    score: float = 0.0
    @property
    def slot(self):
        return (tuple(sorted(self.sources)), self.target)


class CandidateConstructionError(ValueError):
    def __init__(self, status, metadata=None):
        self.status = status
        self.metadata = metadata or {}
        super().__init__(status)


def _compatible(cs):
    return all(not overlap(a, b) for a, b in combinations(cs, 2))


def _slot_valid(doc, slot):
    sources, target = slot
    if not sources or len(set(sources)) != len(sources) or target in sources:
        return False
    if any(component_errors(doc, c) for c in (*sources, target)):
        return False
    if not _compatible((*sources, target)):
        return False
    if doc.corpus == 'aaec':
        return len(sources) == 1
    # Other selected intervening components are handled by the solver, never
    # by the ordering of the mutually incompatible candidate universe.
    return not min(c.start for c in sources) < target.start < max(c.start for c in sources)


def build_candidates(doc: InputDocument, initial: Graph, candidate_graphs=(),
                     span_proposals=(), group_proposals=(),
                     config: CandidateConfig | None = None,
                     relation_score_fn: Callable | None = None) -> CandidatePool:
    """Build one frozen pool; fail explicitly instead of trimming protected data.

    ``relation_score_fn`` receives all supplementary labeled relations and
    returns a mapping keyed by Relation. It is required only if slot pruning is
    necessary. Its values must be the frozen full-object scores used later.
    ``token_count`` in span proposals is optional; omitted counts are disclosed
    (a model-token length constraint cannot be guessed from character offsets).
    """
    if not isinstance(doc, InputDocument):
        raise TypeError('inference requires InputDocument, never Document/gold')
    cfg = config or CandidateConfig()
    if any(getattr(cfg, k) < 0 for k in ('supplement_spans', 'supplement_slots',
           'preflight_slot_limit', 'cdcp_model_group_proposals', 'cdcp_total_group_proposals')):
        raise ValueError('candidate budgets must be nonnegative')
    errors = graph_errors(doc, initial, cfg.acyclic, cfg.one_outgoing)
    if errors:
        raise CandidateConstructionError('invalid_initial_graph', {'errors': errors})
    candidates = tuple(candidate_graphs)
    protected_c = set(initial.components)
    protected_slots = {r.slot for r in initial.relations}
    metadata = {'status': 'constructed', 'annotation_access': False,
                'candidate_graphs': len(candidates), 'invalid_components': 0,
                'invalid_relations': 0, 'invalid_span_proposals': 0,
                'invalid_group_proposals': 0, 'span_token_count_unavailable': 0}
    # A failed relation parse must not discard independently valid components.
    for graph in candidates:
        valid = {c for c in graph.components if not component_errors(doc, c)}
        metadata['invalid_components'] += len(graph.components) - len(valid)
        protected_c.update(valid)
        for r in graph.relations:
            if _slot_valid(doc, r.slot) and not relation_errors(doc, r, valid):
                protected_slots.add(r.slot)
            else:
                metadata['invalid_relations'] += 1

    # Deduplicate spans before spending the supplement limit, then take top types.
    spans = {}
    for p in span_proposals:
        if not isfinite(p.score) or not 0 <= p.start < p.end <= len(doc.text):
            metadata['invalid_span_proposals'] += 1
            continue
        if p.token_count is not None and (p.token_count < 1 or p.token_count > cfg.max_span_tokens):
            metadata['invalid_span_proposals'] += 1
            continue
        types = {t: float(v) for t, v in p.type_scores.items()
                 if t in TYPES[doc.corpus] and v is not None and isfinite(v)}
        if not types:
            metadata['invalid_span_proposals'] += 1
            continue
        key = p.start, p.end
        old_score, old_types = spans.get(key, (-float('inf'), {}))
        for t, v in types.items(): old_types[t] = max(v, old_types.get(t, -float('inf')))
        spans[key] = (max(old_score, p.score), old_types)
        if p.token_count is None: metadata['span_token_count_unavailable'] += 1
    ranked_spans = sorted(spans, key=lambda s: (-spans[s][0], s))
    selected_spans = ranked_spans[:cfg.supplement_spans]
    components = set(protected_c)
    for s in selected_spans:
        for typ in sorted(spans[s][1], key=lambda t: (-spans[s][1][t], t))[:cfg.supplement_types_per_span]:
            components.add(Component(*s, typ))
    components = tuple(sorted(components))
    metadata.update(protected_components=len(protected_c),
                    supplementary_components=len(set(components) - protected_c),
                    supplementary_spans_before=len(spans), supplementary_spans_after=len(selected_spans))
    if len(protected_slots) > cfg.preflight_slot_limit:
        raise CandidateConstructionError('protected_slot_overflow', metadata)

    slots = set(protected_slots)
    priorities = {}
    def add_slot(slot, priority=0.0):
        if slot not in slots:
            slots.add(slot)
            if len(slots) > cfg.preflight_slot_limit:
                metadata['preflight_slots_observed'] = len(slots)
                raise CandidateConstructionError('preflight_slot_overflow', metadata)
        priorities[slot] = max(priority, priorities.get(slot, -float('inf')))

    if doc.corpus == 'aaec':
        for source in components:
            for target in components:
                if source != target and not overlap(source, target):
                    add_slot(((source,), target))
    else:
        proposed = {}
        for p in group_proposals:
            slot = p.slot
            if (not isfinite(p.score) or len(slot[0]) > cfg.max_new_sources
                    or not set((*slot[0], slot[1])) <= set(components) or not _slot_valid(doc, slot)):
                metadata['invalid_group_proposals'] += 1
                continue
            if slot not in protected_slots:
                proposed[slot] = max(p.score, proposed.get(slot, -float('inf')))
        model_slots = sorted(proposed, key=lambda s: (-proposed[s], s))[:cfg.cdcp_model_group_proposals]
        # Rule groups are adjacent within an actual predicted segmentation.
        # A score of -inf ranks these after finite model proposals; key breaks ties.
        rules = set()
        for g in (initial, *candidates):
            if any(component_errors(doc, c) for c in g.components) or not _compatible(g.components):
                continue
            cs = tuple(sorted(g.components))
            for size in range(2, min(3, cfg.max_new_sources) + 1):
                for i in range(len(cs) - size + 1):
                    src = cs[i:i + size]
                    for target in cs:
                        slot = (src, target)
                        if slot not in protected_slots and _slot_valid(doc, slot): rules.add(slot)
        combined = list(model_slots)
        combined += sorted(rules - set(model_slots))
        selected = combined[:cfg.cdcp_total_group_proposals]
        metadata.update(cdcp_model_groups_before=len(proposed), cdcp_model_groups_after=len(model_slots),
                        cdcp_rule_groups_before=len(rules), cdcp_combined_groups_before=len(combined),
                        cdcp_combined_groups_after=len(selected))
        for slot in selected: add_slot(slot, proposed.get(slot, -float('inf')))

    supplements = slots - protected_slots
    metadata['preflight_slots_observed'] = len(slots)
    metadata['supplementary_slots_before'] = len(supplements)
    if len(supplements) > cfg.supplement_slots:
        if relation_score_fn is None:
            raise CandidateConstructionError('scoring_required_for_slot_pruning', metadata)
        objects = tuple(Relation(src, tgt, lab) for src, tgt in sorted(supplements) for lab in LABELS[doc.corpus])
        values = relation_score_fn(objects)
        ranks = {}
        for slot in supplements:
            qs = [values.get(Relation(*slot, lab)) for lab in LABELS[doc.corpus]]
            if any(q is None or not isfinite(q) or not 0 <= q <= 1 for q in qs):
                raise CandidateConstructionError('missing_score_for_slot_pruning', metadata)
            ranks[slot] = max(qs)
        supplements = set(sorted(supplements, key=lambda s: (-ranks[s], s))[:cfg.supplement_slots])
        metadata['pruning_scored_objects'] = len(objects)
    final_slots = protected_slots | supplements
    relations = tuple(sorted(Relation(src, tgt, lab) for src, tgt in final_slots for lab in LABELS[doc.corpus]))
    protected_r = frozenset(Relation(src, tgt, lab) for src, tgt in protected_slots for lab in LABELS[doc.corpus])
    metadata.update(protected_slots=len(protected_slots), supplementary_slots_after=len(supplements),
                    final_slots=len(final_slots), final_relations=len(relations))
    return CandidatePool(doc, components, relations, initial, frozenset(protected_c), protected_r, metadata)
