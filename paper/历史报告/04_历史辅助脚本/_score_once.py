import json, os
src='/Users/channtang/Downloads/paper/research_1011_v12/casimedicos/inputs/casimedicos_318_140__01.json'
out='/Users/channtang/Downloads/paper/research_1011_v12/casimedicos/raw_scores/casimedicos_318_140__01.json'
x=json.load(open(src))
# Exact-object confidence: period-inclusive variants are the stronger boundary candidates.
cs={}
for k,v in x['components'].items():
    cs[k]=0.88 if v['quote'].endswith('.') else 0.60

def rel(a,b):
    # returns (attack, support), judged from the supplied text only
    if a.startswith('c00') and a in {'c000','c001','c002','c003','c004','c005'}:
        if b in {'c008','c009'}: return (0.01, 0.95 if a in {'c002','c003','c004','c005'} else 0.78)
        if b in {'c006','c007'}: return (0.01, 0.42 if a in {'c002','c003'} else (0.30 if a in {'c004','c005'} else 0.18))
        if b in {'c010','c011'}: return (0.01, 0.28 if a in {'c002','c003'} else (0.22 if a in {'c004','c005'} else 0.10))
        if b in {'c014','c015'}: return (0.01, 0.18 if a in {'c002','c003'} else (0.25 if a in {'c004','c005'} else 0.03))
        if b in {'c016','c017'}: return (0.01, 0.24 if a in {'c002','c003'} else (0.15 if a in {'c004','c005'} else 0.12))
        return (0.01,0.01)
    # Claim-to-claim relations.
    if a in {'c008','c009'}:
        if b in {'c006','c007','c010','c011','c014','c015','c016','c017'}: return (0.01,0.48)
    if a in {'c006','c007'}:
        if b in {'c010','c011','c016','c017'}: return (0.01,0.60)
    if a in {'c010','c011'}:
        if b in {'c006','c007','c016','c017'}: return (0.01,0.56)
    if a in {'c012','c013'}:
        if b in {'c006','c007','c016','c017'}: return (0.01,0.48)
    if a in {'c014','c015'}:
        if b in {'c006','c007','c016','c017'}: return (0.01,0.50)
    if a in {'c016','c017'}:
        if b in {'c006','c007'}: return (0.01,0.58)
    return (0.01,0.01)

ss=[]
for s in x['slots']:
    a=s['sources'][0]; b=s['target']; pa,ps=rel(a,b)
    ss.append([s['id'],pa,ps])
assert len(ss)==len(x['slots']) and [z[0] for z in ss]==[z['id'] for z in x['slots']]
assert all(0<=z[1]<=1 and 0<=z[2]<=1 and z[1]+z[2]<=1 for z in ss)
assert not os.path.exists(out)
os.makedirs(os.path.dirname(out),exist_ok=True)
json.dump({'id':x['id'],'batch':x['batch'],'model_requested':'gpt-5.6-luna','component_scores':cs,'slot_scores':ss,'notes':'Semantic judgments; period-inclusive component boundaries generally have higher confidence.'},open(out,'w'),ensure_ascii=False,indent=2)
print(out)
