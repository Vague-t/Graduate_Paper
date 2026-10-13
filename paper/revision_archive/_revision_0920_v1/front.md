# 面向关系感知学习与依赖闭合修正的端到端论辩挖掘方法研究

武汉大学计算机科学与技术学术型硕士学位论文

作者：Chen Tang

0920-v1修订稿　2026年9月20日

英文题目　End-to-End Argument Mining via Relation-Aware Learning and Dependency-Closed Repair

## 版本说明

本版本依据作者批准的完整研究方案v2修订，以本人ICIC 2026工作为基础，形成“面向结论组件的关系感知增强学习”和“多候选驱动的依赖闭合论辩图修正”两项完整方法设计。正文采用MCR-BR-J；原版MCR-BR-O和固定组件的MCR-BR-C保留为对照。不增加强化学习或多代理辩论路线。

本次修订建立方法与验证协议，不把预期结果写成已测得成绩。已公开ICIC结果、旧稿尚待配置绑定的记录及CPU诊断分开归档；它们均不替代新增方法的正式实验。作者此前关于实验已完成的说明予以保留，新增机制的结论以其对应材料为准。本版另存，不覆盖旧稿。

## 摘要

端到端论辩挖掘需要从原始文本中联合识别论辩组件的跨度、类型及组件间关系。组件不是相互独立的标签：训练时改变一个组件的表达，可能同时改变其与外部组件的支持、攻击或无关系状态；推理时修正一个组件的边界或类型，也可能使已有关系失效。现有生成式方法虽然能够统一输出论辩图，但仅增加文本变体或逐项修改预测，难以充分处理上述依赖。本文在作者前期结论组件专项优化、多候选重排序与有界修正研究的基础上，围绕关系监督的保持和预测依赖的恢复，形成两项相互补充的方法。

第一，设计面向结论组件的关系感知增强学习方法。以结论及其论辩邻域为改写单位，将改写区内部关系、跨边界关系和无关系状态共同纳入检查范围。生成器只改写指定组件文字，程序回填全文并输运标注，语义检查失败则拒绝整个变体。在继承结论专项适配、线索提示及句子辅助监督的基础上，以原文和增强文的对应组件及关系因素建立成对监督，约束共享生成表示对标签保持的表达变化维持一致。采用按源文档归一化的增强权重，控制同源变体数量造成的重复训练权重，类别分布另行统计。

第二，提出多候选驱动的依赖闭合论辩图修正方法MCR-BR-J。在多候选重排序获得初始图后，固定由全文跨度提议和候选图组成的可修改对象空间，以组件集合替换统一表示插入、删除、边界或类型调整及分割合并。每个替换方案必须同时重建全部受影响关系，包括入边、出边和原无关系位置，再作为一个事务整体评估、提交或回退。完整对象评分器在交叉拟合预测上学习组件及关系的正确性，固定计数效用将接受决策解释为代价敏感风险代理的改进；预算和严格增分条件限定搜索过程。形式分析给出标注输运、局部差分计算和有限终止的条件，但不将这些性质等同于真实F1必然提高。

本文建立AAEC与CDCP上的验证协议，分别检验训练增强和推理修正的独立贡献，并将CDCP多前提关系作为原生超边处理。验证重点包括近邻增强方法、同数据不同损失、同候选同评分的顺序与联合修正、结构化全局解码，以及候选覆盖、错误修改和计算成本。现有公开成果与轻量诊断用于说明研究基础和适用边界，新增方法的实证结论仍需与相应运行记录及严格评价结果绑定。

关键词：端到端论辩挖掘；关系感知增强；结论组件；依赖闭合；图修正；代价敏感评分

## Abstract

End-to-end argument mining jointly identifies component spans, component types, and argumentative relations from raw text. Components are interdependent: paraphrasing a component during training may alter its relations to surrounding components, while changing its span or type during inference may invalidate existing relations. Increasing the number of textual variants or editing predictions independently does not explicitly address these dependencies. Building on the author's prior work on conclusion-specific modeling, multi-candidate reranking, and bounded repair, this thesis develops two complementary methods for preserving relational supervision and restoring prediction dependencies.

The first method is relation-aware augmentation learning for conclusion components. A conclusion-centered neighborhood defines the editable text, while internal relations, boundary-crossing relations, and annotated no-relation states define the affected supervision. Only designated component text may be rewritten. A deterministic reconstruction procedure transfers annotations to the augmented document, and detected semantic drift leads to rejection of the entire variant. In addition to the inherited adapter, cue-aware prompting, and sentence-level supervision, paired component and relation objectives encourage the shared generation representation to remain consistent across accepted variants. Source-document normalization controls the repeated contribution of unchanged content.

The second method, MCR-BR-J, performs dependency-closed argument-graph repair after multi-candidate reranking. A fixed candidate universe supports component-set replacements, including insertion, deletion, span or type changes, splitting, and merging. Every replacement is evaluated together with the reconstruction of all affected incoming and outgoing relations and previously absent links. The complete transaction is committed or rolled back atomically. An object-correctness scorer trained on out-of-fold predictions supplies a fixed count-based utility with a cost-sensitive risk interpretation. Strict acceptance and explicit budgets bound the search. Conditional analyses establish annotation transport, local utility differences, and finite termination, without claiming guaranteed improvement in true F1.

The evaluation protocol separates the contributions of training-time learning and inference-time repair on AAEC and CDCP, retaining CDCP multi-premise relations as native hyperedges. It includes related augmentation methods, matched-data loss ablations, sequential and joint repair under identical candidates and scores, global structured decoding, candidate recovery, harmful edits, and computational cost. Published prior results and lightweight diagnostics establish the research basis and its limits; empirical claims for the new methods require their own reproducible runs and strict evaluation.

Keywords: End-to-End Argument Mining; Relation-Aware Augmentation; Conclusion Components; Dependency Closure; Graph Repair; Cost-Sensitive Scoring
