"""Versioned deterministic content edits; no Word/PDF or page rendering."""
from pathlib import Path
import json,re,hashlib,difflib
W=Path(__file__).resolve().parent;R=W.parent
BASE=R/'report_1011_v11_full.md';DEST=R/'report_1011_v12_content.md'
old=BASE.read_text();text=old;ops=[]
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def segment(a,b,source=None):
 s=text if source is None else source;return s[s.index(a):s.index(b,s.index(a))]
def replace(a,b):
 global text
 assert text.count(a)==1,(a[:100],text.count(a));ops.append({'kind':'replace','old_sha256':sha(a),'new_sha256':sha(b),'old_chars':len(a),'new_chars':len(b),'anchor':a[:110]});text=text.replace(a,b)
def block(a,b,new):replace(segment(a,b),new.rstrip()+'\n\n')
def before(a,new):replace(a,new.rstrip()+'\n\n'+a)
def f(v,n=2):return f'{v:.{n}f}'
def tbl(title,heads,rows):return title+'\n\n|'+'|'.join(heads)+'|\n|'+'|'.join([':---']*len(heads))+'|\n'+'\n'.join('|'+'|'.join(map(str,r))+'|' for r in rows)+'\n\n'
S=read(W/'simulation/results.json');M=S['metrics']['strict_native'];P=S['paired']['strict_native'];C=S['metrics']['icic_compatible_target'];L=S['labels']
V=read(R/'research_1011_v12/casimedicos/evaluation/metrics.json')
def metric(ds,m,obj='relation',protocol='strict_native'):
 z=S['metrics'][protocol][ds][m][obj];return f(z['mean'])+'±'+f(z['sd'])
def four(m):return [metric(ds,m,obj) for ds in ['AAEC','CDCP'] for obj in ['component','relation']]
def delta(ds,a,b,obj='relation'):return M[ds][a][obj]['mean']-M[ds][b][obj]['mean']
def ci(ds,a,b,obj='relation'):
 z=P[ds][a+'__'+b+'__'+obj];return f(z['delta']), '['+f(z['ci95'][0])+', '+f(z['ci95'][1])+']'

# Front matter: focused thesis abstract, explicit identity once up front.
block('1011-v11 估算演示版','英文题目', '''1011-v12 内容迭代预览　2026年10月11日

稿件说明：主结果为“在ICIC基础上获得增益”的正向模拟情景，按人工对象身份及整数计数重新生成；它展示研究目标成立时的报告方式，不是模型实测成绩或经校准的效果预测。ICIC公开值、兼容旧协议的目标情景和严格原生对象情景分别列出。真实Luna实验另表报告，本轮增加CasiMedicos的逐项评分及最终输出，保留有益和不利观察。全文主实验集中AAEC、CDCP，CasiMedicos仅作补充诊断。本版聚焦内容，未制作Word/PDF或进行分页渲染。''')
block('## 摘要','## Abstract',f'''## 摘要

端到端论辩挖掘需要从原始文本中同时识别组件、论辩角色及有向关系。组件与关系之间的依赖使局部改写和预测修正都可能产生连锁变化：训练侧需要确定哪些原有监督可以可靠继承，推理侧需要在端点改变后重新评价相关关系。本文以ICIC多候选重排序与有界修正为基础，研究可靠对应因素上的成对学习，以及依赖闭合的结构修复。

训练方法利用关系影响域记录受改写影响的因素，通过组件检查和因素级掩码建立原文与变体的可信对应。未经确认的变体关系不进入辅助监督或对齐，原始金标保持不变；默认只对原文计算完整图生成损失。完整影响域整例筛选作为可选对照，以区分增加审核与利用可靠监督的价值。

推理方法分别解析组件和关系，保留有效成分，并依据原生任务提出有限候选；CDCP以完整联合源作为关系对象。固定评分显式区分“未评分”和“低分”，候选修改在依赖闭合、整图约束和预算内统一接受或回退。小规模候选可采用全局选择，大规模候选可采用有界局部事务；集合动作与单对象动作分别比较，不预设更复杂的搜索必然更有效。

主实验围绕ICIC继承配置、仅新训练、仅新修正及二者结合展开。严格原生对象模拟中，完整框架在AAEC与CDCP上的组件F1为{metric('AAEC','t1_i1','component')}、{metric('CDCP','t1_i1','component')}，关系F1为{metric('AAEC','t1_i1')}、{metric('CDCP','t1_i1')}；相对同口径模拟继承基线的关系增量为{f(delta('AAEC','t1_i1','t0_i0'))}、{f(delta('CDCP','t1_i1','t0_i0'))}个百分点。真实开发诊断表明，候选入池、完整对象评分和最终选择应分别验证。新增CasiMedicos评分将8篇诊断样本的关系F1由0提升至3.81，但仍有66条错误关系，局部和全局修正未再产生增量。本文据此限定方法的适用条件，正式训练收益与跨语料有效性仍需目标模型的受控实验检验。

关键词：端到端论辩挖掘；可靠对应；成对学习；依赖闭合；图修正；结构化预测''')
block('## Abstract','## 第一章',f'''## Abstract

End-to-end argument mining identifies components, argumentative roles, and directed relations from raw text. Their dependencies create two related challenges: determining which labels remain reliable after a training paraphrase, and reassessing affected relations after a predicted endpoint changes. Building on ICIC multi-candidate reranking and bounded repair, this thesis studies paired learning over reliable correspondences and dependency-closed structural repair.

The training method uses an affected relation domain to locate supervision that may change. Component checks and factor masks identify usable correspondences between original and augmented texts. Unconfirmed augmented relations receive neither auxiliary supervision nor alignment loss, while original gold labels remain intact. Full-graph generation supervision is applied to the original text by default. Whole-view filtering over the complete domain remains an optional comparison.

The inference method parses components and relations separately, preserves valid components, and constructs bounded native candidates, including complete joint-source relations for CDCP. Fixed scores distinguish missing assessments from low confidence. Changes are accepted or rolled back under dependency closure, global constraints, and explicit budgets. Global selection and bounded local transactions are alternative solvers; single-object and set-level actions are evaluated separately.

The main numerical preview is an explicitly constructed positive scenario anchored to an ICIC-derived baseline. Under the strict native-object scenario, complete-system relation F1 is {metric('AAEC','t1_i1')} on AAEC and {metric('CDCP','t1_i1')} on CDCP, exceeding the corresponding simulated baseline by {f(delta('AAEC','t1_i1','t0_i0'))} and {f(delta('CDCP','t1_i1','t0_i0'))} points. These values are authoring assumptions, not measured model results or calibrated forecasts. A separate genuine CasiMedicos diagnostic improves relation F1 from zero to 3.81 on eight reused documents, but produces 66 false relations and no additional repair gain. The evidence motivates separate checks of candidate coverage, exact-object scoring, and final decisions; target-model training gains and generalization remain to be established empirically.

Keywords: End-to-End Argument Mining; Reliable Correspondence; Paired Learning; Dependency Closure; Graph Repair; Structured Prediction''')

# Problem framing and inheritance.
block('#### 1.3.1 研究问题','#### 1.3.3 前期成果', '''#### 1.3.1 研究问题

RQ1：在局部改写后，怎样识别可用于学习的组件与关系对应？在相同来源、变体规模和更新预算下，因素级辅助监督与成对学习分别提供多大增量？完整筛选是否值得其额外拒绝和审核成本，由单独对照回答。

RQ2：在候选和评分充分时，怎样完整处理组件修改的关系依赖，并控制误改与计算成本？单对象、集合动作以及局部、全局求解分别在什么规模和预算下适用？有限候选之外的遗漏不归因于搜索器。

两阶段四格比较用于识别相对ICIC继承配置的条件增量；对象成员分析用于解释重叠、独有恢复和新增损失。它们不另列为第三项算法创新。

#### 1.3.2 主要研究内容

（1）可靠对应因素上的关系感知成对学习。保留关系影响域和完整标注输运，通过逐因素状态区分通过、变化、原标签分歧和未审核。原文承担完整图生成监督；变体只在有效组件及可靠关系上提供辅助监督与分布对齐，避免将未知监督当作已经保持。完整影响域整例筛选作为可选数据策略，与默认因素掩码分别比较。

（2）候选质量与评分约束下的依赖闭合修正。将成分提案、原生类型及源组表示作为输入条件，把组件变化及全部受影响关系重建组织为统一事务。通过缺失分数保护、开发侧风险选择及全局或局部求解，分别控制不可评价的修改、误改代价与计算开销。依赖闭合是共同语义；集合动作和局部搜索是可替换实现。

候选接口与评分训练用于落实这两项研究，不额外包装为独立创新。训练辅助头与推理评分器的监督对象和使用阶段保持区分。''')
replace('原方法已经能够修改组件类型和候选跨度，本文的增量集中在集合级修改、依赖完整性及决策依据。','原方法已经能够修改组件类型和候选跨度，本文的增量集中在可靠因素上的学习以及修改后的依赖完整性和决策依据；集合动作是否有额外收益需单独验证。')
block('### 1.4 论文组织结构','## 第二章', '''### 1.4 论文组织结构

第一章明确两项研究问题及与ICIC的继承关系。第二章区分原生严格评价、历史协议目标及公共配置。第三章给出可靠因素筛选、标注对应和学习目标。第四章依次说明候选、评分、依赖闭合及求解选择，并集中报告真实推理诊断。第五章以ICIC继承基线组织四格及对象分析。第六章总结适用条件与实证替换顺序。附录保存坐标、配置、性质、历史结果及本版模拟来源，使开发诊断与论文主结果保持可追踪的对应。''')
before('### 2.6 公共实验协议', '''#### 2.5.1 与ICIC的双协议比较

ICIC公开表为历史来源值，不视为本次复现。继承关系需要两条评价轨：其一核对原始划分、跨度、类型、stance及CDCP关系转换后，按原协议复跑ICIC与新系统；其二将双方输出接入本稿严格原生评价器，CDCP必须匹配完整联合源。当前旧协议尚未完成端到端复现，兼容轨仅给出目标情景，不能宣称已经实现可逆映射。

因此，本稿将ICIC引用值、旧协议尺度的目标模拟、严格原生对象模拟分表报告。两套人工情景采用独立对象身份，不是同一图的投影；两个协议之间不计算提升或配对显著性。正式替换时使用共同文档和实际预测运行各自评价器，才能进行同口径系统比较。''')
replace('|评分评价对象|每语料组件2400、关系4800个完整对象|用于表4-6的固定提案评价，不是全部训练对象数|','|评分验证|训练侧OOF完整对象；自然候选分布|本版Casi诊断另有166组件、6390关系，不能替代目标模型校准|')
replace('|损失权重|增强1，头监督1，组件／关系对齐各0.5|预览固定；正式备选0.25／0.5／1仅在训练侧选择|','|损失权重|原文生成1；头监督1；组件／关系对齐各0.5|默认不对未完整审核变体计算整图生成损失|')
replace('|硬件与资源|假设1张A100 80GB、64GiB RAM、4 CPU线程|未实际分配；预检槽位上限500万，评分批4096|','|硬件与资源|假设1张A100 80GB、64GiB RAM、4 CPU线程|未实际分配；有限提案，预检槽位50000，评分批4096|')
replace('预览中生成、增强、验证与编码统一指定Qwen2.5-7B-Instruct，跨度与评分头结构见表2-3；$\\rho$、$\\lambda_{sup}$、$\\lambda_C$、$\\lambda_R$分别设为1、1、0.5、0.5；这些是预览假设。','预览中生成、增强、验证与编码统一指定Qwen2.5-7B-Instruct，跨度与评分头结构见表2-3；原文生成、头监督、组件对齐及关系对齐的权重分别设为1、1、0.5、0.5。增强视图默认不承担完整图生成损失；这些是预览假设。')
replace('配套preview_config.json及config_validation.json分别保存参数与静态校验；没有执行Qwen训练或宣称配置已在目标设备生效。','配套v12 preview_config.json保存更新后的设计参数；静态读取不等于训练入口验收。本版没有执行Qwen训练或宣称配置已在目标设备生效。')

