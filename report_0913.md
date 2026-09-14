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

论辩挖掘研究文本中的主张、理由及其连接方式，目标不只是判断作者赞成或反对什么，还包括定位论证内容并识别论证结构。其研究对象涵盖说服性作文、公共政策评论和其他带有论证行为的文本。论辩挖掘与立场检测、论证质量评价等任务相关，但组件和关系抽取的准确性不能直接替代对论证有效性或事实真实性的评价[1]<!--ref:lawrence2019--><!--anchor:section:Abstract-->。

本文关注从原始文本到组件跨度、组件类型及有向关系的联合预测。AAEC以学生说服性作文为对象，区分MajorClaim、Claim和Premise；CDCP以电子规则制定评论为对象，采用Fact、Testimony、Value、Policy和Reference等组件类型[2]<!--ref:stab2017--><!--anchor:section:3-->[3]<!--ref:park2018--><!--anchor:section:3-->。两个语料的标签不能仅凭名称直接对齐，关系拓扑也不能统一假设为树。因此，本文将图约束限定为给定实验表示下的任务约束，不将所有自然语言论辩都定义为有向无环图。

生成式建模把多个子任务映射到同一输出序列，使组件和关系能够共享上下文，但没有消除输出内部的依赖关系。例如，一个Claim的跨度没有被召回时，以该节点为端点的金标准关系便不能在当前候选集合中得到精确匹配；一个存在的Claim被赋予错误编号时，则可能形成可被确定性检查发现的引用错误。前者是候选空间不足，后者是结构一致性错误，二者需要不同的处理机制。

这一差异构成本文的研究出发点。训练阶段尝试提高结论类组件的候选质量，推理阶段保留多个结构假设并利用图级反馈进行选择和局部修改。研究重点不是证明大语言模型能够生成结构化文本，而是分析结构约束如何参与候选选择、哪些局部错误可以被修正，以及这些操作在什么条件下值得额外的计算开销。

### 1.2 国内外研究现状

#### 1.2.1 组件识别与联合结构预测

Stab和Gurevych围绕说服性作文建立组件与关系分析方法，为AAEC上的结构预测研究提供了任务和标注基础[2]<!--ref:stab2017--><!--anchor:section:3-->。Eger等将组件识别与论证结构预测纳入神经端到端学习框架，说明联合建模并非大语言模型出现后才产生的路线[4]<!--ref:eger2017--><!--anchor:section:Abstract-->。Morio等研究命题级双仿射解析与任务特定参数化，面向非树状论辩结构进行预测，而不是以图神经网络替代所有子任务[5]<!--ref:morio2020--><!--anchor:section:Abstract-->。

这些工作表明，组件识别与关系预测的相互依赖、树与非树结构的差异，以及共享表示和任务特定参数的权衡，均已有直接相关研究。本文的区分点应放在生成候选之后的图级选择与局部回退机制，以及结论类监督如何与完整图恢复衔接，而不能把“联合预测组件和关系”本身列为新贡献。

#### 1.2.2 生成式端到端论辩挖掘

Kawarada等将论辩挖掘表述为文本到文本生成任务，比较了微调模型和提示式模型在不同语料上的表现，是本文最直接的生成式基线[6]<!--ref:kawarada2024--><!--anchor:section:4-->。因此，统一序列化输出、采用生成模型及跨语料评测均属于已有技术基础。本文需要通过相同数据划分、输入粒度、精确匹配规则和计算预算下的比较，证明候选评估与修正的增量价值。

Sun等提出DENIM，通过篇章结构感知前缀辅助生成式端到端论辩挖掘[7]<!--ref:sun2024--><!--anchor:section:Abstract-->。这一工作已经利用篇章信息影响生成过程，与本文线索感知提示和结构信号的使用存在相邻关系；区别在于信号进入模型的位置、表示粒度和是否在生成之后执行结构修改，而不是“是否使用结构信息”。现有稿件尚未提供DENIM在统一协议下的对照结果，故不能宣称超过所有生成式方法。

Li等的综述梳理了大语言模型论辩挖掘中的任务重构、提示和评估问题，并讨论LLM评判可靠性等挑战[8]<!--ref:li2025--><!--anchor:section:Abstract-->。在本研究范围内，模型规模扩大、输出更流畅和验证器自评得分提高都不是充分的有效性证据。端到端结果应回到金标准跨度、类型和关系的匹配，并与额外推理成本一起解释。

#### 1.2.3 中文及跨语料研究

中文论辩资源与英文作文语料的任务设置并不相同。ORCHID面向中文辩论的目标无关立场检测和论辩对话摘要，不是AAEC式全文组件与关系图抽取数据集[9]<!--ref:zhao2023--><!--anchor:section:Abstract-->。IAM整合多项论辩挖掘任务，使用英文资源，不能作为“中文论辩语料”的例证[10]<!--ref:cheng2022--><!--anchor:section:3.1-->。本研究使用英文AAEC和CDCP，因而不能从中文学位论文的写作语言推导模型已具备中文论辩挖掘能力。

跨语料评价还受到标注规范变化的影响。若把AAEC的MajorClaim和Claim合并，再把CDCP的部分功能类型映射为Claim，评价任务本身已发生变化。本文在第五章显式定义这种归约，将其定位为单向、粗粒度协议下的迁移分析，而非无损的标签迁移或通用跨领域论辩理解。

#### 1.2.4 结构感知数据增强

大语言模型数据增强可通过自然语言条件控制生成内容，但可控性、质量筛选和分布偏差仍是重要问题[11]<!--ref:ding2024--><!--anchor:section:Abstract-->。CoDa从训练实例提取约束并通过提示生成新样本，为条件增强提供了相关路线[12]<!--ref:evuru2024--><!--anchor:section:Abstract-->。SegMix则在任务相关片段上进行插值式增强，并在命名实体识别和关系抽取等任务上验证；它不是对论辩组件进行自由文本互换的方法[13]<!--ref:pei2023--><!--anchor:section:Abstract-->。

本文的增强单位是结论节点及其局部邻域。与孤立句子改写相比，该单位显式保留组件数量、类型和关系端点；但其是否优于普通改写，必须在等样本量或等训练步数下比较，不能仅依赖方法描述判断。尤其当每个新增样本同时包含一个Claim和多个Premise时，增强不一定改善实例级类别比例。本文将“表达多样性”与“类别平衡”分开提出验证要求。

#### 1.2.5 约束解码与推理时修正

语法约束解码通过限制允许的后继token约束输出形式，输入相关语法还能表达部分依赖于输入的限制[14]<!--ref:geng2023--><!--anchor:section:Abstract-->。其保证范围取决于实际编码进语法的条件；JSON可解析不等于跨度真实、关系成立或图拓扑正确。本文将语法检查、任务结构检查和语义验证分开处理。

Self-Refine使用生成、反馈和修订循环改进输出[15]<!--ref:madaan2023--><!--anchor:section:Abstract-->。Huang等在所研究的推理设置中发现，缺少外部反馈的内在自纠错可能无效甚至降低表现[16]<!--ref:huang2023--><!--anchor:section:Abstract-->。这些结论支持检查反馈可靠性的必要性，但不能直接证明本文验证器可靠，也不能推广为所有自修正方法均无效。

自一致性方法通过采样多条推理路径并聚合答案提高所研究推理任务的表现[17]<!--ref:wang2022--><!--anchor:section:Abstract-->。完整论辩图则涉及跨度、类型、端点和拓扑的联合一致性，对节点和边独立投票可能拼出任何候选中都不存在的图。本文因此选择在完整候选图层面评分，再执行受约束的局部修改。这一设计与一般多采样共享候选生成思想，其任务特定价值仍需通过预算匹配的消融验证。

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

表2-1依据相应语料与文本到文本基线的任务说明整理[2]<!--ref:stab2017--><!--anchor:section:3-->[3]<!--ref:park2018--><!--anchor:section:3-->[6]<!--ref:kawarada2024--><!--anchor:section:4-->。AAEC中Claim与MajorClaim的立场属性不能在缺少说明的情况下转换为Support或Attack边；因此MajorClaim的重要性不能直接用本文关系集合中的高连接度来论证。CDCP的功能类型也不与Claim/Premise天然等价，第五章的映射是额外评测选择。

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

Transformer通过自注意力聚合上下文信息，为序列建模提供基础[18]<!--ref:vaswani2017--><!--anchor:section:Abstract-->。本文使用的骨干为原稿所述Qwen2.5-7B-Instruct；Qwen2.5技术报告可用于说明模型系列，但不能代替本文具体权重版本、训练配置和硬件记录[19]<!--ref:qwen2024--><!--anchor:section:Abstract-->。序列概率受输出长度和字段顺序影响，用于候选排序时需明确是否长度归一化；高概率并不意味着候选图中的每条关系均正确。

