"""Compose a versioned manuscript from frozen evidence, preserving v9."""
from pathlib import Path
import hashlib,json,re
W=Path(__file__).resolve().parent;R=W.parent;E=R/'research_1011_v10'
read=lambda p:json.loads(Path(p).read_text())
source=(R/'report_1011_v9_full.md').read_text();text=source
assert hashlib.sha256(source.encode()).hexdigest()=='57eae9295efecff9ea49e6c14486652b154f54b8ab937a84191c1f5738651a5a'
old=read(R/'research_1011_luna_expansion_analysis/combined_metrics.json')
new=read(E/'new_corpora/results/evaluation_001/metrics.json')
paired=read(E/'cdcp_scoring/results/evaluation_001/metrics.json')
cd=paired['aggregate']['cdcp'];aa=old['aggregate']['aaec'];cc=old['aggregate']['cdcp']
changes={'source_version':'1011-v9','output_version':'1011-v10','global':[['1011-v9','1011-v10']],'text_replacements':[],'insertions':[],'section_replacements':[],'sections_before':[],'heading_renames':[],'references':[]}
def replace(a,b):
    global text
    assert text.count(a)==1,(a[:80],text.count(a))
    text=text.replace(a,b);changes['text_replacements'].append({'old':a,'new':b})
def para_start(s):
    found=[p for p in text.split('\n\n') if p.startswith(s)]
    assert len(found)==1,(s,len(found));return found[0]
def insert_after(a,b):
    global text
    assert text.count(a)==1,a[:80]
    text=text.replace(a,a+'\n\n'+b);changes['insertions'].append({'anchor':a,'paragraphs':[b]})
def paragraph(s):return {'type':'paragraph','text':s}
def heading(s):return {'type':'heading','level':2,'text':s}
def table(cap,headers,rows,widths,split=None):return {'type':'table','caption':cap,'headers':headers,'rows':[[str(x) for x in r] for r in rows],'widths':widths,'split':split}
def blocks_md(blocks):
    out=[]
    for b in blocks:
        if b['type']=='paragraph':out.append(b['text'])
        elif b['type']=='heading':out.append('### '+b['text'])
        else:out.extend([b['caption'],'\n'.join(['|'+'|'.join(b['headers'])+'|','|'+'|'.join([':---']*len(b['headers']))+'|']+['|'+'|'.join(r)+'|' for r in b['rows']])])
    return '\n\n'.join(out)+'\n\n'
def f(agg,method,axis):return f"{agg['metrics'][method][axis]['F1']*100:.2f}"
def count(agg,method,axis):return '／'.join(str(agg['metrics'][method][axis][k]) for k in ['TP','FP','FN'])
def status_text(agg,method):
    outcomes=agg['relation_outcomes'][method]
    return f"{outcomes.get('improvement',0)}篇提高、{outcomes.get('harm',0)}篇下降、{outcomes.get('unchanged',0)}篇不变"

