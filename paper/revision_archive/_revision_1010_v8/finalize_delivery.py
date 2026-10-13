"""Package a completed, visually reviewed v8 without altering the manuscript."""
from pathlib import Path
import hashlib
import json
import zipfile

W=Path(__file__).resolve().parent
R=W.parent
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,d:Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
audit=read(W/'final_audit.json')
assert audit['mechanical_checks']=='PASS'
review=read(W/'reviewed_pages.json')
assert sorted(set(review))==list(range(1,audit['pages']+1))
pdf=W/'render_final/report_1010_v8_full.pdf'
assert sha(pdf)==audit['pdf_sha256']
assert sha(R/'report_1010_v8_full.md')==audit['source_sha256']
assert sha(R/'report_1010_v8_full.docx')==audit['docx_sha256']
visual={'status':'PASS','pdf_sha256':sha(pdf),'review_method':'Inspected all 117 final rendered pages in labelled contact sheets for layout; enlarged final page pairs for abstracts, revised body text, reproduction entry and all six new diagnostic tables',
        'detailed_pages':[3,4,45,46,73,74,75,76,83,84,91,92,93,94,95,96],
        'pages':[{'page':i,'sha256':sha(W/'render_final'/f'page-{i}.png'),'reviewed':True} for i in sorted(set(review))]}
write(W/'visual_review.json',visual)
audit['visual_review']='PASS';write(W/'final_audit.json',audit)
build=read(W/'docx_build.json');build['rendered']=True;write(W/'docx_build.json',build)

note=R/'1010_v8数据补充说明与待完成事项.md'
note.write_text(f'''# 1010-v8 数据补充说明与待完成事项

完成日期：2026年10月11日。基于1010-v7估算演示版补充既存CPU诊断统计，保留原版；真实案例由作者后续完成。本次没有新增模型训练、目标LLM调用或ILP求解。

## 本次已补充

复核AAEC 66篇与CDCP 116篇审计文档，共182篇；按原文哈希分别为64和116组。原始语料、划分、文本身份及程序记录已核对，38928条编辑提议的TP、FP、FN与逐文档F1均已复算。新增统计集中在附录D.3，正文第4.1、5.2、6.2节及A.5同步了引用和解释范围。

| 表号 | 补充内容 | 数据来源与解释范围 |
|---|---|---|
| D-1 | 初始组件的严格命中、类型和边界错配、未匹配对象 | 已保存CPU预测与原始金标；描述性配对不改变严格评价 |
| D-2 | 0、64、128、256、512补充跨度预算下的覆盖及规模 | 按既存候选排序重算；组合数不是实测评分数或耗时 |
| D-3 | 已入池遗漏跨度的一步动作限制 | 核对旧组件重叠与实际保存的提议；不等于最终恢复 |
| D-4 | 插入、删除、换类型、换跨度提议的F1升／平／降 | 逐文档效果组成；提议条数不作为独立样本量 |
| D-5 | 主策略与同阈值禁删除对照的严格组件结果 | 精确重放既存选择；另做全文哈希组配对重采样 |
| D-6 | 新增正确、损失正确、新增错误、移除错误对象 | 完整跨度与类型键的前后集合比较；仅限CPU组件诊断 |

## 可报告的有限观察

- 初始全部端点跨度及类型正确的原生关系，AAEC为43／627，CDCP为4／200。这描述的是本次弱模型，不能代表目标LLM。
- 128补充池中已覆盖的遗漏跨度，AAEC有268／526、CDCP有530／586与至少两个旧组件冲突，未进入原诊断的一步加入动作。入池并不保证当前动作能够恢复。
- 主策略分别接受66和115次删除，组件TP没有增加；对应F1增量约为0.64和0.17个百分点。
- AAEC禁删除对照净增3个正确组件、净减3个错误组件，但实际新增30个错误对象并移除33个错误对象。净成绩改善可以伴随错误对象之间的替换。

新增95%区间使用种子10108、2000次全文哈希组配对重采样，先汇总计数再算micro-F1。它是单次已保存模型结果的事后文档组区间，不包含重新训练的随机性，也不构成多重比较校正后的确认性结论。

## 四项缺口当前状态

| 缺口 | 本次增加的证据 | 仍待完成 |
|---|---|---|
| 方法必要性 | 真实弱模型的错误、端点、候选及动作限制统计 | 真实改写监督漂移审阅；目标LLM的自然错误与完整关系恢复空间 |
| 可执行性 | 补充来源、运行身份与复算校验；整理既有验收记录 | 实际模型配置绑定、真实梯度路径、求解器及失败提交回退贯通 |
| 贡献证据 | 既存CPU策略对照的精确重放与组件对象变化 | 新方法关键受控比较、外部系统对照、局部与全局的真实采用条件 |
| 综合认识 | 弱模型对象变化揭示净计数隐藏的错误替换 | 目标模型同批四格对象分析；真实同文档成功与失败案例由作者后续完成 |

正文主结果仍保留估算演示身份和原数值。六张新表明确标注“既存CPU诊断”，没有将它们移作新增训练方法、BR-J或全局ILP的成绩。四项缺口均未被标记为实证全部关闭。

## 文件与复算材料

- [修订后Word](/Users/channtang/Downloads/paper/report_1010_v8_full.docx)
- [同步Markdown](/Users/channtang/Downloads/paper/report_1010_v8_full.md)
- [诊断统计与复算材料](/Users/channtang/Downloads/paper/1010_v8诊断统计与复算材料.zip)

材料包包含六份CSV、完整统计JSON、复算脚本、输入文件哈希及执行证据清单。原始语料和原运行记录仍保存在本工作区research_0920中；材料包不重复打包这些输入。执行证据清单如实保留目标实现的未绑定字段和未执行验收项，不能据此声称生产链路已完成。

## 版本与质量检查

Word共{audit['pages']}页，新增6张统计表；原47张编号表、11张图、411个原生数学对象、32个陈列公式、3段算法及49条参考文献均保留。已核对{audit['toc_entries']}个目录条目与最终渲染页码，完成全部页面的版面总览检查，并放大检查修订文字和新增表格。v7及既存诊断源文件哈希保持不变，原案例段落和H.4采集方案未改写。

| 文件 | SHA-256 |
|---|---|
| report_1010_v8_full.docx | `{audit['docx_sha256']}` |
| report_1010_v8_full.md | `{audit['source_sha256']}` |

本次验证属于既存材料复算和文档质量检查，未进行独立重训复现。
''')

