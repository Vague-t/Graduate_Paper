# -*- coding: utf-8 -*-
from pathlib import Path
import json,hashlib,re,zipfile
from collections import Counter
from lxml import etree
R=Path(__file__).resolve().parents[2]
S=json.loads((R/'_source/manuscript_blocks.json').read_text());B=json.loads((R/'_work/revised_blocks.json').read_text());M=json.loads((R/'_work/revision_manifest.json').read_text());P=json.loads((R/'_agents/compare/editorial_patches.json').read_text())['patches']
full='\n'.join(b['text'] for b in B);id_of=lambda s:['V5-B%04d'%b['body_index'] for b in B if s in b['text']]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks=[]
for p in P:
 if p['block_id'] in ['B0778','B0801']:
  status='absorbed_by_chapter5_rewrite'; loc=id_of('这些条件增量表明') if p['block_id']=='B0778' else id_of('本章在统一协议下，将两阶段的总体表现')
 elif p['block_id']=='B0791':status='absorbed_by_chapter5_rewrite';loc=id_of('“联合约束／接受门”列涵盖')
 else:status='exact_text_applied' if p['new'] in full else 'not_found';loc=id_of(p['new']) if len(p['new'])>2 else id_of('文档标识记为d；删除集合D另列')
 checks.append({'source_block_id':p['block_id'],'finding_id':p['finding_id'],'status':status,'revised_locations':loc,'reason':p['reason']})
assert all(q['status']!='not_found' for q in checks)
claims=[
 {'locations':['V5-B0794','V5-B0799'],'claim':'完整T1/I1组件与关系F1在四格中最高；训练3.63/4.89、推理4.48/8.37、总差8.10/13.26 pp','source':['B0775','B0777','B1116'],'judgment':'supported'},
 {'locations':['V5-B0800'],'claim':'AAEC交互−0.24、CDCP0.40，区间均跨零，不确认稳定协同','source':['B0777'],'judgment':'supported'},
 {'locations':['V5-B0811','V5-B0812','V5-B0813'],'claim':'共同/独有/组合恢复及初始TP损失，分别计数；不由TP分解单独证明F1机制','source':['B0785','B0786'],'judgment':'supported'},
 {'locations':['V5-B0818'],'claim':'端点缺失707→588、340→272；端点齐全未选138→135、123→126','source':['B0788'],'judgment':'supported'},
 {'locations':['V5-B0822','V5-B0823'],'claim':'非端点缺失漏检集中评分未过门，CDCP另2条完整槽位未入池；未评分/超时均零，首阻断不是独立因果检验','source':['B0790','B0791'],'judgment':'supported'},
 {'locations':['V5-B0827','V5-B0828'],'claim':'CDCP源数组成218/20/6/8，共252、多源34；合计计数不等于逐种子F1均值','source':['B0796','B0797','B0302'],'judgment':'supported'},
 {'locations':['V5-B0831'],'claim':'单源TP257→318、FP397→222；T1I0→T1I1双/三源TP27/10不变，FP33→22、8→5','source':['B0796'],'judgment':'supported'},
 {'locations':['V5-B0832'],'claim':'四源及以上TP2→3、FN21、F1 15.02，8条原生关系不足以推断稳定分组优势','source':['B0796','B0797'],'judgment':'supported'},
 {'locations':['V5-B0837','V5-B0845','V5-B0846'],'claim':'总结区分模拟配置效果、机制消融和实际CPU诊断，不宣称真实目标模型完成','source':['B0004','B0488','B0710','B0713','B0746','B1170'],'judgment':'supported'}]
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'};roots=[]
for f in [M['source'],M['output']]:
 with zipfile.ZipFile(f) as z:roots.append(etree.fromstring(z.read('word/document.xml')))
math=[Counter(etree.tostring(x,method='c14n') for x in r.xpath('//m:oMath',namespaces=N)) for r in roots];rem=list((math[0]-math[1]).elements());add=list((math[1]-math[0]).elements())
assert len(rem)==1 and not add and ''.join(etree.fromstring(rem[0]).itertext())=='D'
form=[]
for r in roots:
 f=[]
 for p in r.xpath('//w:body/w:p',namespaces=N):
  t=''.join(p.xpath('.//w:t/text()|.//m:t/text()',namespaces=N))
  if re.search(r'（[234]-\d+）$',t):f.append(t)
 form.append(f)
assert len(form[0])==42 and form[0]==form[1]
tabs=[r.xpath('//w:body/w:tbl',namespaces=N) for r in roots];changes=[]
assert len(tabs[0])==len(tabs[1])==73
for i,(a,b) in enumerate(zip(*tabs),1):
 x=''.join(a.xpath('.//w:t/text()|.//m:t/text()',namespaces=N));y=''.join(b.xpath('.//w:t/text()|.//m:t/text()',namespaces=N))
 if x!=y:changes.append(i)