replace('附录D.2—D.3保留既存CPU诊断，4.6.7及D.7—D.9另报告16篇训练侧文档上的Luna真实预测与轻量修正；该试验不替代训练方法及完整系统的受控实验。附录E保留前期存档。',
'附录D.2—D.3保留既存CPU诊断；4.6.7及D.7—D.12分别报告148篇Luna探索性扩样、64篇新语料预测及另32篇CDCP评分对照。它们采用轻量实现，不替代训练方法与完整系统的受控实验。附录E保留前期存档。')
brief_cd=f"另在32篇未用于此前诊断的CDCP文档上固定候选、初始图及预算，原评分与原生说明下显式评分的BRJ-lite关系F1分别为{f(cd,'sparse__BRJ-lite','R')}与{f(cd,'dense_native__BRJ-lite','R')}，均低于共同初始图的{f(cd,'MCR-only','R')}。"
replace(para_start('主实验仍以AAEC与CDCP规模的假设计数演示比较口径：'),
'主实验仍以明确假设计数演示训练和完整系统的比较口径。独立Luna轻量试验扩展至AAEC 32篇、CDCP 116篇：AAEC完整关系F1由0升至1.44，出现生成候选中遗漏前提补入后的关系恢复；CDCP由1.54降至0，暴露候选覆盖不足和代理评分误改。新增ArgUNSC与CasiMedicos-Arg各32篇用于检查不同原生标注下的流程表现。'+brief_cd+'这些实际输出使候选覆盖、评分与结构执行的限制可以逐项核查，但尚未验证训练侧监督保持、集合动作的独立增量、局部相对全局的采用价值或两阶段互补性。')
replace(para_start('The main experimental comparisons still use explicitly assumed counts'),
'The main comparisons use explicitly assumed counts to illustrate the evaluation of training and the full system. A separate Luna pilot covers 32 AAEC and 116 CDCP documents. Strict complete-relation F1 increases from 0 to 1.44 on AAEC, with recorded recovery after a missing premise from the generated candidate pool is inserted, but decreases from 1.54 to 0 on CDCP. Candidate coverage and erroneous proxy scores limit repair. Two further pilots use 32 documents each from ArgUNSC and CasiMedicos-Arg under their native annotations. On another 32 CDCP documents, predictions, candidates, initial graphs, and budgets are held fixed: BRJ-lite obtains relation F1 scores of '+f(cd,'sparse__BRJ-lite','R')+' with the original scoring protocol and '+f(cd,'dense_native__BRJ-lite','R')+' with native-label guidance and explicit object scores, both below the initial graph score of '+f(cd,'MCR-only','R')+'. These outputs support traceable analysis of candidate, scoring, and execution limitations. They do not yet validate supervision preservation, the independent value of set-level actions, local versus global solving, or complementarity between training and inference.')
replace('既存CPU诊断与16篇Luna试验已提供有限观察（D.3及4.6.7），但模型和候选配置均不等同于正式系统，不能据此建立目标系统的问题发生率；完整诊断方案见附录H.1。',
'既存CPU诊断、Luna扩样及新增原生语料试验已记录端点恢复、标签混淆、候选缺失和评分误删（D.3及4.6.7）。这些观察支持检验所针对的问题，但其模型和候选配置与正式系统不同，不能替代目标系统的问题发生率；完整诊断方案见H.1。')
replace('4.6.7进一步给出Luna真实输出的端点恢复及失败轨迹，但小样本、简化候选和未校准评分仍限制方法归因，正式目标模型的完整诊断按附录H.1执行。',
'4.6.7进一步给出生成候选中的组件补入、完整关系恢复及失败轨迹，并在固定候选和初始图上检验评分输入的调整。简化候选及未校准评分仍限制方法归因，正式目标模型诊断按H.1执行。')
replace('4.6.1—4.6.6的主比较与图表使用估算情景；4.6.7单列已执行的Luna小样本案例。两者不共用实验身份、分母或成本口径，正式目标模型的求解、误差与延迟诊断仍按附录H完成。',
'4.6.1—4.6.6保留估算情景的主比较；4.6.7单列实际Luna预测、轻量修正和评分对照。二者具有独立的运行身份、分母与成本口径。正式目标模型的完整比较仍按附录H完成。')
insert_after(para_start('关系池枚举当前没有边的有向槽位，但独立裁剪不保证'),
'不同语料的原生约束分别登记。ArgUNSC与CasiMedicos-Arg只允许单源二元关系；CDCP保留原生完整源集合及连续性要求。多个前提分别支持同一目标时，二元语料使用多条关系，不将其合并为超边；也不把CDCP的联合源范围拆成独立二元边。关系标签或组件类型同名不意味着标注准则相同，评分提示与严格评价均使用对应语料的定义（A.3及D.11）。')
replace('评分失败不默认为零概率，而是按预先声明的失败策略拒绝相关提议并记录。',
'评分接口还须区分低置信度与未取得评分。对缺失、非有限或显式未评估的值，保留缺失状态；只有拟删除或加入的组件，以及经最小合法化扩域后的事务关系空间均有有效分数，才评估该提议。事务外未变对象在差分中相消，不以任意默认值参与变化对象的接受判断。该约束补充输入完整性检查，不改变固定效用、依赖闭合及接受门；启发式模型给出数值也不等于其正确性已被校准。D.12以既定候选开展有限对照。')

main=[paragraph('实际试验分为三个独立部分：AAEC 32篇与CDCP 116篇的探索性扩样；ArgUNSC与CasiMedicos-Arg各32篇的固定规模试验；另32篇CDCP的配对评分对照。各部分均请求gpt-5.6-luna／low，使用同一回答中的g0、g1构造有限候选，由新上下文任务评分，再运行BRJ-lite及RelationOnly。BRJ-lite保留依赖闭合、分项接受门和编辑预算，未训练本文的生成骨干或对象评分器，因此不替代表4-3的完整BR-J。原始记录、失败分母及协议差异见D.7—D.12。')]
rows=[]
for corpus,agg in [('AAEC',aa),('CDCP',cc)]:
    for method in ['MCR-only','RelationOnly','BRJ-lite']:rows.append([corpus,str(agg['documents']),method,f(agg,method,'C'),f(agg,method,'R')])
