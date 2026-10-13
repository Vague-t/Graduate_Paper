"""Atomic, version-bound run records. No default 'PASS' fields."""
from pathlib import Path
import json, hashlib, os, platform, sys, time
from .schema import canonical_json, Document, CandidatePool, Graph, InputDocument, Scores

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    os.replace(tmp,path)

def read_json(path):return json.loads(Path(path).read_text())
def read_jsonl(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def write_jsonl(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    with tmp.open('w') as f:
        for row in rows:f.write(canonical_json(row)+'\n')
    os.replace(tmp,path)
def load_documents(path):
    docs=[Document.from_dict(d) for d in read_jsonl(path)]
    if len({d.doc_id for d in docs})!=len(docs):raise ValueError('duplicate document id')
    return docs
def load_inputs(path):
    docs=[]
    for d in read_jsonl(path):
        if set(d)-{'doc_id','corpus','text','source_group','split'}:raise ValueError('inference input contains undeclared fields (possibly annotations)')
        docs.append(InputDocument(**d))
    if len({d.doc_id for d in docs})!=len(docs):raise ValueError('duplicate input id')
    return docs
def save_pool(pool):
    return {'input':pool.doc.to_dict(),'universe':Graph(pool.components,pool.relations).to_dict(),
            'initial':pool.initial.to_dict(),'protected':Graph(tuple(pool.protected_components),tuple(pool.protected_relations)).to_dict(),
            'metadata':pool.metadata,'key':pool.key}
def load_pool(d):
    doc=InputDocument(**d['input']);g=Graph.from_dict(d['universe']);p=Graph.from_dict(d['protected'])
    pool=CandidatePool(doc,g.components,g.relations,Graph.from_dict(d['initial']),frozenset(p.components),frozenset(p.relations),d.get('metadata',{}))
    if d.get('key',pool.key)!=pool.key:raise ValueError('candidate snapshot hash mismatch')
    return pool
def save_scores(pool,scores):
    return {'pool_key':pool.key,'components':[scores.components.get(c) for c in pool.components],
            'relations':[scores.relations.get(r) for r in pool.relations],'metadata':dict(scores.metadata)}
def load_scores(pool,d):
    if d['pool_key']!=pool.key:raise ValueError('scores from a different candidate snapshot')
    if len(d['components'])!=len(pool.components) or len(d['relations'])!=len(pool.relations):raise ValueError('score lengths')
    return Scores(dict(zip(pool.components,d['components'])),dict(zip(pool.relations,d['relations'])),d.get('metadata',{}))

class Run:
    def __init__(self,path,command,config=None,inputs=()):
        self.path=Path(path)
        if (self.path/'manifest.json').exists():raise FileExistsError(f'Choose a new run directory: {path}')
        self.path.mkdir(parents=True,exist_ok=True);self.start=time.monotonic()
        self.manifest={'status':'running','command':command,'configuration':config or {},'started_unix':time.time(),
            'python':sys.version,'platform':platform.platform(),'inputs':{str(p):file_hash(p) for p in inputs},
            'code':{p.name:file_hash(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
            'evidence_type':'EXECUTED_CODE_OUTPUT_NOT_HISTORICAL_THESIS_RESULTS'}
        self.flush()
    def flush(self):write_json(self.path/'manifest.json',self.manifest)
    def finish(self,**fields):
        self.manifest.update(status='completed',elapsed_seconds=time.monotonic()-self.start,**fields)
        self.manifest['outputs']={str(p.relative_to(self.path)):file_hash(p) for p in self.path.rglob('*') if p.is_file() and p.name!='manifest.json' and not p.name.endswith('.tmp')}
        self.flush()
    def fail(self,exc):
        self.manifest.update(status='failed',error=f'{type(exc).__name__}: {exc}',elapsed_seconds=time.monotonic()-self.start);self.flush()
