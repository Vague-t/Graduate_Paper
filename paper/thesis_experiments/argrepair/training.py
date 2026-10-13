"""Source-normalized Chapter 3 objectives and a real optimizer training loop."""
from dataclasses import dataclass,asdict
from pathlib import Path
import json
import math
import random
import re
import time
import torch
from torch.nn import functional as F
from .schema import Document,Component,TYPES,LABELS,digest,graph_errors
from .augmentation import AugmentedView,SlotFactor,factor_universe
from .modeling import ExtractionModel

@dataclass
class TrainingConfig:
    variant: str = 'T1'  # T0 / Heads / NoPair / CompPair / T1
    epochs: int = 5
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.03
    microbatch_sources: int = 1
    accumulation: int = 32
    gradient_clip: float = 1.0
    lambda_sentence: float = 0.5
    lambda_supervision: float = 1.0
    lambda_component: float = 0.5
    lambda_relation: float = 0.5
    seed: int = 17
    max_steps: int | None = None
    max_factors: int = 50000


def js_divergence(p_logits,q_logits):
    """Stable two-sided Jensen-Shannon divergence (no detach)."""
    logp=F.log_softmax(p_logits.float(),dim=-1);logq=F.log_softmax(q_logits.float(),dim=-1)
    logm=torch.logaddexp(logp,logq)-math.log(2)
    return .5*((logp.exp()*(logp-logm)).sum(-1)+(logq.exp()*(logq-logm)).sum(-1))


def nonempty_group_mean(positive,negative,zero):
    """Equal weights for nonempty positive/NONE groups; never divide by two blindly."""
    groups=[]
    if positive:groups.append(torch.stack(positive).mean())
    if negative:groups.append(torch.stack(negative).mean())
    return torch.stack(groups).mean() if groups else zero


def mean_or_zero(values,zero):return torch.stack(values).mean() if values else zero


def sentence_spans(text):
    spans=[];start=0
    for match in re.finditer(r'[.!?。！？]+(?:\s+|$)|\n+',text):
        end=match.end()
        if text[start:end].strip():spans.append((start,end))
        start=end
    if text[start:].strip():spans.append((start,len(text)))
    return spans


def pool_span(hidden,offsets,start,end):
    indices=[i for i,(a,b) in enumerate(offsets) if a>=0 and max(start,a)<min(end,b)]
    if not indices:raise ValueError(f'native span [{start},{end}) has no input tokens; refuse truncation')
    return hidden[indices].mean(0)


def relation_geometry(text,factor,positions=None):
    """Seven label-free geometry features, normalized evaluation token positions."""
    if positions is None:positions=evaluation_positions(text,factor.endpoints)
    source_positions=[positions[c] for c in factor.sources];target=positions[factor.target]
    return [float(len(source_positions)),min(p[0] for p in source_positions),sum(p[0] for p in source_positions)/len(source_positions),
            max(p[1] for p in source_positions),sum(p[1] for p in source_positions)/len(source_positions),target[0],target[1]]


def evaluation_positions(text,components):
    spans=[(m.start(),m.end()) for m in re.finditer(r'\w+|[^\w\s]',text)];n=max(1,len(spans));positions={}
    for c in components:
        indices=[i for i,(a,b) in enumerate(spans) if max(a,c.start)<min(b,c.end)]
        if not indices:raise ValueError('component contains no evaluation token')
        positions[c]=(min(indices)/n,(max(indices)+1)/n)
    return positions


@dataclass
class FactorPredictions:
    component_logits: dict
    relation_logits: dict
    sentence_loss: torch.Tensor
    zero: torch.Tensor


def factor_predictions(model:ExtractionModel,doc:Document,factors,include_sentence=True)->FactorPredictions:
    """Only the document/task input reaches the causal backbone.

    Gold spans select pooling windows downstream; types and relation answers
    are targets only and cannot reach the input end-state or auxiliary heads.
    """
    hidden,offsets,end=model.input_hidden(doc.text,doc.corpus)
    # Trainable head computation uses float32 even when the frozen LM is bf16.
    hidden=hidden.float();end=end.float();zero=hidden.sum()*0
    pooled={c:pool_span(hidden,offsets,c.start,c.end) for c in doc.gold.components}
    component_logits={}
    if doc.gold.components:
        features=torch.stack([torch.cat((pooled[c],end)) for c in doc.gold.components])
        outputs=model.component_heads[doc.corpus](features)
        component_logits=dict(zip(doc.gold.components,outputs))
    relation_logits={};positions=evaluation_positions(doc.text,doc.gold.components)
    active_factors=[f for f in factors if f.label is not None]
    for offset in range(0,len(active_factors),128):
        batch=active_factors[offset:offset+128];vectors=[]
        for factor in batch:
            source=torch.stack([pooled[c] for c in factor.sources]).mean(0)
            eta=torch.tensor(relation_geometry(doc.text,factor,positions),dtype=hidden.dtype,device=hidden.device)
            vectors.append(torch.cat((source,pooled[factor.target],end,eta)))
        outputs=model.relation_heads[doc.corpus](torch.stack(vectors))
        relation_logits.update(zip(batch,outputs))
    sentence_loss=zero
    if include_sentence:
        conclusion={'Claim','MajorClaim'} if doc.corpus=='aaec' else {'policy','value'}
        losses=[]
        for start,stop in sentence_spans(doc.text):
            vector=pool_span(hidden,offsets,start,stop)
            target=any(c.label in conclusion and max(c.start,start)<min(c.end,stop) for c in doc.gold.components)
            logit=model.sentence_head(vector).squeeze(-1)
            losses.append(F.binary_cross_entropy_with_logits(logit,torch.tensor(float(target),device=logit.device)))
        sentence_loss=mean_or_zero(losses,zero)
    return FactorPredictions(component_logits,relation_logits,sentence_loss,zero)


