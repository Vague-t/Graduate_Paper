"""Every costly stage is an explicit resumable command with a run manifest."""
import argparse, json, time, sys, dataclasses, gc
from pathlib import Path
from collections import defaultdict
from dataclasses import replace,asdict
from .schema import *
from .io import *

def config(path):return read_json(path) if path else {}
def _encoder(cfg):
    from .scoring import TinyTextEncoder,HFTextEncoder
    cfg=dict(cfg)
    if cfg.pop('backend','hf')=='tiny':return TinyTextEncoder(**cfg)
    four=cfg.pop('four_bit',False);dtype=cfg.pop('dtype','float32')
    import torch
    cfg['torch_dtype']=getattr(torch,dtype)
    if four:
        from transformers import BitsAndBytesConfig
        if cfg.get('device')!='cuda':raise ValueError('4bit encoder requires CUDA')
        cfg['quantization_config']=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=cfg['torch_dtype'])
        cfg['device_map']={'':'cuda:0'}
    return HFTextEncoder(**cfg)

def _views(path):
    from .augmentation import AugmentedView
    out=defaultdict(list)
    if path:
        for row in read_jsonl(path):
            v=AugmentedView.from_dict(row);out[v.source_doc_id].append(v)
    return out

def _validate_oof(pool, document):
    sources=pool.metadata.get('oof_sources') or [pool.metadata.get('oof',{})]
    if not document.source_group or not sources:
        raise ValueError('missing OOF source group')
    for source in sources:
        trained=source.get('trained_source_groups')
        span_trained=source.get('span_trained_source_groups')
        if (source.get('held_out_source_group')!=document.source_group
                or not isinstance(trained,list) or not trained
                or not isinstance(span_trained,list) or not span_trained
                or any(not isinstance(g,str) or not g for g in [*trained,*span_trained])
                or document.source_group in trained or document.source_group in span_trained):
            raise ValueError('invalid OOF generator/span training provenance')


def _examples(data,pool_files,require_oof=True,merge=True):
    """Join native inputs strictly; only fit pools may be unioned across generators."""
    from .scoring import ScoringExample
    docs={d.doc_id:d for d in load_documents(data)};pools=defaultdict(list)
    if len({str(Path(f).resolve()) for f in pool_files})!=len(pool_files):
        raise ValueError('duplicate candidate input files')
    for f in pool_files:
        seen=set()
        for row in read_jsonl(f):
            if row['doc_id'] in seen:raise ValueError('duplicate candidate document row in one source')
            seen.add(row['doc_id'])
            if row['doc_id'] not in docs:continue  # OOF files cover fit/calibration/policy together.
            d=docs[row['doc_id']]
            if row['status']!='ok':
                if row.get('input_sha256')!=digest(d.input.to_dict()):
                    raise ValueError('failed candidate input identity mismatch')
                metadata={**row.get('metadata',{}),'candidate_failure':row['status']}
                pools[d.doc_id].append(CandidatePool(d.input,(),(),Graph(),metadata=metadata))
            else:
                pool=load_pool(row['pool'])
                if pool.doc!=d.input:raise ValueError('scorer full input identity mismatch')
                pools[d.doc_id].append(pool)
    if set(pools)!=set(docs):raise ValueError('candidate inputs incomplete for scorer split')
    out=[]
    for ident,pp in sorted(pools.items()):
        d=docs[ident]
        for pool in pp:
            if pool.doc!=d.input:raise ValueError('scorer full input identity mismatch')
            if require_oof:_validate_oof(pool,d)
            probability=pool.metadata.get('sampling_probability',1.)
            if isinstance(probability,bool) or not isinstance(probability,(int,float)) or not 0<probability<=1:
                raise ValueError('invalid candidate sampling probability')
        if not merge:
            # Separate generator observations are repeated in proportion to their
            # actual deployment occurrences; no deduplication across generators.
            for pool in pp:
                natural=pool.metadata.get('natural_distribution') is True
                probability=pool.metadata.get('sampling_probability',1.)
                if not natural or probability!=1.:
                    raise ValueError('calibration requires declared natural candidate distribution')
                out.append(ScoringExample(d,pool,natural,probability))
            continue
        cc=tuple(sorted(set(c for pool in pp for c in pool.components)))
        rr=tuple(sorted(set(r for pool in pp for r in pool.relations)))
        sources=[source for pool in pp for source in (pool.metadata.get('oof_sources') or [pool.metadata.get('oof',{})])]
        natural=all(pool.metadata.get('natural_distribution') is True and pool.metadata.get('sampling_probability',1.)==1. for pool in pp)
        meta={'oof':sources[0],'oof_sources':sources,'natural_distribution':natural,
              'candidate_scope':'training_generator_union','generator_mixture_size':len(pp),
              'source_pool_keys':[pool.key for pool in pp],
              'source_candidate_scopes':[pool.metadata.get('candidate_scope') for pool in pp]}
        pool=CandidatePool(d.input,cc,rr,pp[0].initial,
             frozenset(c for item in pp for c in item.protected_components),
             frozenset(r for item in pp for r in item.protected_relations),meta)
        out.append(ScoringExample(d,pool,natural))
    return out


