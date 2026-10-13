"""Read native training archives. No model inference or test-split evaluation."""
from common import *
import csv,zipfile,re
TYPES={'AAEC':['MajorClaim','Claim','Premise'],'CDCP':['reference','testimony','fact','value','policy']}

def main():
 docs=[];excluded=[];groups={};source_rows=[]
 base=WORK/'research_0920/data'
 for corpus,name in [('AAEC','aaec_brat.zip'),('CDCP','cdcp_acl17.zip')]:
  p=base/name
  with zipfile.ZipFile(p) as z:
   if corpus=='AAEC':
    ids=sorted(x['ID'] for x in csv.DictReader((base/'aaec_split.csv').read_text().splitlines(),delimiter=';') if x['SET']=='TRAIN')
   else:ids=sorted(Path(s).name.split('.')[0] for s in z.namelist() if s.startswith('cdcp/train/') and s.endswith('.ann.json'))
   raw_count=len(ids)
   for ident in ids:
    docid=corpus.lower()+'_'+ident
    if corpus=='CDCP' and ident=='00411':
     excluded.append({'id':docid,'reason':'retain documented incomplete/duplicate annotation exclusion from existing loader'});continue
    if corpus=='AAEC':
     prefix='brat-project-final/'+ident;text=z.read(prefix+'.txt').decode();ann=z.read(prefix+'.ann').decode();spans=[];amap={};rawrels=[]
     for line in ann.splitlines():
      v=line.split('\t')
      if v[0].startswith('T'):
       t,s,e=v[1].split();s=int(s);e=int(e)
       assert text[s:e]==v[2],(docid,v[0],'native surface mismatch')
       amap[v[0]]=len(spans);spans.append((s,e,t))
      elif v[0].startswith('R'):
       t,a,b=v[1].split();rawrels.append((a.split(':')[1],b.split(':')[1],t))
     edges=[([amap[a]],amap[b],lab) for a,b,lab in rawrels]
    else:
     prefix='cdcp/train/'+ident;text=z.read(prefix+'.txt').decode();ann=json.loads(z.read(prefix+'.ann.json'))
     spans=[(s,e,t) for (s,e),t in zip(ann['prop_offsets'],ann['prop_labels'])]
     edges=[(list(range(a,b+1)),target,lab) for field,lab in [('reasons','reason'),('evidences','evidence')] for (a,b),target in ann[field]]
    digest=hash_text(text);group=groups.setdefault((corpus,digest),[]);group.append(docid)
    if len(group)>1:
     excluded.append({'id':docid,'reason':'duplicate exact text','representative':group[0]});continue
    cs={};gold=[];normalization=[]
    for i,(s,e,t) in enumerate(spans):
     before=[s,e];assert 0<=s<e<=len(text) and t in TYPES[corpus],docid
     while s<e and text[s].isspace():s+=1
     while e>s and text[e-1].isspace():e-=1
     assert s<e,docid
     if before!=[s,e]:normalization.append({'index':i,'source':before,'trimmed':[s,e]})
     gid=f'g{i:03d}';gold.append(gid);cs[gid]={'start':s,'end':e,'type':t,'origin_index':i,'origin':'native_gold','quote':text[s:e]}
     alt=TYPES[corpus][(TYPES[corpus].index(t)+1)%len(TYPES[corpus])]
     cs[f't{i:03d}']={**cs[gid],'type':alt,'origin':'constructed_type_error'}
     words=list(re.finditer(r'\S+',text[s:e]));cut=s+words[-1].start() if len(words)>1 else e-1
     while cut>s and text[cut-1].isspace():cut-=1
     if cut>s:cs[f'b{i:03d}']={**cs[gid],'end':cut,'quote':text[s:cut],'origin':'constructed_boundary_error'}
    rs={}
    for ss,t,lab in edges:
     sources=sorted([f'g{x:03d}' for x in ss],key=lambda c:ckey(cs[c]));rr={'sources':sources,'target':f'g{t:03d}','type':lab};rs[rid(rr)]=rr
    d={'id':docid,'corpus':corpus,'source_doc_id':ident,'source_split':'official_train','text':text,'text_sha256':digest,'source_archive':str(p.relative_to(WORK)),'annotation_coordinate':'native_characters_half_open_with_whitespace_trim','components':cs,'relations':rs,'gold_C':gold,'gold_R':sorted(rs),'normalization':normalization}
    errs=legal(d,gold,rs)
    if errs:
     excluded.append({'id':docid,'reason':'native graph incompatible with declared diagnostic constraints','issues':errs});continue
    docs.append(d)
   source_rows.append({'corpus':corpus,'archive':str(p.relative_to(WORK)),'sha256':sha(p),'raw_official_train_documents':raw_count})
 jsonl(ROOT/'data/native_documents.jsonl',docs)
 stats={}
 for corpus in TYPES:
  ds=[d for d in docs if d['corpus']==corpus]
  stats[corpus]={'documents':len(ds),'components':sum(len(d['gold_C']) for d in ds),'relations':sum(len(d['gold_R']) for d in ds),'multi_source_relations':sum(len(r['sources'])>1 for d in ds for r in d['relations'].values()),'max_components':max(len(d['gold_C']) for d in ds),'source_arity_counts':{str(k):sum(len(r['sources'])==k for d in ds for r in d['relations'].values()) for k in sorted({len(r['sources']) for d in ds for r in d['relations'].values()})}}
 dump(ROOT/'data/manifest.json',{'evidence_type':'ACTUAL_NATIVE_TRAINING_CORPUS_FOR_SIMULATION_NOT_HELDOUT_PERFORMANCE','sources':source_rows,'split_sha256':sha(base/'aaec_split.csv'),'duplicates':[v for v in groups.values() if len(v)>1],'exclusions':excluded,'statistics':stats,'test_texts_read':False,'token_alignment':'not performed; native character keys used consistently; previous token alignment issues not silently declared fixed','native_documents_sha256':sha(ROOT/'data/native_documents.jsonl')})
 print(json.dumps(stats,ensure_ascii=False,indent=2));print('excluded',len(excluded))
if __name__=='__main__':main()
