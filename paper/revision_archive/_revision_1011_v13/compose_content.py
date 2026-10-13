"""Version-bound v13 content revision; no model training or page rendering."""
from pathlib import Path
import sys,re,json,hashlib,difflib,statistics
W=Path(__file__).resolve().parent;R=W.parent;sys.path.insert(0,str(R/'research_1011_v13'))
from common import read,dump,sha
BASE=R/'report_1011_v12_content.md';DEST=R/'report_1011_v13_content.md'
old=BASE.read_text();text=old;ops=[]
def repl(a,b):
 global text
 assert text.count(a)==1,(a[:100],text.count(a));text=text.replace(a,b);ops.append({'anchor':a[:110],'old_chars':len(a),'new_chars':len(b)})
def seg(a,b):return text[text.index(a):text.index(b,text.index(a))]
def block(a,b,new):repl(seg(a,b),new.rstrip()+'\n\n')
def before(a,new):repl(a,new.rstrip()+'\n\n'+a)
def f(x,n=2):return f'{x:.{n}f}'
def tbl(title,heads,rows):return title+'\n\n|'+'|'.join(heads)+'|\n|'+'|'.join([':---']*len(heads))+'|\n'+'\n'.join('|'+'|'.join(map(str,r))+'|' for r in rows)+'\n\n'
S=read(R/'research_1011_v13/simulation/results.json');A=read(R/'research_1011_v13/acceptance_scenario/summary.json');K=read(R/'research_1011_v13/cases/case_records.json');E=read(R/'research_1011_v13/simulation/error_chain.json');M=S['metrics'];P=S['paired'];L=S['labels']
def metric(ds,m,o='relation'):
 z=M[ds][m][o];return f(z['mean'])+'±'+f(z['sd'])
def four(m):return [metric(d,m,o) for d in ['AAEC','CDCP'] for o in ['component','relation']]
def diff(d,a,b):return M[d][a]['relation']['mean']-M[d][b]['relation']['mean']
def ci(d,a,b):
 z=P[d][a+'__'+b+'__relation'];return [f(z['delta']),'['+', '.join(f(v) for v in z['ci95'])+']']
def citable_case(cid):
 book=(R/'1011_v13真实语料案例册.md').read_text();start=book.index('## '+cid+' ');end=book.find('\n## ',start+3);s=book[start:end if end!=-1 else len(book)].strip();return s.replace('## '+cid+' ','**'+cid+' ',1).replace('\n\n','**\n\n',1)
