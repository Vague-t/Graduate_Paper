"""Budget-accounted full-graph regeneration; never fabricates matched resources.

Run ``python -m argrepair.regeneration --help``. A reference budget receipt must
bind real I1 usage, the same text/checkpoint and declared ceilings. A missing or
incomplete receipt cannot silently enter a matched-budget statistical comparison.
"""
from dataclasses import dataclass,asdict
from pathlib import Path
import argparse,gc,time
from .schema import InputDocument,Graph,digest,graph_errors
from .io import read_json,read_jsonl,write_json,write_jsonl,file_hash,load_inputs,Run

@dataclass(frozen=True)
class BudgetLimits:
    calls: int
    input_tokens: int
    output_tokens: int
    def __post_init__(self):
        if any(type(v) is not int or v<0 for v in asdict(self).values()):
            raise ValueError('resource limits must be nonnegative integers')

@dataclass(frozen=True)
class RegenerationConfig:
    generation_calls: int = 2
    max_new_tokens_per_call: int = 2048
    temperature: float = .7
    top_p: float = .9
    seed: int = 17
    def __post_init__(self):
        if self.generation_calls<1 or self.max_new_tokens_per_call<1:raise ValueError('positive generation limits required')

class BudgetExhausted(RuntimeError):pass

class UsageLedger:
    def __init__(self,limits):
        self.limits=limits;self.calls=self.input_tokens=self.output_tokens=0;self.records=[];self.accounting_complete=True
    @property
    def remaining_output(self):return self.limits.output_tokens-self.output_tokens
    def invoke(self,purpose,input_tokens,max_output_tokens,callback):
        """callback(allowed_output) -> (payload, actual input/output token mapping)."""
        if not self.accounting_complete:raise BudgetExhausted('previous model call has unknown resource use')
        if self.calls>=self.limits.calls:raise BudgetExhausted('additional model call limit')
        if input_tokens<0 or self.input_tokens+input_tokens>self.limits.input_tokens:raise BudgetExhausted('additional input token limit')
        allowed=min(max_output_tokens,self.remaining_output)
        if allowed<1:raise BudgetExhausted('additional output token limit')
        self.calls+=1;self.input_tokens+=input_tokens;start=time.monotonic()
        record={'call':self.calls,'purpose':purpose,'declared_input_tokens':input_tokens,'allowed_output_tokens':allowed}
        self.records.append(record)
        try:
            payload,usage=callback(allowed)
            used_input=usage.get('input_tokens');used_output=usage.get('output_tokens')
            if type(used_input) is not int or type(used_output) is not int or used_input!=input_tokens or not 0<=used_output<=allowed:
                raise ValueError('model token receipt differs from preflight/allowed budget')
            self.output_tokens+=used_output
            record.update(status='completed',input_tokens=used_input,output_tokens=used_output,elapsed_seconds=time.monotonic()-start)
            return payload
        except BaseException as exc:
            # Do not invent zero usage for a failed model call. Reserve the cap
            # conservatively and disallow formal matched-budget claims.
            self.output_tokens+=allowed;self.accounting_complete=False
            record.update(status='failed_usage_unknown',input_tokens=None,output_tokens=None,
                          charged_input_upper_bound=input_tokens,charged_output_upper_bound=allowed,
                          error=type(exc).__name__+': '+str(exc),elapsed_seconds=time.monotonic()-start)
            raise
    def summary(self):
        return {'limits':asdict(self.limits),'calls':self.calls,'input_tokens':self.input_tokens,
                'output_tokens':self.output_tokens,'accounting_complete':self.accounting_complete,'records':self.records}


def checkpoint_hash(path):
    path=Path(path)
    if path.is_file():return file_hash(path)
    files={str(p.relative_to(path)):file_hash(p) for p in sorted(path.rglob('*')) if p.is_file()}
    if not files:raise ValueError('checkpoint directory is empty')
    return digest(files)