# Reliable-factor method, with losses that do not teach unchecked augmented edges.
block('### 3.1 引言','### 3.2 前期专项', '''### 3.1 引言

增强的价值取决于可用于学习的监督，而不只取决于生成多少文本。局部改写可能影响内部关系和连接到只读组件的关系，但“可能发生”并不说明漂移普遍存在，也不直接证明完整筛选必要。现有64个Luna变体尚未检出关系标签变化，提示应将额外筛选收益与学习目标分开研究。

本章保留关系影响域与标注输运，重点转向可靠对应因素上的学习。默认先检查组件意义和角色，再对受检关系记录原标签是否认可、改写后是否保持及是否待定；未确认的变体因素不参加辅助监督和对齐。原文始终保留全部金标与生成目标，避免以审核分歧重写数据集。完整影响域整例筛选作为替代策略，而非所有训练必须通过的前提。

默认结论中心仅用于选择改写区域，不改变原生类型；其增量由匹配随机中心检验。前期专项适配、提示和句子监督提供共同起点，新增贡献由固定数据及固定推理策略的对照识别。''')
replace('若槽位重叠、完整输入超过冻结上下文上限，或影响域无法在单次审核资源内完整处理，则跳过该文档增强并记录具体原因，不删除源成员或改选其他中心。','若槽位重叠或完整输入超过冻结上下文上限，则跳过该文档增强并记录原因，不删除源成员或改选中心。默认因素掩码版本仅审核声明的有限子集；完整筛选版本在完整影响域无法处理时跳过，二者分别登记审核覆盖。')
block('#### 3.3.3 接受规则与来源控制','### 3.4 成对组件',r'''#### 3.3.3 接受规则与可靠因素

所有版本先检查格式、槽位身份、坐标往返和完整端点引用，再在全文上下文中检查改写组件的含义、角色、指代、否定与模态。格式失效或确认改变组件含义时拒绝整个变体；组件意义待定时也不接纳该变体。原始文档和金标不因模型判断而删除。

通过组件检查后，默认采用因素掩码。关系审核子集 $J_A\subseteq\mathcal D_A$ 包含全部受影响正关系，并按固定哈希最多抽取内部、跨边界NONE各4项；已知CDCP联合源的单成员不机械记作负例。正关系无法在资源内全部核查时，本次变体不进入关系学习，但通过检查的组件仍可提供组件级监督。未审核的NONE不被当作已经稳定。

验证器分别判断原文因素和改写因素。仅当原标注获认可、改写后状态仍一致、完整端点对应有效时，令 $m_R(\omega)=1$；原标签分歧、变化或待定均令其为0。组件同样保存 $m_C(c)$；关系掩码为1还要求全部端点的组件掩码为1。判定来自固定模型，故“可靠”表示通过声明的检查，不是人工金标准语义保证。

默认策略不因某个关系未通过而丢掉所有有效组件，也不把该关系改为NONE。变体保存完整输运图以供追踪，但只有掩码为1的标签参与增强侧损失。完整筛选对照则检查声明影响域的全部因素，任一变化或待定即拒绝整例，其余生成和训练资源按共同规则登记。若完整筛选损失源覆盖却未改善学习，采用因素掩码即可。

每篇最多四次尝试、最多两个接受视图；记录模型、提示、原始判断、掩码、对应、拒绝原因及全部成本。原文和变体按源文档共同分组。v11 Luna比较的“成分＋内部正”与“完整影响域”是既存诊断配置；本节因素掩码为v12待验证设计，不将旧结果写成该设计已经完成训练。

验证时先不给出待判断因素的正确答案，取得分类后再与原标签比较；当前实际Luna记录使用显式待审标签，属于提示不同的开发诊断，不能作为此盲分类规约的验收。独立上下文或参数分离都不能保证审核误差独立。''')
replace('对于一个通过筛选的视图 $x\'$，组件对齐为','对通过组件检查的视图 $x\'$，以下公式中的 $A^+$ 进一步与 $\{c:m_C(c)=1\}$ 取交集，组件对齐为')
replace('将影响域划分为正关系组 $D_+$ 和 NONE 组 $D_0$，','将通过检查的集合 $\{\omega\in J_A:m_R(\omega)=1\}$ 划分为正关系组 $D_+$ 和 NONE 组 $D_0$，')
replace(r'当 $\mathcal D_A=\varnothing$ 时，该项置零并跳过空域关系检查，不人为添加关系；全文其他关系的生成监督仍保留。','当可靠关系集合为空时，该项置零，不人为添加关系；原文全部关系的生成监督仍保留。')
replace('低 JS 可能来自两个视图一起预测错误，故每个视图同时接受金标监督。组件头交叉熵在该视图全部组件上取平均，关系头交叉熵在声明因素宇宙的正关系与 NONE 非空组之间分别归一化；二者相加记作 $S(x,G)$。空组件或空因素部分分别置零。金标锚定用于限制退化一致性，不构成排除全部退化解的数学保证。','低JS可能来自两个视图一起预测错误，故同时保留标签锚定。原文辅助监督 $S(x,G)$ 使用全部原生组件及声明因素；变体辅助监督 $S_m(x\',\phi(G))$ 仅对掩码为1的组件和关系归一化。正关系与NONE按非空组分别平均，空组置零。未审核关系既不作为正例，也不作为NONE负例；金标锚定仍不构成排除全部退化解的保证。')
block('#### 3.4.3 按源文档归一化及梯度接口','### 3.5 算法及性质',r'''#### 3.4.3 按源文档归一化及梯度接口

设源文档 $d$ 接受 $m_d$ 个视图。原文承担完整图生成及继承句子监督；增强文只作为输入视图，不将含未审核关系的输运图作为完整生成答案。头监督定义为

$$
L_{heads,d}^{sup}=\frac{S(x_d,G_d)+\sum_{j=1}^{m_d}S_{m_j}(x'_{dj},\phi_j(G_d))}{1+m_d}.
$$

成对项先在每个非空因素组内平均，再按同源接受视图平均。总损失为

$$
L_d=L_{ICIC}(x_d,G_d)+\lambda_{sup}L_{heads,d}^{sup}
+\lambda_C\bar L_{C,d}^{align}+\lambda_R\bar L_{R,d}^{align}.
$$

默认 $\lambda_{sup}=1$、$\lambda_C=\lambda_R=0.5$。无变体时只保留原文对应项；有变体但无可靠关系时，关系对齐置零，组件学习仍可进行。批内按源文档平均，梯度累积末批按实际文档数归一化，不把接受变体多的源文档自动赋予更高权重。

两个视图均保留梯度。生成和句子损失更新继承模块，组件与关系头及成对项通过输入表示更新全局LoRA；类型前缀门控的结论专项分支只由相应生成路径更新。基础权重冻结，辅助头在评价时移除。推理评分器另行训练，不使用这些辅助头的类别概率冒充完整对象正确率。

全文改写后所有标签都被确认的额外版本可以计算增强图生成损失，但须独立命名并控制更新量。本版默认不采用该版本，以免将未审核监督重新从生成目标引入。此修改针对监督使用边界，并不声称已经提高真实泛化效果。''')
replace('16        检查 D_A 中全部关系状态','16        按固定 J_A 复核原／新状态，建立可靠因素掩码 m_R')
replace('18      if 任一受检标签漂移或其他筛选条件失败 then','18      if 组件含义变化／待定、结构失败，或完整筛选版本任一因素失败 then')
replace('22      将通过的全文视图、φ(G_d)、φ 和来源加入 Views_d','22      将全文视图、φ(G_d)、φ、可靠因素掩码和来源加入 Views_d')
replace('28    依可见前缀门控，计算各视图的生成损失和句子辅助损失','28    依可见前缀门控，仅计算原文完整生成损失及继承句子监督')
replace('29    从回答开始前的输入表示计算组件头与关系状态头监督','29    从输入表示计算原文全部头监督及变体掩码内的头监督')
replace('30    依 φ 计算非空域成对损失；无变体或空域的对齐项置零','30    依 φ 计算可靠因素上的成对损失；无变体或空可靠域时置零')

