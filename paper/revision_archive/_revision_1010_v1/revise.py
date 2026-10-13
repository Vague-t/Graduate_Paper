"""Apply the eight agreed global-review changes, preserving source data and v4."""
from pathlib import Path
import re,json,hashlib,difflib
W=Path(__file__).resolve().parent;R=W.parent
old=(R/'report_1009_v4_full.md').read_text();s=old;edits=[];moved=[]
def change(a,b,key):
    global s
    assert s.count(a)==1,(key,s.count(a),a[:120])
    s=s.replace(a,b,1);edits.append({'id':key,'before':a,'after':b})
def paragraph(prefix,b,key):
    a=next(p for p in s.split('\n\n') if p.startswith(prefix))
    change(a,b,key);return a
def section(start,end,b,key):
    a=s[s.index(start):s.index(end)]
    change(a,b.rstrip()+'\n\n',key);return a
def insert_before(anchor,b,key):change(anchor,b.rstrip()+'\n\n'+anchor,key)

change('1009-v4 模拟数据演示稿　2026年10月9日','1010-v1 模拟数据演示稿　2026年10月10日','V01')
s=s.replace('_revision_1009_v4/figures/','_revision_1010_v1/figures/')
for a,b in [
('面向结论组件的关系感知增强学习','关系影响域约束的增强与成对学习'),
('The first method is relation-aware augmentation learning for conclusion components.','The first method combines relation-domain-constrained augmentation with paired factor learning.'),
('关键词：端到端论辩挖掘；关系感知增强；结论组件；依赖闭合；图修正；代价敏感评分','关键词：端到端论辩挖掘；关系影响域；成对学习；依赖闭合；图修正；结构化预测'),
('Keywords: End-to-End Argument Mining; Relation-Aware Augmentation; Conclusion Components; Dependency Closure; Graph Repair; Cost-Sensitive Scoring','Keywords: End-to-End Argument Mining; Affected Relation Domain; Paired Learning; Dependency Closure; Graph Repair; Structured Prediction')]:
    assert a in s,a
    edits.append({'id':'P02-position','before':a,'after':b,'occurrences':s.count(a)});s=s.replace(a,b)