main.append(table('表4-9 Luna探索性扩样的严格结果（真实运行）',['语料','篇数','配置','组件F1','完整关系F1'],rows,[.75,.55,1.35,.95,1.25]))
main.append(paragraph('表4-9包含原16篇及新增132篇，按全部文档TP、FP、FN汇总计算F1。AAEC有4篇完整关系F1提高，CDCP无提高例；CDCP另有9篇显式失败，全部计入修正结果分母。旧协议的MCR列保留其选中的原始图，即使结构非法，而失败修正计为空输出；两列的差异因而包含初始化失败的影响。扩样曾按是否找到正例决定CDCP后续波次，不据本表估计总体改善概率或作独立测试集推断。'))
main.append(paragraph('AAEC essay051提供了超出标点变体的恢复案例。初始图遗漏“多数图书馆设施可长期使用”这一前提；尝试19从模型生成候选中将其补入，并重建其对“投资图书馆有长期效果”的supports关系。两个端点均为生成候选，完整关系来自有限槽位补充，原g0、g1均未直接含有该正确关系。BRJ-lite关系F1由0升至8.00，RelationOnly仍为0；终态为1 TP、8 FP、15 FN。该例说明组件补入可打开固定组件修正无法使用的关系端点，但缺少单对象和分步对照，尚不能证明集合事务或共同决策的独立优势。'))
main.append(paragraph('AAEC essay001则揭示初选与恢复之间的联系。MCR选择g1后丢失了g0已有的正确对象；尝试1补入目标Claim，尝试7补入前提并恢复supports关系，完整关系F1由0升至12.50，而RelationOnly为0。终态仍含9个关系FP和5个FN。两例均来自全部四个严格正例，另两例essay078、essay085涉及句末标点边界。扩样恢复的55个正确组件中，28个来自标点变体、27个来自生成候选，不能把所有恢复解释成同一种机制。'))
main.append(paragraph('CDCP的负结果给出不同的限制。冻结池仅命中22／200条完整金标关系，19条多源金标关系均未入池；已入池的22条中有19条按原评分规约取得0.05。旧116篇的485个初始组件中，178个完整命中、74个跨度正确但类型错误，其中value→fact为35个、testimony→fact为14个；其余233个没有精确金标跨度对应。该分解提示原生类型语义与候选覆盖值得优先检查，但不能把误差全部归因于提示。01057中，正确reason关系因0.05分被删除，关系F1从33.33降至0，RelationOnly也发生同一损失；合法提交与代理增分不能替代真实正确性。'))

rows=[]
for corpus,label in [('argunsc','ArgUNSC'),('casimedicos','CasiMedicos-Arg')]:
    agg=new['aggregate'][corpus]
    for key,label2 in [('MCR-only','MCR-only'),('sparse__RelationOnly','RelationOnly'),('sparse__BRJ-lite','BRJ-lite')]:rows.append([label,label2,f(agg,key,'C'),f(agg,key,'R')])
main.append(table('表4-10 新增原生语料的固定样本结果（真实运行）',['语料','配置','组件F1','完整关系F1'],rows,[1.6,1.25,1,1.3]))
for corpus,label in [('argunsc','ArgUNSC'),('casimedicos','CasiMedicos-Arg')]:
    agg=new['aggregate'][corpus];cov=agg['coverage']
    main.append(paragraph(f"{label}保留全部32篇，64个候选图中{agg['parsed_graphs']}个通过解析、{agg['valid_graphs']}个满足实现的结构检查，{agg['initial_failures']}篇初始化失败。金标共有{cov['C_gold']}个组件和{cov['R_gold']}条完整关系，冻结池分别命中{cov['C_hits']}和{cov['R_hits']}个；按逐文档关系F1计，BRJ-lite表现为{status_text(agg,'sparse__BRJ-lite')}。失败输出计为空预测，金标保持在分母；格式遵循、候选覆盖和修正变化分别解释，不能从成功子集外推整个语料。"))
main.append(paragraph('CDCP配对试验采用32篇未进入前述审计集合的官方训练文档。两种评分方案固定相同生成结果、候选池、原评分MCR选择的初始图和全部预算，并分别运行BRJ-lite与RelationOnly。“原生显式”方案同时加强fact／testimony／value／policy／reference及reason／evidence的原生说明，并要求每个候选显式给分或标记未知。它是两个输入因素的组合干预，不能单独归因于标签说明或输出格式。'))
rows=[['共同初始','MCR-only',f(cd,'MCR-only','C'),f(cd,'MCR-only','R')]]
for cond,label in [('sparse','原评分'),('dense_native','原生显式')]:
    for mode in ['RelationOnly','BRJ-lite']:rows.append([label,mode,f(cd,cond+'__'+mode,'C'),f(cd,cond+'__'+mode,'R')])
