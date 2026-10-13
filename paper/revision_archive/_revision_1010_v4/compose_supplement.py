"""Bounded manuscript revision from explicit simulated records, never empirical claims."""
from pathlib import Path
import json,re,hashlib,difflib
W=Path(__file__).resolve().parent;R=W.parent
old=(R/'report_1010_v3_full.md').read_text();s=old.replace('_revision_1010_v3/','_revision_1010_v4/').replace('1010-v3','1010-v4');r=json.loads((W/'supplement_results.json').read_text());changes=[];res=json.loads((W/'scenario_results.json').read_text())
def replace(a,b,why):
 global s
 assert s.count(a)==1,(why,s.count(a));s=s.replace(a,b);changes.append({'action':'replace','reason':why,'old_chars':len(a),'new_chars':len(b)})
def section(start,end,new,why):
 a=s[s.index(start):s.index(end,s.index(start))];replace(a,new.rstrip()+'\n\n',why)
def table(caption,headers,rows):return caption+'\n\n|'+'|'.join(headers)+'|\n|'+'|'.join([':---']+[':---:']*(len(headers)-1))+'|\n'+'\n'.join('|'+'|'.join(map(str,row))+'|' for row in rows)+'\n'
def f(x):return f'{x:.2f}'
replace('稿件说明：本稿为模拟数据演示稿。除附录E历史存档和明示的数学构造外，新增实验表图、审计判定、运行配置、成本及案例均为人工设定并由程序汇总的计数级模拟情景，不代表真实实验记录或效果预测。本稿供方法与分析推敲；正式稿须以同口径实测材料整体替换。','稿件说明：本稿为模拟数据演示稿。除附录E历史存档和明示的数学构造外，实验表图、审计判定、运行配置、成本及案例均为程序构造的模拟情景，不代表真实实验记录或效果预测。本版新增模板改写、预算状态、外部方法占位成绩和关系对象清单；外部占位值不是原论文成绩或真实复现。正式稿须以同口径实测材料整体替换。','cover disclosure expands from counts to four explicit synthetic record families')
replace('本版使用AAEC与CDCP人工计数情景演示评价，数值不代表真实模型实验。情景中，同基础损失的数据构造差值为1.79／1.83个关系F1百分点，同增强集合上的成对项差值为1.92／1.88个百分点；中心差异与两阶段关系交互区间均包含0。同求解预算全局ILP的关系F1和初始真阳性保留率略高，BR-J仅节省4.19%／4.73%的端到端时间。现有材料说明了两类增量的区分及结构恢复的质量与代价取舍，尚不能证明真实增益或局部方案的采用优势。','本版以AAEC与CDCP规模的模拟情景组织评价，数值不代表真实模型实验。同基础损失下，数据构造差值为1.79／1.83个关系F1百分点；同增强集合上的成对项差值为1.92／1.88个百分点。共同生成池的模板改写保留了字面变化，严格筛选同时损失复杂文档覆盖。新增预算情景中，CDCP大规模组在36秒时限内呈现局部优势，放宽时限后该优势消失；外部方法占位对照保留更强系统，关系对象补全同时出现共同修复、组合新增和误改。这些模拟结果将局部事务定位为条件选项，并展示两阶段部分重叠的收益结构，不支持普遍优越性或真实效果结论。','CN abstract follows simulated findings and negative evidence')
replace('Artificial count scenarios for AAEC and CDCP illustrate evaluation; these are not empirical model results. The scenarios separate data-construction differences of 1.79/1.83 relation F1 points under the same base loss from paired-learning differences of 1.92/1.88 points on the same augmented data. Intervals for center differences and relation interactions include zero. Equal-solver-budget global ILP has slightly higher relation F1 and initial true-positive retention, while BR-J saves only 4.19%/4.73% of end-to-end time. The available material distinguishes these increments and illustrates quality–cost trade-offs in structural recovery; it establishes neither empirical gains nor an adoption advantage for local repair.','Simulated scenarios at AAEC and CDCP scales illustrate evaluation; they are not empirical model results. They separate data-construction differences of 1.79/1.83 relation F1 points under the same base loss from paired-learning differences of 1.92/1.88 points on the same augmented data. Shared-pool templated rewrites retain lexical variation, while stricter screening reduces coverage of complex documents. In the added resource scenario, local repair benefits the large CDCP group under a 36-second deadline, but loses this advantage when the deadline is relaxed. External-method placeholders include a stronger comparator, and constructed relation memberships show shared recovery, combination-specific recovery and damage. These scenarios position local transactions as a conditional option and illustrate partially overlapping gains across stages, without establishing universal superiority or empirical effectiveness.','EN abstract synchronized')
replace('上述低漂移率只描述被接受因素，不能证明增强具有充分变化，也不能排除选择偏向。只要一个受检因素失败就拒绝整个变体，可能使关系密集、受检因素较多的文档更难通过；单因素判断存在误差时也需警惕这一风险，但当前材料不能认定偏差已经发生。原始增强文本缺失，故本节不报告非复制、编辑距离或复杂度分组结果，测量口径统一放在附录H.2。','上述低漂移率只描述被接受因素，不能单独证明增强有用。3.6.6节新增共同生成池的模板文本模拟，联合检查非复制、编辑距离、变体漂移与复杂度分组覆盖；它提供可复算的模拟实例，不将规则文本充作真实模型改写，也不与本节因素分层审计合并分母。','replace missing-text placeholder with explicit synthetic data route')
names={'plain':'普通筛选','qos':'QOS式筛选','full':'完整筛选'}
rows=[]
for x in r['augmentation']:
 rows.append([x['dataset']+' '+names[x['method']],f"{x['accepted']}/{x['attempts']}",f"{x['noncopy']}/{x['accepted']}",f(x['edit_median']),f"{x['drift_variants']}/{x['accepted']}",f"{x['low_covered']}/20；{x['high_covered']}/20"])
