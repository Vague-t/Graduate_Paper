from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parent
sys.path.insert(0,str(WORK/'research_0920/vendor'))
import numpy as np

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hash_text(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def dump(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def jsonl(p,rows):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w') as f:
  for x in rows:f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
def load_jsonl(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]
def rand(*parts):return np.random.default_rng(int(hash_text('|'.join(map(str,parts)))[:16],16))
def uniform(*parts):return int(hash_text('|'.join(map(str,parts)))[:13],16)/16**13
def ckey(c):return c['start'],c['end'],c['type']
def rkey(r):return tuple(r['sources']),r['target'],r['type']
def rid(r):return 'r'+hash_text(json.dumps(rkey(r),ensure_ascii=False,separators=(',',':')))[:16]
def counts(pred,gold):
 p,g=set(pred),set(gold);return [len(p&g),len(p-g),len(g-p)]
def f1(a):
 a=np.asarray(a);den=2*a[...,0]+a[...,1]+a[...,2]
 return np.divide(200*a[...,0],den,out=np.zeros_like(den,dtype=float),where=den>0)
def legal(d,C,R):
 cs=d['components'];rs=d['relations'];C=set(C);R=set(R);issues=[]
 if not C<=cs.keys() or not R<=rs.keys():return ['unknown object']
 order=sorted(C,key=lambda x:ckey(cs[x]));positions={x:i for i,x in enumerate(order)}
 for a,b in zip(order,order[1:]):
  if cs[a]['end']>cs[b]['start']:issues.append('overlap')
 slots=set()
 for k in R:
  r=rs[k];ss=set(r['sources'])
  if not ss or r['target'] in ss or not (ss|{r['target']})<=C:issues.append('endpoint');continue
  slot=(tuple(r['sources']),r['target'])
  if slot in slots:issues.append('duplicate slot')
  slots.add(slot)
  if d['corpus']=='AAEC' and len(ss)!=1:issues.append('nonbinary')
  if d['corpus']=='CDCP':
   ix=sorted(positions[x] for x in ss)
   if ix!=list(range(ix[0],ix[-1]+1)):issues.append('nonconsecutive sources')
 return issues