main.append(table('表4-11 CDCP相同候选与初始图下的评分对照（真实运行）',['评分方案','修正策略','组件F1','完整关系F1'],rows,[1.2,1.35,1,1.3]))
dc=cd['changes']['dense_native__BRJ-lite']['R'];sc=cd['changes']['sparse__BRJ-lite']['R']
main.append(paragraph(f"原评分BRJ-lite相对共同初始图恢复{sc['TP_recovered']}条真关系、损失{sc['TP_lost']}条，新增／移除错误关系为{sc['FP_added']}／{sc['FP_removed']}；原生显式方案对应{dc['TP_recovered']}、{dc['TP_lost']}及{dc['FP_added']}／{dc['FP_removed']}。两方案复用同一批通过检查的初始图，未重新挑选更有利初始图。分数改变后修正路径也可能改变，因此需同时看真阳性保留、误报和RelationOnly结果，不能仅以接受次数或代理效用判断改进。"))
main.append(paragraph('CDCP 00846提供原生显式评分下的严格正例。原文以“消费者未必知道债权人及其联系方式”作为“通知应列明债权人的地址和电话”的reason；两端点已在共同初始图中，该完整关系只在补充槽位中。其分数由原评分的0.05变为0.75，首次关系提议即将其加入，关系F1由0升至18.18，终态为1 TP、3 FP、6 FN，组件未变化。RelationOnly恢复了同一条关系并取得相同终态，因此该例支持评分与候选关系重建的作用，不能单独支持组件集合替换的增量。'))
gain=cd['metrics']['dense_native__BRJ-lite']['R']['F1']-cd['metrics']['sparse__BRJ-lite']['R']['F1']
main.append(paragraph(('本次原生显式评分的严格关系F1高于原评分，表明在这批固定输入上评分接口的组合调整有所改善；但它仍低于共同初始图的3.33，且未保住原有两条真关系，尚不能作为总体修正有效的证据。' if gain>1e-10 else '本次原生显式评分未取得高于原评分的严格关系F1，不能将接口完整性改进写成任务效果提升。')+'它仍不能补回池外边界、原生类型或完整源组合。方法层面保留原生任务定义和评分缺失检查，研究结论限定于实际发生的对象变化；完整候选构造、训练评分器与局部／全局比较仍须另行验证。'))
start='#### 4.6.7 案例分析\n\n';end='### 4.7 本章小结';a=text.index(start)+len(start);b=text.index(end,a)
changes['section_replacements'].append({'start':'4.6.7 案例分析','end':'4.7 本章小结','old_markdown':text[a:b],'blocks':main});text=text[:a]+blocks_md(main)+text[b:]

# Appendix construction and synchronized conclusions are appended below.
appendix=[heading('D.10 探索性扩样与对象诊断')]
appendix.append(paragraph('原16篇记录之后，先按相同长度分层和冻结哈希顺序扩为每语料32篇；随后仅对尚无严格关系F1正例的CDCP，每层再取4篇、每波至多16篇，直至用尽116个唯一训练侧审计文本。最终AAEC 32篇、CDCP 116篇；原16篇按字节复用，新增37项预测或评分模型任务，任务数不等同于底层API调用次数。这是已登记停止规则的探索性案例搜索，不能按独立固定样本试验解释。'))
rows=[]
for corpus,agg in [('AAEC',aa),('CDCP',cc)]:
    for method in ['MCR-only','RelationOnly','BRJ-lite']:rows.append([corpus,method,count(agg,method,'C'),count(agg,method,'R')])
appendix.append(table('表D-9 探索性扩样的完整对象计数（真实运行）',['语料','配置','组件TP／FP／FN','关系TP／FP／FN'],rows,[.7,1.3,1.65,1.7]))
appendix.append(paragraph('严格键保留原生字符边界和组件类型；关系再要求完整源集合、目标、方向和标签同时匹配。AAEC金标470个组件、295条关系，池中命中102个组件、7条完整关系；CDCP对应723、200及191、22。已入池正确关系中，AAEC 3条、CDCP 19条取原规约的缺省0.05；这说明实际赋值，不证明未覆写对象从未被模型考虑。原评分本就要求检查全部候选，数值稀疏不能直接等同于心理意义上的未评估。'))
appendix.append(paragraph('AAEC的4个严格正例为essay001、essay051、essay078、essay085，全部列入外部核验册。CDCP的9个失败文档为00404、00430、00728、00867、00881、01118、01150、01288、01292，原因涉及非法类型、重叠或非连续源范围。另22篇满足关系FP减少、TP不减少且组件F1不下降的事后条件；这是误报抑制描述，不参与停止规则，也不称为关系F1提高。00312中FP由1降至0、组件F1保持50.00，RelationOnly得到相同结果，因此它不构成联合修正独有收益。'))
appendix.append(paragraph('148篇冻结输出已独立复算，296个文档策略记录完成一次本地重放，终态对象或显式失败均一致，但6组接受尝试序列不同。差异保留在重放记录中，不覆盖原输出；可能涉及集合遍历的浮点累加及近似并列次序，尚未隔离确认单一原因。新增固定规模试验将效用求和顺序固定为规范ID顺序，公式和接受阈值不变；该实现调整不追溯改写旧结果。'))

