from pathlib import Path
import json,hashlib,difflib
W=Path(__file__).resolve().parent;R=W.parent
old=(R/'report_1010_v5_full.md').read_text();text=old;changes=[]
def change(before,after,reason):
    global text
    assert text.count(before)==1,(reason,text.count(before))
    changes.append({'before':before,'after':after,'reason':reason})
    text=text.replace(before,after,1)

text=text.replace('1010-v5','1010-v6').replace('_revision_1010_v5/','_revision_1010_v6/')
change('实际运行的权重revision、分词器及环境在2.6节统一记录。','正式运行前将按2.6节登记具体权重revision、分词器及环境；当前骨干名称仅为参考设置。','2.3区分参考骨干与未绑定运行身份')
change('实验采用统一骨干、源文档分组与严格评价，各种方法的变化集中在增强条件、学习目标或修正策略。表2-2固定计算配置和数据规模，全部结果按语料、方法和种子关联，跨章复用相同记录。','比较方案统一骨干、源文档分组与严格评价，方法间仅改变声明的增强条件、学习目标或修正策略。表2-2列出人工情景的参考设置与规模，不构成可执行配置；情景结果按语料、方法和种子关联，跨章复用同一记录。','2.6.2明确配置表是情景参考而非运行验收')
change('表中参数定义比较条件，不由测试结果反向选择。数据、配置、候选、结果和统计身份分别存放；正文只复用统一汇总入口。评价记录采用文档与种子配对，组件和关系分别保留TP、FP、FN，成本保留模型生成、对象评分及求解分项。附录A列出字段与复算关系。','正式运行前须冻结数据与折清单、各模型及分词器版本、生成与审核提示、采样参数、损失系数、校准方式、求解器和资源上限。当前增强模型、语义验证器、文本编码器、跨度头及评分器尚未绑定具体检查点；$\\rho$、$\\lambda_{sup}$、$\\lambda_C$、$\\lambda_R$的取值及选择方案也未登记。配套配置单列未绑定字段，表中参考值不代替实测环境。运行后按附录A关联配置、候选与逐文档计数，分开保存生成、评分和求解成本。','2.6.2集中交代缺少的模型身份系数及运行字段')
change('本节说明前期专项建模与新增学习目标的接口。模型采用 Qwen2.5-7B-Instruct，','本节说明前期专项建模与新增学习目标的接口。参考骨干为 Qwen2.5-7B-Instruct，','3.2.1避免把参考骨干写成已运行')
change('梯度累积的最后一个不足批次按实际源文档数归一化；系数在开发阶段确定，测试集不参与选择。','梯度累积的最后一个不足批次按实际源文档数归一化。正式运行须在训练侧预先登记系数候选范围与选择规则，经开发选择后冻结；本版未绑定的系数见2.6.2节，测试集不参与选择。','3.4.3纠正损失系数已确定的时态')
change('27    按源文档等权取训练批次；读取原文及其已接受视图','27    按源文档等频取训练批次；读取原文及其已接受视图','算法3-1澄清采样频次与损失权重的区别')
change('|T-A T0与普通增强|相同基础损失，不增加新头|一般文本增量的作用|','|T-A T0与普通增强|相同基础损失，不增加新头|普通增强的整体作用|','表3-2不把普通增强差值单归因于新文本')
change('本轮访问未取得可检查的仓库内容','前次资料核查未取得可检查的仓库内容','G.2保留旧检索记录的时间身份')
change('AASP、ARGUS的本轮记录以原文方法为限','AASP、ARGUS的既有记录以原文方法为限','G.2不将既有文献核对冒充本轮重新核验')

# Author-owned choices are intentionally not applied until explicitly answered.
decision_file=W/'author_decisions.json'
if decision_file.exists():
    decisions=json.loads(decision_file.read_text())
else:
    decisions={'comparison_priority':'PENDING','cost_scope':'PENDING'}