block('1011-v12 内容迭代预览','英文题目', '''1011-v13 内容完善与模拟验收版　2026年10月11日

稿件说明：本版按“剩余研究条件在模拟情景中均满足”编写完整研究叙事，供后续内容评审。主表来自真实AAEC、CDCP训练文本上的构造预测图，明确使用金标设计预期结果；它们不是训练后模型输出或独立测试成绩。人工审核、训练验收、评分及目标GPU成本的补充数值也均标为模拟。真实语料与标注、既有Luna输出和本轮构造输入上的求解运行分别保留来源。E1—E8为作者自定的预览验收项，均为PASS_SIMULATED，不代表学校或审稿人通过。本版仅修改内容，未制作Word/PDF。''')
block('## 摘要','## Abstract',f'''## 摘要

端到端论辩挖掘需要同时识别文本组件、论辩角色和有向关系。组件与关系的依赖使局部改写和预测修正都可能产生连锁变化。本文以ICIC的多候选重排序与有界修正为基础，研究可靠对应因素上的成对学习，以及依赖闭合的结构修复。

训练方法通过组件核查与关系因素掩码确定原文和变体之间可继承的监督。原文承担完整图生成目标，变体仅在通过检查的因素上提供辅助监督和分布对齐。完整影响域整例筛选作为可选对照。推理方法分别提出原生组件与完整关系候选，显式区分未评分与低分，将组件变化及关联关系重建统一评价；在开发侧固定的风险与资源规则下选择单对象、集合局部或全局求解。

数值研究采用明确构造的正向情景：在319篇AAEC及580篇CDCP训练侧文本上，为25种方法、3个种子建立67425个预测图。完整框架的组件F1为{metric('AAEC','t1_i1','component')}、{metric('CDCP','t1_i1','component')}，严格关系F1为{metric('AAEC','t1_i1')}、{metric('CDCP','t1_i1')}；相对同口径ICIC继承参照情景，关系提高{f(diff('AAEC','t1_i1','t0_i0'))}、{f(diff('CDCP','t1_i1','t0_i0'))}个百分点。逐对象分析显示端点遗漏减少与端点具备后的关系选择改善可以同时贡献收益，但交互区间不支持宣称超加性。真实文本案例展示角色保持、联合源完整性、候选缺失和误改的差异；构造评分上的16次实际机制运行进一步说明集合动作的可达性及错误评分的限制。

上述模拟结果用于检验研究论证与报告的一致性，不作为目标模型有效性的实证证明。既有Luna诊断及CasiMedicos的少量正确输出、大量误边均保留，实际执行状态集中列于附录。本文据此给出两阶段框架的适用条件与后续实证替换接口。

关键词：端到端论辩挖掘；可靠对应；成对学习；依赖闭合；图修正；结构化预测''')
block('## Abstract','## 第一章',f'''## Abstract

End-to-end argument mining jointly identifies text spans, argumentative roles, and directed relations. Their dependencies make both training paraphrases and prediction edits potentially affect multiple objects. Building on ICIC candidate reranking and bounded repair, this thesis studies paired learning over reliable correspondences and dependency-closed structural repair.

The training method uses component checks and relation masks to identify transferable supervision. Original texts retain full-graph generation targets; augmented views contribute auxiliary supervision and alignment only on checked factors. Whole-view filtering is an optional control. The inference method separates native component and complete-relation proposals, distinguishes missing scores from low scores, and evaluates endpoint changes with their dependent relations. Single-object, local set-level, and global solvers are selected under fixed development-side resource and risk rules.

The numerical study is an explicitly constructed positive scenario over 319 AAEC and 580 CDCP training texts, comprising 67,425 graphs for 25 configurations and three seeds. The complete-system component F1 scores are {metric('AAEC','t1_i1','component')} and {metric('CDCP','t1_i1','component')}; strict relation F1 scores are {metric('AAEC','t1_i1')} and {metric('CDCP','t1_i1')}, exceeding matched simulated ICIC reference outputs by {f(diff('AAEC','t1_i1','t0_i0'))} and {f(diff('CDCP','t1_i1','t0_i0'))} points. Object-level analysis distinguishes endpoint availability from subsequent relation selection and does not establish super-additive interaction. Source-linked examples and 16 actual solver runs on constructed scores illustrate native source groups, action reachability, and scoring failures.

Gold labels informed the simulated outputs. These results support an internally consistent authoring scenario, not empirical claims about a trained target model or held-out generalization. Existing Luna diagnostics, including harmful edits and limited CasiMedicos success, retain their original evidence status. The thesis specifies the conditions and interfaces needed to replace the scenario with controlled experiments.

Keywords: End-to-End Argument Mining; Reliable Correspondence; Paired Learning; Dependency Closure; Graph Repair; Structured Prediction''')
block('#### 2.5.1 与ICIC的双协议比较','### 2.6 公共实验协议', '''#### 2.5.1 与ICIC的协议关系

ICIC公开表为历史来源值。本版主表只使用一套与真实文本关联的原生对象情景，双方配置都在同一文档、金标和字符键下计数。T0/I0代表完整继承配置的模拟输出，并非复现得到的检查点；不能把它与公开ICIC值混称为同次实验。

旧版按ICIC原协议尺度设定的目标仍作为历史规划值保留于5.1节。它与本版原生图不构成可逆投影，不计算跨协议提升。实际复现需分别核准原划分、跨度、类型、stance及CDCP转换，并使双方预测共同进入各自评价器。

#### 2.5.2 本版原文与模拟对象的对应

本版直接读取已下载的官方训练档案：AAEC原训练清单322篇，按原文哈希去重后319篇；CDCP原训练581篇，沿用00411的既有异常排除后580篇。共含8694个原生组件、3975条完整关系，其中CDCP有85条多源关系，最长8个源成员。重复组和排除原因逐项保存在数据清单，未把重复文本当独立文档。

本版模拟使用原生半开字符坐标，按明确规则修整跨度首尾空白，原坐标、变化及原文均保留。它不声称旧token映射问题已经修复。2.1节的token表示仍是目标训练接口；实际运行须完成字符到token的可逆映射。本轮不读取官方测试文本，不产生独立测试成绩。

每个模拟错误组件由原生跨度的截短、类型替换或遗漏构成；每条关系引用实际被选组件的完整身份。全部预测图满足本情景冻结的非重叠、端点存在、槽位互斥及CDCP源组连续约束，无环及单出度未设为主情景硬约束。构造过程读取金标以控制预期效果，方法名称表示输出情景的假设条件，不代表相应训练或求解器已经运行。''')
block('表2-2的320篇与580篇','评分器使用训练侧OOF记录', '''本版模拟材料为上一节的319／580篇训练侧文档。三折OOF、拟合—校准—策略隔离和独立测试属于目标模型的实验方案：原文及所有变体必须同折，每折生成器和跨度头排除持出源文档；所有评价与调参职责在读取独立测试标签前冻结。本版主图模拟不执行这些训练步骤，也不把训练语料上的构造计数解释为持出结果。''')
repl('AAEC三部分为256、32、32篇，CDCP为464、58、58篇，组间没有共享原文或变体。','按照当前去重规模，拟定AAEC三部分为255、32、32篇，CDCP为464、58、58篇；正式清单须按源哈希冻结并确认组间不共享原文或变体。')
repl('|材料规模|AAEC训练侧320、独立评价80；CDCP训练侧580、独立评价148|训练侧含拟合、校准与策略用途；按源文档分组|','|本版图模拟材料|AAEC 319、CDCP 580篇去重训练侧文本|均非独立测试成绩；官方测试未读取|')
repl('配套v12 preview_config.json保存更新后的设计参数','配套v13 preview_config.json保存更新后的设计参数')
# S1: replace obsolete full-reject raster with two explicitly separate paths.
block('![关系影响域中的内部与跨边界组合]','对训练金标图 $G=(C,R)$',r'''```mermaid
flowchart TD
  A[原文金标与固定改写组件集合] --> B[回填改写并核查格式和组件意义]
  B -->|格式失败或组件变化及待定| X[拒绝本视图并保留原文]
  B -->|通过| C{审核策略}
  C -->|默认因素掩码| D[全部受影响正关系及抽样 NONE]
  D --> E[可靠因素参与监督和对齐]
  D --> F[变化及待定或未审核因素掩码为零]
  C -->|完整筛选对照| G[检查完整影响域全部可审核因素]
  G -->|任一失败或资源不足| X
  G -->|全部通过| H[接纳整例的可审核因素]
  E --> I[原文完整生成与变体可靠因素学习]
  F --> I
  H --> I
```

图3-1 默认因素掩码与可选完整筛选的不同接受路径

“内部／跨边界”描述端点与改写集合的位置关系，“正关系／NONE／语义未知”描述因素状态，二者分别记录。默认路径保留有效组件，屏蔽关系层面的不确定监督；完整筛选路径才因任一可审核因素失败拒绝整例。已知联合源真子集的语义未知状态按3.3.4节处理，不伪装成已经确认的NONE。

''')
# S2 explicit full-domain algorithm branch.
repl('每文档尝试上限 B_try、接受上限 B_accept，训练更新上限 U。','每文档尝试上限 B_try、接受上限 B_accept，训练更新上限 U，\n      审核模式 mode ∈ {FactorMask, FullFilter}。')
repl('16        按固定 J_A 复核原／新状态，建立可靠因素掩码 m_R', '16        if mode = FullFilter then J_A ← D_A；不可完整审核则拒绝本次视图\n16a       else J_A ← 全部受影响正关系 ∪ 固定抽样内部及边界 NONE\n16b       在 J_A 中排除已定义的语义未知因素，逐项核查原／新状态并建立 m_R')
# S3 semantic unknown vs exact absence, applied to both training views.
before('### 3.4 成对组件与关系学习',r'''#### 3.3.4 CDCP联合源子集与NONE的区别

严格抽取评价只问一个完整对象是否在金标中。若金标为 $h=(\{c_1,c_2\},c_3,\mathrm{Reason})$，预测 $(\{c_1\},c_3,\mathrm{Reason})$ 就是不同对象，不能匹配该金标。但是完整联合理由成立，不推出单一成员在语义上既不支持也不反对目标。

为此，训练语义头另定义未知集合 $\mathcal U_{sem}$：对已标注联合源，若同目标的非空真子集没有任何单独正关系标注，则将该端点因素列为语义未知。显式正标注优先，不屏蔽已有单源正关系。$\Omega_{sem}=\Omega\setminus\mathcal U_{sem}$ 为可审核因素宇宙，完整影响域与抽样集合均在该宇宙内定义。完整筛选的“全部”指这里已声明的可审核域，未知项另计数量，不称为已经通过。

原文和变体的语义关系头均不把 $\mathcal U_{sem}$ 当作NONE负例；相应监督与对齐掩码都为0。原文完整生成目标仍保留原始超边，金标不删不改。第四章评分器预测的是“完整对象是否与标注精确匹配”，因此该真子集可作为完整对象不匹配的负例，其0标签不解释为语义上没有关系。推理NONE继续表示该槽位未选正关系。由此分开标注存在性、语义审核与推理决策三种用途。

''')
repl('原文辅助监督 $S(x,G)$ 使用全部原生组件及声明因素；','原文辅助监督 $S(x,G)$ 使用全部原生组件及可审核因素 $\Omega_{sem}$，语义未知集合不参与关系头监督；')
repl('原文全部头监督及变体掩码内的头监督','原文可审核因素的头监督及变体掩码内的头监督')
repl('本节因素掩码为v12待验证设计','本节因素掩码为当前研究设计')
# Results: regenerate every main table from one endpoint-linked graph collection.
train_methods=['t0_i0','original_heads_i0','plain_i0','qos_i0','simple_data_i0','head_i0','t1_i0','full_filter_i0','random_i0']
new='''### 3.6 实验结果与分析

#### 3.6.1 比较口径与贡献拆分

本节在同一批真实文本上构造预期输出，固定推理配置I0，将T0与T1表示为继承训练和新训练的情景条件。数值由完整预测图计算，未执行对应模型训练。普通增强、QOS式适配、可靠对应使用同规模与同辅助头的假设条件；成对学习对照固定视图和掩码。这样明确每行应由何种真实实验替换，不把模拟排序当作机制被证实。

'''+tbl('表3-2 训练侧比较的固定条件',['比较','固定项','变化项','解释范围'],[
['数据构造','骨干、辅助头、I0、规模与预算','普通／QOS式／可靠对应','构造方案整体差异'],['成对目标','同一视图与掩码、辅助头、I0','无成对／组件／组件及关系','目标函数条件增量'],['完整筛选','生成池、尝试预算与目标','因素掩码／整例拒绝','审核与源覆盖取舍'],['中心选择','区域规模、输入长度与更新预算','结论／匹配随机中心','区域选择的附加作用']])
new+='#### 3.6.2 严格抽取结果\n\n'+tbl('表3-3 训练方法的条件结果（真实文本上的模拟预测；固定I0）',['方法','AAEC组件','AAEC关系','CDCP组件','CDCP关系'],[[L[m]]+four(m) for m in train_methods])
new+=f"T1相对继承参照情景的关系增量为{f(diff('AAEC','t1_i0','t0_i0'))}和{f(diff('CDCP','t1_i0','t0_i0'))}个百分点。固定同一可靠视图后增加关系成对项的增量为{f(diff('AAEC','t1_i0','head_i0'))}和{f(diff('CDCP','t1_i0','head_i0'))}个百分点。总增量包含候选与输出分布随训练条件改变的作用，不能全部归于成对项。\n\n"
comparisons=[('可靠对应−QOS式','simple_data_i0','qos_i0'),('组件成对项','head_i0','simple_data_i0'),('增加关系成对项','t1_i0','head_i0'),('完整筛选−默认掩码','full_filter_i0','t1_i0'),('随机−结论中心','random_i0','t1_i0')]
new+='#### 3.6.3 关键比较与解释\n\n'+tbl('表3-4 关系F1差值与文档配对区间（模拟）',['语料','比较','差值pp','95%区间'],[[d,label]+ci(d,a,b) for d in ['AAEC','CDCP'] for label,a,b in comparisons])
new+='''三个种子及全部唯一文本共同进入配对重采样。区间表示该构造情景中的文档差异，不是目标模型总体效果的置信保证。两项核心条件增量可按预期通过，同时允许完整筛选、中心选择或关系成对单项区间跨零；这些可选模块不作为“全部要求满足”的额外必要条件。

#### 3.6.4 审核与训练验收情景

补充验收从既有改写池选取128个组件项目，覆盖32个文档ID下的63个改写视图；每项目保存两路构造判断及一个构造参照。模拟一致率97.66%，Cohen’s κ为0.9202；模拟接受110个组件项目，其中2个被构造参照标为不安全，比例1.82%。这些数值回答“审核质量达到预览标准时如何报告”，并未新增人工审核者，也未把旧模型判断换名为人工答案。

训练日志补充包含两语料、三种子、八个检查点的模拟学习曲线，以及十项实现验收的假定通过状态。损失、梯度和冻结字段均为构造验收输入；不能据此声称已启动训练入口。默认因素掩码保留通过检查的监督，完整筛选另计生成拒绝、源覆盖和审核成本，不用重复少量通过样本补齐规模。全部预览验收项及其标准集中于附录H。

'''
block('### 3.6 实验结果与分析','#### 3.6.5 Luna改写与筛选的真实诊断',new)
before('### 3.7 本章小结','''#### 3.6.6 原文案例与可靠因素的解释

以下案例从既有实际改写中按问题类型选择，不作为漂移发生率的估计。完整回填文本和原审核记录保存在案例数据中；本节用它们解释新规则。

'''+citable_case('K01')+'\n\n'+citable_case('K02')+'\n\n'+citable_case('K03')+'''

前两例说明文字变化与原生角色保持可以同时成立；第三例说明组件意义待定时应拒绝视图。若只有关系状态待定而组件检查通过，默认方法屏蔽该关系及其对齐项、保留其余可靠组件。这两种动作取决于不确定性所在层次，不由“审核更严格”统一替代。

''')
# Update repair intro, without changing the actual historical diagnostic blocks.
repl('同一T1生成检查点提供MCR初始图，所有受控动作比较使用相同候选、完整对象分及合法化规则。','目标受控实验规定同一T1检查点提供MCR初始图，并固定候选、完整对象分及合法化规则；本版主表只构造这些方法的预期输出，没有实际检查点或评分驱动轨迹。')
repl('受控求解表使用共同快照，避免把前端差异归给动作或搜索。','实际构造机制比较使用共同快照；主模拟对象宇宙含金标，仅用于身份对齐，不是盲提案覆盖或受控求解的实测证据。')
inf_methods=['mcr_t1','t1_i0','br_c','relation_only','sequential','single_object','brj_local','global_equal','global_long','t1_i1','uncalibrated','missing_as_low','no_risk_guard','regenerate_equal_tokens']
# Resolve inherited method key without guessing it.
if 'regenerate_equal_tokens' not in L:inf_methods[-1]=next(k for k,v in L.items() if '重生成' in v)
new='#### 4.6.2 正向情景下的质量比较\n\n'+tbl('表4-2 严格原生对象下的推理结果（真实文本上的模拟预测）',['方法','AAEC组件','AAEC关系','CDCP组件','CDCP关系'],[[L[m]]+four(m) for m in inf_methods])
new+=f"完整I1在T1条件下比继承策略提高关系F1 {f(diff('AAEC','t1_i1','t1_i0'))}和{f(diff('CDCP','t1_i1','t1_i0'))}个百分点；相对固定组件的RelationOnly提高{f(diff('AAEC','t1_i1','relation_only'))}和{f(diff('CDCP','t1_i1','relation_only'))}。该差异是预设方法条件下的输出差异，不能由此单独证明候选、评分或搜索中哪一项已起作用。\n\n"
comparisons=[('集合局部−单对象','brj_local','single_object'),('全局−集合局部','global_equal','brj_local'),('完整I1−固定组件','t1_i1','relation_only'),('缺失保护增量','t1_i1','missing_as_low'),('校准配置增量','t1_i1','uncalibrated')]
new+=tbl('表4-3 关键推理差值及配对区间（模拟）',['语料','对照','差值pp','95%区间'],[[d,label]+ci(d,a,b) for d in ['AAEC','CDCP'] for label,a,b in comparisons])
new+='全局等预算与大预算可能具有更高F1，但可行域包含只能约束同一代理目标的最优值，不能推出真实F1排序。集合动作的小增量与区间跨零允许默认采用单对象；第四章的核心是依赖闭合及其评分条件。\n\n'
block('#### 4.6.2 正向情景下的质量比较','#### 4.6.3 候选、评分与恢复链',new)
before('#### 4.6.4 误改与资源的联合报告',r'''本版不另报未经求解的Candidate Oracle成绩。若后续报告此项，应在固定候选宇宙、明确的图约束及预算内，离线以金标匹配目标求最优可行图，并登记是否取得最优证书；“候选中含有多少正确对象”只称覆盖，不等于该Oracle。第五章端点具备率也不等于受约束可达上界。
''')
rows=[]
for d in ['AAEC','CDCP']:
 for m in ['single_object','brj_local','t1_i1','global_equal','no_risk_guard']:
  z=S['risk'][d][m];rows.append([d,L[m],z['recovered'],z['lost_tp'],z['removed_fp'],z['added_fp'],f(z['tp_retention']),str(z['worse_documents'])+'/'+str(z['document_seed_pairs'])])
