"""Check data/context and stage budgets without loading model weights."""
import argparse,json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from argrepair.io import load_documents,load_inputs,write_json,file_hash
from argrepair.modeling import ModelConfig,ExtractionModel,ByteTokenizer,serialize_graph
from argrepair.augmentation import factor_universe
from argrepair.schema import graph_errors

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',required=True);p.add_argument('--config',required=True);p.add_argument('--out',required=True)
a=p.parse_args();cfg=json.loads(Path(a.config).read_text());mc=ModelConfig(**cfg['model'])
if mc.backend=='hf':
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(mc.model_name,revision=mc.revision,local_files_only=mc.local_files_only,use_fast=True)
else:tok=ByteTokenizer()
proxy=SimpleNamespace(config=mc,tokenizer=tok);rows=[];errors=[]
for corpus in ('aaec','cdcp'):
    for d in load_documents(Path(a.data)/f'{corpus}_train.jsonl'):
        try:
            issues=graph_errors(d.input,d.gold)
            if issues:raise ValueError(str(issues))
            enc=ExtractionModel.encode_input(proxy,d.text,corpus)
            target=len(tok.encode(serialize_graph(d.gold),add_special_tokens=False))+1
            total=len(enc.ids)+target+4*enc.prompt_enabled
            universe=factor_universe(d,max_factors=cfg.get('training',{}).get('max_factors',50000))
            if target>mc.max_output_tokens or total>mc.max_context:raise ValueError(f'target/full context overflow: target={target},total={total}')
            rows.append({'doc_id':d.doc_id,'split':'train','input_tokens':len(enc.ids),'target_tokens':target,'total_tokens':total,'factors':len(universe.factors)})
        except ValueError as exc:errors.append({'doc_id':d.doc_id,'split':'train','error':str(exc)})
    # Deliberately cannot access test annotations.
    for d in load_inputs(Path(a.data)/f'{corpus}_test_inputs.jsonl'):
        try:
            enc=ExtractionModel.encode_input(proxy,d.text,corpus)
            if len(enc.ids)+cfg['generation']['max_new_tokens']+4*enc.prompt_enabled>mc.max_context:raise ValueError('inference input + reserved output exceeds context')
            rows.append({'doc_id':d.doc_id,'split':'test_input_only','input_tokens':len(enc.ids)})
        except ValueError as exc:errors.append({'doc_id':d.doc_id,'split':'test_input_only','error':str(exc)})
report={'status':'passed' if not errors else 'failed','weights_loaded':False,'gpu_memory_validated':False,'configuration_sha256':file_hash(a.config),
        'documents_checked':len(rows)+len(errors),'maxima':{k:max((r.get(k,0) for r in rows),default=0) for k in ('input_tokens','target_tokens','total_tokens','factors')},'errors':errors,'documents':rows}
write_json(a.out,report)
print(json.dumps({k:v for k,v in report.items() if k!='documents'},ensure_ascii=False,indent=2));sys.exit(bool(errors))