aug='''#### 3.6.6 共同生成池的表达变化与覆盖

完整筛选在新增模拟中保留了改写幅度，但其收益伴随源覆盖偏移。每种语料构造40篇模板源文档，低、高受检因素组各20篇，分别含4和12个因素；每篇生成4个共同候选，三种筛选读取同一160个变体，按固定顺序最多接受2个。原槽位、改写槽位、模拟因素漂移与逐方法决定均保存。检测率和误报率由生成器预设，不能解释为实际审核器准确率。

'''+table('表3-10 共同池的变化与覆盖诊断（新增模拟情景）',['语料与筛选','接受／尝试','非复制／接受','编辑距离中位数','漂移变体／接受','低／高组覆盖'],rows)+'''
完整筛选在AAEC接受67个变体，其中59个非复制、2个含设定漂移；CDCP接受65个，其中54个非复制、未出现设定漂移。零漂移只描述有限模拟样本，不表示风险为零。三种筛选的编辑距离中位数均为0.75，说明本模拟的主要变化来自筛选，而非凭空扩大文字差异；仅3类固定改写模板也限制了这些数字能代表的表达丰富度。

完整筛选覆盖低复杂度组20／20篇，而高复杂度组降至18／20和16／20篇。由于两组的漂移生成率和因素数同时不同，此结果显示选择偏移的存在，不能将全部差值单独归因于检查数量。其设计含义是保留影响域检查，同时监测分层覆盖与源权重；不以极低漂移率替代训练收益。真正的任务有用性仍由表3-5与表3-6的受控成绩比较演示，文本变化和学习收益承担不同证据功能。

'''
replace('### 3.7 本章小结',aug+'### 3.7 本章小结','add one short evidence chain for useful augmentation')
replace('本章将影响域检查和标注对应连接到成对学习。人工情景把数据构造、头监督和成对项增量分开，同时保留中心区间跨0及源覆盖下降，说明可靠性判断不能只看接受池。真实必要性、有效变化和学习收益仍待验证。','本章将影响域检查和标注对应连接到成对学习。计数与模板情景分别展示条件学习增量、字面变化与复杂度覆盖损失；中心差异区间仍包含0。因此保留影响域和可靠对应作为方法主线，将结论中心视为默认选择，并以覆盖约束限制严格筛选的适用范围。这一模拟证据链尚不能代替真实训练与语义审计。','chapter 3 synthesizes new data rather than repeating missing work')
# External comparator matrix, visible placeholders and inherited method rows.
newrows=[]
for method,label in [('Kawarada_proxy','Kawarada式占位'),('UniASA_proxy','UniASA式占位')]:
 vals={x['dataset']:x for x in r['external'] if x['method']==method}
 newrows.append([label]+[f(vals[ds][ob]['mean'])+'±'+f(vals[ds][ob]['sd']) for ds in ['AAEC','CDCP'] for ob in ['component','relation']])
