"""Actual causal LM + frozen base / global and prefix-gated conclusion LoRA.

Tiny mode is an actual randomly initialized causal Transformer for local code
checks; it is not a pretrained baseline or thesis performance evidence.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
from types import SimpleNamespace
import json
import math
import re
import torch
from torch import nn
from torch.nn import functional as F
from .schema import Document, InputDocument, Graph, Component, Relation, TYPES, LABELS, graph_errors

CUES=re.compile(r'\b(?:therefore|thus|in conclusion|consequently|hence|to conclude)\b',re.I)

@dataclass
class ModelConfig:
    backend: str = 'tiny'
    model_name: str = 'Qwen/Qwen2.5-7B-Instruct'
    revision: str | None = None
    hidden_size: int = 48
    layers: int = 2
    attention_heads: int = 4
    head_hidden: int = 128
    lora_rank: int = 16
    lora_alpha: float = 32
    lora_dropout: float = 0.05
    head_dropout: float = 0.1
    four_bit: bool = False
    gradient_checkpointing: bool = False
    device: str = 'cpu'
    dtype: str = 'float32'
    max_input_tokens: int = 4096
    max_output_tokens: int = 2048
    max_context: int = 8192
    seed: int = 17
    local_files_only: bool = False


def prefix_gate(prefix: str, corpus: str) -> bool:
    """A gate computed exclusively from the visible answer prefix.

    Tracks lexical JSON braces/strings so text mentioning a type cannot switch
    the gate. The controlled serialization orders id, type, span. After the
    type's closing quote the remainder of that component can use conclusion
    LoRA. A component closing brace or the relations region switches it off.
    """
    begin=re.search(r'"components"\s*:\s*\[',prefix)
    if not begin: return False
    pos=begin.end(); in_string=False; escape=False; depth=0; start=None
    for i in range(pos,len(prefix)):
        c=prefix[i]
        if in_string:
            if escape: escape=False
            elif c=='\\': escape=True
            elif c=='"': in_string=False
            continue
        if c=='"': in_string=True
        elif c=='{':
            if depth==0: start=i
            depth+=1
        elif c=='}':
            depth-=1
            if depth==0: start=None
        elif c==']' and depth==0: return False
    if start is None or depth!=1: return False
    # Our schema contains no string field before type except id. Anchoring the
    # regex to the object header prevents a quoted string from imitating a key.
    match=re.match(r'\{\s*"id"\s*:\s*"(?:[^"\\]|\\.)*"\s*,\s*"type"\s*:\s*"([^"\\]*)"',prefix[start:])
    if not match: return False
    return match.group(1) in ({'Claim','MajorClaim'} if corpus=='aaec' else {'policy','value'})


def serialize_graph(graph: Graph) -> str:
    ids={c:f'c{i}' for i,c in enumerate(graph.components)}
    return json.dumps({'components':[{'id':ids[c],'type':c.label,'span':[c.start,c.end]} for c in graph.components],
                       'relations':[{'sources':[ids[c] for c in r.sources],'target':ids[r.target],'type':r.label} for r in graph.relations]},
                      ensure_ascii=False,separators=(',',':'))


def parse_generated_graph(raw: str, doc: InputDocument) -> Graph:
    """Strict parser; no guessed offsets, dropped edges or gold-based repair."""
    text=raw.strip()
    if text.startswith('```'):
        m=re.fullmatch(r'```(?:json)?\s*([\s\S]*?)\s*```',text)
        if not m: raise ValueError('malformed JSON code fence')
        text=m.group(1)
    value=json.loads(text)
    if not isinstance(value,dict) or set(value)!={'components','relations'}: raise ValueError('expected exactly components and relations')
    if not isinstance(value['components'],list):raise ValueError('components must be a list')
    components=[]; seen_ids=set(); seen_keys=set()
    for item in value['components']:
        if not isinstance(item,dict): raise ValueError('component must be an object')
        if 'span' in item:
            if set(item)!={'id','type','span'} or not isinstance(item['span'],list) or len(item['span'])!=2: raise ValueError('invalid component span schema')
            start,end=item['span']
        else:
            if set(item)!={'id','type','start','end'}: raise ValueError('invalid component schema')
            start,end=item['start'],item['end']
        if not isinstance(item['type'],str):raise ValueError('component type must be a string')
        if not isinstance(item['id'],str) or item['id'] in seen_ids: raise ValueError('ambiguous component id')
        if type(start) is not int or type(end) is not int: raise ValueError('native offsets must be integer characters')
        c=Component(start,end,item['type'])
        if c.key in seen_keys: raise ValueError('duplicate native component')
        seen_ids.add(item['id']); seen_keys.add(c.key)
        components.append({'id':item['id'],'start':start,'end':end,'type':item['type']})
    if not isinstance(value['relations'],list): raise ValueError('relations must be a list')
    for item in value['relations']:
        if not isinstance(item,dict) or set(item)!={'sources','target','type'} or not isinstance(item['sources'],list): raise ValueError('invalid relation schema')
        if not isinstance(item['type'],str) or not isinstance(item['target'],str) or not all(isinstance(x,str) for x in item['sources']):raise ValueError('invalid relation value types')
    try:graph=Graph.from_dict({'components':components,'relations':value['relations']})
    except (KeyError,TypeError,ValueError) as exc:raise ValueError('invalid generated endpoint references') from exc
    errors=graph_errors(doc,graph)
    if errors: raise ValueError('invalid generated graph: '+','.join(errors))
    return graph


class ByteTokenizer:
    """Unicode-aware byte vocabulary: actual character offsets, not byte offsets."""
    eos_token_id=2; pad_token_id=0; bos_token_id=1
    def encode(self,text,add_special_tokens=False):
        return ([1] if add_special_tokens else [])+[b+3 for b in text.encode('utf8')]
    def __call__(self,text,add_special_tokens=False,return_offsets_mapping=False,**kwargs):
        ids=[]; offsets=[]
        for i,char in enumerate(text):
            for b in char.encode('utf8'): ids.append(b+3); offsets.append((i,i+1))
        if add_special_tokens: ids=[1]+ids; offsets=[(0,0)]+offsets
        result={'input_ids':ids}
        if return_offsets_mapping:result['offset_mapping']=offsets
        return result
    def decode(self,ids,skip_special_tokens=True):
        return bytes(int(i)-3 for i in ids if 3<=int(i)<259).decode('utf8',errors='replace')


class GateState:
    gate=None


class DualLoRALinear(nn.Module):
    def __init__(self,base: nn.Module,rank,alpha,dropout,state:GateState):
        super().__init__(); self.base=base; self.state=state; self.scale=alpha/rank
        self.global_A=nn.Parameter(torch.empty(rank,base.in_features)); self.global_B=nn.Parameter(torch.zeros(base.out_features,rank))
        self.conclusion_A=nn.Parameter(torch.empty(rank,base.in_features)); self.conclusion_B=nn.Parameter(torch.zeros(base.out_features,rank))
        nn.init.kaiming_uniform_(self.global_A,a=math.sqrt(5)); nn.init.kaiming_uniform_(self.conclusion_A,a=math.sqrt(5))
        self.dropout=nn.Dropout(dropout)
        for p in base.parameters():p.requires_grad=False
    def forward(self,x):
        base=self.base(x)
        delta=F.linear(F.linear(self.dropout(x).to(self.global_A.dtype),self.global_A),self.global_B)*self.scale
        gate=self.state.gate
        if gate is not None and bool(torch.any(gate).item()):
            if gate.shape!=x.shape[:2]:raise RuntimeError('gate and token positions disagree')
            conclusion=F.linear(F.linear(self.dropout(x).to(self.conclusion_A.dtype),self.conclusion_A),self.conclusion_B)*self.scale
            delta=delta+conclusion*gate.to(conclusion.dtype).unsqueeze(-1)
        return base+delta.to(base.dtype)


class TinyAttention(nn.Module):
    def __init__(self,h,n):
        super().__init__();self.h=h;self.n=n
        self.q_proj=nn.Linear(h,h,bias=False);self.k_proj=nn.Linear(h,h,bias=False);self.v_proj=nn.Linear(h,h,bias=False);self.o_proj=nn.Linear(h,h,bias=False)
    def forward(self,x):
        b,t,h=x.shape
        q,k,v=(proj(x).reshape(b,t,self.n,h//self.n).transpose(1,2) for proj in (self.q_proj,self.k_proj,self.v_proj))
        out=F.scaled_dot_product_attention(q,k,v,is_causal=True)
        return self.o_proj(out.transpose(1,2).reshape(b,t,h))


class TinyLayer(nn.Module):
    def __init__(self,h,n):
        super().__init__();self.norm1=nn.LayerNorm(h);self.attention=TinyAttention(h,n);self.norm2=nn.LayerNorm(h)
        self.mlp=nn.Sequential(nn.Linear(h,4*h),nn.GELU(),nn.Linear(4*h,h))
    def forward(self,x):
        x=x+self.attention(self.norm1(x));return x+self.mlp(self.norm2(x))


class TinyLM(nn.Module):
    def __init__(self,cfg):
        super().__init__();self.embed=nn.Embedding(259,cfg.hidden_size);self.pos=nn.Embedding(cfg.max_context,cfg.hidden_size)
        self.layers=nn.ModuleList([TinyLayer(cfg.hidden_size,cfg.attention_heads) for _ in range(cfg.layers)])
        self.norm=nn.LayerNorm(cfg.hidden_size);self.lm_head=nn.Linear(cfg.hidden_size,259,bias=False)
        self.config=SimpleNamespace(hidden_size=cfg.hidden_size,_commit_hash=None)
    def get_input_embeddings(self):return self.embed
    def forward(self,inputs_embeds,**kwargs):
        x=inputs_embeds+self.pos(torch.arange(inputs_embeds.shape[1],device=inputs_embeds.device))[None]
        for layer in self.layers:x=layer(x)
        x=self.norm(x);return SimpleNamespace(logits=self.lm_head(x),hidden_states=(x,))


@dataclass
class EncodedInput:
    ids: list[int]
    offsets: list[tuple[int,int]]
    prompt_enabled: bool
    text: str
    corpus: str


class ExtractionModel(nn.Module):
    def __init__(self,config:ModelConfig):
        super().__init__();self.config=config;self.gate_state=GateState();self.last_generation={}
        if config.lora_rank<1:raise ValueError('LoRA rank must be positive')
        torch.manual_seed(config.seed)
        if config.backend=='tiny':
            if config.four_bit:raise ValueError('four_bit requires HF CUDA backend')
            self.tokenizer=ByteTokenizer();self.backbone=TinyLM(config)
        elif config.backend=='hf':
            from transformers import AutoModelForCausalLM,AutoTokenizer
            dtype={'float32':torch.float32,'bfloat16':torch.bfloat16,'float16':torch.float16}[config.dtype]
            kwargs={'revision':config.revision,'local_files_only':config.local_files_only,'torch_dtype':dtype,'attn_implementation':'sdpa'}
            if config.four_bit:
                if not config.device.startswith('cuda') or not torch.cuda.is_available():raise RuntimeError('4-bit QLoRA requires a CUDA GPU and bitsandbytes')
                from transformers import BitsAndBytesConfig
                kwargs.update(quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=dtype),device_map={'':config.device})
            self.tokenizer=AutoTokenizer.from_pretrained(config.model_name,revision=config.revision,local_files_only=config.local_files_only,use_fast=True)
            if not self.tokenizer.is_fast:raise ValueError('a fast tokenizer with native character offsets is required')
            self.backbone=AutoModelForCausalLM.from_pretrained(config.model_name,**kwargs)
        else:raise ValueError('backend must be tiny or hf')
        for p in self.backbone.parameters():p.requires_grad=False
        wrapped=[]
        for name,module in list(self.backbone.named_modules()):
            if name.split('.')[-1] in {'q_proj','k_proj','v_proj','o_proj'} and hasattr(module,'in_features'):
                parent_name,_,leaf=name.rpartition('.')
                parent=self.backbone.get_submodule(parent_name) if parent_name else self.backbone
                setattr(parent,leaf,DualLoRALinear(module,config.lora_rank,config.lora_alpha,config.lora_dropout,self.gate_state));wrapped.append(name)
        if not wrapped:raise ValueError('requested q/k/v/o projections not found; unsupported model architecture')
        self.wrapped_modules=wrapped;h=self.backbone.config.hidden_size
        self.soft_prompt=nn.Parameter(torch.randn(4,h)*0.02)
        self.sentence_head=nn.Linear(h,1)
        def head(in_features,classes):return nn.Sequential(nn.Linear(in_features,config.head_hidden),nn.GELU(),nn.Dropout(config.head_dropout),nn.Linear(config.head_hidden,classes))
        self.component_heads=nn.ModuleDict({corpus:head(2*h,len(types)) for corpus,types in TYPES.items()})
        self.relation_heads=nn.ModuleDict({corpus:head(3*h+7,len(labels)+1) for corpus,labels in LABELS.items()})
        if not config.four_bit:self.to(config.device)
        else:
            # Quantized base cannot be moved through Module.to; move only the
            # freshly initialized float adapters/heads to the existing device.
            for module in self.backbone.modules():
                if isinstance(module,DualLoRALinear):
                    for name in ('global_A','global_B','conclusion_A','conclusion_B'):
                        p=getattr(module,name);p.data=p.data.to(config.device)
            self.soft_prompt.data=self.soft_prompt.data.to(config.device)
            self.sentence_head.to(config.device);self.component_heads.to(config.device);self.relation_heads.to(config.device)
        if config.gradient_checkpointing and config.backend=='hf':self._enable_checkpointing()
        from .provenance import model_artifact_identity
        self.artifact_identity=(model_artifact_identity(config.model_name,config.revision,getattr(self.backbone.config,'_commit_hash',None))
                                if config.backend=='hf' else {'kind':'random_tiny','seed':config.seed})

    def _enable_checkpointing(self):
        # HF checkpoint recomputation occurs after subsequent original/augmented
        # forwards. Capture the gate per checkpoint; a mutable last-forward gate
        # would silently break conclusion branch gradients during recomputation.
        from torch.utils.checkpoint import checkpoint
        self.backbone.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        state=self.gate_state
        def checkpoint_with_gate(function,*args,**kwargs):
            captured=state.gate
            def run(*inner):
                previous=state.gate;state.gate=captured
                try:return function(*inner)
                finally:state.gate=previous
            return checkpoint(run,*args,use_reentrant=False,**kwargs)
        for module in self.backbone.modules():
            if hasattr(module,'_gradient_checkpointing_func'):module._gradient_checkpointing_func=checkpoint_with_gate
        self.backbone.config.use_cache=False

    @property
    def device(self):return self.soft_prompt.device

    def encode_input(self,text:str,corpus:str)->EncodedInput:
        if corpus not in TYPES:raise ValueError('unknown corpus')
        instruction=('Extract the argument graph using native character offsets [start,end). Return one JSON object with arrays "components" and "relations", without Markdown. '
                     'Every component has a unique "id", a "type" chosen from the allowed component types, and "span":[start,end]. '
                     'Every relation has "sources" (an array of existing component IDs), "target" (an existing component ID), and "type" chosen from the allowed relation types. '
                     f'Component types: {", ".join(TYPES[corpus])}. Relation types: {", ".join(LABELS[corpus])}. '
                     'Use the exact spelling and case of these types. Keep complete source groups. Offsets refer only to the supplied document, counted in Unicode characters. '
                     'Do not output schema placeholders. All relation endpoints must be present among your components, and sources must differ from the target.')
        if self.config.backend=='hf':
            messages=[{'role':'system','content':instruction},{'role':'user','content':'DOCUMENT:\n'+text}]
            prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            doc_start=prompt.find('DOCUMENT:\n')+len('DOCUMENT:\n')
            if doc_start<len('DOCUMENT:\n') or prompt[doc_start:doc_start+len(text)]!=text:raise ValueError('chat template did not preserve document')
        else:
            # Short deterministic instruction keeps CPU diagnostics affordable.
            prompt=f'Extract {corpus} graph. DOCUMENT:\n{text}\nANSWER:\n';doc_start=prompt.index('DOCUMENT:\n')+len('DOCUMENT:\n')
        encoded=self.tokenizer(prompt,add_special_tokens=False,return_offsets_mapping=True)
        offsets=[]
        for start,end in encoded['offset_mapping']:
            left=max(start,doc_start);right=min(end,doc_start+len(text))
            offsets.append((left-doc_start,right-doc_start) if left<right else (-1,-1))
        ids=list(encoded['input_ids']);enabled=bool(CUES.search(text))
        if len(ids)>self.config.max_input_tokens or len(ids)+(4 if enabled else 0)>self.config.max_context:raise ValueError('input_context_overflow_no_truncation')
        return EncodedInput(ids,offsets,enabled,text,corpus)

    def _forward(self,encoded:EncodedInput,answer_ids=None,hidden_only=False,use_cache=False):
        answer_ids=[] if answer_ids is None else list(answer_ids)
        ids=encoded.ids+answer_ids;prefix_count=4 if encoded.prompt_enabled else 0
        if len(ids)+prefix_count>self.config.max_context:raise ValueError('full_context_overflow_no_truncation')
        tensor=torch.tensor([ids],dtype=torch.long,device=self.device)
        embeds=self.backbone.get_input_embeddings()(tensor)
        gate_values=[False]*len(encoded.ids)
        for i in range(len(answer_ids)):
            visible=self.tokenizer.decode(answer_ids[:i],skip_special_tokens=True)
            gate_values.append(prefix_gate(visible,encoded.corpus))
        if prefix_count:
            embeds=torch.cat((self.soft_prompt.to(embeds.dtype)[None],embeds),dim=1)
            gate_values=[False]*prefix_count+gate_values
        gate=torch.tensor([gate_values],dtype=torch.bool,device=self.device)
        previous=self.gate_state.gate;self.gate_state.gate=gate
        try:
            module=self.backbone.model if hidden_only and self.config.backend=='hf' else self.backbone
            result=module(inputs_embeds=embeds,attention_mask=torch.ones(embeds.shape[:2],dtype=torch.long,device=self.device),output_hidden_states=True,use_cache=use_cache)
        finally:self.gate_state.gate=previous
        return result,prefix_count

    def input_hidden(self,text:str,corpus:str):
        encoded=self.encode_input(text,corpus);result,prefix=self._forward(encoded,hidden_only=True)
        hidden=result.hidden_states[-1][0,prefix:]
        return hidden,encoded.offsets,hidden[-1]

    def generation_loss(self,document:Document):
        encoded=self.encode_input(document.text,document.corpus)
        answer=self.tokenizer.encode(serialize_graph(document.gold),add_special_tokens=False)+[self.tokenizer.eos_token_id]
        if len(answer)>self.config.max_output_tokens:raise ValueError('target_context_overflow_no_truncation')
        result,prefix=self._forward(encoded,answer,hidden_only=True)
        start=prefix+len(encoded.ids)-1
        features=result.hidden_states[-1][0,start:start+len(answer)]
        target=torch.tensor(answer,dtype=torch.long,device=self.device)
        # Chunk and checkpoint the frozen vocabulary projection. Materializing
        # an 8192 x 152k Qwen logits tensor needlessly consumes multiple GiB.
        from torch.utils.checkpoint import checkpoint
        losses=[]
        for offset in range(0,len(answer),128):
            h=features[offset:offset+128]; y=target[offset:offset+128]
            def chunk_loss(hidden,labels):
                return F.cross_entropy(self.backbone.lm_head(hidden).float(),labels,reduction='sum')
            losses.append(checkpoint(chunk_loss,h,y,use_reentrant=False) if self.training else chunk_loss(h,y))
        loss=torch.stack(losses).sum()/len(answer)
        return loss,{'generation_tokens':len(answer),'input_tokens':len(encoded.ids),'soft_prompt_tokens':prefix}

    @torch.no_grad()
    def generate(self,document:InputDocument,max_new_tokens:int|None=None,temperature:float=0.0,top_p:float=0.9,seed:int|None=None):
        was_training=self.training;self.eval()
        try:
            encoded=self.encode_input(document.text,document.corpus)
            budget=max_new_tokens if max_new_tokens is not None else self.config.max_output_tokens
            if budget<1 or budget>self.config.max_output_tokens:raise ValueError('invalid generation token budget')
            answer=[];generator=torch.Generator(device=self.device).manual_seed(self.config.seed if seed is None else seed)
            stop='max_new_tokens';cache=None
            for _ in range(budget):
                if len(encoded.ids)+len(answer)+(4 if encoded.prompt_enabled else 0)>=self.config.max_context:stop='context_limit';break
                if self.config.backend=='hf' and answer and cache is not None:
                    token_input=torch.tensor([[answer[-1]]],dtype=torch.long,device=self.device)
                    embedding=self.backbone.get_input_embeddings()(token_input)
                    gate=prefix_gate(self.tokenizer.decode(answer[:-1],skip_special_tokens=True),encoded.corpus)
                    previous=self.gate_state.gate
                    self.gate_state.gate=torch.tensor([[gate]],device=self.device,dtype=torch.bool)
                    try:
                        result=self.backbone.model(inputs_embeds=embedding,past_key_values=cache,use_cache=True,
                            attention_mask=torch.ones((1,len(encoded.ids)+len(answer)+(4 if encoded.prompt_enabled else 0)),device=self.device,dtype=torch.long),
                            output_hidden_states=True)
                    finally:self.gate_state.gate=previous
                else:result,_=self._forward(encoded,answer,hidden_only=True,use_cache=self.config.backend=='hf')
                cache=getattr(result,'past_key_values',None)
                logits=self.backbone.lm_head(result.hidden_states[-1][0,-1]).float()
                if temperature<=0: token=int(logits.argmax())
                else:
                    prob=F.softmax(logits/temperature,dim=-1)
                    if 0<top_p<1:
                        sorted_prob,order=torch.sort(prob,descending=True);mask=sorted_prob.cumsum(0)-sorted_prob>top_p
                        sorted_prob[mask]=0;sorted_prob/=sorted_prob.sum();token=int(order[torch.multinomial(sorted_prob,1,generator=generator)])
                    else:token=int(torch.multinomial(prob,1,generator=generator))
                if token==self.tokenizer.eos_token_id:stop='eos';break
                answer.append(token)
            self.last_generation={'input_tokens':len(encoded.ids),'output_tokens':len(answer)+(stop=='eos'),'budget':budget,'stop_reason':stop,'truncated':stop!='eos','temperature':temperature,'seed':seed}
            return self.tokenizer.decode(answer,skip_special_tokens=True)
        finally:self.train(was_training)

    def parameter_manifest(self):
        return {'backend':self.config.backend,'model_name':self.config.model_name if self.config.backend=='hf' else 'random_tiny_causal_transformer',
                'resolved_revision':self.artifact_identity.get('resolved_revision'),
                'artifact_identity':self.artifact_identity,
                'trainable_parameters':sum(p.numel() for p in self.parameters() if p.requires_grad),
                'frozen_parameters':sum(p.numel() for p in self.parameters() if not p.requires_grad),
                'lora_modules':self.wrapped_modules,'four_bit':self.config.four_bit}

    def save_adapter(self,path):
        path=Path(path);path.mkdir(parents=True,exist_ok=True)
        (path/'model_config.json').write_text(json.dumps(asdict(self.config),ensure_ascii=False,indent=2)+'\n')
        (path/'model_manifest.json').write_text(json.dumps(self.parameter_manifest(),ensure_ascii=False,indent=2)+'\n')
        if self.config.backend=='tiny':state=self.state_dict()
        else:
            keys={name for name,p in self.named_parameters() if p.requires_grad};state={k:v for k,v in self.state_dict().items() if k in keys}
        torch.save({k:v.detach().cpu() for k,v in state.items()},path/'adapter.pt')

    def load_adapter(self,path):
        saved=json.loads((Path(path)/'model_manifest.json').read_text())
        if saved.get('artifact_identity')!=self.artifact_identity:raise ValueError('adapter base model identity mismatch')
        state=torch.load(Path(path)/'adapter.pt',map_location=self.device,weights_only=True)
        missing,unexpected=self.load_state_dict(state,strict=self.config.backend=='tiny')
        trainable={name for name,p in self.named_parameters() if p.requires_grad}
        if unexpected or set(missing)&trainable:raise ValueError('incompatible or incomplete adapter state')
        return self

    @classmethod
    def from_adapter(cls,path,device=None,**overrides):
        config=json.loads((Path(path)/'model_config.json').read_text());config.update(overrides)
        if device is not None:config['device']=device
        return cls(ModelConfig(**config)).load_adapter(path)