def validate_reference(reference,doc,checkpoint_sha256,limits):
    """Verify an executed, file-bound per-document reference receipt."""
    if reference is None:return False
    expected={'doc_id':doc.doc_id,'input_sha256':digest(doc.to_dict()),'checkpoint_sha256':checkpoint_sha256,
              'reference_method':'I1','limits':asdict(limits),'accounting_complete':True}
    if any(reference.get(k)!=v for k,v in expected.items()):raise ValueError('reference budget identity/limits mismatch')
    file=Path(reference['evidence_file'])
    if file_hash(file)!=reference['evidence_sha256']:raise ValueError('reference evidence hash mismatch')
    evidence=read_json(file)
    if evidence.get('evidence_type')!='EXECUTED_CODE_OUTPUT_NOT_HISTORICAL_THESIS_RESULTS':raise ValueError('reference evidence is not an execution receipt')
    if any(evidence.get(k)!=v for k,v in expected.items()):raise ValueError('reference evidence does not bind expected protocol')
    records=evidence.get('usage_records')
    if not isinstance(records,list):raise ValueError('reference lacks actual usage records')
    totals={'calls':0,'input_tokens':0,'output_tokens':0}
    for r in records:
        if r.get('status')!='completed':raise ValueError('reference has incomplete actual usage')
        for key in totals:
            value=r.get(key,1 if key=='calls' else None)
            if type(value) is not int or value<0:raise ValueError('reference has unknown usage')
            totals[key]+=value
    if any(totals[k]>getattr(limits,k) for k in totals):raise ValueError('reference exceeded declared matched ceilings')
    # At least one source run receipt is required, not just an editable totals row.
    sources=evidence.get('source_artifacts',[])
    if not sources:raise ValueError('reference lacks source execution artifacts')
    actual=[]
    for source in sources:
        if file_hash(source['path'])!=source['sha256']:raise ValueError('reference source artifact drift')
        source_path=Path(source['path'])
        payload=read_jsonl(source_path) if source_path.suffix=='.jsonl' else read_json(source_path)
        source_records=payload if isinstance(payload,list) else payload.get('records',payload.get('usage_records'))
        if not isinstance(source_records,list):raise ValueError('source artifact lacks actual call receipts')
        indices=source.get('record_indices',list(range(len(source_records))))
        for index in indices:
            r=source_records[index]
            if r.get('doc_id',doc.doc_id)!=doc.doc_id:raise ValueError('source call receipt belongs to another document')
            actual.append({'calls':r.get('calls',1),'input_tokens':r.get('input_tokens'),
                           'output_tokens':r.get('output_tokens'),'status':r.get('status','completed')})
    normalized=[{'calls':r.get('calls',1),'input_tokens':r['input_tokens'],'output_tokens':r['output_tokens'],'status':r['status']} for r in records]
    if actual!=normalized:raise ValueError('reference totals do not reproduce source call receipts')
    return True