new='#### 4.6.4 误改与资源的联合报告\n\n'+tbl('表4-5 相对T1的MCR初始图的关系变化（三个模拟种子累计）',['语料','方法','恢复TP','损失TP','移除FP','新增FP','原TP保留%','关系F1下降文档次'],rows)
new+='''原TP保留率的分母为共同初始图TP，下降文档次的分母为该语料文档数乘三个种子。总体F1提高不表示每篇都改善，TP保留接近100%也不表示没有新增FP。完整I1满足本版自定的5%损失预览门限，但真实风险必须在独立策略选择及评价数据上重测。

'''+tbl('表4-6 生成时延记录的均值与P95（秒；全部模拟）',['语料','配置','生成','提案','评分','求解','总均值','总P95'],[[z['corpus'],L[z['method']]]+[f(z[k]) for k in ['generation','proposal','scoring','solver','mean','p95']] for z in A['latency_simulation']])
new+='''表4-6先生成逐文档、逐种子时延记录，再求分位数；P95是这些构造记录的分位数，不是目标GPU尾延迟实测。各方法成本比例为预设情景，不以此宣称局部优于全局。成本比较保留初始化、准备、拒绝及超时的完整记录要求；本轮真正执行的小型求解耗时另列于4.6.8节。

'''
block('#### 4.6.4 误改与资源的联合报告','#### 4.6.5 冻结输入的既存求解对照',new)
# Embed real success/failure examples rather than a detached appendix only.
extra='''#### 4.6.7 真实输出中的恢复、误改与首个阻断

案例使用既有冻结预测和评分，不把它们重记为本版目标模型输出。先确定正确对象是否入池，再检查分数、选择和最后图；“解释”来自可回放的对象变化，不采用模型生成的理由作为内部因果证据。

'''
for cid in ['K04','K05','K06','K07']:extra+=citable_case(cid)+'\n\n'
extra+='''这四例分别显示恢复TP伴随FP、边界改善仍不足、候选缺失导致不可恢复，以及评分缺失或错误高分可能破坏正确结构。它们限定修正器可解决的问题：不能从不存在的候选中恢复金标，也不能以优化更充分弥补目标函数偏好错误对象。

#### 4.6.8 真实联合源上的构造机制运行

'''+citable_case('K08')+'\n\n'
F=read(R/'research_1011_v13/mechanism/summary.json');names={'native_aaec_boundary':'AAEC边界替换','native_cdcp_collective_split':'CDCP联合源拆分','native_cdcp_score_failure':'CDCP错误高分','native_cdcp_missing_score':'CDCP评分缺失'}
extra+=tbl('表4-10 固定构造输入的实际求解结果（关系F1；非模型成绩）',['构造问题','RelationOnly','SingleObject','BRJ-lite','GlobalILP-lite'],[[names.get(fixture,fixture)]+[f(next(z['R_F1'] for z in F['records'] if z['fixture']==fixture and z['mode']==mode)) for mode in ['RelationOnly','SingleObject','BRJ-lite','GlobalILP-lite']] for fixture in dict.fromkeys(z['fixture'] for z in F['records'])])
extra+=f'''本表F1的金标分母限于构造问题中列出的局部组件及一条关系，并非整篇文档的抽取成绩。四种构造输入各运行四个求解配置，共16条输出、{sum(z['solver_calls'] for z in F['records'])}次求解调用；单条运行实测耗时{min(z['seconds'] for z in F['records']):.6f}至{max(z['seconds'] for z in F['records']):.6f}秒，仅包含这组小型本地问题。AAEC边界替换可由单对象完成；CDCP合并组件必须拆成两个源成员时，集合与全局才可达。错误高分输入中所有方法均失败，评分缺失输入则保护原状态。16条结果均符合各自预设行为，不表示16次均恢复金标，更不替代主表中的目标训练或系统效果。

'''
before('### 4.7 本章小结',extra)
# Chapter five: same graph four-cell comparisons and real-text explanatory cards.
new='''## 第五章 两阶段框架的综合分析

### 5.1 ICIC继承基线与协议边界

T0表示ICIC训练配置，I0表示其多候选重排序及有界修正；T0/I0是完整继承参照情景，不能用MCR初始图替代。T1和I1分别表示新增训练及推理配置。主四格只在同一批原生对象上比较，历史引用与旧目标分开保存。

'''+tbl('表5-1 ICIC历史引用与旧协议规划目标（不参与本版配对检验）',['语料','来源','组件F1','关系F1'],[['AAEC','ICIC原协议公开引用[34]','83.71','64.83'],['AAEC','旧版设定目标中心，非实测','85.20','68.20'],['CDCP','ICIC原协议公开引用[34]','76.45','38.17'],['CDCP','旧版设定目标中心，非实测','78.30','41.50']])
new+='''原协议目标中心只说明研究规划。v12旧人工对象及整数化值保留在历史文件，本版不将它们混入真实文本关联的主图。CDCP公开38.17与下节完整源集合的严格值不作直接差分。

### 5.2 同一批原生图上的四格

'''+tbl('表5-2 四格组合的严格原生结果（全部为构造预测）',['配置','AAEC组件','AAEC关系','CDCP组件','CDCP关系'],[[L[m]]+four(m) for m in ['t0_i0','t1_i0','t0_i1','t1_i1']])
new+='''四格共用文档、金标、坐标及对象身份；预测组件和关系允许随配置变化。真实受控训练应使这些变化来自各自模型，而本版按预期分布构造。相同身份支持下列配对及成员分析，但不自动提供训练损失或推理搜索的因果证据。

'''
rows=[]
for d in ['AAEC','CDCP']:
 for label,a,b in [('仅训练增量','t1_i0','t0_i0'),('仅修正增量','t0_i1','t0_i0'),('T1下修正增量','t1_i1','t1_i0'),('组合总增量','t1_i1','t0_i0')]:rows.append([d,label]+ci(d,a,b))
 z=S['interactions'][d]['relation'];rows.append([d,'交互差',f(z['value']),'['+', '.join(f(x) for x in z['ci95'])+']'])
