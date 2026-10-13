"""Audit upstream representations without model outputs or semantic gold repairs."""
from pathlib import Path
import ast, collections, csv, hashlib, itertools, json, re, unicodedata

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'datasets/raw'
TOKEN = re.compile(r'\w+|[^\w\s]', re.UNICODE)

def sha(text): return hashlib.sha256(text.encode()).hexdigest()
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def finish(doc):
    text=doc['text']; offsets=[(m.start(),m.end()) for m in TOKEN.finditer(text)]
    doc.update(text_sha256=sha(text),tokens=[text[s:e] for s,e in offsets],offsets=offsets)
    for c in doc['components']:
        found=[i for i,(s,e) in enumerate(offsets) if s>=c['char_start'] and e<=c['char_end']]
        if not found or offsets[found[0]][0]!=c['char_start'] or offsets[found[-1]][1]!=c['char_end']:
            doc['issues'].append({'kind':'gold_non_token_boundary','component':c})
        else: c.update(token_start=found[0],token_end=found[-1]+1)
    for a,b in itertools.combinations(doc['components'],2):
        if max(a['char_start'],b['char_start'])<min(a['char_end'],b['char_end']):
            doc['issues'].append({'kind':'gold_component_overlap','a':a,'b':b})
    return doc

def argunsc():
    rows=list(csv.DictReader((RAW/'argunsc_base.csv').open()))
    groups=collections.defaultdict(list)
    for r in rows:groups[r['Speech']].append(r)
    docs=[]; global_ids={}; base_edges=set()
    for name,rs in groups.items():
        sent={};problems=[]
        for r in rs:
            sid=int(r['Sentence_ID'])
            if sid in sent and sent[sid]!=r['Full_Sentence']: problems.append({'kind':'inconsistent_sentence','sid':sid})
            sent[sid]=r['Full_Sentence']
        parts=[];positions={};pos=0
        for sid,s in sorted(sent.items()):positions[sid]=pos;parts.append(s);pos+=len(s)+1
        text=' '.join(parts); cs=[];idmap={};local_edges=[]
        for r in rs:
            if r['Component_Type']=='non-arg':continue
            try: cid,q=ast.literal_eval(r['Component'])
            except Exception as e:problems.append({'kind':'component_parse','row':r['ID'],'error':str(e)});continue
            q=q.strip();sentence=sent[int(r['Sentence_ID'])]
            start_of_sentence=positions[int(r['Sentence_ID'])]
            # A component can extend across multiple sentence records.
            hits=[m.start() for m in re.finditer('(?='+re.escape(q)+')',text)
                  if start_of_sentence<=m.start()<start_of_sentence+len(sentence)]
            if len(hits)!=1:
                problems.append({'kind':'component_string_alignment','upstream_id':cid,'quote':q,'sentence':sentence,'matches':len(hits)})
                continue
            s=hits[0];e=s+len(q)
            if cid in idmap: problems.append({'kind':'duplicate_component_id','upstream_id':cid});continue
            idmap[cid]=len(cs);global_ids[cid]=(name,q,r['Component_Type'])
            cs.append({'char_start':s,'char_end':e,'type':r['Component_Type'],'upstream_id':cid})
            try: incoming={} if r['Premises']=='standalone' else ast.literal_eval(r['Premises'])
            except Exception:
                problems.append({'kind':'relation_list_parse','upstream_id':cid,'value':r['Premises']});incoming={}
            if not isinstance(incoming,dict):
                problems.append({'kind':'relation_list_not_dict','upstream_id':cid,'value':r['Premises']});incoming={}
            for src,lab in incoming.items():local_edges.append((src,cid,lab));base_edges.add((src,cid,lab))
        rels=[]
        for src,tgt,lab in local_edges:
            if src not in idmap or tgt not in idmap:problems.append({'kind':'missing_relation_endpoint','source':src,'target':tgt})
            else:rels.append({'sources':[idmap[src]],'target':idmap[tgt],'type':lab})
        docs.append(finish({'id':'argunsc_'+name,'source_doc_id':name,'corpus':'argunsc','split':'unsplit_author_release','text':text,'components':cs,'relations':rels,'issues':problems,'text_reconstruction':'Full_Sentence by Sentence_ID once, joined with one space; original sentence characters preserved; exact multi-sentence component strings allowed if starting in their source sentence'}))
    pair_rows=list(csv.DictReader((RAW/'argunsc_component_relations_local.csv').open()))
    pair_edges=set();pair_issues=[]
    for r in pair_rows:
        if r['relation type']=='no relation':continue
        src,tgt=ast.literal_eval(r['ids of components']);pair_edges.add((src,tgt,r['relation type']))
        if src not in global_ids or tgt not in global_ids:pair_issues.append({'kind':'pair_unknown_endpoint','row':r['id']})
        elif global_ids[src][0]!=global_ids[tgt][0]:pair_issues.append({'kind':'cross_speech_pair','row':r['id']})
    audit={'documents':len(docs),'base_annotation_components':sum(r['Component_Type']!='non-arg' for r in rows),'base_relation_count':len(base_edges),'positive_pair_row_count':sum(r['relation type']!='no relation' for r in pair_rows),'unique_positive_pair_count':len(pair_edges),'base_only_edges':sorted(base_edges-pair_edges),'pair_only_edges':sorted(pair_edges-base_edges),'pair_issues':pair_issues,'relation_authority':'base.csv Premises on each component; pairs checked independently; mismatches retained in audit','issue_counts':dict(collections.Counter(i['kind'] for d in docs for i in d['issues']))}
    return docs,audit

