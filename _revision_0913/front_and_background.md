# 基于大语言模型的端到端论辩挖掘方法研究

武汉大学计算机科学与技术学术型硕士学位论文

0913修订工作稿　2026年9月13日

英文题目　End-to-End Argument Mining with Large Language Models

## 版本说明

本稿以report_final.md为内容基线，依据严格审阅意见完成结构精简、任务与评价口径统一、文献更正及方法边界分析。原稿实验表格的数值予以保留，本次修订未重新训练模型或复现实验。文中“原稿记录”表示数值来自原稿，不表示已通过日志核验；“待核验”标记属于工作稿编辑说明，需用实际代码、数据和实验记录解决后方可删除。

当前最重要的未决事项是第三章与第四章Single-Pass分数及Full配置的对应关系、Claim-specific Adapter的门控实现、修复操作的可执行定义，以及实验划分、重复次数和统计量来源。本稿不能替代上述证据，也不作为已满足送审要求的声明。正式封面、作者及导师信息、原创性声明、授权页、致谢和成果页应在定稿时按学院当年模板补齐，本稿不代填或代签。

## 摘要

论辩挖掘旨在从非结构化文本中识别论辩组件及其关系，并恢复符合语料标注规范的论辩图。生成式大语言模型能够统一输出组件跨度、类型和有向关系，但组件遗漏会限制后续关系预测的可达空间，格式合法的输出也可能包含错误引用或缺乏语义依据的连接。本文围绕候选组件质量和推理阶段结构恢复两个问题，研究面向端到端论辩挖掘的训练增强与多候选修正方法。

在训练阶段，本文以结论类组件及其局部论辩子图为条件构造增强样本，通过格式、结构和语义检查控制样本质量，并结合类型条件低秩适配、线索感知连续提示和句子级辅助目标，增强结论组件的表示。该设计以保留监督结构和提高结论表达多样性为目标，不将扩充样本数量直接等同于改善类别平衡。

在推理阶段，本文提出多候选重排序与有界修正框架MCR-BR。框架为多个组件假设构建候选图，结合论证连接覆盖、边语义连贯性和输出合法性进行评分，再对检测到的异常尝试局部、可回退的修改。评分非下降仅约束代理目标，不保证每次修改都提高真实任务指标；现有轮数和接受动作预算限制的是修正步数，而非未经进一步约束的模型调用总量。

按原稿保留的实验记录，完整框架在AAEC上的Component-F1和Relation-F1分别为83.71和64.83，在CDCP上分别为76.45和38.17。AAEC到CDCP的零样本迁移采用粗粒度组件标签及有向无标签连接评价，完整框架的Link-F1为43.21，较同骨干Single-Pass记录提高9.79个F1点。这些结果为方法的进一步验证提供了依据，但训练增强的独立贡献、相同计算预算下的优势及跨域稳健性仍需结合配置核验和补充实验确定。

关键词：论辩挖掘；大语言模型；结构化生成；结论组件增强；多候选重排序；局部修正

## Abstract

Argument mining identifies argumentative components and their relations in unstructured text and recovers an argument graph under corpus-specific annotation guidelines. Generative large language models can jointly output component spans, types, and directed relations. However, missing components restrict the space of recoverable relations, while syntactically valid outputs may still contain invalid references or semantically unsupported links. This thesis studies training-time component enhancement and inference-time structural recovery for end-to-end argument mining.

For training-time enhancement, local argument subgraphs centered on conclusion-type components are used to condition synthetic example generation. Format, structural, and semantic checks filter the generated examples. Type-conditioned low-rank adaptation, cue-aware continuous prompts, and a sentence-level auxiliary objective are combined to strengthen conclusion representations. The augmentation is intended to diversify conclusion expressions while preserving supervision; increasing the number of examples does not by itself establish improved class balance.

For inference-time recovery, this thesis develops MCR-BR, a framework for multi-candidate reranking and bounded repair. It constructs argument graphs from multiple component hypotheses, scores them using argument-link coverage, edge-level semantic coherence, and output validity, and attempts local, reversible edits in response to detected anomalies. Non-decreasing scores constrain a surrogate objective rather than guarantee improvements in task F1. The current iteration and accepted-action budgets bound repair steps, not the total number of model calls without additional restrictions.