paragraph('以AAEC与CDCP任务表示开展比较，',"""本版以人工计数情景演示AAEC与CDCP原生任务的评价与分析，所述数值不代表真实模型实验。情景中，完整增强＋基础损失相对QOS式适配的严格关系F1分别增加1.79和1.83个百分点；同一增强集合上，成对项相对头监督再增加1.92和1.88个百分点。结论中心差值与两阶段关系交互区间均包含0。BR-J相对T1初始图增加5.99和6.71个百分点，但同求解时限全局ILP取得略高的关系F1与初始真阳性保留率，BR-J仅节省约4.19%和4.73%的端到端时间。由此，论文将第一项工作聚焦于监督对应与学习目标，将第二项工作定位为需要结合资源和变更要求检验的结构修正选项；真实问题规模、对象级互补及外部系统比较仍需相应运行材料支持。""",'P02-abstract-zh')
paragraph('Under the AAEC and CDCP task representations,',"""This edition uses artificial count scenarios to demonstrate evaluation and analysis under the native AAEC and CDCP task representations; the numbers are not empirical model results. In these scenarios, full augmentation with the base loss exceeds the QOS-style adaptation by 1.79 and 1.83 relation F1 points, while paired learning adds 1.92 and 1.88 points over head supervision on the same augmented data. The intervals for conclusion-center differences and relation interactions include zero. BR-J adds 5.99 and 6.71 points over T1 initial predictions, but equal-solver-budget global ILP attains slightly higher relation F1 and initial true-positive retention; BR-J saves only 4.19% and 4.73% of end-to-end time. These comparisons focus the first contribution on supervision correspondence and paired learning, and frame the second as a structural repair option whose value depends on resource and change-control requirements. Empirical error prevalence, object-level complementarity, and external-system comparisons require corresponding execution evidence.""",'P02-abstract-en')
insert_before('### 1.2 国内外研究现状',"""方法的必要性还取决于错误的实际数量级。训练侧需观察普通改写在内部正关系、跨边界正关系及两类NONE上的漂移；推理侧需区分组件定位错误、端点已正确时的关系错误，以及候选不能覆盖的对象。上述观察限定在训练侧持出文档中，先冻结诊断抽样和比较条件，再开展独立评价。第三、四章引言列出观察单位与设计响应，完整记录规则见附录H；当前人工情景用于推敲分析方式，不承担真实问题发生率的证明。""",'P01-motivation')
change('是本文的直接生成式基线','为本文的直接生成式对照候选','P06-no-fake-external-run')
insert_before('结构与语义信号为生成提供了更具体的条件。',"""GMAM通过约束指针与重构位置编码生成组件和关系序列[47]，提供了处理输出依赖的一种紧凑方式。UniASA则将多种论辩结构任务统一为序列生成，并引入子任务分解的多视图学习[48]。前者适合参照结构生成机制，后者适合考察统一表示与辅助任务的作用；本论文的成对学习另以同一原文及其经过检查的改写为对应单位。统一生成、辅助目标与对应约束解决的问题有所联系，其比较需要固定输入及完整对象评价，而不能仅按是否使用大模型分类。""",'P06-generative-neighbors')
insert_before('关系抽取研究为这种质量控制提供了相邻思路。',"""QOS与同文提出的多样性导向合成DOS分别提供质量和多样性的参照[35]；本文的QOS式适配只继承其中的槽位化改写思想，不能代表两种方案或原论文完整系统的复现。2026年10月公开的对抗强化学习合成研究交替优化生成器与判别器，生成新的文本—结构标注对[49]。这说明可靠性与变化幅度可以共同研究；本文则限定为保留原图监督的局部改写，需分别验证关系影响域检查和对应因素学习的增量。两类数据构造目标不同，比较时先统一训练规模和下游抽取器，再解释结构新颖性与表达变化。""",'P06-synthesis-neighbors')
paragraph('表中的机制依据本章已说明的材料范围归纳，',"""表中的机制依据已核对的原文归纳。外部对照选择进一步覆盖结构解析、文本生成、结构感知生成、动作生成与大模型系统，见附录G。系统层面的主要复现候选为Kawarada等的文本生成方法与UniASA；GMAM、DENIM作为结构生成补充，QOS／DOS作为数据构造近邻。选择依据是输入、表示及代码入口的可核对程度，而非仅选取较低的已发表分数。AAEC的stance处理、CDCP完整源集合和预测坐标仍须接入共同评价器后才确认可比性。其他语言和任务范围见附录A.3。""",'P06-selection')
paragraph('RQ1：',"""RQ1：按关系影响域检查局部改写中的正关系与NONE，并建立可靠的标注对应，能否在保留足够表达变化和源覆盖的条件下改善监督质量？在相同增强数据和训练预算上，成对因素学习能否进一步改善严格抽取结果？中心选择作为区域策略单独比较。""",'P02-rq1')
paragraph('RQ2：',"""RQ2：在共同候选、评分与任务约束下，组件集合替换和关系闭合能够处理哪些逐项修改难以处理的错误？与同条件全局ILP相比，局部事务在什么求解预算、端到端时限或变更控制要求下值得采用？候选覆盖、真实误改及决策代价共同决定结论。""",'P04-rq2')
paragraph('第一章介绍研究背景、',"""第一章从监督漂移与结构恢复两个问题出发，比较相关方法并明确成果归属。第二章统一原生任务、完整对象评价与公共协议。第三章研究关系影响域约束的增强与成对学习，区分数据构造、学习目标及中心选择。第四章研究依赖闭合事务，并以同评分全局求解检验其使用条件。第五章围绕阶段增量、对象重叠、训练对修正条件的影响、配置选择和最终失败开展综合分析。第六章总结研究认识与适用范围。""",'P08-outline')
paragraph('附录补充复现协议、',"""附录A、B集中保存坐标、序列化、执行边界及性质证明，附录C、D说明成果和构造材料，附录E保留历史数值，附录F提供阅读索引。附录G记录外部方法核查及接入协议，附录H给出诊断、表达变化、资源和对象轨迹的取证规则。正文保留影响研究判断的定义与假设，完整实现细节按引用查阅。""",'P08-appendix-map')

