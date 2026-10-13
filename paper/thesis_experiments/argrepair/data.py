"""Read official archives, preserve all test documents and native hyperedges."""
from dataclasses import replace
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,json,zipfile,random,re
from .schema import *
from .io import write_json,write_jsonl,file_hash

def text_hash(text):return hashlib.sha256(text.encode()).hexdigest()
def _native(doc_id,corpus,text,split,spans,edges,audit,attributes=()):
    cs={}
    for ident,(start,end,label) in spans.items():
        if not 0<=start<end<=len(text):raise ValueError(f'{doc_id}: invalid annotation offsets {ident}')
        a,b=start,end
        while a<b and text[a].isspace():a+=1
        while b>a and text[b-1].isspace():b-=1
        if a==b:raise ValueError(f'{doc_id}: whitespace-only component')
        if (a,b)!=(start,end):audit['trimmed'].append({'doc_id':doc_id,'id':ident,'before':[start,end],'after':[a,b]})
        cs[ident]=Component(a,b,label)
    graph=Graph(tuple(cs.values()),tuple(Relation(tuple(cs[s] for s in ss),cs[t],lab) for ss,t,lab in edges))
    inp=InputDocument(doc_id,corpus,text,corpus+':'+text_hash(text),split)
    issues=graph_errors(inp,graph)
    if issues:audit['annotation_issues'].append({'doc_id':doc_id,'issues':issues,'action':'preserved_not_silently_removed'})
    # Char-native identity preserves boundaries inside evaluation tokens.
    bounds={p for m in re.finditer(r'\w+|[^\w\s]',text) for p in (m.start(),m.end())}
    for c in graph.components:
        if c.start not in bounds or c.end not in bounds:audit['inside_token'].append({'doc_id':doc_id,'component':c.to_dict()})
    annotations=tuple({'component':cs[ident].to_dict(),'name':name,'value':value} for name,ident,value in attributes)
    return Document(inp,graph,annotations)

def read_official(aaec_archive,aaec_split,cdcp_archive):
    audit={'trimmed':[],'inside_token':[],'annotation_issues':[],'duplicates':[],'cross_split_duplicates':[]}
    docs=[]
    with zipfile.ZipFile(aaec_archive) as z:
        split_rows=list(csv.DictReader(Path(aaec_split).read_text().splitlines(),delimiter=';'))
        for row in sorted(split_rows,key=lambda r:r['ID']):
            ident=row['ID'];prefix='brat-project-final/'+ident
            text=z.read(prefix+'.txt').decode('utf-8');ann=z.read(prefix+'.ann').decode('utf-8');spans={};edges=[];attributes=[]
            for line in ann.splitlines():
                parts=line.split('\t')
                if parts[0].startswith('T'):
                    typ,a,b=parts[1].split();a=int(a);b=int(b)
                    if text[a:b]!=parts[2]:raise ValueError(f'{ident}: annotation text mismatch')
                    spans[parts[0]]=(a,b,typ)
                elif parts[0].startswith('R'):
                    lab,s,t=parts[1].split();edges.append(((s.split(':')[1],),t.split(':')[1],lab))
                elif parts[0].startswith('A'):
                    name,ident_attr,value=parts[1].split();attributes.append((name,ident_attr,value))
            docs.append(_native('aaec_'+ident,'aaec',text,row['SET'].lower(),spans,edges,audit,attributes))
    with zipfile.ZipFile(cdcp_archive) as z:
        for path in sorted(n for n in z.namelist() if n.endswith('.ann.json')):
            split=path.split('/')[1];ident=Path(path).name.split('.')[0]
            ann=json.loads(z.read(path));text=z.read(path.replace('.ann.json','.txt')).decode('utf-8')
            if len(ann['prop_offsets'])!=len(ann['prop_labels']):raise ValueError('annotation lengths')
            spans={i:(a,b,t) for i,((a,b),t) in enumerate(zip(ann['prop_offsets'],ann['prop_labels']))}
            edges=[(tuple(range(a,b+1)),t,lab) for field,lab in [('reasons','reason'),('evidences','evidence')] for (a,b),t in ann[field]]
            docs.append(_native('cdcp_'+ident,'cdcp',text,split,spans,edges,audit))
    # Keep one canonical train representative; never delete a test document.
    groups=defaultdict(list)
    for d in docs:groups[d.source_group].append(d)
    retained=[]
    for group,ds in sorted(groups.items()):
        train=sorted((d for d in ds if d.split=='train'),key=lambda d:d.doc_id)
        test=[d for d in ds if d.split=='test']
        if train and test:
            audit['cross_split_duplicates'].append({'group':group,'train':[d.doc_id for d in train],'test':[d.doc_id for d in test],'action':'train_excluded_test_preserved'})
            train=[]
        if len(train)>1:
            audit['duplicates'].append({'retained':train[0].doc_id,'excluded':[d.doc_id for d in train[1:]],'annotation_equal':all(d.gold==train[0].gold for d in train)})
        retained+=train[:1]+test
    audit['raw_documents']=dict(Counter((d.corpus+'_'+d.split) for d in docs))
    audit['retained_documents']=dict(Counter((d.corpus+'_'+d.split) for d in retained))
    audit['statistics']={}
    for corpus in TYPES:
        for split in ('train','test'):
            ds=[d for d in retained if d.corpus==corpus and d.split==split]
            audit['statistics'][corpus+'_'+split]={'documents':len(ds),'components':sum(len(d.gold.components) for d in ds),'relations':sum(len(d.gold.relations) for d in ds),'multi_source':sum(len(r.sources)>1 for d in ds for r in d.gold.relations),'attributes':sum(len(d.annotations) for d in ds)}
    audit['sources']={str(p):file_hash(p) for p in (aaec_archive,aaec_split,cdcp_archive)}
    return sorted(retained,key=lambda d:d.doc_id),audit