appendix.append(heading('D.11 新增语料的来源与固定试验'))
appendix.append(paragraph('新增检索截至2026年10月11日，优先选择同时提供原文、组件边界、原生类型及有向关系的作者发布语料。ArgUNSC于2025年发布，覆盖144篇安理会发言，含claim／premise和support／attack[50]；CasiMedicos-Arg于2024年发布，以医生解释的病例问答为对象，含Claim／Premise和Support／Attack[51]。前者的多个前提以分别指向主张的二元关系表达；后者允许Claim支持Claim，一般医学知识仍标Claim，病例特定观察才标Premise。本试验仅使用后者的英文版本，未将同一病例的四种语言当作独立样本。'))
appendix.append(paragraph('ArgUNSC使用作者仓库的组件级CSV快照，按Sentence_ID拼接原句，组件必须完整逐字匹配并在来源句内开始；跨句组件允许延伸到后句。base.csv的Premises字段与独立关系对文件校对：发布快照中有3060条正关系行，去重为3009条，与组件表的关系集合相同；论文的关系总数为2973，二者没有强行对齐。两个文档存在重复组件ID或重叠，整篇排除；其余142篇中再排除22篇超过8000字符的文档，得到120篇合格源文档。'))
appendix.append(paragraph('CasiMedicos-Arg固定Hugging Face revision 54a07ccf2993afc42a368e04682125b6f7b13be4，读取原始英文有序token／BIO与relations文件。各句内以单空格、句间以换行重建文本，Claim／Premise由BIO还原，其他医学实体和Marker不改写成论辩组件。关系端点只允许对完整组件作唯一匹配，比较时统一NFKC、空白和末尾 .,:;!?；不作编辑距离或语义补配，任何未映射端点使整篇不进入本次严格试验。'))
appendix.append(paragraph('论文报告558个标注病例；所用快照的三划分共622行，其中69行缺少token标注，剩余553行，不能直接沿用论文分母。官方test的125行中117行有token标注，93行可完整映射组件和全部关系；本次只从这93行抽样。排除记录先于预测冻结，故它限定了可转换子集的解释范围；不能把该子集成绩冒充官方完整测试集成绩。英文材料源于西班牙文病例，经翻译与人工修订，这也是其文本条件的一部分。'))
appendix.append(table('表D-10 新语料转换与抽样范围',['项目','ArgUNSC','CasiMedicos-Arg英文'],[['所用发布文档／行','144','test 125'],['完整可转换','142','test 93'],['长度限制后合格','120','93'],['固定样本','32','32'],['原生发布划分','本次发布无官方划分','官方test子集'],['字符构造','原句单空格连接','token单空格与句间换行']],[1.45,1.35,1.8]))
appendix.append(paragraph('两套语料分别按token长度四分位分层，在层内按SHA256(V10-LUNA-FIXED32|语料|原文)排序各取8篇，预测前保存完整顺序、源文件哈希、盲输入和金标快照。各8篇一个预测任务，每篇生成两个图；关系为多源时不拆平来挽救二元语料的非法输出。全程不按效果追加文档或重试格式失败。ArgUNSC、CasiMedicos-Arg和新CDCP预测共12项模型任务，盲评分共31项，合计43项；实际模型快照、温度、随机种子及token用量未由调度工具暴露。'))
appendix.append(paragraph('新试验的构造器只在两张成功解析图给出的类型范围内保留跨度，补充去句末标点变体；二元槽位按不重叠端点枚举，CDCP多源槽位仅来自生成图及其端点变体。4096是构造预检的槽位上限，不是论文完整候选方案的等价实现。所有新文档采用逐文档累计5秒、每MILP调用最多0.25秒的求解额度，其余128次尝试、12次接受及24／96编辑上限沿用旧试验；效用求和次序固定。'))
appendix.append(paragraph('ArgUNSC 64个图中6个因多源关系未通过二元解析；CasiMedicos-Arg为35个，另有3个已解析图违反结构检查。错误记录和全部文档保持在评价分母。MCR依原分数排名选图，未因为已知金标而换成其他候选；初始化失败时本次MCR、BRJ-lite及RelationOnly均按空预测计数。该规则与D.10保留原始MCR图的历史口径不同，两个试验不合并计算成绩。'))
for corpus,label in [('argunsc','ArgUNSC'),('casimedicos','CasiMedicos-Arg')]:
    agg=new['aggregate'][corpus]
    append=agg['changes']['sparse__BRJ-lite']
    appendix.append(paragraph(f"{label}的共同初始组件／关系TP、FP、FN为{count(agg,'MCR-only','C')}与{count(agg,'MCR-only','R')}；BRJ-lite为{count(agg,'sparse__BRJ-lite','C')}与{count(agg,'sparse__BRJ-lite','R')}。关系恢复／损失TP为{append['R']['TP_recovered']}／{append['R']['TP_lost']}，新增／移除FP为{append['R']['FP_added']}／{append['R']['FP_removed']}。每篇严格计数、格式失败和候选覆盖保存于独立评价文件。"))