# Move machine-level details, retaining the concept in chapter 2.
serial=section('以下人为构造的token序列为','### 2.3 生成建模',"""组件序列化与关系引用采用固定字段顺序；类型门控只读取已经生成的前缀。完整示例、坐标往返和异常处理见附录A.6。统一sources字段只是表示入口，多前提任务还需候选、评分、优化与评价共同保留完整源集合。""",'P08-serialization')
moved.append(('序列化与字段顺序',serial))
paragraph('局部与全局ILP采用一致的软件、',"""局部与全局ILP首先比较相同逐文档总求解预算，另以相同端到端时限评价部署条件；两种预算分别命名。软件、线程、缓存条件和共同准备开销保持一致，大预算结果不自动视为最优。核心比较包括相同增强集合上的成对项增量、BR-J与组件优先分步策略，以及BR-J与等求解预算全局ILP的差异。其余消融和交互用于解释机制。95%区间为固定三种子条件下逐比较的文档配对区间，未作多重比较校正；区间跨零不能解释为等效。完整求解状态、成本记录和统计规则见附录H.3。""",'P04-public-budget')

# Training chapter: diagnosis, declared tracks and two minimal diversity measures.
section('### 3.1 引言','### 3.2 前期专项建模基础',"""### 3.1 引言

训练数据增强的关键问题，是文字发生变化后，组件角色与关系监督还能否被可靠继承。只看流畅度或组件含义，可能漏掉跨出改写区域的关系；只检查已有正关系，也可能遗漏原NONE组合被改写成支持关系的情况。关系影响域因此决定需要复核的对象，而原文与增强文的标注对应决定哪些监督可以共同学习。

表3-NEW将问题观察与设计连接起来。真实诊断使用训练侧固定持出文档，在选择中心、阈值和提示前冻结抽样；四层均记录源文档数、变体数、被审因素数和漂移数。现有因素记录属于人工情景，真实数量级尚不由本版建立；具体抽样与分母见附录H.1。

表3-NEW 训练侧诊断与方法响应（诊断方案）

|观察对象|计数单位与分母|对应设计|
|:---|:---|:---|
|内部正关系|改写区内被审正关系因素|检查原有角色、方向与标签|
|跨边界正关系|连接区内外的被审正关系因素|把区域外端点纳入条件|
|内部NONE|区内被审无关系组合|识别改写新引入的关系|
|跨边界NONE|区内外被审无关系组合|避免只保护显式已有边|

本章提出关系影响域约束的增强与成对学习：按完整端点依赖检查改写，迁移通过检查的标注，再将两视图的组件与关系因素对应用于共享表示学习。结论优先是默认区域选择策略，其价值由匹配随机中心对照检验；即使中心差异不稳定，监督对应和成对学习仍有各自可检验的问题。前期结论专项适配、提示与句子监督提供生成基础[34]，LoRA、辅助头与JS散度作为实现机制说明。

图书馆片段用于解释语义如何漂移，表3-NEW用于规定如何观察其发生频率。方法在原生组件类型和完整关系上展开，AAEC的stance不转换为普通边，CDCP的结论角色也不改变原生类型。下文先说明继承接口，再给出影响域、对应构造和成对目标，实验分别检验质量、表达变化、任务收益和成本。
""",'P01-P02-ch3-intro')
change('|T-B QOS式与完整增强|共同接口、评价及资源轨道|数据构造策略的差异|','|T-B QOS式与完整增强|相同基础损失、匹配训练规模与更新条件|比较数据构造，不与T1全机制混比|','P02-tb-loss')
paragraph('生成侧同时保留固定尝试预算和匹配训练规模两条轨道。',"""构造轨道固定每篇源文档最多4次尝试、接受2个变体，用于比较生成池、接受覆盖和构造成本。主成绩轨道匹配训练规模：AAEC与CDCP分别使用500和900个变体、0.82M和1.35M增强token，并匹配源文档采样规则和有效更新条件。表3-5、3-6和3-8属于后一轨道；表3-9只报告前一轨道的构造成本。两轨不拼接为同资源优势。""",'P02-two-tracks')
change('表3-5 训练方案的严格抽取结果','表3-5 训练方案的严格抽取结果（匹配训练规模）','P02-main-track')
change('表3-6 相同增强集合上的学习目标比较','表3-6 相同增强集合上的学习目标比较（匹配训练规模）','P02-loss-track')
change('表3-8 结论中心与匹配随机中心的比较','表3-8 结论中心与匹配随机中心的比较（匹配训练规模）','P02-center-track')
paragraph('T1相对T0在AAEC与CDCP上的严格关系F1分别增加',"""T1相对T0的严格关系F1分别增加7.32和7.21个百分点，这一总差值包含数据构造、头监督和成对学习。数据构造作用由T-B单独解释：QOS式适配与完整增强都采用基础损失，对照表3-6首行，AAEC为55.68对57.47，CDCP为50.25对52.08，差值分别为1.79和1.83个百分点。过滤消融另在共同生成池和相同学习配置下变化审核项，反映跨边界正关系与NONE检查的条件作用。它们不能将T1的全部增量归给增强、中心或某一个损失项。""",'P02-data-effect')
insert_before('#### 3.6.3 抽取结果与学习目标消融',"""表达变化另按变体统计，不能由因素漂移率推出。生成池与接受池分别报告非复制比例，并在实际允许改写的组件区域计算规范化编辑距离的中位数与四分位区间。距离只按一一对应的改写槽位计算，不让全文未改区域稀释变化；解析失败单列，不从总尝试账本消失。

表3-DIV 表达变化与选择偏向的检查项目（诊断方案）

|指标|观察单位|配套分组|
|:---|:---|:---|
|非复制比例|生成池／接受池中的可解析变体|源文档、长度、关系复杂度|
|规范化编辑距离|同一变体的可改写槽位token|中位数、四分位区间与零值比例|
|接受覆盖|源文档是否至少有一条合格变体|短／长、低／高关系度及隐式关系|

只有在表达变化仍然充分、源覆盖没有集中于容易文档时，低漂移才支持“可靠且有变化的增强”。当前计数记录不含原始增强文本，表3-DIV规定分析口径而不填造距离分布。因素审计继续用于标签保持判断；本章不主张筛选器的变体级精确率，因而也不把拒绝层中的稳定因素视为整条变体误拒。指标公式与记录入口见附录H.2。""",'P03-diversity')
# Remove cross-track training hours from construction table; retain them in appendix H.
mt=re.search(r'表3-9 固定尝试预算下的覆盖与构造成本\n\n(\|.*?\n)(?=\n)',s,re.S)
assert mt
cost_table=mt.group(1);training_rows=[]
newrows=[]
for line in cost_table.strip().splitlines():
    cells=line.strip('|').split('|')
    training_rows.append((cells[0],cells[-1]));newrows.append('|'+'|'.join(cells[:-1])+'|')