LoRA在冻结基础权重的条件下引入低秩增量[20]<!--ref:hu2021--><!--anchor:section:Abstract-->。对于一般线性投影，采用统一表示：

$$W=W_0+\frac{\alpha}{r}BA,\quad A\in\mathbb R^{r\times d_{in}},\quad B\in\mathbb R^{d_{out}\times r}.$$

其中$r$为秩，$\alpha$为缩放系数。第三章的类型条件门控是附加于这一低秩分支的任务设计，不应把LoRA本身描述为新提出的结构。连续提示则使用可学习向量为冻结或部分微调的模型提供任务条件，其相关基础来自参数高效提示调优研究[21]<!--ref:lester2021--><!--anchor:section:Abstract-->。是否启用提示、提示插入位置及其与LoRA共同训练的方式，均属于具体实现而非方法名称自带的性质。

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

## 第三章 面向结论类组件的结构感知增强

端到端论辩挖掘同时预测组件与关系，组件集合决定了后续关系搜索空间。若关键Claim未被识别，任何关系模块都无法在缺失节点上恢复正确边。为降低这一上游瓶颈，本章面向MajorClaim和Claim提出结论类组件优化方法：首先在训练数据层面生成带局部论证结构的增强样本，再在模型层面引入Claim-specific Adapter、Cue-aware Soft Prompting和辅助判别目标。三类机制分别补充样本多样性、强化类型相关参数更新并显式建模结论线索。

### 3.1 组件不平衡与结构影响

#### 3.1.1 统计口径

设训练集组件类型集合为$\mathcal{T}$，类型$\tau$的组件实例数为$N_\tau$，则实例级类别不平衡比定义为：

$$\operatorname{IR}=\frac{\max_{\tau\in\mathcal{T}}N_\tau}{\min_{\tau\in\mathcal{T}}N_\tau}.$$

本文以完成数据划分之后的训练集组件实例作为类别统计单位。该口径不同于token级BIO标签数和句子级标签数，不能相互替代。实例数也不能直接决定生成损失的贡献，因为不同类型组件对应的输出长度和损失归一化方式可能不同。

待核验R01：原稿没有提供实际训练划分下各类型的实例数、增强后的数量及IR值。本稿保留结论类增强的研究动机，但不把未经统计的“长尾程度”或“梯度覆盖”当作已证实事实。应分别报告MajorClaim、Claim和Premise的实例数、平均跨度长度及含该类型的文档数。

在本文AAEC关系评价中，Claim到MajorClaim的stance不计为关系边。因此，局部Claim的遗漏可直接影响其关联边召回，MajorClaim的优化主要对应文档级类型与语境表示；二者不能共享“高连接度节点”的统一论证。

#### 3.1.2 错误传播路径

给定金标准组件集合$C$和预测组件集合$\hat C$，关系模块若不改变组件集合，只能在$\hat C\times\hat C$上预测。令$V_{hit}$为按既定端点匹配规则被召回的金标准节点集合，定义可达金标准边集合：

$$E_{reach}=\{(i,j,r)\in E:i\in V_{hit},j\in V_{hit}\}.$$

当$|E|>0$且评价要求两端点精确匹配时，关系召回率满足：

$$R_{rel}\leq \frac{|E_{reach}|}{|E|}.$$

证明：任何计为正确的预测关系，其两个端点都必须存在于当前可匹配组件集合中，因此正确关系集合是$E_{reach}$的子集。该上界只描述候选空间，不保证这些边能被关系模块预测正确。对多个遗漏节点，应按关联边的并集计数，避免一条边因两个端点均遗漏而重复计入损失；对于在当前关系表示中没有关联边的MajorClaim，不能由该式推出直接的关系召回损失。

本文据此将优化目标从一般类别平衡进一步收敛为两点：一是提高结论类组件的边界与类型识别能力；二是在不过度牺牲Premise性能的前提下，提高包含高连接度结论节点的候选图召回率。

### 3.2 基于大语言模型的结构感知数据增强

#### 3.2.1 局部子图作为增强单位

普通文本改写只约束句子语义，容易在改写后破坏组件边界或关系方向。本文以局部论辩子图而非孤立句子作为增强单位。对训练文档图$G=(V,E)$中的结论类节点$v_c$，提取其一跳支撑或攻击邻域：

$$G_c=(V_c,E_c),\qquad V_c=\{v_c\}\cup\{v_i\mid(v_i,v_c,r)\in E\}.$$

在AAEC中，局部子图按段落关系标注构造，不将未标注的Claim—MajorClaim立场直接转化为关系边。增强模型接收组件文本、组件类型、关系方向和目标结构等条件，生成保持图拓扑不变但表述不同的文本变体。这样既增加结论表达的词汇与句法多样性，也保留关系训练所需的结构监督。

#### 3.2.2 条件生成约束

对局部子图$G_c$，生成过程表示为：

$$D_c'=\operatorname{LLM}_{aug}(D_c\mid \mathcal{T}_c,E_c,\Pi),$$

其中$D_c$为原始局部文本，$\mathcal{T}_c$为目标组件类型，$E_c$为需要保持的关系集合，$\Pi$为生成约束。约束包括：组件数量和类型保持一致；关系端点必须能够在生成文本中对齐；不得新增原结构之外的支持或攻击关系；不得复制验证集或测试集文本。

为降低模板化生成造成的分布偏差，增强提示同时允许词汇替换、句法重组和论据表述变化，但不允许改变原有立场。生成仅基于训练集进行；原始文档的全部增强版本与原文保持在同一数据划分中，防止同源样本跨集合泄漏。

#### 3.2.3 三层质量筛选

对生成样本$(D_c',G_c')$依次执行三层筛选：

1. **格式合法性**：JSON可解析、必需字段存在、组件编号唯一且跨度位于文本范围内；
2. **结构一致性**：组件数量、类型集合和关系方向满足给定模板，且不存在悬空引用和循环边；
3. **语义一致性**：独立验证器判断生成组件是否承担目标论辩角色，并检查每条关系是否获得上下文支持。

定义三个二值检查函数$q_{fmt}$、$q_{str}$和$q_{sem}$，样本接受条件为：

$$q(D_c',G_c')=q_{fmt}\cdot q_{str}\cdot q_{sem}=1.$$

三层筛选区分可解析性、拓扑一致性和语义合理性。前两层不能证明标签语义正确，第三层也只是验证器判断，仍需人工抽检估计其误判。这里的“独立验证器”指单独验证调用，是否与增强模型使用不同权重、提示或训练数据须由实际配置说明。

#### 3.2.4 增强效果的可识别性与数据追踪

若一个以Claim为中心的增强单位包含一个Claim和$k$个Premise，接受$u$个同类变体后，两类实例数分别变为$N_C+u$和$N_P+ku$。当$u>0$时，Claim相对Premise的数量比提高，当且仅当$N_P>kN_C$。因此，保留局部拓扑并不自动改善类别平衡，应分别验证实例比例变化和表达多样性变化。该推导是对增强机制的分析，不是本稿新增的实验结果。

MajorClaim在不包含stance边的AAEC表示中可能形成单节点增强单位。这时只能声称增强了结论表达，不能声称保留了原本不存在的关系监督。局部子图文本若单独作为训练实例，需要说明输入上下文与测试时整篇输入的差异；若回填原文，则必须重新分词、更新所有受影响跨度及引用。两种路径不能在方法与实验之间混用。

待核验R02：需补充增强模型名称与版本、完整提示、每个种子子图的尝试数、三层筛选各自通过数、去重规则、原始与增强样本混合比例，以及局部文本回填方式。不得使用测试集标签调节筛选阈值。建议为每个增强样本保留源文档ID、源组件ID、生成配置、拒绝原因和坐标映射，以支持训练集去重与错误追踪。

### 3.3 面向结论组件的表示增强

#### 3.3.1 Claim-specific Adapter

本文在组件生成器的注意力投影层旁路注入低秩适配器。对基础权重$W_0$和隐藏状态$h_t$，结论分支的输出表示为：

$$h_t'=W_0h_t+g_t\frac{\alpha}{r}BAh_t,$$

式中为说明方便写作等输入输出维度$d$；一般投影的矩阵维度按第二章定义。原稿给出的参数为$r=16$、$\alpha=32$，$g_t\in\{0,1\}$表示生成状态门控。原稿将门控描述为依赖JSON状态和已经生成的标签前缀，不读取测试金标准标签。