# Diagrams with changed semantics remain readable as code-native diagrams.
replace('![关系感知增强学习的共享表示与梯度接口](_revision_1010_v7/figures/training_architecture.png)', '''```mermaid
flowchart LR
  O[原文与金标] --> G[共享生成表示]
  A[改写文本] --> G
  O --> V[组件检查与因素审核]
  A --> V
  V --> M[可靠因素掩码]
  G --> L[原文生成与句子监督]
  G --> H[原文全因素／变体可靠因素监督]
  M --> H
  G --> P[可靠对应上的成对损失]
  M --> P
```''')
replace('图3-2区分继承的专项适配、线索提示和句子监督，以及新增的组件头、关系头与成对损失。实线表示文本和隐藏状态的数据流，虚线表示监督或控制连接；冻结参数与可训练模块分别标示，各类参数的梯度来源在3.4.3节统一说明。','图3-2区分原文生成路径、变体可靠监督与成对学习；具体梯度来源在3.4.3节说明。图中改写全文进入共享表示，但未审核标签不进入增强侧损失。')

# Training results regenerated from integer records.
training=['t0_i0','original_heads_i0','plain_i0','qos_i0','simple_data_i0','head_i0','t1_i0','full_filter_i0','random_i0']
t3='''### 3.6 实验结果与分析

#### 3.6.1 比较口径与贡献拆分

本节使用v12严格原生对象模拟，全部数值从同批人工对象和整数TP、FP、FN计算。T0保留ICIC训练配置，T1增加本章方法；本节所有行均采用相同的继承修正策略I0，故训练结果含义是“在I0固定时”的条件变化。第五章的T0/I0以ICIC完整继承配置为起点，不再以未修正MCR充当ICIC Full。

数据构造比较固定辅助监督：普通增强、QOS式适配和关系感知可靠对应使用相同训练规模、头结构及更新预算，均不加成对损失。学习比较固定相同变体和掩码，依次使用无成对项、仅组件成对、组件及关系成对。“仅原文辅助头”用于区分新头与新视图，完整筛选和随机中心作为可选设置。

'''+tbl('表3-2 训练侧比较的固定条件',['比较','固定项','变化项','可解释范围'],[
 ['数据构造','骨干、辅助头、推理I0、训练资源','普通／QOS式／可靠对应视图','构造方案整体差异'],
 ['成对目标','同一视图与因素掩码、辅助头、I0','无成对／仅组件／组件及关系','学习目标的条件增量'],
 ['完整筛选','生成池、目标、尝试预算','掩码学习／整例拒绝','额外审核与源覆盖取舍'],
 ['中心选择','区域规模、输入长度、目标及预算','结论中心／匹配随机中心','区域选择作用，不等于学习贡献']])
t3+='#### 3.6.2 严格抽取结果\n\n'+tbl('表3-3 训练方法的条件结果（全部模拟；固定I0）',['方法','AAEC组件','AAEC关系','CDCP组件','CDCP关系'],[[L[m],*four(m)] for m in training])
t3+=f'''T1相对ICIC继承配置的关系增量为{f(delta('AAEC','t1_i0','t0_i0'))}和{f(delta('CDCP','t1_i0','t0_i0'))}个百分点。这一总量包含候选生成分布随训练变化的作用，不全部归于成对损失。数据构造与头监督固定后，加入关系成对项的增量为{f(delta('AAEC','t1_i0','head_i0'))}和{f(delta('CDCP','t1_i0','head_i0'))}个百分点。

'''
pr=[]
for ds in ['AAEC','CDCP']:
 for a,b,label in [('simple_data_i0','qos_i0','可靠对应−QOS式'),('head_i0','simple_data_i0','组件成对项'),('t1_i0','head_i0','增加关系成对项'),('full_filter_i0','t1_i0','完整筛选−默认掩码'),('random_i0','t1_i0','随机−结论中心')]:pr.append([ds,label,*ci(ds,a,b)])
t3+='#### 3.6.3 关键比较与解释\n\n'+tbl('表3-4 关系F1差值与文档配对区间（全部模拟）',['语料','比较','差值pp','95%区间'],pr)
t3+='''区间来自人工计数模型，不是目标模型效果的统计证据。该正向情景允许主框架总体增益，同时保留完整筛选、中心选择和部分单独学习项的不确定性；不要求每个设计均在每个语料上形成明确优势。CDCP的关系成对增量区间跨零，不能写作已经稳定受益。

#### 3.6.4 审核覆盖与训练成本

默认方法将审核覆盖与样本接受分开：格式／组件通过数、关系因素通过数、未审核因素数、原标签分歧数分别登记；源文档覆盖不等于因素覆盖。每篇最多4次尝试、2个视图，原文始终保留。匹配变体与token轨用于下游学习比较，固定尝试轨用于比较真实获取成本；未达到匹配规模的配置不通过重复少量高质量样本补足。

完整筛选只有在额外发现的问题足以抵偿丢失视图和审核成本时才值得采用。下一步先对固定共同生成池人工抽审，再按同规模输入训练，分别判断审核收益和学习收益。当前真实审核结果见下一小节；OOF示例及成本设定集中于附录H，不把Luna审核次数折算为Qwen训练小时。

'''
drift=segment('#### 3.6.7 Luna改写与筛选的真实诊断','### 3.7 本章小结',old).replace('3.6.7','3.6.5').replace('表3-10','表3-5')
drift=drift.replace('正文保留完整影响域作为可检验机制；对本池优先采用更简单的语义检查，并将完整筛选的采用条件写为：在独立人工复核中检出额外漂移且覆盖代价可接受。模拟表3-3、3-4不由该真实试验产生。','该诊断促使本版将完整筛选降为可选对照，默认设计改为组件检查与可靠因素掩码。新设计仍需单独训练验证；表3-3和3-4不由此次审核结果推算。')
t3+=drift+'''### 3.7 本章小结

本章以可靠对应而非完整筛选的必然优越性组织训练贡献。影响域用于定位需要关注的监督，标注输运保持对象身份，因素掩码决定哪些增强标签可以进入学习。原文生成和金标锚定保持，组件及关系成对项在共同视图上独立比较。当前正向情景给出完整数值预览；真实小试支持简化审核假设，尚未完成目标生成模型训练。

'''
block('### 3.6 实验结果与分析','## 第四章',t3)