appendix.append(heading('D.12 CDCP原生评分接口的配对检查'))
appendix.append(paragraph('CDCP按可评价性区分类型：fact是可依陈述当时的证据核验、且不依赖个人经历的命题，未来预测未必为fact；testimony表达个人状态或经历；value为评价，policy为具体行动建议，reference标记外部证据来源。reason给出理由，evidence提供判断目标真假的根据，其来源在原标注模型中与testimony或reference相关[3]。本次将这些区别写入评分说明，未把它们新增为硬类型掩码，也未将全部事实性语句自动当成evidence。'))
appendix.append(paragraph('新增32篇仅来自官方训练划分，排除前期整个CDCP审计文本集合，因此不与D.10的116篇重叠。抽样与预测同D.11；候选、MCR初始选择、求解器、队列生成规则和预算在两条件间完全相同。原评分仍使用低默认值0.05和显式覆写；原生显式方案对所有组件及关系ID输出[0,1]数值或null，不允许缺键。null保持未知，涉及未知变化组件或闭合域关系的提议被拒绝；未变化对象的数值在差分中抵消。'))
cov=cd['coverage'];sd=cd['score_diagnostics']
appendix.append(paragraph(f"本批金标包含{cov['C_gold']}个组件、{cov['R_gold']}条完整关系，有限池覆盖{cov['C_hits']}个组件、{cov['R_hits']}条完整关系；{cov['R_multisource_gold']}条多源金标关系中，池内命中{cov['R_multisource_in_pool']}条。该上游范围在两条件间不变；调整评分不能生成缺失的类型、跨度或源集合。两条件的原生图解析相同，64个图全部解析成功，63个满足实现的结构检查。"))
appendix.append(table('表D-11 CDCP候选评分的覆盖与金标事后诊断',['指标','原评分','原生显式'],[['组件候选数',cov['C_candidates'],cov['C_candidates']],['关系候选数',cov['R_candidates'],cov['R_candidates']],['关系取默认0.05',sd['sparse_default_R'],'无默认'],['显式未知组件／关系','无此字段',f"{sd['dense_unknown_C']}／{sd['dense_unknown_R']}"],['池内正确关系得分≥0.5',sd['sparse_positive_gold_R'],sd['dense_positive_gold_R']],['池内正确关系取默认分',sd['sparse_default_gold_R'],'无默认']],[2.6,1.1,1.2]))
appendix.append(paragraph('表D-11的显式覆盖只证明字段齐备及数值有效，不能独立证明模型逐一完成了可靠语义判断；金标只用于冻结后的诊断。评分与预测为同型号模型的不同上下文，误差独立性未获证明。原生说明和输出覆盖同时变化，故该对照检验组合输入调整，不区分两个因素各自的效应。即使关系F1提高，也不等于分数已校准或完整BR-J有效。'))
appendix.append(paragraph('本地接口检查覆盖两套新语料的二元元数、未知变化组件、未知关联关系、最小合法化扩域中的未知同槽标签，以及不相关未知对象不应阻断已评分提议。原始源文件、候选、分数和执行输入在读入评价标签前冻结；独立检查再从发布CSV／BIO／关系JSONL及CDCP原压缩包重建金标，复核事务外关系、接受门、累计预算与终态。构造检查只证明这些边界分支按规约执行，不替代语料上的收益。'))
cost_rows=[]
for result in [new,paired]:
    for key,cost in result['costs'].items():
        corpus,cond,mode=key.split('__')
        label={'argunsc':'ArgUNSC','casimedicos':'CasiMedicos-Arg','cdcp':'CDCP'}[corpus]+' '+{'sparse':'原评分','dense_native':'原生显式'}[cond]
        cost_rows.append([label,mode,f"{cost['completed']}／{cost['failures']}",f"{cost['wall_seconds']:.4f}",f"{cost['solver_seconds']:.4f}"])
appendix.append(table('表D-12 新增试验的修正阶段实测成本',['语料与评分','策略','完成／失败','墙钟秒','MILP秒'],cost_rows,[1.75,1.2,1.1,.85,.85]))
appendix.append(paragraph('表D-12为每种语料、条件和策略的32篇合计，从固定候选和分数之后开始计时，不含Luna预测、评分、下载或环境准备。它不能解释为端到端延迟或局部相对全局的速度优势；完整逐调用状态保存在运行轨迹。'))
replays={name:read(E/name/'results/replay_001/audit.json') for name in ['new_corpora','cdcp_scoring']}
replay_rows=[x for result in replays.values() for x in result['runs']]
appendix.append(paragraph(f"新增试验的{len(replay_rows)}个文档条件策略记录另作一次冻结分数的本地重放，其中{sum(x['terminal_match'] for x in replay_rows)}个终态或显式失败一致，{sum(x['commit_indices_match'] for x in replay_rows)}个接受尝试序列一致。重放不再调用Luna，也不替换原轨迹；一致性只验证冻结输入后的执行，不代表模型多次抽样结果稳定。"))
anchor='## 附录E 前期数值与协议存档';assert text.count(anchor)==1
text=text.replace(anchor,blocks_md(appendix)+anchor);changes['sections_before'].append({'anchor':'附录E 前期数值与协议存档','blocks':appendix})

