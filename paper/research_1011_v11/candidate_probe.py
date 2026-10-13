"""Gold-free candidate construction, then a separate post-freeze coverage audit."""
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone
import hashlib,itertools,json,re,sys,time,tracemalloc
R=Path(__file__).resolve().parent;W=R.parent
sys.path.insert(0,str(W/'research_1011_v10/cdcp_scoring'))
import graph_core as core
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
def key(c):return c['start'],c['end'],c['type']
def compatible(cs):return all(max(a[0],b[0])>=min(a[1],b[1]) for a,b in itertools.combinations(cs,2))
def raw_components(text,corpus,raw):
 primary=set();alternatives=set();sequences=[];groups=[];errors=[]
 for g in raw['graphs']:
  mapping={};seq=[]
  for c in g['components']:
   try:
    parsed,_,_=core.parse_graph(text,corpus,{'components':[c],'relations':[]});k=parsed[0]
    primary.add(k);mapping[c['id']]=k;seq.append(k)
    for typ in c.get('alternative_types',[]):
     if typ not in core.TYPES[corpus]:raise ValueError('invalid alternative type')
     alternatives.add((k[0],k[1],typ))
   except Exception as e:errors.append({'candidate_id':g['candidate_id'],'component_id':c.get('id'),'error':str(e)})
  seq=sorted(set(seq));sequences.append(seq)
  if corpus=='cdcp':
   for rel in g.get('relations',[]):
    try:
     src=tuple(sorted(mapping[i] for i in rel['sources']));target=mapping[rel['target']]
     if src and target not in src and compatible((*src,target)):groups.append((src,target))
    except (KeyError,TypeError):pass
 return primary,alternatives,sequences,groups,errors
def punctuation_variants(C,text):
 out=set(C)
 for s,e,t in C:
  tokens=list(core.TOKEN.finditer(text[s:e]))
  if len(tokens)>1 and tokens[-1].group() in ('.',',',';',':','!','?'):
   ee=s+tokens[-1].start()
   while ee>s and text[ee-1].isspace():ee-=1
   if ee>s:out.add((s,ee,t))
 return out
def expand_boundaries(C,text):
 spans=list(core.TOKEN.finditer(text));starts={x.start():i for i,x in enumerate(spans)};ends={x.end():i+1 for i,x in enumerate(spans)};out=set()
 for s,e,t in C:
  a,b=starts[s],ends[e]
  for da,db in itertools.product([-1,0,1],repeat=2):
   aa,bb=a+da,b+db
   if 0<=aa<bb<=len(spans) and bb-aa<=64:out.add((spans[aa].start(),spans[bb-1].end(),t))
 return out
def select_components(protected,ranked_sets,cap=64):
 selected=set(protected);supplement=[]
 for entries in ranked_sets:
  for k in sorted(entries):
   if k not in selected and len(supplement)<cap: selected.add(k);supplement.append(k)
 return selected,supplement
def slots_for(C,protected,corpus,sequences,groups):
 slots=set(protected)
 for a,b in itertools.permutations(sorted(C),2):
  if compatible([a,b]):slots.add(((a,),b))
 for src,target in groups:
  if set(src)|{target}<=C:slots.add((src,target))
 if corpus=='cdcp':
  variants=defaultdict(list)
  for c in C:variants[c[:2]].append(c)
  for seq in sequences:
   # Complete adjacent groups in an observed component segmentation. Never gold-derived.
   for size in [2,3]:
    for i in range(len(seq)-size+1):
     srcbase=seq[i:i+size]
     if not compatible(srcbase):continue
     for targetbase in seq:
      if targetbase in srcbase or not compatible(srcbase+[targetbase]):continue
      lists=[variants[x[:2]] for x in srcbase+[targetbase]]
      if not all(lists):continue
      for combo in itertools.product(*lists):
       if compatible(combo):slots.add((tuple(sorted(combo[:-1])),combo[-1]))
 # Fixed supplementary cap. Native groups get a reserved quarter of new slots;
 # unused capacity is reassigned. Every original v10 slot stays protected.
 supplement=slots-set(protected)
 def rank(x):
  src,target=x;distance=min(abs((c[0]+c[1])-(target[0]+target[1])) for c in src)
  return distance,sum(c[1]-c[0] for c in (*src,target)),x
 binary=sorted((x for x in supplement if len(x[0])==1),key=rank);multi=sorted((x for x in supplement if len(x[0])>1),key=rank)
 pick=binary[:3072]+multi[:1024];seen=set(pick)
 remainder=sorted((x for x in supplement if x not in seen),key=rank)
 pick+=remainder[:4096-len(pick)];kept=set(protected)|set(pick)
 return kept,{'slots_before_cap':len(slots),'slots_after_cap':len(kept),'supplement_before_cap':len(supplement),'supplement_after_cap':len(pick),'protected_slots':len(protected),'binary_supplement':sum(len(x[0])==1 for x in pick),'multisource_supplement':sum(len(x[0])>1 for x in pick)}