def endpoint_key(s):
    # Only serialization differences: Unicode compatibility, whitespace, terminal punctuation.
    return ' '.join(unicodedata.normalize('NFKC',s).split()).rstrip(' .,:;!?')

def casimedicos():
    docs=[];stats={}
    for split in ['train','validation','test']:
        raw=json.loads((RAW/f'casimedicos_en_{split}_en_ordered.json').read_text())
        rmap={}; relation_file_nonobjects=[]
        for line in (RAW/f'casimedicos_relations_{split}_relations.jsonl').read_text().splitlines():
            record=json.loads(line)
            if not isinstance(record,dict):
                relation_file_nonobjects.append(record)
                if isinstance(record,list) and len(record)==1 and isinstance(record[0],dict):record=record[0]
                else:continue
            for k,v in record.items():
                assert k not in rmap,('duplicate relation document',split,k)
                rmap[k]=v
        split_docs=[]
        for row in raw:
            issues=[];cs=[];pieces=[];pos=0;ignored=collections.Counter()
            if not isinstance(row['text'],list) or not isinstance(row['labels'],list):
                docs.append({'id':'casimedicos_'+row['id'],'source_doc_id':row['id'],'corpus':'casimedicos','split':split,'text':None,'components':[],'relations':[],'issues':[{'kind':'missing_token_annotation','text_value':row['text'],'labels_value':row['labels']} ]});continue
            assert len(row['text'])==len(row['labels'])
            for toks,labs in zip(row['text'],row['labels']):
                assert len(toks)==len(labs)
                starts=[];ends=[]
                for j,t in enumerate(toks):
                    if j:pieces.append(' ');pos+=1
                    starts.append(pos);pieces.append(t);pos+=len(t);ends.append(pos)
                active=None
                for j,lab in enumerate(labs+['O']):
                    prefix,typ=(lab.split('-',1) if '-' in lab else ('O',None))
                    if typ not in ('Claim','Premise'):
                        if typ and prefix=='B':ignored[typ]+=1
                        typ=None;prefix='O'
                    if active and (prefix!='I' or typ!=active[1]):
                        cs.append({'char_start':starts[active[0]],'char_end':ends[j-1],'type':active[1]});active=None
                    if typ and prefix=='B':active=(j,typ)
                    elif typ and prefix=='I' and active is None:
                        issues.append({'kind':'orphan_BIO_I','sentence':len(pieces),'token':j,'label':lab});active=(j,typ)
                pieces.append('\n');pos+=1
            text=''.join(pieces).rstrip('\n')
            keys=collections.defaultdict(list)
            for i,c in enumerate(cs):keys[endpoint_key(text[c['char_start']:c['char_end']])].append(i)
            relations=[];alignment=[]
            if row['id'] not in rmap:issues.append({'kind':'missing_relation_record'})
            for ri,(a,b,l) in enumerate(rmap.get(row['id'],[])):
                aa=keys[endpoint_key(a)];bb=keys[endpoint_key(b)]
                if len(aa)!=1 or len(bb)!=1:
                    issues.append({'kind':'relation_string_alignment','row':ri,'source':a,'target':b,'source_matches':aa,'target_matches':bb});continue
                if aa==bb:issues.append({'kind':'self_relation','row':ri});continue
                relations.append({'sources':[aa[0]],'target':bb[0],'type':l})
                alignment.append({'row':ri,'source_component':aa[0],'target_component':bb[0],'source_raw':a,'target_raw':b})
            d=finish({'id':'casimedicos_'+row['id'],'source_doc_id':row['id'],'corpus':'casimedicos','split':split,'text':text,'components':cs,'relations':relations,'upstream_relation_count':len(rmap.get(row['id'],[])),'relation_alignment':alignment,'ignored_auxiliary_spans':dict(ignored),'issues':issues,'text_reconstruction':'upstream tokens joined by one space within each sentence, newline between sentences; gold spans from Claim/Premise BIO only'})
            split_docs.append(d);docs.append(d)
        stats[split]={'rows':len(raw),'token_annotation_rows':len(split_docs),'missing_token_rows':len(raw)-len(split_docs),'relation_records':len(rmap),'relation_file_nonobjects':relation_file_nonobjects,'complete_mapped_rows':sum(not d['issues'] for d in split_docs),'issue_counts':dict(collections.Counter(i['kind'] for d in split_docs for i in d['issues']))}
    return docs,{'splits':stats,'component_scope':'Claim and Premise BIO spans; Marker/Disease/Treatment/Diagnostics not relabelled; any relation needing an unmapped endpoint invalidates that document for strict full-graph study','relation_endpoint_alignment':'unique complete BIO-span match after NFKC, whitespace collapse and trailing .,:;!? removal; no edit-distance or semantic matching'}

if __name__=='__main__':
    audit={}
    for name,func in [('argunsc',argunsc),('casimedicos',casimedicos)]:
        docs,a=func();write(ROOT/'datasets/converted'/f'{name}.json',{'documents':docs});audit[name]=a
    write(ROOT/'datasets/conversion_audit.json',audit)
    print(json.dumps(audit,ensure_ascii=False,indent=2))
