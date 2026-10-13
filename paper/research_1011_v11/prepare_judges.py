"""Gold-visible training augmentation transport; masked model assessor inputs."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,itertools,sys
from prepare import R,W,read,write,wt,sha,hh
def factors(g):
 edit=set(g['editable_component_ids']);rels=g['relations'];out=[]
 native_slots={(tuple(r['sources']),r['target']) for r in rels}
 for r in rels:
  ep=set(r['sources'])|{r['target']}
  if ep&edit:out.append({'category':'internal_positive' if ep<=edit else 'crossing_positive',**r})
 for kind in ['internal_NONE','crossing_NONE']:
  pool=[]
  for a,b in itertools.permutations(range(len(g['components'])),2):
   ep={a,b}
   if not ep&edit or ((ep<=edit)!=(kind=='internal_NONE')):continue
   if ((a,),b) in native_slots:continue
   # A singleton from an annotated joint source is not a genuine binary NONE probe.
   if any(b==r['target'] and a in r['sources'] for r in rels):continue
   pool.append({'category':kind,'sources':[a],'target':b,'type':'NONE'})
  out+=sorted(pool,key=lambda r:hh('V11-NONE|'+g['id']+'|'+json.dumps(r,sort_keys=True)))[:4]
 return [{'id':f'f{i:03d}','category':r['category'],'sources':[f'c{x:03d}' for x in r['sources']],'target':f"c{r['target']:03d}",'original_label':r['type']} for i,r in enumerate(out)]
def transport(g,reps):
 cs=g['components'];changes=sorted((cs[int(i[1:])]['char_start'],cs[int(i[1:])]['char_end'],t) for i,t in reps.items())
 assert all(changes[i][1]<=changes[i+1][0] for i in range(len(changes)-1))
 text=g['text'];out='';pos=0
 for s,e,t in changes:out+=text[pos:s]+t;pos=e
 return out+text[pos:]
def main():
 gold={g['id']:g for g in read(R/'drift/evaluation/source_gold.json')['documents']}
 source={d['id']:d for p in (R/'drift_generate/inputs').glob('*.json') for d in read(p)['documents']}
 baseprompt='''You are a fresh gpt-5.6-luna / low semantic assessor of argument-mining augmentation. You see source text, native original component labels, an annotated original relation factor, and paraphrased variants. These are linguistic annotation judgments, not medical/legal/political truth judgments. Evaluate each variant independently. Do not infer any desired acceptance rate or method superiority. No filter decisions, other judgments or method names are provided. Original labels can be imperfect: assess original and rewritten validity separately. An original-label disagreement must NOT automatically be called paraphrase-induced drift. Direct argument links are required; do not invent transitive closure. For CDCP, a source group means the complete joint reason/evidence; do not treat any singleton as sufficient just because it is in a joint source. NONE means no direct native labeled link for the specified complete source and target, not "no conceivable association".
Native definitions: AAEC MajorClaim is overall position, Claim is a standpoint supported or attacked, Premise gives reasons; supports/attacks are direct argumentative links. CDCP reference is external citation/URL, testimony personal experience/state, fact externally verifiable at statement time, value evaluative judgment, policy concrete recommended action. CDCP reason is rationale for the target, evidence grounds for its truth, typically testimony/reference sources. An objective-sounding statement is not automatically evidence.
For every editable component assess whether its intended meaning is preserved (preserved/changed/uncertain), and whether the original type is valid in original and rewritten contexts (true/false/null). For EVERY factor assess whether original_label is valid in the ORIGINAL context and in the REWRITTEN context separately, each true/false/null; null means genuinely unresolved. Inspect incoming/outgoing context and quantification, negation, modality, reference, and whether the complete joint source still supports its target. Do not claim independence from the same model family. No gold search, scripts for semantic classification, or access outside assigned inputs. Scripts may serialize your own individual judgments and mechanically validate keys.
Schema: {"model_requested":"gpt-5.6-luna","documents":[{"id":"input id","variants":[{"variant_id":"concise","components":{"c000":{"meaning":"preserved","original_type_valid":true,"rewritten_type_valid":true,"reason":"brief text-specific reason"}},"factors":{"f000":{"original_label_valid":true,"rewritten_label_valid":false,"reason":"brief text-specific reason"}}},{"variant_id":"fluent","components":{},"factors":{}}]}]}. Include exactly every supplied document, variant, editable component, and factor, with no default omission. Save once at assigned output. Return path and mechanical validation only, no messaging.
'''
 for role in ['filter','audit']:
  path=R/'drift'/f'{role}_instruction.md'
  if not path.exists():wt(path,baseprompt)
 created=[]
 for p in sorted((R/'drift_generate/raw').glob('*.json')):
  inp=read(R/'drift_generate/inputs'/p.name)['documents'];raw=read(p);ds=raw['documents']
  assert {x['id'] for x in ds}=={x['id'] for x in inp} and len(ds)==len(inp)
  group=[]
  for d in ds:
   g=gold[d['id']];src=source[d['id']];vs=[]
   assert [x['variant_id'] for x in d['variants']]==['concise','fluent']
   for x in d['variants']:
    assert set(x['replacements'])==set(src['editable_ids'])
    assert all(isinstance(t,str) and t.strip() for t in x['replacements'].values())
    vs.append({'variant_id':x['variant_id'],'replacements':x['replacements'],'rewritten_text':transport(g,x['replacements'])})
   group.append({'id':d['id'],'corpus':g['corpus'],'original_text':g['text'],'original_components':src['components'],'editable_ids':src['editable_ids'],'factors':factors(g),'variants':vs})
  key=p.stem.replace('drift_generate','drift_judge');inputpath=R/'drift/judge_inputs'/f'{key}.json'
  obj={'documents':group}
  if inputpath.exists():assert read(inputpath)==obj
  else:write(inputpath,obj)
  for role in ['filter','audit']:
   task=f'v11_{key}_{role}';out=R/'drift'/f'{role}_outputs'/f'{key}.json';inst=R/'drift'/f'{role}_instruction.md'
   disp=R/'dispatch'/f'{task}.txt'
   if not disp.exists():
    wt(disp,f'Run the authorized gpt-5.6-luna / low masked semantic assessment. Read ONLY {inst} and {inputpath}. Save once to {out}. This is a fresh context independent of generation and the other assessor. No other outputs, accept flags, gold files, manuscript, memory, web, other files or other tasks may be read. Do all judgments yourself; code only serializes and checks the schema. Do not message others. Return path and validation only.')
    created.append(task)
  freeze=R/'drift/freezes'/f'{key}.json'
  if not freeze.exists():write(freeze,{'at_utc':datetime.now(timezone.utc).isoformat(),'raw_generation_sha256':sha(p),'input_sha256':sha(inputpath),'instruction_hashes':{r:sha(R/'drift'/f'{r}_instruction.md') for r in ['filter','audit']}})
 print(json.dumps({'new_tasks':created,'available_groups':len(list((R/'drift/judge_inputs').glob('*.json')))}))
if __name__=='__main__':main()