def supervised_factors(pred:FactorPredictions,corpus,components,factors):
    comps=[];pos=[];none=[]
    for c in components:
        logits=pred.component_logits[c]
        comps.append(F.cross_entropy(logits[None],torch.tensor([TYPES[corpus].index(c.label)],device=logits.device)))
    for f in factors:
        if f.label is None:continue
        logits=pred.relation_logits[f]
        target=(*LABELS[corpus],'NONE').index(f.label)
        loss=F.cross_entropy(logits[None],torch.tensor([target],device=logits.device))
        (none if f.label=='NONE' else pos).append(loss)
    return mean_or_zero(comps,pred.zero)+nonempty_group_mean(pos,none,pred.zero)


def _validate_view(doc,view):
    if view.source_doc_id!=doc.doc_id or not view.audit.get('accepted',False):raise ValueError('unaccepted or wrong-source view')
    if view.document.split!=doc.split or view.document.source_group!=doc.source_group:raise ValueError('augmentation escaped its source group')
    if view.audit.get('source_hash')!=digest(doc.to_dict()):raise ValueError('view source checksum mismatch')
    if view.audit.get('augmented_hash')!=digest(view.document.to_dict()):raise ValueError('view document checksum mismatch')
    if set(view.correspondence)!=set(doc.gold.components) or set(view.correspondence.values())!=set(view.document.gold.components):raise ValueError('incomplete component correspondence')
    if not view.rewrite_set or not all(view.component_mask.get(c,False) for c in view.rewrite_set):raise ValueError('accepted view requires reliable rewritten components')
    for f,mask in view.relation_mask.items():
        if mask and (f.label is None or not all(view.component_mask.get(c,False) for c in f.endpoints)):raise ValueError('invalid reliable relation mask')
    if not view.alignment_components<=view.component_mask.keys():raise ValueError('unknown component alignment')


def compute_source_loss(model:ExtractionModel,document:Document,views:list[AugmentedView]|None,config:TrainingConfig):
    if config.variant not in {'T0','Heads','NoPair','CompPair','T1'}:raise ValueError('unsupported training ablation')
    if document.split not in {'train','training'}:raise ValueError('training loss must not access held-out gold')
    if graph_errors(document.input,document.gold):raise ValueError('invalid training gold')
    generation,token_log=model.generation_loss(document)
    universe=factor_universe(document,max_factors=config.max_factors)
    # T0 keeps inherited objectives but no auxiliary head/factor loss.
    original=factor_predictions(model,document,universe.auditable if config.variant!='T0' else ())
    total=generation+config.lambda_sentence*original.sentence_loss
    head_loss=original.zero;calign=original.zero;ralign=original.zero
    accepted=[] if config.variant in {'T0','Heads'} else list(views or [])
    if config.variant!='T0':
        head_values=[supervised_factors(original,document.corpus,document.gold.components,universe.auditable)]
        cviews=[];rviews=[]
        for view in accepted:
            _validate_view(document,view)
            phi=view.correspondence
            reliable=[f for f in view.factors if view.relation_mask.get(f,False) and f.label is not None]
            mapped=[f.map(phi) for f in reliable]
            augmented=factor_predictions(model,view.document,mapped,include_sentence=False)
            components=[phi[c] for c in document.gold.components if view.component_mask.get(c,False)]
            head_values.append(supervised_factors(augmented,document.corpus,components,mapped))
            if config.variant in {'CompPair','T1'}:
                cviews.append(mean_or_zero([js_divergence(original.component_logits[c],augmented.component_logits[phi[c]])
                                           for c in view.alignment_components if view.component_mask.get(c,False)],original.zero))
            if config.variant=='T1':
                pos=[];none=[]
                for old,new in zip(reliable,mapped):
                    value=js_divergence(original.relation_logits[old],augmented.relation_logits[new])
                    (none if old.label=='NONE' else pos).append(value)
                rviews.append(nonempty_group_mean(pos,none,original.zero))
        head_loss=torch.stack(head_values).mean()
        calign=mean_or_zero(cviews,original.zero);ralign=mean_or_zero(rviews,original.zero)
        total=total+config.lambda_supervision*head_loss+config.lambda_component*calign+config.lambda_relation*ralign
    def number(x):return float(x.detach().cpu())
    log={'source_doc_id':document.doc_id,'variant':config.variant,'accepted_views':len(accepted),
         'loss':number(total),'generation':number(generation),'sentence':number(original.sentence_loss),
         'head_supervision':number(head_loss),'component_js':number(calign),'relation_js':number(ralign),
         'semantic_unknown_factors':len(universe.unknown),'auditable_factors':len(universe.auditable),**token_log}
    return total,log


