# 面向关系感知学习与依赖闭合修正的端到端论辩挖掘方法研究

武汉大学计算机科学与技术学术型硕士学位论文

作者：Chen Tang

1007-v2结构与文字修订稿　2026年10月7日　含预期数值占位，非实测，勿送审

英文题目　End-to-End Argument Mining via Relation-Aware Learning and Dependency-Closed Repair

## 摘要

端到端论辩挖掘从原始文本中识别论辩组件及其关系，为分析观点与理由之间的组织方式提供结构化表示。组件与关系之间的依赖贯穿训练和推理过程：训练文本的局部改写可能改变原有论证作用，使继承标注失真；预测组件的跨度或类型发生变化，也会使关联关系的端点失效。围绕这两类问题，本文在前期结论组件专项建模、多候选重排序与有界修正研究基础上，分别研究训练阶段的关系监督保持与推理阶段的结构恢复。

针对局部改写后的监督保持问题，提出面向结论组件的关系感知增强学习方法。该方法按组件端点依赖确定改写的关系影响域，同时检查集合内部与跨边界组合的已有关系及无关系状态。通过标注迁移建立原文与增强文的对应，在筛选合格的文本对上联合学习组件和关系因素，使增强数据构造与生成模型的学习目标相衔接。

针对组件修改后的结构恢复问题，提出多候选驱动的依赖闭合论辩图修正方法。该方法保持输入原文不变，将组件集合替换及全部受影响关系的重建组织为一个事务，依据完整对象评分、整图约束和编辑预算整体接受或回退。集合替换可表示遗漏补回、多检删除、边界与类型调整以及拆分合并；固定评分下的局部效用分析与有界执行明确了决策和停止条件。

本文以AAEC与CDCP为验证对象，保留CDCP原生多前提关系，通过独立方法对照、训练与推理组合、误改风险及计算成本分析区分两项研究的作用。前期成果用于说明研究基础，新增方法的验证框架已明确。当前版本所列P后缀数值均为人工占位，尚不构成新增方法的实测结论；方法性质也不保证真实抽取F1提高。

关键词：端到端论辩挖掘；关系感知增强；结论组件；依赖闭合；图修正；代价敏感评分

## Abstract

End-to-end argument mining identifies argumentative components and their relations directly from raw text. Dependencies between components and relations create two related problems. During training, a local paraphrase may alter the argumentative role of a component and invalidate inherited labels. During inference, changing a predicted span or type may invalidate the endpoints of associated relations. Building on prior work on conclusion-specific modeling, multi-candidate reranking, and bounded repair, this thesis studies supervision preservation during training and structural recovery during inference.

The first method is relation-aware augmentation learning for conclusion components. It defines an affected relation domain from component dependencies and checks both annotated relations and no-relation states within and across the editable set. Annotation transfer establishes correspondences between original and augmented documents. Paired component and relation learning then connects accepted text variations to the shared generation representation.

The second method is dependency-closed argument graph repair driven by multiple candidates. It leaves the input text unchanged and combines compatible component-set replacement with reconstruction of all affected relations. Each proposed transaction is accepted or rolled back as a whole under complete-object scores, global structural constraints, and explicit editing budgets. Set replacement represents insertion, deletion, span or type changes, splitting, and merging. Conditional analysis characterizes local utility differences and bounded execution without guaranteeing improvement in true extraction F1.

The evaluation framework uses AAEC and CDCP, retaining CDCP multi-premise relations as native hyperedges. Independent comparisons, a training-by-inference factorial design, harmful-edit analysis, and cost measurements separate the two methods and their combined effects. Prior results establish the research basis. Values marked with a P suffix in this revision are manually specified placeholders, not measurements; empirical conclusions for the new methods remain pending.

Keywords: End-to-End Argument Mining; Relation-Aware Augmentation; Conclusion Components; Dependency Closure; Graph Repair; Cost-Sensitive Scoring

## 第一章 绪论

### 1.1 研究背景与问题提出

论辩挖掘研究文本中的主张、理由及其连接方式。与仅判断作者赞成或反对某一议题相比，该任务还需要定位论证内容，并识别不同组件之间的支持或攻击关系，从而将自然语言论述转化为可分析的结构[1]<!--ref:lawrence2019--><!--anchor:section:Abstract-->。组件与关系抽取服务于论证结构分析，但抽取准确并不直接证明论证有效或事实真实。

