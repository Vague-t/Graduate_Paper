# 1010 v4 模拟记录复算包

全部新增记录的身份为SIM-1010-V4。没有真实语料模型输出、训练、人工语义标注或优化器执行。Kawarada_proxy、UniASA_proxy是人工参数生成的外部路线占位，不能归为作者成绩。关系对象键是与旧计数相容的一种补全，不是真实文档坐标。

## 复算记录

解压后保留目录结构，使用Python 3及numpy，在解压目录执行：

```bash
python _revision_1010_v4/generate_supplement.py
python _revision_1010_v4/audit_supplement.py --portable
python _revision_1010_v4/audit_scenario.py
```

生成程序会覆盖包内的新增模拟记录和汇总；原件已在本包保留，可另解压一份用于比较。supplement_manifest.json登记生成器与9份结果文件的SHA-256。脚本仅需本包内数据，不访问网络或外部系统。

portable模式跳过对本地上一版资产目录的逐字节比较，但继续核对记录、统计、四格对象、表格、公式和两版Markdown。完整工作区审计的旧文件及11图保留结果见supplement_audit.json；portable模式输出独立的portable_audit.json，不伪称检查了缺失资产。

## 绘图

新增图的PNG、SVG、PDF与draw_budget.py均在_revision_1010_v4中。安装requirements.txt中的绘图库后，可执行绘图程序；中文字体默认使用macOS的Arial Unicode字体路径，其他系统需修改addfont路径与相应字体族。七张机制图和四张既有结果图未重复打包，继续使用上一版图源包及工作区资产。

## 文件说明

- augmentation_text_pairs.json、augmentation_screening.csv：80个模板源文档、320个共同候选、960个筛选决定。
- resource_envelope.csv、budget_outcomes.csv：228文档的规模和成本函数，以及8,208条预算、方法、种子、对象记录。状态来自设定，没有求解证书。
- external_placeholders.csv：2,736条外部占位计数。
- object_memberships.json、object_transitions.csv、synthetic_object_cases.json：684组四格关系对象集合、集合变化和3个模拟例子。
- supplement_results.json：全部规模组、预算点、汇总与配对区间。
- document_counts.csv等7份旧情景文件：原有人工成绩的可复算输入；未重新定义其来源。
- 两版Markdown用于表号、表值和公式身份审计；本包不重复全部论文图片资产。

本包的可复现性表示同一生成假设可重建相同记录，不能证明真实方法有效。正式研究须整体替换模拟结果、模型输出、成本、案例和结论。
