"""Validate the scope of the editorial revision, not research completion."""
from pathlib import Path
import json,re,hashlib
W=Path(__file__).resolve().parent;R=W.parent
old=(R/'report_1010_v1_full.md').read_text();new=(R/'report_1010_v2_full.md').read_text()
changes=json.loads((W/'changes.json').read_text());mapping=changes['table_mapping']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def table_blocks(text):
    result={};lines=text.splitlines()
    for i,line in enumerate(lines):
        m=re.fullmatch(r'表([A-H0-9]+-\d+) (.+)',line)
        if not m:continue
        j=i+1
        while j<len(lines) and not lines[j].strip():j+=1
        rows=[]
        while j<len(lines) and lines[j].startswith('|'):rows.append(lines[j]);j+=1
        assert rows,m[0]
        result[m[1]]={'title':m[2],'rows':'\n'.join(rows)}
    return result
ot,nt=table_blocks(old),table_blocks(new)
removed={'3-1','3-6','4-1'}
assert len(ot)==47 and len(nt)==44
preserved=[]
for key,record in ot.items():
    if key in removed:continue
    target=mapping.get(key,key)
    assert record['title']==nt[target]['title'],key
    expected=re.sub(r'表([34]-\d+)(?!\d)',lambda m:'表'+mapping.get(m[1],m[1]),record['rows'])
    if key=='F-2':expected=expected.replace('5.1至5.5阶段增量、对象变化与配置选择','5.1至5.5条件增量、净计数、配置与超边范围')
    assert expected==nt[target]['rows'],key
    preserved.append({'old':key,'new':target,'payload_identical_except_authorized_crossrefs':True})
for prefix in sorted(set(k.split('-')[0] for k in nt)):
    nums=[int(k.split('-')[1]) for k in nt if k.startswith(prefix+'-')]
    assert nums==list(range(1,len(nums)+1)),(prefix,nums)
captions=set(re.findall(r'^(?:\*\*)?((?:表|图|算法)[A-H0-9]+-\d+)(?=\s)',new,re.M))
refs=set(re.findall(r'(?:表|图|算法)[A-H0-9]+-\d+(?!\d)',new))
assert not refs-captions,sorted(refs-captions)
assert re.findall(r'\$\$(.*?)\$\$',new,re.S)==re.findall(r'\$\$(.*?)\$\$',old,re.S)
assert re.findall(r'```algorithm.*?```',new,re.S)==re.findall(r'```algorithm.*?```',old,re.S)
def block(t,a,z):return t[t.index(a):t.index(z)]
assert block(old,'## 附录E','## 附录F')==block(new,'## 附录E','## 附录F')
assert block(old,'## 参考文献','## 附录A')==block(new,'## 参考文献','## 附录A')
assert len(re.findall(r'^## 第[一二三四五六]章 ',new,re.M))==6
raw=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
for name in raw:assert sha(W/name)==sha(R/'_revision_1010_v1'/name),name
for image in (W/'figures').glob('*.png'):assert sha(image)==sha(R/'_revision_1010_v1/figures'/image.name)
evidence=json.loads((W/'template-evidence.json').read_text())
for name,h in evidence['baseline_hashes'].items():assert sha(R/name)==h,name
required=['抽取成绩表3-5、学习消融表3-6和中心比较表3-8','独立的两阶段决策简例','0.20＋0.90＝1.10','0.80＋0.20＝1.00','可能使关系密集、受检因素较多的文档更难通过','当前材料不能认定偏差已经发生','局部累计编辑与全局净编辑约束的差异','不能说被全局在所有维度严格支配','净错误变化与对象分析边界','训练条件变化的解释边界','在线配置的质量与时间取舍','超边规模与恢复范围','当前没有证据选择其中一种','QOS式适配不替代端到端外部对照','属于本研究的验证缺口','不要求共同修复少、独有修复多或交互显著为正']
for text in required:assert text in new,text
for text in ['表3-11','表3-10','表4-10','表3-6 表达变化','表3-1 训练侧诊断','表4-1 初始错误诊断','本章使用同一批人工情景记录，围绕五个综合问题']:assert text not in new,text
# Track outcomes explicitly instead of reporting editorial coverage as scientific closure.
items=[
 {'id':'R1','issue':'正文方案化','location':['## 摘要','### 3.1','#### 3.6.2','### 4.1','### 5.2','### 5.3','### 6.3','### H.5'],'editorial':'完成收束','research':'未闭合','blocker':'真实诊断与结果尚未取得，不能改写为已完成发现'},
 {'id':'R2','issue':'任务内必要性','location':['### 1.1','#### 3.6.2','### H.1','### H.2'],'editorial':'完成风险与比较边界说明','research':'未完成','blocker':'缺真实原文和增强文、审核判断、源覆盖与固定基线预测'},
 {'id':'R3','issue':'第一项增量可信度','location':['#### 1.2.2','#### 3.6.1','#### 3.6.3','### 3.7','### H.2'],'editorial':'保留两项关键比较，收紧近邻主张','research':'未完成','blocker':'同条件数据构造与同增强集合学习比较仍为人工情景'},
 {'id':'R4','issue':'局部事务采用价值','location':['#### 4.2.5','#### 4.6.1','#### 4.6.5','### 5.4','### H.3','### H.5'],'editorial':'明确成本、可行域和待定选择','research':'未完成且定位待定','blocker':'缺真实端到端时延、预检失败、规模分组、求解与误改轨迹'},
 {'id':'R5','issue':'外部系统比较','location':['### G.2','### G.4','### H.5'],'editorial':'明确至少一个兼容系统及转换边界','research':'未完成','blocker':'未安装或执行外部模型，表示审计不等于成绩复现'},
 {'id':'R6','issue':'第五章标题超前','location':['## 第五章','### 5.2','### 5.3','### 5.4','### 5.5','### H.4'],'editorial':'标题和内容收束完成','research':'对象级综合发现未完成','blocker':'现有TP/FP/FN缺对象身份，不能恢复交集、作用路径或同输入真实案例'},
 {'id':'S1','issue':'成绩轨道表格误引','location':['#### 3.6.1'],'editorial':'已纠正并核对全篇重编号','research':'不涉及新增实证','blocker':None},
 {'id':'S2','issue':'不同数值算例混引','location':['#### 4.6.2'],'editorial':'已纠正独立简例及赋值条件','research':'仅数学示意','blocker':None},
]
for item in items:
    item['lines']={a:next(i for i,line in enumerate(new.splitlines(),1) if line.startswith(a)) for a in item['location']}
main_old=block(old,'## 摘要','## 参考文献');main_new=block(new,'## 摘要','## 参考文献')
result={'passed':True,'scope':'EDITORIAL_SCOPE_AND_IDENTITY_ONLY','source_sha256':sha(R/'report_1010_v2_full.md'),'review_sha256':sha(R/'1010_v1全局评审与完整修改建议.md'),'source_chars':len(new),'main_chars_before':len(main_old),'main_chars_after':len(main_new),'main_chars_removed':len(main_old)-len(main_new),'removed_diagnostic_tables':sorted(removed),'retained_table_payloads':preserved,'table_reference_targets_valid':True,'display_formulas_preserved':32,'references_preserved':49,'raw_files_preserved':raw,'baseline_unchanged':True,'items':items,'genuine_corpus_or_model_runs':0,'research_findings_certified':False}
(W/'review_coverage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in {'items','retained_table_payloads'}},ensure_ascii=False))