def split_roles(docs,seed=17,folds=3):
    """OOF over ALL training groups; heldout records partition into 80/10/10 roles."""
    if folds<2:raise ValueError('OOF requires at least two folds')
    result=[];manifest={'seed':seed,'folds':folds,'documents':{}}
    for corpus in TYPES:
        groups=sorted({d.source_group for d in docs if d.corpus==corpus and d.split=='train'})
        random.Random(seed).shuffle(groups)
        n=len(groups);cal=round(n*.1);pol=round(n*.1)
        if n<folds:raise ValueError('too few training groups for OOF')
        roles={g:('calibration' if i<cal else 'policy' if i<cal+pol else 'fit') for i,g in enumerate(groups)}
        fold={g:i%folds for i,g in enumerate(groups)}
        for d in docs:
            if d.corpus!=corpus:continue
            role=roles[d.source_group] if d.split=='train' else 'test'
            result.append(replace(d,input=replace(d.input,split=role)))
            manifest['documents'][d.doc_id]={'source_group':d.source_group,'official_split':d.split,'role':role,'oof_fold':fold.get(d.source_group)}
    return sorted(result,key=lambda d:d.doc_id),manifest

def prepare(output,aaec_archive,aaec_split,cdcp_archive,seed=17):
    output=Path(output)
    if (output/'split_manifest.json').exists():raise FileExistsError(output)
    docs,audit=read_official(aaec_archive,aaec_split,cdcp_archive)
    role_docs,splits=split_roles(docs,seed)
    output.mkdir(parents=True,exist_ok=True)
    for corpus in TYPES:
        for role in ('fit','calibration','policy','test'):
            ds=[d for d in role_docs if d.corpus==corpus and d.split==role]
            write_jsonl(output/f'{corpus}_{role}.jsonl',(d.to_dict() for d in ds))
            write_jsonl(output/f'{corpus}_{role}_inputs.jsonl',(d.input.to_dict() for d in ds))
        tr=[replace(d,input=replace(d.input,split='train')) for d in role_docs if d.corpus==corpus and d.split!='test']
        write_jsonl(output/f'{corpus}_train.jsonl',(d.to_dict() for d in tr))
        for fold in range(3):
            fit=[d for d in tr if splits['documents'][d.doc_id]['oof_fold']!=fold]
            held=[d for d in role_docs if d.corpus==corpus and splits['documents'][d.doc_id]['oof_fold']==fold]
            write_jsonl(output/f'{corpus}_fold{fold}_train.jsonl',(d.to_dict() for d in fit))
            write_jsonl(output/f'{corpus}_fold{fold}_heldout.jsonl',(d.to_dict() for d in held))
            write_jsonl(output/f'{corpus}_fold{fold}_inputs.jsonl',(d.input.to_dict() for d in held))
    write_json(output/'data_audit.json',audit);write_json(output/'split_manifest.json',splits)
    return audit