图1-1以一个人为构造的图书馆片段说明任务输入与输出。原文中的“增加图书馆经费”和“延长开放时间”表达两个观点，“图书馆现有座位不足，而且开放时间偏短”提供相关理由。论辩挖掘需要共同确定这些文字的范围、论辩角色及连接关系。若只识别出观点而遗漏理由，或把完整理由截成一部分，关系预测所依赖的端点也会随之改变。

![原文到组件与关系的论辩挖掘示意](_revision_1007_v2/figures/argument_example.png)

图1-1 原始文本中的组件与关系示意

该例为便于说明而构造，不是AAEC或CDCP的标注样本，也不作为实验效果证据。本文后续沿用这一片段解释关系影响域和组件替换，使任务、训练与推理三个层面的讨论具有一致的直观参照。

生成式建模将组件和关系编码为同一输出序列，使多个子任务共享上下文[7]<!--ref:kawarada2024--><!--anchor:section:4-->。共享表示并未消除输出对象之间的依赖。当组件跨度没有进入候选集合时，以该组件为端点的关系就无法严格匹配；当组件存在而显示编号错误时，则可能通过确定性检查修复引用。候选遗漏、语义判断错误与编码不一致具有不同成因，需要分别处理。

训练数据增强也受到同一依赖关系的约束。将上述理由改写为“图书馆座位不够用”，可能仍然支持增加经费，却不再说明延长开放时间的必要性。如果直接继承原关系标注，增强样本就会引入监督噪声。仅检查改写集合内部的关系还不够，连接到集合外组件的关系以及原先无关系的端点组合也可能发生变化。

推理阶段的输入原文保持不变，但模型可能漏掉“延长开放时间”，或仅抽取理由的一部分。补回组件、扩展边界或调整类型之后，关联关系必须依据新的端点对象重新判断。本文据此形成两项互补研究：训练阶段保持文本改写后的关系监督，推理阶段恢复预测修改后的依赖结构。两项研究以真实文本上的严格组件和关系评价为共同依据，并分别考察收益、失败情形与计算代价。

### 1.2 国内外研究现状

相关研究从组件识别逐步扩展到联合结构预测，并形成生成建模、数据增强和预测后修正等路线。本文按这些机制组织综述，重点关注输入是否包含金标组件、关系依赖如何进入模型，以及修改后如何判定结构质量。AAEC和CDCP的任务表示及评价规则统一在第二章说明。

#### 1.2.1 端到端论辩挖掘与生成建模

组件与关系的联合预测是端到端论辩挖掘的基础。Stab和Gurevych围绕说服性作文建立组件与关系分析方法[2]<!--ref:stab2017--><!--anchor:section:3-->；Eger等将组件识别与论证结构预测纳入神经端到端学习框架[4]<!--ref:eger2017--><!--anchor:section:Abstract-->；Morio等通过双仿射解析和任务特定参数化支持非树状结构预测[5]<!--ref:morio2020--><!--anchor:section:Abstract-->。这些工作使组件识别、关系判断和结构约束能够在统一任务中研究，同时提示不同语料不能一律按树结构处理。

生成式方法进一步统一了多个子任务的输出接口。Kawarada等将论辩挖掘表述为文本到文本生成，是本文的直接生成式基线[7]<!--ref:kawarada2024--><!--anchor:section:4-->。Cabessa等把组件分类、关系识别和关系分类组织为生成任务，其方法基于已有组件列表展开，评价范围与从原始文本定位跨度的设定不同[8]<!--ref:cabessa2025--><!--anchor:section:2.2-->。AASP则以受约束的预定义动作逐步构建论辩结构，将结构信息引入自回归生成过程[9]<!--ref:das2025aasp--><!--anchor:section:Abstract-->。本文依据该工作的2025年公开预印本讨论其机制。

结构与语义信号为生成提供了更具体的条件。DENIM使用篇章结构感知前缀辅助端到端预测[12]<!--ref:sun2024--><!--anchor:section:Abstract-->；Das等以关联组件间的关键短语表达概念联系[13]<!--ref:das2025key--><!--anchor:section:3-->；FOL-AM利用一阶逻辑规则组织关系查询和多跳推理[14]<!--ref:sun2025fol--><!--anchor:section:1-->。后两项工作以已分割组件为前提，适合用于比较关系语义建模思想，不能直接把分类分数视为严格整图抽取成绩。