for method,label in [('t1_i0','T1＋I0'),('t1_i1','T1＋BR-J'),('global_equal','T1＋全局等时限')]:
 newrows.append([label]+[f(res['metrics'][ds][method][ob]['mean'])+'±'+f(res['metrics'][ds][method][ob]['sd']) for ds in ['AAEC','CDCP'] for ob in ['component','relation']])
ext='''#### 4.6.7 外部系统的占位比较

外部比较用于判断本方法在强系统面前的定位。表4-10加入Kawarada文本生成路线与UniASA路线的占位模拟[7,48]：为两种方法预设召回与误检分布，在与主表相同的模拟文档、金标数和三种子下生成逐文档计数。没有运行作者代码、加载其权重或抄用原论文成绩；占位结果不预测真实排名。任务对齐与实现转换仍按附录G执行。

'''+table('表4-10 共同评价口径下的外部方法占位对照（模拟成绩）',['方法','AAEC组件','AAEC关系','CDCP组件','CDCP关系'],newrows)+'''
在这一设定下，UniASA式占位关系F1为68.52和65.51，高于T1＋BR-J的66.56和61.96；Kawarada式占位则为64.80和60.79。由此，内部受控增量不自动等于对领域系统的全面领先。本稿将贡献限定为增强监督与结构恢复的组织及其条件性作用，不用内部消融代替外部定位，也不据占位分数宣称超过或落后于原作者方法。

与表3-6的同骨干损失消融不同，此处是系统层面的比较示范；骨干、额外数据及输出转换没有在模拟中真实实现，不能进一步解释差异来源。附录G保留两条正式接入路线，后续实测必须分别报告原配置复核与共同任务比较。

#### 4.6.8 裁剪前成本与局部采用条件

新增预算情景将共同准备、求解和回退放入同一逐文档时限。它复用80／148篇模拟文档的金标与已存逐文档终态计数，再由声明的规模和成本函数决定在时限内完成的比例；不调用实际ILP。分组使用预设规模排序的三等分，用于情景分层，不能充作训练侧实测切点。两种方法使用相同候选规模、准备成本和预检失败文档，局部累计预算与全局净预算的区别仍然存在。

'''
rr=[]
groupnames={'small':'小','medium':'中','large':'大'}
for x in r['resources']:
 if x['group']=='all':continue
 rr.append([x['dataset']+' '+groupnames[x['group']],x['docs'],int(x['slots_median']),x['slots_max'],f(x['preparation_p95']),f"{x['precheck_fail']}/{x['docs']}"])
ext+=table('表4-11 裁剪前规模与预检成本（新增模拟情景）',['语料与规模','文档数','槽位中位数','槽位最大值','准备P95秒','预检失败'],rr)
ext+='''
每个槽位对应两个正标签评分对象，补充保留上限4096只约束后续搜索数量。CDCP预检失败10／148篇，均来自大规模组；它们以初始状态回退，仍保留金标和耗时分母。失败文档的潜在可恢复覆盖保持未知，不能填作0。预检阈值、合法槽位比例和每对象成本均为公开设定，表中准备P95从这些逐文档模拟耗时计算。

'''
rr=[]
for ds in ['AAEC','CDCP']:
 for mult in [.5,1,2]:
  def get(method):return next(x for x in r['budget'] if x['dataset']==ds and x['group']=='all' and x['multiplier']==mult and x['method']==method)
  l,g=get('local'),get('global');sec=int((24 if ds=='AAEC' else 36)*mult)
  rr.append([f'{ds} {sec}秒',f(l['mean_f1'])+'±'+f(l['sd_f1']),f(g['mean_f1'])+'±'+f(g['sd_f1']),f(l['p95_s'])+'／'+f(g['p95_s']),f(l['fallback_pct'])+'／'+f(g['fallback_pct']),f(g['timeout_pct'])])
