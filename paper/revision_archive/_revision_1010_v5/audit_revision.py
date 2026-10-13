"""Independent algebra and document-preservation checks; no empirical execution."""
from pathlib import Path
import hashlib,json,re,csv
from collections import defaultdict
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v4'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=(R/'report_1010_v4_full.md').read_text();new=(R/'report_1010_v5_full.md').read_text()
members=json.loads((W/'object_memberships.json').read_text())
counts={}
with (W/'document_counts.csv').open() as f:
    for x in csv.DictReader(f):
        if x['object']=='relation':counts[x['dataset'],x['document'],int(x['seed']),x['method']]=tuple(int(x[k]) for k in ['tp','fp','fn'])
totals=defaultdict(lambda:defaultdict(int));records=[]
for row in members:
    ds,doc,seed=row['dataset'],row['document'],row['seed'];g=set(row['gold']);p={k:set(v) for k,v in row['predictions'].items()}
    for k,v in p.items():assert (len(v&g),len(v-g),len(g-v))==counts[ds,doc,seed,k]
    pool=g-p['t0_i0'];t=(p['t1_i0']&g)-p['t0_i0'];i=(p['t0_i1']&g)-p['t0_i0']
    a,b,M=len(t),len(i),len(pool);lo=max(0,a+b-M);hi=min(a,b)
    assert t<=pool and i<=pool
    non=sorted(pool-t);inter=sorted(t)
    min_new=set(non[:min(b,len(non))])|set(inter[:lo])
    max_new=set(inter[:hi])|set(non[:b-hi])
    fixed=(p['t0_i1']&p['t0_i0'])|(p['t0_i1']-g)
    assigned=len(t&i)
    for tag,new_hits,expected in [('minimum',min_new,lo),('maximum',max_new,hi)]:
        candidate=fixed|new_hits
        assert len(new_hits)==b and len(new_hits&t)==expected
        assert (candidate&g&p['t0_i0'])==(p['t0_i1']&g&p['t0_i0'])
        assert candidate-g==p['t0_i1']-g
        assert (len(candidate&g),len(candidate-g),len(g-candidate))==counts[ds,doc,seed,'t0_i1']
        # Other three cells remain exactly the original sets; all T1-to-joint risks are unchanged.
        changed=dict(p);changed['t0_i1']=candidate
        for k in ['t0_i0','t1_i0','t1_i1']:assert changed[k]==p[k]
        risk=lambda q:(len((q['t1_i1']&g)-q['t1_i0']),len((q['t1_i0']&g)-q['t1_i1']),len((q['t1_i1']-g)-q['t1_i0']),len((q['t1_i0']-g)-q['t1_i1']))
        assert risk(changed)==risk(p)
    for k,v in [('records',1),('assigned',assigned),('minimum',lo),('maximum',hi)]:totals[ds][k]+=v
    records.append({'dataset':ds,'document':doc,'seed':seed,'a':a,'b':b,'M':M,'assigned':assigned,'minimum':lo,'maximum':hi,'minimum_new_objects':sorted(min_new),'maximum_new_objects':sorted(max_new)})
assert dict(totals['AAEC'])=={'records':240,'assigned':353,'minimum':26,'maximum':434}
assert dict(totals['CDCP'])=={'records':444,'assigned':505,'minimum':158,'maximum':550}
(W/'overlap_extremes.json').write_text(json.dumps(records,ensure_ascii=False,separators=(',',':'))+'\n')
nonunique={'passed':True,'scope':'ABSTRACT_RELATION_SET_NON_IDENTIFIABILITY','memberships_sha256':sha(W/'object_memberships.json'),'record_count':len(records),'bounds':totals,'extremes_sha256':sha(W/'overlap_extremes.json'),'all_four_cell_counts_preserved':True,'all_t1_to_joint_risks_preserved':True,'complete_graph_feasibility_tested':False,'real_model_runs':0}
(W/'nonuniqueness_audit.json').write_text(json.dumps(nonunique,ensure_ascii=False,indent=2)+'\n')
def tables(s):return dict(re.findall(r'^(表[A-H0-9]+-\d+) [^\n]+\n\n((?:\|[^\n]+\n)+)',s,re.M))
ot,nt=tables(old),tables(new);assert len(ot)==50 and len(nt)==47
mapping={'表3-10':'表H-2','表4-11':'表H-3','表4-12':'表H-4','表5-6':'表5-5','表5-7':'表5-4'}
removed=['表4-10','表5-4','表5-5'];checked=[]
def normalize(t):return t.replace('全局ILP等时限','全局ILP等求解预算').replace('全局等时限','全局等求解预算').replace('5.1至5.5条件增量、净计数、配置与超边范围','5.1至5.3条件增量、对象边界与配置选择').replace('5.5及附录E.8至E.9','5.2及附录E.8至E.9').replace('比较数据构造，不与T1全机制混比','文本、源选择及重加权的整体效应')
for label,payload in ot.items():
    if label in removed:continue
    target=mapping.get(label,label);assert normalize(payload)==nt[target],(label,target)
    checked.append([label,target])