def build():
 inputs={d['id']:d for p in (R/'candidate_extract/inputs').glob('*.json') for d in read(p)['documents']}
 raw={}
 for p in (R/'candidate_extract/raw').glob('*.json'):
  ds=read(p)['documents'];ids=[d['id'] for d in ds];expected=[d['id'] for d in read(R/'candidate_extract/inputs'/p.name)['documents']]
  assert ids==expected and len(set(ids))==len(ids)
  raw.update({d['id']:d for d in ds})
 assert set(inputs)==set(raw),'All 24 extraction outputs must exist before construction'
 old={};oldraw={};frozen=[]
 for family in ['cdcp_scoring','new_corpora']:
  root=W/'research_1011_v10'/family
  old.update({d['id']:d for d in read(root/'candidate_pools.json')['documents']});frozen.append(root/'candidate_pools.json')
  for p in (root/'raw_predictions').glob('*.json'):oldraw.update({d['id']:d for d in read(p)['documents']});frozen.append(p)
 out=R/'candidate/constructed';out.mkdir(parents=True,exist_ok=False)
 write(out/'input_freeze.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'code_sha256':sha(__file__),'gold_read':False,'cap_semantics':'all original components/slots protected, plus64 components and4096 slots; 3072 binary +1024 multi reservation with remainder reuse','hashes':{str(p.relative_to(W)):sha(p) for p in frozen+list((R/'candidate_extract/inputs').glob('*.json'))+list((R/'candidate_extract/raw').glob('*.json'))}})
 summary=[]
 for ident,b in sorted(inputs.items()):
  text=b['text'];corpus=b['corpus'];original=old[ident];C0={key(c) for c in original['components'].values()};protected={(tuple(sorted(key(original['components'][c]) for c in r['sources'])),key(original['components'][r['target']])) for r in original['relations'].values()}
  a,aa,aseq,agroups,aerrors=raw_components(text,corpus,oldraw[ident]);fresh,alts,fseq,fgroups,ferrors=raw_components(text,corpus,raw[ident])
  salvage=punctuation_variants(a,text);primary=punctuation_variants(fresh,text);alt=punctuation_variants(alts,text)
  C1,_=select_components(C0,[salvage]);C2,_=select_components(C0,[salvage,primary,alt]);C3,_=select_components(C0,[salvage,primary,alt,expand_boundaries(salvage|primary|alt,text)])
  layers=[('A_original',C0,[],[]),('B_parse_components',C1,[],agroups),('C_separate_extraction',C2,[],agroups),('D_boundary_and_joint',C3,aseq+fseq,agroups+fgroups)]
  data=[]
  for name,C,seq,groups in layers:
   tracemalloc.start();start=time.perf_counter()
   if name=='A_original':slots=protected;cost={'slots_before_cap':len(slots),'slots_after_cap':len(slots),'protected_slots':len(slots),'supplement_before_cap':0,'supplement_after_cap':0}
   else:slots,cost=slots_for(C,protected,corpus,seq,groups)
   seconds=time.perf_counter()-start;current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
   relations=sorted((src,target,label) for src,target in slots for label in core.LABELS[corpus])
   row={'layer':name,'components':sorted(C),'relations':relations,'cost':{**cost,'component_candidates':len(C),'relation_candidates':len(relations),'slot_construction_seconds_with_tracemalloc':seconds,'python_allocation_peak_bytes':peak}};data.append(row)
  # A cheap upper-bound diagnosis of types: no extra predictions or scored outputs.
  spans={c[:2] for c in C3};alltypes={(s,e,t) for s,e in spans for t in core.TYPES[corpus]}
  write(out/f'{ident}.json',{'id':ident,'corpus':corpus,'layers':data,'all_native_types_component_upper_universe':sorted(alltypes),'original_component_parse_errors':aerrors,'new_component_parse_errors':ferrors,'new_graph_component_counts':[len(g['components']) for g in raw[ident]['graphs']]})
  summary.append({'id':ident,'corpus':corpus,'layers':[{k:v for k,v in row.items() if k not in ['components','relations']} for row in data],'all_types_count':len(alltypes)})
  print(json.dumps(summary[-1]),flush=True)
 write(out/'summary.json',{'documents':summary})
 write(out/'output_freeze.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'gold_read':False,'hashes':{p.name:sha(p) for p in out.glob('*.json')}})
def canonical_rel(r):return tuple(sorted(tuple(c) for c in r[0])),tuple(r[1]),r[2]
def evaluate():
 inp=R/'candidate/constructed';out=R/'candidate/evaluation/coverage.json';assert not out.exists()
 for p,h in read(inp/'input_freeze.json')['hashes'].items():assert sha(W/p)==h
 for p,h in read(inp/'output_freeze.json')['hashes'].items():assert sha(inp/p)==h
 gold=read(R/'candidate/evaluation/source_gold.json')['documents'];rows=[];agg=defaultdict(Counter)
 for g in gold:
  z=read(inp/f"{g['id']}.json");gc=[(c['char_start'],c['char_end'],c['type']) for c in g['components']];GC=set(gc);GR={(tuple(sorted(gc[i] for i in r['sources'])),gc[r['target']],r['type']) for r in g['relations']};multi={r for r in GR if len(r[0])>1};gs={c[:2] for c in GC}
  for layer in z['layers']:
   C={tuple(c) for c in layer['components']};E={canonical_rel(r) for r in layer['relations']};span={c[:2] for c in C}
   row={'id':g['id'],'corpus':g['corpus'],'layer':layer['layer'],'gold_C':len(GC),'gold_R':len(GR),'gold_multi_R':len(multi),'C_hit':len(C&GC),'span_hit':len(span&gs),'R_hit':len(E&GR),'multi_R_hit':len(E&multi),'all_endpoints_typed':sum(set(src)|{target}<=C for src,target,label in GR),'all_endpoints_span':sum(all(c[:2] in span for c in (*src,target)) for src,target,label in GR),'missing_C_keys':sorted(GC-C),'missing_R_keys':sorted(GR-E),'cost':layer['cost']}
   rows.append(row);a=agg[g['corpus'],layer['layer']]
   for k in ['gold_C','gold_R','gold_multi_R','C_hit','span_hit','R_hit','multi_R_hit','all_endpoints_typed','all_endpoints_span']:a[k]+=row[k]
   a['documents']+=1;a['components']+=len(C);a['relations']+=len(E)
  upper={tuple(c) for c in z['all_native_types_component_upper_universe']};rows[-1]['all_types_C_hit']=len(GC&upper)
  rows[-1]['all_types_endpoint_R_hit']=sum(set(src)|{target}<=upper for src,target,label in GR)
 write(out,{'status':'POST_FREEZE_DIAGNOSTIC','aggregates':[dict(corpus=c,layer=l,**a) for (c,l),a in sorted(agg.items())],'by_document':rows,'not_end_to_end':'Candidate membership and endpoint accessibility only. Extra candidates have not been semantically scored or selected. No F1 benefit is inferred.'})
 print(json.dumps(read(out)['aggregates'],indent=2))
if __name__=='__main__':build() if sys.argv[1]=='build' else evaluate()