if decisions['comparison_priority']=='A1':
    change('训练侧固定基础损失比较数据构造整体，固定增强集合比较辅助监督与成对项；推理侧以固定组件、单对象动作和同目标全局求解分别检验组件可变性、集合表达与资源取舍。','训练侧以数据构造整体及同数据学习增量为关键比较，分别固定基础损失或增强集合；推理侧以RelationOnly和单对象动作检验组件可变性与集合表达，以同目标全局求解判断资源取舍，分步策略补充检验共同决策。','A1 中文摘要统一关键比较职责')
    change('Training comparisons separate the overall data-construction effect under a fixed base loss from auxiliary supervision and paired learning on the same augmented set. Inference comparisons use fixed-component repair, single-object actions and same-objective global optimization to examine component changes, set-level expressiveness and resource tradeoffs.','Key training comparisons examine the overall data-construction effect under a fixed base loss and learning increments on the same augmented set. For inference, RelationOnly and single-object controls test component changes and set-level expressiveness, while same-objective global optimization tests resource tradeoffs. A sequential strategy provides a supplementary comparison of joint decision-making.','A1 英文摘要同步对照职责')
    change('局部与全局ILP首先比较相同逐文档总求解预算，另以相同端到端时限评价部署条件；两种预算分别命名。软件、线程、缓存条件和共同准备开销保持一致，大预算结果不自动视为最优。核心比较包括相同增强集合上的成对项增量、BR-J与组件优先分步策略，以及BR-J与等求解预算全局ILP的差异。其余消融和交互用于解释机制。95%区间为固定三种子条件下逐比较的文档配对区间，未作多重比较校正；区间跨零不能解释为等效。完整求解状态、成本记录和统计规则见附录H.3。',
           '正式运行前，训练侧将T-B的数据构造整体比较和T-E的同数据学习比较列为关键对照；推理侧以RelationOnly和单对象动作分别检验组件可变性与集合表达，以同目标全局ILP检验求解策略取舍。组件优先分步策略补充检验共同决策，其余消融和交互用于机制解释。各关键比较统一报告效应量、文档配对区间、错误代价和完整成本，不因现有人工材料只为部分比较提供区间而改变职责。\n\n局部与全局ILP先比较相同逐文档总求解预算，另以相同端到端时限评价部署条件；软件、线程、缓存条件和共同准备开销保持一致，大预算结果不自动视为最优。95%区间为固定三种子条件下逐比较的文档配对区间，未作多重比较校正；区间跨零不能解释为等效，也不以多个未校正区间共同确认全部机制。求解状态、成本及失败记录见附录H.3。',
           'A1 2.6.3预先指定关键比较并统一统计报告要求')
    change('本章分别评价监督可靠性、增强数据的任务作用和成对学习的独立增量。前者关注改写后标签是否保持，后两者关注原始测试文本上的抽取结果。','本章以监督可靠性诊断为前提，按2.6.3预定的T-B、T-E分别评价数据构造整体及同数据学习增量；中心策略和过滤消融补充解释其条件。可靠性诊断关注改写后的标签，任务比较关注原始测试文本上的严格抽取结果。','A1 3.6实验引言对齐训练侧关键比较')
    change('本章固定T1训练条件，以I0为共同起点，分别比较完整系统和受控机制。组件及完整关系计数用于评价最终输出，候选覆盖、Oracle、对象评分、恢复风险和资源曲线用于解释增量来源。','本章固定T1训练条件，以I0为共同起点，按2.6.3区分贡献检验与求解策略比较。RelationOnly和单对象动作直接检验组件可变性与集合表达，同目标全局ILP检验局部策略的采用价值，组件优先分步策略补充检验共同决策。组件及完整关系计数评价最终输出，覆盖、Oracle、对象评分和恢复风险解释增量来源。','A1 4.6引言明确直接对照与补充比较')
    change('当前差值来自人工计数，尚未建立真实端点错误上的收益；不能仅由对I0的总增量确认每个复杂机制都值得保留。','当前两项关键比较仅给出人工均值差；正式运行须按2.6.3一并报告配对区间、错误代价和成本。本文不据现有差值确认真实端点错误上的收益，也不由对I0的总增量确认各机制均有必要。','A1 4.6.2明确关键对照现有报告的缺口')
    change('相对于组件优先分步策略，BR-J的关系增量为3.41和4.28个百分点，文档配对95%区间分别为[+2.58, +4.16]和[+3.39, +5.14]。该比较支持联合决策策略相对于本节分步策略的整体差异。','作为共同决策的补充比较，BR-J相对于组件优先分步策略的关系增量为3.41和4.28个百分点，文档配对95%区间分别为[+2.58, +4.16]和[+3.39, +5.14]。这些人工结果演示两种策略整体差异的报告方式。','A1 4.6.2保留分步数据并调整解释职责')
    change('RelationOnly、单对象动作及同目标全局求解分别承担组件可变性、集合表达与资源代价的检验。','RelationOnly和单对象动作是组件可变性与集合表达的关键对照，同目标全局求解检验资源取舍，分步策略补充分析共同决策。','A1 6.1总结同步主张与比较职责')
    change('第二阶段只完成支撑主要主张的比较：固定学习目标比较增强构造，固定增强集合比较学习项，完成至少一个可解释的原生外部系统对照，以及共同条件下的推理和四格运行。','第二阶段按2.6.3完成关键比较：T-B固定学习目标比较增强构造，T-E固定增强集合比较学习项；推理侧用RelationOnly、单对象动作和同目标全局ILP分别检验修改范围与求解取舍，分步策略作为补充。同时完成至少一个可解释的原生外部系统对照及共同条件下的四格运行。','A1 H.5执行顺序同步关键比较')