replace(para_start('评价围绕RelationOnly、单对象动作和同目标全局求解展开'),
'评价以RelationOnly、单对象和同目标全局求解分别检验组件变化、集合表达与成本。Luna轨迹提供端点补入、关系恢复及评分误改的真实观察，评分对照检验输入质量的作用；有限候选和未校准分数仍限制结论。完整系统与全局比较待执行，预算条件分析见附录H，下一章讨论两阶段对象作用的解释边界。')

ac=aa['changes']['BRJ-lite']['C']
replace('Luna试验还呈现AAEC组件FP净变化为0、实际新增和移除FP却各34个，以及CDCP 00396的错误关系标签替换（4.6.7及D.8）。两类运行共同说明净计数会隐藏对象更替；它们都不是同批训练四格输出，尚不能解释两阶段互补性。',
f"Luna扩样中，AAEC组件FP净增加{ac['FP_added']-ac['FP_removed']}个，实际新增{ac['FP_added']}个、移除{ac['FP_removed']}个；essay001还表现为初选丢失已有正确对象、后续修正又将其恢复（4.6.7及D.10）。这说明恢复增量既受初始选择影响，也可能伴随错误对象更替。上述观察以及D.12的评分对照均只涉及推理阶段，不能代替同批训练四格的对象分析。")
replace('数学构造说明动作和决策边界，人工成绩展示比较口径，Luna小样本则记录了端点重建及评分误删的实际过程；',
'数学构造说明动作和决策边界，人工成绩展示比较口径，Luna试验记录了生成端点补入、完整关系恢复、候选限制及评分误删，并对原生评分输入作了固定样本检查；')
replace(para_start('正文主比较、增强审计判断和设定成本仍为估算情景，训练侧增强、成对学习'),
'正文主比较、增强审计判断和设定成本仍为估算情景。训练侧增强、成对学习、人工语义审核、同目标局部／全局与训练四格比较尚未完成。D.3保留CPU诊断，D.7—D.10报告148篇Luna探索性样本，D.11—D.12另报告64篇新语料与32篇CDCP配对样本，均保留失败与严格计数。实际MILP已在轻量实现中执行，但其生成候选、同型号启发式评分、样本划分和本地运行成本不能代表正式系统。主成绩、模板筛选、预算函数和对象补全分别用于演示评价、指标阅读、条件分析及不可识别性，不与这些真实记录混为同一次实验。')
replace(para_start('本文主比较范围为英文AAEC和CDCP。ORCHID'),
'本文主比较范围仍为英文AAEC和CDCP。补充试验纳入ArgUNSC的安理会发言[50]及CasiMedicos-Arg的英文病例解释[51]，分别保留原生跨度、类型与二元关系。前者的Claim／Premise按论证作用区分，后者将一般医学知识标为Claim、病例特定观察标为Premise；名称相同不意味着可合并标签或分母。ORCHID面向中文辩论的目标无关立场检测和论辩对话摘要[28]，IAM整合多项论辩挖掘任务并使用英文资源[29]。本稿只报告已经完成兼容转换与严格评价的范围，不由单语补充试验推断中文或多语言效果。')
replace('方法配置身份沿用1010-v1-global-review；文稿版本为1011-v9，单独登记，不表示重新运行实验或更改方法配置。',
'正式方法参考配置身份沿用1010-v1-global-review；文稿版本为1011-v10。新增Luna固定规模试验另有运行身份和评分接口调整（D.11—D.12），不追溯改写参考配置或历史输出。')
replace(para_start('真实案例的独立入口为research_1010_v7_luna。'),
'真实试验入口分别为research_1010_v7_luna、research_1011_luna_expanded及其w02—w07分波目录、research_1011_luna_expansion_analysis与research_1011_v10。历史原16篇按字节保留；合并文件逐篇连接源波次。新增目录保存发布文件哈希、转换审计、预先冻结样本、预测与评分提示、候选、输入／输出冻结及逐事务记录。评价与重放文件保存严格计数、原生源核对和差异清单。逐例原文、金标、前后对象及核验入口见配套实测分析记录，不将合并汇总当作新增模型调用。')
insert_after(para_start('AAEC和CDCP的数据使用遵循原始发布条款'),
'ArgUNSC所用作者仓库含MIT许可，CasiMedicos-Arg数据卡标注CC-BY 4.0；本地清单同时保存许可文本、发布版本和文件哈希[50][51]。许可记录用于追踪本次获取条件，正式公开材料仍须保留作者引用及适用归属说明。后者仅用于论辩结构抽取，不作为诊疗建议或医学正确性评价。')
replace('自动生成的文字、理论例子和软件测试不作为人工标注或正式模型实验记录。',
'自动生成的文字、理论例子和软件测试不作为人工标注或正式目标系统实验。本文另将明确请求模型、输入及输出均已冻结的Luna任务作为模型行为记录；其启发式评分未被称为人工审阅、独立专家判断或校准概率。')
replace('D.7—D.9及4.6.7另提供Luna同文档前后案例；样本来自本诊断划分的子集，模型及运行身份分开，不能相加为198篇独立诊断文档。',
'D.7—D.10的148篇Luna样本仍来自本诊断划分，模型及运行身份分开，不能与182篇相加为独立文本总数。D.11—D.12的另96篇使用单独冻结的语料或训练侧文档，亦按各自协议报告。')
replace('后续首先在共同候选中加入仅标点规范化对照，并检验低默认关系分对原真阳性保留的影响；这属于待执行的控制实验，不在当前记录中补填结果。',
'该初始批之后的探索性扩样与固定样本评分检查分别见D.10和D.12；原16篇结果不重算、不回填。仅标点规范化、单对象及分步对照仍未完成。')
replace('4.6.7已按独立Luna试验的固定规则给出改善、受损与不变案例；该试验没有训练四格、分步对照及经事后验证的错误拒绝病例，缺失类别不由推演填补。',
'4.6.7从已冻结的Luna输出给出生成端点补入、评分误删和新语料失败等观察，配套记录列出全部严格正例与按ID排序的代表例。它们没有训练四格、分步对照或经事后验证的错误拒绝病例，缺失类别不由推演填补。')
replace('现有Luna案例已补足轻量推理层面的真实展示，但缺少训练因素及完整对照，不能据此将四格对象分析标为完成。',
'现有Luna扩样、新语料和评分对照已提供轻量推理层面的真实输出，但缺少训练因素及完整对照，不能据此将四格对象分析标为完成。')
for a,b in [('D.7 Luna真实试验的条件与来源','D.7 初始Luna试验的条件与来源'),('D.8 完整对象计数与逐文档结果','D.8 初始批的完整计数与逐文档结果'),('D.9 实际执行与方法解释边界','D.9 初始批的执行与解释边界')]:
    assert text.count('### '+a)==1;text=text.replace('### '+a,'### '+b);changes['heading_renames'].append({'old':a,'new':b})