待核验R03：这一描述尚不能确定可执行门控。如果类型值的首个token尚未生成，不能提前依据该类型是否为Claim决定门控；如果span字段先于type字段生成，后续类型分支也不能回溯改变已生成跨度。教师强制训练时也应避免把当前位置尚不可见的金标准类型作为推理时不可获得的门控信号。

因此，该分支目前只能作为需与代码对齐的条件适配设计，不能直接归因于“提前改善组件边界”或“减少Premise梯度覆盖”。确认时需给出字段顺序、首个类型token的处理、门控启停位置、基础LoRA与专项LoRA是否并存，以及相同参数预算下的全局LoRA对照。改变门控或字段顺序后必须重跑实验，不能沿用旧分数作为新实现的结果。

#### 3.3.2 Cue-aware Soft Prompting

显式篇章线索对结论识别有帮助，但线索词与组件类型并非一一对应。本文首先在输入中检测预定义线索，如“therefore”“thus”“in conclusion”等，再向输入表示附加$m=4$个可学习连续提示向量：

$$X'=[P_1,P_2,\dots,P_m;X],$$

其中$P_i\in\mathbb{R}^{d}$为可训练提示向量。线索检测仅控制提示分支是否启用，最终组件边界与类型仍由上下文模型联合判断，从而避免把词典匹配直接等同于结论标签。对于未出现显式线索的隐式结论，模型仍可依赖正文语义和辅助目标进行预测。

#### 3.3.3 多目标训练

主任务采用结构化序列生成损失：

$$\mathcal{L}_{gen}=-\sum_{t=1}^{T_y}\log P(y_t\mid D,y_{<t}).$$

为在编码阶段提供结论存在性监督，本文为每个句子增加二分类头。若句子包含MajorClaim或Claim，则标签$z_i=1$，否则为0：

$$\mathcal{L}_{sat}=-\sum_i[z_i\log \hat z_i+(1-z_i)\log(1-\hat z_i)].$$

联合目标为：

$$\mathcal{L}_{comp}=\mathcal{L}_{gen}+\lambda\mathcal{L}_{sat},\qquad \lambda=0.5.$$

辅助目标只参与训练，推理时不增加JSON字段。不过，对decoder-only骨干，“句子表示”仍需明确来自哪些输入token、哪一层以及何种池化；不能笼统称为额外编码器提供的表示。原稿的两个损失均写为求和形式，实际损失尺度随输出长度和句子数变化。实现若采用均值归一化，应同步修改公式并重新解释$\lambda=0.5$。

待核验R04：需补充句子切分、跨句组件的句子标签规则、分类头结构、池化方式、loss mask和归一化方式；Cue-aware分支需补充完整词典、大小写及短语匹配规则、提示插入位置和无显式线索样本的结果。这里不代填未提供的配置。

### 3.4 实验设置与结果分析

#### 3.4.1 设置与评价指标

实验采用Qwen2.5-7B-Instruct作为骨干模型，并使用LoRA进行参数高效微调。组件评价采用边界和类型同时精确匹配的F1；除整体Component-F1外，分别报告MajorClaim-F1和Claim-F1，以避免总体指标被高频类别主导。所有增强样本均由训练集产生，验证集用于模型选择和超参数确定，测试集仅用于最终评价。

表3-1暂作为原稿分类别结果记录保留，不能独立确认训练增强的净贡献：本表Single-Pass的Comp-F1为81.67，而第四章同名记录为77.82；本表Full的83.71又与第四章包含推理修正的Full相同。需根据run ID确认是否使用相同训练数据、检查点、推理预算和评价脚本，再决定拆表或更正名称。本稿不从两个冲突值中任选其一。

待核验R05：本表配置对应关系以及外部基线分类别分数来源未确定。

#### 3.4.2 主要结果

表3-1 AAEC组件分类别结果原稿记录

|方法|MajorClaim-F1|Claim-F1|Comp-F1|
|:---|:---|:---|:---|
|FLAN-T5 (XXL)|71.23|76.45|80.15|
|LLM Single-Pass|73.45|78.21|81.67|
|**Ours (Full)**|**77.34**|**81.77**|**83.71**|

按表内数值相减，Full相对本表Single-Pass的MajorClaim-F1、Claim-F1和Component-F1差值分别为3.89、3.56和2.04个F1点；相对FLAN-T5 (XXL)的整体差值为3.56个点。这些是算术差值，不是已完成配置控制的因果归因。当前没有Premise分类结果、组件Precision与Recall或错误混淆矩阵，不能据此排除对高频类别的损害，也不能把各类别F1与总体F1的差值直接解释为贡献比例。

#### 3.4.3 模块作用与解释边界

第四章的完整消融结果显示，移除Claim-specific Adapter后Component-F1下降1.75个点，移除Cue-aware Soft Prompting后下降1.37个点，移除辅助目标后下降0.82个点。由于各模块共享训练数据和生成器参数，消融差值反映的是“在其他模块保留条件下”的边际影响，不应将多个差值简单相加解释为总增益。

结构感知数据增强的独立效果还应同时结合合成样本通过率、人工抽检一致性和真实测试集性能判断。本文不以生成样本数量本身作为有效性证据，而以未参与增强的测试集表现作为主要依据。

### 3.5 误差类型与讨论

结论组件优化后仍存在三类典型错误。第一，隐式结论没有显式线索词，Cue-aware分支难以提供额外信息；第二，一个长句同时包含论据和结论时，模型容易扩大组件边界；第三，MajorClaim与Claim语义相近，模型可能在类型之间混淆。前两类错误需要更细粒度的边界建模，第三类错误则说明仅依赖局部语义不足，还需要结合文档级位置和段落结构。

本章方法以改善候选组件质量为目标；其净效果仍需消除表格配置冲突后验证。下一章进一步保留多个组件假设，并利用完整关系结构对候选进行重排序和局部修复，以分析仅改变训练阶段之外的恢复空间。

### 3.6 本章小结

本章围绕关键结论组件提出训练阶段优化方法。结构感知增强在保持局部图约束的条件下扩充训练样本，Claim-specific Adapter和Cue-aware Soft Prompting分别提供类型专项参数与篇章线索，多目标训练则增加结论存在性监督。原稿分类别记录呈现了正向差值，但尚需完成配置核验、增强独立消融和Premise性能检查，才能确认本章各机制对候选质量的具体贡献。

## 第四章 基于多候选评估与有界修正的论辩图生成方法

本章提出MCR-BR推理时结构恢复框架。其核心思想不是用规则替代模型预测，而是保留多个由模型生成的结构假设，以确定性约束和单独调用的语义验证信号选择初始图，再在有限预算内对局部异常进行可回退修复。完整流程包括候选组件生成、候选图构建、一致性评分、初始解选择、异常检测和有界修正六个阶段。

### 4.1 单次生成的错误传播与恢复目标

单次生成系统直接输出一个组件列表和关系列表。一旦组件被遗漏、边界偏移或编号错误，后续关系便可能出现悬空引用、孤立节点和错误连接。简单后处理可以删除非法边，却不能补回缺失组件；无约束Self-Refine又可能在修改错误部分的同时破坏原本正确的结构。

原稿记录的AAEC修正触发率为42.5%，修正前无效组件引用比例为18.5%，JSON格式错误比例为6.2%，验证器判定的不连贯边比例为22.4%。这些指标的分母可能分别是文档、引用或关系边，不能相加为总体错误率。触发率还依赖异常阈值，不等于经人工确认的错误文档比例。

相应恢复目标是改善可解析性与引用有效性、边级语义一致性和预设的连接覆盖偏好。覆盖不足并不必然是标注错误，未带显式理由的合法Claim也可能触发这一软偏好。

### 4.2 多候选组件生成与完整图构建

#### 4.2.1 候选组件集合

给定文档$D$，模型不立即提交单一结果，而是通过温度采样和提示改写生成$K$个组件候选集：

$$\mathcal{C}=\{C^{(1)},C^{(2)},\dots,C^{(K)}\}.$$

每个$C^{(k)}$包含组件跨度和类型。生成结果使用统一JSON Schema解析。原稿提出按模型置信度、跨度长度和文本位置消解重叠，但未给出排序优先级、置信度定义和并列处理规则，故目前尚不是可复现的确定性算法；待核验R06要求同时保存消解前后结果及端点重映射。候选的目的不是重复采样相同输出，而是保留在组件边界、类型或遗漏节点上存在差异的竞争假设。

#### 4.2.2 候选论辩图构建

对每个组件候选集$C^{(k)}$，关系模块在有效组件编号之间预测关系集合$R^{(k)}$，得到完整候选结构：

