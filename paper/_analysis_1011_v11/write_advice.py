"""Write a version-bound framework and time-cost review, leaving v11 unchanged."""
from pathlib import Path
import hashlib,json
W=Path(__file__).resolve().parent;R=W.parent
timing=json.loads((W/'timing_audit.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
md=R/'report_1011_v11_full.md';assert sha(md)==timing['manuscript_sha256']
def tbl(head,rows):return '|'+ '|'.join(head)+'|\n|'+ '|'.join([':---']*len(head))+'|\n'+'\n'.join('|'+ '|'.join(map(str,row))+'|' for row in rows)
phase_rows=[[p['phase'],p['start_local'][11:16]+'—'+p['end_local'][11:16],f"{p['minutes']:.1f}",f"{p['percent']:.1f}%"] for p in timing['phases']]
render_rows=[[p['version'],p['render_runs'],p['rendered_page_images'],f"{p['render_file_production_seconds']:.1f}"] for p in timing['recent_versions']]
target={'status':'PROPOSED_POSITIVE_TARGET_SCENARIO_NOT_EMPIRICAL_OR_CALIBRATED_FORECAST','base_revision':'1011-v11','purpose':'Discuss an ICIC-aligned positive preview; not a replacement for any existing main table, native gold evaluation or solver result.','protocol':'Targets below apply only to an assumed replication of the ICIC in-domain metric protocol. The strict native complete-object protocol requires a separate baseline and result table.','rows':[{'dataset':'AAEC','metric':'Comp-F1','ICIC_reported':83.71,'proposed_target':85.20},{'dataset':'AAEC','metric':'Relation-F1','ICIC_reported':64.83,'proposed_target':68.20},{'dataset':'CDCP','metric':'Comp-F1','ICIC_reported':76.45,'proposed_target':78.30},{'dataset':'CDCP','metric':'Relation-F1','ICIC_reported':38.17,'proposed_target':41.50}],'not_done':['No new manuscript version','No new synthetic integer counts generated from these target means','No empirical runs or superiority validation','No change to archived negative outputs'],'formal_replacement_requirements':['matched protocol and budgets','four-cell and method ablations','integer counts and seed-level reconstruction','paired uncertainty and object identities regenerated','all tables figures and claims updated together']}
for x in target['rows']:x['assumed_delta_pp']=round(x['proposed_target']-x['ICIC_reported'],2)
(W/'proposed_ICIC_target_scenario.json').write_text(json.dumps(target,ensure_ascii=False,indent=2)+'\n')
targets=[[x['dataset'],x['metric'],f"{x['ICIC_reported']:.2f}",f"{x['proposed_target']:.2f}",f"+{x['assumed_delta_pp']:.2f}"] for x in target['rows']]
text=f'''# 1011 v11 框架改进与开销分析

日期：2026年10月11日。评估基于v11及其原始实验文件；论文Markdown SHA256为 `{sha(md)}`。本次是建议与时间分析，不改动v11正文，不运行新模型或重排Word。数值目标仅为讨论用的正向模拟情景。

## 一、结论与数据集范围

建议保留两阶段研究主线，先简化没有显示额外收益的实现，再优先改善候选与评分。主实验集中AAEC、CDCP；ArgUNSC退出后续主实验和追加投入，已有记录归入探索性附录或证据包，正文用一句话交代范围调整。CasiMedicos暂作可选迁移诊断，完成新增候选的真实评分和终图评价后再决定是否进入正式扩展实验。

依据是同样各8篇的候选诊断：ArgUNSC从0/107到3/107；CasiMedicos从0/37到13/37；CDCP从1/22到2/22。三者都是正确完整关系入池数，不是最终TP或F1。8篇小试足以帮助分配当前研究资源，不足以证明某个数据集原则上不适合整个框架。停止ArgUNSC投入的准确理由是当前适配成本高、可用候选少、对AAEC/CDCP主问题的增量信息有限。

不应把观察结果后的范围调整改写为“预先排除ArgUNSC”；也不必让一个非目标骨干的小规模探索在每章反复出现。正式研究范围与探索诊断分开交代即可。

## 二、框架的五项具体改进

|优先级|改什么|为什么|怎样判断是否保留|
|:---|:---|:---|:---|
|1|成分与关系分阶段解析，保留有效成分；训练原生跨度与类型；CDCP提出完整源范围|关系字段失败不应丢掉整份成分；候选缺失时优化器没有正确对象可选|固定文档评估跨度、类型、完整关系覆盖，尤其多源；不只看候选数量|
|2|把默认低分与真实低置信判断分开；完善训练侧OOF评分与保留风险检查|默认0.05及错误类型可能驱动删除；固定代理目标的提升并不保证F1提升|报告原TP保留、误改率、净恢复和最终F1；未评分对象拒绝事务或保留原图|
|3|保留关系影响域和标注对应，筛选从简单方案开始，完整筛选作为可验证选项|64个改写未检出关系漂移；简化与完整筛选拦下同一含义变化例，完整方案覆盖代价更大|同一生成池人工抽审，再比较训练增量与成本；不预设完整筛选必胜|
|4|保留依赖闭合事务，但不把集合动作或局部求解固定为必选|1536条冻结输入记录中单对象与集合聚合相同，小池全局平均更快|按开发侧固定选择规则：小池可全局，大池可局部；同候选、评分和预算比较|
|5|以ICIC完整系统作继承基线，明确训练与推理各自增量|当前模拟起点没有围绕ICIC旧协议对齐，单看两套分数难判断论文深化价值|保留四格：ICIC基础／仅新训练／仅新修正／二者结合；分别做机制消融|

前两项是让既定方法具备足够输入质量的实现工作，不必包装成第三、第四项论文创新。论文可以继续围绕“可靠关系监督上的成对学习”和“依赖闭合的结构修复”组织两项贡献。完整筛选、动作粒度、局部或全局是需要证据支持的实现选择。

训练侧建议把重点从“必须证明改写会大量破坏关系”移到“如何在可信对应因素上提供有效监督”。原标签分歧单列，不能让验证器自动改金标。若完整筛选没有额外收益，采用简化检查，仍可单独检验成对学习的贡献。

推理侧最应补的是评分与保留策略。开发侧校准接受阈值时，除了关系F1，也应跟踪原本正确对象的损失。阈值与规模切换规则在开发集固定，不能按测试文档是否修好临时选优化器。即使加入这些保护，也不宣称真实F1单调不降。

## 三、负结果怎么处理

|结果类型|主文处理|必须保留的内容|
|:---|:---|:---|
|ArgUNSC等非主线探索|可退出主实验；简短说明范围，细节放附录或证据包|原始输出、样本范围及后验调整事实|
|Luna小模型与目标Qwen不一致|作为实现诊断，避免外推成目标骨干失败|模型、训练状态、候选限制及实际结果|
|直接触及核心主张的负结果|说明适用边界或修改主张|完整筛选未体现增量、单对象与集合未拉开、误改、成本不占优|
|纯模拟压力情景|可只在附录保留简短敏感性分析|明确是假设，不混同实测|

因此，“不再围绕负结果组织整篇论文”是合理的；“删除已观察的不利证据，然后写成普遍有效”会改变结论含义。若最终Qwen受控实验取得正增益，主文以它为核心，Luna开发记录可以压缩，但不改写旧记录。

## 四、模拟主表怎样改成优于ICIC的目标情景

作为完整论文预览，设定“新框架优于ICIC”是允许且有用的设计目标。但框架更复杂并不能推出真实分数一定更高；目标情景表示假如研究假设成立，结果怎样报告。

当前v11模拟最终值为AAEC组件82.26、关系61.87，CDCP组件74.77、关系57.36。ICIC原表分别为83.71、64.83、76.45、38.17。前者采用当前严格完整对象情景，后者属于ICIC原配置；此外v11的T0/I0还不是原ICIC Full的直接等价行。上版没有先锚定这个继承关系，是模拟设计应改进的地方。

建议分两套评价：

1. ICIC原协议对齐的系统比较：明确原始数据划分、标签、跨度匹配、关系表示及预算，保留ICIC引用值，另列新方法目标情景。实际复现时必须重新跑基线，不能把引用均值当作当前重复实验。
2. 严格原生完整对象比较：用当前评价器重新建立ICIC基线和新方法结果。CDCP完整联合源与原表关系指标不能仅凭都叫Relation-F1就拼为一列。

下面仅是一组便于讨论的正向目标，不是预计能达到的精确预测，也尚未生成对应整数记录：

{tbl(['语料','ICIC原协议指标','ICIC报告值','新框架目标情景','假设增量pp'],targets)}

目标值无需大幅超过ICIC，也无需每个消融、每个种子、每套语料都严格同序。尤其不宜强行让局部BR-J在质量和耗时上同时超过同目标全局求解。新候选和新训练可以改变旧ICIC的候选Oracle；不能继续沿用旧67.24作为新模型的必然上界。

若将该情景用于新稿，须从整数TP/FP/FN及同批对象身份重建三种子、四格、增量、区间、图表和案例计数，再同步摘要、第三至第五章。不能只将最终F1单元格改大。本次目标文件为[proposed_ICIC_target_scenario.json]({W/'proposed_ICIC_target_scenario.json'})，身份是PROPOSED，不替换已交付论文或任何真实结果。

## 五、这轮究竟把时间花在哪里

v11从2026年10月11日14:56:50至16:03:39，墙钟总时长约{timing['turn_elapsed_minutes']:.1f}分钟。以下按保存的里程碑划分，互不重叠；它是阶段窗口，不能当作逐秒独占工时或“思考精力”计量。模型任务存在并行，后期窗口也包含计数复算与正文修正。

{tbl(['阶段','北京时间','分钟','占本轮'],phase_rows)}

这轮主要在做实验和证据整理、数字一致性、全文交付；纯句子润色占比没有单独计时。首版渲染后的28.3分钟约占42.3%，其中包括分页、表目录、短页、公式保留、源码与Word一致性及视觉检查。不能把42.3%全部称为纯格式时间，但格式迭代明显偏多。

近期几版保留的完整渲染记录如下。仅比较渲染次数及文件写出区间，不把各版不同的实验范围当成同一种润色任务：

{tbl(['版本','全篇渲染次数','累计页面PNG','渲染输出区间合计秒'],render_rows)}

v11九次共生成1254张页面图，但最终稿只有137页。九次目录创建至最后一张PNG写出的区间合计114.2秒，约1.9分钟；这个近似指标不含看图、推敲、修改、目录缓存或工具间间隔。因此慢点主要在反复修订和核验，不是PDF转换程序。

1536条求解批次从输入冻结到输出冻结仅{timing['solver_batch_input_to_output_freeze_seconds']:.2f}秒，已不含候选、语言模型和评分生成；代码实现、测试、评价以及解释这些结果远比求解本身耗时。30项Luna任务也不能按单任务时长简单相加为用户等待时间。

没有足够可靠的分模块token和金额归因，本报告不编造收费或计算资源占比。原始计时元数据见[timing_audit.json]({W/'timing_audit.json'})，其中不含对话内容。

## 六、后续工作方式如何压缩

1. 方法讨论和数字方案阶段先固定Markdown、图表数据及修改清单。未要求完整Word交付时，不重排整篇论文。
2. 先确认继承基线、主实验范围和正向目标情景，再一次性生成所有计数和图表；避免表格成形后反复修主张与数字。
3. Word交付集中在内容稳定后：首次渲染查问题，集中修复，再更新目录并最终核验。以2—3次完整渲染为流程目标；出现实际缺陷时才追加，不保证任何版本都恰好三次。
4. 正文保留必要的模拟身份说明和真实诊断边界，详细运行清单、重复限制和哈希留在附录／配套文件，减少反复扩充正文导致的分页返工。
5. 纯格式阶段尽量控制在常规内容修订轮的10%—15%时间目标内；首次大改或公式表格结构变化单列。该比例是流程目标，不是本轮测量结果或保证。

这一轮可压缩的主要是重复生成及格式返工。数字一致性、正确关系评价和核心结论的核对仍应保留，因为它们决定论文结论是否站得住。

## 证据入口

- [v11论文]({md})：表3-5、4-3及附录E原ICIC表。
- [实际候选覆盖]({R/'research_1011_v11/candidate/evaluation/coverage.json'})：24篇、四层候选。
- [实际漂移判断]({R/'research_1011_v11/drift/analysis/metrics.json'})：64变体、原标签分歧和筛选代价。
- [求解比较]({R/'research_1011_v11/solver/evaluation/metrics.json'})：冻结候选与评分的1536条记录。
- [ICIC本地原文]({R/'research_0920/sources/icic_2026_5295.txt'})：原配置、主结果和Oracle范围。
'''
out=R/'1011_v11框架改进与开销分析.md';out.write_text(text)
print(out)