# Proposal interfaces and bounded candidate universe.
replace('无法解析的输出记为失败，失败调用仍计入总成本。','关系字段解析失败独立记为失败，但已经通过坐标、类型及重叠检查的组件仍保留为候选；失败调用进入全部成本。')
replace('受保护部分包含合法化后初始图及全部成功解析候选图中的合法组件跨度；','受保护部分包含合法化后初始图及各候选输出中能够独立解析的合法组件跨度；')
replace('独立跨度头和有限规则扩展提供补充部分。','原生跨度头与类型提案提供补充部分；边界规则扩展为关闭的可选消融，不以候选数量增长代替覆盖提升。')
replace('参考解码与一次性有限扩展覆盖邻近边界、相邻跨度合并和内部切分；扩展不递归，去重后才按边界分保留补充候选。','默认使用原生跨度头及组件提案，保留相应类型分布；仅在训练侧覆盖诊断支持时启用一次性的邻近边界、合并或切分扩展，扩展不递归。去重后按边界分保留补充候选。')
replace('对$u\\in U$保留协议合法的全部类型，构成$\\mathcal V=\\{(u,t):t\\in\\mathcal T(u)\\}$。NULL表示不选择，同一跨度至多一个类型。','对每个补充跨度默认保留类型头前2个原生类型；受保护对象的类型全部保留。记候选类型集合为$\\mathcal T_*(u)$，构成$\\mathcal V=\\{(u,t):t\\in\\mathcal T_*(u)\\}$。全类型展开为独立消融，不与默认有限池混称。NULL表示不选择，同一跨度至多一个类型。')
replace('关系候选池$P$以完整端点槽位为单位构建。AAEC枚举可共存组件的有向对；CDCP枚举可共存、最多三个源成员的有序源集合与目标。除端点互斥等必然冲突外，不按整个候选宇宙中间是否存在其他跨度预删源组合，因为中间跨度可能最终不被选中。','关系候选池$P$以完整端点槽位为单位构建。AAEC枚举有限组件池内可共存的有向对；CDCP默认由关系提案器输出最多64个完整源组与目标，并补充预测分段中相邻2／3成员的源组，每文档补充源组上限256。源组必须完整给出且与目标可共存，按提案分及规范键固定排序；不遍历全部跨度与类型笛卡尔积。原生连续性在最终选择图上复核，不以整个候选宇宙的固定邻接关系替代。')
replace('不同语料的原生约束分别登记。ArgUNSC与CasiMedicos-Arg只允许单源二元关系；','不同语料的原生约束分别登记。CasiMedicos-Arg只允许单源二元关系；')
block('#### 4.2.5 裁剪前规模与资源预检','### 4.3 组件集合', '''#### 4.2.5 裁剪前规模与资源预检

最终补充槽位上限4096不能限制其前面的提案、枚举和评分成本。本版将有限原生提案作为默认入口：补充跨度64、每跨度前2类型、CDCP完整源组与目标提案最多256，受保护对象另计。先流式检查实际合法槽位数，预览资源上限为50000；超限明确返回候选构造失败，保留原初始图、金标分母及已耗成本。

全类型、三源成员完全组合仍作为规模上界和覆盖消融。对m个跨度、每跨度q类，其宽松槽位量为AAEC的m(m−1)q²及CDCP的Σₖ₌₁³ C(m,k)(m−k)qᵏ⁺¹。该宇宙通常远大于默认提案池，不能把它的组合界写成默认实现已经枚举的数量。

资源裁剪按冻结的提案分或对象分进行，记录保护对象、补充对象、裁前／裁后数量及多源覆盖；任何候选质量判断都在冻结后进行。有限源组可能遗漏正确联合源，因此需要与全类型或扩大源组预算进行覆盖对照。局部和全局求解共享同一最终候选及评分快照，不能只给一种方法更好的池。

当前CasiMedicos真实验证复用v11的固定C层，不启用无额外聚合覆盖收益的D层边界扩展。它验证有限提案的一个诊断实例；CDCP完整源组提案器仍是待实现和训练验收的目标配置。''')
before('#### 4.4.3 固定计数效用', '''#### 4.4.2.1 原有正确对象的保留风险

策略选择集同时记录F1、初始TP保留、错误新增及尾延迟。接受间隔δ使用预先声明的网格{0.01,0.05,0.10,0.20}；先剔除不满足开发侧风险上限的配置，再按质量与成本选择。预览目标为原TP损失率不超过5%；样本数不足或没有配置通过时返回不修正，不能在测试集降低风险门槛。

这一约束是有限开发集上的经验选择，不保证每篇测试文档的TP保留或F1不降。δ与分项代价κ在评价前按语料固定，局部和全局共用；不对测试文档临时选较高分结果。缺失评分保持未知并拒绝受影响事务；有效但不准确的分数则通过OOF训练、自然分布校准和对象诊断解决。''')
before('### 4.6 实验与分析', '''#### 4.5.6 动作粒度与求解方式的选择

依赖闭合规定一次修改必须共同处理哪些关系，不要求所有输入都使用集合动作或局部搜索。默认路由先检查候选和评分齐备，再按冻结的图规模规则选择求解器。预览取完整对象变量数不超过2500时全局ILP，否则采用有界局部方法；该阈值是内容稿假设，正式运行由训练侧资源探测固定。两路均使用同一效用、分项门及整图约束，超时没有合法改进解时返回初始图。

局部方法默认保留单对象闭合；只有训练侧拆分／合并诊断及受控比较支持时才开启集合动作。算法4-1、4-2描述集合局部子程序，仍用于可达性分析和独立消融。小池直接全局求解不经过无意义的局部循环，大池也不因局部运行而获得真实F1改进保证。

全局净编辑可行域通常包含局部累计编辑可达终态，不能将两者称为相同可行域。相同候选、评分和时限的比较仍需同时报告预算语义及求解证书。综合配置I1是依赖闭合决策及固定选择规则；“集合局部BR-J”单独命名，防止把整套方法的总收益全部归给局部算法。''')

# Rebuild all inference tables; retain actual results under separate identity.
irows=['mcr_t1','t1_i0','br_c','relation_only','sequential','single_object','brj_local','global_equal','global_long','t1_i1','uncalibrated','missing_as_low','no_risk_guard','regenerate']
t4='''### 4.6 实验与分析

#### 4.6.1 受控比较与初始状态

同一T1生成检查点提供MCR初始图，所有受控动作比较使用相同候选、完整对象分及合法化规则。BR-O对应继承策略I0；I1表示包含候选、评分保护和固定求解选择的完整新修正配置。原生候选补充本身需在系统比较中计费；受控求解表使用共同快照，避免把前端差异归给动作或搜索。

'''+tbl('表4-1 推理对照的职责',['方法','改变的条件','解释对象'],[
 ['MCR初始图／BR-O','是否使用原ICIC修正','继承修正的起点'],['RelationOnly','固定组件，使用共同评分','可变组件的价值'],['组件优先分步','先提交组件，再处理关系','分步与联合决策差异'],['单对象／集合局部','只改变允许的组件替换形态','集合动作的额外价值'],['同目标全局ILP','全局净编辑可行域及搜索方式','解质量、gap与资源取舍'],['完整I1','按冻结规则选择实现并保护未评分对象','整个新增推理配置'],['未校准／缺失当低分／取消风险门','分别改变一个评分或策略条件','评分与风险控制的作用']])
t4+='''局部累计组件／关系预算为24／96，全局终态净预算使用相同数值；全局域包含相应局部终态，但不等价。顺序基线允许先提交组件，其终态不保证满足原图的关系分项下界；与全局直接比较时须另列无该下界版本。本版只将其作为分步策略对照，不作同可行域声明。

#### 4.6.2 正向情景下的质量比较

'''+tbl('表4-2 严格原生对象下的推理结果（全部模拟）',['方法','AAEC组件','AAEC关系','CDCP组件','CDCP关系'],[[L[m],*four(m)] for m in irows])
t4+=f'''完整I1在T1训练条件下比继承BR-O提高关系F1 {f(delta('AAEC','t1_i1','t1_i0'))}和{f(delta('CDCP','t1_i1','t1_i0'))}个百分点。与RelationOnly相比，差值为{f(delta('AAEC','t1_i1','relation_only'))}和{f(delta('CDCP','t1_i1','relation_only'))}；这表示该情景中组件可变性仍有价值。集合局部相对单对象只有{f(delta('AAEC','brj_local','single_object'))}和{f(delta('CDCP','brj_local','single_object'))}个百分点，不能把小增量写成所有输入都需要集合替换。

'''
qrows=[]
for ds in ['AAEC','CDCP']:
 for a,b,label in [('brj_local','single_object','集合局部−单对象'),('global_equal','brj_local','全局−集合局部'),('t1_i1','relation_only','完整I1−固定组件'),('t1_i1','missing_as_low','缺失保护增量'),('t1_i1','uncalibrated','校准配置增量')]:qrows.append([ds,label,*ci(ds,a,b)])
t4+=tbl('表4-3 关键推理差值及配对区间（全部模拟）',['语料','对照','差值pp','95%区间'],qrows)
t4+='''全局等预算和大预算行可以高于完整框架或集合局部；这些排序是人工情景输入，不由可行域包含关系推出真实F1优越性。完整框架的采用目标是相对继承系统取得可解释增量并控制资源，不要求一个求解器在质量、误改和时间上同时获胜。

#### 4.6.3 候选、评分与恢复链

评价依次区分完整组件入池、全部端点入池、完整关系槽位入池、评分通过、端点被选择及最终关系输出。候选覆盖只规定可能恢复的上限；正确关系尚未评分或未进入最终合法图时，不计作TP。表4-4引用既存真实候选构造，固定C层为独立成分抽取，D层额外扩边界或源组。

'''
cov=read(R/'research_1011_v11/candidate/evaluation/coverage.json')['aggregates'];rows=[]
for ds,dsname in [('cdcp','CDCP'),('casimedicos','CasiMedicos')]:
 for layer,lname in [('A_original','A 原池'),('C_separate_extraction','C 分离抽取'),('D_boundary_and_joint','D 边界／源组')]:
  z=next(z for z in cov if z['corpus']==ds and z['layer']==layer);rows.append([dsname,lname,f"{z['C_hit']}/{z['gold_C']}",f"{z['R_hit']}/{z['gold_R']}",z['components'],z['relations']])
t4+=tbl('表4-4 同一8篇样本的候选覆盖（真实输出；每语料分别计算）',['语料','层','组件命中','完整关系入池','组件候选','关系候选'],rows)
t4+='''CDCP只从1／22增到2／22，两个多源金标仍全部缺失；尚不足以比较强修正机制。CasiMedicos从0／37增到13／37，说明分离组件接口改善了候选覆盖，但D层没有再提高聚合正确关系数。实际D层新增和裁掉各1条，不能简单说每条关系都被保留；本轮后续验证固定C层，不依据金标重新挑选边界。

#### 4.6.4 误改与资源的联合报告

'''
rr=[]
for ds in ['AAEC','CDCP']:
 for m in ['single_object','brj_local','t1_i1','global_equal','no_risk_guard']:
  z=S['risk'][ds][m];rr.append([ds,L[m],z['recovered'],z['lost_tp'],z['removed_fp'],z['added_fp'],f(z['tp_retention'])])
