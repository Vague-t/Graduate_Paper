"""Local HF instruction backend for augmentation, blind review and group proposals."""
from dataclasses import dataclass,asdict
import json,time,hashlib

@dataclass
class ChatConfig:
    model_id: str = 'Qwen/Qwen2.5-7B-Instruct'
    revision: str | None = None
    device: str = 'cuda'
    dtype: str = 'bfloat16'
    load_in_4bit: bool = True
    max_context: int = 8192
    max_new_tokens: int = 1024
    max_calls: int = 1000000
    max_total_output_tokens: int = 100000000
    local_files_only: bool = True
    seed: int = 17

def json_response(raw):
    text=raw.strip()
    if text.startswith('```') and text.endswith('```'):
        text=text.split('\n',1)[1].rsplit('```',1)[0].strip()
    return json.loads(text)

class HFChatBackend:
    def __init__(self,config:ChatConfig):
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM,BitsAndBytesConfig
        self.config=config;self.records=[];self.calls=0;self.output_tokens=0
        self.tokenizer=AutoTokenizer.from_pretrained(config.model_id,revision=config.revision,local_files_only=config.local_files_only,use_fast=True)
        kwargs={'revision':config.revision,'local_files_only':config.local_files_only,'torch_dtype':getattr(torch,config.dtype),'attn_implementation':'sdpa'}
        if config.load_in_4bit:
            if config.device!='cuda':raise ValueError('4bit chat backend requires CUDA')
            kwargs.update(quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=getattr(torch,config.dtype)),device_map={'':'cuda:0'})
        self.model=AutoModelForCausalLM.from_pretrained(config.model_id,**kwargs)
        if not config.load_in_4bit:self.model.to(config.device)
        self.model.eval();self.model.requires_grad_(False)
        from .provenance import model_artifact_identity
        self.identity={**model_artifact_identity(config.model_id,config.revision,getattr(self.model.config,'_commit_hash',None)),
                       'configuration':asdict(config),'purpose':'LOCAL_INSTRUCTION_CALLS_NOT_TRAINED_EXTRACTION_MODEL'}
    def __call__(self,prompt,*,temperature=0.,max_new_tokens=None):
        import torch
        c=self.config
        if self.calls>=c.max_calls:raise RuntimeError('chat call budget exhausted')
        requested=max_new_tokens or c.max_new_tokens
        budget=min(requested,c.max_total_output_tokens-self.output_tokens)
        if budget<=0:raise RuntimeError('chat output token budget exhausted')
        rendered=self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True)
        x=self.tokenizer(rendered,return_tensors='pt',add_special_tokens=False).to(c.device)
        n=x['input_ids'].shape[1]
        if n+budget>c.max_context:raise ValueError('chat context overflow: no silent truncation')
        torch.manual_seed(c.seed+self.calls);self.calls+=1;start=time.monotonic()
        with torch.inference_mode():
            y=self.model.generate(**x,max_new_tokens=budget,do_sample=temperature>0,temperature=temperature if temperature>0 else None,top_p=.9 if temperature>0 else None,pad_token_id=self.tokenizer.eos_token_id)
        tokens=y[0,n:];raw=self.tokenizer.decode(tokens,skip_special_tokens=True);self.output_tokens+=len(tokens)
        self.records.append({'call':self.calls,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'input_tokens':n,'output_tokens':len(tokens),'hit_output_limit':len(tokens)==budget,'elapsed_seconds':time.monotonic()-start,'raw':raw})
        return raw

class RelationVerifier:
    """Cache semantic labels independently of graph selection and annotation."""
    def __init__(self,backend):self.backend=backend;self.cache={}
    def __call__(self,doc,relation):
        from .schema import LABELS,digest
        key=digest([doc.to_dict(),relation.key])
        if key not in self.cache:
            payload={'text':doc.text,'sources':[{'text':doc.text[c.start:c.end],'span':[c.start,c.end]} for c in relation.sources],
                     'target':{'text':doc.text[relation.target.start:relation.target.end],'span':[relation.target.start,relation.target.end]}}
            prompt='Classify the directed relation from the COMPLETE source set jointly to the target in this document. Do not infer separate single-source edges. Return ONLY JSON {"label": one of '+json.dumps([*LABELS[doc.corpus],'NONE','UNKNOWN'])+'}. No desired answer is supplied.\n'+json.dumps(payload,ensure_ascii=False)
            answer=json_response(self.backend(prompt))
            if answer.get('label') not in (*LABELS[doc.corpus],'NONE','UNKNOWN'):raise ValueError('verifier invalid label')
            self.cache[key]=answer['label']
        label=self.cache[key]
        if label=='UNKNOWN':return None
        return float(label==relation.label)
