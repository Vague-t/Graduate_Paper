"""Verify native boundary example and create explicitly synthetic statistics fixtures."""
from pathlib import Path
import re, json, zipfile, hashlib
from recompute_statistics import demo_rows, self_test

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
native=ROOT/'research_0920/data/aaec_brat.zip'
with zipfile.ZipFile(native) as z:
    txt_name=next(n for n in z.namelist() if n.endswith('/essay098.txt') or n=='essay098.txt')
    ann_name=txt_name[:-4]+'.ann'
    data=z.read(txt_name);x=data.decode('utf-8')
    annotation=next(line for line in z.read(ann_name).decode('utf-8').splitlines() if line.startswith('T6\t'))
kind,b,e=annotation.split('\t')[1].split();b,e=int(b),int(e)
assert (kind,b,e)==('Claim',858,914)
text_sha=hashlib.sha256(data).hexdigest()
assert text_sha=='f68e231bdf7576fe87d57e801350c2b0ef2f513d51e29938b223671a392f528c'
tokens=[(m.start(),m.end(),m.group()) for m in re.finditer(r'\w+|[^\w\s]',x)]
def derived(left,right):
    overlap=[i for i,(a,z,_) in enumerate(tokens) if a<right and z>left]
    s,u=overlap[0],overlap[-1]
    rho=(left-tokens[s][0],tokens[u][1]-right)
    assert (tokens[s][0]+rho[0],tokens[u][1]-rho[1])==(left,right)
    return (s+1,u+1),rho
assert derived(858,914)==((162,172),(0,1))
assert derived(858,915)==((162,172),(0,0))
d=('AAEC','essay098',text_sha)
gold=(d,858,914,'Claim');contrast=(d,858,915,'Claim')
assert gold!=contrast and len({gold,contrast})==2
display1={'T6':gold};display2={'T100':gold}
assert set(display1.values())==set(display2.values())
target=(d,0,10,'Claim') # Synthetic endpoint for identity verification only.
def relation(sources,target,label):return (tuple(sorted(set(sources))),target,label)
assert relation([gold],target,'Support')!=relation([contrast],target,'Support')
assert relation([gold,contrast],target,'Support')==relation([contrast,gold],target,'Support')
assert (('AAEC','essay098','different_text_version'),858,914,'Claim')!=gold
boundary={'native_zip':str(native),'archive_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),'text_sha256':text_sha,'annotation':annotation,'token_rule':r'\w+|[^\w\s]','native_roundtrip':True,'contrast_roundtrip':True,'same_token_bounds':True,'distinct_character_keys':True,'renumbering_preserves_key':True,'endpoint_change_changes_relation':True,'source_set_order_invariant':True,'text_version_in_identity':True,'scope':'native T6 boundary verified; expanded span and auxiliary endpoints are constructed checks, not extra gold annotations'}
(BASE/'boundary_qa.json').write_text(json.dumps(boundary,ensure_ascii=False,indent=2))
(BASE/'statistics_selftest.json').write_text(json.dumps(self_test(),ensure_ascii=False,indent=2))
(BASE/'demo_counts.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in demo_rows())+'\n')
(BASE/'demo_family.json').write_text(json.dumps([{'dataset':'DEMO','a':'A','b':'B','object_family':'relation'}],indent=2))
pairs=[('training','T1/I0','T0/I0'),('pair','T1/I0','NoPair'),('inference','T1/I1','T1/I0'),('scope','T1/I1','RelationOnly'),('joint','Single','Sequential'),('regenerate','T1/I1','Regenerate'),('risk','T1/I1','NoRisk')]
family=[dict(dataset=d,comparison_id=k,a=a,b=b,object_family='relation') for d in ('AAEC','CDCP') for k,a,b in pairs]
(BASE/'main_family_14.json').write_text(json.dumps(family,ensure_ascii=False,indent=2))
print(json.dumps({'boundary_checks':8,'statistics_checks':9,'demo_records':len(demo_rows()),'main_family_size':len(family),'main_results_reproduced':False},ensure_ascii=False))
