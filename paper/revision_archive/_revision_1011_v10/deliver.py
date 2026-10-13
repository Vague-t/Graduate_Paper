"""Bind revision advice and evidence ZIP to the final verified manuscript."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,zipfile,shutil
W=Path(__file__).resolve().parent;R=W.parent;E=R/'research_1011_v10'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
audit=read(W/'final_audit.json');visual=read(W/'visual_review.json')
assert audit['mechanical_checks']=='PASS' and visual['all_pages_reviewed']
assert audit['pdf_sha256']==visual['pdf_sha256'] and audit['pages']==visual['pages']
word=R/'report_1011_v10_full.docx';md=R/'report_1011_v10_full.md';pdf=R/'report_1011_v10_full.pdf'
shutil.copyfile(W/'render_final_v2/report_1011_v10_full.pdf',pdf)
assert sha(word)==audit['docx_sha256'] and sha(md)==audit['source_sha256']
lines=md.read_text().splitlines();pages=read(W/'page_map.json')
def loc(label):
    n=next(i for i,s in enumerate(lines,1) if s.lstrip('# ').strip()==label)
    return f'[{label}]({md}:{n})（正文页{pages[label]}）'
report=R/'1011_v10修订说明与评审意见落实.md'
text=f'''# 1011 v10 修订说明与评审意见落实

日期：2026年10月11日。唯一文稿基线为1011-v9；旧Word/Markdown及原始实验输出未改动。交付v10的Markdown SHA256为`{sha(md)}`，Word为`{sha(word)}`。本文档绑定这一版本，不代表后续版本的评审结论。

## 已完成的四项工作

1. 核查并转换ArgUNSC（2025）和CasiMedicos-Arg（2024），各固定32篇开展Luna试验；另固定32篇未进入此前诊断的CDCP训练文档开展评分配对对照。共43项新的模型任务，输出与失败全部保留。
2. 将既有148篇探索性扩样与新96篇分协议整理，保留AAEC essay051/001的非标点恢复案例及CDCP 00846的新严格正例。新两套语料未提升、CDCP调整后总体仍低于MCR等负结果同步写入。
3. 小幅补充原生关系格式登记、CDCP类型/关系说明与显式评分，以及未知评分的事务拒绝规则。未改变两阶段框架、固定效用、依赖闭合、分项接受门或编辑预算；未增加第三项算法创新。
4. 按评审问题压缩重复措辞，同步中英文摘要、引言、第四章结果、小结、第五章对象讨论、总结及A/C/H。详细协议留在D.10—D.12，正文篇幅仅增加1236个Unicode字符（含Markdown，约1.9%，不等同于Word字数）。

## 重点阅读位置

- {loc('4.6.7 案例分析')}：三组真实结果、AAEC机制例子、CDCP评分对照和00846。
- {loc('4.4.1 固定文本证据评分器')}：区分低分与缺失，明确变化组件及闭合关系域的输入完整性。
- {loc('D.10 探索性扩样与对象诊断')}：148篇的停止规则、候选覆盖、类型混淆和历史重放差异。
- {loc('D.11 新增语料的来源与固定试验')}：原生定义、转换排除、发布版本差异和格式失败分母。
- {loc('D.12 CDCP原生评分接口的配对检查')}：同候选同初始图、组合干预、实测成本及重放。

## 评审问题逐项状态

沿用v6评审后的10项落实清单；本次新增语料和弱模型试验不能直接关闭全部Major问题。

|项|本版状态|已补证据与位置|仍需达到的完成条件|
|:---|:---|:---|:---|
|1 监督漂移及筛选必要性|未补齐|保留第3章与H.1—H.2既有计划|真实改写池、独立语义审阅、筛选前后漂移及覆盖代价|
|2 端点错误与恢复空间|部分补强|4.6.7、D.10—D.12提供真实端点恢复、类型错误、完整候选覆盖及误删|目标模型训练侧OOF诊断；不能用Luna弱模型频率替代|
|3 裁剪前候选成本|未补齐正式方案|本版记录轻量候选数量与修正阶段成本|完整候选生成、评分、裁剪准备的时间/内存/P95与失败范围|
|4 可执行配置|轻量试验已绑定，正式系统未绑定|预冻结协议、模型请求身份、代码/数据哈希及SciPy环境|正式训练/编码/评分模型和设备实际绑定并由入口验收|
|5 真实接口验收|推理局部通过|96篇原生金标复核、256条执行和重放、6项边界测试|训练梯度、完整增强链及未触发异常分支仍需正式验收|
|6 训练方法贡献|未补齐|未新增模拟或伪造训练成绩|T-B/T-E真实训练、配对输出与误差/成本|
|7 推理增量及局部/全局取舍|部分补强|同候选、初始图和预算的评分对照与RelationOnly|单对象、完整BR-J、同目标全局ILP及端到端预算比较|
|8 外部系统定位|未补齐|新增语料适配并非外部系统比较|至少一个经原生任务兼容核查的真实外部系统输出|
|9 第五章综合认识|未补齐训练四格|加入初选—恢复与对象更替的纯推理观察|同批T0I0/T1I0/T0I1/T1I1完整对象对齐及非重复的综合发现|
|10 最优补全措辞|沿用已修订状态|4.3.2保留“取得最优性证书时才称为最优”|当前措辞与可行incumbent、回退规约保持一致|

## 结论应怎样表述

可写：有限候选中补入缺失端点能够打开部分关系恢复空间；CDCP原生说明与显式评分的组合在固定输入上改善了相对原评分的结果。CDCP 00846的关系F1由0升至18.18，属于关系重建正例，RelationOnly也得到同一结果。

不应写：BRJ-lite已在四套语料普遍有效、显式评分已校准、集合动作已优于单对象、局部求解优于全局或两阶段互补已验证。新CDCP总体关系F1虽从原评分0提高到1.60，仍低于初始图3.33；ArgUNSC 1.08→0、CasiMedicos-Arg 0.83→0。新候选池缺失的原生类型和多源关系不能由评分补回。真实病例与模型输出也不升级为完整系统正式实验。

## 文档与实验核验

- 最终{audit['pages']}页；231项原生目录条目及234个标题/题注页码标签已与最终PDF核对。
- 全部页面已做视觉检查，最后一轮按页面主体像素比对复用已查页，再检查所有变化页；新增表格整表排布，第四章小结溢出已消除。无越页字符、断裂公式或新增表格裁切。
- 411个原生数学对象、32个陈列公式、3段算法、11张图保留；54张原表不变，替换2张旧案例表、新增7张，合计61张编号表；原49条参考文献保留，追加2条一手文献。
- 新96篇保留全部分母；256条执行计数经第二实现复算，金标从原发布文件独立核对，256条重放终态和接受序列一致。
- DOCX完整性、书签/超链接、未编辑包部件、v9哈希、所有冻结输入和输出哈希检查通过。文档QA通过不代表上述未完成的实证项目完成。

结果与方法分析见[实验报告]({R/'1011_v10新语料实验与方法调整报告.md'})，全部96篇见[逐例核验册]({E/'casebook.md'})。脚本、源数据、原始输出、失败、指标、审计与文稿放入[实验证据包]({R/'1011_v10新语料实验与修订证据包.zip'})。
'''
report.write_text(text)
files=[word,md,pdf,report,R/'1011_v10新语料实验与方法调整报告.md',R/'report_1011_v9_full.md',R/'report_1011_v9_full.docx',R/'1011_Luna扩样分析与正例核验记录.md',R/'1011_Luna扩样正例与反例核验.md',R/'research_1010_v7_luna/evaluate.py',R/'research_0920/data/cdcp_acl17.zip']
files += [p for p in E.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
files += [p for p in W.iterdir() if p.is_file() and p.suffix in ['.py','.json','.md','.conf']]
files += [R/'research_1011_luna_expansion_analysis'/n for n in ['combined_metrics.json','candidate_score_diagnostics.json','case_source_objects.json','integrity_audit.json','replay_all.json','replay_path_differences.json']]
files=sorted(set(files));assert all(p.exists() for p in files)
manifest={'revision':'1011-v10','created_at_utc':datetime.now(timezone.utc).isoformat(),'manuscript_sha256':sha(md),'docx_sha256':sha(word),'pdf_sha256':sha(pdf),'new_documents':96,'new_model_tasks':43,'run_records':256,'replay_records':256,'files':{str(p.relative_to(R)):sha(p) for p in files}}
manifest_path=R/'1011_v10交付清单.json';manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
verifier=R/'verify_1011_v10_bundle.py'
verifier.write_text('''from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
m=json.loads((root/'1011_v10交付清单.json').read_text())
for name,expected in m['files'].items():
    p=root/name
    assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
print('PASS:',len(m['files']),'files; no model calls and no writes')
''')
out=R/'1011_v10新语料实验与修订证据包.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[manifest_path,verifier]:z.write(p,str(p.relative_to(R)))
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for name,h in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==h,name
print(json.dumps({'word':str(word),'report':str(report),'zip':str(out),'zip_bytes':out.stat().st_size,'files':len(files),'pages':audit['pages']},ensure_ascii=False,indent=2))
