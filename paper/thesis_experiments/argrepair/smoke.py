"""Executed software diagnostics, explicitly separate from benchmark evidence."""
from pathlib import Path
from dataclasses import replace
import gc, math, time
import torch
from .schema import Component as C, Relation as R, Graph, InputDocument, Document, CandidatePool, digest
from .io import write_json, write_jsonl, load_documents, save_pool, save_scores, load_pool, load_scores


def fixture(corpus='cdcp', split='train', group='fixture-train'):
    text='Alpha. Beta. Gamma.'
    labels=('fact','value','policy') if corpus=='cdcp' else ('Premise','Premise','Claim')
    a,b,c=(C(s,e,t) for (s,e),t in zip(((0,6),(7,12),(13,19)),labels))
    r=R((a,b) if corpus=='cdcp' else (a,),c,'reason' if corpus=='cdcp' else 'supports')
    return Document(InputDocument(group,corpus,text,group,split),Graph((a,b,c),(r,)))


def diagnostic_pool(doc):
    """Gold plus perturbations ONLY for software debugging, never production OOF."""
    from .schema import TYPES,LABELS
    a,b,c=doc.gold.components[:3] if len(doc.gold.components)>=3 else (*doc.gold.components,doc.gold.components[0])
    wrong=C(a.start+1,a.end,a.label)
    label=next(t for t in TYPES[doc.corpus] if t!=a.label)
    typed=C(a.start,a.end,label)
    cs=tuple(sorted(set((*doc.gold.components,wrong,typed))))
    rr=set(doc.gold.relations)
    for r in doc.gold.relations:
        rr.add(R(r.sources,r.target,next(x for x in LABELS[doc.corpus] if x!=r.label)))
        if len(r.sources)>1:rr.add(R((r.sources[0],),r.target,r.label))
    rr.add(R((b,),a,LABELS[doc.corpus][0]))
    return CandidatePool(doc.input,cs,tuple(sorted(rr)),doc.gold,
                         frozenset(doc.gold.components),frozenset(doc.gold.relations),
                         {'evidence_type':'CONSTRUCTED_DIAGNOSTIC_POOL_USING_TRAIN_LABELS','natural_distribution':False})