references=[
{'text':'[50] POIAGANOVA M, STEDE M. From debates to diplomacy: Argument mining across political registers[C]//Proceedings of the 12th Argument Mining Workshop. Vienna: Association for Computational Linguistics, 2025: 205–216. DOI: 10.18653/v1/2025.argmining-1.20.','url':'https://aclanthology.org/2025.argmining-1.20/'},
{'text':'[51] SVIRIDOVA E, YEGINBERGEN A, ESTARRONA A, et al. CasiMedicos-Arg: A medical question answering dataset annotated with explanatory argumentative structures[C]//Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing. Association for Computational Linguistics, 2024: 18463–18475. DOI: 10.18653/v1/2024.emnlp-main.1026.','url':'https://aclanthology.org/2024.emnlp-main.1026/'}]
anchor='## 附录A 数据处理与复现协议';text=text.replace(anchor,'\n\n'.join(ref['text']+' [来源]('+ref['url']+')' for ref in references)+'\n\n'+anchor);changes['references']=references
for a,b in changes['global']:text=text.replace(a,b)
assert not (R/'report_1011_v10_full.md').exists() or hashlib.sha256((R/'report_1011_v10_full.md').read_bytes()).hexdigest()==read(W/'docx_build.json')['source_sha256']
(R/'report_1011_v10_full.md').write_text(text)
(W/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
build=read(R/'_revision_1011_v9/docx_build.json')
build['headings']=[[len(m.group(1))-1,m.group(2)] for m in re.finditer(r'(?m)^(#{2,4}) (.+)$',text)]
removed=set(re.findall(r'(?m)^(表\d+-\d+ .+)$',changes['section_replacements'][0]['old_markdown']))
build['captions']=[c for c in build['captions'] if c not in removed]
for blocks in [main,appendix]:
    build['captions'] += [b['caption'] for b in blocks if b['type']=='table']
build['captions'].sort(key=lambda s:text.index(s))
assert len(build['captions'])==len(set(build['captions']))
build.update(source_sha256=hashlib.sha256(text.encode()).hexdigest(),output=str(R/'report_1011_v10_full.docx'),retained_template_sha256=hashlib.sha256((R/'report_1011_v9_full.docx').read_bytes()).hexdigest(),rendered=False)
(W/'docx_build.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
plan=read(W/'editorial_plan.json')
def main_chars(s):return len(s[s.index('## 第一章'):s.index('## 参考文献')])
plan['word_count_change']={'measure':'Unicode characters including Markdown, not Word word count','full_before':len(source),'full_after':len(text),'chapters_before':main_chars(source),'chapters_after':main_chars(text),'chapter_delta':main_chars(text)-main_chars(source)}
plan['replacement_count']=len(changes['text_replacements']);plan['appendix_sections_added']=3
(W/'editorial_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':'report_1011_v10_full.md','text_replacements':len(changes['text_replacements']),'new_tables':sum(b['type']=='table' for b in main+appendix),'removed_tables':len(removed),'headings':len(build['headings']),'word_count_change':plan['word_count_change']},ensure_ascii=False,indent=2))