The experimental records retained from the original manuscript report Component-F1 and Relation-F1 scores of 83.71 and 64.83 on AAEC, and 76.45 and 38.17 on CDCP. Under an AAEC-to-CDCP zero-shot transfer protocol using coarse component labels and directed unlabeled links, the full framework records a Link-F1 of 43.21, 9.79 points above the same-backbone Single-Pass baseline. These records motivate further validation. Establishing the independent contribution of training enhancement, advantages under matched computational budgets, and transfer robustness requires configuration checks and additional experiments.

Keywords: Argument Mining; Large Language Models; Structured Generation; Conclusion Component Enhancement; Multi-Candidate Reranking; Local Repair

## 第一章 绪论

### 1.1 研究背景与问题提出

论辩挖掘研究文本中的主张、理由及其连接方式，目标不只是判断作者赞成或反对什么，还包括定位论证内容并识别论证结构。其研究对象涵盖说服性作文、公共政策评论和其他带有论证行为的文本。论辩挖掘与立场检测、论证质量评价等任务相关，但组件和关系抽取的准确性不能直接替代对论证有效性或事实真实性的评价[@lawrence2019]。

本文关注从原始文本到组件跨度、组件类型及有向关系的联合预测。AAEC以学生说服性作文为对象，区分MajorClaim、Claim和Premise；CDCP以电子规则制定评论为对象，采用Fact、Testimony、Value、Policy和Reference等组件类型[@stab2017][@park2018]。两个语料的标签不能仅凭名称直接对齐，关系拓扑也不能统一假设为树。因此，本文将图约束限定为给定实验表示下的任务约束，不将所有自然语言论辩都定义为有向无环图。

生成式建模把多个子任务映射到同一输出序列，使组件和关系能够共享上下文，但没有消除输出内部的依赖关系。例如，一个Claim的跨度没有被召回时，以该节点为端点的金标准关系便不能在当前候选集合中得到精确匹配；一个存在的Claim被赋予错误编号时，则可能形成可被确定性检查发现的引用错误。前者是候选空间不足，后者是结构一致性错误，二者需要不同的处理机制。

这一差异构成本文的研究出发点。训练阶段尝试提高结论类组件的候选质量，推理阶段保留多个结构假设并利用图级反馈进行选择和局部修改。研究重点不是证明大语言模型能够生成结构化文本，而是分析结构约束如何参与候选选择、哪些局部错误可以被修正，以及这些操作在什么条件下值得额外的计算开销。

### 1.2 国内外研究现状

#### 1.2.1 组件识别与联合结构预测

Stab和Gurevych围绕说服性作文建立组件与关系分析方法，为AAEC上的结构预测研究提供了任务和标注基础[@stab2017]。Eger等将组件识别与论证结构预测纳入神经端到端学习框架，说明联合建模并非大语言模型出现后才产生的路线[@eger2017]。Morio等研究命题级双仿射解析与任务特定参数化，面向非树状论辩结构进行预测，而不是以图神经网络替代所有子任务[@morio2020]。

这些工作表明，组件识别与关系预测的相互依赖、树与非树结构的差异，以及共享表示和任务特定参数的权衡，均已有直接相关研究。本文的区分点应放在生成候选之后的图级选择与局部回退机制，以及结论类监督如何与完整图恢复衔接，而不能把“联合预测组件和关系”本身列为新贡献。

#### 1.2.2 生成式端到端论辩挖掘

Kawarada等将论辩挖掘表述为文本到文本生成任务，比较了微调模型和提示式模型在不同语料上的表现，是本文最直接的生成式基线[@kawarada2024]。因此，统一序列化输出、采用生成模型及跨语料评测均属于已有技术基础。本文需要通过相同数据划分、输入粒度、精确匹配规则和计算预算下的比较，证明候选评估与修正的增量价值。

Sun等提出DENIM，通过篇章结构感知前缀辅助生成式端到端论辩挖掘[@sun2024]。这一工作已经利用篇章信息影响生成过程，与本文线索感知提示和结构信号的使用存在相邻关系；区别在于信号进入模型的位置、表示粒度和是否在生成之后执行结构修改，而不是“是否使用结构信息”。现有稿件尚未提供DENIM在统一协议下的对照结果，故不能宣称超过所有生成式方法。

Li等的综述梳理了大语言模型论辩挖掘中的任务重构、提示和评估问题，并讨论LLM评判可靠性等挑战[@li2025]。在本研究范围内，模型规模扩大、输出更流畅和验证器自评得分提高都不是充分的有效性证据。端到端结果应回到金标准跨度、类型和关系的匹配，并与额外推理成本一起解释。

