"""Create the version-bound implementation report after all QA gates pass."""
from pathlib import Path
import json,hashlib,re
W=Path(__file__).resolve().parent;R=W.parent
read=lambda n:json.loads((W/n).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=read('final_audit.json');v=read('visual_review.json');n=read('numerical_audit.json');c=read('review_coverage.json')
source=R/'report_1010_v1_full.md';docx=R/'report_1010_v1_full.docx'
assert a['mechanical_checks']=='PASS' and v['all_pages_reviewed']
assert n['passed'] and c['passed']
assert all(z['source_sha256']==sha(source) for z in [a,n,c])
assert a['docx_sha256']==sha(docx)
assert v['pdf_sha256']==a['pdf_sha256'] and v['pages']==a['pages']
report=R/'1010_v1全局评审逐项落实与核验说明.md'
lines=[
'# 1010-v1 全局评审逐项落实与核验说明',
'',
'修订依据：[1009-v4全局评审与完整修改建议](%s)。本轮按作者确认的方案完成定位、结构、文字与分析方式的修改，并扩大外部研究检索。两项研究、六章框架、原生任务、前期成果归属及历史附录继续保留。'%(R/'1009_v4全局评审与完整修改建议.md'),
'',
'本轮覆盖8项主意见、39个具体检查点。可直接完成的写作修改已落实；需要原始增强文本、完整预测、模型或求解器运行才能完成的证据项，已写成明确的诊断／比较协议，未填造成已有实证发现。此版本继续为模拟数据演示稿。',
'',
'## 一、交付与版本',
'',
f'- [Word正文]({docx})',
f'- [Markdown正文]({source})',
'- 本文与上述正文绑定，原1009-v4文件和7个原始情景数据／生成记录保持不变。',
'',
'## 二、八项主意见的实际落实',
'',
'|意见|本版实际修改|仍需取得的真实证据|',
'|:---|:---|:---|',
'|1. 动机缺少问题数量级|第一章增加诊断路径；第三、四章入口各加小表；H.1固定抽样、文档／变体／因素分母及错误归类|基线改写及OOF预测的真实分布；当前小表明确为诊断方案|',
'|2. 第一贡献过度突出结论中心|第三章改为“关系影响域约束的增强与成对学习”；摘要、关键词、贡献与总结同步；T-B采用同基础损失；主成绩标匹配训练规模|真实同数据比较及中心对照；保留中心区间跨0的现有负结果|',
'|3. 低漂移可能只是少改|增加非复制比例与可改写槽位编辑距离；生成池／接受池分开；检查选择偏向；保留因素级审计范围|原始增强文本及清单；不虚构距离或变体级精确率|',
'|4. 为何不用同评分全局ILP|RQ2和第四章将等求解预算全局作为关键竞争方案；另定义等端到端轨；补状态、gap、预算点、图规模及成本；复算取舍并收紧优势|真实全链路时延、失败率、求解证书及可复核事务|',
'|5. 4096未约束裁剪前成本|4.2.5补组合规模、评分对象与预检；失败保留分母；表5-5改为1／2／3／超过3并报告金标数|裁剪前规模及资源；长超边保护和新建分别取证|',
'|6. 外部研究位置|考虑13组方法／输入条件；新增3条文献；G列代码入口、缺口和评价协议；优先Kawarada与UniASA|至少一个原生评价可比的外部系统复跑；未将原论文成绩并入模拟主表|',
'|7. 第五章独立分析不足|按五个问题重写；给出对象集合；区分初始错误、候选和评分；新增在线配置选择；风险图移第四章，去重复成绩|共同／独有修复对象、候选变化及真实失败案例|',
'|8. 正文信息层级|细则和证明集中到A.6／B.6；结论移除调度细节；摘要、实验与表图增加轻量模拟身份；更新索引|真实证据齐备后整体更新主发现|',
'',
'## 三、新增分析及其边界',
'',
'以下由未改动的人工情景复算，没有新增模型运行：',
'',
'- 同基础损失的完整增强相对QOS式，关系F1增加1.79／1.83个百分点；T1全部增益不再归给数据构造。',
'- BR-J相对等求解预算全局平均总时间仅少4.19%／4.73%；自身求解只占总时间5.00%／5.67%。局部求解较快不足以推出明显端到端优势。',
'- 全局对照关系F1按未舍入结果分别高0.40／0.50个百分点，初始TP保留率亦略高。CDCP显示值62.47−61.96为0.51，正文新差值采用原始值相减再舍入。',
'- 训练投入已完成且只比较关系F1和在线平均时间时，T1＋I0高于且快于T0＋I1：AAEC高0.70个百分点、少13.00秒；CDCP高0.90个百分点、少21.16秒。此结论不外推到无法重训或无法摊销投入的场景。',
'- CDCP人工金标中1／2／3成员关系数为556／252／121，超过3为0；这不代表真实CDCP的源成员分布，不能证明长超边能力。',
'',
'四格交集、表达变化和真实求解状态仍缺记录。本稿分别给出集合定义、指标算法和字段，没有用更多聚合计数代替对象证据。',
'',
'## 四、外部研究检索与选择',
'',
'检索截至2026年10月10日，依据论文原文、ACL Anthology、arXiv作者版本及论文所指向仓库。本轮没有安装或复跑外部模型，也没有对全部49条文献重新进行穷尽审查。',
'',
'|方法／类别|主来源与入口|采用方式|',
'|:---|:---|:---|',
'|结构SVM／RNN|[ACL 2017](https://aclanthology.org/P17-1091/)|结构化历史参照，核对CDCP转换|',
'|MT-AM|[TACL 2022](https://aclanthology.org/2022.tacl-1.37/)|辅助语料与多任务条件参照|',
'|GMAM（新增[47]）|[EMNLP 2022](https://aclanthology.org/2022.emnlp-main.713/)；[仓库](https://github.com/HITSZ-HLT/GMAM)|结构生成补充候选|',
'|Kawarada等|[EACL 2024](https://aclanthology.org/2024.eacl-long.121/)；[仓库](https://github.com/masayouk/am-as-text2text)|优先系统对照；README明确CDCP转换器不在仓库，不能宣称已跑通原配置|',
'|DENIM|[ACL Findings 2024](https://aclanthology.org/2024.findings-acl.689/)；[论文所载仓库](https://github.com/syiswell/DENIM)|结构生成补充；仓库内容本轮未成功读取|',
'|UniASA（新增[48]）|[CL 2025](https://aclanthology.org/2025.cl-3.2/)；[仓库](https://github.com/HITSZ-HLT/UniASA)|优先系统对照；已核对处理和训练入口，仍需原生任务审计|',
'|AASP|[作者版本](https://arxiv.org/abs/2510.16363)|动作机制参照，不声称代码复现|',
'|ARGUS|原参考文献[10]的AAAI 2026方法|系统接口参照，区分分割和求解目标|',
'|AMELIA|[仓库](https://github.com/brunoyun/amelia)|分类任务与多数据集输入边界|',
'|QOS／DOS|[EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1351/)；[仓库](https://github.com/YuqiHuang2003/QOS_DOS)|增强近邻，新增适配差异表|',
'|对抗强化学习合成（新增[49]）|[2026-10-06作者版本](https://arxiv.org/abs/2610.07699v1)；[论文所载仓库](https://github.com/ZhangZJ-GH/Synthetic-Data-for-Argument-Mining)|近期近邻；区分联合合成与原监督保持，仓库内容本轮未成功读取|',
'|FOL-AM|原参考文献[14]|给定组件的关系推理参照|',
'|Cabessa等|原参考文献[8]|给定组件列表的生成分类参照|',
'',
'附录G规定先审计Kawarada与UniASA的表示并固定版本；可无损导出原生对象的进入共同评价，无法适配完整超边的另列兼容任务。保持原生主任务，不为比较改变金标。',
'',
'## 五、39项具体落实位置',
'',
'“落实”表示相应写作修改已进入正文；运行事项以状态栏保留完成条件。',
'',
'|编号|事项|正文定位|落实状态|',
'|:---|:---|:---|:---|'
]
for item in c['items']:
    lines.append(f"|{item['id']}|{item['topic']}|[{item['locations']}]({source}:{item['line']})|{item['status']}|")
lines += [
'',
'## 六、保留项与章节同步',
'',
'两项研究、六章框架、严格原生评价、同数据消融、强全局对照和不利结果均保留。32个陈列公式的内容与次序保持不变，附录E全文保持不变。正文移出的定义与证明可沿引用查回。',
'',
'摘要及关键词、第一章问题与贡献、第二章预算口径、第三章标题及轨道、第四章全局竞争关系、第五章五个问题、第六章总结与后续顺序，以及附录和索引已同步。原版留存。',
'',
'## 七、核验结果与证据身份',
'',
f"- Word共{a['pages']}页，全部页面已查看或通过与已查看页面逐字节一致的整页图像确认；{a['verified_page_labels']}个标题／题注定位核对通过。",
f"- {a['numbered_tables']}张表、{a['figures']}幅图、{a['algorithms']}个算法、{a['native_display_equations']}个陈列公式、{a['native_math_objects']}个原生数学对象、{a['references']}条参考文献；长表、页码、引用和图片嵌入已核验。",
f"- 独立复算{n['count_rows']:,}行人工计数、{n['metric_cells']}个均值／标准差单元及{n['paired_and_interaction_intervals']}组配对／交互区间，另核对概率和人工判断；新派生数值及分组检查通过。",
'- 上述检查验证文本、算术与版式，不证明真实研究效果；本轮真实模型与语料实验次数为0。',
'',
f"[逐项覆盖记录]({W/'review_coverage.json'}) · [正文差异]({W/'source.diff'}) · [数值复算]({W/'numerical_audit.json'}) · [排版核验]({W/'final_audit.json'})",
'',
'## 八、版本校验值',
'',
f"- Markdown SHA-256：{sha(source)}",
f"- Word SHA-256：{sha(docx)}",
f"- 保留的1009-v4 Word SHA-256：{sha(R/'report_1009_v4_full.docx')}",
f"- 保留的1009-v4 Markdown SHA-256：{sha(R/'report_1009_v4_full.md')}",
'',
'本轮完成已确认范围内的文稿修订与核验。后续真实证据按附录H从问题诊断和全流程强对照开始，依据结果判断方法复杂度与适用范围，再整体更新主发现。'
]
report.write_text('\n'.join(lines)+'\n')
local_links=re.findall(r'\]\((/[^)]+)\)',report.read_text())
for target in local_links:assert Path(re.sub(r':\d+$','',target)).exists(),target
support=['artifact.md','template-evidence.json','reference_config.json','review_coverage.json','numerical_audit.json','final_audit.json','visual_review.json','derived_global_analysis.json','source.diff','edits.json','prepare.py','revise.py','compose.py','audit_revision.py','audit_scenario.py','build_docx.py','render_document.py','cache_pages.py','generate_figures.py','deliver.py','generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
files=[source,docx,report]+[W/name for name in support]+list((W/'figures').glob('*.png'))
manifest={'edition':'1010-v1','evidence_type':'SIMULATION_WRITING_REVISION','genuine_model_runs':0,'pages':a['pages'],'covered_items':39,'files':{str(p.relative_to(R)):sha(p) for p in files}}
(W/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('delivered',report,'manifest files',len(files),'verified report local links',len(local_links))
