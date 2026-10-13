from pathlib import Path
from collections import Counter
import hashlib,json,shutil

O=Path(__file__).resolve().parents[1]
R=Path('/Users/channtang/Downloads/paper')
V=json.loads((O/'_work/verification.json').read_text())
M=json.loads((O/'_work/revision_manifest.json').read_text())
P=json.loads((O/'_work/patches.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=R/'论文规范排版稿_v12.docx'
assert sha(source)==V['source_sha256']
assert sha(O/'论文规范排版稿_v13.docx')==V['docx_sha256']
assert sha(O/'论文规范排版稿_v13.pdf')==V['pdf_sha256']
assert len(P)==46
assert Counter('abstract' if int(p['block_id'][1:])<100 else 'intro' for p in P)=={'abstract':6,'intro':40}
qa=[('qa_pages_1_18.md',1,18),('qa_pages_19_49.md',19,49),('qa_pages_50_89.md',50,89),('qa_pages_90_127.md',90,127)]
covered=[]
for name,start,end in qa:
    t=(O/'_work'/name).read_text()
    assert len(t)>100
    covered.extend(range(start,end+1))
assert covered==list(range(1,128))
V['visual_qa_reports']=[{'report':str(O/'_work'/n),'physical_page_start':s,'physical_page_end':e} for n,s,e in qa]
V['remaining_visual_check_pages']=[]
V['visual_qa_passed']=True
V['visual_qa_covered_pages']=covered
V['result']='passed'
(O/'_work/verification.json').write_text(json.dumps(V,ensure_ascii=False,indent=2))

report='''# v12 → v13：摘要与绪论润色说明

日期：2026年10月13日

本轮依据你指定的 [chinese-thesis-polish skill](/Users/channtang/Downloads/paper/writing_style_research_20261013/skill/chinese-thesis-polish/SKILL.md)，以《论文规范排版稿_v12.docx》为原稿，完成中英文摘要和第一章的语言与局部组织调整，另存为 v13。v12 原文件保留。

## 1. 修改范围

共修改 46 段：中文摘要 3 段、英文摘要 3 段、绪论 40 段。第一章的标题层级、图表与段落顺序保留。1.4 节已阅读，原有章节安排说明清楚，本轮未改写。第二章至第六章、参考文献和附录正文保持原样。

| 位置 | 本轮主要调整 | 希望改善的阅读体验 |
| --- | --- | --- |
| 中英文摘要 | 按任务困难、两阶段方法、结果与适用条件展开；说明 I0、T1 所指；对齐中英文的比较对象和统计结论。 | 读者能直接识别解决什么问题、怎样处理、得到什么结果。 |
| 1.1 研究背景与意义（8 段） | 从实际论辩文本进入任务；用图1-1的组件依赖例子连接训练标注保持和预测图修正；压缩重复背景及泛泛的意义表述。 | 背景、技术困难与研究动机连续推进。 |
| 1.2 国内外研究现状（21 段） | 围绕端到端建模、数据构造和预测修正组织段内比较；明确方法之间的输入、监督与评价差异；将文献介绍接回本文的具体问题。 | 读者能够理解引用文献与本文工作的关系，而不只是读到方法列表。 |
| 1.3 研究问题与主要研究工作（11 段） | 理顺两阶段分工、研究问题、实现操作和实验对照之间的关系；把抽象的贡献说明展开为具体对象和动作；集中说明系统效果与机制作用的区别。 | 读者能对应研究问题、方法设计和检验方式，减少反复寻找解释。 |

## 2. 主要语言变化

**把抽象概括展开为明确操作。** 例如，摘要中的“两个阶段的依赖维护”改为训练阶段的“监督保持”和推理阶段的“关系重建”；在方法概述中说明哪些因素参与学习、哪些关系随组件变化重新处理。

**拆开同时承载多个条件的长句。** 对象修改、事务接受条件和记录用途分别表达。必要的固定候选、冻结评分、预算限制仍保留，不因拆句而丢失条件。

**让衔接落在具体问题上。** 背景由例子引出组件与关系的依赖，相关工作由已有做法引出待处理的问题，研究内容再说明相应设计与比较。减少仅靠连接词或重复贡献说明完成的衔接。

**保留结论强度与比较范围。** AAEC训练增量未达到统计显著性、共享增强下的跨骨干验证范围，以及完整配置改善不等于每个机制都有独立优势，均按原稿保留。中英文摘要的数值和限定一致。

## 3. 代表性前后对照

以下是实际修改句段的节选，完整改写已进入 v13。

### 摘要：说清两项工作的对象

原文：

> 本文在多候选重排序与有界修正的基础上，研究训练与推理两个阶段的依赖维护。

改后：

> 本文以多候选重排序与有界修正（MCR-BR）为基础，分别研究训练阶段的监督保持与推理阶段的关系重建。

变化：保留继承关系，将概括性的“依赖维护”落到两阶段各自处理的问题。

### 摘要：先交代评价条件，再报告结果

原文：

> 在AAEC和CDCP官方测试划分及自由预测数量协议下，Qwen3.5-9B完整配置的严格关系F1分别为71.63和50.77，相对同骨干ICIC/MCR-BR基线提高5.94和8.98个百分点。

改后：

> 实验在AAEC和CDCP官方测试划分上开展，评价时允许模型自由预测对象数量。Qwen3.5-9B完整配置的严格关系F1分别为71.63和50.77，比同骨干ICIC/MCR-BR基线提高5.94和8.98个百分点。

变化：将密集的前置条件拆为独立句，保留全部数值、基线和评价范围。

### 1.1 节：压缩重复概括

原文：

> 因此，如何在控制修改范围和计算成本的同时，协调处理组件与关联关系，是提升论辩结构预测可靠性需要面对的问题。

改后：

> 因此，组件与关联关系需要协调修改，同时控制修改范围和计算成本。

变化：前文已经解释困难及其例子，结尾直接回收具体问题，减少套叠表述。

### 1.2 节：分开接受条件与记录用途

原文：

> 在固定候选和对象评分下，事务须满足依赖闭合、分项接受条件及预算限制，并按规定字段保留修改记录。这样，组件与关系的变化能够共同评价、共同接受并供回放核对。

改后：

> 在固定候选与对象评分下，事务须满足依赖闭合、分项接受条件和预算限制，使组件与关系的变化得到共同评价和接受。修改过程按规定字段记录，以便回放核对。

变化：接受条件对应修改决策，记录字段对应回放用途，使修饰关系更明确。

## 4. 文件与排版核对

对照原稿，46 段中的数字和引文编号序列保持一致；380 个原生公式对象、83 张表及全部图像资源保持一致。第二章及以后的 Word 正文结构逐项对照未变。

最终 PDF 为 127 页，149 条目录页码均与正文一致，字体已嵌入。全篇页面已分段逐页复核；摘要完整容纳于各自一页，绪论的图表、题注和分页正常，未发现新增缺字、内容裁切或公式显示错误。

本次完成的是摘要与绪论的润色，后续章节仍保留 v12 的内容与表述。

## 5. 交付文件

- [v13 Word](/Users/channtang/Downloads/paper/论文规范排版稿_v13.docx)
- [v13 PDF](/Users/channtang/Downloads/paper/论文规范排版稿_v13.pdf)
- 原稿：[v12 Word](/Users/channtang/Downloads/paper/论文规范排版稿_v12.docx)

版本校验值（SHA-256）：

| 文件 | 校验值 |
| --- | --- |
| v12 Word（原稿） | `__SOURCE_SHA__` |
| v13 Word | `__DOCX_SHA__` |
| v13 PDF | `__PDF_SHA__` |
'''
report=report.replace('__SOURCE_SHA__',V['source_sha256']).replace('__DOCX_SHA__',V['docx_sha256']).replace('__PDF_SHA__',V['pdf_sha256'])
name='论文规范排版稿_v12至v13_摘要与绪论润色说明.md'
(O/name).write_text(report)
for n in ['论文规范排版稿_v13.docx','论文规范排版稿_v13.pdf',name]:
    sourcefile=O/n;target=R/n
    if target.exists():assert target.read_bytes()==sourcefile.read_bytes(),f'Unexpected existing output: {target}'
    else:shutil.copy2(sourcefile,target)
    assert sha(sourcefile)==sha(target)
assert sha(source)==V['source_sha256']
print(json.dumps({'outputs':[str(R/n) for n in ['论文规范排版稿_v13.docx','论文规范排版稿_v13.pdf',name]],'source_preserved':True,'changed_paragraphs':46,'pages':127,'visual_qa':'passed','native_math_unchanged':380,'tables_unchanged':83},ensure_ascii=False,indent=2))
