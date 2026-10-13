"""Apply the second review to the simulation edition; all new counts are derived."""
from pathlib import Path
from collections import defaultdict
import json,re,difflib,hashlib
W=Path(__file__).resolve().parent;R=W.parent
old=(R/'report_1009_v3_full.md').read_text(); text=old; edits=[]
def sub(before,after,reason):
    global text
    n=text.count(before); assert n==1,(reason,n,before[:80])
    text=text.replace(before,after);edits.append({'reason':reason,'before':before,'after':after})
text=text.replace('1009-v3','1009-v4').replace('_revision_1009_v3/','_revision_1009_v4/')
text=re.sub(r'表3-([4-8])(?!\d)',lambda m:'表3-'+str(int(m[1])+1),text)
text=re.sub(r'表5-([3-4])(?!\d)',lambda m:'表5-'+str(int(m[1])+1),text)
edits.append({'reason':'新增表3-4、表5-3之前统一后移原表号及全部交叉引用；图和公式编号不变'})
sub('本文将跨语料分析作为适用范围检验，区分多任务训练、单源零样本迁移和目标域校准，不把这些设定合并为一种“泛化”成绩。','本文以两种原生任务检验方法的适用范围，并将附录中的历史跨域结果单独保留。多任务训练、单源零样本迁移和目标域校准具有不同数据条件，不合并为一种“泛化”成绩。','R11：相关工作与本章实际比较范围同步')
sub('训练与推理的组合实验用于分析两项方法的互补性，跨语料实验用于说明适用边界，均不另列为第三项算法创新。','训练与推理的组合实验用于分析两项方法的互补性，两种原生任务的比较用于讨论适用边界，均不另列为第三项算法创新。','R10：贡献限定为两项')
sub('第五章分析两阶段组合、整体成本和跨语料适用性。','第五章分析两阶段组合、整体成本、原生超边与适用范围。','R11：章节导读同步')
sub('第五章跨语料分析采用另行声明的粗粒度映射，该映射不反向改变域内金标。','第五章分别评价两种语料的原生任务，不将域内比较解释为跨域迁移。粗粒度跨域映射仅属于附录E的历史协议，不反向改变本章的原生金标。','R11：修正不存在的第五章粗粒度映射')
sub('生成器只使用训练数据，增强中心选择、提示调整、早停和超参数筛选不使用测试标签。评分器的训练候选由训练集内部三折交叉拟合产生，使每个文档的预测不由已经拟合该文档标签的生成器直接给出。两种训练方案各自产生交叉拟合候选，覆盖其实际错误分布。\n\n开发文档划分为校准部分与策略选择部分，分别用于概率校准及阈值、预算选择。数据不足时采用预先固定的交叉验证安排，并记录每个阶段的数据用途。最终选择冻结后再进行完整测试报告。上述隔离控制数据泄漏；模型误差的关系仍须按2.4节区分。',
'''表2-2的320篇与580篇均为训练侧源文档总数，包含开发用途；独立评价文档分别为80篇与148篇。生成超参数和固定训练轮数在OOF候选生成前冻结。三折交叉拟合在训练侧进行，每折生成器与跨度头均排除持出源文档及其全部变体；T0和T1分别产生候选，覆盖各自错误分布。最终生成模型拟合全部训练侧源文档，独立评价标签不参与训练、提示调整或选择。

评分器使用训练侧OOF记录，并按固定源文档分组进一步划分拟合、校准和策略选择用途。AAEC三部分为256、32、32篇，CDCP为464、58、58篇，组间没有共享原文或变体。校准部分只拟合概率变换，策略部分只选择阈值与预算；这些角色属于同一训练侧总量，不另增加隐含开发集。评分器及规则冻结后，才在独立评价集汇总最终结果。上述隔离针对信息使用路径，不能据此认定生成器与评分器的误差独立。''','R06/R07：明确训练、OOF、校准与策略选择的数据用途')
sub('|材料规模|AAEC训练源320、评价80；CDCP训练源580、评价148|变体和重复文本按源文档共同分组|','|材料规模|AAEC训练侧320、独立评价80；CDCP训练侧580、独立评价148|训练侧含拟合、校准与策略用途；按源文档分组|','R06：规模分母一致')
sub('|评分数据|每语料组件2400、关系4800个完整对象|训练内三折OOF，开发校准与策略选择分开|','|评分评价对象|每语料组件2400、关系4800个完整对象|用于表4-6的固定提案评价，不是全部训练对象数|','R06/R08：评分评价与训练规模区分')
sub('主比较事先确定，多重探索比较另行标识并说明调整方法。只有与实际运行绑定的统计量才能进入效果结论。','核心对比为相同增强集合下成对项的增量，以及BR-J与所定义分步策略的差异；其余消融、中心策略与交互分析用于探索机制。文中的95%区间均为逐比较的边际区间，未作多重比较校正，不提供跨所有表格的同时覆盖保证，也不据此逐项宣称统计显著。','R07/R08/R09：明确统计区间解释与多重比较边界')
sub('充分求解结果与等资源结果分列，超时报告可行解、有效界或gap，运行到时限不等于求得最优。','等资源结果、大预算可行解和已证明最优的结果分别标识；超时报告可行解、有效界或gap。增加时限不等于证明最优。','R08：大预算与全局最优区分')
sub('|等预算通用重写或重生成|相同token或调用资源|专门修正机制的成本效益|解析失败、幻觉跨度及全部成本|','|等额度通用重写或重生成|明确对齐token额度或调用额度|给定额度代理下的修正收益|另报真实时间、解析失败、幻觉跨度及全部成本|','R08：公平性只限明确资源维度')
sub('充分求解的全局效用构成相应局部解的上界；比较须同时报告等时间预算下的可行解、求解间隙及充分求解结果。','已证明最优的全局效用构成相应局部解的上界；若求解未完成，最大化问题的有效求解上界也可用作界，但当前可行解的效用不是该保证。比较分别报告等时间预算下的可行解、求解间隙和最优性状态，不把大预算行自动视为全局最优。','R08：全局域包含与求解证据分离')