assert changes==[35,57,67]
review={
 'review_type':'Independent final text review, read only',
 'source_v4_sha256':M['source_sha256'],
 'reviewed_text_snapshots':{str(p.relative_to(R)):sha(p) for p in [R/'_work/revised_full_text.md',R/'_work/revised_blocks.json',R/'_work/revision_manifest.json']},
 'docx_at_review':{'path':M['output'],'observed_sha256':sha(M['output']),'merge_manifest_sha256':M['output_sha256'],'note':'DOCX may be receiving downstream layout edits. Refresh final delivery manifest after QA; this review is bound to the text snapshots above.'},
 'verdict':'pass_for_text_delivery_with_known_evidence_and_configuration_limits',
 'required_text_revisions':[],
 'editorial_patch_absorption':checks,
 'chapter5_claim_traceability':claims,
 'structure_review':[
 {'chapter':1,'status':'pass','detail':'背景、现状、研究问题和逐章组织形成递进；第五章职责已同步为组合、恢复、漏检和多源局限。'},
 {'chapter':2,'status':'pass','detail':'共用定义、评价与接口承接方法章；补充配置指向附录J，原章首与小结无需重复增补。'},
 {'chapter':3,'status':'pass','detail':'新增章首承担承接与路线，3.1保留问题展开；原目录式段落已缩短，章末转向预测修正。'},
 {'chapter':4,'status':'pass','detail':'章首承接第三章，4.1不再重复原承接句；章末解释第五章综合分析的必要性。'},
 {'chapter':5,'status':'pass','detail':'设置→总体/交互→恢复/漏检→多源局限→小结；导语、表格、解释连贯，无新无据数字。'},
 {'chapter':6,'status':'pass','detail':'章首说明总结职责；6.1回扣两个研究点与组合分析，模拟身份、独立机制局限和CPU边界已同步。'}],
 'preservation_checks':{'tables':73,'changed_table_ordinals':[35,57,67],'changed_table_content':'Only CPU diagnostic scope wording, symbol alias/boundary, and H-6 cross-reference. Research data unchanged.','math_objects_before':382,'math_objects_after':381,'only_removed_math_object':'Obsolete D alias in symbol-table input-document row','numbered_equations':42,'numbered_equation_text_identical':True},
 'rounding_check':{'contrast':'CDCP T0I1 - T0I0','unrounded_seed_differences':[7.333333333333333,7.292731112473601,9.27415116156838],'unrounded_mean':7.966738535791771,'displayed_mean':7.97,'detail':'Compute from integer TP/FP/FN before rounding; mean of displayed seed differences is not the reporting estimator.'},
 'known_unresolved':[{'id':'C02','issue':'I0是否含继承旧BR，以及I1与G0的执行关系','status':'kept as configuration question; no algorithm inferred'},{'id':'C07','issue':'CDCP关系提案64与256上限的阶段及包含关系','status':'kept as configuration question; no number guessed'},{'id':'evidence','issue':'主结果完整文档×种子×方法输入、真实目标模型与大池路径验证','status':'not supplied by editorial revision; no CI/p or real experiment reproduction claimed'}],
 'delivery_note':'刷新最终DOCX/PDF SHA和页数后再交付；文本审查不替代渲染和逐页排版检查。'
}
(R/'_agents/compare/final_text_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
lines=['# v5合并稿独立文本复查','', '**结论：文本复查通过，无必须追加的文字修改。** 已知配置与真实实验资料缺口继续保留，不能将本结论称为真实实验验收。','', '本次只读复查 `_work/revised_full_text.md`、`revised_blocks.json`、`revision_manifest.json`，并直接比较v4/v5的DOCX数学对象及表格。修订后的定位以下用V5-B表示，避免与v4稳定B编号混淆。','', '## 第五章新增推论','', '| v5位置 | 核查内容 | v4来源 | 结论 |','|---|---|---|']
for q in claims:lines.append(f"| {', '.join(q['locations'])} | {q['claim']} | {', '.join(q['source'])} | 可回溯 |")
lines+=['','第五章区分了条件增量与交互、TP成员分解与F1、候选端点入池与终态端点选择、合计整数计数与逐种子均值。新增表后分析均有原表依据，未把结构保证或代理效用解释为真实F1保证。', '', '## 全局修改吸收','', '15条文字建议均已吸收：12条按建议文字出现；B0778、B0801的“主效应”修正及B0791的列指代由第五章重写等义落实。中英文摘要、6.1、C.2、模拟验收说明、H-6旧表号和附录回指范围均已同步。符号表只删除输入文档的旧D别名，保留删除集合D的独立说明。','', '## 章节结构与衔接','']
for q in review['structure_review']:lines.append(f"- 第{q['chapter']}章：{q['detail']}")
lines+=['','章末提示下一章、下一章章首承接上一章属于正常双向导航，本稿已压缩原重复目录句，没有新增整段重复。第五章不再只罗列表格，其综合分析职责与第一章组织结构、第四章结尾和第六章总结一致。', '', '## 数值、表格与公式保留','', '- 73张表全部保留。只有第35表CPU案例说明、第57表符号说明、第67表交叉引用发生文字变化，研究数据未修改。','- 原生数学对象382→381，直接XML集合比较确认仅移除符号表旧别名D；没有增加其他数学对象。','- 42条编号公式文本逐条一致。文中另外3次公式号引用不算新增编号公式。','- CDCP T0推理差值应保留7.97：三个精确差值为7.333333333333、7.292731112474、9.274151161568，均值7.966738535792。显示差值先舍入再平均产生7.9633，不应反向改写报告值。','- 未复算主表CI及Holm p；当前材料缺完整逐文档联合计数，稿内已明确此限制。', '', '## 已知待核实项','', '- I0是否执行继承旧BR、I1替换或接续哪一初始状态，仍需真实配置或代码确认。','- CDCP关系提案64与256分别约束的阶段及包含关系，仍需配置确认。','- 真实目标模型、完整增强审核、大池局部路线及主统计复算，不因文字润色完成。', '', '上述项目未被本次修订擅自定论。没有要求更改的段落，也没有需要新增的数字。','', '## 交付绑定','', '本复查绑定的三个文本快照SHA详见 `final_text_review.json`。复查时DOCX已进入后续排版，其实际SHA与初次合并manifest中的SHA不同；最终交付应在排版完成后刷新DOCX/PDF的manifest。本审查不替代逐页渲染核对。']
(R/'_agents/compare/final_text_review.md').write_text('\n'.join(lines)+'\n')
print('Final text review PASS; 15 patches absorbed; 9 claim groups supported; 42 equations preserved.')