change(cost_table,'\n'.join(newrows)+'\n','P02-cost-separation')
paragraph('表3-9记录固定尝试预算轨道的构造覆盖和成本，',"""表3-9仅记录固定尝试轨道的覆盖、生成与审核成本，拒绝和失败尝试也计费。完整方案在AAEC、CDCP分别接受520、940个变体，覆盖292、522篇源文档；匹配规模轨道再按预定规则组织500、900个变体。原记录中的训练GPU小时属于固定尝试情景，移至附录H.2存档，不作为匹配规模主成绩的成本。正式比较同时保存两轨的样本清单和训练账本，再讨论任务收益是否值得其投入。""",'P02-cost-analysis')
paragraph('表3-3列出接受样本的四类漂移率。',"""表3-3中，完整方案的接受层分层均值为3.62%和5.75%，低于普通增强与QOS式适配。各层的差异并非在所有方法和语料上同向；例如CDCP普通增强的内部NONE高于内部正关系，说明因素身份需要分别保留。表中跨边界风险为影响域检查提供情景化解释，真实设计必要性则需由训练侧诊断验证。完整方案还伴随覆盖下降，质量、变化幅度和源分布应联合解释。""",'P03-drift-tone')

# Inference motivation, candidate growth, strong global comparison and auditable evidence.
insert_before('本章方法记为MCR-BR-J，',"""表4-NEW给出进入复杂修正前需要观察的错误。组件诊断以严格匹配为基础；对未匹配对象，先检查完全相同跨度但类型错误，再在剩余对象上按token交并比和坐标顺序做一对一诊断匹配，区分边界误差与遗漏／多检。此匹配只解释错误，不改变主F1。关系按全部端点是否正确分层，候选缺失再作为独立可恢复条件交叉统计。

表4-NEW 初始错误诊断与恢复条件（诊断方案）

|观察对象|分母与归类规则|对应问题|
|:---|:---|:---|
|组件类型、边界、遗漏／多检|未严格匹配组件；按固定顺序归类|是否需要允许组件集合变化|
|端点未全正确的金标关系|金标完整关系；全部端点共同判断|上游组件错误限制了多少关系|
|端点正确但关系错误|端点均命中的金标关系|纯关系判断的剩余空间|
|候选未覆盖的组件／关系|分别使用金标组件／完整关系|增加求解时间是否有恢复对象|

上述维度不直接相加为互斥因果比例；尤其候选缺失与组件错误可以重叠。诊断使用训练侧持出预测，记录文档、对象和候选快照，方法冻结后才在独立评价中复核。当前人工计数没有完整原文与模型预测，表4-NEW说明取证方式，不能据此声称已得到现实错误分布。""",'P01-inference-diagnosis')
paragraph('据此，本章将问题定义为有预算的结构选择。',"""据此，本章将问题定义为有预算的结构选择，并把同候选、同评分的全局ILP作为主要竞争方案。局部事务能明确一次变更及其依赖，但全局求解也可能提供更好的结构与保留率。研究重点是在共同准备成本、求解预算和变更要求下比较二者，而非将局部性、日志或有限终止直接视为优势。若真实比较不能形成有价值的质量、时延或变更控制取舍，则应简化局部机制或将其保留为可选修正策略。""",'P04-inference-position')
p=paragraph('独立跨度头使用全文编码器和两个线性层，',"""独立跨度头以训练金标监督起止边界，为候选召回提供补充，并在OOF中遵守与生成器相同的持出隔离。参考解码与一次性有限扩展覆盖邻近边界、相邻跨度合并和内部切分；扩展不递归，去重后才按边界分保留补充候选。坐标转换、排序和异常细则见附录A.6，边界分仅用于召回排序。""",'P08-span-interface')
moved.append(('跨度头坐标与解码',p))
p=paragraph('参考有限扩展对受保护跨度及跨度头前',"""受保护跨度不受补充长度和数量上限裁剪。候选的保护来源、补充来源及重叠数量分别登记；新增跨度不能通过改变去重或坐标规则隐式扩张候选空间。""",'P08-finite-expansion')
moved.append(('有限扩展与去重',p))
p=paragraph('对$u\\in U$保留协议合法的全部类型，',"""对$u\\in U$保留协议合法的全部类型，构成$\\mathcal V=\\{(u,t):t\\in\\mathcal T(u)\\}$。NULL表示不选择，同一跨度至多一个类型。组件兼容按语料协议逐对判定；语义身份取决于规范跨度和类型，显示ID不进入评分。完整键与坐标映射见附录A.6。""",'P08-object-keys')
moved.append(('对象键与兼容判定',p))
insert_before('### 4.3 依赖闭合的组件集合事务' if '### 4.3 依赖闭合的组件集合事务' in s else next(x for x in s.splitlines() if x.startswith('### 4.3 ')),r"""#### 4.2.5 裁剪前规模与资源预检

保留4096个补充槽位，只约束最终进入搜索的数量。设候选宇宙含$m$个可区分跨度、每跨度至多$q$类，在忽略冲突和标签掩码的宽松计数下，AAEC有至多$m(m-1)q^2$个带类型端点槽位；CDCP新增源成员数不超过3时，枚举规模可达$\sum_{k=1}^{3}C(m,k)(m-k)q^{k+1}$。其中$C(m,k)$为组合数。实际合法性会减少数量，受保护长超边则另行加入。该计数说明候选补充的组合增长发生在裁剪之前，并不等于实测内存或运行时间。

因此预检同时记录受保护／补充跨度、带类型组件、裁剪前完整槽位、全部标签评分对象、评分批次与峰值占用。阈值只在训练侧资源探测中确定，并写入冻结配置；正式文档超限即返回有原因的构造失败，保留已消耗时间，金标仍进入FN与失败率。若保护部分已超限，不得静默删除初始正确对象。

当前保持既定候选策略，以实际规模测量决定是否需要改变它。若裁剪前枚举不可承受，再比较预筛选或受限生成，并重新测量覆盖及完整关系遗漏；所有局部／全局对照都使用改变后同一候选快照。资源字段及失败分母见附录H.3。
""",'P05-prepruning')
paragraph('局部事务的价值通过有限算力下的修正质量、',"""局部事务的价值由质量、端到端代价和变更要求共同决定。主比较首先固定每文档总求解上限，另设端到端时限相同的比较；后者扣除候选准备、裁剪前评分与失败尝试后，将剩余时间分配给各自策略。少量预算点和图规模分组在训练侧确定，报告平均与P95时延、超时、无可行解、F1及误改。当前情景只提供等求解预算行，不能将其改称为等端到端时限实验。若引用全局界，还需记录incumbent、有效bound、gap和最优性状态，详见附录H.3。""",'P04-global-protocol')
paragraph('BR-J的平均总时间为32.00秒和45.16秒，',"""BR-J相对等求解时限全局ILP节省的平均总时间仅为4.19%和4.73%，关系F1按未舍入值计算分别低0.40和0.50个百分点。表4-7中全局方法的初始关系TP保留率也略高，因此当前情景没有支持“局部更安全”或突出的效率优势。按已有成本分项，BR-J求解仅占总时间的5.00%和5.67%；大部分时间在生成与评分，单独加速局部求解难以等比例改善整体时延。这些是人工成本设定下的算术关系，真实适用条件须由完整资源轨迹决定。冷启动、缓存和一次性准备费用单独报告，不将GPU小时、CPU秒与token互相换算。""",'P04-global-tradeoff')
paragraph('从一轮增加到两轮带来较明显改善，',"""轮数曲线显示当前情景的边际增量逐步减小。图中局部轮数与全局时限属于不同控制量，只能结合实际端到端时间阅读；它还不能证明大图或紧预算下局部方法必然更优。完整调度边界见算法4-1、4-2及附录B.4.3。""",'P08-budget-prose')
paragraph('表4-9围绕组件边界、',"""表4-9以人工片段说明组件边界、完整源集合和接受门的作用，属于机制案例。正式实验案例按附录B.5和H.4保存完整原文、金标、初始与最终对象，并记录每项删除／新增、受影响关系、分项分数、门限和求解状态。可复核轨迹需能重算该次接受或拒绝，不能仅凭一条成功日志认定预测更可信。""",'P04-case-evidence')
paragraph('本章将组件集合替换与全部受影响关系重建组织为共同事务，',"""本章以组件集合替换和完整关系重建形成结构事务，分析其表达能力及预算内决策。人工情景中的BR-J优于所定义的分步策略，但等求解预算全局ILP取得略高关系结果与保留率，仅付出小幅总时间增量。因而局部方法的使用价值仍取决于实际预算、候选规模和变更要求。下一章把这些取舍与训练条件共同分析，识别可由现有计数支持的结论及需要完整对象轨迹的问题。""",'P04-ch4-summary')

# Move detailed proofs but retain all displayed equations and theorem statements.
for prefix,replacement,key in [
('两状态共有对象的得分相同，','固定评分使共同对象抵消，完整依赖重建使差集覆盖所有改变的关系。详细推导及评分变化时的适用边界见附录B.6。','P08-proof1'),
('构造两个互不重叠的旧组件','附录B.6给出两个旧组件合并为一个新组件的合法构造：单对象严格改进无法通过，整体替换可以通过。该反例刻画动作表达能力，不提供真实F1保证。','P08-proof2'),
('证明：若回到某个已访问状态','严格增加同一固定效用排除状态重复；有限候选空间使接受序列有限。证明及预算停止的区别见附录B.6。','P08-proof3')]:
    p=paragraph(prefix,replacement,key);moved.append(('固定评分下的性质说明',p))

# Store training-hour archive and moved details for the remaining composition step.
(W/'revision_stage1.md').write_text(s)
(W/'edit_stage1.json').write_text(json.dumps({'edits':edits,'moved':moved,'training_rows':training_rows},ensure_ascii=False,indent=2))
print('stage1',len(s),len(edits))