$$S_k=(C^{(k)},R^{(k)},G^{(k)}),\qquad G^{(k)}=(V^{(k)},E^{(k)}).$$

关系预测的目标是只引用$C^{(k)}$中存在的组件。若这一限制通过每一步解码的硬约束实施，且后处理不破坏映射，则该阶段不应再产生悬空ID；仅在提示中列出ID不构成同样的保证。原稿残余无效ID记录与约束阶段的关系须在日志中核对。AAEC关系标签为Support/Attack；CDCP域内实验保留Reason/Evidence；跨领域实验映射为有向Link。

以下流程整理原稿的模块关系，不代表新增实验或新增修复动作。

图4-1 MCR-BR候选选择与局部修正流程

```flow
原始文档
  ↓ 组件生成与规范化
K个组件候选
  ↓ 对每个候选预测关系
K个完整候选图
  ↓ 合法性检查与语义验证
候选评分与初始图选择
  ↓ 检测异常并尝试局部动作
接受或回退 → 终止判断 → 输出图
```

如果候选不能解析，则其节点、关系和语义分量无法直接定义。应记录为解析失败并执行实现明确规定的处置，不能把解析失败偷偷当作空图加入正常语义统计。

### 4.3 一致性引导的候选评分

综合评分函数定义为：

$$E(S_k)=\alpha E_{dens}(S_k)+\beta E_{coh}(S_k)+\gamma E_{val}(S_k),$$

其中$\alpha=0.4$、$\beta=0.4$、$\gamma=0.2$。三个分量均归一化到$[0,1]$，分别评价论证连接覆盖、边语义连贯性和输出合法性。其中覆盖分数只是对预测图的启发式偏好，不是相对于金标准的完整性度量。

#### 4.3.1 论证连接覆盖

令$\mathcal{Q}(S_k)$为根据预设规则从预测组件中选出的覆盖评价节点集合，不使用测试金标准确定该集合。在AAEC中不要求文档级MajorClaim具有关系入边。集合成员的具体选择规则需与实现一起公开；若按已有入边选择，就可能漏掉本应诊断的孤立节点。验证器对边$(i,j,r_{ij})$返回$p_{ij}\in\{0,1\}$，结论节点$v_j$的通过验证的入边数为：

$$d_{coh}^{in}(v_j)=\sum_{(i,j,r_{ij})\in R^{(k)}}p_{ij}.$$

论证连接覆盖得分为：

$$E_{dens}(S_k)=
\begin{cases}
\dfrac{1}{|\mathcal{Q}(S_k)|}\displaystyle\sum_{v_j\in\mathcal{Q}(S_k)}
\min\left(\dfrac{d_{coh}^{in}(v_j)}{\tau(t_j)},1\right), & |\mathcal{Q}(S_k)|>0,\\
0, & |\mathcal{Q}(S_k)|=0.
\end{cases}$$

其中$\tau(t_j)$是原稿设置的期望连接数；此处$t_j$应理解为节点结构角色，而非只含组件类别的$\tau_j$。原稿给出顶层关系结论节点取2、其他评价节点取1，但未给出角色识别和阈值选择记录，均需核验。此计数包含通过验证的Attack边，故称“论证连接”而非“支持证据数量”。它不测量前提的事实真实性，也不要求所有合法Claim必须至少有两条理由。

该分量是软偏好，不直接删除低入度节点。但它依赖预测的$\mathcal Q$，遗漏难以满足阈值的结论节点反而可能抬高平均分；因此高覆盖得分也可能与低组件召回并存。需用固定候选池比较移除该项后的F1、预测边数和孤立节点分布，检查其是否诱导过连边或过删节点。

#### 4.3.2 语义连贯性

对每条预测边，验证器结合源组件、目标组件、关系类型和上下文判断关系是否成立。语义连贯性得分为：

$$E_{coh}(S_k)=
\begin{cases}
\dfrac{1}{|R^{(k)}|}\displaystyle\sum_{(i,j,r_{ij})\in R^{(k)}}p_{ij}, & |R^{(k)}|>0,\\
0, & |R^{(k)}|=0.
\end{cases}$$

该得分与生成模型的序列概率不同：序列概率衡量输出在生成模型下是否常见，而$E_{coh}$专门判断边是否得到当前上下文支持。

#### 4.3.3 输出合法性

若候选通过全部确定性检查，则$E_{val}(S_k)=1$，否则为0。检查项目包括JSON可解析性、必需字段完整性、token跨度合法性、组件编号引用完整性、自环与结构环检测，以及数据集Schema允许的组件和关系类型。约束解码只能保证部分语法条件，无法替代跨度、引用和拓扑检查。

最终选择：

$$k^*=\arg\max_{1\leq k\leq K}E(S_k),\qquad S^{(0)}=S_{k^*}.$$

### 4.4 图约束下的有界局部修正

#### 4.4.1 异常表示与优先级

对当前图$S$，错误检测器返回异常集合：

$$\mathcal{E}(S)=\{e=(\nu,\eta,\sigma)\},$$

其中$\nu\in\{VAL,COH,DENS\}$表示有效性、连贯性或完整性异常，$\eta$表示受影响的节点或边，$\sigma\in[0,1]$表示严重度。严重度定义为：

$$\sigma(e)=
\begin{cases}
1, & \nu=VAL,\\
1-p_{ij}, & \nu=COH,\ \eta=(i,j),\\
1-\min\left(\dfrac{d_{coh}^{in}(v_j)}{\tau(t_j)},1\right), & \nu=DENS,\ \eta=j.
\end{cases}$$

异常按严重度降序排列，同分时采用$VAL\succ COH\succ DENS$。有效性错误和被验证器拒绝的边直接触发修复。原稿“低于$\delta_{dens}=1.0$”应针对节点覆盖值$\min(d_{coh}^{in}/\tau,1)$解释，相应严重度为$1$减覆盖值，不能反过来把低严重度解释为需要修正。待核验R07：阈值比较方向须与实际代码核对，本稿不据此认定旧实验已使用该解释。

#### 4.4.2 修复动作

BR定义四类局部动作：

1. **Promote/Demote**：在标注规范允许的结论类类型之间转换，例如MajorClaim与Claim；
2. **Replace**：从其他候选集中选择与问题位置对应的替代跨度或组件类型；
3. **RemoveEdge**：删除验证器拒绝且删除后不产生新引用错误的边；
4. **LocalRerun**：固定当前组件集合，仅对受影响源节点的关系进行约束重预测，目标编号限定在有效组件集合内。

对候选动作$a$，记执行后的结构为$a(S)$。接受条件为：

$$\operatorname{Accept}(a,S)=\mathbb{I}[a(S)\in\mathcal{G}_{\mathcal{A}}]\cdot
\mathbb{I}[E(a(S))\geq E(S)].$$

因此，每次被接受的动作产生的图满足规定合法性检查，且在评分可重复的前提下不降低该代理评分；不满足条件的动作回退。这是对被接受后状态的性质，不保证初始图合法，也不保证最终一定合法。

Replace在原稿中定义为替换已有位置的跨度或类型，并没有明确定义插入缺失节点。如果其实现不改变节点数量，不能据此声称找回所有遗漏Claim；LocalRerun固定组件集合，也不能补节点。Promote/Demote改变类型后须同步重查允许的边类型和拓扑，尤其不能把AAEC的stance隐式转换为关系边。待核验R08：四类动作需补充前置条件、受影响字段、坐标和ID更新规则及失败返回值。

#### 4.4.3 终止条件与计算预算

原稿设置最多执行$T=3$轮，每轮最多接受$M=2$个动作。以下为保留原语义的伪代码；GenerateActions需返回有限序列，模型调用需有超时或解码上限，否则仅靠外层预算不足以保证整个程序终止。

算法4-1 原稿有界修正流程及其接口要求

```text
输入：候选图集合 {S1,...,SK}，最大轮数 T，每轮动作预算 M
输出：修正后的论辩图 S

S ← argmax E(Sk)
for t = 1,...,T:
    errors ← DetectErrors(S)
    if errors 中不存在触发项:
        break
    accepted ← 0
    for e in SortBySeverity(errors):
        for a in GenerateActions(e, candidate_pool):
            S' ← a(S)
            if Valid(S') and E(S') ≥ E(S):
                S ← S'
                accepted ← accepted + 1
                break
        if accepted = M:
            break
    if accepted = 0:
        break
return S
```

算法在三种情况下退出外层迭代：不存在触发异常、当前动作空间中没有可接受修改、轮数预算耗尽。在动作生成有限且每次调用终止的前提下，总接受动作数不超过$TM=6$。这一界限不约束被拒绝的尝试次数，不能据此声称最多发生6次额外模型调用。