组件边界仍是生成系统中的重要误差来源。Caputo等在2026年采用成对标签进行细粒度组件分割，并分析自动分割对后续分类的影响[6]<!--ref:caputo2026acs--><!--anchor:section:Abstract-->。同年的ARGUS系统整合组件分割、组件分类、关系识别与分类，并连接符号求解器开展论辩框架分析[10]<!--ref:caputo2026argus--><!--anchor:section:Abstract-->。结合LLM论辩挖掘综述所讨论的任务和评价差异[11]<!--ref:li2025--><!--anchor:section:Abstract-->，本文将研究重点落在可独立检验的监督保持与结构恢复机制，而非模型规模或生成式接口本身。

#### 1.2.2 关系保持数据增强

数据增强通过改变表达扩充监督，但生成内容与原标签之间的对应需要单独检查[15]<!--ref:ding2024--><!--anchor:section:Abstract-->。CoDa从训练实例提取生成约束[16]<!--ref:evuru2024--><!--anchor:section:Abstract-->，SegMix在任务相关片段上进行结构感知混合[17]<!--ref:pei2023--><!--anchor:section:Abstract-->。这些方法表明，增强的作用不仅取决于样本数量，也取决于生成条件和标签可靠性。

论辩挖掘中的直接近邻是质量导向合成QOS。该方法将上下文和组件组织为槽位化输入，在改写后恢复跨度并继承组件类型及关系标注；其方法节说明，论辩关系并未显式提供给生成模型，而依赖语义保持使原关系继续成立[35]<!--ref:bao2025qos--><!--anchor:section:4.1-->。本文沿用局部改写与标注恢复这一研究基础，进一步关注改写的关系影响范围：同时考察集合内部、跨边界的合法端点组合，以及已有关系和无关系状态。

关系抽取研究为这种质量控制提供了相邻思路。ConsistRE以关系条件和上下文约束组织细粒度生成[38]<!--ref:zheng2024--><!--anchor:section:Abstract-->，CovEReD通过反事实实体替换研究文档级关系预测的一致性[37]<!--ref:modarressi2024--><!--anchor:section:Abstract-->，ODDA关注低资源条件下增强样本的质量与多样性[39]<!--ref:zhong2025--><!--anchor:section:Abstract-->。Wang等将LLM生成样本用于联合实体关系抽取，结合一致性正则化、伪标签与迭代反馈[36]<!--ref:wang2026ssl--><!--anchor:section:Abstract-->。对后一工作的认识限于出版方摘要和方法摘录，未核实的细节不用于排除性比较。

增强还可能改变模型对表面线索的依赖。话语标记补全的效果因语料而异[40]<!--ref:rocha2025--><!--anchor:section:1-->，弱监督论辩挖掘也需要处理组件边界和关系噪声[18]<!--ref:sun2026weak--><!--anchor:section:Abstract-->。因此，本文同时评价标签漂移、表达多样性、接受覆盖和训练成本，并在同一批增强样本上比较不同学习目标，以区分数据构造与成对监督的作用。“保持”是生成和审核目标，其语义可靠性仍需真实审计与任务评价支持。

#### 1.2.3 结构化预测与论辩图修正

结构化预测可以在生成时施加约束，也可以在生成后选择和修正候选。语法约束解码通过限制后继token控制输出形式[19]<!--ref:geng2023--><!--anchor:section:Abstract-->，AASP则把结构动作约束纳入生成过程[9]<!--ref:das2025aasp--><!--anchor:section:Abstract-->。这类约束保证的是已编码的规则，跨度是否准确、关系是否成立还需要依据文本与标注评价。

生成后修订和多候选聚合提供了另一类接口。Self-Refine利用反馈迭代修订输出[20]<!--ref:madaan2023--><!--anchor:section:Abstract-->，自一致性通过采样多条路径聚合答案[22]<!--ref:wang2022--><!--anchor:section:Abstract-->。在缺乏外部反馈的推理设置中，自纠错也可能无效或降低表现[21]<!--ref:huang2023--><!--anchor:section:Abstract-->。论辩分析中的LLM-refine生成不同Claim、Evidence和Warrant组合，再选择分割结果[23]<!--ref:tran2025--><!--anchor:section:4.2-->。上述研究支持对候选与判断过程分别分析，而不是默认更多修订必然带来收益。