new+=tbl('表5-3 关系F1条件增量与交互（模拟）',['语料','效应','差值pp','95%区间'],rows)
new+='''交互差定义为F11−F10−F01＋F00。两个语料组合总增量为正，交互区间均跨零，因此不能把“结合后表现更好”解释成显著超加性。按预览要求通过的是核心条件增量与总增量，不是每项次级比较都必须显著。

### 5.3 同一完整对象的作用分解

先从两种单阶段TP中减去基线TP，再计算共同与独有恢复；组合额外增加和丢失均独立计数。三种子同一对象表示三次配对条件，不当作独立文本。

'''
fields=['both_only','training_only','repair_only','neither_single_but_combined','single_recovery_lost_in_combined','baseline_lost_combined']
new+=tbl('表5-4 关系正确对象的成员分解（三个模拟种子累计）',['语料','共同恢复','仅训练恢复','仅修正恢复','组合独有新增','单阶段恢复在组合中丢失','基线TP被组合丢失'],[[d]+[sum(z[k] for z in S['members'] if z['dataset']==d and z['object']=='relation') for k in fields] for d in ['AAEC','CDCP']])
new+='''成员不是无文本的占位ID，而是以完整端点和关系标签标识的对象。不过“训练独有”等名称只描述四格输出的集合位置，不证明一个训练因素在模型内部造成了该恢复。以下首个可观察阻断将端点不足与端点具备后的未选关系分开。

'''+tbl('表5-5 金标关系的端点与最终选择链（三个模拟种子累计）',['语料','配置','金标关系次','最终TP','端点不足','端点齐全但未选'],[[z['corpus'],L[z['method']],z['gold_R'],z['selected_TP'],z['endpoint_blocked'],z['endpoints_ready_but_unselected']] for z in E['rows']])
new+='''最后三列之和等于金标关系次。AAEC从T0/I0到T1/I1，端点不足由1624降至1435，端点齐全但未选由1695降至1577；CDCP分别由659降至583、1210降至1199。两类改善可以共存。CDCP仅训练条件下端点改善而后一类未选略增，说明更多正确端点进入图后，关系选择仍可能成为后续瓶颈。主图没有实际评分和搜索轨迹，因此不将后一类再虚分成评分失败或超时。

四格案例固定种子17，按文档与完整关系键排序选取每个结果类别的首例，不按句子可读性挑选。配套案例册给出完整原文、跨度和四张图；本节摘录如下。

'''
for c in K['four_cell_cases']:
 # Structural keys are read from persisted case records, not reconstructed prose.
 cat={'training_only':'仅训练恢复','repair_only':'仅修正恢复','both':'共同恢复','combined_only':'组合独有恢复'}[c['category']];doc=c['id'];r=c.get('relation',{})
 new+=f"**四格例：{cat}，{doc}。**\n\n"
 if r:
  for endpoint in r.get('sources',[]):new+=f"来源 [{endpoint['start']},{endpoint['end']})／{endpoint['type']}：{endpoint['quote']}\n\n"
  endpoint=r['target'];new+=f"目标 [{endpoint['start']},{endpoint['end']})／{endpoint['type']}：{endpoint['quote']}；关系标签：{r['type']}。\n\n"
 # The persisted casebook is the authoritative source for richer object quotations.
 new+='同一关系在四个配置中的状态：'+ '；'.join(f"{m}：{'命中' if z['relation_selected'] else '未命中'}，{'端点齐全' if z['gold_endpoints_selected'] else '端点不全'}" for m,z in c['states'].items())+'。这是构造输出的可观察差异，不能替代实际训练归因。\n\n'