#### 4.4.4 代理目标与可恢复性分析

命题一：若验证器结果固定或缓存，评分函数固定，且每次仅接受$E(S')\geq E(S)$的动作，则被接受状态的评分序列单调不降。证明由接受条件逐次应用直接得到。若逐次重新随机调用验证器而不固定结果，同一图的分数也可能变化，因而这一命题的前提不再成立。由于评分范围有界，这一数值性质不意味着在有限时间达到全局最优，也不意味着Relation-F1单调提高；本文的停止依据仍是显式预算与有限动作空间。

命题二：软合法性加权不能保证初始选择合法。按原稿权重，一个非法图若覆盖与连贯性都为1，可得0.8；一个合法图若两项都为0.5，则得0.6。最大加权分可能选中非法图。这是由评分式构造的反例，不是实际测试样本。

命题三：全图合法后才接受的条件可能阻碍逐步修复。若初始图有两个独立无效引用，一次局部动作只修复其中一个，修改后的图仍不合法，因此被拒绝；即使两步组合能得到合法图，当前一步式接受规则也不一定能走到该状态。原稿同时报告残余无效ID，因此不能宣称BR保证最终输出全部合法。

上述分析说明，现有方法的可陈述保证是“有限前提下的步数界”和“固定代理评分下的接受状态非下降”，不是语义正确性或全局最优保证。附录B提出可行候选优先、非法状态处置和总调用预算的修订建议；这些建议需要实现并重新评测，不能回填为本章已有实验的生成过程。

### 4.5 实验设置

#### 4.5.1 数据集与指标

域内实验使用AAEC和CDCP。对任一预测对象集合，精确率、召回率和F1定义为：

$$P=\frac{TP}{TP+FP},\qquad R=\frac{TP}{TP+FN},\qquad F_1=\frac{2PR}{P+R}.$$

组件只有在起止边界和类型均与金标准一致时计为$TP$。关系只有在源组件、目标组件、方向和关系标签均正确时计为$TP$。AAEC报告Component-F1以及Support、Attack和总体Relation-F1；CDCP保留Reason和Evidence两类关系并分别报告F1。关系评价基于模型预测组件而非金标准组件，因此同时反映组件识别与关系预测错误；Oracle实验另行使用金标准组件估计关系模块上限。跨领域实验的粗粒度指标在第五章说明。

#### 4.5.2 基线与实现

外部基线包括FLAN T5-XXL、GPT-4-turbo 20-shot和RoBERTa-large多任务模型。为比较同骨干配置，原稿内部比较采用Qwen2.5-7B-Instruct及相同LoRA训练设置，包括Single-Pass、Constrained Decoding、DAG Post-process、Multi-Sample (LogProb)、Self-Refine、无修正的$K=1$版本和仅验证器重排序的$K=3$版本。原稿称优化器采用AdamW并使用早停，数据划分与评价脚本遵循文本到文本生成基线[6]<!--ref:kawarada2024--><!--anchor:section:4-->，但当前未提供配置文件与脚本，尚不能认定所有协议已经对齐。

待核验R09：需补齐数据版本及文档ID划分、输入按全文还是段落组织、分词及跨度转换、CDCP多片段前提的处理、训练步数和有效batch size、学习率、LoRA目标层、dropout、温度、top-p、提示版本、检查点选择、随机种子、运行次数与硬件。原稿各表的“±”暂按原样保留，其代表标准差、标准误还是置信区间尚不确定，不进行显著性判断。

待核验R10：下列外部FLAN T5-XXL的AAEC总体80.15/61.19、CDCP总体72.68/33.96，以及GPT-4-turbo的AAEC总体55.51/28.38可在Kawarada等的结果表找到；本稿未核实这些外部基线的分类别数值来源。RoBERTa及其他内部行也需绑定复现实验记录。相同骨干不等于相同预算，当前材料没有证实Self-Refine、多采样和MCR-BR已做到总token数或调用次数匹配。

### 4.6 域内主要结果

#### 4.6.1 AAEC结果

表4-1 AAEC域内结果原稿记录

|方法|Comp-F1|Support-F1|Attack-F1|Relation-F1|
|:---|---:|---:|---:|---:|
|FLAN T5-XXL|80.15|62.34|48.72|61.19|
|GPT-4-turbo 20-shot|55.51|29.86|18.45|28.38|
|RoBERTa-large MTL|76.43±0.55|54.21±0.52|41.83±0.67|52.15±0.54|
|LLM Single-Pass|77.82±0.51|58.43±0.45|44.21±0.62|56.87±0.48|
|LLM w/ Constrained Decoding|78.54±0.46|59.12±0.42|45.33±0.58|57.65±0.45|
|LLM w/ DAG Post-process|78.91±0.49|59.45±0.48|45.87±0.61|58.12±0.47|
|LLM Multi-Sample (LogProb)|79.45±0.38|60.12±0.41|46.58±0.55|58.94±0.42|
|LLM w/ Self-Refine|79.82±0.45|60.75±0.43|47.12±0.56|59.63±0.45|
|Ours ($K=1$, w/o correction)|81.24±0.44|61.87±0.39|48.34±0.58|60.73±0.41|
|Ours (Verifier-only Rerank, $K=3$)|82.18±0.40|63.15±0.36|49.82±0.52|62.21±0.38|
|**Ours (Full, $K=3$)**|**83.71±0.42**|**65.92±0.38**|**51.47±0.54**|**64.83±0.38**|

按表4-1记录，Full相对FLAN T5-XXL的Component-F1和Relation-F1差值分别为3.56和3.64个点，相对本表Single-Pass分别为5.89和7.96个点。约束解码、DAG后处理及Self-Refine各行也呈现正向差值，但在提示、训练设置和推理预算未核验前，不能把差异全部归因于BR，亦不能据此判断修复了哪一类节点或关系错误。

#### 4.6.2 CDCP结果

表4-2 CDCP域内结果原稿记录

|方法|Comp-F1|Reason-F1|Evidence-F1|Relation-F1|
|:---|---:|---:|---:|---:|
|FLAN T5-XXL|72.68|35.24|28.41|33.96|
|RoBERTa-large MTL|68.52±0.58|31.45±0.61|25.72±0.73|30.23±0.64|
|LLM Single-Pass|71.35±0.48|33.82±0.52|27.15±0.68|32.64±0.55|
|LLM w/ DAG Post-process|72.14±0.50|34.65±0.49|28.02±0.63|33.51±0.52|
|LLM w/ Self-Refine|72.95±0.47|35.58±0.48|28.94±0.60|34.42±0.50|
|Ours ($K=1$, w/o correction)|74.56±0.45|36.94±0.46|30.27±0.58|35.78±0.48|
|Ours (Verifier-only Rerank, $K=3$)|75.12±0.41|37.85±0.44|31.42±0.55|36.64±0.45|
|**Ours (Full, $K=3$)**|**76.45±0.43**|**39.12±0.45**|**32.86±0.57**|**38.17±0.46**|

按表4-2记录，CDCP上的Full Relation-F1比FLAN T5-XXL高4.21个点，为非AAEC语料上的适用性提供了待复核的结果。Evidence-F1低于Reason-F1，但该差异可能与样本数量、边界错误或标签判别等因素有关；没有类别计数及错误分解时，不能仅归因为证据型关系稀疏或语义隐含。

### 4.7 消融与机制分析

#### 4.7.1 模块消融

表4-3 模块消融原稿记录

|配置|Comp-F1|Relation-F1|$\Delta$Comp|$\Delta$Rel|
|:---|---:|---:|---:|---:|
|Full Method|83.71±0.42|64.83±0.38|—|—|
|$K=1$, w/o correction|81.24±0.44|60.73±0.41|-2.47|-4.10|
|w/o Claim-specific Adapter|81.96±0.48|63.08±0.44|-1.75|-1.75|
|w/o Cue-aware Prompting|82.34±0.45|62.87±0.40|-1.37|-1.96|
|w/o Multi-Objective|82.89±0.43|63.54±0.39|-0.82|-1.29|
|w/o Validity Signal $E_{val}$|81.56±0.46|61.92±0.43|-2.15|-2.91|

由$K=1$无修正记录到$K=3$仅重排序记录，Relation-F1差值为1.48个点，但同时改变候选数和选择过程，不能解释为重排序的单独贡献。由$K=3$仅重排序到Full的差值为2.62个点；只有在两者使用相同检查点、相同缓存候选池和相同评价脚本时，这才是对加入BR的有效对照。去除$E_{val}$的记录下降2.91个Relation-F1点，也需明确是仅移除评分项，还是同时移除了硬合法性检查。

训练模块消融反映其在其他模块保留时的条件差异，不能把各差值相加。本稿尚缺等样本量普通改写、无增强、无$E_{dens}$、无$E_{coh}$、逐动作移除和候选数—成本曲线等对照。因此当前表格没有完全分离增强、候选覆盖、选择器与修正操作的贡献。

#### 4.7.2 验证器替换分析

表4-4 验证器替换原稿记录

|验证器|Comp-F1|Relation-F1|Top-1一致率|修正触发率|
|:---|---:|---:|---:|---:|
|Qwen2.5-7B（默认）|83.71|64.83|100.0%|42.5%|
|Llama-3-8B（独立）|83.71|64.55|94.2%|43.8%|

按原稿记录，替换验证器后Relation-F1差值为-0.28个点，Top-1选择与默认验证器的一致率为94.2%。默认行100.0%是与自身比较的参照值，不是候选选择正确率；高模型间一致率也可能来自共同偏差，不能视为人工标注一致率。待核验R11：需说明一致率的分母、候选池是否固定、验证提示与解码配置，并以独立人工标注评估边判定的Precision、Recall及错误修改比例。

#### 4.7.3 Oracle上限

表4-5 Oracle条件结果原稿记录

|条件|Comp-F1|Relation-F1|$\Delta$Rel|
|:---|---:|---:|---:|
|预测组件与当前选择器|83.71±0.42|64.83±0.38|—|
|Candidate Oracle（$K=3$中择优）|85.12±0.36|67.24±0.34|+2.41|
|Condition Oracle（金标准组件输入）|—|78.42±0.35|+13.59|
|Output Oracle（金标准替换）|100.00|83.35±0.32|+18.52|

按表4-5记录，Candidate Oracle相对当前选择器的Relation-F1差值为2.41个点，Condition Oracle差值为13.59个点。前者只是给定候选池及Oracle选择准则下的经验诊断，不是整个任务的理论上限。后者同时改变关系模块的输入条件，可能引入分布变化，不能把13.59个点直接当作组件错误可被某一训练模块消除的量。

待核验R12：Candidate Oracle需说明逐文档优化哪个指标、如何处理并列以及先选择后汇总的口径。Output Oracle必须明确金标准替换的是组件、关系还是全部图：若只替换组件且保留预测关系，Relation-F1可以低于100；若全部输出均替换为同一金标准，则表中83.35不符合该定义。定义澄清前不用于量化某类误差贡献。

#### 4.7.4 修正行为统计

表4-6 修正行为原稿记录

|指标|结果|
|:---|---:|
|修正触发率|42.5%|
|触发文档平均迭代轮数|1.8|
|触发文档平均动作数|2.4|
|LocalRerun占比|45.2%|
|RemoveEdge占比|24.8%|
|Replace占比|19.5%|
|Promote/Demote占比|10.5%|
|无效ID比例|18.5% → 2.1%|
|JSON格式错误比例|6.2% → 0.0%|
|不连贯边比例|22.4% → 5.8%|
|整体$E_{val}$通过率|75.3% → 97.9%|

平均轮数和动作数只描述原稿记录下的运行行为，不足以证明多数真实错误已被修复。LocalRerun的使用占比最高，也可能由动作生成顺序或触发策略决定，不能直接作为错误类别分布。RemoveEdge的收益必须结合关系Precision与Recall判断，以避免通过过度删边取得表面合法性。

待核验R13：需逐项声明分母及前后阶段，例如触发率按全部测试文档计算，动作占比按尝试还是接受动作计算，无效ID按引用还是文档计算。不连贯边比例来自验证器自身判断，与人工语义正确率不同；前后预测边数可能变化，应同时报告数量及比例。原稿75.3%到97.9%的合法率变化也需与6.2%的JSON错误、18.5%的无效ID进行同阶段核对。

### 4.8 误差分析与局限

根据动作定义，删除错误边和在固定组件集上重预测关系属于可尝试的恢复情形；实际成功率需由逐例前后图与金标准证明。原稿没有提供可定位的真实案例，因此本稿不把概括性描述当作成功案例。尤其“从候选池找回遗漏Claim”需要插入或联合替换机制，现有Replace定义不足以保证该能力。

潜在失败情形包括所有候选均遗漏隐式组件、局部判断无法发现多跳矛盾、验证器错误拒绝有效边或接受表面相关边。这些是需检验的失效假设，不是已完成标注的误差占比。真实案例应同时展示原文、金标准、初始图、触发异常、每步动作、代理评分以及最终任务匹配结果，并纳入错误修改案例。

MCR-BR还带来额外推理成本。$K=3$候选和逐边验证增加了并行计算量，局部修复则引入顺序解码。现有$T=3$和$M=2$仅限制轮数与接受动作数，尚未给出最坏调用成本上界。若有$A_{try}$次动作尝试，每次还可能涉及多个边验证调用，实际开销取决于候选边数、验证批处理和缓存策略。应测量生成与验证的调用次数、输入输出token、端到端平均及P95时延、峰值显存，并在相同硬件上与Single-Pass比较。当前没有这些记录，不能定量宣称效率改善或成本已严格受控。

### 4.9 本章小结

本章提出完整的MCR-BR结构恢复流程。多候选生成避免过早提交单一组件集合，多维评分将结构和语义信号用于候选选择，有界修正则把检测到的异常转化为局部、可回退的修改动作。现有域内结果、消融、验证器替换与Oracle记录呈现了值得进一步验证的趋势；本章同时指出软合法性选择、非法初始图恢复和调用预算的限制。各模块的独立贡献及预算匹配优势仍需通过可复现实验建立。

## 第五章 粗粒度标签协议下的跨语料迁移分析

本章检验第三、四章方法在训练域与测试域不一致时的表现。跨领域实验不作为独立算法创新，而作为对结构恢复框架适用范围的补充验证。为避免不同标签体系造成不可比较结果，本文首先定义粗粒度组件映射和无标签连接协议，再分析零样本迁移结果及其局限。

### 5.1 跨领域异构性

AAEC与CDCP的差异至少包括三个层面。第一，AAEC由学生说服性作文构成，CDCP来自电子政务评论，文本长度、篇章组织和语言风格不同。第二，AAEC使用MajorClaim、Claim和Premise三级组件体系，CDCP使用Fact、Testimony、Value、Policy和Reference功能类型。第三，AAEC关系为Support/Attack并额外包含Claim stance，CDCP关系为Reason/Evidence且允许多父节点。因此，直接比较细粒度类型F1或关系标签F1会同时混入领域变化和标注规范变化。

### 5.2 粗粒度标签与关系映射

组件映射函数$\phi:\mathcal{T}_{src}\cup\mathcal{T}_{tgt}\rightarrow\{Claim,Premise\}$定义如下：

表5-1 跨语料组件标签归约

|数据集原标签|粗粒度标签|映射依据|
|:---|:---|:---|
|AAEC MajorClaim|Claim|表达全文立场|
|AAEC Claim|Claim|表达局部结论|
|AAEC Premise|Premise|提供支撑或反驳理由|
|CDCP Policy|Claim|提出行动方案或规范性主张|
|CDCP Value|Claim|表达评价性或价值判断|
|CDCP Fact|Premise|提供可核验事实|
|CDCP Testimony|Premise|提供经验或证言|
|CDCP Reference|Premise|提供外部来源|

关系映射函数$\psi$将AAEC的Support/Attack和CDCP的Reason/Evidence统一为有向Link：

$$\psi(r)=Link,\qquad r\neq None.$$

该协议保留组件角色的粗粒度差异和关系方向，但主动舍弃支持/攻击、理由/证据等细粒度语义。因此，Unlabeled Link-F1只能说明模型能否迁移“哪些组件应连接及连接方向”，不能证明细粒度关系分类已经实现跨域泛化。

### 5.3 零样本迁移协议

本章协议要求在AAEC训练集上拟合模型，并仅使用AAEC验证集选择检查点和超参数；迁移到CDCP时不使用目标域标注样本更新参数或选择阈值。原稿是否完全遵循该数据使用边界，仍需配置和日志核验。测试前仅提供目标域标签定义及上述映射规则，候选数、评分权重、完整性阈值和修正预算均沿用源域设置。评价采用：

1. **Coarse Component-F1**：组件边界正确且映射后的Claim/Premise类型正确；
2. **Unlabeled Link-F1**：源节点、目标节点和方向均正确，不区分Reason与Evidence。

该设置把目标域适配限制在Schema说明和确定性映射层面，避免使用目标测试集调节评分阈值。所有指标基于预测组件计算，从而保留真实端到端难度。

### 5.4 跨领域迁移结果

表5-2 AAEC到CDCP迁移结果原稿记录

|方法|Coarse Component-F1|Unlabeled Link-F1|
|:---|---:|---:|
|FLAN T5-XXL（zero-shot）|52.34±0.65|31.25±0.72|
|LLM Single-Pass（zero-shot）|54.87±0.58|33.42±0.68|
|Ours ($K=1$, w/o correction, zero-shot)|57.23±0.52|38.76±0.61|
|**Ours (Full, zero-shot)**|**60.78±0.48**|**43.21±0.55**|

按表5-2记录，Full相对FLAN T5-XXL的Coarse Component-F1和Unlabeled Link-F1差值分别为8.44和11.96个点，相对同骨干Single-Pass分别为5.91和9.79个点。两个指标的增幅不能直接用于错误归因；在未提供目标域错误分解时，不能断言收益主要来自连接碎片化或无效引用的减少。

43.21的Link-F1与第四章AAEC域内64.83的Relation-F1使用不同标签口径，不能直接相减估计领域退化。要分离领域差异，应在源域与目标域都重新使用同一粗粒度组件映射、端点匹配和有向无标签连接脚本。本章目前只比较同一目标协议下各方法的记录。

待核验R14：需确认模型在迁移时输出源标签、目标标签还是粗标签，映射发生在生成前还是评价前；同时说明Link端点匹配是否包含粗类型。提供Schema定义不等于使用标注示例，但若使用目标域示例、开发标签或按目标测试表现调阈值，就不再满足本章声明的零样本协议。

### 5.5 泛化来源与有效性威胁

框架可能从三个方面改善迁移。其一，多候选组件集合保留了目标域中不确定的边界和类型假设；其二，跨度、引用和无环性检查不依赖具体主题；其三，局部重预测比整图重新生成更少破坏已经正确的目标域结构。不过，当前证据仍受到以下限制：

1. 仅验证AAEC到CDCP单一迁移方向，尚不能覆盖医学、法律或多语言场景；
2. Policy/Value到Claim、Fact/Testimony/Reference到Premise是基于功能角色的启发式归约，会损失部分语义；
3. Unlabeled Link-F1不评价细粒度关系类型；
4. 目标域模型可能受公开数据预训练污染影响；
5. 验证器与生成器可能共享相似的预训练偏差。

因此，本章将跨领域结果定位为适用性证据，而不是对通用领域泛化能力的最终证明。后续可通过增加AbstRCT等目标域、开展双向迁移和比较多种标签对齐策略，进一步检验结论的稳定性。

### 5.6 本章小结

本章在明确标签映射和无标签连接评价范围的基础上，完成AAEC到CDCP的零样本迁移验证。原稿记录中MCR-BR的组件和连接指标高于列出的零样本基线，但该结论仅限同一映射和同一目标评价协议，且仍需核验数据使用边界。标签归约、单向迁移和预训练污染风险限制了对跨领域泛化的进一步解释。

## 第六章 总结与展望

### 6.1 工作总结

本文研究生成式端到端论辩挖掘中组件候选不足与推理阶段结构错误相互影响的问题。围绕训练和推理两个阶段，形成了结论组件增强与MCR-BR图级恢复两项相互衔接的方法设计。

训练阶段以结论节点及其局部邻域为增强单位，通过格式、结构和语义筛选控制合成样本，并结合条件低秩适配、线索感知提示与辅助目标强化结论表示。本文进一步分析了保留局部拓扑不必然改善类别比例，以及组件召回对可达关系集合的限制。该部分的研究价值应通过实际类别统计、独立增强消融和可复现门控实现验证，不能仅由完整系统的最终分数替代。

推理阶段保留多个组件假设并构建完整候选图，通过连接覆盖、边级语义与合法性信号进行选择，再执行异常驱动的局部修改。本文明确了评分非下降与真实F1提升的区别，并给出软合法性选择和非法初始状态修复的反例。现有算法在有限动作生成和调用终止的前提下具有接受步数上界，但没有由此自动得到模型调用总量上界或最终图必然合法的保证。

原稿域内表格记录的Full结果为AAEC Component-F1 83.71、Relation-F1 64.83，以及CDCP Component-F1 76.45、Relation-F1 38.17。跨语料记录在规定的粗粒度与无标签连接协议下为60.78和43.21。这些数值在本稿中原样保留，不作为本轮独立复现的结果；配置冲突、基线来源和重复运行统计仍需核验。

综合而言，本文可论证的研究主线是：结论组件质量影响关系恢复的候选空间，图级结构信号可用于候选选择与局部修改，而这两类机制的有效性必须在统一协议、明确实现和预算匹配的条件下检验。本文不将既有技术的组合名称视为创新证据，也不把有限语料上的正向记录外推为普遍适用结论。

### 6.2 当前不足与后续研究

首先，实验可追溯性尚不完整。应优先绑定每张结果表与实际运行配置，解决第三章和第四章同名方法的分数差异，补齐评价脚本、数据划分、重复次数及“±”含义。这些工作属于现有结论的验证前提，不应全部放入长期展望。

其次，训练增强的独立贡献尚未分离。后续应在等训练预算下比较无增强、普通改写和结构感知增强，报告类别数量、筛选通过率、人工抽检及Premise表现；条件适配器需在训练与推理可用信息一致的实现下重新核验。

再次，图级修正需要同时控制错误修改与计算成本。除当前接受动作预算外，应定义被拒绝尝试的上限、验证缓存和失败返回策略。评价时应包含原本正确对象被破坏的比例，以及性能—时延—token开销的对照，避免只以代理分数或合法率衡量修正收益。

最后，跨语料证据只覆盖一种归约和一个方向。双向迁移、更多目标语料、不同映射策略以及预训练污染审计可以检验结论的稳定性。在完成这些验证之前，中文、多语言及长篇专业文本仍属于待研究范围。



## 参考文献

[1] LAWRENCE J, REED C. Argument mining: A survey[J]. Computational Linguistics, 2019, 45(4): 765–818. DOI: 10.1162/coli_a_00364. [来源](https://aclanthology.org/J19-4006/)

[2] STAB C, GUREVYCH I. Parsing argumentation structures in persuasive essays[J]. Computational Linguistics, 2017, 43(3): 619–659. DOI: 10.1162/COLI_a_00295. [来源](https://aclanthology.org/J17-3005/)

[3] PARK J, CARDIE C. A corpus of eRulemaking user comments for measuring evaluability of arguments[C]//Proceedings of the Eleventh International Conference on Language Resources and Evaluation. Miyazaki: European Language Resources Association, 2018. [来源](https://aclanthology.org/L18-1257/)

[4] EGER S, DAXENBERGER J, GUREVYCH I. Neural end-to-end learning for computational argumentation mining[C]//Proceedings of the 55th Annual Meeting of the Association for Computational Linguistics, Volume 1. Vancouver: Association for Computational Linguistics, 2017: 11–22. DOI: 10.18653/v1/P17-1002. [来源](https://aclanthology.org/P17-1002/)

[5] MORIO G, OZAKI H, MORISHITA T, et al. Towards better non-tree argument mining: Proposition-level biaffine parsing with task-specific parameterization[C]//Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics. Association for Computational Linguistics, 2020: 3259–3266. DOI: 10.18653/v1/2020.acl-main.298. [来源](https://aclanthology.org/2020.acl-main.298/)

[6] KAWARADA M, HIRAO T, UCHIDA W, et al. Argument mining as a text-to-text generation task[C]//Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics, Volume 1. St. Julian’s: Association for Computational Linguistics, 2024: 2002–2014. DOI: 10.18653/v1/2024.eacl-long.121. [来源](https://aclanthology.org/2024.eacl-long.121/)

[7] SUN Y, CHEN G, YANG C, et al. Discourse structure-aware prefix for generation-based end-to-end argumentation mining[C]//Findings of the Association for Computational Linguistics: ACL 2024. Bangkok: Association for Computational Linguistics, 2024: 11597–11613. DOI: 10.18653/v1/2024.findings-acl.689. [来源](https://aclanthology.org/2024.findings-acl.689/)

[8] LI H, SCHLEGEL V, SUN Y, et al. Large language models in argument mining: A survey[EB/OL]. arXiv:2506.16383v6, 2025[2026-09-13]. DOI: 10.48550/arXiv.2506.16383. [来源](https://arxiv.org/abs/2506.16383v6)

[9] ZHAO X, WANG K, PENG W. ORCHID: A Chinese debate corpus for target-independent stance detection and argumentative dialogue summarization[C]//Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing. Singapore: Association for Computational Linguistics, 2023: 9358–9375. DOI: 10.18653/v1/2023.emnlp-main.582. [来源](https://aclanthology.org/2023.emnlp-main.582/)

[10] CHENG L, BING L, HE R, et al. IAM: A comprehensive and large-scale dataset for integrated argument mining tasks[C]//Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics, Volume 1. Dublin: Association for Computational Linguistics, 2022: 2277–2287. DOI: 10.18653/v1/2022.acl-long.162. [来源](https://aclanthology.org/2022.acl-long.162/)

[11] DING B, QIN C, ZHAO R, et al. Data augmentation using LLMs: Data perspectives, learning paradigms and challenges[C]//Findings of the Association for Computational Linguistics: ACL 2024. Bangkok: Association for Computational Linguistics, 2024: 1679–1705. DOI: 10.18653/v1/2024.findings-acl.97. [来源](https://aclanthology.org/2024.findings-acl.97/)

[12] EVURU C K, GHOSH S, KUMAR S, et al. CoDa: Constrained generation based data augmentation for low-resource NLP[C]//Findings of the Association for Computational Linguistics: NAACL 2024. Mexico City: Association for Computational Linguistics, 2024: 3754–3769. DOI: 10.18653/v1/2024.findings-naacl.238. [来源](https://aclanthology.org/2024.findings-naacl.238/)

[13] PEI Y, BHUSE P, LIU Z, et al. SegMix: A simple structure-aware data augmentation method[EB/OL]. arXiv:2311.09505v1, 2023[2026-09-13]. DOI: 10.48550/arXiv.2311.09505. [来源](https://arxiv.org/abs/2311.09505v1)

[14] GENG S, JOSIFOSKI M, PEYRARD M, et al. Grammar-constrained decoding for structured NLP tasks without finetuning[C]//Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing. Singapore: Association for Computational Linguistics, 2023: 10932–10952. DOI: 10.18653/v1/2023.emnlp-main.674. [来源](https://aclanthology.org/2023.emnlp-main.674/)

[15] MADAAN A, TANDON N, GUPTA P, et al. Self-Refine: Iterative refinement with self-feedback[EB/OL]. arXiv:2303.17651v2, 2023[2026-09-13]. DOI: 10.48550/arXiv.2303.17651. [来源](https://arxiv.org/abs/2303.17651v2)

[16] HUANG J, CHEN X, MISHRA S, et al. Large language models cannot self-correct reasoning yet[EB/OL]. arXiv:2310.01798v2, 2024[2026-09-13]. DOI: 10.48550/arXiv.2310.01798. [来源](https://arxiv.org/abs/2310.01798v2)

[17] WANG X, WEI J, SCHUURMANS D, et al. Self-consistency improves chain of thought reasoning in language models[EB/OL]. arXiv:2203.11171v4, 2023[2026-09-13]. DOI: 10.48550/arXiv.2203.11171. [来源](https://arxiv.org/abs/2203.11171v4)

[18] VASWANI A, SHAZEER N, PARMAR N, et al. Attention is all you need[EB/OL]. arXiv:1706.03762, 2017[2026-09-13]. DOI: 10.48550/arXiv.1706.03762. [来源](https://arxiv.org/abs/1706.03762)

[19] QWEN TEAM. Qwen2.5 technical report[EB/OL]. arXiv:2412.15115, 2024[2026-09-13]. DOI: 10.48550/arXiv.2412.15115. [来源](https://arxiv.org/abs/2412.15115)

[20] HU E J, SHEN Y, WALLIS P, et al. LoRA: Low-rank adaptation of large language models[EB/OL]. arXiv:2106.09685, 2021[2026-09-13]. DOI: 10.48550/arXiv.2106.09685. [来源](https://arxiv.org/abs/2106.09685)

[21] LESTER B, AL-RFOU R, CONSTANT N. The power of scale for parameter-efficient prompt tuning[C]//Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing. Association for Computational Linguistics, 2021: 3045–3059. DOI: 10.18653/v1/2021.emnlp-main.243. [来源](https://aclanthology.org/2021.emnlp-main.243/)

## 附录A 复现与证据核验清单

本附录保留工作稿中的未决事项。每项应以配置、日志、数据清单或实验结果解决，不能只删去标记。

表A-1 待核验事项及最低交付证据

|编号|位置与事项|所需证据|
|:---|:---|:---|
|R01|3.1 类别分布|固定训练划分的类型计数、跨度长度及增强前后IR|
|R02|3.2 增强流程|模型与提示版本、生成及筛选计数、数据混合和跨度回填实现|
|R03|3.3 门控因果性|字段顺序、首token处理、训练与推理门控轨迹、参数预算|
|R04|3.3 提示与辅助目标|词典、插入位置、句子池化、损失mask及归一化|
|R05|3.4 结果配置冲突|81.67与77.82、两处83.71各自对应的run ID|
|R06|4.2 候选规范化|重叠消解规则、置信度与ID重映射、解析失败记录|
|R07|4.3至4.4 评分与触发|评价节点选择、结构角色判定、阈值与比较方向|
|R08|4.4 动作可执行性|前置条件、字段修改、组件插入是否存在、回退记录|
|R09|4.5 实验配置|划分ID、评价脚本、超参数、种子、重复数、硬件及统计量定义|
|R10|4.5 基线与预算|外部分类型来源、内部复现日志、相同预算比较|
|R11|4.7 验证器|提示、模型版本、固定候选池和人工边级评价|
|R12|4.7 Oracle|选择指标、替换对象、端点匹配及汇总顺序|
|R13|4.7 行为统计|统计分母、生成阶段、前后数量和尝试或接受动作定义|
|R14|5.3至5.4 迁移协议|输出标签空间、目标数据使用记录和统一评价脚本|

最小补实验顺序为：先复现同一Single-Pass和Full配置，再在固定候选池上比较序列概率、验证器评分和BR；其后完成增强独立消融、合法性与语义评分消融、等计算预算对比。验证器人工评价和跨域扩展应在评价脚本稳定后开展，以免重复标注和重跑。

## 附录B 算法修订建议

本附录仅给出针对第四章逻辑缺口的可实验建议，未声明已经实现，也未使用原稿分数验证这些建议。

### B.1 合法候选优先与失败处理

可先对可解析候选执行确定性检查，在存在合法候选时仅对合法子集按语义与覆盖分数排序。若所有候选均不合法，应返回显式失败状态，或进入单独定义的合法化阶段，而不是继续宣称输出有硬合法性保证。保守删除和重新生成会改变召回与计算预算，必须作为独立配置评测。

### B.2 非法状态下的阶段性修复

若允许从非法图逐步恢复，可定义有限的违规计数并使用词典序目标，先降低确定性违规，再在合法集合内优化代理分数。该策略改变了当前“修改后全图立即合法”的接受条件，因此需要新的终止与回退说明。也可以把能够一起消除相关错误的操作定义为原子事务，但不应把任意多次修改包装为一次动作从而规避预算统计。

### B.3 节点补回与总调用预算

若希望补回遗漏Claim，应显式定义Insert或联合替换动作，说明新跨度来自哪个候选、如何消解重叠、如何更新ID以及哪些边需要重预测。若不增加该动作，则应保留当前方法不能一般性补回缺失节点的限制。

总预算可分别设置为最大动作尝试数、最大生成调用数、最大验证调用数和最大输出token数，并将所有被拒绝操作计入预算。具体数值应根据验证集上的性能—成本曲线确定，本稿不代填。新增预算策略后，需要重新报告与基线在等预算下的结果。

### B.4 建议的可复现实验记录

每个测试文档可记录文档ID、检查点与提示哈希、候选原始输出、规范化结果、各分量评分、选中候选、触发异常、每次动作尝试与回退原因、调用及token消耗、最终预测。该记录有助于核验评分是否因验证器随机性变化，以及代理目标改善是否真正对应任务F1改善。

## 附录C 修订与辅助工具使用说明

0913版使用academic-research-suite的论文修订与引用核查流程，基于原稿和审阅意见进行编辑。辅助工作包括措辞修改、结构调整、公开文献元数据与相关论述核查、公式和指标一致性检查，以及Word排版；未运行训练实验，未生成人工标注结果，未代替作者确认研究事实。作者应逐项审阅修改，核对引用、实现和实验数据，并按学校及学院适用要求确认是否以及如何披露辅助工具使用。

原稿列出的作者阶段性成果及其发表状态尚缺可核验材料，本稿不将其认定为虚假，也不继续作“已发表”陈述。后续可依据论文首页、录用通知或出版社记录补充成果页。
