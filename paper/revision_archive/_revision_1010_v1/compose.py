"""Complete synthesis, appendices and global consistency of the revision."""
from pathlib import Path
import re,json,hashlib,difflib
W=Path(__file__).resolve().parent;R=W.parent
old=(R/'report_1009_v4_full.md').read_text()
s=(W/'revision_stage1.md').read_text()
state=json.loads((W/'edit_stage1.json').read_text());edits=state['edits']
r=json.loads((W/'scenario_results.json').read_text())
def change(a,b,key):
    global s
    assert s.count(a)==1,(key,s.count(a),a[:90])
    s=s.replace(a,b,1);edits.append({'id':key,'before':a,'after':b})
def section(a,b,t,key):change(s[s.index(a):s.index(b)],t.rstrip()+'\n\n',key)
def insert_before(a,b,key):change(a,b.rstrip()+'\n\n'+a,key)
def block_table(n,source=None):
    return re.search(r'^表'+re.escape(n)+r' [^\n]+\n\n(?:\|[^\n]*\n)+',source or s,re.M).group(0)

# Move the risk figure to the chapter where the recovery counts are introduced.
risk=re.search(r'!\[[^\n]+recovery_risk\.png\)\n\n图5-2 [^\n]+\n',s).group(0)
change(risk,'','P07-move-risk-figure')
s=s.replace('图4-3','图4-BUDGET')
insert_before('表4-8 推理成本与预算取舍',risk.replace('图5-2','图4-3'),'P07-risk-in-ch4')
s=s.replace('图4-BUDGET','图4-4')

t51=block_table('5-1');t52=block_table('5-2');t53=block_table('5-3');t55=block_table('5-5')
figure51=re.search(r'!\[[^\n]+four_cell_results\.png\)\n\n图5-1 [^\n]+\n',s).group(0)
# Source member counts are per artificial gold set, not multiplied by seeds.
group_n={k:v[0][0]+v[0][2] for k,v in r['cdcp_source_strata']['t0_i0'].items()}
t55=t55.replace('|源成员数|','|源成员数／金标数|').replace('|1个源成员|',f"|1个／{group_n['1']}|").replace('|2个源成员|',f"|2个／{group_n['2']}|").replace('|3个及以上|',f"|3个／{group_n['3']}|")
t55+='|超过3个／0|—|—|—|—|\n'
selection=[]
for code,label,t in [('t0_i0','T0＋I0',(0,0)),('t1_i0','T1＋I0',(1,1)),('t0_i1','T0＋I1',(14,22.16)),('t1_i1','T1＋I1',(15,23.16))]:
    vals=[r['metrics'][ds][code]['relation']['mean']-r['metrics'][ds]['t0_i0']['relation']['mean'] for ds in ['AAEC','CDCP']]
    selection.append(f"|{label}|{vals[0]:+.2f}|{t[0]:.2f}|{vals[1]:+.2f}|{t[1]:.2f}|")
t54='表5-4 相对共同起点的关系增量与在线额外时间\n\n|配置|AAEC增量|AAEC增秒|CDCP增量|CDCP增秒|\n|:---|:---:|:---:|:---:|:---:|\n'+'\n'.join(selection)+'\n'
ch5=r"""## 第五章 两阶段框架的综合分析

本章使用同一批人工情景记录，围绕五个综合问题组织分析：两阶段分别增加多少、修复对象是否重叠、训练如何改变修正条件、何时值得启用修正，以及最终失败发生在哪里。四格计数和成本可以复用；对象级结论需要完整预测与候选轨迹，不能由聚合分数反推。

### 5.1 两阶段各自带来多少增量

四格为T0＋I0、T1＋I0、T0＋I1和T1＋I1，I1采用BR-J。同一训练条件下，I0与I1共用检查点、初始图和候选；不同训练条件可以改变候选及评分适配，因而四格估计的是条件系统增量。第三章T1和第四章BR-J分别复用T1＋I0、T1＋I1的主行，全部三个种子均进入汇总。

@@T51@@

完整组合相对T0＋I0的关系增量为13.31和13.92个百分点。令$F_{ti}$表示同一指标的四格结果，交互差为$I=F_{11}-F_{10}-F_{01}+F_{00}$；下表按未舍入的种子均值计算，单位为百分点。

@@T52@@

AAEC关系交互差为−0.64，配对95%区间为[−1.71, +0.41]；CDCP为+0.40，区间为[−1.01, +1.80]。两者均包含0，因此组合增量与稳定超加性应分别判断。AAEC组件交互为负，与收益重叠相容，但不能据此确定两阶段改变的是哪些对象。

@@FIG51@@

### 5.2 两阶段修复了哪些相同或不同对象

净计数为对象分析提供总量约束。表5-3分别计算T1＋I0减T0＋I0、T0＋I1减T0＋I0，以及T1＋I1减T1＋I0，按同文档和种子累加；金标固定，所以每项ΔFN等于−ΔTP。

@@T53@@

AAEC在T1下修正的关系净TP增加224，小于T0下的248；CDCP则为187与176。训练后剩余修正空间并非在两个语料上同幅度收缩。表4-7中BR-J的恢复与损失分别为289−65、233−46，恰好对应上述净增量；图4-3保留两类数量，第五章不重复绘制同一风险。

对象重叠以相同原文上的完整语义键对齐。记$P_{ti}$为四格中的预测对象集合，$\Omega$为金标，训练新命中集合为$R_T=(P_{10}\cap\Omega)\setminus P_{00}$，仅修正新命中为$R_I=(P_{01}\cap\Omega)\setminus P_{00}$。二者交集表示共同修复，差集分别表示独有修复；再检查完整组合新增命中中未被两种单阶段覆盖的对象，以及$\Omega\setminus P_{11}$中的剩余遗漏。原有正确对象被组合破坏、T1正确对象被I1破坏也分别登记，新增错误关系与移除错误关系单列。

当前逐文档TP、FP、FN只能支持净变化，无法重建这些集合。同一净增量可以由不同的恢复和损失组成，故本版不填共同／独有修复比例，也不将负交互解释为已证实的对象重叠。附录H.4给出可复用正式四格预测的记录格式；真实分析按文档配对，重复种子不扩大独立文档数。

### 5.3 训练如何改变修正条件

四格中的训练变化至少经由三个环节影响修正。第一，初始图的错误构成发生变化：边界、类型、完整端点与关系判断需要分别统计。第二，多候选生成可能改变完整对象覆盖，特别是正确组件能否同时共存、完整超边是否进入冻结候选。第三，T0与T1的错误分布不同，评分适配及高分错误对象也可能随之变化。任何一个环节都不能由最终F1单独识别。

正式分析在同一评价文档上关联初始错误、裁剪前后覆盖和最终对象变化。评分变化先在共同提案集合上比较，再查看各自搜索访问的提案，避免把访问分布变化误称为校准改善。若需进一步归因，可在训练侧选择固定评分器与适配评分器的交叉比较；缺少这一控制时，四格只解释整个训练条件的影响。

现有情景显示AAEC的修正条件增量由6.62降至5.99，而CDCP由6.31增至6.71，但相关交互区间包含0。它提示分析方向，却没有确定变化来自初始错误减少、候选改善或评分适配。表4-4的T1覆盖结果也不能被当作T0到T1的覆盖变化。

### 5.4 何时值得启用修正

配置选择应同时考虑在线质量、额外时延和错误变更。表5-4压缩重复F1，直接列出相对T0＋I0的关系增量与逐文档额外时间；AAEC和CDCP共同起点分别为17.00秒和22.00秒。

@@T54@@

若训练的一次性投入已经完成，仅比较本情景的关系F1与在线平均时间，T1＋I0同时优于T0＋I1：AAEC高0.70个百分点、少13.00秒，CDCP高0.90个百分点、少21.16秒。这说明不能仅因允许预测后修正就默认采用“只修正”配置。若无法重训、服务量很小或已有模型必须冻结，一次性训练投入会改变判断，上述在线比较不适用。

在T1上启用BR-J需再增加14.00秒和22.16秒，关系F1增加5.99和6.71个百分点，同时仍发生误改。等求解预算全局ILP则在本情景中具有略高的关系F1与初始TP保留率，其端到端时间只多1.40秒和2.24秒。需要最高抽取质量且能容忍这部分时间时，全局方案应进入优先比较；需要限制每次变更或复核局部修改时，可进一步测量事务策略的实际价值，不能仅凭局部日志预判优劣。

上述排序限于设定的平均时间。P95、超时、无可行解、缓存及批量吞吐可能改变实际选择；等端到端时限与真实图规模分组尚需附录H.3的运行记录。若相同资源下局部方法没有稳定质量或变更控制收益，简化它比继续增加规则更有意义。

### 5.5 最终失败发生在哪里

对于未恢复金标对象，先检查组件候选缺失，再检查完整关系槽位、动作表达、队列纳入、预算执行和接受门。按照最早阻断环节给出一个主标签，其余原因作为附加标签。该顺序把“增加时间能解决什么”与“需要改变候选或动作才能解决什么”分开；它描述恢复路径上的阻断，不自动给出自然语言错误的独立因果比例。成功或错误接受还需完整前后状态，案例格式见附录B.5。

长源集合尤其需要区分保护与新建。表5-5保留CDCP原生超边计数，金标数按一个固定人工集合报告，三个种子共享该集合；各组F1分别计算，整体仍从所有对象计数重算。

@@T55@@

原“3个及以上”实际只含3成员，超过3成员组在当前人工集合中为0，故不报告F1。已有长超边是否保住，应以初始图中已正确预测的长超边为分母；遗漏长超边能否新建，应以初始遗漏的长超边为分母，进一步区分其他完整候选图已经提供的保护槽位与新增枚举槽位。新增枚举上限为3，不排除从其他成功候选图选回更长的受保护对象，但不能创造未在保护池中的任意长源组合。

这两个问题需要不同账本，当前0样本组不能用于证明保护成功或恢复无效。本章只比较AAEC与CDCP的原生域内任务，附录E的粗粒度跨域记录保持历史身份。

### 5.6 本章小结

综合分析得到三点情景内认识：训练与推理均有条件增量，但关系交互尚未显示稳定超加；在线配置的选择受到训练能否摊销以及修正额外时延影响；BR-J面对等求解预算全局对照时，现有质量、时间与保留率不足以建立突出优势。对象重叠、训练对候选和评分的传递，以及真实失败构成仍需完整运行材料。由此，两阶段组合应作为可检验的配置选择，而非预设处处优于单阶段的方法结论。
"""
for token,val in [('T51',t51),('T52',t52),('T53',t53),('T54',t54),('T55',t55),('FIG51',figure51)]:ch5=ch5.replace('@@'+token+'@@',val.strip())
section('## 第五章 两阶段框架的综合分析','## 第六章 总结与展望',ch5,'P07-rewrite-ch5')

section('### 6.1 研究总结','## 参考文献',"""### 6.1 研究总结

本文以组件与关系之间的依赖为主线，分别研究训练时监督保持和推理时结构恢复。第一项工作按关系影响域检查局部改写，以标注对应连接原文、增强文及成对因素学习；第二项工作以组件集合替换及全部受影响关系重建作为共同决策单位，在固定候选与评分下比较局部事务和全局结构选择。两项工作共享原生任务和严格评价，承担不同阶段的问题。

第一项工作需要同时回答增强是否可靠、是否仍有充分变化，以及对应因素学习是否具有独立作用。本文把数据构造、头监督、成对项和中心策略分开比较。现有人工情景中，数据构造与成对项分别表现出条件增量，而中心差值区间包含0；因此贡献落在关系影响域及可靠对应的组织方式，结论优先保留为默认策略。

第二项工作明确了集合动作如何联合处理相互依赖的修改，但动作表达能力不等于使用价值。在当前情景中，BR-J相对分步策略改善关系结果；同评分、等求解预算全局ILP又取得略高关系F1和保留率，BR-J只节省少量端到端时间。这使研究结论转向具体资源和变更要求下的取舍，局部方法是否值得保留需由实际比较决定。

两阶段四格避免把组合总增量误写为相互独立或稳定超加。第五章进一步区分净计数与对象重叠，讨论离线训练投入、在线时延及完整超边范围。方法价值最终由现实问题规模、可复核输出和相应代价支撑；数学构造与文档复算负责检验定义和论述的内部一致性。

### 6.2 研究局限

本版采用人工计数情景，尚未完成真实语料上的训练、增强审阅与求解比较，情景数值不用于证明方法有效。原始改写文本、四格完整预测和求解状态等材料缺失，使表达变化、对象级互补和真实尾延迟尚不能定量判断；外部方法已完成定位与接入条件核查，尚无本版同协议复跑成绩。

方法本身也有边界。影响域检查受语义判断与标注完备性影响，严格筛选可能改变源分布；成对项约束辅助因素，不能保证生成整图严格等变。推理只能访问冻结候选及声明动作，长超边新增能力受限；对象评分偏差会造成误改，分项门也可能拒绝真实有益方案。固定效用的性质限定决策过程，不提供真实F1或全局最优保证。

统计结论限定于原生AAEC与CDCP及三个重复种子的协议。原生关系、二元投影与历史跨域Link-F1分别解释；平均时间也不能替代部署中的尾延迟、批量吞吐和一次性投入。结论中的取舍须随真实结果一起更新。

### 6.3 后续研究方向

首先完成训练侧的小规模问题诊断和全流程资源测量，以真实漂移、表达变化、初始错误及裁剪前规模决定设计是否值得继续。其次在共同候选与评分下比较BR-J和等求解／等端到端预算全局方法，保留不利和不显著结果。关键假设不成立时，先调整定位或简化机制。

之后复用同一批正式运行完成外部系统定位、同数据学习比较、推理策略及四格对象分析。新增候选组织或长超边扩展仅在覆盖与资源证据需要时开展，并重新核对全部对照的共同条件。主要主张已有直接证据后，工作重点转为压缩论证和整理交付，不继续以模块或检查数量扩张研究范围。
""",'P08-rewrite-conclusion')

# Preserve transferred implementation detail and theorem proofs in focused appendices.
serial=[(a,b) for a,b in state['moved'] if a in ['序列化与字段顺序','跨度头坐标与解码','有限扩展与去重','对象键与兼容判定']]
insert_before('## 附录B 评分与事务执行记录','### A.6 序列化、坐标与候选构造细则\n\n'+'\n\n'.join(b.strip() for a,b in serial),'P08-technical-appendix')
proof=[b for a,b in state['moved'] if a=='固定评分下的性质说明']
insert_before('## 附录C 成果归属与研究声明','### B.6 固定评分性质的证明与构造\n\n本节对应4.5.3至4.5.5节，分别说明精确差值、集合动作的表达边界与有限终止。\n\n'+'\n\n'.join(proof),'P08-proof-appendix')
insert_before('## 附录A 数据处理与复现协议',"""[47] BAO J, HE Y, SUN Y, et al. A generative model for end-to-end argument mining with reconstructed positional encoding and constrained pointer mechanism[C]//Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing. Abu Dhabi: Association for Computational Linguistics, 2022: 10437–10449. DOI: 10.18653/v1/2022.emnlp-main.713. [来源](https://aclanthology.org/2022.emnlp-main.713/)

[48] BAO J, JING M, DONG K, et al. UniASA: A unified generative framework for argument structure analysis[J]. Computational Linguistics, 2025, 51(3): 739–784. DOI: 10.1162/coli_a_00553. [来源](https://aclanthology.org/2025.cl-3.2/)

[49] ZHANG Z, WANG Q, DING K, et al. Improving synthetic data generation for argument mining via adversarial reinforcement learning[EB/OL]. arXiv:2610.07699v1, 2026[2026-10-10]. DOI: 10.48550/arXiv.2610.07699. [来源](https://arxiv.org/abs/2610.07699v1)""",'P06-new-references')

appendix_g=r"""
## 附录G 外部方法定位与比较协议

### G.1 检索范围与方法选择

本轮检索截至2026年10月10日，优先使用ACL Anthology、论文原文、arXiv作者版本与论文所指向的公开仓库。表G-1记录纳入考虑的方法类别，检索目的为建立可执行的比较范围，未据此作穷尽性新颖性或“首次”判断。原论文成绩不并入本版人工情景主表。

表G-1 外部研究候选与本稿比较用途

|研究|输入与机制|比较用途|接入时重点核对|
|:---|:---|:---|:---|
|结构SVM／RNN[46]|联合组件与关系的结构化预测|历史结构对照|CDCP预处理与完整源集合|
|MT-AM[25]|辅助语料与多任务训练|训练来源参照|额外监督不得混入单语料主轨|
|GMAM[47]|序列生成、约束指针与位置编码|结构生成补充|输出跨度、标签及候选表达|
|Kawarada等[7]|标注文本的端到端生成|优先系统对照|AAEC stance、CDCP转换|
|DENIM[12]|篇章结构感知前缀|生成条件补充|篇章分析成本、AAEC口径|
|UniASA[48]|统一生成与多视图学习|优先系统对照|标签映射、原生超边、辅助目标|
|AASP[9]|自回归结构动作|机制参照|动作表示与完整对象导出|
|ARGUS[10]|分割、分类与关系系统|系统接口参照|分割输入、求解目标与评价|
|AMELIA[26]|跨数据集分类及多任务接口|任务边界参照|不能替代原文跨度抽取成绩|
|QOS／DOS[35]|质量／多样性导向合成|数据构造近邻|生成目标、样本量与训练日程|
|对抗强化学习合成[49]|文本与结构标注对联合生成|近期合成参照|生成器训练成本、数据目标|

FOL-AM[14]与Cabessa等[8]还提供关系推理和生成分类的思路，但给定组件的输入条件与本稿端到端定位不同，放在相关机制比较中。纳入更多方法有助于定位，但不意味着所有方法都必须同等规模复跑。

### G.2 代码入口与可复现性核查

Kawarada方法的公开入口为[am-as-text2text](https://github.com/masayouk/am-as-text2text)。当前说明使用T5／FLAN-T5及TANL接口，支持LoRA等配置，并明确CDCP转换模块不在仓库中。它提供实现入口，但当前代码配置不能自动等同于2024论文原始设置；正式运行需固定提交、补全数据转换并核对差异。

UniASA的[公开仓库](https://github.com/HITSZ-HLT/UniASA)提供AAEC、CDCP等数据处理及训练脚本；AAEC说明含标注修正，CDCP依赖graph_parser预处理。这使其具备较明确的起点，也要求保留本稿原生金标并记录转换损失，不能直接采用处理后分数代替完整超边评价。[GMAM仓库](https://github.com/HITSZ-HLT/GMAM)提供另一结构生成入口。

DENIM原文给出的代码地址为[syiswell/DENIM](https://github.com/syiswell/DENIM)，近期合成论文给出[Synthetic-Data-for-Argument-Mining](https://github.com/ZhangZJ-GH/Synthetic-Data-for-Argument-Mining)；本轮访问未取得可检查的仓库内容，因此仅确认论文所载地址，不标记环境可运行。QOS／DOS的[作者仓库](https://github.com/YuqiHuang2003/QOS_DOS)用于核对两类合成入口；[AMELIA仓库](https://github.com/brunoyun/amelia)所列分类任务用于说明输入边界。AASP、ARGUS的本轮记录以原文方法为限，不将未检查的代码写成已复现。

本轮没有安装或执行上述模型。系统主对照优先完成Kawarada与UniASA的表示审计，再依据真实接入结果保留至少一种原生任务可比方法；GMAM、DENIM和动作模型用于必要的补充，避免用大量异口径原报告分数替代一个可靠对照。

### G.3 QOS式适配与本方法的差异

表G-2 当前数据构造对照的适配范围

|维度|QOS式适配|完整增强＋基础损失|
|:---|:---|:---|
|输入|共同标注文档与槽位接口|相同文档及关系影响域条件|
|改写范围|本稿固定槽位范围|相同范围，检查内部与跨界因素|
|标签检查|槽位恢复及共同基础检查|增加正关系／NONE影响域审核|
|训练规模|AAEC 500、CDCP 900变体|相同规模及增强token预算|
|学习目标|继承基础损失|相同基础损失；不含新增头／成对项|
|评价|原文严格组件与完整关系|相同原生评价器与独立文档|

这一定义控制T-B的数据构造比较，不声称复现原论文全部QOS、DOS及联合日程。完整T1另包含头监督与成对项；表3-6的同数据比较承担其学习增量。若追加原始QOS／DOS复现，原方法和本稿适配版本分别命名，生成器调用、合成样本与下游训练全部计费。

### G.4 外部系统接入与结果登记

先冻结原始文档ID、划分、评价分词器、类型和完整超边，再审计外部转换的每一步。AAEC原方法若将Claim stance并入组件标签，需同时保留其原任务结果与本稿映射结果；CDCP若拆分或收缩源集合，必须保留可逆来源，否则只进入兼容任务补充。不能借助测试金标为外部预测补回遗漏端点或合并出正确超边。

每个系统分别运行原配置核对轨与共同任务比较轨，记录代码提交、模型身份、额外数据、选择规则及全部失败文档。共同评价只比较可直接导出的原生完整对象；统一骨干可控时另做方法适配，不可控时解释为系统比较。若无法无损表达本稿任务，不把该方法放入严格主榜，也不以转换失败暗示其原任务能力较差。
"""
appendix_h=r"""
## 附录H 关键诊断与综合证据记录

### H.1 训练侧问题规模与初始错误

增强诊断按语料在训练侧持出组固定抽取40篇源文档，按文档长度与金标关系数的中位数交叉分层，层内随机抽取；不足的层取全量并记录实际文档数。先固定普通改写生成池，每篇最多4次尝试。内部正、跨界正、内部NONE、跨界NONE分别抽至200个可审因素，若不足则全取，报告实际分母；同一变体允许多个因素，但保留源文档与变体ID，按文档而非因素独立重采样。

原文与改写文并排审阅，审阅者不看方法名及接受标志；两人独立判断并保留分歧，经裁决形成因素标签。接受／拒绝分层用于筛选诊断，不能替代未筛生成池的问题发生率。方法选择使用训练侧材料，独立评价仅验证冻结结论。开发诊断完成后按2.6节重新生成正式OOF记录，保持拟合、校准及策略角色隔离。审计至少记录四层的文档数、变体数、因素数和漂移数，等层均值与按原池构成加权值分别报告。

初始预测诊断复用训练侧OOF记录。组件先按严格键命中，再配对同跨度异类型对象；剩余对象按token交并比降序、坐标顺序破同分进行一对一配对，交并比阈值在训练侧预定为0.5，仅用于描述边界误差，完全不改主评价。未配对金标记遗漏，未配对预测记多检。关系同时记录“全部端点正确”“至少一个端点错误”及关系标签／方向状态；候选覆盖另作交叉维度，不能把各维度相加为因果比例。

### H.2 表达变化、源覆盖与资源轨道

非复制在仅作Unicode NFC及换行规范化后比较允许改写的组件文本，保留大小写、否定和标点。所有可解析变体为分母，只要一个允许槽位与原文不同即为非复制；生成池与接受池分别报告，解析失败数以全部尝试为分母另列。跨变体重复和完全复制另存标志，避免把反复生成同一个新句子视为高多样性。

规范化编辑距离采用固定评价分词器。对同一变体的各改写槽位，分别计算Levenshtein距离，再将距离之和除以各槽位原、新token长度较大值之和；不拼接跨槽边界，不纳入未允许改写的全文区域。分母为0时记0并单列空槽异常。报告中位数、四分位区间和零值比例，源文档为重采样单位。两项指标度量字面变化，不等于语义多样性或标签正确性。

接受覆盖按源文档统计，并在训练侧冻结的长度、关系数及显式／隐式关系组中并列展示非复制、编辑距离、接受比例与因素漂移。任务结果另来自匹配规模轨道；分组差异用于检查选择偏向，不据聚合相关性声称某种改写幅度必然提高F1。

表H-1保留旧情景的固定尝试轨训练成本。它不进入匹配训练规模主结果的成本比较；正式训练需为两轨各自登记变体清单、增强token、实际更新数、设备小时和峰值显存。

表H-1 固定尝试轨训练成本存档（人工情景）

|语料与方法|训练GPU小时|
|:---|:---:|
|AAEC 普通增强|1.46|
|AAEC QOS式|1.48|
|AAEC 完整方案|1.79|
|CDCP 普通增强|2.32|
|CDCP QOS式|2.38|
|CDCP 完整方案|2.91|

### H.3 候选规模、共同预算与求解状态

资源探测逐文档保存保护跨度数、补充跨度数、去重后跨度数、带类型组件数、裁剪前槽位数、正标签评分对象数、批次数、裁剪后槽位数，以及各阶段时间和峰值内存。槽位与标签对象分别计数，受保护与补充部分记录交集，不能重复相加。资源阈值依据训练侧探测及设备容量设定，连同探测文档ID冻结；预检失败、评分失败、无可行解和超时分别编码，所有独立评价文档保留在分母内。

等求解预算轨以表2-2的3秒／5秒为基准，预定0.5、1、2倍三个逐文档总额度，大预算全局行另作补充。图规模按训练侧带类型组件数和裁剪前槽位数分别确定三分位切点，测试只应用固定切点。等端到端轨另按共同准备时间的训练侧P95加基准求解额度确定基准时限，并比较相同倍数；计时自读取文档后开始，包含生成、枚举、评分、提议构造、全部拒绝、求解和提交。输入无法在时限内完成准备也计失败，不把它从速度表排除。

共同候选与评分缓存可以复用，但单文档比较须向双方计入相同冷缓存准备成本；热缓存吞吐另报，不能只向一方计费。分别报告平均、P95、超时率、返回完整可行图的比例、无incumbent率、F1、初始TP损失与新FP。局部和全局都提供从初始图出发的可行回退，求解器无incumbent与系统能返回回退图是不同事件。

每次最大化求解保存status、incumbent效用、有效上界、绝对gap和求解器定义的相对gap，缺失值保持缺失并注明原因；最优性只采用求解器证书或已证明状态，不由时限长短推断。局部子问题的界不拼成整图全局界。只有已验证包含关系的同目标全局上界，才能用于限制局部终态效用，仍不构成真实F1上界。

现有人工情景的平均与P95耗时是设定输入，不是从真实逐文档延迟计算的尾分位，也没有真实求解证书。新预算轨和规模分组在取得日志前只作为协议，不补填超时率、gap或可行解覆盖。

### H.4 四格对象、恢复阻断与案例

四格每个预测对象保存语料、文档ID、种子、配置、原文规范坐标、组件类型及关系完整端点与标签。金标与预测都按共同语义键形成集合，先验证四格文档集合及评价身份完全一致，再生成共同修复、各自独有修复、组合新增、仍遗漏与新破坏的清单。关系新FP、已移除FP独立记录，不把TP增加解释为所有错误减少。每个清单保留对象键及源运行身份，以供原文核查。

恢复失败按组件候选、完整槽位、动作、队列、执行资源、接受门的顺序取首个阻断；动作不可表达需要穷尽声明邻域或给出规则证据，未搜索到不能直接判定不可达。附加标志保留评分异常、超时等并发原因。保护长超边与新建长超边分别以初始命中／遗漏金标为分母，并报告其他候选图提供的长槽位来源；0样本组不计算F1或成功率。

完整案例采用附录B.5的原文、金标、初始与最终对象和事务轨迹。选择规则在看结论前固定：覆盖成功恢复、错误接受、错误拒绝及最常见阻断类型，每类按预定文档排序取例，并与总体频数并列。教学例只解释机制，人工片段不能更名为实际运行案例。

### H.5 从模拟情景替换为真实证据的顺序

先取得增强文本与基线OOF预测，检查问题频率和表达变化；再跑通候选—评分—修正全链路及强全局对照，测量实际规模与资源。若关键收益不足，先简化方法和调整定位，再决定正式比较规模。之后复用冻结的训练、推理与外部基线运行形成主表、误改、四格对象和案例，不为每个分析另选有利运行。

正式替换同时更新表、图、区间、摘要、结论及模拟标识。文档排版、公式一致和人工计数复算仍作为质量检查保存；它们不计入真实训练或求解次数。历史附录E及本模拟版本继续存档。
"""
s=s.rstrip()+'\n\n'+appendix_g.strip()+'\n\n'+appendix_h.strip()+'\n'
edits.append({'id':'P06-external-appendix','after':appendix_g})
edits.append({'id':'P01-P03-P04-P05-P07-evidence-protocols','after':appendix_h})