#### 1.2.3 中文及跨语料研究

中文论辩资源与英文作文语料的任务设置并不相同。ORCHID面向中文辩论的目标无关立场检测和论辩对话摘要，不是AAEC式全文组件与关系图抽取数据集[@zhao2023]。IAM整合多项论辩挖掘任务，使用英文资源，不能作为“中文论辩语料”的例证[@cheng2022]。本研究使用英文AAEC和CDCP，因而不能从中文学位论文的写作语言推导模型已具备中文论辩挖掘能力。

跨语料评价还受到标注规范变化的影响。若把AAEC的MajorClaim和Claim合并，再把CDCP的部分功能类型映射为Claim，评价任务本身已发生变化。本文在第五章显式定义这种归约，将其定位为单向、粗粒度协议下的迁移分析，而非无损的标签迁移或通用跨领域论辩理解。

#### 1.2.4 结构感知数据增强

大语言模型数据增强可通过自然语言条件控制生成内容，但可控性、质量筛选和分布偏差仍是重要问题[@ding2024]。CoDa从训练实例提取约束并通过提示生成新样本，为条件增强提供了相关路线[@evuru2024]。SegMix则在任务相关片段上进行插值式增强，并在命名实体识别和关系抽取等任务上验证；它不是对论辩组件进行自由文本互换的方法[@pei2023]。

本文的增强单位是结论节点及其局部邻域。与孤立句子改写相比，该单位显式保留组件数量、类型和关系端点；但其是否优于普通改写，必须在等样本量或等训练步数下比较，不能仅依赖方法描述判断。尤其当每个新增样本同时包含一个Claim和多个Premise时，增强不一定改善实例级类别比例。本文将“表达多样性”与“类别平衡”分开提出验证要求。

#### 1.2.5 约束解码与推理时修正

语法约束解码通过限制允许的后继token约束输出形式，输入相关语法还能表达部分依赖于输入的限制[@geng2023]。其保证范围取决于实际编码进语法的条件；JSON可解析不等于跨度真实、关系成立或图拓扑正确。本文将语法检查、任务结构检查和语义验证分开处理。

Self-Refine使用生成、反馈和修订循环改进输出[@madaan2023]。Huang等在所研究的推理设置中发现，缺少外部反馈的内在自纠错可能无效甚至降低表现[@huang2023]。这些结论支持检查反馈可靠性的必要性，但不能直接证明本文验证器可靠，也不能推广为所有自修正方法均无效。

自一致性方法通过采样多条推理路径并聚合答案提高所研究推理任务的表现[@wang2022]。完整论辩图则涉及跨度、类型、端点和拓扑的联合一致性，对节点和边独立投票可能拼出任何候选中都不存在的图。本文因此选择在完整候选图层面评分，再执行受约束的局部修改。这一设计与一般多采样共享候选生成思想，其任务特定价值仍需通过预算匹配的消融验证。

### 1.3 研究问题与贡献定位

本文将研究目标组织为三个可检验问题。

RQ1：结论类组件的结构感知增强及表示增强，能否在不明显损害Premise识别的条件下改善结论跨度与类型预测？这一问题需要分类别Precision、Recall和F1，以及增强、适配器、提示和辅助损失的独立消融；完整系统总分不能单独回答它。

RQ2：给定相同骨干和候选预算，图级评分与局部修正是否比序列概率选择、确定性后处理和通用自修正获得更好的端到端结果？这一问题需要保持候选池一致，区分候选数增加、选择器改变和BR本身的影响，并报告错误修改与推理成本。

RQ3：上述方法在明确标签归约的AAEC到CDCP迁移协议下，是否仍获得相对于源域训练基线的改进？这一问题只涉及规定的单向迁移设置，不能推导多语言或所有领域上的稳健性。

本文的方法贡献定位为两项。第一，围绕结论类节点组织训练增强，将局部拓扑条件、样本筛选和类型相关表示结合起来。第二，构造MCR-BR，将完整候选图选择与异常驱动的局部回退机制结合起来。LoRA、连续提示、多候选采样和自修正本身均不是本文原创技术；可主张的创新在于面向论辩图恢复的具体组织方式及其经实验支持的增量价值。

表1-1 研究问题与证据对应关系