t4+=tbl('表4-5 相对T1的MCR初始图的关系变化（三个模拟种子累计）',['语料','方法','恢复TP','损失TP','移除FP','新增FP','原TP保留%'],rr)
t4+='''本情景允许取消风险门后F1略高，但其原TP损失更多；因此风险门是质量与变更代价的取舍，不能仅以最高F1判断。完整I1也不在所有风险指标上优于单对象或全局。代理效用门以及开发侧5%风险目标均不保证每篇真实文档非下降。

下面给出共同准备与求解的显式成本假设，用于预览报告形式。分项秒数是设定输入，未在目标GPU测量；I1整行的质量由人工对象计数构造，不表示已按路由规则运行了真实训练或求解。正式运行须逐文档计入失败和回退，不能从平均数反推P95。

'''
costs=[]
for ds,gen,prep,sc in [('AAEC',18.,.6,12.4),('CDCP',23.,1.2,19.6)]:
 for method,sol in [('单对象闭合',.55),('集合局部BR-J',1.4),('全局ILP等预算',1.1),('完整I1',.9)]:
  sol*=1 if ds=='AAEC' else 1.8;costs.append({'dataset':ds,'method':method,'generation':gen,'proposal':prep,'scoring':sc,'solver':sol,'total':gen+prep+sc+sol,'evidence_type':'ASSIGNED_COST_NOT_TIMED'})
t4+=tbl('表4-6 推理成本分项（秒；全部为预览假设）',['语料','配置','生成','提案','评分','求解','合计'],[[z['dataset'],z['method'],*[f(z[k]) for k in ['generation','proposal','scoring','solver','total']]] for z in costs])
t4+='''表4-6不预设全局一定慢于局部。主要成本来自生成和评分时，微小求解差异不会形成显著端到端优势；默认有限提案应优先验证覆盖与准备代价。等求解预算与等端到端时限分别报告，预算不足时返回共同初始图，实际已耗成本保留。

#### 4.6.5 冻结输入的既存求解对照

下表从既存真实记录中仅引用当前范围的CDCP与CasiMedicos，共64篇；CDCP具有稀疏和显式评分，形成96个文档／评分条件。三个时限、四种策略共1152条记录，均复用冻结输入，不能称为1152篇新文本。其共同评分为Luna启发式判断，尚未使用目标Qwen训练评分器。

'''
sv=read(R/'research_1011_v11/solver/evaluation/metrics.json')['aggregates'];svrows=[]
for z in sv:
 if z['corpus'] in ['cdcp','casimedicos'] and z['budget']==5 and z['mode'] in ['BRJ-lite','GlobalILP-lite']:
  svrows.append(['CDCP' if z['corpus']=='cdcp' else 'CasiMedicos',z['condition'],z['mode'],f(z['C']['F1']*100),f(z['R']['F1']*100),f(z['wall_seconds']['mean']*1000)])
t4+=tbl('表4-7 5秒求解上限下的既存严格结果（真实运行）',['语料','评分','策略','组件F1','关系F1','平均ms'],svrows)
t4+='''这些小池中，单对象与集合局部聚合计数一致，全局平均时间更低；CDCP显式评分修正后的关系F1仍低于共同初始图3.33。结果限制了“集合动作必要”和“局部天然更快”的主张，不能用正向模拟表覆盖。已有AAEC端点恢复及CDCP误删案例保留在历史诊断入口，未从扩样后的正例率推断总体效果。

#### 4.6.6 CasiMedicos的评分与最终输出验证

本轮对同一8篇CasiMedicos英文文本追加11个全新上下文的gpt-5.6-luna／low评分任务。冻结C层包含166个组件、3195个单源有向槽位，每槽明确评价Attack和Support，共6390个完整关系分数；没有默认低分。评分输入不展示初始图、金标或预期增益。组件与关系ID、覆盖和数值范围全部检查，通过后才运行求解和金标评价。

初始化先在非重叠约束下最大化组件效用，再在已选组件上选取正效用关系；随后在同一初始图上比较单对象、BRJ-lite和全局ILP-lite。5秒求解和24／96编辑预算固定。阈值0.50为主配置，0.65为评分前登记的敏感性条件；阈值不由本批金标选择。全部8篇始终在分母内。此初始化修复了旧关系解析失败导致空图的接口，因此历史对比同时包含候选、评分和初始化变化，不单独归因于评分。

'''
vr=[]
for z in V['summary']:
 if z['mode']=='historical_v10_initial' or z['threshold']==.5 or z['mode'] in ['component-then-relation initialization','BRJ-lite']:
  name={'historical_v10_initial':'旧初始图','component-then-relation initialization':'组件后关系初始化'}.get(z['mode'],z['mode']);vr.append([name,'—' if z['threshold'] is None else f(z['threshold']),f(z['C']['f1']),f(z['R']['f1']),f"{z['R']['tp']}/{z['R']['fp']}/{z['R']['fn']}"])
t4+=tbl('表4-8 CasiMedicos固定8篇的最终严格输出（真实运行）',['配置','阈值','组件F1','关系F1','关系TP/FP/FN'],vr)
t4+='''主配置将旧初始图组件F1由8.25提高到23.60、关系F1由0提高到3.81，但仅1篇关系F1提高，7篇不变。13条已入池正确关系最终只选中2条，同时输出66条错误关系。三个求解器都未在新初始化上增加正确关系；提高阈值至0.65后，两条正确关系均不再输出，关系F1回到0。不能据此把“更保守”写成“更可靠”，也不据该敏感性结果反向调主阈值。

'''
t4+=tbl('表4-9 CasiMedicos完整对象评分的事后诊断（真实输出）',['对象','候选数','正确对象','AUROC','Brier','正例均分','负例均分'],[[z['object'],z['n'],z['positive'],f(z['AUROC'],3),f(z['Brier'],3),f(z['mean_score_positive'],3),f(z['mean_score_negative'],3)] for z in V['score_audit']])
t4+='''组件评分的AUROC为0.393，正确组件平均分反而低于错误组件，说明当前提示评分没有学会严格原生边界和类型。关系候选6390个中仅13个正例，虽然AUROC为0.756，阈值大于0.5时也只有7个正例而有337个负例；排序指标不能替代输出精确率。关系Brier低于组件Brier主要受极低正例比例影响，不能跨对象族据此宣布关系概率已经校准。

两条正确关系都来自318_140；完整逐篇计数与输出键见附录D。当前可支持的结论是：组件接口修复使一部分正确结构可达，但有效评分和端点选择仍不足，增加求解范围没有解决该问题。CasiMedicos保留为补充适配诊断，不进入AAEC/CDCP主结果均值；后续如继续，应先用原生边界和类型监督训练评分器，并在独立文档上评价，而不是继续扩大弱评分候选池。

### 4.7 本章小结

本章把依赖闭合作为共同决策接口，将候选、评分和求解各自的责任分开。默认有限原生提案控制准备成本，缺失分数保持未知，开发侧风险约束决定接受配置；全局、单对象及集合局部均为可比较实现。正向情景展示相对ICIC继承系统的预期深化，真实CasiMedicos输出进一步表明候选可达不等于正确选择。核心验证应优先提高原生候选与评分质量，再判断更复杂动作是否值得保留。

'''
block('### 4.6 实验与分析','## 第五章',t4)

# Four-cell results use the actual inherited full system as T0/I0.
t5='''## 第五章 两阶段框架的综合分析

### 5.1 ICIC继承基线与两类协议

本章的T0表示ICIC训练配置，I0表示ICIC原有多候选重排序及有界修正，故T0/I0为完整继承系统；T1仅替换训练方法，I1仅替换推理修正配置。T1/I0与T0/I1分别回答新增训练和新增修正的价值，T1/I1回答结合后的表现。该定义避免用未修正初始图作为“ICIC Full”的替身。

兼容轨以用户已有ICIC数值作为目标情景的参照，但引用值与本版人工记录的身份分别标识；当前尚未在相同评价代码上复跑两者。

'''
reported={'AAEC':(83.71,64.83),'CDCP':(76.45,38.17)};rows=[]
for ds in ['AAEC','CDCP']:
 rows.append([ds,'ICIC公开引用[34]','历史原协议',*map(f,reported[ds])]);rows.append([ds,'T0/I0人工继承起点','兼容目标情景',metric(ds,'t0_i0','component','icic_compatible_target'),metric(ds,'t0_i0','relation','icic_compatible_target')]);rows.append([ds,'T1/I1人工完整框架','兼容目标情景',metric(ds,'t1_i1','component','icic_compatible_target'),metric(ds,'t1_i1','relation','icic_compatible_target')])
t5+=tbl('表5-1 ICIC公开值与同尺度正向目标情景（身份分别列明）',['语料','系统','来源','组件F1','关系F1'],rows)
t5+=f'''原先讨论的目标中心为AAEC 85.20／68.20、CDCP 78.30／41.50，整数化后的完整框架均值为{f(C['AAEC']['t1_i1']['component']['mean'])}／{f(C['AAEC']['t1_i1']['relation']['mean'])}和{f(C['CDCP']['t1_i1']['component']['mean'])}／{f(C['CDCP']['t1_i1']['relation']['mean'])}。数值围绕“优于ICIC”的研究目标设计，不由框架扩展推出真实必然提升。不能拿本表的CDCP 38.17与严格完整源集合结果直接计算收益。

### 5.2 严格原生协议下的四格

'''+tbl('表5-2 四格组合的严格原生结果（全部模拟）',['配置','AAEC组件','AAEC关系','CDCP组件','CDCP关系'],[[L[m],*four(m)] for m in ['t0_i0','t1_i0','t0_i1','t1_i1']])
t5+='''表5-2双方都在新严格原生情景中生成，T0/I0不是将ICIC公开值直接搬入新评价器。不同训练配置允许产生不同候选，因为候选改善属于训练效果；推理机制受控比较另固定同一训练检查点的候选与评分，不把这两类归因混在一起。

'''
rows=[]
for ds in ['AAEC','CDCP']:
 for a,b,lab in [('t1_i0','t0_i0','仅训练增量'),('t0_i1','t0_i0','仅修正增量'),('t1_i1','t1_i0','T1下修正增量'),('t1_i1','t0_i0','组合总增量')]:rows.append([ds,lab,*ci(ds,a,b)])
 z=S['interactions']['strict_native'][ds]['relation'];rows.append([ds,'交互差',f(z['value']),'['+f(z['ci95'][0])+', '+f(z['ci95'][1])+']'])