ar=json.loads((W/'audit_judgements.json').read_text()); sr=json.loads((W/'scenario_results.json').read_text())
audit=[]
names={'plain':'普通增强','qos':'QOS式','full':'完整方案'}
for ds in ['AAEC','CDCP']:
    for method in names:
        item={'dataset':ds,'method':method}
        for accepted,key in [(True,'accepted'),(False,'rejected')]:
            rows=[x for x in ar['rows'] if x['dataset']==ds and x['method']==method and x['accepted']==accepted]
            assert len(rows)==800
            counts=defaultdict(int)
            for row in rows: counts[row['factor']]+=1
            assert len(counts)==4 and set(counts.values())=={200}
            d=sum(x['drift'] for x in rows); item[key]={'n':len(rows),'drift':d,'stable':len(rows)-d,'rate':100*d/len(rows)}
        audit.append(item)
audit_table='''表3-4 接受与拒绝样本的因素漂移审计

|语料与方法|接受漂移数／800|接受漂移%|拒绝漂移数／800|拒绝漂移%|
|:---|:---:|:---:|:---:|:---:|
'''+''.join(f"|{x['dataset']} {names[x['method']]}|{x['accepted']['drift']}|{x['accepted']['rate']:.2f}|{x['rejected']['drift']}|{x['rejected']['rate']:.2f}|\n" for x in audit)
sub('|语料与方法|内部正|跨边界正|内部NONE|跨边界NONE|平均|','|语料与方法|内部正|跨边界正|内部NONE|跨边界NONE|分层均值|','R07：漂移率采用等层权重')
sub('完整判定集合共16000个因素，原始两路判定一致率为96.31%，Cohen κ为0.902。这些统计描述判定一致性；语义保持还依赖判定准则和裁决质量。拒绝样本中存在标签保持的改写，接受样本中也存在漂移，故自动筛选是质量与覆盖的折中。程序的坐标和引用检查为语义审计提供结构前提，两者不能相互替代。',
audit_table+'''
两表以关系因素为单位，四类因素各占相同样本量，百分比是等层权重的均值，不是按整个生成池构成加权的总体漂移率。完整方案的拒绝层中，AAEC有559／800、CDCP有536／800个因素保持标签。单个稳定因素不代表整个变体应被接受：其他因素、组件角色或质量条件仍可能不合格。因此这些数值不能直接解释为变体级误拒率；接受层漂移率也不能直接替代变体级筛选精确率。

完整审计还纳入两种过滤消融，共5种方法、2种语料、每组1600个因素，合计16000个。两路因素判定的一致率为96.31%，Cohen κ为0.902，描述的是一致性而非相对于独立金标准的准确率。接受层残余漂移与拒绝层稳定因素共同提示质量和覆盖的取舍；坐标、引用检查只提供结构前提，不能替代这一语义审计。''','R07：补全拒绝审计并限制误拒与可靠性归因')
text=text.replace('等token重生成','等token额度重生成')
sub('重生成与BR-J采用相同总token预算，解析失败与额外调用进入成本，实际调用组织可以不同。','重生成与BR-J对齐总token额度，解析失败与额外调用进入成本，实际调用组织可以不同。这里的token合计包含各模型输入与输出，是额度代理；输入读取、评分和自回归解码的单位代价不同，等token不表示等GPU时间、等能耗或等端到端时延，成本结论须同时查看时间列。','R08：不将token相等扩展为算力相等')
sub('“Staffing, transport and safety jointly constrain the schedule.”需要完整三源集合','“Staffing is limited. Buses stop early. Lighting is unsafe.”三条前提共同支持“The library should close early.”','R08：案例完整源成员改为三条完整前提')
sub('AAEC组件交互差为负，表明训练和修正所覆盖的部分错误发生重叠。','AAEC组件交互差为负，与两阶段收益部分重叠相容；仅凭聚合分数不能确认它们修复了哪些相同对象。','R09：负交互不直接证明对象级重叠')
net=[]
for ds in ['AAEC','CDCP']:
    for obj in ['component','relation']:
        item={'dataset':ds,'object':obj}
        for label,a,b in [('training','t1_i0','t0_i0'),('repair_t0','t0_i1','t0_i0'),('repair_t1','t1_i1','t1_i0')]:
            ac=sr['metrics'][ds][a][obj]['counts'];bc=sr['metrics'][ds][b][obj]['counts']
            delta=[sum(x[i] for x in ac)-sum(x[i] for x in bc) for i in range(3)]
            assert delta[0]==-delta[2];item[label]={'tp':delta[0],'fp':delta[1],'fn':delta[2]}
        risk=sr['risk'][ds]['t1_i1'][obj]; assert item['repair_t1']['tp']==risk['recovered']-risk['lost_tp']
        net.append(item)