ext+=table('表4-12 同端到端时限的质量与尾延迟（新增模拟情景）',['语料与时限','局部关系F1','全局关系F1','P95秒 局部／全局','回退% 局部／全局','全局超时%'],rr)
ext+='''
AAEC在24秒时限下，局部和全局都完成设定过程，全局均值略高；12秒时限导致双方90%的文档种子记录回退，说明准备阶段即可耗尽资源。CDCP在36秒时限下，局部和全局均值为61.53与61.07，文档配对差值区间为[−0.35, +1.24]，整体质量差异不稳定；但局部P95为34.30秒，全局触及时限，后者34.23%的记录发生求解超时。双方6.76%的预检失败均已计入，这部分不能归于求解方法。

进一步看预先声明的大规模组，CDCP局部相对全局增加1.80个百分点，文档配对95%区间为[+0.43, +3.19]；72秒时限下则变为−0.54，区间[−1.66, +0.50]。该模拟支持“特定规模与时限下的条件选项”，不支持把局部方案设为所有文档的默认最优。区间只描述给定生成假设下的文档变化，不能覆盖成本函数设错或真实求解器行为的偏差。

![同端到端时限下的关系结果与规模边界](_revision_1010_v4/figures/budget_conditions.png)

图4-5 预算变化下的整体表现与大规模边界（新增模拟情景）

模拟中，充足时限恢复了全局较高的终态质量，准备失败又限制了两种方法的共同上限。故本稿保留依赖闭合恢复框架，将局部事务作为紧预算大规模情景的候选策略，并允许按数据规模和时延要求选择全局方案。此处使用独立成本函数，不能将表4-8的旧平均秒数与表4-12拼接成同次运行曲线；正式部署阈值仍须实测确定。

'''
replace('### 4.7 本章小结',ext+'### 4.7 本章小结','add external placeholders and complete resource scenario')
replace('本章明确了集合事务的表达与决策条件。人工情景中，BR-J优于所定义分步策略，但与等求解预算全局方法相比尚无突出质量、时间或保留率优势。局部方法的使用条件需由真实资源和变更轨迹检验；第五章继续分析其与训练条件的关系。','本章明确了集合事务的表达与决策条件。旧情景保留强全局对照，新增占位系统也未给本方法全面领先的排名；预算模拟进一步把局部优势限制在部分紧预算大规模条件。由此，局部事务保留为可选择的求解策略，其用途由完整成本和质量共同决定。第五章继续通过对象补全检查训练与推理增量的重叠和损失。','chapter 4 bounded outcome')
replace('本章复用四格人工计数与成本，分析条件增量、净错误变化和在线配置取舍，并说明超边规模的评价范围。聚合计数能支持这些比较，不能识别共同修复对象或训练影响修正的具体路径；相应分析设计集中于附录H.4。','本章复用四格人工计数与成本，并新增与原关系计数逐项相容的对象补全情景，分析条件增量、共同修复、组合新增和误改。对象身份由程序赋予，不是从计数唯一反推，也不代表真实原文对象；补全只用于演示聚合成绩之外的分析。训练影响候选与评分的路径仍不作因果分解。','chapter 5 scope now includes explicit memberships')
replace('### 5.2 净错误变化与对象分析边界','### 5.2 净错误变化与对象修复重叠','replace boundary-only heading with simulated findings')
obrows=[]
for x in r['objects']:
 obrows.append([x['dataset'],x['training_only'],x['repair_only'],x['common'],x['combination_new'],x['t1_destroyed'],x['remaining_fn']])