def _tiny(out,cfg):
    from .modeling import ExtractionModel,ModelConfig
    from .training import train,TrainingConfig
    from .augmentation import select_rewrite_set,transport,review_view
    from .scoring import TinyTextEncoder,ObjectScorer,ScoringExample,fit_scorer,PlattCalibrator
    from .proposals import SpanProposer,fit_span_proposer
    from .repair import repair,RepairConfig,replay_ledger
    from .evaluation import evaluate
    summaries=[]
    for corpus in ('aaec','cdcp'):
        target=out/corpus;target.mkdir(parents=True,exist_ok=True);doc=fixture(corpus)
        A,_=select_rewrite_set(doc);replacements={c:doc.text[c.start:c.end]+' yes' for c in A}
        changed,phi=transport(doc,replacements)
        def fixture_reviewer(request):
            # Deliberately an oracle fixture for testing masks and data flow.
            # The real augment CLI uses an independent blind HF reviewer.
            if request['task']=='component_meaning':return 'SAME'
            d=doc if request['text']==doc.text else changed
            if request['task']=='component_type':
                span=request['span'];return next(c.label for c in d.gold.components if (c.start,c.end)==(span['start'],span['end']))
            sources=tuple((s['start'],s['end']) for s in request['sources']);t=request['target']
            return next((r.label for r in d.gold.relations if tuple((c.start,c.end) for c in r.sources)==sources and (r.target.start,r.target.end)==(t['start'],t['end'])),'NONE')
        view=review_view(doc,replacements,fixture_reviewer,rewrite_set=A,reviewer_id='CONSTRUCTED_TEST_ORACLE_NOT_REAL_REVIEWER')
        write_jsonl(target/'views.jsonl',[view.to_dict()])
        mc=ModelConfig(backend='tiny',hidden_size=16,layers=1,attention_heads=2,head_hidden=16,lora_rank=2,
                       lora_dropout=0,head_dropout=0,max_input_tokens=512,max_output_tokens=1024,max_context=2048)
        model=ExtractionModel(mc)
        trained=train(model,[doc],{doc.doc_id:[view]},TrainingConfig(epochs=1,accumulation=1,max_steps=1),target/'training')
        assert trained['steps_completed']==1 and math.isfinite(trained['final_loss'])
        loaded=ExtractionModel.from_adapter(target/'training/checkpoint');loaded.eval();model.eval()
        assert abs(loaded.generation_loss(doc)[0].item()-model.generation_loss(doc)[0].item())<1e-6
        del model,loaded;gc.collect()
        enc=TinyTextEncoder(12);scorer=ObjectScorer(enc,corpus,hidden=16,dropout=0)
        fitdoc=replace(doc,input=replace(doc.input,split='fit'))
        caldoc=fixture(corpus,'calibration','fixture-calibration')
        hist=fit_scorer(scorer,[ScoringExample(fitdoc,diagnostic_pool(fitdoc))],epochs=2,lr=.01)
        # Exercise the optimizer on explicit constructed values. The production
        # fit_calibrators API correctly rejects these as non-natural candidates.
        cs,rs=scorer.raw_scores(diagnostic_pool(caldoc));cal={}
        for family,values,truth in [('component',cs,set(caldoc.gold.components)),('relation',rs,set(caldoc.gold.relations))]:
            objects=[o for o,v in values.items() if v is not None]
            fitted=PlattCalibrator().fit([values[o] for o in objects],[int(o in truth) for o in objects])
            scorer.calibrators[family]=fitted
            cal[family]={**fitted.to_dict(),'evidence_type':'CONSTRUCTED_CALIBRATOR_OPTIMIZER_DIAGNOSTIC','observations':len(objects)}
        scorer.calibration_groups={caldoc.source_group};scorer._score_cache.clear()
        scorer.save(target/'scorer.pt');scorer=ObjectScorer.load(target/'scorer.pt',enc)
        span=SpanProposer(enc,corpus,hidden=16,dropout=0)
        sh=fit_span_proposer(span,[doc],epochs=1)
        suggestions=span.propose(doc.input,max_spans=4)
        pool=diagnostic_pool(doc);scores=scorer.score(pool)
        write_json(target/'snapshot.json',{'pool':save_pool(pool),'scores':save_scores(pool,scores)})
        clone=load_pool(save_pool(pool));restored=load_scores(clone,save_scores(pool,scores))
        results={}
        for method in ('Global','Single','SetLocal','RelationOnly','Sequential','I1'):
            result=repair(clone,restored,RepairConfig(time_limit=5,total_time_limit=20),method)
            replay=replay_ledger(clone,restored,result.ledger)
            assert replay==result.graph
            results[method]=result.to_dict()
        summary,_=evaluate([doc],[{'doc_id':doc.doc_id,'status':'ok','graph':results['I1']['graph']}],'fixture-I1',17)
        write_json(target/'repairs.json',results)
        row={'corpus':corpus,'evidence_type':'CONSTRUCTED_SOFTWARE_DIAGNOSTIC','training_steps':trained['steps_completed'],
             'loss':trained['final_loss'],'accepted_fixture_views':1,'scorer_history':hist,'calibration':cal,
             'span_history':sh,'span_proposals':len(suggestions),'strict_metrics_on_fixture':summary,'repair_methods':list(results)}
        write_json(target/'report.json',row);summaries.append(row)
    return {'diagnostic_kind':'CONSTRUCTED_TINY_END_TO_END','benchmark_evidence':False,'corpora':summaries}