net_table='''表5-3 四格比较的净错误计数变化

|语料与对象|训练增量 ΔTP／ΔFP|T0修正 ΔTP／ΔFP|T1修正 ΔTP／ΔFP|
|:---|:---:|:---:|:---:|
'''+''.join('|'+x['dataset']+' '+{'component':'组件','relation':'关系'}[x['object']]+'|'+ '|'.join(f"{x[k]['tp']:+d}／{x[k]['fp']:+d}" for k in ['training','repair_t0','repair_t1'])+'|\n' for x in net)
anchor='![联合修正的关系恢复与真阳性损失](_revision_1009_v4/figures/recovery_risk.png)'
sub(anchor,net_table+'''
表5-3分别计算T1＋I0减T0＋I0、T0＋I1减T0＋I0、T1＋I1减T1＋I0，按相同文档与种子累加净计数。金标固定，故每项ΔFN等于−ΔTP。AAEC在T1下修正的关系净TP增加224，小于T0下的248；CDCP相应为187与176，说明更好的训练并不必然同幅度压缩修正空间。T1关系净增量又分别等于289−65与233−46，与表4-7的恢复和损失账本一致。

这些数值是三种子计数之和，不是新增独立文档，也不用于替代先逐种子计算再求均值的表5-1。净计数不能识别训练与推理修复对象的交集；确认对象级互补仍需对齐完整预测键的逐对象轨迹。不同训练条件还改变候选分布并带来评分适配，四格差值据此解释为条件系统增量，不等同于固定评分器下的单因素作用。

'''+anchor,'R09：补齐四格直接净错误计数并核对恢复账本')
sub('对剩余错误的解释遵循候选缺失、动作范围、队列截断和接受门四层。候选不存在时提高评分精度不能补回对象；候选存在而动作不表达所需替换时扩大计算预算也不一定有效；具备可达路径仍可能被错误评分或资源限制阻断。由此，负交互可以与部分错误被训练提前修复相容，正交互也需要结合候选分布和评分适配解释，不能仅由一项差值推断普遍机制。',
'剩余错误先区分组件候选缺失与完整关系槽位缺失，再检查动作能否表达、提议是否进入队列、是否在预算内执行，以及评分和接受门是否通过。若一个错误涉及多种原因，以最早失败层作为互斥主因，其余原因另作附加标记；改变组件后才合法的新关系也须检查是否重新入队。该顺序区分扩大候选、扩大动作与增加算力各自能解决的问题。交互差只提供条件收益变化，不能代替这些逐对象归因。','R08/R09：失败层次区分候选、动作、队列、执行与接受')
sub('### B.5 案例的统一记录格式',
'''#### B.4.3 外层预算与提交的边界判定

表B-1规定调度器的验收语义，与算法4-1、4-2及顺序方法的阶段账本保持一致。它是实现与测试应共同满足的判定表；独立参考函数通过不表示生产调度器已经完成这些分支的验收。

表B-1 提议评估与提交的预算判定

|边界情形|允许动作|账本与返回状态|
|:---|:---|:---|
|最后一次允许尝试得到合格候选|接受、编辑和安全提交资源足够时仍可提交|尝试已计费，不再要求新的尝试名额|
|尝试额度为0，尚未启动新提议|不得评估新提议|保留当前图；已评估候选另按提交条件处理|
|接受额度为0，拟启动新的外层接受|不得提交新的外层提议|已产生的计算消耗不退还|
|累计编辑或安全验证、提交资源不足|不得开始不能完成安全提交的动作|保留最近完整合法图，已耗计算不退还|
|顺序阶段一刚占满接受额度|允许同一外层提议的配套阶段二，仍检查编辑和实际资源|不增加外层接受数；阶段二失败保留阶段一|

验证日志分别给出评估前余额、评估消耗、提交前余额和提交结果，使“不能继续评估”与“不能提交已评估结果”可独立核对。阶段二属于已有外层接受；该例外不能被用于启动另一个提议。

### B.5 案例的统一记录格式''','S01/R06：增加规范预算边界判定表，不冒充生产测试')
sub('配置身份为1009-v4-simulation-s01-s02。','配置身份为1009-v4-simulation-review。','配置身份同步')
sub('最终模型只在规定训练数据上重训，测试集不参与上述过程。','最终生成器拟合训练侧源文档，评分模型则遵守2.6.1的拟合、校准和策略用途，不将校准或策略标签合并回评分器拟合池。','R06/R08：评分器冻结后不合并开发用途重训')
sub('OOF生成器的训练规模小于最终生成器，候选分布可能发生变化，因此校准部分还需检查最终生成器产生的候选。候选级校准并不直接保证被搜索选中的动作可靠；4.6.4和4.6.5节进一步区分有益、中性和有害修改，检验选择后偏差与多轮误改。','OOF生成器的训练规模小于最终生成器，候选分布可能发生变化。概率变换仅拟合OOF校准记录，不使用已被最终生成器拟合过的文档来冒充独立校准样本。冻结后在独立评价集检查评分偏差，不据其标签重新调参。候选校准不直接保证搜索后动作可靠，4.6.4和4.6.5节进一步分析评分及误改。','R08：最终生成器的已见训练文档不能冒充独立校准')
sub('减少监督漂移提高了数据质量，同时也丢弃一部分标签仍保持的变体；','降低因素漂移有利于监督质量，但拒绝池仍含标签保持的因素；','R07：不从因素级标签外推整变体误拒')
assert text[text.index('## 附录E'):text.index('## 附录F')]==old[old.index('## 附录E'):old.index('## 附录F')]
assert re.findall(r'\$\$(.*?)\$\$',text,re.S)==re.findall(r'\$\$(.*?)\$\$',old,re.S)
assert not re.search(r'(?<![\d.])\d+(?:\.\d+)?%?P%?',text)
assert len(re.findall(r'^表[\dA-F]+-\d+ ',text,re.M))==41
(R/'report_1009_v4_full.md').write_text(text)
(W/'edits.json').write_text(json.dumps(edits,ensure_ascii=False,indent=2)+'\n')
(W/'source.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='report_1009_v3_full.md',tofile='report_1009_v4_full.md')))
derived={'evidence_type':'DERIVED_FROM_EXISTING_SIMULATED_DATA','source_hashes':{n:hashlib.sha256((W/n).read_bytes()).hexdigest() for n in ['audit_judgements.json','scenario_results.json','document_counts.csv']},'audit_rows':audit,'net_error_rows':net,'new_empirical_experiments':0}
(W/'review_derived_tables.json').write_text(json.dumps(derived,ensure_ascii=False,indent=2)+'\n')
print('revised',len(edits),'edits;',len(text),'characters; 41 tables; old data unchanged')