def regenerate(doc:InputDocument,initial:Graph,generate_fn,judge_fn,limits:BudgetLimits,
               checkpoint_sha256,reference=None,config:RegenerationConfig|None=None,
               legacy_config=None):
    """Perform real callbacks and MCR reranking within one shared resource ledger.

    generate_fn.input_tokens(doc) estimates exact prompt tokens before a call;
    generate_fn(doc, max_new_tokens=..., seed=..., temperature=..., top_p=...)
    returns (raw, usage). judge_fn(doc, relation, ledger) must charge any model
    invocation through ledger; a declared cached judgment need not charge again.
    """
    from .modeling import parse_generated_graph
    from .legacy import select_initial
    if not isinstance(doc,InputDocument):raise TypeError('regeneration never receives gold')
    cfg=config or RegenerationConfig();ledger=UsageLedger(limits)
    verified=validate_reference(reference,doc,checkpoint_sha256,limits)
    if graph_errors(doc,initial,acyclic=bool(getattr(legacy_config,'acyclic',False))):raise ValueError('invalid regeneration initial graph')
    samples=[];graphs=[initial]
    for slot in range(cfg.generation_calls):
        try:
            prompt_tokens=generate_fn.input_tokens(doc)
            # Reserve a fair part for each remaining graph call. Verifier usage
            # shares the same total meter; insufficient later budget is explicit.
            cap=min(cfg.max_new_tokens_per_call,ledger.remaining_output//(cfg.generation_calls-slot))
            def call(allowed):
                return generate_fn(doc,max_new_tokens=allowed,seed=cfg.seed+slot,
                                   temperature=cfg.temperature,top_p=cfg.top_p)
            raw=ledger.invoke('full_graph_generation',prompt_tokens,cap,call)
            try:
                graph=parse_generated_graph(raw,doc)
                if graph_errors(doc,graph):raise ValueError('parsed graph is structurally invalid')
                graphs.append(graph);samples.append({'slot':slot,'status':'parsed','raw':raw,'graph':graph.to_dict()})
            except ValueError as exc:samples.append({'slot':slot,'status':'parse_failed','raw':raw,'error':str(exc)})
        except (ValueError,RuntimeError) as exc:
            samples.append({'slot':slot,'status':'generation_failed','error':str(exc)})
            if not ledger.accounting_complete:break
    status='regenerated';ranking={};final=initial;rank_start=time.monotonic()
    try:
        final,ranking=select_initial(doc,graphs,lambda d,r:judge_fn(d,r,ledger),legacy_config)
    except (ValueError,RuntimeError) as exc:
        status='reranking_failed_retained_G0';ranking={'error':str(exc)}
    if len(graphs)==1:status='no_valid_regeneration_retained_G0'
    matched=bool(verified and ledger.accounting_complete)
    return {'doc_id':doc.doc_id,'status':'ok','graph':final.to_dict(),'input_sha256':digest(doc.to_dict()),
            'regeneration_status':status,'samples':samples,'ranking':ranking,
            'metadata':{'method':'Regenerate','checkpoint_sha256':checkpoint_sha256,
                        'matched_budget':matched,'reference_verified':verified,'usage':ledger.summary(),
                        'reranking_wall_seconds':time.monotonic()-rank_start,
                        'solver_cpu_seconds':0.0,'limits_match_actual_consumption_need_not_equal':True}}


def verify_matched_predictions(rows):
    if len({r['doc_id'] for r in rows})!=len(rows):raise ValueError('duplicate regeneration document ids')
    bad=[]
    for row in rows:
        metadata=row.get('metadata',{})
        valid=metadata.get('matched_budget') is True and metadata.get('reference_verified') is True
        if metadata.get('initial_failure_retained'):
            valid=valid and row.get('status')=='initial_failed'
        else:
            usage=metadata.get('usage',{});limits=usage.get('limits',{})
            valid=valid and usage.get('accounting_complete') is True
            for key in ('calls','input_tokens','output_tokens'):
                value=usage.get(key);limit=limits.get(key)
                valid=valid and type(value) is int and type(limit) is int and 0<=value<=limit
            records=usage.get('records',[])
            valid=valid and isinstance(records,list) and all(r.get('status')=='completed' for r in records)
            if valid:
                valid=(len(records)==usage['calls'] and sum(r['input_tokens'] for r in records)==usage['input_tokens']
                       and sum(r['output_tokens'] for r in records)==usage['output_tokens'])
        if not valid:bad.append(row['doc_id'])
    if bad:raise ValueError('Regenerate is not a verified matched-budget comparison for: '+','.join(bad[:10]))
    return True


class ExtractionGenerator:
    def __init__(self,model):self.model=model
    def input_tokens(self,doc):
        encoded=self.model.encode_input(doc.text,doc.corpus)
        # Model receipt currently counts vocabulary input tokens; soft prompts
        # are separately declared input embeddings, not invented tokenizer IDs.
        return len(encoded.ids)
    def __call__(self,doc,**kwargs):
        raw=self.model.generate(doc,**kwargs)
        return raw,dict(self.model.last_generation)


def budgeted_relation_judge(backend):
    from .chat import json_response
    from .schema import LABELS,canonical_json
    cache={}
    def judge(doc,relation,ledger):
        key=digest([doc.to_dict(),relation.key])
        if key in cache:return cache[key]
        payload={'text':doc.text,'sources':[{'span':[c.start,c.end],'text':doc.text[c.start:c.end]} for c in relation.sources],
                 'target':{'span':[relation.target.start,relation.target.end],'text':doc.text[relation.target.start:relation.target.end]}}
        prompt='Classify the COMPLETE directed source set jointly to its target. Return ONLY JSON {"label":"..."}; allowed labels: '+str([*LABELS[doc.corpus],'NONE','UNKNOWN'])+'.\n'+canonical_json(payload)
        rendered=backend.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True)
        n=len(backend.tokenizer(rendered,add_special_tokens=False)['input_ids'])
        def call(allowed):
            raw=backend(prompt,max_new_tokens=allowed)
            return raw,backend.records[-1]
        raw=ledger.invoke('relation_verification_for_reranking',n,backend.config.max_new_tokens,call)
        label=json_response(raw).get('label')
        if label not in (*LABELS[doc.corpus],'NONE','UNKNOWN'):raise ValueError('invalid verifier label')
        value=None if label=='UNKNOWN' else float(label==relation.label)
        cache[key]=value
        return value
    return judge


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('config','out','inputs','ranked','adapter','reference-budget'):p.add_argument('--'+name,required=True)
    p.add_argument('--seed',type=int,default=None,help='Override regeneration and verifier seed for this experiment')
    args=p.parse_args();cfg=read_json(args.config)
    if args.seed is not None:
        cfg={**cfg,'regeneration':{**cfg.get('regeneration',{}),'seed':args.seed},'chat':{**cfg.get('chat',{}),'seed':args.seed}}
    from .modeling import ExtractionModel
    from .chat import HFChatBackend,ChatConfig
    from .legacy import LegacyConfig
    run=Run(args.out,'regenerate',cfg,[args.config,args.inputs,args.ranked,args.reference_budget])
    try:
        docs=load_inputs(args.inputs);ranked={r['doc_id']:r for r in read_jsonl(args.ranked)}
        refs=read_json(args.reference_budget)
        if isinstance(refs,dict):refs=refs['documents']
        refs={r['doc_id']:r for r in refs}
        if set(refs)!={d.doc_id for d in docs} or set(ranked)!=set(refs):raise ValueError('reference/ranked/input document identities differ')
        checkpoint=checkpoint_hash(args.adapter)
        for doc in docs:
            if ranked[doc.doc_id].get('input_sha256')!=digest(doc.to_dict()):raise ValueError('ranked input identity mismatch')
            validate_reference(refs[doc.doc_id],doc,checkpoint,BudgetLimits(**refs[doc.doc_id]['limits']))
        model=ExtractionModel.from_adapter(args.adapter,device=cfg['model'].get('device','cpu'))
        generator=ExtractionGenerator(model);backend=HFChatBackend(ChatConfig(**cfg['chat']));judge=budgeted_relation_judge(backend)
        regen_cfg={k:v for k,v in cfg.get('regeneration',{}).items() if k in RegenerationConfig.__dataclass_fields__}
        rows=[]
        for doc in docs:
            row=ranked[doc.doc_id]
            if row['status']!='ok':
                rows.append({'doc_id':doc.doc_id,'status':'initial_failed','graph':Graph().to_dict(),
                             'input_sha256':digest(doc.to_dict()),'metadata':{'matched_budget':True,'reference_verified':True,'initial_failure_retained':True}})
                continue
            rows.append(regenerate(doc,Graph.from_dict(row['initial']),generator,judge,BudgetLimits(**refs[doc.doc_id]['limits']),
                        checkpoint,refs[doc.doc_id],RegenerationConfig(**regen_cfg),LegacyConfig(**cfg.get('legacy',{}))))
        write_jsonl(run.path/'predictions.jsonl',rows)
        write_json(run.path/'budget_audit.json',{'matched_documents':sum(r['metadata']['matched_budget'] for r in rows),'documents':len(rows),
                    'all_matched':all(r['metadata']['matched_budget'] for r in rows),'checkpoint_sha256':checkpoint,
                    'reference_budget_sha256':file_hash(args.reference_budget)})
        run.finish(documents=len(rows),all_matched=all(r['metadata']['matched_budget'] for r in rows))
    except BaseException as exc:run.fail(exc);raise

if __name__=='__main__':main()