对象与关系的联合处理也存在直接近邻。Re-Cent以关系标签引导跨度对抽取，并通过关系与跨度对之间的相关性实施修正[43]<!--ref:li2025recent--><!--anchor:section:Abstract-->。Pirozelli等的论辩重构流程提供组件合并、重写和关系检查步骤，其允许改写组件表述，区别于原文字面跨度抽取[44]<!--ref:pirozelli2026--><!--anchor:section:3-->。Xiao和Li的ARGUS研究则把LLM自解释转为抽象论辩框架，以形式语义定义最小代价修复目标[24]<!--ref:xiao2026repair--><!--anchor:section:Abstract-->；它与前述同名论辩挖掘系统不是同一工作，修复目标也不同于本文的抽取对象效用。

本文的直接基础是作者参与完成的ICIC 2026多候选重排序与有界修正方法MCR-BR[34]<!--ref:tang2026icic--><!--anchor:section:4.1-4.4-->。原方法已包含候选跨度替换、类型调整和关系修改。本文进一步把兼容组件集合替换及全部受影响关系的重建作为完整事务，显式规定评分、约束、预算和回退，重点研究修改之间的依赖如何进入决策。

评价目标为上述设计划定了边界。F1的最优决策一般不能由单个对象的边际概率直接替代[41]<!--ref:waegeman2014--><!--anchor:section:4-5-->，校准概率与最优F1阈值的关系也依赖特定条件[42]<!--ref:lipton2014--><!--anchor:section:4-->。概率校准用于检查置信度与经验正确率的对应[45]<!--ref:guo2017--><!--anchor:section:Abstract-->。本文据此区分对象概率、代价敏感效用和严格抽取F1，以同候选、同评分的比较检验事务机制，并独立报告错误接受与计算成本。

#### 1.2.4 综合评述与本文研究位置

不同语料的任务表示和训练来源会影响方法比较。MT-AM利用辅助论辩语料开展多任务训练[25]<!--ref:morio2022--><!--anchor:section:Abstract-->；AMELIA统一19个数据集的格式，并比较单任务、多任务及模型合并策略[26]<!--ref:savigny2026amelia--><!--anchor:section:Abstract-->。句子级泛化研究还观察到模型对数据集相关词汇线索的依赖[27]<!--ref:feger2025--><!--anchor:section:Abstract-->。本文将跨语料分析作为适用范围检验，区分多任务训练、单源零样本迁移和目标域校准，不把这些设定合并为一种“泛化”成绩。

表1-1从方法机制而非异口径分数比较最接近的研究。相关工作已经建立了结构保持增强、多候选选择及对象修正的基础；本文的研究位置在于两种依赖处理：改写前后监督对应的维护，以及组件变化后关联关系的完整重建。前者通过近邻增强、匹配中心和同数据学习消融评价，后者通过同候选同评分的动作比较及结构化全局解码评价。

表1-1 近邻方法与本文研究位置

|研究|任务或输入条件|相关机制|本文比较重点|
|:---|:---|:---|:---|
|QOS[35]<!--ref:bao2025qos--><!--anchor:section:4.1-->|论辩标注文本的槽位化增强|改写后恢复跨度并继承类型及关系|内部与跨边界关系、NONE检查及资源匹配|
|ConsistRE与CovEReD[38]<!--ref:zheng2024--><!--anchor:section:Abstract-->[37]<!--ref:modarressi2024--><!--anchor:section:Abstract-->|关系抽取及文档级关系预测|关系条件生成或反事实一致性|论辩角色依赖与组件关系成对学习|
|AASP[9]<!--ref:das2025aasp--><!--anchor:section:Abstract-->|自回归论辩结构生成|受约束动作构建结构|生成过程约束与生成后事务决策的区别|
|Re-Cent[43]<!--ref:li2025recent--><!--anchor:section:Abstract-->|联合实体关系抽取|关系引导跨度对抽取与修正|组件集合修改的依赖域与整体接受条件|
|前期MCR-BR[34]<!--ref:tang2026icic--><!--anchor:section:4.1-4.4-->|从原文生成多个完整论辩图|整图重排序及有界组件关系修改|集合替换、完整关系重建与风险成本归因|

表中的机制依据本章已说明的材料范围归纳，不表示各方法使用相同数据、输入或评价协议，也不据未核实信息断言其缺少某一细节。本文主实验限定为英文AAEC和CDCP，其他语言与任务资源的范围说明见附录A.3。

### 1.3 研究问题与主要研究工作

组件与关系之间的依赖是两项研究的共同出发点。训练阶段改变文本表达而保持经过检查的图监督，推理阶段保持原文而修改预测图。图1-2概括二者的研究关系；它表示问题与方法的对应，不表示将测试预测重新当作训练金标。