readme='''# 1010-v8 诊断统计与复算材料

本包对应论文附录D.3的六张新增统计表。数据身份：既存2026-09-20 CPU诊断的事后重分析；不是目标LLM实验，也不是BR-J、全局ILP或训练增强效果。

六份CSV分别提供逐文档错误、端点分组、预算覆盖、提议组成、策略结果及对象变化。diagnostic_supplement.json提供输入文件哈希、重采样口径、完整汇总和校验结果。没有新增真实案例叙述。

在原paper工作区保留research_0920/data、research_0920/results及原诊断脚本和协议，解压本包后，使用具有NumPy的Python运行：

    python3 _revision_1010_v8/analyze_saved_diagnostics.py

脚本只提取并执行原模块的纯数据读取及计数函数，不导入训练模块，不拟合模型，不调用外部服务，不执行求解器。输出写入_revision_1010_v8，既存输入保持只读。原语料和既存运行记录未重复打包；缺少输入时不能独立复算。

execution_evidence_inventory.json列出已有有限检查及尚未执行的目标系统验收；输入名称对应先前方案，不代表字段已完成绑定。final_audit.json和visual_review.json仅记录文档与复算交付检查，不是研究有效性证明。
'''
(W/'README.md').write_text(readme)
files=[W/'README.md',W/'analyze_saved_diagnostics.py',W/'diagnostic_supplement.json',W/'execution_evidence_inventory.json',W/'final_audit.json',W/'visual_review.json']+sorted(W.glob('diagnostic_*.csv'))
bundle=R/'1010_v8诊断统计与复算材料.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,str(p.relative_to(R)))
with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
outputs=[R/'report_1010_v8_full.docx',R/'report_1010_v8_full.md',note,bundle]
manifest={'status':'COMPLETE_WITH_EXISTING_CPU_DIAGNOSTIC_SUPPLEMENT',
          'deliverables':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in outputs},
          'new_observed_diagnostic_tables':6,'new_training_runs':0,'new_solver_runs':0,
          'real_case_narratives':'deferred by user','mechanical_audit':'PASS','visual_pages':audit['pages']}
write(W/'delivery_manifest.json',manifest)
print(json.dumps(manifest,ensure_ascii=False,indent=2))