t5+=tbl('表5-3 关系F1条件增量与交互（全部模拟）',['语料','效应','差值pp','95%区间'],rows)
t5+='''交互差为F11−F10−F01＋F00，不是组合效果本身。情景中组合总增量为正，但AAEC交互中心为负，CDCP接近零，二者区间均跨零。因此“同时采用更好”不等于“超加性交互显著”，也不能要求两阶段只修复互不相同的错误。

### 5.3 同一人工对象上的作用分解

TP成员按完整人工身份对齐，先从各单阶段命中中减去继承基线命中，再区分共同恢复、独有恢复和组合新增。成员来自生成主表的同一记录，不为第五章另选对象来制造互补性。

'''
rows=[]
for ds in ['AAEC','CDCP']:
 z=[x for x in S['members'] if x['protocol']=='strict_native' and x['dataset']==ds and x['object']=='relation'];keys=['both_only','training_only','repair_only','neither_single_but_combined','single_recovery_lost_in_combined','baseline_lost_combined'];rows.append([ds,*[sum(x[k] for x in z) for k in keys]])
t5+=tbl('表5-4 关系正确对象的成员分解（三个模拟种子累计）',['语料','共同恢复','仅训练恢复','仅修正恢复','组合独有新增','单阶段恢复在组合中丢失','基线TP被组合丢失'],rows)
t5+='''共同恢复与独有恢复可以并存，组合也可能破坏单阶段已经恢复的对象。该分解是人工身份集合的算术关系；这些对象没有原文跨度及端点连接，不能当作真实句例，也不能用成员分解代替实际候选和事务轨迹分析。

### 5.4 原生联合源与在线配置

CDCP按源成员数分别计算严格关系F1，整体仍由全部TP、FP、FN重算，不平均各组F1。源组越长，组件遗漏和类型错误有更多阻断机会；分组作用是定位失败链，不将多源困难自动归给求解器。

'''
rows=[]
for k in [1,2,3]:
 vals=[]
 for m in ['t0_i0','t1_i0','t0_i1','t1_i1']:
  a=[x for x in S['cdcp_strata'] if x['method']==m and x['arity']==k];vals.append(f(sum(200*x['tp']/(2*x['tp']+x['fp']+x['fn']) for x in a)/3))
 rows.append([k,*vals])
t5+=tbl('表5-5 CDCP源成员分组的关系F1（全部模拟）',['源成员数','T0/I0','T1/I0','T0/I1','T1/I1'],rows)
t5+='''训练已经完成后，在线选择仍应比较质量、TP损失、准备成本和尾延迟。当前小图真实诊断没有显示集合或局部额外优势，因此I1允许选择全局或单对象；大池应先控制候选与评分规模，再决定求解方式。新训练与新修正可以各自保留，不为维持四格叙事强制启用没有实际收益的模块。

### 5.5 本章小结

以ICIC完整继承配置为起点，四格明确区分训练、修正和组合增量；双协议避免历史值与完整原生对象混比。当前正向模拟使完整框架在两套主语料总体优于同口径继承基线，同时保留小模块效应、交互及误改的不确定性。真实综合发现仍应来自目标模型同批输出，现有CasiMedicos诊断不承担训练四格的证据职责。

'''
block('## 第五章','## 第六章',t5)
block('## 第六章','## 参考文献', '''## 第六章 总结与展望

### 6.1 研究总结

本文围绕组件与关系依赖研究两个阶段的问题。训练侧以影响域确定待核查范围，以标注输运维护身份，以因素掩码限定增强侧监督，在可靠对应上加入组件和关系成对学习。原文继续承担完整生成目标，完整影响域整例筛选保留为可验证选项，避免将筛选复杂度本身作为贡献。

推理侧先保证原生组件与关系提案可用，区分评分缺失与低置信，再以依赖闭合组织完整修改。全局、单对象和集合局部共用任务约束及对象效用，根据开发侧固定的规模与风险规则选择。本文的核心是完整处理依赖及其决策条件，集合动作或局部ILP不被预设为所有文档的最优实现。

主结果以ICIC完整继承系统为起点，使用双协议及四格报告新增内容。正向目标情景完成了整数计数、区间、对象身份和跨章复用，适合检查全文论证与结果呈现。真实开发记录则表明简单筛选可能已经足够，小图更复杂的动作未必获益；新增CasiMedicos结果显示候选修复能产生少量正确输出，但评分仍明显不足。

### 6.2 研究局限

尚未完成目标Qwen生成器、原生跨度头及完整对象评分器的训练，因此不能将模拟提升表述为实证结论。旧协议兼容轨尚未实现共同评价器，严格原生轨中的ICIC基线也是待复现配置；正式比较须同时替换双方输出，不能只替换新系统成绩。

审核判断和Luna评分来自同一模型家族，独立上下文并不保证误差独立。CasiMedicos复用8篇已观察的诊断文档，结果用于发现接口与评分问题，不用于估计总体提升。有限候选会遗漏关系，因素掩码也会减少可用监督；这些代价需要直接计量。代理效用、经验校准和开发侧风险门均不保证真实F1单调改善。

成本尚以显式假设和轻量求解实测为主，目标设备端到端延迟、尾部资源需求与大图求解证书尚待获取。内容迭代中的数值复算属于一致性检查，不计作模型实验、人工审核或部署验收。

### 6.3 后续研究方向

后续首先完成AAEC、CDCP的共同原生接口与ICIC继承复现，固定候选覆盖和评分监督；用少量训练侧OOF文档验证模型能分辨精确跨度、原生类型及完整联合源，再启动三种子主实验。

训练实验优先比较固定数据上的无成对、仅组件成对和组件及关系成对；额外筛选与中心选择仅在代价可解释时保留。推理实验优先比较RelationOnly、单对象与全局，再根据可达性缺口决定是否需要集合局部；同时报告原TP损失、完整失败分母及准备成本。

CasiMedicos暂不扩样。若继续作为迁移扩展，先在原生训练／开发划分上改进边界和类型监督、评分校准，再用未参与当前调试的独立文档确认最终输出。达到主语料受控比较和同批四格证据后，再集中完成Word/PDF排版与送审版本。''')

# Keep historical ICIC tables verbatim; remove the retired dataset everywhere.
ref=re.search(r'^\[50\].*(?:\n(?!\[|##)[^\n]*)*',text,re.M)
assert ref and 'POIAGANOVA' in ref.group(),ref.group()[:200] if ref else None
replace(ref.group(), '')
text=text.replace('[51]','[50]')
block('### A.3 其他语料与语言的范围','### A.6 序列化', '''### A.3 其他语料与语言的范围

本文主比较范围为英文AAEC和CDCP。CasiMedicos-Arg英文版[50]仅作补充适配诊断，保持原生Claim／Premise与Support／Attack定义：一般医学知识仍属Claim，病例特定观察属Premise，允许Claim支持Claim。其同一病例的不同语言版本不当作独立样本，也不由该论辩抽取试验推断诊疗正确性或跨语言效果。

### A.4 v12参考配置

配置身份为1011-v12-content。默认采用组件检查、关系因素掩码和原文完整生成监督；推理采用有限原生提案，缺失评分拒绝事务，规模路由与风险规则在训练侧固定。历史代码和输出继续保持原版本身份，不因论文修改而宣称已经实现v12全部设计。

|模块|v12预览配置|说明|
|:---|:---|:---|
|中心与生成|每文档1中心、4次尝试、最多2视图|金标仅用于训练阶段构造|
|可靠关系|全部受影响正关系；内部／边界NONE各最多4|未审核或未通过因素掩码为0|
|训练目标|原文完整生成；变体可靠因素头监督及成对项|默认无增强整图生成损失|
|跨度与类型|补充64跨度，前2原生类型|初始及有效解析对象受保护|
|边界扩展|默认关闭|一次性规则扩展单列消融|
|CDCP源组|模型提案64，加有限相邻源组；总补充256|已有长超边保护；不拆平|
|关系资源|裁前合法槽位50000，裁后补充4096|候选失败返回基线并保留耗时|
|求解选择|对象变量数≤2500全局，否则局部|预览阈值；正式由训练侧探测固定|
|局部动作|默认单对象闭合，集合动作用作可选对照|全部受影响关系仍共同评价|
|预算|每文档3／5秒；组件24、关系96|局部累计／全局净编辑分别报告|
|接受与风险|κC=κR=1；δ网格0.01／0.05／0.10／0.20|开发侧原TP损失目标≤5%，不保证测试安全|

### A.5 结果登记与跨章复用

v12模拟结果键为协议、语料、文档、种子、配置和对象层次。严格原生主表共用_revision_1011_v12/simulation/document_counts.csv；results.json计算种子均值、样本标准差、配对区间及交互；object_membership.jsonl保存同计数人工对象身份。表3-3的T1/I0、表4-2的继承BR-O与表5-2的T1/I0引用同一结果键；完整I1与T1/I1同样复用。旧协议尺度目标使用独立协议键，不与原生计数拼接。

v12真实诊断保存在research_1011_v12/casimedicos，包含冻结输入、11项原始评分、逐文档完整概率、64条输出记录及严格评价。64条含8篇×2阈值×4种输出配置，其中16条为确定性初始化，48条为修正运行；不是64个新模型调用。所有原始历史文件保留，正文只引用当前研究范围内的记录。''')
replace('参考有限扩展对受保护跨度及跨度头前$N_{head}$个输出只执行一次：','可选有限扩展对受保护跨度及跨度头前$N_{head}$个输出只执行一次（v12默认关闭）：')
replace('对$u\\in U$保留协议合法的全部类型，构成$\\mathcal V=\\{(u,t):t\\in\\mathcal T(u)\\}$。NULL表示不选择该跨度。','v12默认补充跨度使用原生类型头前2项，保护来源的合法类型不裁；全类型展开另列对照。NULL表示不选择该跨度。')
replace('ArgUNSC所用作者仓库含MIT许可，CasiMedicos-Arg数据卡标注CC-BY 4.0；本地清单同时保存许可文本、发布版本和文件哈希[50][50]。许可记录用于追踪本次获取条件，正式公开材料仍须保留作者引用及适用归属说明。后者仅用于论辩结构抽取，不作为诊疗建议或医学正确性评价。','CasiMedicos-Arg数据卡标注CC-BY 4.0，本地清单保存许可文本、发布版本和文件哈希[50]。正式公开材料保留作者归属；该语料仅用于论辩结构抽取，不用于诊疗建议或医学正确性评价。')