![两项研究的共同问题与分工](_revision_1007_v2/figures/research_relationship.png)

图1-2 组件关系依赖下的两项研究内容

#### 1.3.1 研究问题

RQ1：在继承结论组件专项建模的基础上，检查改写集合内部及跨边界的端点组合，并同时保持已有关系和NONE状态，能否提高增强样本的监督可靠性？在同一批增强数据上，成对图因素学习能否进一步改善原始测试文本的严格抽取质量？两问分别检验数据构造与学习目标的作用。

RQ2：在固定初始图、候选对象和评分器的条件下，组件集合替换与关系依赖闭合能否恢复顺序局部修正难以处理的组件关系错误，并取得可接受的误改风险与计算成本？候选覆盖、评分可靠性与预算内搜索分别构成恢复能力的限制，需要独立诊断。

训练与推理的组合实验用于分析两项方法的互补性，跨语料实验用于说明适用边界，均不另列为第三项算法创新。

#### 1.3.2 主要研究内容

（1）面向结论组件的关系感知增强学习。针对局部改写可能使继承标注失真的问题，按端点关联定义关系影响域，同时检查集合内部、跨边界组合的正关系与NONE。通过标注迁移建立原文和增强文的对应，并在共享生成表示上学习对应组件与关系因素。该研究把增强数据构造与学习目标连接起来，在实验中分别识别约束范围、中心选择及成对监督的作用。

（2）多候选驱动的依赖闭合论辩图修正。针对组件变化会使关联关系失效、逐项修改难以完整评价影响的问题，以兼容组件集合替换统一表示补回、删除、边界与类型调整及拆分合并，同步重建全部受影响关系。候选事务在固定完整对象评分、整图约束和预算下整体接受或回退。代价敏感效用提供可核算的决策依据，局部整数规划用于求解预算内的关系补全。

两项方法共享任务表示，但优化对象不同。训练辅助头只用于学习阶段，推理评分器以完整预测对象的正确性为目标；推理评分不向生成器回传梯度。相应实验在各自固定条件下验证独立作用，再分析组合表现。

#### 1.3.3 前期成果与本论文的关系

本文以前期论文Improving End-to-End Argument Mining with LLMs via Multi-Candidate Reranking and Bounded Repair为基础，作者为Chen Tang、Min Peng和Gang Tian，官方公开记录归于ICIC 2026 Posters Volume I[34]<!--ref:tang2026icic--><!--anchor:section:4.1-4.4-->。表1-2区分已公开机制与本论文深化内容，已有模块作为研究基础保留，其结果仍归于原配置。

表1-2 前期成果与本论文深化内容

|研究层次|ICIC已公开机制|本论文深化内容|结果归属|
|:---|:---|:---|:---|
|训练与表示|结论专项适配、线索提示、句子辅助监督|关系影响域约束增强及成对因素学习|原表支持前期训练配置|
|候选生成与选择|多候选组件、关系构建、整图重排序|保留初始图接口，建立固定候选空间|候选质量与后续决策分别分析|
|组件及关系修正|类型调整、候选跨度替换、删边与局部重预测|兼容集合替换、完整依赖重建与事务接受|新增机制采用独立实验|
|评分与评价|覆盖、语义、合法性混合评分及非下降接受|完整对象正确性、计数效用与风险分析|新效用及原生超边评价单独报告|

原方法已经能够修改组件类型和候选跨度，本文的增量集中在集合级修改、依赖完整性及决策依据。LoRA、提示、辅助头和散度函数分别是继承基础或实现手段，不单独计为原创贡献。共同成果与个人分工的说明保留在附录C，最终成果页需依据正式材料由作者核准。

### 1.4 论文组织结构

第一章介绍研究背景、相关工作与两项研究的关系。第二章统一任务表示、评价口径、公共实验协议和训练推理接口。第三章围绕关系感知增强学习，依次说明前期基础、影响域、标注迁移、成对学习及训练侧实验。第四章围绕依赖闭合修正，说明候选、事务、评分、求解及推理侧实验。第五章分析两阶段组合、整体成本和跨语料适用性。第六章总结方法与局限，并讨论后续研究方向。

附录补充复现协议、执行记录、成果说明、前期诊断、历史数值和符号索引。各方法章中的占位数值均保留明确标记，不作为实验结论。