def train(model:ExtractionModel,documents:list[Document],views_by_doc:dict[str,list[AugmentedView]]|None,
          config:TrainingConfig,output_dir):
    """Optimizer updates normalized by actual source count, including last batch.

    One source is processed at a time; microbatch_sources*accumulation determines
    the effective update size without retaining separate source graphs in memory.
    A source's original and accepted view graphs coexist until that backward.
    """
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    if not documents:raise ValueError('no training documents')
    if config.epochs<1 or config.microbatch_sources<1 or config.accumulation<1:raise ValueError('invalid training schedule')
    if config.max_steps is not None and config.max_steps<1:raise ValueError('max_steps must be positive')
    if any(doc.split not in {'train','training'} for doc in documents):raise ValueError('training contains held-out data')
    if len({doc.doc_id for doc in documents})!=len(documents):raise ValueError('duplicate training document id')
    torch.manual_seed(config.seed);rng=random.Random(config.seed);model.train()
    parameters=[p for p in model.parameters() if p.requires_grad]
    optimizer=torch.optim.AdamW(parameters,lr=config.learning_rate,weight_decay=config.weight_decay,betas=(.9,.999),eps=1e-8)
    size=config.microbatch_sources*config.accumulation
    planned=config.epochs*math.ceil(len(documents)/size)
    if config.max_steps is not None:planned=min(planned,config.max_steps)
    warmup=math.ceil(planned*config.warmup_ratio)
    def lr_scale(step):
        if warmup and step<warmup:return (step+1)/warmup
        return max(0.,(planned-step)/max(1,planned-warmup))
    scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lr_scale)
    manifest={'status':'RUNNING','kind':'REAL_OPTIMIZER_TRAINING','model':model.parameter_manifest(),'training':asdict(config),
              'sources':[{'doc_id':d.doc_id,'sha256':digest(d.to_dict())} for d in documents],
              'steps_completed':0,'sources_processed':0,'local_tiny_diagnostic':model.config.backend=='tiny',
              'device':str(model.device),'torch_version':torch.__version__,'start_unix':time.time()}
    (output/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    steps=0;sources=0;logs=[]
    try:
        with (output/'training_log.jsonl').open('w') as handle:
            for epoch in range(config.epochs):
                order=list(documents);rng.shuffle(order)
                for offset in range(0,len(order),size):
                    batch=order[offset:offset+size];optimizer.zero_grad(set_to_none=True)
                    batch_logs=[]
                    for doc in batch:
                        loss,log=compute_source_loss(model,doc,(views_by_doc or {}).get(doc.doc_id,[]),config)
                        if not bool(torch.isfinite(loss)):raise FloatingPointError('non-finite training objective')
                        (loss/len(batch)).backward();batch_logs.append(log);sources+=1
                    grad_norm=torch.nn.utils.clip_grad_norm_(parameters,config.gradient_clip,error_if_nonfinite=True)
                    lr=optimizer.param_groups[0]['lr'];optimizer.step();scheduler.step();steps+=1
                    record={'step':steps,'epoch':epoch+1,'actual_source_count':len(batch),'learning_rate':lr,'gradient_norm':float(grad_norm),
                            'mean_loss':sum(x['loss'] for x in batch_logs)/len(batch_logs),'sources':batch_logs}
                    if model.device.type=='cuda':record['peak_cuda_allocated_bytes']=torch.cuda.max_memory_allocated(model.device)
                    handle.write(json.dumps(record,ensure_ascii=False)+'\n');handle.flush();logs.append(record)
                    if config.max_steps is not None and steps>=config.max_steps:break
                if config.max_steps is not None and steps>=config.max_steps:break
        model.save_adapter(output/'checkpoint')
        torch.save({'optimizer':optimizer.state_dict(),'scheduler':scheduler.state_dict(),'steps':steps,'torch_rng':torch.get_rng_state()},output/'optimizer_state.pt')
        manifest.update(status='COMPLETED',steps_completed=steps,sources_processed=sources,end_unix=time.time(),final_loss=logs[-1]['mean_loss'])
    except Exception as exc:
        manifest.update(status='FAILED',steps_completed=steps,sources_processed=sources,end_unix=time.time(),error=type(exc).__name__+': '+str(exc))
        raise
    finally:(output/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest
