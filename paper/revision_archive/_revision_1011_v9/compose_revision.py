"""Integrate frozen real-text pilot records without changing the v8 baseline."""
from pathlib import Path
import json,re,hashlib
W=Path(__file__).resolve().parent;R=W.parent;L=R/'research_1010_v7_luna'
read=lambda p:json.loads(Path(p).read_text())
old=(R/'report_1010_v8_full.md').read_text(); text=old
metrics=read(L/'results/evaluation_001/metrics.json')
changes={'source_version':'1010-v8','output_version':'1011-v9','global':[['1010-v8','1011-v9']], 'text_replacements':[],'insertions':[],'section_replacements':[],'sections_before':[],'heading_renames':[]}
def replace(a,b):
 global text
 assert text.count(a)==1,(a[:70],text.count(a))
 text=text.replace(a,b);changes['text_replacements'].append({'old':a,'new':b})
def insert_after(a,b):
 global text
 assert text.count(a)==1,a[:70]
 text=text.replace(a,a+'\n\n'+b);changes['insertions'].append({'anchor':a,'paragraphs':[b]})
def paragraph(s):return {'type':'paragraph','text':s}
def table(cap,headers,rows,widths,split=None):return {'type':'table','caption':cap,'headers':headers,'rows':[[str(x) for x in row] for row in rows],'widths':widths,'split':split}
def heading(s):return {'type':'heading','level':2,'text':s}
def blocks_md(bs):
 parts=[]
 for b in bs:
  if b['type']=='paragraph':parts.append(b['text'])
  elif b['type']=='heading':parts.append('### '+b['text'])
  else:parts += [b['caption'],'\n'.join(['|'+'|'.join(b['headers'])+'|','|'+'|'.join([':---']*len(b['headers']))+'|']+['|'+'|'.join(row)+'|' for row in b['rows']])]
 return '\n\n'.join(parts)+'\n\n'

replace('附录D.2—D.3引用已保存的CPU轻量诊断，并补充逐文档复算统计；附录E保留前期存档，两者均不替代新增方法实验。','附录D.2—D.3保留既存CPU诊断，4.6.7及D.7—D.9另报告16篇训练侧文档上的Luna真实预测与轻量修正；该试验不替代训练方法及完整系统的受控实验。附录E保留前期存档。')
replace('本版采用AAEC与CDCP规模的假设计数形成估算演示，不代表真实模型实验。训练侧以数据构造整体及同数据学习增量为关键比较，分别固定基础损失或增强集合；推理侧以RelationOnly和单对象动作检验组件可变性与集合表达，以同目标全局求解判断资源取舍，分步策略补充检验共同决策。给定人工计数，成对项的关系F1增量为1.21／1.22个百分点，BR-J相对固定组件RelationOnly的增量为2.31／2.60个百分点；这些数字只展示对应比较的解释口径。两阶段四格用于分析条件增量，以及训练完成后的在线质量与时间取舍；聚合成绩尚不能确定对象重叠。真实监督漂移、目标模型的端点错误分布及方法运行仍待验证，局部与全局求解的采用优先级尚未确定。',
'主实验仍以AAEC与CDCP规模的假设计数演示比较口径：训练侧分别固定基础损失或增强集合，推理侧区分组件可变性、集合表达与求解资源取舍。另在两语料各8篇训练侧文档上，以gpt-5.6-luna真实预测和启发式对象分数执行轻量修正及固定组件对照。AAEC完整关系F1由0升至2.82，CDCP由5.71降至0；实际轨迹同时呈现端点调整后的关系恢复、候选缺失和错误评分导致的真阳性损失。AAEC新增30个正确组件中28个来自标点边界变体，不能将其全部归因于联合事务。该小样本试验提供了可追溯的运行案例，尚未验证训练侧监督保持、完整BR-J的效果或两阶段互补性；局部与全局求解的采用优先级仍待受控比较。')
replace('Explicitly assumed counts at AAEC and CDCP scales illustrate hypothetical outcomes, not empirical model performance or validated forecasts. Key training comparisons examine the overall data-construction effect under a fixed base loss and learning increments on the same augmented set. For inference, RelationOnly and single-object controls test component changes and set-level expressiveness, while same-objective global optimization tests resource tradeoffs. A sequential strategy provides a supplementary comparison of joint decision-making. Under the assigned counts, paired learning adds 1.21/1.22 relation F1 points, while BR-J exceeds fixed-component RelationOnly by 2.31/2.60 points; these values illustrate the interpretation of the respective comparisons. A four-cell analysis examines conditional gains and online quality–time tradeoffs after training costs have been incurred; aggregate scores do not identify object overlap. Actual supervision drift, endpoint-related errors in the target model and method performance remain to be tested, and the choice between local and global solving is unresolved.',
'The main experimental comparisons still use explicitly assumed counts at AAEC and CDCP scales. They separate data construction from learning on fixed augmented data, and distinguish component changes, set-level expressiveness, and solving costs. A separate pilot uses actual gpt-5.6-luna predictions on eight training-side documents per corpus, heuristic object scores, and lightweight repair with a fixed-component control. Strict complete-relation F1 changes from 0 to 2.82 on AAEC and from 5.71 to 0 on CDCP. Recorded trajectories show relation recovery after endpoint changes, candidate limitations, and loss of a true relation when erroneous scores reward deletion. Of 30 newly correct AAEC components, 28 originate from punctuation-boundary variants; their recovery cannot be attributed entirely to joint transactions. This small pilot provides traceable execution cases, but does not validate supervision preservation, the full BR-J method, or complementarity between training and inference. The choice between local and global solving remains unresolved.')
replace('当前估算情景不建立真实问题发生率，诊断方案集中于附录H.1。','既存CPU诊断与16篇Luna试验已提供有限观察（D.3及4.6.7），但模型和候选配置均不等同于正式系统，不能据此建立目标系统的问题发生率；完整诊断方案见附录H.1。')
replace('附录C、D说明成果和构造材料，','附录C说明成果归属，附录D分别保存前期基础、CPU诊断、构造材料和Luna真实试验，')
replace('该弱模型的过度分割不能代表目标LLM，目标模型的完整诊断仍按附录H.1执行。','该弱模型的过度分割不能代表目标LLM。4.6.7进一步给出Luna真实输出的端点恢复及失败轨迹，但小样本、简化候选和未校准评分仍限制方法归因，正式目标模型的完整诊断按附录H.1执行。')
replace('算法先求出受影响关系的最优可行补全','算法先求受影响关系的合格可行补全（取得最优性证书时才称为最优）')
replace('本节表图和案例使用估算情景；求解状态、错误分布与真实延迟的新增诊断按附录H执行后另行报告。','4.6.1—4.6.6的主比较与图表使用估算情景；4.6.7单列已执行的Luna小样本案例。两者不共用实验身份、分母或成本口径，正式目标模型的求解、误差与延迟诊断仍按附录H完成。')
replace('本章固定T1训练条件，以I0为共同起点，按2.6.3区分贡献检验与求解策略比较。','本章主比较固定T1训练条件，以I0为共同起点，按2.6.3区分贡献检验与求解策略比较；4.6.7的独立试验未进行T1训练。')

main=[]
main.append(paragraph('为将机制说明连接到实际模型错误，记录AM-LUNA-20261010-001在AAEC与CDCP各8篇训练侧文档上生成预测，冻结候选和评分后执行BRJ-lite及RelationOnly。BRJ-lite是依赖闭合思想的轻量试验实现，候选来自同一回答中的两个图及标点边界变体，评分采用新上下文gpt-5.6-luna的启发式置信度。该模型未进行本文的专项适配、增强或成对训练，故结果不作为表4-3中完整BR-J的实测替代。样本、预算、实现差异及复算入口见D.7—D.9。'))
rows=[]
for ds in ['aaec','cdcp']:
 for method in ['MCR-only','RelationOnly','BRJ-lite']:
  m=metrics['aggregate'][ds]['metrics'][method]
  rows.append([ds.upper(),method,f"{m['C']['F1']*100:.2f}",f"{m['R']['F1']*100:.2f}"])
main.append(table('表4-9 Luna训练侧小样本的严格抽取结果（真实运行）',['语料','配置','组件F1','完整关系F1'],rows,[.8,1.5,1,1.4]))
main.append(paragraph('各语料均保留全部8篇文档，F1先汇总TP、FP、FN再计算；初始图由MCR选择，本次16篇均选择g0。AAEC新增30个正确组件、恢复2条正确关系，同时移除32条错误关系并新增58条错误关系；CDCP没有恢复正确关系，却损失了唯一一条初始真阳性。AAEC关系F1仅2篇提高、6篇不变，CDCP为1篇下降、7篇不变。未以这16篇训练侧样本作显著性或独立测试集泛化推断。'))
case_rows=[['AAEC 078','端点调整后恢复','0→10.53','新增1个TP，终态仍有8个FP'],['CDCP 01057','错误接受','33.33→0','低默认分使正确关系被删除'],['AAEC 037','候选完整对象缺失','0→0','池中0／16条金标完整关系'],['CDCP 00396','错误标签之间替换','0→0','代理增分，FP仍为1']]
main.append(table('表4-10 按固定取例规则选择的真实前后案例',['文档','观察类型','关系F1前→后','关键结果'],case_rows,[1.1,1.5,1.2,2.3]))
main.append(paragraph('取例规则为按关系F1的提高、下降、不变分组，在各语料组内取文档ID最小者；规则在输出评价前登记。AAEC无下降例，CDCP无提高例，不补造缺失类别。以下坐标为原文0起始半开字符区间，标签按原始运行记录保留大小写；它们区别于正文方法的token记号，可在原始标注中核对。'))
main.append(paragraph('（1）AAEC essay078：边界改变后重建完整关系。原文Premise [1766,1802)为“it may spur its economic development”，其支持Claim [1511,1587)“taking environmental consequences seriously can enhance working efficiencies”。初始c012和c010均多含句末句号，严格端点未命中；第62次尝试将c010换为c009，第83次再将c012换为c011，删除旧端点相关对象并重新选择关系，最终加入supports关系r0329。后一次组件效用增加0.12、关系效用增加0.24，满足分项门和严格总效用门。终态关系计数为1 TP、8 FP、9 FN，组件F1为50.00。该轨迹显示端点更新与关系重建实际发生，但没有单独标点规范化及分步对照，不能由此证明联合决策的必要性。'))
main.append(paragraph('（2）CDCP 01057：代理门通过却误删真关系。原文fact [139,178)为“The check either bounced or it did not.”，金标reason关系指向policy [0,138)：该段主张州法或联邦法应惩罚开出空头或已关闭账户的支票，并包含有罪推定。初始r0063完整匹配金标，但评分记录未给它覆写值，按预定规则取0.05，效用为−0.90。第0次尝试保持组件不变并删除该关系，组件效用差为0、关系效用差为+0.90，合法性和预算通过后提交，真实TP由1降为0。RelationOnly也丢失同一关系。此例将失败定位于评分输入及默认值处理，求解器遵守接受门本身不能保证语义正确。'))
main.append(paragraph('（3）AAEC essay037：固定候选限制恢复。池内仅覆盖2／21个正确组件，0／16条完整正确关系；修正后组件F1为13.79，关系仍为0 TP、8 FP、16 FN。由于完整金标关系均不在池中，延长当前求解时间也不能恢复它们。该例支持先核查完整对象覆盖，不能用于判断局部与全局求解器的相对能力。'))
main.append(paragraph('（4）CDCP 00396：增分不等于改对。该文档没有金标正关系，初始evidence关系为FP。修正以同端点的reason替换它，评分由0.88升至0.94，关系效用增加0.12，而FP仍为1。按零分母约定，两状态关系F1均为0；需要查看完整对象变化，才能识别这次错误标签之间的替换。'))
main.append(paragraph('这些案例给出的研究线索是：覆盖决定哪些完整对象可被选回，评分决定代理门会奖励什么，合法事务保证的是依赖与计费一致。三者均需检查，不能以合法提交代替真实恢复。AAEC恢复的30个组件中28个来自句末标点变体；唯一拆分发生在CDCP 00428，组件F1由50.00降至40.00，且本次没有合并提交。因此，本次试验尚未提供拆合或集合动作必要性的正向证据，也未关闭完整方法的受控比较缺口。'))
start='#### 4.6.7 案例分析\n\n';end='### 4.7 本章小结'
a=text.index(start)+len(start);b=text.index(end,a)
changes['section_replacements'].append({'start':'4.6.7 案例分析','end':'4.7 本章小结','old_markdown':text[a:b],'blocks':main})
text=text[:a]+blocks_md(main)+text[b:]
replace('现有人工计数展示了比较口径，不能确定真实采用条件。','现有人工计数展示了比较口径；独立Luna试验补充了真实恢复、候选缺失与评分误改轨迹，但简化实现和小样本不足以确定完整方法的真实采用条件。')
replace('该观察只属于弱模型的单阶段组件诊断，不能解释本章四格关系对象的互补性；目标模型的同批对象对齐与真实案例仍按H.4补充。','该观察只属于弱模型的单阶段组件诊断。Luna试验还呈现AAEC组件FP净变化为0、实际新增和移除FP却各34个，以及CDCP 00396的错误关系标签替换（4.6.7及D.8）。两类运行共同说明净计数会隐藏对象更替；它们都不是同批训练四格输出，尚不能解释两阶段互补性。')
replace('数学构造说明动作和决策边界，人工成绩展示比较口径；','数学构造说明动作和决策边界，人工成绩展示比较口径，Luna小样本则记录了端点重建及评分误删的实际过程；')
replace('正文主成绩、增强审计判断和设定成本均为估算情景，新增方法尚未完成真实语料训练、语义审阅及求解比较。附录D.3的既存CPU输出复算提供了有限的真实诊断统计，其模型、对象范围及运行条件与主实验分开。','正文主比较、增强审计判断和设定成本仍为估算情景，训练侧增强、成对学习、人工语义审阅及同目标局部／全局比较尚未完成。附录D.3保留真实CPU诊断；4.6.7及D.7—D.9补充16篇Luna真实预测、32个文档策略运行及局部ILP轨迹。后者采用训练侧样本、标点补充池和未校准的同型号评分，不能替代正式目标模型的完整实现。实际求解已在轻量实现中执行，完整训练到推理链路、超时及提交失败分支仍须另外验收。')
replace('真实同文档展示案例仍待按H.4补充。','D.7—D.9及4.6.7另提供Luna同文档前后案例；样本来自本诊断划分的子集，模型及运行身份分开，不能相加为198篇独立诊断文档。')
replace('教学例只解释机制，人工片段不能更名为实际运行案例。','教学例只解释机制，人工片段不能更名为实际运行案例。4.6.7已按独立Luna试验的固定规则给出改善、受损与不变案例；该试验没有训练四格、分步对照及经事后验证的错误拒绝病例，缺失类别不由推演填补。')
replace('第三阶段复用同一批输出，形成至少一项对象级综合认识及少量同文档真实前后案例，再以结果替换诊断方案。','第三阶段复用正式同批四格输出，形成至少一项对象级综合认识及同文档前后案例。现有Luna案例已补足轻量推理层面的真实展示，但缺少训练因素及完整对照，不能据此将四格对象分析标为完成。')
insert_after('附录D.3另以research_0920/results中的既存运行清单、候选预测与编辑记录为输入，由_revision_1010_v8/analyze_saved_diagnostics.py复算；diagnostic_supplement.json保存输入哈希、判定口径和汇总，六份diagnostic_*.csv保存文档错误、端点、覆盖、提议、策略及对象变化统计。该入口不生成第三至第五章的估算计数，也不进行模型训练或求解。',
'真实案例的独立入口为research_1010_v7_luna。protocol.json、sample_manifest.json及model_dispatch_manifest.json记录试验身份、样本和模型任务；candidate_pools.json与scoring_protocol.json固定候选及评分。results/run_001保存输入／输出冻结哈希及32份逐步轨迹，results/evaluation_001保存严格计数、对象差集和独立审核。逐例原文、原生标注及前后图见1011_v7_Luna逐例标注与修正轨迹.md。本文按这些既存记录整合案例，未新增模型调用、训练或求解运行。')

appendix=[heading('D.7 Luna真实试验的条件与来源')]
appendix.append(paragraph('试验AM-LUNA-20261010-001实际执行于上海时间2026年10月10日至11日。每语料按文本长度四分位分层，每层按固定SHA-256顺序取2篇，共16篇；使用已有官方训练侧审计划分，不读取官方测试集。全部16篇与D.3的182篇按文档ID和全文哈希对应，为其子集。AAEC原始训练文件在本地读取为322篇，CDCP沿用排除00411后580篇的记录；该身份不改写表2-2的参考配置。模型可能在预训练时接触公开语料，未作污染排查。'))
appendix.append(paragraph('请求模型为gpt-5.6-luna，reasoning effort为low；实际快照、温度、采样种子和token数未由调度工具暴露，保持未记录。两项预测任务分别处理两语料，每篇在同一回答中给出g0、g1，不视为独立抽样；另三项任务在新上下文中评分。五项任务不是五次底层API调用，生成与评分仍属同型号模型，未证明误差独立。提示仅提供盲输入，评分及输出冻结后本地评价才读取金标；这是输入与指令层面的隔离，共享文件系统没有操作系统级访问封锁。'))
appendix.append(paragraph('候选合并两图的带类型跨度，并按预定规则补充去句末标点的边界变体。二元槽位在兼容候选之间枚举，多源槽位来自生成图及其端点变体，没有穷举论文主协议的全部多源组合。210个组件均有显式评分；5404个完整关系中149个被显式覆写，其余5255个使用事前固定默认值0.05。这里的分数为启发式置信度，未训练、校准第四章的对象评分器。输入、评分、代码及预算均在金标评价前冻结，评价后不按结果改分或补候选。'))
appendix.append(paragraph('两种修正策略使用同一合法初始图、候选池、评分及评价器。每个事务最多3个组件编辑，累计组件／关系编辑上限24／96；每轮至多32次尝试、3次接受，共4轮，批长6。组件与关系的错误代价及权重均为1，严格总效用门为0.01；允许空图，不加无环约束。实际使用SciPy 1.13.1的HiGHS MILP，单线程、每调用上限0.25秒，逐文档累计求解上限AAEC 3秒、CDCP 5秒。RelationOnly保持组件集合固定。'))
appendix.append(heading('D.8 完整对象计数与逐文档结果'))
rows=[]
for ds in ['aaec','cdcp']:
 for method in ['MCR-only','RelationOnly','BRJ-lite']:
  m=metrics['aggregate'][ds]['metrics'][method]
  rows.append([ds.upper(),method,'／'.join(str(m['C'][k]) for k in ['TP','FP','FN']),'／'.join(str(m['R'][k]) for k in ['TP','FP','FN'])])
appendix.append(table('表D-7 Luna试验的完整组件与关系计数（真实运行）',['语料','配置','组件TP／FP／FN','关系TP／FP／FN'],rows,[.7,1.3,1.7,1.7]))
appendix.append(paragraph('本试验以原文字符跨度、类型及完整关系键作精确集合匹配，未另行验证其与第二章正式token评价器的逐项等价性，故不与主表混算。金标组件共AAEC 126个、CDCP 49个，金标完整关系分别82条、17条。冻结池精确覆盖组件33／126、19／49，完整关系3／82、1／17；CDCP两条多前提金标关系均未进入池。因此本次数据不能评价多前提恢复效果。RelationOnly在AAEC移除32个初始关系FP且未恢复TP，在CDCP损失1个TP、移除16个FP并新增3个FP；不能将较少输出直接解释为更好恢复。'))
appendix.append(paragraph('BRJ-lite的AAEC组件对象差集为新增正确30、损失正确0、新增错误34、移除错误34；关系为2、0、58、32。CDCP组件对应0、1、6、4，关系对应0、1、5、14。上述顺序按完整语义键比较初始与终态，不把累计编辑次数当作对象数。AAEC的28个标点变体恢复及CDCP的真阳性损失均保留，不因总体分数或解释便利而删除。'))
rows=[]
for d in metrics['documents']:
 m0=d['metrics']['MCR-only'];m1=d['metrics']['BRJ-lite']
 rows.append([d['id'].replace('aaec_essay','AAEC ').replace('cdcp_','CDCP '),f"{m0['C']['F1']*100:.2f}→{m1['C']['F1']*100:.2f}",f"{m0['R']['F1']*100:.2f}→{m1['R']['F1']*100:.2f}",f"{d['coverage']['C_hits']}／{d['gold_C']}",f"{d['coverage']['R_hits']}／{d['gold_R']}"])
appendix.append(table('表D-8 全部16篇文档的初始至BRJ-lite结果及候选覆盖',['文档','组件F1前→后','关系F1前→后','组件覆盖','关系覆盖'],rows,[1.2,1.5,1.5,1,1],split=[6]))
appendix.append(paragraph('表D-8按原始文档ID列出全部样本，覆盖以完整跨度、类型及关系源集合／目标／标签严格匹配，分母为各文档金标数。CDCP 00396的关系覆盖为0／0，表示该文档无正关系，不计算覆盖百分比；其一个FP的标签更换见4.6.7。零真阳性情形的F1统一为0，配合TP、FP、FN解释。该表没有省略组件下降但关系不变的00428、01282，也未把16篇结果扩展为语料基准。'))
appendix.append(heading('D.9 实际执行与方法解释边界'))
appendix.append(paragraph('本次32个文档策略运行均返回合法图，共评估1738项提议，提交139项。1632次MILP调用中516次返回最优、1116次无可行解；后者包含258次最优解唯一性检查，不等于1116个运行失败。全部139项提交均完成最优值、最少关系编辑及唯一性核查。本次未发生超时或无incumbent回退，不能据这些成功轨迹声称相关失败分支已经历真实验收。金标评价前输出冻结，独立审核逐项检查原生标注、预算、事务外关系和效用门；本地重放32个运行得到相同终态及接受尝试序列。'))
appendix.append(paragraph('轻量实现与正文仍有明确差异。候选生成没有采用本文训练骨干及完整两阶段抽取；多源枚举受生成图限制；评分没有使用训练及校准后的神经对象模型。六类队列虽保留轮转、冲突闭合与批内完整效用比较，类内却按规范对象键排序，而附录B.3按组件效用增益排序；有限尝试下这会改变访问路径。实现容差为10⁻⁸，并在严格总效用约束中加入10⁻⁶余量，与正文统一规约需再核对。因此BRJ-lite始终单列命名，不把其轨迹视为算法4-1的完整等价实现。'))
appendix.append(paragraph('AAEC的BRJ-lite与RelationOnly修正阶段总耗时分别0.434276、0.124535秒，CDCP为0.120818、0.110312秒；对应累计求解时间为0.104983、0.060285、0.028174、0.038296秒，均为各8篇总和。这些时间从冻结候选和评分输入后计量，不包含模型预测、评分、环境导入或完整准备成本，不能代入表4-8或作为端到端速度优势。当前没有同预算全局、单对象动作、分步策略、标点规范化专用对照，也没有训练四格，因而不能判定集合动作的增量、联合决策的必要性或局部策略的采用条件。'))
appendix.append(paragraph('后续首先在共同候选中加入仅标点规范化对照，并检验低默认关系分对原真阳性保留的影响；这属于待执行的控制实验，不在当前记录中补填结果。真实增强漂移与成对训练仍须独立完成。已有案例能够支撑“实际出现何种恢复或失败”的描述，不能替代“新增机制为何有效”的受控证据。'))
anchor='## 附录E 前期数值与协议存档';assert text.count(anchor)==1
text=text.replace(anchor,blocks_md(appendix)+anchor)
changes['sections_before'].append({'anchor':'附录E 前期数值与协议存档','blocks':appendix})
for a,b in changes['global']:text=text.replace(a,b)
(R/'report_1011_v9_full.md').write_text(text)
(W/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
build=read(R/'_revision_1010_v8/docx_build.json')
build['headings']=[[len(m.group(1))-1,m.group(2)] for m in re.finditer(r'(?m)^(#{2,4}) (.+)$',text)]
build['captions']=[c for c in build['captions'] if not c.startswith('表4-9 ')]
for bs in [main,appendix]:
 for b in bs:
  if b['type']=='table':build['captions'].append(b['caption'])
build['captions'].sort(key=lambda s:text.index(s))
build['source_sha256']=hashlib.sha256(text.encode()).hexdigest();build['output']=str(R/'report_1011_v9_full.docx')
build['retained_template_sha256']=hashlib.sha256((R/'report_1010_v8_full.docx').read_bytes()).hexdigest();build['rendered']=False
(W/'docx_build.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'source':str(R/'report_1011_v9_full.md'),'changes':len(changes['text_replacements']),'new_sections':3,'new_tables':4,'removed_tables':1,'headings':len(build['headings']),'captions':len(build['captions'])},ensure_ascii=False))