ob='''同一净增量可以由不同的恢复和损失组成。本版为四格关系计数构造一组完整对象键，逐文档、逐种子保持TP、FP、FN，并约束T1到组合的恢复、误改、新增FP和移除FP总数与表4-7一致。键包含源文档身份、模拟端点坐标、类型、完整源集合和标签；不重新构造组件预测图，也不把抽象坐标映射为真实原文。表5-6将各集合直接枚举后累加，同一金标可在三个种子分别计数。

'''+table('表5-6 四格关系对象的修复与损失（补全模拟情景）',['语料','训练独有','修正独有','共同修复','组合新增','T1命中受损','组合仍遗漏'],obrows)+'''
AAEC与CDCP的共同修复分别为353和505，占两种单阶段新增命中并集的51.91%和68.89%；同时仍有173／120个训练独有、154／108个修正独有对象。组合另外恢复96／68个未被两种单阶段覆盖的对象，但也破坏65／46个T1原有命中。共同修复、独有修复和损害可以同时存在，因此组合有增量并不要求收益完全独立，更不等于交互项稳定为正。

这一补全与原主表严格相容，却不是唯一相容的对象分布。它支持的是当前模拟中的部分重叠结构，不能反过来证明旧计数隐含了这些对象关系。组合新增也不直接称为机制协同：不同训练条件下候选和评分可能共同变化，须另有受控设计才能分解原因。

表5-7列出按类别和固定文档顺序选择的三个模拟对象。四格列中1表示命中该完整金标关系，0表示未命中；源、目标跨度均为程序赋予的半开坐标，类型分别为Premise与Claim，标签为Support。

'''+table('表5-7 相同模拟对象在四格中的命中状态',['类别与对象','T0I0','T1I0','T0I1','T1I1'],[['共同修复 001：[108,111)→[116,119)',0,1,1,1],['组合新增 001：[120,123)→[128,131)',0,0,0,1],['T1受损 018：[48,51)→[56,59)',0,1,0,0]])+'''
三例均为AAEC规模情景、种子17，文档全名分别为SIM-AAEC-001与SIM-AAEC-018。它们提供同一对象的前后对照，不冒充真实语句或真实模型案例；完整清单同时保留未展示对象和全部剩余遗漏。模拟关系FP的移除与新增仍单独累计，避免只看命中增长。
'''
replace('同一净增量可以由不同的恢复和损失组成。当前TP、FP、FN未绑定完整预测对象，无法计算共同／独有修复比例，也不能把负交互解释为已证实的对象重叠。相关集合定义与同文档案例规则见附录H.4。',ob,'replace object-analysis placeholder with fully enumerated synthetic completion')
replace('上述排序限于设定的平均时间。P95、超时、无可行解、缓存及批量吞吐可能改变实际选择；等端到端时限与真实图规模分组尚需附录H.3的运行记录。若相同资源下局部方法没有稳定质量或变更控制收益，简化它比继续增加规则更有意义。','上述排序限于旧情景的平均时间。4.6.8节新增逐文档预算模拟后，CDCP大规模组在36秒条件下出现局部优势，时限放宽后不再保持；因而局部方法采用条件应绑定规模和时限。真实缓存、批量吞吐与评分成本仍可能改变边界。若实测中同资源下没有稳定质量或变更控制收益，应简化局部设计。','online selection integrates new scenario without merging independent cost tracks')
replace('综合分析得到三点情景内认识：训练与推理均有条件增量，但关系交互尚未显示稳定超加；在线配置的选择受到训练能否摊销以及修正额外时延影响；BR-J面对等求解预算全局对照时，现有质量、时间与保留率不足以建立突出优势。对象重叠、训练对候选和评分的传递，以及真实失败构成仍需完整运行材料。由此，两阶段组合应作为可检验的配置选择，而非预设处处优于单阶段的方法结论。','综合分析得到三点情景内认识：关系交互未显示稳定超加，但相容的对象补全可同时包含共同修复、独有修复、组合新增及误改；训练与推理投入的取舍取决于离线成本能否摊销；局部相对全局的优势仅在部分规模和时限条件出现。由此，两阶段组合及求解策略均应按条件选择，而非预设处处更优。真实对象分布、因果路径和采用阈值仍需实际输出检验。','chapter 5 synthesis from new object evidence')
replace('第一项工作把数据构造、头监督、成对项和中心策略分开比较，使不同差值对应不同变化条件。现有人工情景中，数据构造与成对项分别表现出条件增量，而中心差值区间包含0；因此贡献落在关系影响域及可靠对应的组织方式，结论优先保留为默认策略。','第一项工作把数据构造、头监督、成对项和中心策略分开比较。模拟成绩分别给出条件增量，模板文本诊断进一步显示严格筛选在保留字面变化的同时损失复杂源覆盖；中心差值区间仍包含0。因此贡献落在影响域及可靠对应的组织方式，结论中心只保留为默认策略，并须同时监测筛选质量和源覆盖。','conclusion answers usefulness within simulation')
replace('第二项工作明确了集合动作如何联合处理相互依赖的修改，但动作表达能力不等于使用价值。在当前情景中，BR-J相对分步策略改善关系结果；同评分、等求解预算全局ILP又取得略高关系F1和保留率，BR-J只节省少量端到端时间。这组人工材料没有建立局部方法的采用优势，实际定位仍待真实比较决定。','第二项工作明确了集合动作如何联合处理相互依赖的修改。等求解预算情景保留全局较高的终态质量；新增端到端预算模拟则把局部收益限制在CDCP大规模组的部分紧时限条件。因此本稿将依赖闭合作为恢复框架，将局部事务定位为条件选项，而非通用优胜方案。外部方法占位对照同样保留更强系统，避免把内部改进提升为领域全面领先。','conclusion positions local choice and external boundary')
replace('两阶段四格避免把组合总增量误写为相互独立或稳定超加。第五章进一步区分净计数与对象重叠，讨论离线训练投入、在线时延及完整超边范围。方法价值最终由现实问题规模、可复核输出和相应代价支撑；数学构造与文档复算负责检验定义和论述的内部一致性。','两阶段四格避免把组合总增量误写为相互独立或稳定超加。新增对象补全在逐项保持旧计数的同时，显式展示共同修复、组合新增与损害；离线训练投入、在线时限及完整超边范围共同限定配置选择。以上结论只在声明的模拟分布内成立，真实方法价值仍需由现实问题规模、可复核模型输出和相应代价支撑。','conclusion integrates objects without empirical overclaim')
replace('本版采用人工计数情景，尚未完成真实语料上的训练、增强审阅与求解比较，情景数值不用于证明方法有效。原始改写文本、四格完整预测和求解状态等材料缺失，使表达变化、对象级互补和真实尾延迟尚不能定量判断；外部方法已完成定位与接入条件核查，尚无本版同协议复跑成绩。','本版采用人工计数、模板改写、资源函数和对象补全情景，尚未完成真实语料上的训练、语义审阅与求解比较。新增材料使四项分析可以在模拟内部复算，但其漂移、对象身份和成本均来自设定，不能估计真实效应。外部方法只有显式占位成绩，没有作者系统的同协议复现；命名路线仅用于比较设计，不能据此评价原方法。','research limitations distinguish new simulation material from real evidence')
# G: retains actual implementation limitations but points to newly delivered simulated comparator.
replace('本稿未给出这些外部模型的同协议运行结果。Kawarada与UniASA作为优先表示审计入口；至少一种方法通过原生任务兼容性核查后，才能形成外部系统比较。GMAM、DENIM和动作模型仅作必要补充，QOS式适配不替代端到端外部对照。','本稿4.6.7节给出Kawarada式与UniASA式的显式占位模拟，不属于外部模型的同协议运行结果。两者仍作为优先审计入口；至少一种方法通过原生任务兼容性核查并真实运行后，才能形成实证系统比较。GMAM、DENIM和动作模型仅作必要补充，QOS式适配不替代端到端外部对照。','external implementation state remains honest')
# H plans remain formal protocols; replace no-data placeholders with new evidence index.
replace('现有人工情景的平均与P95耗时是设定输入，不是从真实逐文档延迟计算的尾分位，也没有真实求解证书。新预算轨和规模分组在取得日志前只作为协议，不补填超时率、gap或可行解覆盖。','旧情景的平均与P95耗时仍为设定输入。SIM-1010-V4新增逐文档成本函数、状态和计数，表4-11与表4-12据其计算尾分位、超时和回退比例；这些状态也是模拟值，没有实际求解证书，gap字段保持空值。正式预算轨继续按本节协议采集，不能用模拟状态替代实测日志。','H resource protocol now distinguishes old and new simulation tracks')
replace('### H.5 核心验证缺口与推进顺序','### H.5 模拟结果后的实证替换顺序','update H title after synthetic evidence completed')
replace('以下为尚未完成的核心验证，不能仅靠润色关闭。第一阶段使用有限固定真实文档，取得关系漂移、实际表达变化与源覆盖，并测量裁剪前枚举、完整评分和局部／全局求解的资源，失败文档保留。若漂移少、严格审核主要排斥复杂文档，或局部收益不足以抵偿复杂度，先收缩主张、简化设计。','本版已为增强用途、局部采用条件、外部比较及对象综合分析补齐模拟记录与结果，以下步骤用于替换为真实证据。第一阶段使用有限固定真实文档复核漂移、表达变化、覆盖及裁剪前成本。模板诊断提示的复杂文档覆盖损失和预算情景中的局部条件优势均须允许被推翻；失败文档保留，结果不支持时收缩主张或简化设计。','four simulation items are actually delivered, empirical replacement still pending')
replace('当前没有证据选择其中一种；日志可追溯并非局部独占优势，声称变更可控时须给出具体约束和实际表现。','当前模拟选择“条件选项”；正式定位须由真实结果重新决定。日志可追溯并非局部独占优势，声称变更可控时须给出具体约束和实际表现。','explicitly select local role within simulation')
# Add compact record index, assumptions and denominator details, rather than unbounded main text.
s+='''
### H.6 新增模拟记录与复算边界

新增材料身份统一为SIM-1010-V4，与旧主成绩轨分开。generate_supplement.py固定随机来源，由输入键哈希确定随机序列；生成器、各原始文件和汇总文件均登记SHA-256。没有调用真实模型、人工标注者或优化器。

增强诊断保存80篇模板源文档的320个共同改写候选，以及三种筛选共960条决定。4／12因素组各占一半，三种检测概率为0.18、0.55、0.90，误报概率为0.005、0.012、0.023；每源最多接受2个。漂移标签由规则赋予。非复制按槽位文本比较，编辑距离按固定英文单词、数字与标点切分；0.75的中位数来自有限模板，不表示自然语言表达多样性达到某一水平。新增诊断不与表3-3的因素均值或表3-9的训练源覆盖拼接。

资源情景复用228篇模拟文档。候选跨度数设为模拟金标组件数加8，每跨度2种类型；裁剪前合法槽位数取4.2.5组合上界的60%，每槽位2个正标签评分对象。AAEC／CDCP预检槽位阈值为9000／330000，端到端基准时限为24／36秒，再比较0.5、1、2倍。所有比例、单位成本和求解时间函数均为设定，不是硬件基准。完整状态记录包括准备超时、无incumbent超时、有可行状态超时、预检失败与完成；失败回退到已有初始计数，双方共同准备成本全额计入。

表4-12的标准差来自17、29、43三个种子；区间按文档成对重采样2000次，每次先汇总TP／FP／FN，再对种子F1取平均。规模组在模拟设计中按候选规模排序三等分，正文只解释预先列出的整体与大规模结果；全部组与预算点一并保存，不按有利结果挑选。预检失败所含金标数另存，未枚举对象的可恢复覆盖不补零。返回模拟计数不等于验证过完整图合法性。

外部占位记录含Kawarada_proxy与UniASA_proxy两种标识，分别按公开在生成器中的Bernoulli召回、误检参数生成逐文档计数。参数不是从原论文估计，也未实现其解码器和任务转换；表4-10不能用于引用作者性能、判断真实公平性或决定实际系统排名。

object_memberships.json保存684个文档种子记录，每项含金标和四格关系对象集合。补全过程约束全部既有关系计数，并匹配T1到组合的恢复／损失与FP变化总量；未对原始计数追认真实对象身份。各关系键中的坐标、类型和端点为程序构造，只支持关系集合代数，不代表完整预测图或真实原文案例。synthetic_object_cases.json按固定类别与文档顺序选取示例，全部清单与未命中项仍保留。

这四组材料使模拟结果章节具备可检查的输入、记录、分母和结论，但不能关闭真实研究证据缺口。正式替换时须更新全套结果与结论，并保留本版及其生成假设作为独立存档。
'''
# Preserve formula and historical identities exactly.
s=s.replace('在这一设定下，UniASA式占位关系F1为68.52和65.51，高于T1＋BR-J的66.56和61.96；Kawarada式占位则为64.80和60.79。由此，内部受控增量不自动等于对领域系统的全面领先。本稿将贡献限定为增强监督与结构恢复的组织及其条件性作用，不用内部消融代替外部定位，也不据占位分数宣称超过或落后于原作者方法。','在这一设定下，UniASA式占位的关系F1高于T1＋BR-J，Kawarada式占位略低。内部受控增量不自动等于领域全面领先，本稿据此限定贡献的表述范围；占位分数不能用于评价原作者方法。')
s=s.replace('与表3-6的同骨干损失消融不同，此处是系统层面的比较示范；骨干、额外数据及输出转换没有在模拟中真实实现，不能进一步解释差异来源。附录G保留两条正式接入路线，后续实测必须分别报告原配置复核与共同任务比较。','这是系统比较示范，与表3-6的同骨干损失消融口径不同。模拟未实现外部骨干、额外数据和任务转换，不能解释差异来源；正式比较须按附录G完成原配置复核与共同任务评价。')
s=s.replace('新增预算情景将共同准备、求解和回退放入同一逐文档时限。它复用80／148篇模拟文档的金标与已存逐文档终态计数，再由声明的规模和成本函数决定在时限内完成的比例；不调用实际ILP。分组使用预设规模排序的三等分，用于情景分层，不能充作训练侧实测切点。两种方法使用相同候选规模、准备成本和预检失败文档，局部累计预算与全局净预算的区别仍然存在。','新增情景将准备、求解和回退纳入逐文档时限，复用80／148篇模拟文档的金标与终态计数，由声明的成本函数决定完成比例，不调用实际ILP。规模排序三等分仅作情景分层。两种方法共用候选规模、准备成本和失败文档，局部累计预算与全局净预算的差别仍然存在。')
s=s.replace('准备P95秒|预检失败','完整准备估计P95秒|预检失败')
s=s.replace('表中准备P95从这些逐文档模拟耗时计算。','表中P95按全部文档的完整准备估计计算；预检在枚举后进行，失败文档不再评分，其实际到达的模拟耗时计入表4-12。')
s=s.replace('图4-5 预算变化下的整体表现与大规模边界（新增模拟情景）','图4-5 预算变化下的整体表现与大规模边界（新增模拟情景）\n\n图中误差棒为三个模拟种子的样本标准差；两个面板采用相同坐标范围。')
number_map={'3':'3','4':'6','5':'7','6':'4','7':'5'}
s=re.sub(r'表5-([3-7])(?!\d)',lambda m:'表5-'+number_map[m.group(1)],s)
s=s.replace('这一补全与原主表严格相容，却不是唯一相容的对象分布。','这一补全与原主表的未分组计数相容，却不是唯一相容的对象分布。它未约束类型、标签及源成员数分组，不能与表5-7的旧分组情景作逐对象对齐。')
s=s.replace('补全过程约束全部既有关系计数，并匹配T1到组合的恢复／损失与FP变化总量；未对原始计数追认真实对象身份。','补全过程约束既有未分组关系计数，并匹配T1到组合的恢复／损失与FP变化总量；不约束类型、标签及源成员数分组，不对原始计数追认真实对象身份。')
changes.append({'reason':'Sequential chapter 5 numbering and explicit full-preparation/figure uncertainty scope','chapter5_number_map':number_map})
assert re.findall(r'\$\$(.*?)\$\$',old,re.S)==re.findall(r'\$\$(.*?)\$\$',s,re.S)
assert old[old.index('# 附录E'):old.index('# 附录F')]==s[s.index('# 附录E'):s.index('# 附录F')]
(R/'report_1010_v4_full.md').write_text(s)
(W/'source.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='1010-v3',tofile='1010-v4')))
(W/'writing_audit.json').write_text(json.dumps({'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'changes':changes,'old_chars':len(old),'new_chars':len(s),'real_model_runs':0,'result_allocation':[{'item':'augmentation variation and coverage','function':'necessary_support and qualification','destination':'3.6.6; assumptions H.6'},{'item':'external placeholders including stronger competitor','function':'qualification','destination':'4.6.7; formal compatibility G'},{'item':'budget and size boundary','function':'heterogeneity changing local adoption','destination':'4.6.8; full scenario records'},{'item':'overlap and damage','function':'core synthesis within assigned memberships','destination':'5.2; H.4 and H.6'}],'statistics_location':'Primary tables contain estimates; one paired interval at each decisive budget interpretation; full groups and intervals in supplement_results.json; no multiplicity-wide significance claim.'},ensure_ascii=False,indent=2)+'\n')
print('Composed v4',len(changes),'anchored edits',len(s),'characters')
