# 基于大语言模型的端到端论辩挖掘方法研究

武汉大学计算机科学与技术学术型硕士学位论文

0914修订工作稿　2026年9月14日

英文题目　End-to-End Argument Mining with Large Language Models

## 版本说明

本稿在report_0913.md基础上修订，重点统一研究主线与贡献表述，补充2025—2026年相关研究，并同步更新各章的方法定位和结果解释。原稿实验表格及数值予以保留，本次修订未重新训练模型或复现实验。文中“原稿记录”表示数值继承自原稿，不表示本轮已通过日志核验；“待核验”标记属于工作稿编辑说明，需用实际代码、数据和实验记录解决后方可删除。具体修改和新增文献的任务边界见随稿《0914修订说明》。

当前最重要的未决事项是第三章与第四章Single-Pass分数及Full配置的对应关系、Claim-specific Adapter的门控实现、修复操作的可执行定义，以及实验划分、重复次数和统计量来源。实验结果符合研究预期，不等于上述可追溯性问题已经解决。本稿不作为已满足送审要求的声明；正式封面、作者及导师信息、原创性声明、授权页、致谢和成果页应在定稿时按学院适用模板补齐，不在本次修订中代填或代签。

## 摘要

论辩挖掘旨在从非结构化文本中识别论辩组件及其关系，恢复符合语料标注规范的论辩图。生成式大语言模型能够统一表示组件跨度、类型和有向关系，但组件识别错误会限制后续关系预测的候选空间，单次生成也可能产生错误引用和缺乏语义依据的连接。针对上述问题，本文从训练阶段的结论组件增强和推理阶段的论辩图修正两个方面研究端到端论辩挖掘方法。

在训练阶段，本文设计面向结论类组件的局部论辩结构保持增强方法。以结论节点及其支撑或攻击邻域作为增强单位，在保留组件类型、关系端点与方向的条件下生成表达变体，并通过格式、结构和语义检查筛选样本。结合类型条件低秩适配、线索感知连续提示和句子级辅助目标，该方法旨在丰富结论表达及其关系上下文，为组件和关系预测提供结构一致的训练监督。增强目标是提高有效样本的多样性，不将样本扩充直接等同于类别平衡改善。

在推理阶段，本文提出基于完整候选图评估与异常驱动局部修正的方法MCR-BR。该方法从多个组件假设构建候选论辩图，利用论证连接覆盖、边语义连贯性和输出合法性进行图级评分；随后针对检测到的异常尝试局部修改，通过接受检查与回退机制控制修改过程，并限制修正轮数和每轮接受动作数。该设计将候选选择与生成后的局部调整衔接起来，目标是改善端到端抽取结果，而非以代理评分代替任务正确性判断。

现有实验记录中，完整框架在AAEC上的Component-F1和Relation-F1分别为83.71和64.83，在CDCP上分别为76.45和38.17。在采用粗粒度组件标签及有向无标签连接的AAEC到CDCP零样本迁移设置下，完整框架的Link-F1为43.21，较同骨干Single-Pass记录提高9.79个F1点。上述记录呈现了训练增强与推理修正相结合的应用价值；两项方法的独立增益、等计算预算优势及更广泛的迁移能力，仍需在配置核验和相应消融基础上分别确定。

关键词：论辩挖掘；大语言模型；局部结构保持增强；结论组件；候选图评估；异常驱动修正

## Abstract

Argument mining reconstructs components and relations from unstructured text under corpus-specific annotation guidelines. Generative large language models can represent component spans, types, and directed relations jointly. However, component errors restrict relation prediction, while a single generation may contain invalid references or unsupported links. This thesis studies complementary training-time conclusion enhancement and inference-time graph repair for end-to-end argument mining.

For training-time enhancement, this thesis designs local structure-preserving augmentation centered on conclusion components and their supporting or attacking neighborhoods. Expression variants preserve component types, relation endpoints, and directions, and undergo format, structural, and semantic checks. Type-conditioned low-rank adaptation, cue-aware continuous prompts, and a sentence-level auxiliary objective provide supporting mechanisms. The aim is to diversify conclusion expressions and relational contexts with consistent supervision, without assuming that more examples automatically improve class balance.

For inference-time repair, this thesis proposes MCR-BR, combining complete candidate-graph evaluation with anomaly-driven local repair. Graphs built from multiple component hypotheses are scored using argument-link coverage, edge-level semantic coherence, and output validity. Detected anomalies trigger local edits subject to acceptance checks, rollback, and limits on iterations and accepted actions. This connects candidate selection with post-generation adjustment; the surrogate score does not replace gold-standard evaluation.

The retained records report full-framework Component-F1/Relation-F1 scores of 83.71/64.83 on AAEC and 76.45/38.17 on CDCP. Under AAEC-to-CDCP zero-shot transfer with coarse component labels and directed unlabeled links, Link-F1 is 43.21, 9.79 points above the same-backbone Single-Pass baseline. These records indicate the potential value of combining enhancement and repair. Independent gains, matched-budget advantages, and broader transferability require configuration verification and corresponding ablations.

Keywords: Argument Mining; Large Language Models; Local Structure-Preserving Augmentation; Conclusion Components; Candidate-Graph Evaluation; Anomaly-Driven Repair
