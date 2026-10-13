"""Check the added tables against row records, independent of the authoring helper."""
from pathlib import Path
from collections import defaultdict
import csv,json,re,hashlib
W=Path(__file__).resolve().parent;R=W.parent
def read(n):return json.loads((W/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
data=read('review_derived_tables.json');rows=read('audit_judgements.json')['rows']
counts=defaultdict(lambda:[0,0,0])
with (W/'document_counts.csv').open() as f:
    for r in csv.DictReader(f):
        k=(r['dataset'],r['object'],r['method'])
        for i,n in enumerate(['tp','fp','fn']):counts[k][i]+=int(r[n])
for row in data['net_error_rows']:
    ds,obj=row['dataset'],row['object']
    for label,a,b in [('training','t1_i0','t0_i0'),('repair_t0','t0_i1','t0_i0'),('repair_t1','t1_i1','t1_i0')]:
        actual=[counts[ds,obj,a][i]-counts[ds,obj,b][i] for i in range(3)]
        assert actual==[row[label][x] for x in ['tp','fp','fn']]
for row in data['audit_rows']:
    for accept,key in [(True,'accepted'),(False,'rejected')]:
        selected=[x for x in rows if x['dataset']==row['dataset'] and x['method']==row['method'] and x['accepted']==accept]
        n=len(selected);d=sum(x['drift'] for x in selected)
        assert row[key]=={'n':n,'drift':d,'stable':n-d,'rate':100*d/n}
for n,digest in data['source_hashes'].items():assert sha(W/n)==digest==sha(R/'_revision_1009_v3'/n)
source=(R/'report_1009_v4_full.md').read_text()
captions=re.findall(r'^(表[0-9A-F]+-\d+) (.+)$',source,re.M)
assert len(captions)==len(set(x[0] for x in captions))==41
mentions=set(re.findall(r'表[0-9A-F]+-\d+',source)); assert not mentions-{x[0] for x in captions}
for chapter in ['3','5']:
    nums=[int(k.split('-')[1]) for k,_ in captions if k.startswith('表'+chapter+'-')]
    assert nums==list(range(1,len(nums)+1))
cfg=read('reference_config.json');roles=cfg['simulation_runtime_assumptions']['training_side_roles']
for ds in ['AAEC','CDCP']:
    s=roles[ds];assert s['source_documents']==s['scorer_fit']+s['calibration']+s['policy_selection']
    for key in ['scorer_fit','calibration','policy_selection']:assert str(s[key]) in source
assert cfg['configuration_id'] in source
assert '第五章跨语料分析采用另行声明的粗粒度映射' not in source
assert '表B-1 提议评估与提交的预算判定' in source
result={'passed':True,'scope':'DERIVED_SIMULATION_TABLES_AND_CROSS_REFERENCES','added_audit_rows':len(data['audit_rows']),'added_net_error_rows':len(data['net_error_rows']),'raw_data_byte_identical_to_v3':True,'table_labels_unique_and_all_references_resolved':True,'new_real_experiments':0,'source_sha256':sha(R/'report_1009_v4_full.md')}
(W/'review_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