|研究问题|主要方法|现有材料|尚缺的关键证据|
|:---|:---|:---|:---|
|RQ1 结论组件质量|结构感知增强与表示增强|分类别表与部分模块消融|配置冲突消解、类别统计、增强独立消融|
|RQ2 图级结构恢复|多候选评分与有界修正|域内比较、验证器替换、Oracle记录|固定候选池比较、可执行动作、预算与时延|
|RQ3 跨语料适用性|粗粒度映射下的源域迁移|AAEC到CDCP单向记录|目标数据使用审计、双向迁移和映射敏感性|

表1-1用于限定本稿的证据范围。原稿报告的性能差值属于待配置核验的实验记录；新增的方法分析属于对现有定义的推导，不是新增实验证据。

### 1.4 论文组织结构

第一章介绍研究问题、相关工作和贡献边界。第二章统一任务表示、序列化规范、评价口径及方法所需的技术基础。第三章讨论结论组件增强，明确其监督来源和可复现条件。第四章给出MCR-BR的评分与修正流程，分析算法保证范围并整理域内实验。第五章讨论粗粒度协议下的跨语料迁移。第六章总结研究内容及当前证据边界。附录给出实现核验清单和可单独实验的算法修订建议，不将建议视为已完成实验的方法。

## 第二章 任务表示与方法基础

### 2.1 论辩组件与关系表示

设输入文档在固定评价分词器下表示为$D=(x_1,\ldots,x_n)$。一个组件定义为$c_i=(s_i,e_i,\tau_i)$，其中$1\leq s_i\leq e_i\leq n$，跨度采用从1开始的闭区间，$\tau_i$为数据集规定的类型。评价token与模型内部子词token不是同一概念；模型输出需映射回统一评价坐标后再比较。具体分词器和映射脚本属于实验配置，不能仅靠这一数学定义确定。

组件集合记为$C=\{c_1,\ldots,c_m\}$。关系定义为$(i,j,r)$，其中$i$和$j$引用组件编号，方向约定为论据或攻击来源指向被支持或被攻击的目标。预测图为$G=(V,E)$，节点对应组件，边对应关系。本文的“端到端”指评价从原始文本出发、不提供金标准组件；系统内部可以包含组件生成、关系构建与验证等阶段，并不特指一次模型调用。

表2-1 域内任务的标签与评价边界

|语料|组件类型|本文域内关系标签|需要区分的属性或结构|
|:---|:---|:---|:---|
|AAEC|MajorClaim、Claim、Premise|Support、Attack|Claim对MajorClaim的stance不混入本文关系F1|
|CDCP|Fact、Testimony、Value、Policy、Reference|Reason、Evidence|允许非树状连接；需核验多片段前提的预处理|

表2-1依据相应语料与文本到文本基线的任务说明整理[@stab2017][@park2018][@kawarada2024]。AAEC中Claim与MajorClaim的立场属性不能在缺少说明的情况下转换为Support或Attack边；因此MajorClaim的重要性不能直接用本文关系集合中的高连接度来论证。CDCP的功能类型也不与Claim/Premise天然等价，第五章的映射是额外评测选择。

### 2.2 合法图与序列化约定

对实验标注规范$\mathcal{A}$，记满足跨度、类型、引用和指定拓扑条件的图集合为$\mathcal{G}_{\mathcal A}$。本文的无环性属于所采用实验表示的约束，不是对所有论辩语料或抽象论辩理论的定义。若预处理删除环、合并组件或简化边，应报告受影响样本及其比例，以免通过预处理改变测试任务。

在“论据指向结论”的边方向下，局部根节点的出度为0，叶节点的入度为0。若需要定义深度，应沿实际边方向计算叶到根路径，或明确在反向图上计算根到叶距离，不能在原图中同时采用根出度为0和根沿出边到达叶的定义。一个文档可能包含多个不连通子图，因此不要求每篇文档恰好一个根。

序列化规范包括唯一组件ID、整数跨度、合法类型及关系端点。以下为人工构造的格式示例，不是实验样本。评价token序列为“Libraries / should / stay / open / longer / . / Students / need / study / space / .”，其中Claim跨度为1至5，Premise跨度为7至10，后者支持前者。

```json
{
  "components": [
    {"id": 1, "span": [1, 5], "type": "Claim"},
    {"id": 2, "span": [7, 10], "type": "Premise"}
  ],
  "relations": [
    {"source": 2, "target": 1, "type": "Support"}
  ]
}
```