def _pretrained(out,cfg):
    from .modeling import ExtractionModel,ModelConfig,parse_generated_graph
    from .training import train,TrainingConfig
    from .scoring import HFTextEncoder,ObjectScorer,ScoringExample,fit_scorer
    from .proposals import SpanProposer,fit_span_proposer
    from .repair import repair,RepairConfig,replay_ledger
    root=Path(__file__).resolve().parent.parent
    source=Path(cfg.get('smoke',{}).get('training_data',root/'data/native_v1/cdcp_train.jsonl'))
    docs=load_documents(source)
    doc=min((d for d in docs if d.gold.relations and len(d.gold.components)>=2),key=lambda d:len(d.text))
    if doc.split!='train':raise ValueError('pretrained smoke only uses official training sources')
    mc=ModelConfig(**cfg['model']);mc.backend='hf';mc.device='cpu';mc.dtype='float32';mc.four_bit=False
    mc.head_hidden=32;mc.lora_rank=4;mc.lora_alpha=8;mc.lora_dropout=0;mc.head_dropout=0
    mc.gradient_checkpointing=True
    model=ExtractionModel(mc);model.eval()
    before=model.generation_loss(doc)[0].item()
    steps=cfg.get('smoke',{}).get('steps',1)
    trained=train(model,[doc],{},TrainingConfig(variant='T1',epochs=steps,accumulation=1,max_steps=steps),out/'training')
    assert trained['steps_completed']==steps and math.isfinite(trained['final_loss'])
    model.eval();after=model.generation_loss(doc)[0].item()
    raw=model.generate(doc.input,max_new_tokens=cfg.get('smoke',{}).get('max_new_tokens',256),seed=17)
    usage=dict(model.last_generation)
    try:
        graph=parse_generated_graph(raw,doc.input);generation={'status':'ok','graph':graph.to_dict()}
    except ValueError as exc:generation={'status':'parse_failed','error':str(exc)}
    generation.update(raw=raw,usage=usage,input_sha256=digest(doc.input.to_dict()))
    write_json(out/'generation.json',generation)
    identity=model.parameter_manifest()
    del model;gc.collect()
    loaded=ExtractionModel.from_adapter(out/'training/checkpoint',device='cpu');loaded.eval()
    reloaded=loaded.generation_loss(doc)[0].item()
    assert abs(after-reloaded)<1e-5
    del loaded;gc.collect()
    # Actual pretrained representations with deliberately constructed candidate
    # negatives. This checks optimizer/scoring interfaces, not calibrated quality.
    enc=HFTextEncoder(mc.model_name,revision=mc.revision,local_files_only=True,device='cpu',max_tokens=mc.max_input_tokens,torch_dtype=torch.float32)
    fitdoc=replace(doc,input=replace(doc.input,split='fit'))
    pool=diagnostic_pool(fitdoc)
    scorer=ObjectScorer(enc,doc.corpus,hidden=32,dropout=0)
    history=fit_scorer(scorer,[ScoringExample(fitdoc,pool)],epochs=1)
    scores=scorer.score(pool)
    assert all(q is not None and math.isfinite(q) for q in (*scores.components.values(),*scores.relations.values()))
    proposer=SpanProposer(enc,doc.corpus,hidden=32,dropout=0)
    span_history=fit_span_proposer(proposer,[doc],epochs=1)
    span_rows=proposer.propose(doc.input,max_spans=4)
    result=repair(pool,scores,RepairConfig(time_limit=5,total_time_limit=20),'Global')
    assert replay_ledger(pool,scores,result.ledger)==result.graph
    write_json(out/'score_and_repair.json',{'pool':save_pool(pool),'scores':save_scores(pool,scores),'result':result.to_dict(),
                                          'scorer_history':history,'span_history':span_history,'proposed_spans':len(span_rows)})
    report={'diagnostic_kind':'REAL_PRETRAINED_MODEL_REAL_TRAIN_SOURCE_SOFTWARE_DEBUG','benchmark_evidence':False,
            'model_identity':identity,'training_document':doc.doc_id,'source_sha256':digest(doc.to_dict()),
            'training_steps':trained['steps_completed'],'accepted_augmentation_views':0,
            'teacher_forced_generation_loss_before':before,'teacher_forced_generation_loss_after':after,
            'reloaded_loss':reloaded,'generation_status':generation['status'],'generation_usage':usage,
            'scorer_training_examples':1,'candidate_pool_origin':'CONSTRUCTED_FROM_TRAIN_GOLD_FOR_DEBUG_ONLY',
            'calibration_performed':False,'repair_status':result.status,'gpu_validation_performed':False}
    write_json(out/'report.json',report)
    return report


def smoke(out,cfg,pretrained=False):
    torch.set_num_threads(2)
    return _pretrained(Path(out),cfg) if pretrained else _tiny(Path(out),cfg)
