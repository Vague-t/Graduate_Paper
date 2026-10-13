"""Gold-free graph parsing, finite candidate construction and legality checks."""
from pathlib import Path
import hashlib, json, re, itertools, time

ROOT = Path(__file__).resolve().parent
TYPES={'aaec':('MajorClaim','Claim','Premise'),
       'cdcp':('reference','testimony','fact','value','policy'), 'argunsc':('claim','premise'), 'casimedicos':('Claim','Premise')}
LABELS={'aaec':('attacks','supports'),'cdcp':('evidence','reason'), 'argunsc':('attack','support'), 'casimedicos':('Attack','Support')}
TOKEN=re.compile(r'\w+|[^\w\s]',re.UNICODE)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump_new(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():raise FileExistsError(p)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def ck(c):return (c['start'],c['end'],c['type'])
def overlap(a,b):return max(a['start'],b['start'])<min(a['end'],b['end'])
def slot(r):return (tuple(r['sources']),r['target'])
def endpoints(r):return set(r['sources'])|{r['target']}
def state_key(C,R):return (tuple(sorted(C)),tuple(sorted(R)))

def relation_legal(doc,r,C):
    cs=doc['components']
    if not endpoints(r)<=C or r['target'] in r['sources'] or not r['sources']:return False
    if len(set(r['sources']))!=len(r['sources']):return False
    if doc['corpus']=='cdcp':
        ordered=sorted(C,key=lambda c:ck(cs[c]))
        pos=[ordered.index(c) for c in r['sources']]
        if sorted(pos)!=list(range(min(pos),max(pos)+1)):return False
    return True

def legal(doc,C,R):
    cs=doc['components'];rs=doc['relations'];issues=[]
    if any(c not in cs for c in C):return ['unknown_component']
    for a,b in itertools.combinations(sorted(C),2):
        if overlap(cs[a],cs[b]):issues.append('overlapping_components:'+a+','+b)
    used=set()
    for rid in sorted(R):
        if rid not in rs:issues.append('unknown_relation:'+rid);continue
        r=rs[rid]
        if not relation_legal(doc,r,C):issues.append('invalid_endpoints_or_continuity:'+rid)
        if slot(r) in used:issues.append('multiple_labels_same_slot:'+rid)
        used.add(slot(r))
    return issues

def parse_graph(text,corpus,raw):
    cmap={};norm=[];notes=[]
    boundaries=list(TOKEN.finditer(text)); starts={m.start() for m in boundaries};ends={m.end() for m in boundaries}
    for c in raw['components']:
        cid=c['id'];q=c['quote'];occ=c.get('occurrence',0)
        if cid in cmap:raise ValueError('duplicate display component id '+cid)
        if c['type'] not in TYPES[corpus]:raise ValueError('illegal type '+str(c['type']))
        if not q or not isinstance(occ,int) or occ<0:raise ValueError('invalid quotation')
        matches=[m.start() for m in re.finditer('(?='+re.escape(q)+')',text)]
        if occ>=len(matches):raise ValueError('quote not matched '+cid)
        s=matches[occ];e=s+len(q)
        while s<e and text[s].isspace():s+=1
        while e>s and text[e-1].isspace():e-=1
        if s not in starts or e not in ends:raise ValueError('non-token boundary '+cid)
        key=(s,e,c['type']);cmap[cid]=key;norm.append(key)
    if len(set(norm))<len(norm):notes.append('deduplicated_identical_component_keys')
    rel=[]
    for r in raw['relations']:
        if r['type'] not in LABELS[corpus]:raise ValueError('illegal relation label')
        src=tuple(sorted({cmap[c] for c in r['sources']}));tgt=cmap[r['target']]
        if not src or tgt in src:raise ValueError('empty source or self loop')
        if corpus!='cdcp' and len(src)!=1:raise ValueError('nonbinary relation in binary corpus')
        rel.append((src,tgt,r['type']))
    return sorted(set(norm)),sorted(set(rel)),notes

def build_doc(blind,raw):
    start=time.monotonic();text=blind['text'];corpus=blind['corpus']
    parsed=[];errors=[]
    for g in raw.get('graphs',[]):
        try:
            C,R,notes=parse_graph(text,corpus,g)
            parsed.append({'candidate_id':g['candidate_id'],'C':C,'R':R,'normalization':notes})
        except Exception as e:errors.append({'candidate_id':g.get('candidate_id'),'error':type(e).__name__+': '+str(e)})
    allc=sorted({c for g in parsed for c in g['C']})
    # A small declared subset of v7's one-step boundary expansion. No gold use.
    variants={}
    for c in allc:
        s,e,t=c;vv={c}
        m=list(TOKEN.finditer(text[s:e]))
        if len(m)>1 and m[-1].group() in ('.',',',';',':','!','?'):
            ee=s+m[-1].start()
            while ee>s and text[ee-1].isspace():ee-=1
            if ee>s:vv.add((s,ee,t))
        variants[c]=sorted(vv)
    expanded=sorted({v for vv in variants.values() for v in vv})
    ids={c:'c'+str(i).zfill(3) for i,c in enumerate(expanded)}
    components={ids[c]:{'start':c[0],'end':c[1],'type':c[2],'quote':text[c[0]:c[1]],
                         'origin':'generated' if c in allc else 'terminal_punctuation_boundary_variant'} for c in expanded}
    slots=set();protected=set()
    # All compatible binary typed slots in this small observed component pool.
    for a,b in itertools.permutations(expanded,2):
        if max(a[0],b[0])>=min(a[1],b[1]):slots.add(((ids[a],),ids[b]))
    # Preserve native complete multi-source hypotheses and endpoint variants.
    for g in parsed:
        for src,tgt,lab in g['R']:
            original=(tuple(ids[c] for c in src),ids[tgt]);protected.add(original);slots.add(original)
            if len(src)>3:continue
            for combo in itertools.product(*(variants[c] for c in (*src,tgt))):
                if len(set(combo))!=len(combo):continue
                if any(max(a[0],b[0])<min(a[1],b[1]) for a,b in itertools.combinations(combo,2)):continue
                ss=tuple(sorted((ids[c] for c in combo[:-1]),key=lambda x:ck(components[x])))
                slots.add((ss,ids[combo[-1]]))
    if len(slots)>4096:raise RuntimeError('declared 4096 slot preflight limit exceeded')
    keys=sorted((s,t,l) for s,t in slots for l in LABELS[corpus])
    rid={key:'r'+str(i).zfill(4) for i,key in enumerate(keys)}
    relations={rid[(s,t,l)]:{'sources':list(s),'target':t,'type':l,
                             'origin':'protected_generated_slot' if (s,t) in protected else 'finite_supplement'} for s,t,l in keys}
    doc={'id':blind['id'],'corpus':corpus,'text':text,'components':components,'relations':relations,'graphs':[],
         'parse_errors':errors,'candidate_scope':{'generated_components':len(allc),'all_components':len(expanded),
          'boundary_variants':len(expanded)-len(allc),'slots_before_cap':len(slots),'relation_objects':len(relations),
          'all_types_per_span':False,'all_multisource_combinations':False,'gold_used':False}}
    for g in parsed:
        C=sorted(ids[c] for c in g['C']);R=sorted(rid[(tuple(ids[c] for c in src),ids[t],l)] for src,t,l in g['R'])
        issues=legal(doc,set(C),set(R))
        doc['graphs'].append({'candidate_id':g['candidate_id'],'components':C,'relations':R,
                              'normalization':g['normalization'],'structurally_valid':not issues,'issues':issues})
    doc['construction_seconds']=time.monotonic()-start
    return doc

def main():
    all_docs=[];summary=[]
    for corpus in ('aaec','cdcp'):
        bp=ROOT/'blind_inputs'/f'{corpus}.json';rp=ROOT/'raw_predictions'/f'{corpus}_luna.json'
        blind=json.loads(bp.read_text())['documents'];raw=json.loads(rp.read_text())['documents']
        rawmap={d['id']:d for d in raw}
        if set(rawmap)!={d['id'] for d in blind}:raise ValueError('document identity mismatch')
        for b in blind:
            d=build_doc(b,rawmap[b['id']]);all_docs.append(d)
            scoring={'id':d['id'],'corpus':corpus,'text':d['text'],
                     'components':[{'id':k,'quote':v['quote'],'type':v['type']} for k,v in d['components'].items()],
                     'relations':[{'id':k,'sources':v['sources'],'target':v['target'],'type':v['type']} for k,v in d['relations'].items()]}
            dump_new(ROOT/'scoring_inputs'/f"{d['id']}.json",scoring)
            summary.append({'id':d['id'],**d['candidate_scope'],'graphs':[(g['candidate_id'],g['structurally_valid'],g['issues']) for g in d['graphs']],
                            'parse_errors':d['parse_errors']})
    dump_new(ROOT/'candidate_pools.json',{'documents':all_docs,'raw_prediction_hashes':{p.name:sha(p) for p in sorted((ROOT/'raw_predictions').glob('*.json'))}})
    dump_new(ROOT/'candidate_audit.json',{'status':'BUILT','documents':summary,'code_sha256':sha(__file__),
             'scope_deviations':['only types proposed by Luna are retained','boundary expansion only terminal punctuation trim','multisource slots only model-proposed source groups and their boundary variants','no trained span head','scoring is separate same-model heuristic confidence, not trained/calibrated probability'],
             'scoring_input_hashes':{p.name:sha(p) for p in sorted((ROOT/'scoring_inputs').glob('*.json'))}})
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