new+='''### 5.4 原生联合源与在线配置

CDCP完整源组按1、2、3及4个以上成员分组。F1从各组TP、FP、FN计算后跨种子平均；整体F1始终从所有计数汇总，不能平均分组F1。85条多源金标均保留，包括4、5、6、8成员各2条。

'''
def sf(m,k):
 vals=[]
 for s in S['seeds']:
  z=next(v for v in S['cdcp_strata'] if v['method']==m and v['seed']==s and v['arity']==k);den=2*z['tp']+z['fp']+z['fn'];vals.append(200*z['tp']/den if den else 0)
 return f(statistics.mean(vals))
new+=tbl('表5-6 CDCP源成员分组的关系F1（模拟）',['源成员数','金标数','T0/I0','T1/I0','T0/I1','T1/I1'],[[k,{'1':884,'2':59,'3':18,'4+':8}[k]]+[sf(m,k) for m in ['t0_i0','t1_i0','t0_i1','t1_i1']] for k in ['1','2','3','4+']])
new+='''4个以上源成员只有8条金标，种子17在四格中均为零命中，另两个种子分别命中2条和1条；表中均值仍使用全部三个种子。整体情景通过不要求低频组都得到好结果。K08说明完整联合源在有限输入上的可达性，但不能填补长源组的总体统计证据。在线配置还须比较TP损失、完整准备时间与尾延迟；候选足够时优先验证单对象和全局方案，只有可达性及成本证据支持时启用集合局部。

### 5.5 本章小结

四格把相对ICIC继承参照的训练、修正和组合增量分开，同一完整对象进一步显示共同恢复、独有恢复、端点阻断及新增损失。模拟情景满足两项核心贡献的预览目标，同时保留交互不确定性、低频长源组失败和逐文档下降。真实输出案例解释方法条件，二者不合并为一个实测结论。

'''
block('## 第五章 两阶段框架的综合分析','## 第六章 总结与展望',new)
block('## 第六章 总结与展望','## 参考文献', '''## 第六章 总结与展望

### 6.1 研究总结

本文围绕组件与关系依赖提出两项研究内容。训练侧用影响域定位可能变化的监督，用标注输运维护身份，用因素掩码确定可学习的对应；原文保留完整生成目标，可靠因素承担变体监督及成对学习。完整筛选与中心选择保留为可选策略，避免把额外审核本身等同于贡献。

推理侧分别组织原生组件和完整关系候选，将组件变化与依赖关系作为共同决策；缺失评分保护、训练侧风险规则及有限预算约束修改。单对象、集合局部与全局方案共用依赖闭合语义，选择依据是可达性、评分条件与资源需求，而非预设复杂方案总能取得更高F1。

本版在真实语料上补齐预期数值、四格、成员分解和源组分析，并用真实输出及实际构造求解展示成功与失败。两项核心增量、参照比较、审核、实现、成本、统计、评分风险和研究包完整性在自定情景标准下均通过。其证据身份仍是模拟验收；实际执行状态集中列于附录H，后续可逐项替换而不改变研究问题及比较职责。

### 6.2 适用条件与局限

可靠对应依赖组件语义核查与关系状态可判定性。联合源真子集的标注缺失不等于语义无关，应在语义学习中屏蔽，同时保留严格抽取的完整对象评价。因素掩码降低错误监督风险，也减少可用监督，收益应与源覆盖及审核成本共同分析。

依赖闭合只在有限候选内工作，错误高分仍可主导最优代理解。原TP保留、较低ECE或更充分搜索均不保证真实F1单调提高。CasiMedicos既有诊断中的66条误边及修正无新增收益说明，原生边界、角色和评分应先于求解复杂度改进；复用的小样本仅支持问题定位。

当前主图按金标构造、使用训练文本，不能估计独立测试或跨语料推广效果。模拟审核和GPU分位数分别不等于人工裁决和设备实测，学校评价标准也未经过实际核准。这些身份限制不因预览条件通过而消失。

### 6.3 后续实证替换与简化原则

后续按固定数据接口依次替换ICIC参照输出、新训练输出、评分与修正记录，同时更新摘要、主表、区间和逐对象案例。训练优先验证同视图下的无成对、组件成对及完整成对；推理优先固定候选与评分比较RelationOnly、单对象及全局求解。

可选完整筛选、集合动作或局部搜索若没有额外收益，应采用简化配置并收缩对应主张。主语料保持AAEC、CDCP，CasiMedicos只作为补充诊断。内容评审通过后再进入Word/PDF排版与正式送审准备；本版保留全部历史版本和原始不利观察，便于比较修订依据。

''')
# Correct dangling Oracle cross-reference (S4) and update source registry.
repl('Oracle遵循4.6.3的松弛集合，不能调用预测效用ILP替代金标目标优化。','若报告Oracle，按4.6.3节固定候选及约束并离线优化金标匹配目标；本版仅报告覆盖，没有新增Oracle成绩。')
repl('|NONE|合法端点组合无标注或未选正关系|训练保持金标状态；推理允许纠正漏检|','|NONE|可审核语义因素无关系，或推理槽位未选正关系|联合源未知子集不作语义负例；严格对象不匹配另计|')
repl('### A.4 v12参考配置','### A.4 v13参考配置')
repl('配置身份为1011-v12-content。','配置身份为1011-v13-content。')
repl('|模块|v12预览配置|说明|','|模块|v13预览配置|说明|')
repl('历史代码和输出继续保持原版本身份，不因论文修改而宣称已经实现v12全部设计。','历史代码和输出继续保持原版本身份；新构造求解仅验证其声明的有限输入。完整训练实现另列模拟验收。')
block('v12模拟结果键为协议','v12真实诊断保存在', '''v13主表统一关联research_1011_v13/simulation中的prediction_graphs.jsonl、object_universes.jsonl和document_counts.csv。results.json汇总25个方法、3个种子的均值、标准差与配对区间；error_chain.json保存同图端点阻断统计。每张图均有原文ID、种子、方法、组件和关系键。方法标签不代表实际训练运行，实际构造求解另存在mechanism目录。\n\n''')
repl('（v12默认关闭）','（当前默认关闭）');repl('v12默认补充跨度','当前默认补充跨度')
# G2 simulated external comparators stay anonymous and use the new common graph source.
block('表G-2 匿名外部系统的数值预览','## 附录H',tbl('表G-2 匿名外部系统的数值预览（全部模拟）',['配置','AAEC组件','AAEC关系','CDCP组件','CDCP关系'],[[L[m]]+four(m) for m in L if m.startswith('external')])+'''匿名标签仅代表后续外部比较的结果槽位，不把预设分数归给任何具名论文或现成系统。本版通过的参照要求是同口径ICIC继承情景，尚未实际复现外部模型。既有文献定位表只说明相关方法，不构成具名优越性结论。''')
# Consolidate evidence disclosure and assumptions in one appendix.
new='''## 附录H v13情景验收、数据身份与复算

### H.1 本版材料及实际执行边界

主表以899篇真实训练文本为基底，构造25种方法×3种子共67425个预测图、134850行组件／关系计数。全部对象与原文跨度、类型及端点相连；构造器读取金标，不是盲测。错误对象由明确规则产生，输出分布按预期F1中心控制。共享对象宇宙是分析索引，不是实际提案模型达到的覆盖。

实际新增工作包括：读取并审计训练原文及标注，构造并复算全部预测图，整理10个真实语料案例及4个四格案例，在4组构造输入上运行16个求解配置、共26次求解调用。没有新增Qwen训练、Luna模型调用、人工审核或目标GPU测量。既有Luna输出与CasiMedicos评分沿用原始身份，未将负向观察改成预期正向结果。

### H.2 八项预览验收

这些门限是为本次内容预览自行设定的条件，不来自学校官方量表。按用户设定，八项均以模拟数据认定满足；实际事实列在上一节。次级可选模块的区间跨零、长源组零命中不与核心条件通过矛盾。

'''
requirements=[
('E1','两项核心贡献','训练增量AAEC/CDCP 2.20/1.60pp；T1下修正1.20/1.41pp，各配对下界>0'),
('E2','同口径继承参照','完整关系增量3.40/3.00pp，均≥2pp'),
('E3','审核质量','模拟一致97.66%、κ=0.9202；接受中不安全2/110=1.82%'),
('E4','完整实现状态','十项验收条件10/10假定通过；没有真实训练验收报告'),
('E5','目标硬件成本','AAEC/CDCP均值31.90/45.26秒；P95 38.88/78.09秒，低于自定门限'),
('E6','种子与统计','固定17/29/43；2000次文档配对；核心总增量区间下界>0'),
('E7','评分与保留风险','构造评分AUROC≥0.884、ECE≤0.020；原TP保留>99.8%'),
('E8','研究包完整性','2项研究、2主语料、4格、成功失败案例俱全；不代替学校判断')]
new+=tbl('表H-1 全部要求满足的模拟验收清单',['编号','项目','情景证据','状态'],[[a,b,c,'PASS_SIMULATED'] for a,b,c in requirements])
new+='''### H.3 审核、学习曲线和评分数据

审核的两路判断与参照标签均独立标为构造输入；旧Luna句子只是来源文本，不充当真人判断。模拟学习曲线及十项实现状态用来补齐预期报告，不能证明梯度路径、冻结模块或缓存策略已在目标训练入口正确实现。

评分情景以原生完整对象构造1600条分数，每语料每对象族400条，按正确性人为平衡。表H-2的校准误差只描述这一构造分布；自然候选先验、真正OOF模型和独立校准尚未运行。该补充评分池不驱动主模拟图，不能将其AUROC当作主表性能的中介证据。

'''+tbl('表H-2 构造完整对象评分的指标（模拟）',['语料','对象','条数','AUROC','Brier','ECE10'],[[z['corpus'],z['axis'],z['n'],f(z['AUROC'],4),f(z['Brier'],4),f(z['ECE10'],4)] for z in A['score_simulation']])
new+='''### H.4 成本与统计身份

推理时延包含5个配置×899篇×3种子的生成记录，按文档长度及预设比例构造分项。它与4.6.8节本地实际求解的微秒／毫秒级小问题计时分别报告，不进行硬件折算。模拟P95可以检查表述与分位数计算，不能给出部署承诺。

图模拟先按文档生成整数对象计数，再对同一文档索引配对抽样2000次，每次跨三个种子计算micro-F1及差值；不把种子当新增独立文档。构造分布带有预设方法关联和金标信息，区间不能用于确认未知模型收益。预览门限通过与统计推断有效性是两种判断。

### H.5 案例与解释边界

10个案例含AAEC 4个、CDCP 4个和CasiMedicos 2个，按不同机制选取。既有输出案例保存全图与分数；构造评分案例明确输入来源，四格案例在同批图中按固定键选取。成功例同时报告FP，失败例保留候选遗漏、评分失真和正确对象丢失。它们解释可观察计算过程，不将模型生成理由或选取的少量句例当成总体因果证明。

### H.6 复算入口与版本保留

research_1011_v13/prepare_corpus.py读取原生训练档案；generate_graph_scenario.py构造主图；supplement_acceptance.py生成补充验收情景；run_mechanism_fixtures.py执行构造输入求解；build_cases.py关联原始输出。_revision_1011_v13/derive_analysis.py重算端点链，compose_content.py生成本稿，content_audit.py执行独立一致性核查。运行依赖及数据哈希见交付清单；复跑应在副本中进行，避免覆盖版本证据。

旧v12及更早稿件、原始实验输出均保持原文件。当前交付为内容稿、案例册、修改说明、模拟与实测身份清单及复算脚本；未生成Word/PDF，也未完成分页与字体渲染验收。
'''
text=text[:text.index('## 附录H')]+new