if decisions['cost_scope']=='B1':
    change('两阶段四格用于区分组合增量与配置成本，聚合成绩尚不能确定对象重叠。','两阶段四格用于分析条件增量，以及训练完成后的在线质量与时间取舍；聚合成绩尚不能确定对象重叠。','B1 中文摘要限定成本范围')
    change('A four-cell analysis separates combination gains from configuration costs, but aggregate scores do not identify object overlap.','A four-cell analysis examines conditional gains and online quality–time tradeoffs after training costs have been incurred; aggregate scores do not identify object overlap.','B1 英文摘要同步在线成本条件')
    change('第五章围绕组合增量、对象作用和配置选择三个问题展开。','第五章围绕组合增量、对象作用和训练完成后的在线配置选择展开。','B1 1.4章节说明限定配置问题')
    change('本章复用同一批四格人工计数，依次讨论组合增加了什么、对象作用能否从聚合成绩识别，以及训练、修正或组合如何比较成本。','本章复用同一批四格人工计数，依次讨论组合增量、对象作用的可识别性，以及训练完成后各配置的在线质量与时间取舍。','B1 第五章引言收紧任务承诺')
    change('### 5.3 训练 修正与组合的配置取舍','### 5.3 训练完成后的在线配置取舍','B1 5.3标题明确条件和范围')
    change('配置选择比较一次性训练投入、在线质量、额外时延和错误变更。表5-5仅在既有人工成本情景内列出相对T0＋I0的关系增量与在线额外时间；AAEC和CDCP共同起点为17.00秒和22.00秒。','本节在训练投入已经发生的条件下，比较各配置的关系F1与在线平均时间。表5-5给出相对T0＋I0的情景增量，AAEC和CDCP共同起点分别为17.00秒和22.00秒；一次性训练投入、服务量及摊销阈值不属于本表的分析范围。','B1 5.3开头与现有表格证据对齐')
    change('若一次性训练投入已经完成，只比较本情景的关系F1和在线平均时间，T1＋I0优于T0＋I1：AAEC高0.70个百分点、少13.00秒，CDCP高0.90个百分点、少21.16秒。这个条件比较说明配置选择需计入成本是否已经发生。无法重训、服务量不足以摊销训练或现有模型必须冻结时，不能沿用该排序。','在这一条件下，T1＋I0的关系F1高于T0＋I1，在线平均时间也更短：AAEC高0.70个百分点、少13.00秒，CDCP高0.90个百分点、少21.16秒。该排序以相应训练检查点已经可用为前提；尚需重训、需评估训练摊销或现有模型必须冻结时，本表不能直接给出总体选择。','B1 5.3保留数值与必要限制并去除重复条件')
    change('是否采用组合应据目标错误、质量收益与完整成本决定；具体局部和全局求解取舍统一见4.6.5—4.6.6节，本节不重复预算曲线，也不以假设的规模阈值推荐策略。','是否采用组合应结合目标错误、质量收益与在线代价判断；实际部署还须按4.6.5—4.6.6节检查尾延迟、失败及局部和全局求解取舍。','B1 5.3结论不越过在线比较范围')
    change('配置比较则需要区分已付训练成本和后续在线成本。','本章配置比较仅回答训练完成后的在线取舍，不推算训练投入的摊销条件。','B1 5.4小结同步范围')
    change('两阶段综合分析使用四格条件增量和在线成本讨论配置选择；','两阶段综合分析使用四格条件增量，并在训练投入已经发生的前提下讨论在线配置选择；','B1 6.1总结同步条件')
    change('|两项研究如何组合|2.7|5.1至5.3条件增量、对象边界与配置选择|','|两项研究如何组合|2.7|5.1至5.3条件增量、对象边界与在线配置选择|','B1 附录F阅读索引同步')

(R/'report_1010_v6_full.md').write_text(text)
(W/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
(W/'revision.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='report_1010_v5_full.md',tofile='report_1010_v6_full.md')))
(W/'writing_audit.json').write_text(json.dumps({'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'change_groups':len(changes),'author_decisions':decisions,'new_model_runs':0,'new_simulation_generation':False,'full_read_before_edit':True},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'characters':len(text),'change_groups':len(changes),'decisions':decisions},ensure_ascii=False))