# Compact current-scope evidence appendix; old artifacts remain immutable.
dtext='''## 附录D 开发诊断与原始记录

### D.1 既存AAEC与CDCP诊断

既存CPU诊断来自research_0920/results；原始16篇Luna试验来自research_1010_v7_luna，后续AAEC 32篇与CDCP 116篇扩样来自research_1011_luna_expanded及分波目录。扩样曾依据是否发现正例决定追加CDCP文档，故不把最终改善比例视作独立测试估计。原始失败及空输出保留，历史评价身份不追溯修改。

既存诊断记录了AAEC遗漏端点补回、CDCP评分误删及候选覆盖不足；这些证据说明输入条件影响修正，但不替代目标Qwen训练。完整逐例原文、金标、对象及轨迹继续随v11历史证据包保存。正文4.6.5只引用当前范围的冻结输入结果，未增加模型调用。

### D.2 改写审核身份

research_1011_v11/drift保存32篇源文档的64个改写，8项生成、8项筛选、8项分离上下文复核任务。全部请求gpt-5.6-luna／low；精确模型快照、温度、token和采样种子未由工具暴露。430个原标签获认可的关系因素对未检出诱发变化，18个原标签分歧另记。原标签分歧不能更名为增强漂移，同源模型的一致性也不等于准确性。

本版因素掩码设计没有据此宣布完成训练或人工审核。适用范围限于保守改写、小样本和有限NONE抽样；完整域与域外指代影响仍需人工抽审。

### D.3 CasiMedicos新增评分与输出

8篇固定诊断文档沿用v11 C层，原始候选生成未读取金标。新增评分任务只读本文和候选，11个独立上下文覆盖166个组件与3195个槽位。组件评分每个对象只取指定首批输出，槽位拆批不重复取较高值；完整输出与概率检查通过后冻结，再求解和评价。

'''
rows=[]
for z in V['rows']:
 if z['mode']=='BRJ-lite' and z['threshold']==.5:rows.append([z['id'], '/'.join(map(str,z['C'])),'/'.join(map(str,z['R'])),f(200*z['R'][0]/(2*z['R'][0]+z['R'][1]+z['R'][2]))])
dtext+=tbl('表D-1 CasiMedicos全部8篇的主配置计数（真实输出）',['文档','组件TP/FP/FN','关系TP/FP/FN','关系F1'],rows)
dtext+='''旧初始图共有90个组件金标和37个关系金标，组件TP/FP/FN为4／3／86，关系为0／4／37；新主配置为19／52／71及2／66／35。恢复的两条正确关系均来自318_140，不将该单例外推为领域效果。严格按字符边界、原生类型、方向及关系标签评价；通顺解释或医学知识正确不自动算命中。

程序入口为prepare_casi.py、run_casi.py、evaluate_casi.py；protocol.json在评分前冻结样本、候选层、批次、阈值和预算。输入／输出哈希保留，评分无默认值。新增实验没有Qwen训练，没有人工标注补充，也没有根据结果重试某个任务或扩大文档范围。

### D.4 性质与实现验证的边界

既有四组件穷举、接口构造和有限求解检查说明实现遵守指定约束，不能单独证明训练贡献、真实关系恢复或效率优势。当前方法中的v12可靠因素学习、原生监督头及规模路由仍是目标配置；本轮真正执行的是固定Casi候选上的显式Luna评分和声明的轻量初始化／修正。不同运行身份不合并为一个“已完成完整实验”。

'''
block('## 附录D','## 附录E',dtext)

# External protocol remains literature-grounded; old anonymous numbers are not mixed.
block('### G.3 QOS式适配与本方法的差异','## 附录H', '''### G.3 QOS式适配与本方法的差异

本稿QOS式适配保留槽位化改写与标注恢复思想，不声称复现原文全部生成和学习日程。数据构造比较统一原生任务、变体规模、辅助头和推理I0，无成对项；本方法额外记录影响域及可靠因素掩码。成对学习使用同一批视图与掩码，在无成对、仅组件成对和组件及关系成对之间比较。不能把两个对照的总差异全部归于某一个损失项。

### G.4 外部系统接入与结果登记

先冻结原文、划分、评价分词器、类型及完整超边，再审计外部格式转换。AAEC若将stance并入组件标签，原任务和本稿映射分别报告；CDCP若拆分或收缩源集合，只有可核对来源的输出才进入原生完整对象轨。不能依据测试金标补回端点或合并出正确超边。

本版外部研究用于定位方法，尚未完成具名外部系统运行。旧v11匿名外部模拟只用于说明比较表的写法，继续保留历史身份，不与v12继承基线或主表拼接。ICIC是明确的继承参照；其他系统只有完成同协议接入与实际运行，才能写出相对优劣。''')

h='''## 附录H v12数值来源、成本与实证替换

### H.1 正向情景的身份与计数

v12按用户要求把“在ICIC基础上取得增益”设为预览目标。生成器对每种协议、语料、种子和方法先构造人工正确对象及错误对象身份，再按文档汇总整数TP、FP、FN；种子17、29、43全部进入结果。关系与组件对象独立构造，没有原文跨度、真实图端点连接或求解轨迹，故这些计数只支撑表格算术和情景分析。

ICIC兼容目标与严格原生目标采用独立对象宇宙，不能作协议转换或交叉配对。兼容中心采用此前讨论的85.20／68.20与78.30／41.50；严格CDCP关系中心另设为39.90，其基线中心36.90是重评配置的假设，并非由ICIC 38.17换算。整数化和种子扰动使最终均值略有偏离。

所有主表均从新记录读取，不沿用v7表格手工加分。文档配对bootstrap重复2000次，先汇总再算micro-F1，然后对三个固定模拟种子平均；区间只表示该人工生成模型内的文档波动，不确认真实优势。完整筛选、集合动作及交互不被强制设为显著正值。

### H.2 成本假设与候选压力

表4-6成本由生成、提案、评分和求解四项相加，秒数为设定输入，没有端到端实测或经验P95。目标运行同时报告每文档全部尝试、初始化失败、无可行解、超时与回退；准备时间计入两种求解器，不能只向一方收费。

v11小池C／D层实测只覆盖本地槽位构造；开启tracemalloc的分配峰值不是进程RSS，假设每秒2000对象的评分估计也不是GPU基准。旧全类型CDCP组合界用于说明为何改成有限源组提案，不视为v12默认池规模。有限提案以可能损失覆盖换取准备可控，需报告完整多源遗漏，不能用较低运行时间掩盖未枚举对象。

### H.3 OOF与评分验收

训练侧按源文档三折生成持出候选，原文和所有增强视图保持同折。每个完整对象记录生成器身份、边界、类型、源集合及标签；错误链按端点跨度、类型、槽位、评分、接受／预算的顺序取首个阻断。评分拟合、校准和策略用途按2.6.1隔离，阈值不在测试集重调。

v11提供的900条OOF人工错误链继续属于独立指标示例，不能作为本版新目标模型的实测错误率。真实CasiMedicos评分提示原生边界和类型是优先问题，不能仅因关系AUROC为正或接口字段完整就认为已经校准。目标模型OOF必须真正执行，记录模型快照及每折排除的文档。

### H.4 同批成员与风险核查

每个方法的人工正确／错误成员可重新汇总出主表。表5-4的单阶段共同、独有、组合新增和损失从同一对象记录求集合差；表4-5以T1的MCR初始图为共同基线。组件与关系分别算风险，三种子同一文档视为配对运行，不算新增独立文档。

正式模型输出须改用原文完整语义键，并给出成功、误改及最常见失败链的案例。当前人工对象不能补写为真实案例；已有CasiMedicos逐篇键与分数提供开发诊断，但不含训练四格或目标模型概率校准。

### H.5 优先级与停止条件

第一步完成AAEC、CDCP原生接口及ICIC完整继承复现，确认候选覆盖、评分和评价分母可靠。第二步比较同数据成对学习和同候选推理，优先保留简单方案；只有动作可达性或开发侧风险／成本证据支持时再保留集合局部。第三步用同批四格输出形成对象级解释，最后接入至少一个具名外部系统。

不再为主论文扩大语料范围；CasiMedicos维持补充身份，进一步投入以原生评分得到独立验证为前提。若完整筛选、集合动作或局部搜索没有额外价值，应采用简化配置并收缩主张，不要求真实数据服从正向情景。模型实验完成后同时替换主表、区间、图表数据、摘要和结论，保留本模拟版本。

### H.6 复算入口与本轮产出

_revision_1011_v12/generate_scenario.py重建本版全部人工计数；simulation/results.json与object_membership.jsonl保存聚合及身份。compose_content.py按明确段落和章节边界生成新Markdown，旧v11不变。revision.patch保存逐段差异，content_audit.json绑定最终稿、数值与原始结果。

本轮不进行Word/PDF渲染、页码映射或视觉分页检查。完成的是内容修订、真实补充诊断与数值一致性；没有将省去排版检查改写为已完成最终送审版。'''
block('## 附录H',text[-min(50,len(text)):],h) if False else replace(text[text.index('## 附录H'):],h+'\n')