# Remove redundant case prose so the chapter summary stays with the cases.
for prefix,newtext,ident in [
    ('表4-9以人工片段','表4-9使用人工机制片段。正式案例按附录B.5和H.4保留完整原文、金标、前后对象、分数、门限和求解状态；可复核轨迹需能重算该次接受或拒绝。','P08-case-concision'),
    ('这些轨迹分别对应表达能力','四类片段分别说明动作表达、评分偏差、接受门和候选限制；真实频率与误改风险由总体运行记录评价。','P08-case-ending'),
    ('本章以组件集合替换和完整关系重建形成结构事务','本章明确了集合事务的表达与决策条件。人工情景中，BR-J优于所定义分步策略，但与等求解预算全局方法相比尚无突出质量、时间或保留率优势。局部方法的使用条件需由真实资源和变更轨迹检验；第五章继续分析其与训练条件的关系。','P08-ch4-concision')]:
    paragraph=next(p for p in s.split('\n\n') if p.startswith(prefix))
    change(paragraph,newtext,ident)

# Keep table numbering contiguous and update all references once.
for ch in ['3','4']:
    s=re.sub(r'表'+ch+r'-(\d+)(?!\d)',lambda m:'表'+ch+'-'+str(int(m.group(1))+1),s)
s=s.replace('表3-NEW','表3-1').replace('表4-NEW','表4-1')
# Diversity table is placed after original table 3-4; renumber following tables again.
for num in range(10,5,-1):s=re.sub(r'表3-'+str(num)+r'(?!\d)','表3-TEMP'+str(num+1),s)
s=s.replace('表3-TEMP','表3-').replace('表3-DIV','表3-6')
# Add light identities to independently circulating experimental tables and figures.
lines=s.splitlines()
empirical_tables={'表2-2'}|{f'表3-{i}' for i in [4,5,7,8,9,10,11]}|{f'表4-{i}' for i in range(4,11)}|{f'表5-{i}' for i in range(1,6)}
for i,line in enumerate(lines):
    label=line.split(' ',1)[0]
    if re.match(r'^表\S+ ',line) and label in empirical_tables and '人工情景' not in line:
        lines[i]=line+'（人工情景）'
    if re.match(r'^图(?:3-3|4-3|4-4|5-1) ',line) and '人工情景' not in line:
        lines[i]=line+'（人工情景）'