def _input_files(args):
    """Bind direct files, checkpoint contents, and sidecar training identities."""
    files=set()
    for name in ('data','inputs','adapter','views','ranked','generations','groups','scorer','span',
                 'scores','policy','gold','predictions','comparisons','config'):
        value=getattr(args,name,None)
        if not value:continue
        path=Path(value)
        if path.is_file():files.add(path)
        elif path.is_dir():files.update(p for p in path.rglob('*') if p.is_file())
        if name in ('adapter','ranked','generations','span'):
            identity=path.parent/'training_identity.json'
            if identity.is_file():files.add(identity)
    for value in [*(getattr(args,'pools',[]) or []),*(getattr(args,'counts',[]) or [])]:
        files.add(Path(value))
    return sorted(files,key=str)

def execute(args):
    cfg=config(getattr(args,'config',None));cmd=args.command
    if cmd=='prepare':
        from .data import prepare
        p=Path(args.raw);result=prepare(args.out,p/'aaec_brat.zip',p/'aaec_split.csv',p/'cdcp_acl17.zip',args.seed)
        print(json.dumps(result['statistics'],ensure_ascii=False,indent=2));return
    if cmd=='plan':
        from .workflow import make_plan
        print(make_plan(args.data,args.config,args.out,args.corpus,args.seeds));return
    if cmd=='run-plan':
        from .workflow import run_plan
        run_plan(args.plan,args.resume,args.timeout);return
    run=Run(args.out,cmd,cfg,_input_files(args))
    try:
        if cmd=='train':
            from .modeling import ExtractionModel,ModelConfig
            from .training import TrainingConfig,train
            docs=load_documents(args.data)
            if any(d.split!='train' for d in docs):raise ValueError('generator must receive explicit train split, never test')
            mc=ModelConfig(**cfg.get('model',{}));tc=TrainingConfig(**{**cfg.get('training',{}),'variant':args.variant,'seed':args.seed})
            mc.seed=args.seed;model=ExtractionModel(mc)
            vv=_views(args.views)
            if any(k not in {d.doc_id for d in docs} for k in vv):raise ValueError('views include source outside training fold')
            result=train(model,docs,vv,tc,run.path/'adapter')
            identity={'source_groups':sorted({d.source_group for d in docs}),'document_ids':[d.doc_id for d in docs],'variant':args.variant,'seed':args.seed,'data_sha256':file_hash(args.data),'views_sha256':file_hash(args.views) if args.views else None}
            write_json(run.path/'adapter'/'training_identity.json',identity)
            write_json(run.path/'training_identity.json',identity)
            run.finish(training_result=result)
        elif cmd=='augment':
            from .augmentation import select_rewrite_set,review_view,ViewRejected,build_generation_payload
            from .chat import HFChatBackend,ChatConfig,json_response
            docs=load_documents(args.data)
            if any(d.split!='train' for d in docs):raise ValueError('augment only official training sources')
            backend=HFChatBackend(ChatConfig(**cfg['chat']));views=[];attempts=[]
            def reviewer(request):
                prompt='Perform the requested blind semantic classification. Return ONLY JSON {"label":"..."}. Choose from allowed_labels if provided; if uncertain return UNKNOWN. Compare meaning in full document context, including negation, modality, role and reference.\n'+canonical_json(request)
                return json_response(backend(prompt))
            for d in docs:
                A,selection=select_rewrite_set(d);accepted=0
                if not A:
                    attempts.append({'doc_id':d.doc_id,'attempt':None,'accepted':False,'reason':'no_components_skip_augmentation'})
                    continue
                for attempt in range(cfg.get('augmentation',{}).get('attempts',4)):
                    if accepted>=cfg.get('augmentation',{}).get('accepted',2):break
                    catalog={f'c{i}':c for i,c in enumerate(d.gold.components) if c in A}
                    try:
                        payload=build_generation_payload(d,A,max_factors=cfg.get('training',{}).get('max_factors',50000))
                        prompt='Paraphrase ONLY each listed component slot while preserving its complete meaning, native type/attributes, argumentative role, negation, modality, reference, and all auditable relation states in the declared influence domain. Read the full endpoint catalogue, explicit positive relations, semantic-unknown exceptions, and finite NONE complement. Return ONLY a JSON object with a replacements object mapping every ID in slots to its new text. Do not add explanations or a graph.\n'+canonical_json(payload)
                        raw=json_response(backend(prompt,temperature=.7));mapping=raw['replacements']
                        if set(mapping)!=set(catalog):raise ValueError('replacement ids mismatch')
                        view=review_view(d,{catalog[k]:v for k,v in mapping.items()},reviewer,mode=args.mode,variant_id=f'{args.mode}-{attempt}',reviewer_id=canonical_json(backend.identity))
                        views.append(view.to_dict());accepted+=1
                        attempts.append({'doc_id':d.doc_id,'attempt':attempt,'accepted':True,'audit':view.audit})
                    except (ValueError,RuntimeError,KeyError) as exc:
                        attempts.append({'doc_id':d.doc_id,'attempt':attempt,'accepted':False,'reason':str(exc),'audit':getattr(exc,'audit',{})})
            write_jsonl(run.path/'views.jsonl',views);write_jsonl(run.path/'attempts.jsonl',attempts);write_json(run.path/'model_calls.json',backend.records)
            run.finish(accepted_views=len(views),attempts=len(attempts),backend=backend.identity)
        elif cmd=='span-train':
            from .proposals import SpanProposer,fit_span_proposer
            import torch
            training_cfg=dict(cfg.get('span_training',{}))
            if getattr(args,'seed',None) is not None:training_cfg['seed']=args.seed
            effective_seed=training_cfg.get('seed',17)
            docs=load_documents(args.data);enc=_encoder(cfg['encoder']);torch.manual_seed(effective_seed)
            model=SpanProposer(enc,args.corpus,**cfg.get('head',{}))
            history=fit_span_proposer(model,docs,**training_cfg);model.save(run.path/'span')
            write_json(run.path/'history.json',history);write_json(run.path/'training_identity.json',{'source_groups':sorted({d.source_group for d in docs}),'data_sha256':file_hash(args.data)})
            run.finish(documents=len(docs),effective_seed=effective_seed,training_config=training_cfg)
        elif cmd=='generate':
            from .modeling import ExtractionModel,parse_generated_graph
            docs=load_inputs(args.inputs)
            identity=Path(args.adapter).parent/'training_identity.json'
            if not identity.exists():raise ValueError('adapter has no training source identity')
            training_identity=read_json(identity)
            model=ExtractionModel.from_adapter(args.adapter,device=cfg['model'].get('device','cpu'))
            rows=[];generation=cfg.get('generation',{})
            base_seed=int(generation.get('seed',training_identity.get('seed',17)))
            for d in docs:
                samples=[]
                for i in range(generation.get('candidates',3)):
                    raw='';model.last_generation={}
                    sample_seed=(base_seed+int(digest({'doc_id':d.doc_id,'candidate':i})[:12],16))%(2**63-1)
                    try:
                        raw=model.generate(d,max_new_tokens=generation.get('max_new_tokens',2048),
                            temperature=0. if i==0 else generation.get('temperature',.7),
                            top_p=generation.get('top_p',.9),seed=sample_seed)
                        graph=parse_generated_graph(raw,d)
                        samples.append({'status':'ok','raw':raw,'graph':graph.to_dict(),
                                        'seed':sample_seed,'usage':dict(model.last_generation)})
                    except (ValueError,RuntimeError) as exc:
                        samples.append({'status':'generation_failed','error':str(exc),'raw':raw,
                                        'seed':sample_seed,'usage':dict(model.last_generation)})
                rows.append({'doc_id':d.doc_id,'input_sha256':digest(d.to_dict()),'samples':samples})
            write_jsonl(run.path/'generations.jsonl',rows)
            write_json(run.path/'training_identity.json',training_identity)
            run.finish(documents=len(docs),parsed_graphs=sum(s['status']=='ok' for r in rows for s in r['samples']),
                       generation_seed=base_seed,model=model.parameter_manifest())
        elif cmd=='rank':
            from .chat import HFChatBackend,ChatConfig,RelationVerifier
            from .legacy import LegacyConfig,select_initial,repair_legacy,rerun_callback
            docs=load_inputs(args.inputs);raw={r['doc_id']:r for r in read_jsonl(args.generations)}
            if set(raw)!={d.doc_id for d in docs}:raise ValueError('generation doc ids differ')
            backend=HFChatBackend(ChatConfig(**cfg['chat']));judge=RelationVerifier(backend);lc=LegacyConfig(**cfg.get('legacy',{}));rows=[];preds=[]
            for d in docs:
                rr=raw[d.doc_id]
                if rr['input_sha256']!=digest(d.to_dict()):raise ValueError('generation input hash mismatch')
                graphs=[Graph.from_dict(s['graph']) for s in rr['samples'] if s['status']=='ok']
                try:
                    initial,ranking=select_initial(d,graphs,judge,lc)
                    row={'doc_id':d.doc_id,'status':'ok','initial':initial.to_dict(),'candidates':[g.to_dict() for g in graphs],'ranking':ranking,'input_sha256':digest(d.to_dict())}
                    if args.with_i0:
                        final,ledger,meta=repair_legacy(d,initial,graphs,judge,rerun_callback(backend),lc)
                        preds.append({'doc_id':d.doc_id,'status':'ok','graph':final.to_dict(),'input_sha256':digest(d.to_dict()),'ledger':ledger,'metadata':meta})
                except (ValueError,RuntimeError) as exc:
                    row={'doc_id':d.doc_id,'status':'initial_failed','error':str(exc),'input_sha256':digest(d.to_dict())}
                    if args.with_i0:preds.append({'doc_id':d.doc_id,'status':'initial_failed','graph':Graph().to_dict(),'input_sha256':digest(d.to_dict())})
                rows.append(row)
            write_jsonl(run.path/'ranked.jsonl',rows);write_jsonl(run.path/'i0_predictions.jsonl',preds);write_json(run.path/'model_calls.json',backend.records)
            write_json(run.path/'training_identity.json',read_json(Path(args.generations).parent/'training_identity.json'))
            run.finish(documents=len(rows),backend=backend.identity)
        elif cmd=='groups':
            from .chat import HFChatBackend,ChatConfig
            from .proposals import SpanProposer,build_group_prompt,parse_group_proposals
            from .candidates import CandidateConfig
            docs=load_inputs(args.inputs);ranked={r['doc_id']:r for r in read_jsonl(args.ranked)}
            if set(ranked)!={d.doc_id for d in docs}:raise ValueError('ranked/group doc ids differ')
            ccfg=CandidateConfig(**cfg.get('candidates',{}));catalogs={};errors={}
            # Encode all proposal catalogs, then release the frozen encoder before
            # loading an independent chat model on a single 24 GB accelerator.
            if any(d.corpus=='cdcp' for d in docs):
                enc=_encoder(cfg['encoder']);span=SpanProposer.load(args.span,enc)
                for d in docs:
                    if d.corpus!='cdcp':continue
                    row=ranked[d.doc_id]
                    try:
                        if row.get('input_sha256')!=digest(d.to_dict()):raise ValueError('ranking input hash mismatch')
                        if row['status']!='ok':raise ValueError(row['status'])
                        components={c for graph in row['candidates'] for c in Graph.from_dict(graph).components}
                        components.update(Graph.from_dict(row['initial']).components)
                        supplements=span.propose(d,max_spans=ccfg.supplement_spans,
                            max_tokens=ccfg.max_span_tokens,types_per_span=ccfg.supplement_types_per_span)
                        for proposal in supplements:
                            components.update(Component(proposal.start,proposal.end,typ) for typ in proposal.type_scores)
                        catalogs[d.doc_id]=tuple(sorted(components))
                    except (ValueError,RuntimeError) as exc:errors[d.doc_id]=str(exc)
                del span,enc
                gc.collect()
                import torch
                if torch.cuda.is_available():torch.cuda.empty_cache()
            backend=HFChatBackend(ChatConfig(**cfg['chat'])) if catalogs else None
            rows=[]
            for d in docs:
                groups=[];status='ok';error=errors.get(d.doc_id);raw=None
                if error:status='proposal_failed'
                elif d.corpus=='cdcp':
                    try:
                        components=catalogs[d.doc_id]
                        raw=backend(build_group_prompt(d,components,ccfg.cdcp_model_group_proposals))
                        groups=parse_group_proposals(raw,d,components,ccfg.cdcp_model_group_proposals)
                    except (ValueError,RuntimeError) as exc:status='proposal_failed';error=str(exc)
                rows.append({'doc_id':d.doc_id,'input_sha256':digest(d.to_dict()),'status':status,
                    'error':error,'raw':raw,'component_catalog':[c.to_dict() for c in catalogs.get(d.doc_id,())],
                    'groups':[{'sources':[c.to_dict() for c in g.sources],'target':g.target.to_dict(),'score':g.score} for g in groups]})
            write_jsonl(run.path/'groups.jsonl',rows)
            if backend:write_json(run.path/'model_calls.json',backend.records)
            run.finish(documents=len(rows),backend=backend.identity if backend else None,
                       proposal_catalog='candidate_graphs_plus_frozen_span_top_types')
        elif cmd=='build-pools':
            from .candidates import CandidateConfig,build_candidates,GroupProposal,CandidateConstructionError
            from .proposals import SpanProposer
            from .scoring import ObjectScorer
            docs=load_inputs(args.inputs);ranked={r['doc_id']:r for r in read_jsonl(args.ranked)}
            groups={r['doc_id']:r for r in read_jsonl(args.groups)} if args.groups else {}
            enc=_encoder(cfg['encoder']);span=SpanProposer.load(args.span,enc);scorer=ObjectScorer.load(args.scorer,enc) if args.scorer else None
            cc=CandidateConfig(**cfg.get('candidates',{}))
            if args.oof:
                if any(d.split not in ('fit','calibration','policy') for d in docs):raise ValueError('unpruned OOF pool only on training-side heldouts')
                cc=replace(cc,supplement_slots=cc.preflight_slot_limit)
            gen_identity=read_json(Path(args.ranked).parent/'training_identity.json');span_identity=read_json(Path(args.span).parent/'training_identity.json')
            if args.oof and set(gen_identity['source_groups'])!=set(span_identity['source_groups']):raise ValueError('OOF generator/span training groups differ')
            def comp(d):return Component(d['start'],d['end'],d['type'])
            rows=[]
            for d in docs:
                provenance={'held_out_source_group':d.source_group,'trained_source_groups':gen_identity['source_groups'],'span_trained_source_groups':span_identity['source_groups']}
                if args.oof and d.source_group in provenance['trained_source_groups']:raise ValueError('OOF source leakage')
                try:
                    r=ranked[d.doc_id]
                    if r['status']!='ok':raise ValueError(r['status'])
                    if r['input_sha256']!=digest(d.to_dict()):raise ValueError('ranking input hash mismatch')
                    gg=groups.get(d.doc_id,{'status':'ok','groups':[]})
                    if d.corpus=='cdcp' and (not args.groups or gg['status']!='ok'):raise ValueError('CDCP group proposer missing/failed')
                    if d.corpus=='cdcp' and gg.get('input_sha256')!=digest(d.to_dict()):raise ValueError('group proposal input hash mismatch')
                    initial=Graph.from_dict(r['initial']);graphs=[Graph.from_dict(g) for g in r['candidates']]
                    gps=[GroupProposal(tuple(comp(c) for c in g['sources']),comp(g['target']),g['score']) for g in gg['groups']]
                    sps=span.propose(d,max_spans=cc.supplement_spans,max_tokens=cc.max_span_tokens,types_per_span=cc.supplement_types_per_span)
                    fn=(lambda rels:scorer.pruning_relation_scores(d,tuple({c for rel in rels for c in rel.endpoints}),rels)) if scorer else None
                    pool=build_candidates(d,initial,graphs,sps,gps,cc,fn)
                    meta={**pool.metadata,'oof':provenance if args.oof else {},'candidate_scope':'unpruned_oof_training_side' if args.oof else 'deployment_pruned','natural_distribution':True}
                    pool=replace(pool,metadata=meta);rows.append({'doc_id':d.doc_id,'status':'ok','pool':save_pool(pool)})
                except (ValueError,RuntimeError) as exc:
                    # Retain G0 on proposal/construction failure; evaluation denominator remains.
                    fallback=ranked.get(d.doc_id,{}).get('initial',Graph().to_dict())
                    rows.append({'doc_id':d.doc_id,'status':'candidate_failed','error':str(exc),'initial':fallback,'input_sha256':digest(d.to_dict()),'metadata':{'oof':provenance if args.oof else {},'natural_distribution':True,
                        'candidate_scope':'unpruned_oof_training_side' if args.oof else 'deployment_pruned'}})
            write_jsonl(run.path/'pools.jsonl',rows);run.finish(documents=len(rows),successful_pools=sum(r['status']=='ok' for r in rows))
        elif cmd in ('scorer-train','calibrate'):
            from .scoring import ObjectScorer,fit_scorer,fit_calibrators,prune_pool_for_calibration
            examples=_examples(args.data,args.pools,require_oof=True,merge=cmd=='scorer-train')
            enc=_encoder(cfg['encoder'])
            if cmd=='scorer-train':
                import torch
                training_cfg=dict(cfg.get('score_training',{}))
                if getattr(args,'seed',None) is not None:training_cfg['seed']=args.seed
                torch.manual_seed(training_cfg.get('seed',17))
                scorer=ObjectScorer(enc,args.corpus,**cfg.get('head',{}))
                history=fit_scorer(scorer,examples,require_oof=True,**training_cfg)
            else:
                scorer=ObjectScorer.load(args.scorer,enc)
                budgets=cfg.get('candidates',{})
                examples=[replace(example,pool=prune_pool_for_calibration(scorer,example.pool,
                    supplement_slots=budgets.get('supplement_slots',4096),
                    preflight_slot_limit=budgets.get('preflight_slot_limit',50000))) for example in examples]
                history=fit_calibrators(scorer,examples)
                write_jsonl(run.path/'calibration_pools.jsonl',
                    [{'doc_id':e.document.doc_id,'status':'ok','pool':save_pool(e.pool)} for e in examples])
            scorer.save(run.path/'scorer');write_json(run.path/'history.json',history)
            run.finish(documents=len({e.document.doc_id for e in examples}),candidate_observations=len(examples),
                       **({'effective_seed':training_cfg.get('seed',17),'training_config':training_cfg} if cmd=='scorer-train' else {}))
        elif cmd=='score':
            from .scoring import ObjectScorer,prune_pool_for_calibration
            enc=_encoder(cfg['encoder']);scorer=ObjectScorer.load(args.scorer,enc);rows=[]
            budgets=cfg.get('candidates',{})
            for path in args.pools:
                for row in read_jsonl(path):
                    if row['status']!='ok':rows.append(row);continue
                    pool=load_pool(row['pool'])
                    if pool.metadata.get('candidate_scope')=='unpruned_oof_training_side':
                        _validate_oof(pool,pool.doc)
                        pool=prune_pool_for_calibration(scorer,pool,
                            supplement_slots=budgets.get('supplement_slots',4096),
                            preflight_slot_limit=budgets.get('preflight_slot_limit',50000))
                    scores=scorer.score(pool)
                    rows.append({**row,'pool':save_pool(pool),'scores':save_scores(pool,scores)})
            write_jsonl(run.path/'scored.jsonl',rows);run.finish(documents=len(rows))
        elif cmd=='select-policy':
            from .policy import select_policy
            result=select_policy(load_documents(args.data),read_jsonl(args.scores),cfg.get('repair',{}),min_documents=args.min_documents)
            write_json(run.path/'policy.json',result);run.finish(enabled=result['enabled'])
        elif cmd=='repair':
            from .repair import RepairConfig,repair
            policy=read_json(args.policy) if args.policy else None
            if args.method=='I1' and not policy:raise ValueError('I1 requires training-side frozen policy; use Global for diagnostic runs')
            repaircfg={**cfg.get('repair',{}),**(policy.get('repair_config',{}) if policy else {})};rc=RepairConfig(**repaircfg);rows=[]
            for row in read_jsonl(args.scores):
                repair_start=time.monotonic()
                if row['status']!='ok':
                    rows.append({'doc_id':row['doc_id'],'status':'ok' if row.get('initial',{}).get('components') else 'candidate_failed','graph':row.get('initial',Graph().to_dict()),'input_sha256':row.get('input_sha256'),'repair_status':row['status']});continue
                pool=load_pool(row['pool']);scores=load_scores(pool,row['scores'])
                if args.method=='NoRisk':
                    from .repair import repair_no_risk
                    result=repair_no_risk(pool,scores,rc)
                    graph=result.graph;status=result.status;ledger=result.ledger;metadata=result.metadata
                elif policy and not policy['enabled']:
                    graph=pool.initial;status='policy_no_repair';ledger=[];metadata={}
                else:
                    result=repair(pool,scores,rc,method=args.method);graph=result.graph;status=result.status;ledger=result.ledger;metadata=result.metadata
                rows.append({'doc_id':row['doc_id'],'status':'ok','repair_status':status,'repair_elapsed_seconds':time.monotonic()-repair_start,'graph':graph.to_dict(),'input_sha256':digest(pool.doc.to_dict()),'pool_key':pool.key,'ledger':ledger,'metadata':metadata})
            write_jsonl(run.path/'predictions.jsonl',rows);run.finish(documents=len(rows),repair_method=args.method)
        elif cmd=='evaluate':
            from .evaluation import evaluate
            summary,rows=evaluate(load_documents(args.gold),read_jsonl(args.predictions),args.method,args.seed,require_input_hash=True)
            write_json(run.path/'metrics.json',summary);write_jsonl(run.path/'counts.jsonl',rows);run.finish(summary=summary)
        elif cmd=='bootstrap':
            from .evaluation import paired_bootstrap
            rows=[r for p in args.counts for r in read_jsonl(p)]
            result=paired_bootstrap(rows,read_json(args.comparisons),args.repetitions,args.seed)
            write_json(run.path/'statistics.json',result);run.finish(primary_family_size=result['primary_family_size'])
        elif cmd=='smoke':
            from .smoke import smoke
            report=smoke(run.path,cfg,args.pretrained);run.finish(**report)
        else:raise ValueError('unknown command')
    except BaseException as exc:run.fail(exc);raise

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--raw',required=True);a.add_argument('--out',required=True);a.add_argument('--seed',type=int,default=17)
    for name in ('train','augment','span-train','generate','rank','groups','build-pools','scorer-train','calibrate','score','select-policy','repair','evaluate','bootstrap','smoke'):
        a=sub.add_parser(name);a.add_argument('--out',required=True);a.add_argument('--config')
        if name in ('train','augment','span-train','scorer-train','calibrate','select-policy'):a.add_argument('--data',required=True)
        if name in ('generate','rank','groups','build-pools'):a.add_argument('--inputs',required=True)
        if name=='train':
            a.add_argument('--views');a.add_argument('--variant',default='T1',choices=['T0','Heads','NoPair','CompPair','T1']);a.add_argument('--seed',type=int,default=17)
        if name=='augment':a.add_argument('--mode',default='factor',choices=['factor','full'])
        if name in ('span-train','scorer-train'):
            a.add_argument('--corpus',choices=list(TYPES),required=True);a.add_argument('--seed',type=int)
        if name=='generate':a.add_argument('--adapter',required=True)
        if name=='rank':a.add_argument('--generations',required=True);a.add_argument('--with-i0',action='store_true')
        if name in ('groups','build-pools'):a.add_argument('--ranked',required=True)
        if name in ('groups','build-pools'):a.add_argument('--span',required=True)
        if name=='build-pools':a.add_argument('--groups');a.add_argument('--scorer');a.add_argument('--oof',action='store_true')
        if name in ('scorer-train','calibrate','score'):a.add_argument('--pools',nargs='+',required=True)
        if name in ('calibrate','score'):a.add_argument('--scorer',required=True)
        if name in ('select-policy','repair'):a.add_argument('--scores',required=True)
        if name=='select-policy':a.add_argument('--min-documents',type=int,default=10)
        if name=='repair':a.add_argument('--policy');a.add_argument('--method',default='I1',choices=['I1','Global','Single','SetLocal','RelationOnly','Sequential','NoRisk'])
        if name=='evaluate':
            a.add_argument('--gold',required=True);a.add_argument('--predictions',required=True);a.add_argument('--method',required=True);a.add_argument('--seed',type=int,default=17)
        if name=='bootstrap':
            a.add_argument('--counts',nargs='+',required=True);a.add_argument('--comparisons',required=True);a.add_argument('--repetitions',type=int,default=2000);a.add_argument('--seed',type=int,default=20261012)
        if name=='smoke':a.add_argument('--pretrained',action='store_true')
    a=sub.add_parser('plan');a.add_argument('--data',required=True);a.add_argument('--config',required=True);a.add_argument('--out',required=True);a.add_argument('--corpus',choices=['aaec','cdcp','both'],default='both');a.add_argument('--seeds',nargs='+',type=int,default=[17,29,43])
    a=sub.add_parser('run-plan');a.add_argument('--plan',required=True);a.add_argument('--resume',action='store_true');a.add_argument('--timeout',type=int,default=172800)
    execute(p.parse_args())

if __name__=='__main__':main()