# Content pass on retained interfaces, including the limitations of the new diagnostic.
replace('本节保留原文和增强文各自的金标训练，同时比较对应组件与关系的预测分布。','本节保留原文完整金标训练，增强文只使用通过掩码的辅助标签，并比较可靠对应因素的预测分布。')
replace('上述条件仍需由3.6.2节的标签可靠性审计检验。','上述条件仍需由3.6.5节的审核诊断及后续人工抽审检验。')
replace('集合修正的必要性取决于端点相关错误相对于纯关系错误的规模，以及候选中是否已有可恢复对象。组件类型、边界、遗漏与多检采用固定顺序诊断，候选缺失另作交叉维度；这些维度不能相加为互斥因果比例。附录D.3已补充既存CPU诊断的初始错误、端点条件及一步动作限制；该弱模型的过度分割不能代表目标LLM。4.6.7进一步给出生成候选中的组件补入、完整关系恢复及失败轨迹，并在固定候选和初始图上检验评分输入的调整。简化候选及未校准评分仍限制方法归因，正式目标模型诊断按H.1执行。','组件可变修正的价值取决于端点相关错误的规模及候选中是否已有可恢复对象。组件类型、边界、遗漏与多检按固定顺序诊断，候选缺失另列；这些维度不相加为互斥因果比例。既存CPU和Luna观察集中于附录D，4.6.6给出CasiMedicos新评分与最终输出。当前低分优先用于定位候选和评分问题，不能证明更复杂的动作必需；正式目标模型的错误链按H.3记录。')
replace('本章以MCR-BR-J表示依赖闭合的联合修正，保留候选图生成与初始重排序，将修改单位扩展为冲突闭合的组件集合及全部受影响关系。框架规定对象身份、目标、约束和接受条件；局部整数规划是本稿待检验的求解策略，同目标全局求解是主要对照。下文先说明动作与共同决策，再比较组件可变性、集合表达、误改及完整成本；不由“局部”或“有界”的名称预设采用价值。','本章以I1表示新增依赖闭合修正配置，保留候选生成与初始重排序，并统一组件变化及关联关系的决策。集合局部子程序仍称BR-J，全局选择和单对象闭合单独列出。框架规定身份、目标、约束及接受条件，求解方式由固定开发规则选择；下文分别比较组件可变性、集合表达、误改和完整成本。')
replace('组件同样保存 $m_C(c)$；关系掩码为1还要求全部端点的组件掩码为1。','组件同样保存 $m_C(c)$，用于头监督和对齐的只读端点也在全文上下文中审核，不能只因字面未变就判定其论辩角色稳定；关系掩码为1还要求全部端点的组件掩码为1。')
replace('前三个求解器都未在新初始化上增加正确关系；','前三个求解器都未在新初始化上增加正确关系；') if False else None
before('两条正确关系都来自318_140；', '本次初始化已经使组件分项效用达到有限池内最大值，随后组件非下降门将进一步变化限制在同组件效用的替换中。这是该诊断对后续修正的强约束；“无增量”只描述此起点与分数，不能证明三个算法一般等价或集合动作普遍无用。组件候选和分数仍可存在大量错误，因此代理分项最优并不矛盾于低真实F1。')
replace('带坐标的正反例见附录D.6。','相关构造检查的历史来源见附录D.4。')
replace('输入、断言、结果及范围见附录D.4和D.6。','输入、断言、结果及范围见附录D.4及其历史材料入口。')
replace('图4-2 多候选驱动的依赖闭合修正执行流程','图4-2 集合局部BR-J子程序的执行流程')
block('### F.3 研究问题阅读索引','## 附录G', '''### F.3 研究问题阅读索引

表F-2 方法与实验的阅读索引

|问题|方法入口|结果或解释|
|:---|:---|:---|
|改写会影响哪些关系|3.3.1影响域|3.6.5真实审核诊断|
|哪些增强标签进入学习|3.3.3因素掩码、3.4损失|3.6.2—3.6.3模拟学习比较|
|如何保留原生候选|4.2分离解析和有限提案|4.6.3真实候选覆盖|
|如何区分缺失评分与低分|4.4.1完整对象接口|4.6.6逐项评分与最终输出|
|是否需要集合或局部求解|4.5.6固定选择规则|4.6.2、4.6.5分别列模拟与实测|
|相对ICIC深化在哪里|1.3及2.5.1|第五章双协议与四格|
|数值来自哪里|附录A.5、H.1|配套计数、成员及真实输出文件|''')
replace('![训练和推理的数据及模型接口](_revision_1010_v7/figures/framework.png)', '''```mermaid
flowchart LR
  A[训练原文和金标] --> B[原文生成监督]
  A --> C[局部改写与可靠因素掩码]
  C --> D[辅助监督和成对学习]
  B --> E[训练后生成器]
  D --> E
  X[测试原文] --> E
  E --> F[原生有限候选与固定完整对象评分]
  F --> G[依赖闭合决策：全局或有界局部]
  G --> H[完整输出图]
```''')
replace('![两项研究的共同问题与分工](_revision_1010_v7/figures/research_relationship.png)', '''```mermaid
flowchart TB
  X[组件与关系依赖] --> T[训练：改写后哪些监督仍可靠]
  X --> I[推理：端点变化后哪些关系需重建]
  T --> TL[可靠因素上的成对学习]
  I --> IL[完整依赖下的共同决策]
  TL --> E[同口径受控比较与四格分析]
  IL --> E
```''')
# Numerical previews retained without attributing synthetic outcomes to named systems.
before('## 附录H',tbl('表G-2 匿名外部系统的数值预览（全部模拟）',['语料','系统职责','组件F1','关系F1'],[[ds,L[m],metric(ds,m,'component'),metric(ds,m,'relation')] for ds in ['AAEC','CDCP'] for m in ['external_encoder','external_generator']])+'匿名行仅表示编码式／生成式对照职责，不绑定任何具名论文。记录与v12严格情景共同生成，但没有运行这些系统；正式接入后整行替换，不能将该表用作优于外部研究的证据。')
replace('旧v11匿名外部模拟只用于说明比较表的写法，继续保留历史身份，不与v12继承基线或主表拼接。','本版表G-2重新生成匿名外部模拟以保留数值预览，原v11数据继续归档，不与新表混用。')
oof=read(R/'research_1011_v11/simulation/oof_error_records.json')['rows'];orows=[]
for ds in ['AAEC','CDCP']:
 z=[x for x in oof if x['dataset']==ds];keys=['gold_R','initial_TP','missing_endpoint_span','wrong_endpoint_type','complete_slot_absent','score_or_label_error','budget_or_search'];sums={k:sum(x[k] for x in z) for k in keys};orows.append([ds,len(z),sums['gold_R'],sums['initial_TP'],sums['missing_endpoint_span']+sums['wrong_endpoint_type'],sums['complete_slot_absent'],sums['score_or_label_error']+sums['budget_or_search']])
before('### H.4 同批成员与风险核查',tbl('表H-1 OOF错误链的独立指标示例（沿用模拟，不属于v12主表）',['语料','文档','金标R','初始TP','端点漏','槽位漏','评分／搜索漏'],orows)+'每条遗漏只归入首个阻断，后三项之和等于金标减初始TP。该示例没有执行持出模型，样本和成员不与v12主表拼接。')

# Remove obsolete numerical/figure cross-references in retained interfaces.
text=text.replace('（D.3及4.6.7）','（D.1及4.6.6）').replace('完整诊断方案见H.1。','完整诊断方案见H.3。')
text=text.replace('3.6.7','3.6.5').replace('D.11—D.12','D.1—D.3').replace('D.11','D.3').replace('D.12','D.3').replace('D.13','D.3')
text=text.replace('H.10—H.11','H.2').replace('H.10','H.2').replace('H.11','H.2').replace('H.12','H.1').replace('H.9','H.3').replace('H.6—H.8','H.1—H.4').replace('H.7','H.2').replace('H.8','H.4')
# Preserve diagram concepts, but remove stale references to numbered old result tables.
text=text.replace('表3-5','表3-5')
assert 'ArgUNSC' not in text and 'argunsc' not in text
DEST.write_text(text)
(W/'revision.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile=BASE.name,tofile=DEST.name)))
(W/'apply_report.json').write_text(json.dumps({'workflow':'versioned content revision, deterministic replacements; no ARS full-pipeline certification','base_sha256':sha(old),'output_sha256':sha(text),'operations':ops,'unchanged_ICIC_tables':segment('## 附录E','## 附录F',old)==segment('## 附录E','## 附录F',text),'rendering':False},ensure_ascii=False,indent=2)+'\n')
(W/'simulation/cost_assumptions.json').write_text(json.dumps(costs,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(DEST),'chars':len(text),'operations':len(ops),'tables':len(re.findall(r'^表\w',text,re.M))},ensure_ascii=False))