s='\n'.join(lines)+'\n'
s=s.replace('### 3.6 实验结果与分析\n\n','### 3.6 实验结果与分析\n\n本节数值、审计判断和成本为人工情景，用于展示比较与分析；正式结果须由对应原始文本和运行记录整体替换。\n\n')
s=s.replace('### 4.6 实验与分析\n\n','### 4.6 实验与分析\n\n本节表图和案例使用人工情景；求解状态、错误分布与真实延迟的新增诊断按附录H执行后另行报告。\n\n')
# Keep inherited checks and cue rules in their actual evidential scope.
s=s.replace('原文与增强文分别按各自文本触发提示，线索依赖由3.6.4节检验。','原文与增强文分别按各自文本触发提示；该规则沿用前期配置，本章不将其单独计为新增机制。')
s=s.replace('本版保留并原样复算v1机制程序，另运行中心匹配、条件反向、分阶段账本、带坐标拆合与状态队列的接口参考程序。','本版保留前版v1机制程序，以及中心匹配、条件反向、分阶段账本、带坐标拆合和状态队列接口程序的构造检查记录。')
s=s.replace('### D.6 本轮接口构造材料','### D.6 既有接口构造材料')

# Reader index follows the reorganized synthesis.
s=s.replace('5.1至5.3四格结果、交互差与成本','5.1至5.5阶段增量、对象变化与配置选择')
s=s.replace('**算法3-1 关系感知增强学习**','**算法3-1 关系影响域增强与成对学习**')
s=s.replace('输出：结论专项生成器 θ','输出：训练后的端到端生成器 θ')
s=s.replace('图3-2 关系感知增强学习的训练架构','图3-2 关系影响域增强与成对学习的训练架构')
s=s.replace('配置身份为1009-v4-simulation-review','配置身份为1010-v1-global-review')
s=s.replace('|5.4及附录E.8至E.9|','|5.5及附录E.8至E.9|')
s=s.replace('第五章组合、成本与跨语料分析','第五章阶段增量、配置选择与失败分析')
# Version strings in current reference configuration only, not historical appendix E.
e0=re.search(r'## 附录E .*?(?=## 附录F)',old,re.S).group(0)
e1=re.search(r'## 附录E .*?(?=## 附录F)',s,re.S).group(0)
assert e0==e1,'Historical appendix E changed'
f0=[x.strip() for x in re.findall(r'\$\$(.*?)\$\$',old,re.S)]
f1=[x.strip() for x in re.findall(r'\$\$(.*?)\$\$',s,re.S)]
assert f0==f1 and len(f1)==32
assert len(re.findall(r'^!\[',s,re.M))==11
assert '@@' not in s and 'TEMP' not in s and '-NEW' not in s
assert re.findall(r'^\[(\d+)\] ',s,re.M)==[str(x) for x in range(1,50)]
(R/'report_1010_v1_full.md').write_text(s)
(W/'edits.json').write_text(json.dumps(edits,ensure_ascii=False,indent=2)+'\n')
(W/'source.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='report_1009_v4_full.md',tofile='report_1010_v1_full.md')))
derived={'identity':'DERIVED_FROM_UNCHANGED_ARTIFICIAL_SCENARIO','source_sha256':hashlib.sha256(s.encode()).hexdigest(),'source_member_gold_counts':group_n,'comparison':{}}
for ds in ['AAEC','CDCP']:
    c=r['costs'][ds];m=r['metrics'][ds];risk=r['risk'][ds]
    derived['comparison'][ds]={'brj_time_saving_percent':100*(c['global_equal']['mean_s']-c['t1_i1']['mean_s'])/c['global_equal']['mean_s'],'brj_solver_share_percent':100*c['t1_i1']['solver_s']/c['t1_i1']['mean_s'],'global_relation_advantage':m['global_equal']['relation']['mean']-m['t1_i1']['relation']['mean'],'global_tp_retention':risk['global_equal']['relation']['tp_retention'],'brj_tp_retention':risk['t1_i1']['relation']['tp_retention'],'base_loss_augmentation_increment':m['full_data_i0']['relation']['mean']-m['qos_i0']['relation']['mean']}
(W/'derived_global_analysis.json').write_text(json.dumps(derived,ensure_ascii=False,indent=2)+'\n')
print('final source',len(s),'edits',len(edits),'formulas',len(f1),'refs',49,'sha',derived['source_sha256'])