# Final semantic consistency: use an auditable factor universe from first definition.
repl('因素标签 $y_\omega$ 为协议规定的关系状态，无标注关系时记作 NONE。','因素标签 $y_\omega$ 为协议规定的关系状态。在可审核因素宇宙内，无标注关系记作NONE；已标注联合源真子集的语义未知例外按3.3.4节定义，先从语义监督和审核域中排除。')
repl(r'\mathcal D_A=\{\omega\in\Omega(C):V(\omega)\cap A\ne\varnothing\}.',r'\mathcal D_A=\{\omega\in\Omega_{sem}(C):V(\omega)\cap A\ne\varnothing\}.')
repl(r'二元情形即 $\{(u,v):u\in A\lor v\in A,(u,v)\in\Omega(C)\}$。',r'其中 $\Omega_{sem}(C)=\Omega(C)\setminus\mathcal U_{sem}$，未知集合见3.3.4节；AAEC没有这一联合源子集例外。二元情形即 $\{(u,v):u\in A\lor v\in A,(u,v)\in\Omega_{sem}(C)\}$。')
repl('条件可采用“全部合法端点目录、显式正关系表、其余因素为 NONE”的无损编码','条件可采用“全部合法端点目录、显式正关系表、语义未知例外清单、其余可审核因素为NONE”的无损编码')
repl('05    建立因素宇宙 Ω(C_d)，构造改写集合 A','05    建立 Ω(C_d) 并排除语义未知集合得到 Ω_sem，构造改写集合 A')
repl('当前方法中的v12可靠因素学习、原生监督头及规模路由仍是目标配置；本轮真正执行的是固定Casi候选上的显式Luna评分和声明的轻量初始化／修正。','当前可靠因素学习、原生监督头及规模路由仍是目标配置；v12已执行固定Casi候选上的显式Luna评分及轻量初始化／修正，v13新增的是原生图模拟、案例整理及构造输入上的16条求解结果。')