assert len(checked)==47
for chapter in '123456ABCDEFGH':
    nums=[int(k.split('-')[1]) for k in nt if k.startswith('表'+chapter+'-')]
    if nums:assert nums==list(range(1,len(nums)+1)),(chapter,nums)
assert re.findall(r'\$\$(.*?)\$\$',new,re.S)==re.findall(r'\$\$(.*?)\$\$',old,re.S)
assert new[new.index('## 附录E'):new.index('## 附录F')]==old[old.index('## 附录E'):old.index('## 附录F')]
def refs(s):return s[s.index('## 参考文献'):s.index('## 附录A')]
assert refs(new)==refs(old)
def algorithms(s):return re.findall(r'```(?:algorithm|plaintext)\n(.*?)```',s,re.S)
assert algorithms(new)==algorithms(old) and len(algorithms(new))==3
images=re.findall(r'^!\[[^]]*\]\(([^)]+)\)',new,re.M);assert len(images)==11
for path in images:assert sha(R/path)==sha(P/'figures'/Path(path).name)
for caption in re.findall(r'(?:表|图|算法)[A-H0-9]+-\d+',re.sub(r'<!--.*?-->','',new)):
    assert re.search(r'^\*{0,2}'+re.escape(caption)+r' ',new,re.M),caption
main=new[:new.index('## 参考文献')]
assert '36秒' not in main and '353' not in main and '505' not in main
for token in ['式占位','Kawarada_proxy','UniASA_proxy','条件选项，并展示','4.6.8','表4-10','表5-7']:
    assert token not in new,token
for name,h in json.loads((W/'template-evidence.json').read_text())['baseline_hashes'].items():assert sha(R/name)==h,name
raw=list(json.loads((W/'scenario_manifest.json').read_text())['files'])+['generate_scenario.py','scenario_manifest.json']
supp=list(json.loads((W/'supplement_manifest.json').read_text())['files'])+['generate_supplement.py','supplement_manifest.json']
for name in raw+supp:assert sha(W/name)==sha(P/name),name
res=json.loads((W/'scenario_results.json').read_text())
direct={ds:{m:res['metrics'][ds]['t1_i1']['relation']['mean']-res['metrics'][ds][m]['relation']['mean'] for m in ['relation_only','single_object']} for ds in ['AAEC','CDCP']}
assert [round(direct[ds]['relation_only'],2) for ds in direct]==[3.59,4.39]
assert [round(direct[ds]['single_object'],2) for ds in direct]==[1.99,3.01]
result={'passed':True,'source_sha256':sha(R/'report_1010_v5_full.md'),'retained_table_payloads':checked,'removed_tables':removed,'preserved_images':images,'unchanged_display_equations':32,'algorithms_unchanged':3,'references_unchanged':49,'appendix_E_unchanged':True,'original_files_preserved':True,'all_original_data_preserved':True,'main_text_removes_assigned_external_scores_and_adoption_thresholds':True,'direct_comparison_deltas':direct,'nonuniqueness':nonunique,'real_model_runs':0}
(W/'revision_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':True,'tables_checked':len(checked),'figures_checked':len(images),'bounds':totals,'source_sha256':result['source_sha256']},ensure_ascii=False))
