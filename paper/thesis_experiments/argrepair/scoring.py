"""Frozen text encoding and strict, complete-object correctness scores.

This module is separate from the train-time semantic heads. In particular a
proper subset of a gold CDCP hyperedge is a strict-object negative, not a
semantic NONE annotation. Nothing here reads gold at inference time.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from functools import cached_property
from typing import Protocol, Sequence
import json
import math
import random
import hashlib

import torch
from torch import nn
from .schema import (Component, Relation, Document, InputDocument, CandidatePool,
                     Scores, TYPES, LABELS, digest, component_errors)


@dataclass(frozen=True)
class TextEncoding:
    hidden: torch.Tensor
    offsets: tuple[tuple[int, int], ...]
    text: str

    def span_indices(self, start: int, end: int) -> list[int]:
        if not 0 <= start < end <= len(self.text):
            raise ValueError('native span is outside text')
        indices = [i for i, (a, b) in enumerate(self.offsets) if a < end and b > start and b > a]
        if not indices:
            raise ValueError('span has no encoded input tokens')
        # A gap is not silently assigned to a neighboring token. Tokenizers can
        # omit spaces; those gaps may be internal, but both boundaries must be covered.
        if not any(a <= start < b for a, b in (self.offsets[i] for i in indices)):
            raise ValueError('span start is not covered by encoder offsets')
        if not any(a < end <= b for a, b in (self.offsets[i] for i in indices)):
            raise ValueError('span end is not covered by encoder offsets')
        return indices

    @cached_property
    def context(self):
        indices = [i for i, (a, b) in enumerate(self.offsets) if b > a]
        if not indices:
            raise ValueError('empty encoded input')
        return self.hidden[indices].mean(0)

    def span(self, start: int, end: int):
        ids = self.span_indices(start, end)
        n = max(1, len(self.text))
        a, _ = self.offsets[ids[0]]
        _, b = self.offsets[ids[-1]]
        positions = self.hidden.new_tensor([start/n, end/n, (end-start)/n,
                    (start-a)/max(1, self.offsets[ids[0]][1]-a),
                    (b-end)/max(1, b-self.offsets[ids[-1]][0]),
                    len(ids)/max(1, len(self.offsets))])
        return torch.cat((self.hidden[ids].mean(0), positions))


class TextEncoder(Protocol):
    hidden_size: int
    identity: dict
    def encode(self, document: InputDocument) -> TextEncoding: ...


class TinyTextEncoder(nn.Module):
    """Frozen, seeded character embeddings for actual offline Torch debugging.

    This is deliberately not a pretrained language model and must not be used
    as evidence of Qwen or thesis benchmark performance.
    """
    def __init__(self, hidden_size=32, seed=17, vocab_size=4096):
        super().__init__()
        self.hidden_size, self.seed, self.vocab_size = hidden_size, seed, vocab_size
        with torch.random.fork_rng():
            torch.manual_seed(seed)
            self.embedding = nn.Embedding(vocab_size, hidden_size)
        self.requires_grad_(False)
        self.eval()
        self.identity = {'kind':'tiny_random_character_debug', 'hidden_size':hidden_size,
                         'seed':seed, 'vocab_size':vocab_size, 'revision':'v1',
                         'weights_sha256':hashlib.sha256(self.embedding.weight.detach().cpu().numpy().tobytes()).hexdigest()}

    @torch.no_grad()
    def encode(self, document):
        if not isinstance(document, InputDocument):
            raise TypeError('encoder takes InputDocument, never annotated Document')
        ids = torch.tensor([ord(c) % self.vocab_size for c in document.text],
                           device=self.embedding.weight.device, dtype=torch.long)
        return TextEncoding(self.embedding(ids).detach(),
                            tuple((i, i+1) for i in range(len(document.text))), document.text)


class HFTextEncoder(nn.Module):
    """Frozen HF backbone; fast-tokenizer native offsets, no output/answer tokens.

    Pass quantization_config/device_map through model_kwargs for a 24 GB GPU.
    Inputs beyond max_tokens are rejected rather than silently truncated.
    """
    def __init__(self, model_id, revision=None, max_tokens=4096, device='cpu', **model_kwargs):
        super().__init__()
        from transformers import AutoTokenizer, AutoModel
        tokenizer_kwargs = {key:model_kwargs[key] for key in
                            ('local_files_only','cache_dir','token','trust_remote_code','force_download')
                            if key in model_kwargs}
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, use_fast=True, **tokenizer_kwargs)
        if not self.tokenizer.is_fast:
            raise ValueError('a fast tokenizer with native offset mapping is required')
        self.model = AutoModel.from_pretrained(model_id, revision=revision, **model_kwargs)
        if 'device_map' not in model_kwargs:
            self.model.to(device)
        self.model.requires_grad_(False)
        self.model.eval()
        self.hidden_size = self.model.config.hidden_size
        self.max_tokens = max_tokens
        resolved = getattr(self.model.config, '_commit_hash', None)
        self.identity = {'kind':'hf_frozen_text', 'model_id':str(model_id),
                         'revision_requested':revision, 'revision_resolved':resolved,
                         'hidden_size':self.hidden_size, 'max_tokens':max_tokens,
                         'compute_dtype':str(self.model.dtype),
                         'quantization':json.loads(json.dumps(self.model.config.to_dict().get('quantization_config'),default=str)),
                         'attention_implementation':getattr(self.model.config,'_attn_implementation',None),
                         'tokenizer_class':type(self.tokenizer).__name__,
                         'tokenizer_digest':hashlib.sha256(self.tokenizer.backend_tokenizer.to_str().encode()).hexdigest()}
        # Local model snapshots have no hub commit; bind their complete weight files.
        p = Path(model_id)
        if p.is_dir():
            files = sorted(set(p.glob('*.safetensors')) | set(p.glob('pytorch_model*.bin')))
            weights = hashlib.sha256()
            for file in files:
                weights.update(file.name.encode())
                with file.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(8*1024*1024), b''):
                        weights.update(chunk)
            self.identity['local_weights_sha256'] = weights.hexdigest()

    @torch.no_grad()
    def encode(self, document):
        if not isinstance(document, InputDocument):
            raise TypeError('encoder takes InputDocument, never annotated Document')
        tokens = self.tokenizer(document.text, return_tensors='pt', return_offsets_mapping=True,
                                add_special_tokens=True, truncation=False)
        offsets = tuple(tuple(v) for v in tokens.pop('offset_mapping')[0].tolist())
        if len(offsets) > self.max_tokens:
            raise ValueError(f'encoder_context_overflow:{len(offsets)}>{self.max_tokens}')
        device = self.model.get_input_embeddings().weight.device
        tokens = {k:v.to(device) for k,v in tokens.items()}
        self.model.eval()
        output = self.model(**tokens, return_dict=True)
        return TextEncoding(output.last_hidden_state[0].detach().float(), offsets, document.text)


def component_target(span: tuple[int, int], gold, corpus: str) -> int:
    """NULL=0; wrong boundaries remain NULL even when their text overlaps gold."""
    matches = [c.label for c in gold.components if (c.start, c.end) == tuple(span)]
    if len(set(matches)) > 1:
        raise ValueError('ambiguous multiple gold types on one span')
    return TYPES[corpus].index(matches[0])+1 if matches else 0


def relation_target(relation: Relation, gold) -> int:
    return int(relation in set(gold.relations))


@dataclass(frozen=True)
class ScoringExample:
    document: Document
    pool: CandidatePool
    natural_distribution: bool = True
    sampling_probability: float = 1.0
    def __post_init__(self):
        if self.document.input != self.pool.doc:
            raise ValueError('candidate pool is not bound to the labeled input')


def _group(doc):
    return doc.source_group or doc.doc_id


def _check_examples(examples, allowed):
    if not examples:
        raise ValueError('no supervision records')
    for example in examples:
        if example.document.split not in allowed:
            raise ValueError(f'forbidden supervision split:{example.document.split}')


class PlattCalibrator:
    def __init__(self, slope=1., intercept=0., fitted=False):
        self.slope, self.intercept, self.fitted = float(slope), float(intercept), bool(fitted)

    def fit(self, logits, targets):
        x = torch.as_tensor(logits, dtype=torch.float64).flatten()
        y = torch.as_tensor(targets, dtype=torch.float64).flatten()
        if not len(x) or len(x) != len(y) or not torch.isfinite(x).all():
            raise ValueError('invalid calibration observations')
        if set(y.tolist()) != {0., 1.}:
            raise ValueError('calibration requires both object correctness classes')
        # Positive slope preserves object ranking; this is an explicit engineering
        # choice rather than an unconstrained sign-flipping logistic fit.
        a = nn.Parameter(torch.zeros((), dtype=torch.float64))
        b = nn.Parameter(torch.zeros((), dtype=torch.float64))
        optimizer = torch.optim.LBFGS([a, b], max_iter=100, line_search_fn='strong_wolfe')
        def closure():
            optimizer.zero_grad()
            loss = nn.functional.binary_cross_entropy_with_logits(a.exp()*x+b, y)
            loss = loss + 1e-6*(a*a+b*b)
            loss.backward()
            return loss
        optimizer.step(closure)
        slope, intercept = float(a.detach().exp()), float(b.detach())
        if not math.isfinite(slope) or not math.isfinite(intercept) or slope <= 0:
            raise ValueError('nonfinite calibration fit')
        self.slope, self.intercept, self.fitted = slope, intercept, True
        return self

    def __call__(self, value):
        x = max(-80., min(80., self.slope*float(value)+self.intercept))
        return 1/(1+math.exp(-x))

    def to_dict(self):
        return {'slope':self.slope,'intercept':self.intercept,'fitted':self.fitted}


class ObjectScorer(nn.Module):
    def __init__(self, encoder: TextEncoder, corpus: str, hidden=1024, dropout=.1):
        super().__init__()
        self.encoder, self.corpus, self.width, self.dropout = encoder, corpus, hidden, dropout
        h, t, r = encoder.hidden_size, len(TYPES[corpus]), len(LABELS[corpus])
        def mlp(n_in, n_out):
            return nn.Sequential(nn.Linear(n_in, hidden), nn.GELU(), nn.Dropout(dropout), nn.Linear(hidden, n_out))
        self.component_head = mlp(2*h+6, t+1)
        self.relation_head = mlp(3*h+12+2*t+r+4, 1)
        self.calibrators = {'component':PlattCalibrator(), 'relation':PlattCalibrator()}
        self.fit_groups = set()
        self.calibration_groups = set()
        self.training_history = []
        self._score_cache = {}

    @property
    def device(self):
        return next(self.component_head.parameters()).device

    def train(self, mode=True):
        super().train(mode)
        self.encoder.eval()
        return self

    def component_features(self, encoding, start, end):
        return torch.cat((encoding.span(start,end), encoding.context)).to(self.device)

    def relation_features(self, encoding, relation):
        if not relation.sources or relation.target in relation.sources:
            raise ValueError('empty source group or self relation')
        native_types = TYPES[self.corpus]
        def type_vector(c):
            result = encoding.hidden.new_zeros(len(native_types))
            result[native_types.index(c.label)] = 1
            return result
        source = torch.stack([encoding.span(c.start,c.end) for c in relation.sources]).mean(0)
        target = encoding.span(relation.target.start,relation.target.end)
        source_types = torch.stack([type_vector(c) for c in relation.sources]).mean(0)
        target_type = type_vector(relation.target)
        label = encoding.hidden.new_zeros(len(LABELS[self.corpus]))
        label[LABELS[self.corpus].index(relation.label)] = 1
        centers = [(c.start+c.end)/2 for c in relation.sources]
        tc = (relation.target.start+relation.target.end)/2
        positions = encoding.hidden.new_tensor([sum(x < tc for x in centers)/len(centers),
                         sum(x > tc for x in centers)/len(centers),
                         (sum(centers)/len(centers)-tc)/max(1,len(encoding.text)),
                         math.log1p(len(centers))])
        return torch.cat((source,target,encoding.context,source_types,target_type,label,positions)).to(self.device)

    @torch.no_grad()
    def raw_scores(self, pool, batch_size=256):
        self.eval()
        if batch_size < 1: raise ValueError('batch size must be positive')
        if pool.doc.corpus != self.corpus:
            raise ValueError('scorer corpus mismatch')
        encoding = self.encoder.encode(pool.doc)
        cs, rs = {}, {}
        span_logits = {}
        # Streaming prevents a 7B-width feature matrix for every slot being kept
        # simultaneously on the accelerator.
        for c in pool.components:
            try:
                if component_errors(pool.doc,c): raise ValueError('invalid component')
                span = (c.start,c.end)
                if span not in span_logits:
                    span_logits[span] = self.component_head(self.component_features(encoding,*span)).softmax(-1)
                prob = float(span_logits[span][TYPES[self.corpus].index(c.label)+1])
                cs[c] = math.log(max(1e-7,prob)/max(1e-7,1-prob)) if math.isfinite(prob) else None
            except (ValueError, IndexError):
                cs[c] = None
        pending = []
        def flush():
            if not pending: return
            vals = self.relation_head(torch.stack([v for _,v in pending])).flatten().tolist()
            for (r,_),value in zip(pending,vals):
                rs[r] = value if math.isfinite(value) else None
            pending.clear()
        for r in pool.relations:
            try:
                if any(component_errors(pool.doc,c) for c in r.endpoints): raise ValueError('invalid endpoint')
                pending.append((r,self.relation_features(encoding,r)))
            except (ValueError, IndexError):
                rs[r] = None
            if len(pending) >= batch_size: flush()
        flush()
        return cs, rs

    def model_identity(self, include_calibration=True):
        h = hashlib.sha256()
        for prefix, module in (('C',self.component_head),('R',self.relation_head)):
            for key,value in module.state_dict().items():
                h.update((prefix+key+str(value.dtype)).encode()); h.update(value.detach().float().cpu().contiguous().numpy().tobytes())
        identity = {'encoder':self.encoder.identity,'corpus':self.corpus,'head_sha256':h.hexdigest()}
        if include_calibration:
            identity['calibration'] = {k:v.to_dict() for k,v in self.calibrators.items()}
        return digest(identity)

    def score(self, pool, batch_size=256):
        identity = self.model_identity()
        key = (pool.key,identity)
        if key not in self._score_cache:
            failure = None
            try:
                cs,rs = self.raw_scores(pool,batch_size=batch_size)
            except ValueError as exc:
                cs = {c:None for c in pool.components}; rs = {r:None for r in pool.relations}
                failure = str(exc)
            result = Scores(MappingProxyType({c:None if v is None else self.calibrators['component'](v) for c,v in cs.items()}),
                            MappingProxyType({r:None if v is None else self.calibrators['relation'](v) for r,v in rs.items()}),
                            MappingProxyType({'pool_key':pool.key,'scorer_identity':identity,'failure':failure,
                                'calibrated':all(c.fitted for c in self.calibrators.values()),
                                'fit_source_groups':tuple(sorted(self.fit_groups)),
                                'calibration_source_groups':tuple(sorted(self.calibration_groups))}))
            self._score_cache[key] = result
        return self._score_cache[key]

    def score_relations(self, doc, components, relations, batch_size=256):
        from .schema import Graph
        return self.score(CandidatePool(doc,tuple(components),tuple(relations),Graph()),batch_size).relations

    def score_relations_for_pruning(self, doc, components, relations, batch_size=256):
        """Frozen *uncalibrated* probabilities for identical pre/post-cal pruning.

        Positive Platt calibration preserves mathematical order, but floating
        point saturation can introduce ties. Always use this same transform for
        both calibration-pool construction and deployment-pool construction.
        These numbers are proposal ranks, not final calibrated utilities.
        """
        from .schema import Graph
        pool = CandidatePool(doc,tuple(components),tuple(relations),Graph())
        _, raw = self.raw_scores(pool,batch_size=batch_size)
        identity_transform = PlattCalibrator()
        return {r:None if v is None else identity_transform(v) for r,v in raw.items()}

    def pruning_relation_scores(self, doc, components, relations, batch_size=256):
        return self.score_relations_for_pruning(doc,components,relations,batch_size=batch_size)

    def save(self,path):
        payload = {'version':1,'encoder_identity':self.encoder.identity,'corpus':self.corpus,
                   'hidden':self.width,'dropout':self.dropout,
                   'component_head':self.component_head.state_dict(),'relation_head':self.relation_head.state_dict(),
                   'calibrators':{k:v.to_dict() for k,v in self.calibrators.items()},
                   'fit_groups':sorted(self.fit_groups),'calibration_groups':sorted(self.calibration_groups),
                   'training_history':self.training_history,'identity':self.model_identity()}
        torch.save(payload,path)

    @classmethod
    def load(cls,path,encoder):
        saved = torch.load(path,map_location='cpu',weights_only=True)
        if saved['encoder_identity'] != encoder.identity:
            raise ValueError('saved scorer encoder identity mismatch')
        result = cls(encoder,saved['corpus'],saved['hidden'],saved['dropout'])
        result.component_head.load_state_dict(saved['component_head'])
        result.relation_head.load_state_dict(saved['relation_head'])
        result.calibrators = {k:PlattCalibrator(**v) for k,v in saved['calibrators'].items()}
        result.fit_groups = set(saved['fit_groups']); result.calibration_groups = set(saved['calibration_groups'])
        result.training_history = saved['training_history']
        if result.model_identity() != saved['identity']:
            raise ValueError('scorer checkpoint integrity mismatch')
        result.eval()
        return result


def fit_scorer(scorer, examples: Sequence[ScoringExample], epochs=10, lr=.001,
               seed=17, batch_size=256, require_oof=False):
    if epochs < 1 or batch_size < 1 or lr <= 0: raise ValueError('invalid fit hyperparameters')
    _check_examples(examples,{'fit','train','oof_fit'})
    if not any(e.pool.components or e.pool.relations for e in examples):
        raise ValueError('no candidate objects for scorer fitting')
    groups = {_group(x.document) for x in examples}
    if groups & scorer.calibration_groups:
        raise ValueError('fit/calibration source-group overlap')
    if require_oof:
        for example in examples:
            sources = example.pool.metadata.get('oof_sources') or [example.pool.metadata.get('oof',{})]
            heldout = _group(example.document)
            for provenance in sources:
                if provenance.get('held_out_source_group') != heldout or 'trained_source_groups' not in provenance:
                    raise ValueError('OOF provenance missing')
                if heldout in provenance['trained_source_groups']:
                    raise ValueError('OOF held-out source was used for fitting')
                if heldout in provenance.get('span_trained_source_groups',[]):
                    raise ValueError('OOF held-out source was used for span fitting')
    parameters = list(scorer.component_head.parameters())+list(scorer.relation_head.parameters())
    optimizer = torch.optim.AdamW(parameters,lr=lr)
    rng = random.Random(seed)
    torch.manual_seed(seed)
    history = []
    for epoch in range(epochs):
        scorer.train()
        order = list(examples); rng.shuffle(order)
        total_loss=0.; total_objects=0
        for example in order:
            if example.document.corpus != scorer.corpus: raise ValueError('corpus mismatch')
            encoding = scorer.encoder.encode(example.document.input)
            spans = sorted({(c.start,c.end) for c in example.pool.components})
            for family,objects in (('component',spans),('relation',list(example.pool.relations))):
                for begin in range(0,len(objects),batch_size):
                    batch = objects[begin:begin+batch_size]
                    if family == 'component':
                        features = torch.stack([scorer.component_features(encoding,*s) for s in batch])
                        target = torch.tensor([component_target(s,example.document.gold,scorer.corpus) for s in batch],device=scorer.device)
                        loss = nn.functional.cross_entropy(scorer.component_head(features),target)
                    else:
                        features = torch.stack([scorer.relation_features(encoding,r) for r in batch])
                        target = torch.tensor([relation_target(r,example.document.gold) for r in batch],device=scorer.device,dtype=torch.float32)
                        loss = nn.functional.binary_cross_entropy_with_logits(scorer.relation_head(features).flatten(),target)
                    if not torch.isfinite(loss): raise ValueError('nonfinite scorer loss')
                    optimizer.zero_grad(); loss.backward(); optimizer.step()
                    total_loss += float(loss.detach())*len(batch); total_objects += len(batch)
        history.append({'epoch':epoch+1,'loss':total_loss/max(1,total_objects),'objects':total_objects})
    scorer.fit_groups.update(groups); scorer.training_history.extend(history)
    # Refitting invalidates previous calibration; no stale calibrated flags.
    scorer.calibrators = {'component':PlattCalibrator(),'relation':PlattCalibrator()}
    scorer.calibration_groups.clear(); scorer._score_cache.clear(); scorer.eval()
    return history


def fit_calibrators(scorer, examples: Sequence[ScoringExample]):
    _check_examples(examples,{'calibration'})
    groups = {_group(x.document) for x in examples}
    if groups & scorer.fit_groups:
        raise ValueError('fit/calibration source-group overlap')
    logits={'component':[],'relation':[]}; labels={'component':[],'relation':[]}
    for example in examples:
        metadata = example.pool.metadata
        if metadata.get('candidate_scope') == 'unpruned_oof_training_side':
            raise ValueError('calibration pool must reproduce deployment pruning first')
        if (not example.natural_distribution or example.sampling_probability != 1.
                or metadata.get('natural_distribution',True) is not True
                or metadata.get('sampling_probability',1.) != 1.):
            raise ValueError('calibration requires unsampled natural candidate distribution')
        cs,rs = scorer.raw_scores(example.pool)
        for family,objects in (('component',cs),('relation',rs)):
            for obj,value in objects.items():
                if value is None: continue
                logits[family].append(value)
                labels[family].append(int(obj in (example.document.gold.components if family=='component' else example.document.gold.relations)))
    fitted = {family:PlattCalibrator().fit(logits[family],labels[family]) for family in logits}
    scorer.calibrators = fitted; scorer.calibration_groups = groups; scorer._score_cache.clear()
    return {family:{**value.to_dict(),'observations':len(logits[family])} for family,value in fitted.items()}


def prune_pool_for_calibration(scorer, pool, supplement_slots=4096, preflight_slot_limit=50000):
    """Reproduce deployment slot pruning without reading labels or recalibrating.

    Apply independently to each generator's unpruned pool, before pooling
    natural calibration observations. Do not union generator pools first: that
    changes their protection sets and deployment candidate distribution.
    """
    from dataclasses import replace
    if not isinstance(pool.doc,InputDocument): raise TypeError('pruning is annotation blind')
    if supplement_slots < 0: raise ValueError('negative supplementary slot budget')
    slots = {r.slot for r in pool.relations}
    if len(slots)>preflight_slot_limit: raise ValueError('preflight slot overflow')
    protected = {r.slot for r in pool.protected_relations} | {r.slot for r in pool.initial.relations}
    if not protected <= slots: raise ValueError('initial/protected slot missing from universe')
    objects = set(pool.relations)
    for slot in slots:
        if any(Relation(*slot,label) not in objects for label in LABELS[pool.doc.corpus]):
            raise ValueError('incomplete native labels in candidate slot')
    supplements = slots-protected
    before = len(supplements)
    if before>supplement_slots:
        relations = tuple(r for r in pool.relations if r.slot in supplements)
        values = scorer.score_relations_for_pruning(pool.doc,pool.components,relations)
        ranks = {}
        for slot in supplements:
            qs = [values.get(Relation(*slot,label)) for label in LABELS[pool.doc.corpus]]
            if any(q is None or not math.isfinite(q) or not 0<=q<=1 for q in qs):
                raise ValueError('missing score for calibration slot pruning')
            ranks[slot] = max(qs)
        supplements = set(sorted(supplements,key=lambda s:(-ranks[s],s))[:supplement_slots])
    retained = protected|supplements
    relations = tuple(r for r in pool.relations if r.slot in retained)
    metadata = {**pool.metadata,'candidate_scope':'deployment_pruned',
                'calibration_pruning':{'supplement_slots':supplement_slots,
                    'supplementary_slots_before':before,'supplementary_slots_after':len(supplements),
                    'protected_slots':len(protected),'raw_scorer_identity':scorer.model_identity(False),
                    'rank_transform':'uncalibrated_sigmoid_fixed_before_calibration',
                    'labels_accessed':False,'source_pool_key':pool.key}}
    return replace(pool,relations=relations,
                   protected_relations=frozenset(r for r in relations if r.slot in protected),metadata=metadata)