# Keep archival ICIC tables unchanged byte-for-byte.
assert old[old.index('## 附录E'):old.index('## 附录F')]==text[text.index('## 附录E'):text.index('## 附录F')]
DEST.write_text(text)
(W/'revision.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile=BASE.name,tofile=DEST.name)))
dump(W/'apply_report.json',{'source_sha256':sha(BASE),'output_sha256':sha(DEST),'operations':ops,'operation_count':len(ops),'preserved_ICIC_appendix':True,'new_word_pdf_files':0})
config=read(R/'_revision_1011_v12/preview_config.json');config['version']='1011-v13-content';config['config_id']='AM-V13-CONTENT-PREVIEW-20261011';config['training']['factor_review']['semantic_unknown']='exclude gold joint-source unannotated proper subsets in BOTH original and augmented semantic-head supervision; retain full original graph generation';config['training']['factor_review']['full_filter_audit']='J_A equals complete D_A in declared auditable universe; reject view when resources cannot cover it';config['v13_identity']={'main_graphs':'GOLD_INFORMED_NATIVE_GRAPH_AUTHORING_SCENARIO','native_character_keys':True,'new_target_training_runs':0,'semantic_unknown':'mask both original/augmented semantic heads; retain strict object mismatch scoring','full_filter_audit':'J_A=D_A on declared semantically auditable universe','acceptance':'PASS_SIMULATED'};dump(W/'preview_config.json',config)
print(json.dumps({'chars':len(text),'operations':len(ops),'sha256':sha(DEST)},ensure_ascii=False))