该例只说明坐标和引用约定。它不声称所有实现均采用相同字段顺序；第三章的门控依赖字段顺序，必须另行核对实际解码配置。去重、重叠跨度消解和编号重排均应同时更新关系端点，并保留原始输出与规范化输出，以便区分生成错误和解析器造成的变化。

### 2.3 生成建模与参数高效适配

对序列化输出$Y=(y_1,\ldots,y_L)$，自回归模型定义为：

$$P_\theta(Y\mid D)=\prod_{t=1}^{L}P_\theta(y_t\mid D,y_{<t}).$$

Transformer通过自注意力聚合上下文信息，为序列建模提供基础[@vaswani2017]。本文使用的骨干为原稿所述Qwen2.5-7B-Instruct；Qwen2.5技术报告可用于说明模型系列，但不能代替本文具体权重版本、训练配置和硬件记录[@qwen2024]。序列概率受输出长度和字段顺序影响，用于候选排序时需明确是否长度归一化；高概率并不意味着候选图中的每条关系均正确。

LoRA在冻结基础权重的条件下引入低秩增量[@hu2021]。对于一般线性投影，采用统一表示：

$$W=W_0+\frac{\alpha}{r}BA,\quad A\in\mathbb R^{r\times d_{in}},\quad B\in\mathbb R^{d_{out}\times r}.$$

其中$r$为秩，$\alpha$为缩放系数。第三章的类型条件门控是附加于这一低秩分支的任务设计，不应把LoRA本身描述为新提出的结构。连续提示则使用可学习向量为冻结或部分微调的模型提供任务条件，其相关基础来自参数高效提示调优研究[@lester2021]。是否启用提示、提示插入位置及其与LoRA共同训练的方式，均属于具体实现而非方法名称自带的性质。

### 2.4 候选选择与代理评分

给定候选集合$\mathcal S=\{S_1,\ldots,S_K\}$，重排序选择代理评分最高的候选：

$$S^*=\arg\max_{S\in\mathcal S}E(S).$$

这一过程包含两个不同问题：候选池中是否存在较好的结构，以及评分器是否能选到该结构。增加候选数可能改善前者，却不保证后者；重复候选还会增加成本而不扩大结构覆盖。Candidate Oracle可以在预先规定的金标准指标下估计当前候选池的可利用空间，但只能作为离线诊断，不能参与测试时的实际选择。

本研究采用语义与结构混合评分。确定性检查能判断跨度越界、引用缺失等形式条件，语义验证器则判断上下文是否支持某条论辩关系。二者性质不同：前者相对于明确定义的检查规则可重复计算，后者仍受模型误判、提示和采样影响。生成器与验证器分开调用并不等于模型或知识来源独立，相关误差也不能通过调用次数自然消除。

### 2.5 评价指标与可比性条件

对于组件或关系集合，以$TP$、$FP$、$FN$分别表示正确预测、错误预测和遗漏对象的数量。总体精确率、召回率和F1为：

$$P=\frac{TP}{TP+FP},\quad R=\frac{TP}{TP+FN},\quad F_1=\frac{2TP}{2TP+FP+FN}.$$

组件评价采用跨度和类型精确匹配；关系评价要求源组件、目标组件、方向及关系类型符合预先约定的匹配规则。为避免端点类型处理差异，复现实验必须明确端点匹配是否包含类型，并对所有方法使用同一脚本。总体micro-F1应先汇总对象计数再计算，不能用分类别F1的算术平均替代。每文档macro-F1、跨类别macro-F1和多次运行的均值属于不同统计量，需分别命名。

本稿公式和新增分析使用集合级精确匹配解释；原稿表格尚缺评价脚本与重复运行记录，故不据此补填其micro/macro配置，也不把“±”擅自解释为标准差或置信区间。F1数值按百分制报告，两个值相减称为“F1点”，不称相对提升百分比。相对增幅若使用，必须另列分母。

跨域Link-F1主动忽略关系类型，不能与域内细粒度Relation-F1直接比较来估计领域性能下降。结构合法率也不能代替任务F1：删除所有关系可能消除引用错误，却同时丢失真实边。完整评价应同时关注组件和关系质量、输出合法性、错误修改风险以及推理成本。

### 2.6 本章小结

本章统一了组件坐标、关系方向、数据集特定约束和评价口径，并区分语法合法性、图结构一致性与语义正确性。上述定义为第三章的结论组件增强和第四章的图级修正提供共同接口，也限定了实验结果能够支持的结论范围。
