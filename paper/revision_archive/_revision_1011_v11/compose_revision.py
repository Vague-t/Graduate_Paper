"""Assemble a complete preview from retained v10 plus labeled real/synthetic evidence."""
from pathlib import Path
import hashlib,json,re
W=Path(__file__).resolve().parent;R=W.parent;E=R/'research_1011_v11';S=E/'simulation'
read=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=(R/'report_1011_v10_full.md').read_text();text=source
changes={'global':[['1011-v10','1011-v11']],'text_replacements':[],'insertions':[],'sections_before':[],'append_blocks':[],'heading_renames':[]}
def P(s):return {'type':'paragraph','text':s}
def H(s,level=3):return {'type':'heading','text':s,'level':level}
def T(c,headers,rows,widths=None,split=None):return {'type':'table','caption':c,'headers':headers,'rows':[[str(x) for x in r] for r in rows],'widths':widths or [1]*len(headers),'split':split or []}
def md(blocks):
 out=[]
 for b in blocks:
  if b['type']=='paragraph':out.append(b['text'])
  elif b['type']=='heading':out.append('#'*b['level']+' '+b['text'])
  else:out.append(b['caption']+'\n\n|'+'|'.join(b['headers'])+'|\n|'+'|'.join([':---']*len(b['headers']))+'|\n'+'\n'.join('|'+'|'.join(r)+'|' for r in b['rows']))
 return '\n\n'.join(out)+'\n\n'
def replace(a,b):
 global text
 assert text.count(a)==1,(a[:80],text.count(a));text=text.replace(a,b);changes['text_replacements'].append({'old':a,'new':b})
def para(prefix):
 q=[p for p in text.split('\n\n') if p.startswith(prefix)];assert len(q)==1,(prefix,len(q));return q[0]
def before(label,blocks,main=False):
 global text
 match=re.search(r'(?m)^#{2,4} '+re.escape(label)+'$',text);assert match,label
 text=text[:match.start()]+md(blocks)+text[match.start():];changes['sections_before'].append({'anchor':label,'blocks':blocks,'main':main})
def add_after(anchor,paragraphs):
 global text
 assert text.count(anchor)==1;text=text.replace(anchor,anchor+'\n\n'+'\n\n'.join(paragraphs));changes['insertions'].append({'anchor':anchor,'paragraphs':paragraphs})
fmt=lambda x:f'{x:.2f}'
corpus_names={'aaec':'AAEC','cdcp':'CDCP','argunsc':'ArgUNSC','casimedicos':'CasiMedicos'}
drift=read(E/'drift/analysis/metrics.json');solver=read(E/'solver/evaluation/metrics.json');coverage=read(E/'candidate/evaluation/coverage.json')
assert solver['runs']==1536 and solver['unique_documents']==96
assert read(E/'solver/evaluation/audit.json')['status']=='PASS'

replace(para('稿件说明：'), '稿件说明：本稿为完整数字预览，主表及新增训练、OOF、外部对照和四格对象数据均为明确假设下的模拟材料，不代表真实实验记录或经验证的效果预测。真实材料包括既存CPU诊断、此前Luna预测与评分试验，以及本版64个改写、24篇成分抽取诊断和1536条固定输入求解记录。真实诊断和模拟主结果分表报告，负结果不以模拟数字覆盖；成本中的实测、组合上界与吞吐假设分别标识。附录E保留前期存档，H.6—H.8保留独立旧情景。本版补齐了预览所需数据，正式训练、人工审核及完整系统验收仍须实测替换。')
replace(para('主实验仍以明确假设计数演示'), '主比较以明确假设计数展示训练和完整系统的评价，补齐训练对照区间、错误链、四格对象与成本条件。真实Luna诊断保留AAEC关系恢复和CDCP评分误改等结果。新增64个改写经两路模型判断，标记1个成分语义变化，未检出关系标签漂移，尚不支持完整影响域筛选的额外收益。三套语料各8篇的候选诊断中，分离成分抽取使CasiMedicos完整关系入池数由0增至13／37；ArgUNSC和CDCP覆盖仍低。对既有96篇冻结输入开展1536条局部、单对象和全局求解记录，单对象与集合动作的聚合指标相同，全局也未解决低正确关系率。上述证据将研究结论限定于有限候选、原生接口与评分条件，训练贡献、目标系统优势和两阶段互补仍是待实测验证的主张。')
replace(para('The main comparisons use explicitly assumed counts'), 'The main comparisons are explicitly simulated and now include paired training contrasts, error-chain records, four-cell object identities, and cost assumptions. Genuine Luna diagnostics retain both successful recovery and harmful edits. Two model assessments of 64 new paraphrases flag one component-meaning change but detect no relation-label drift, providing no additional benefit for the full affected-domain filter in this small pool. In eight documents per diagnostic corpus, separate component extraction increases complete-relation candidate coverage on CasiMedicos from 0 to 13 of 37 gold relations, while coverage remains low on ArgUNSC and CDCP. A total of 1,536 solver records reuse fixed inputs from 96 documents: single-object and set-level actions yield identical aggregate metrics, and global optimization does not resolve the low true-relation rate. These observations bound the proposed methods by candidate coverage, native annotation interfaces, and score quality. Training gains, full-system superiority, and two-stage complementarity remain hypotheses requiring empirical validation.')
replace('第六章总结两项设计及尚未完成的核心验证。','第六章总结两项设计、真实诊断的边界及模拟预览需要替换的实证部分。')
replace('真实语义风险、源选择偏移和训练增量仍需同源记录验证，现阶段不由低漂移或字面变化推定方法有效。','新增改写池尚未显示完整筛选的额外收益；人工语义判断、源选择偏移和训练增量仍需同源记录验证，不由低漂移或字面变化推定方法有效。')
replace('表2-2列出估算情景的参考设置与规模，不构成可执行配置；','表2-2列出估算情景的参考设置与规模，表2-3及配套JSON补齐预览参数；静态配置校验通过不等于训练入口或设备已经验收；')
replace('当前增强模型、语义验证器、文本编码器、跨度头及评分器尚未绑定具体检查点；','预览中生成、增强、验证与编码统一指定Qwen2.5-7B-Instruct，跨度与评分头结构见表2-3；')
replace('的取值及选择方案也未登记。配套配置单列未绑定字段，表中参考值不代替实测环境。','分别设为1、1、0.5、0.5；这些是预览假设。模型工件revision和实际设备在正式启动时解析、校验并写入运行清单，不能预填虚构的检查点哈希。')
replace('本版未绑定的系数见2.6.2节','本版预览固定系数与实际运行身份要求见2.6.2节')
before('2.6.3 统计分析与计算成本',[
 T('表2-3 补充实现配置（预览假设）',['模块','固定参数','身份与用途'],[
 ['模型与分词器','Qwen/Qwen2.5-7B-Instruct','四类模型职责共用该家族；实际revision待启动解析'],
 ['跨度与对象头','起止各一线性层；2层MLP，隐藏1024、dropout 0.1','跨度BCE；完整对象sigmoid；新头须实际训练'],
 ['优化细节','AdamW，衰减0.01，β=(0.9,0.999)，ε=10⁻⁸','warmup 3%，梯度裁剪1，bfloat16'],
 ['头部训练','学习率10⁻³，评分头10 epoch','生成适配仍5 epoch；不得改写为ICIC实际轮数'],
 ['损失权重','增强1，头监督1，组件／关系对齐各0.5','预览固定；正式备选0.25／0.5／1仅在训练侧选择'],
 ['生成与校准','增强temperature 0.7、top-p 0.9；评价temperature 0','按对象族Platt校准；3折OOF及8∶1∶1用途划分'],
 ['硬件与资源','假设1张A100 80GB、64GiB RAM、4 CPU线程','未实际分配；预检槽位上限500万，评分批4096'],
 ],[1.15,2.25,2.6]),
 P('配置写法沿用ICIC对骨干、LoRA、优化器及修正预算的集中登记方式；ICIC原文没有给出本表GPU型号、所有新头和本版固定训练轮数，这些字段均为新设的预览条件。实际Luna任务使用gpt-5.6-luna、low，其温度、精确快照、token用量未由当前接口提供，不套用本表参数。配套preview_config.json及config_validation.json分别保存参数与静态校验；没有执行Qwen训练或宣称配置已在目标设备生效。')],True)

drift_rows=[]
for r in drift['filters']:
 st=r['accepted_states'];drift_rows.append([corpus_names[r['corpus']],{'format_only':'仅格式','internal_positive':'成分＋内部正','full_affected':'成分＋完整影响域'}[r['filter']],f"{r['accepted']}/32",f"{r['source_coverage']}/16",st.get('drift',0),st.get('unresolved_or_anchor_disagreement',0)])
before('3.7 本章小结',[
 H('3.6.7 Luna改写与筛选的真实诊断',4),
 P('在AAEC、CDCP训练侧各固定16篇文本，按长度四分位和预定哈希选样，每篇对至多3个组件生成简洁、流畅两个改写，共64个变体。生成者不读取关系标签；筛选与复核由两个全新上下文分别执行，均请求gpt-5.6-luna／low。复核不读取筛选接受标志。原文与改写后的标签分别判定，先排除原标签本就被模型否定或无法判断的因素，再统计改写诱发变化；这种设计不把模型质疑原标注误算为监督漂移。'),
 T('表3-10 同一真实改写池的筛选与复核',['语料','筛选','接受／32','源覆盖／16','接受中变化','接受中待定'],drift_rows,[1,2.15,1.15,1.15,1.3,1.3]),
 P('表中“变化”是复核模型对成分含义、类型或关系标签变化的判定，“待定”包含原标签分歧，不计作确认稳定。AAEC的32个变体中24个未检出漂移、8个待定；CDCP为21个未检出、10个待定、1个成分含义变化。后者为00423的obligation改成debt，两路模型均认为范围收窄，但原上下文就在讨论债务，仍需人工裁决；不能称为已确认的严重语义错误。'),
 P('448个关系因素与变体配对中，复核模型认可原标签的有430个，未检测到其中任何关系标签因改写改变；其余18个属于原标签分歧。因此本试验不支持“原始关系漂移较高”或“完整影响域比简化检查多发现漂移”。两种语义筛选都拒绝了同一个成分变化例；完整筛选在CDCP另拒绝3个复核未检出漂移的变体，简化筛选为1个。这里描述的是相对模型复核的拒绝代价，并非人工金标准误拒率。'),
 P('64个变体均不是原样复制；AAEC和CDCP改写区域的字面编辑距离中位数分别为0.793和0.671，不能解释为语义多样性。两路变体状态判断分别在28／32和23／32例上一致。样本较小、改写要求保守、NONE只按预定槽位抽样且两路模型同源，结论只覆盖本池。正文保留完整影响域作为可检验机制；对本池优先采用更简单的语义检查，并将完整筛选的采用条件写为：在独立人工复核中检出额外漂移且覆盖代价可接受。模拟表3-3、3-4不由该真实试验产生。')],True)

candidate_rows=[]
layers={'A_original':'原候选','B_parse_components':'成分独立解析','C_separate_extraction':'另行成分抽取','D_boundary_and_joint':'再扩边界／源组'}
for r in coverage['aggregates']:
 candidate_rows.append([corpus_names[r['corpus']],layers[r['layer']],f"{r['C_hit']}/{r['gold_C']}",f"{r['R_hit']}/{r['gold_R']}",r['components'],r['relations']])
solver_rows=[]
for r in solver['aggregates']:
 if r['budget']==5 and r['mode'] in ['BRJ-lite','GlobalILP-lite']:
  solver_rows.append([corpus_names[r['corpus']]+('显式' if r['condition']=='dense_native' else ''),r['mode'].replace('GlobalILP-lite','全局ILP-lite'),fmt(100*r['C']['F1']),fmt(100*r['R']['F1']),fmt(r['wall_seconds']['mean']*1000),fmt(r['wall_seconds']['P95']*1000)])
before('4.7 本章小结',[
 H('4.6.8 候选修复与求解范围的真实对照',4),
 P('为诊断正确关系过少的原因，在既有CDCP、ArgUNSC、CasiMedicos样本中各固定8篇，按长度分层和预定哈希取样，共24篇。该集合复用了已经观察过结果的文本，属于诊断复用，不能称为独立测试集。追加的6项Luna任务仅抽取成分和至多一种备选类型，不同时输出关系；先独立解析旧输出中可定位的成分，再加入新成分，最后一次性扩展边界和CDCP相邻2／3成员源组。候选构建不读金标，冻结后才核查覆盖。'),
 T('表4-12 成分接口调整后的严格候选覆盖（真实输出）',['语料','候选层','组件命中','关系入池','组件数','关系数'],candidate_rows,[1.35,1.8,1.2,1.2,1,1]),
 P('表4-12各层使用相同文档分母；所有原候选受保护，补充组件上限64、补充槽位4096。该诊断的距离排序和源组保留不等于正式方法的全类型评分排序。CasiMedicos从0／37到13／37说明接口与成分覆盖确实是可改善瓶颈，但这些新关系尚未评分或选入终图，不能写成F1提高。ArgUNSC最高3／107、CDCP最高2／22，仍不足以可靠比较复杂修正机制。增加边界候选显著扩大池，却没有继续增加聚合正确关系数；CasiMedicos实际新增1条、同时在固定裁剪中失去1条，其他两套没有新命中。CDCP两个多源金标仍全部缺失。'),
 P('据此将实现职责拆开：语法错误的关系字段不连带丢弃能够独立定位的成分；二元语料分别输出多条边，CDCP保留完整联合源；新增候选与评分缺失分别登记。CasiMedicos优先完善成分抽取和原生类型学习；ArgUNSC优先处理子句边界及外交语篇的Claim／Premise定义；CDCP优先修复value／fact／testimony混淆和完整源组提案。保留这些接口调整，不以无效的候选膨胀代替任务适配。'),
 P('另在既有96篇的冻结候选、对象分和共同初始图上，比较RelationOnly、单对象、BRJ-lite及同目标全局ILP-lite。CDCP使用稀疏与显式两种评分，因此共有128个文档与评分条件；乘以4个策略和0.25、1、5秒三档求解预算，形成1536条真实执行记录。局部采用累计编辑预算，全局采用终态净编辑预算，包含关系沿用4.6.1；全局实现依次最大化效用、最小化净编辑，未实现完整词典序破同分。'),
 T('表4-13 冻结Luna输入的5秒求解对照（真实运行）',['语料／评分','策略','组件F1','关系F1','均时ms','P95 ms'],solver_rows,[1.35,1.65,1,1,1,1]),
 P('各预算下的单对象与BRJ-lite聚合严格计数相同，因此本批没有显示集合动作的独立增量；这不证明两者所有可达图相同。CDCP显式评分下RelationOnly关系F1为1.65，BRJ-lite为1.60，全局为1.59，均低于共同初始图3.33。其余评分条件的修正后关系F1均为0。全局在这些小图上的平均时间反而更低，不能把主情景中局部节时的设定推广到本批。这里计时从候选与分数已准备后开始，不包含模型生成和语义评分。'),
 P('适配性取决于原生表示、候选召回和评分。当前低分首先暴露后两项不足，既不能否定结构机制，也不能证明跨语料有效。若上述适配仍不足，可改用监督跨度／关系抽取器或固定成分的关系判别。AAEC用于恢复案例，CDCP用于多源压力检验，两套新增语料用于迁移局限分析。')],True)

replace('当前材料尚不能量化预检拒绝比例及恢复空间损失，计量字段见附录H.3。','本版以真实小池枚举量及显式吞吐假设补充成本推测，并计算正式全类型组合的宽松规模界（H.10—H.11）；它们不能量化正式池实际拒绝比例或恢复损失，计量字段仍按H.3保存。')
replace('当前保持既定候选策略，以实际规模测量决定是否需要改变它。若裁剪前枚举不可承受，再比较预筛选或受限生成，并重新测量覆盖及完整关系遗漏；所有局部／全局对照都使用改变后同一候选快照。','正式定义保留全类型候选的参考边界；对组合数过大的CDCP，受限源组提案作为资源适配选项，必须单独命名、冻结并重测覆盖，不再假设4096的最终上限足以控制准备成本。4.6.8仅验证一个轻量提案池，未证明其多源召回充分；所有局部／全局对照使用同一候选快照。')
replace('4.6.7单列实际Luna预测、轻量修正和评分对照。二者具有独立的运行身份、分母与成本口径。','4.6.7—4.6.8单列Luna预测、候选与求解诊断。各批材料具有独立的运行身份、分母与成本口径。')
replace(para('本章将组件集合替换'), '本章定义完整图编辑事务及其受限执行性质。真实诊断显示候选与评分仍是瓶颈；单对象与集合动作聚合相同，小图全局求解更快。策略须据质量与成本选择，模拟主表不证明真实优势。')
replace(para('评价以RelationOnly、单对象和同目标全局求解分别检验'), '真实轻量对照支持先完善候选与评分；完整系统的训练与推理组合，仍需同批受控结果验证。')
replace('对象补全仅作为附录H.8的非唯一性示例，不充当模型输出。','5.4节补齐与主表一致的人工成员分析，附录H.8保留非唯一性示例，两者均不充当模型输出。')
# A new subsection follows the existing online cost table, so numbering stays in reading order.
overlap=read(S/'four_cell_overlap.json')['rows'];overlap_rows=[]
for ds in ['AAEC','CDCP']:
 for obj in ['component','relation']:
  rows=[r for r in overlap if r['dataset']==ds and r['object']==obj]
  sums={k:sum(r[k] for r in rows) for k in rows[0] if k not in ['dataset','object','seed']}
  overlap_rows.append([ds+('组件' if obj=='component' else '关系'),sums['training_only'],sums['inference_only'],sums['shared'],sums['combination_new'],sums['lost_vs_T1'],sums['remaining_FN']])
before('5.4 本章小结',[
 H('5.4 同计数四格的对象成员分析'),
 P('为补齐综合分析预览，重新构造主情景生成器的人工对象身份，逐文档、逐种子核对四格TP、FP、FN与表5-1完全一致，再对成员集合取交差。这里没有从真实模型输出重建原生跨度图；对象ID仅在模拟记录内有意义。表5-6合计三个种子的对象出现次数，同一文档的重复种子不被当作独立新样本。'),
 T('表5-6 四格正确对象作用的成员分解（模拟）',['对象','训练独有','推理独有','共同恢复','组合独有','相对T1损失','组合仍漏'],overlap_rows,[1.3,1,1,1,1,1.25,1.1]),
 P('在该指定对象构造中，AAEC关系的训练独有、推理独有和共同恢复分别为99、98和141次；CDCP为80、77和106次。两阶段存在较多共同覆盖，同时组合出现125和103次未由任一单阶段命中的关系，但又损失T1已经正确的78和58次关系。因此“组合总F1更高”不等于两阶段互不重复，也不等于每个训练收益都能保留。'),
 P('该分解完整回答了预览中的对象重叠问题，却仍不是实际互补性证据。由于总计数允许多个成员配置，H.8的不可识别性论证继续成立；本表只选择与主情景相容的一个构造。正式替换须保留同批四格原生对象键，并优先检查组合独有恢复是否来自真实端点补入、较好评分或仅仅预测集合变化，不以模拟ID补作文本案例。')],True)
old='5.4 本章小结';new='5.5 本章小结'
# Only the existing heading is renamed; the inserted 5.4 has a different title.
text=text.replace('### '+old,'### '+new);changes['heading_renames'].append({'old':old,'new':new})
replace(para('四格比较把组合总增量分解'), '四格比较将组合增量拆分为条件变化，成员级模拟进一步显示共同恢复、独有恢复和新增损失可以同时出现。它补齐了完整数字预览，但实际互补性仍需同批训练与推理输出验证。在线配置比较只回答训练投入已发生后的取舍，不把毫秒级轻量求解结果或设定吞吐外推成完整系统成本。')
replace('当前材料尚未验证真实漂移规模及学习收益。','新增小规模改写未检出关系标签漂移，因而尚未建立完整影响域筛选的额外必要性；学习收益仍由模拟展示，不能据此认定真实成立。')
replace('局部与全局的真实优先级尚未确定，允许依据运行结果简化求解设计。','新增冻结输入对照未显示集合动作的独立收益，且小图全局求解平均更快；本版据此保留简化为单对象或全局选择的路径，完整系统优先级仍待实际目标模型结果决定。')
replace(para('正文主比较、增强审计判断和设定成本仍为估算情景。'), '正文主比较及新增训练错误链、匿名外部比较、四格成员和成本吞吐仍为模拟或假设。真实增补覆盖32篇的64个改写、24篇成分候选诊断，以及复用96篇输入的1536条求解记录；它们不是新增1536篇文本，也没有Qwen训练。监督判断来自同型号模型的分离上下文，未经过人工金标准审核；候选诊断只测入池能力，成本只在声明范围内计量。因此本版达到数字与版式完整预览，未达到全部实证贡献完成。')
replace('当前核心比较和真实问题诊断尚未完成，属于本研究的验证缺口，集中列于附录H.5。','核心比较已有轻量诊断与完整模拟预览，但正式训练、人工审阅及目标系统比较仍是验证缺口，集中列于附录H.5。')
replace('仅标点规范化、单对象及分步对照仍未完成。','该旧批未完成仅标点、单对象及分步对照；本版单对象／全局检查另在D.13所列96篇冻结输入上完成，不回填为原16篇的结果。')
replace('真实增强漂移与成对训练仍须独立完成。','新增改写诊断见3.6.7；人工裁决与成对训练仍须独立完成。')

factor_rows=[]
for r in drift['factor_breakdown']:
 factor_rows.append([corpus_names[r['corpus']],{'internal_positive':'内部正','crossing_positive':'跨边界正','internal_NONE':'内部NONE','crossing_NONE':'跨边界NONE'}[r['category']],r['factor_variants'],r['original_label_agreed'],r['original_disagreed'],r['drift']])
before('附录E 前期数值与协议存档',[
 H('D.13 新增改写、候选与求解的运行身份'),
 P('research_1011_v11保存30项新的gpt-5.6-luna／low任务：8项改写、8项筛选、8项独立上下文复核和6项成分抽取。每项限制只读指定指令与输入；生成和候选预测不读评价金标。判断原／新标签保持时，筛选和复核读取的是待判定的原标注及迁移标注，不能称为对标签身份盲审；它们对彼此输出与接受决定隔离。请求模型名与推理档位已登记，精确部署快照、采样种子、API token数未暴露。失败与待定全部保留，无按结果重试。'),
 T('表D-13 原标签分歧与改写后关系变化（模型复核）',['语料','因素','配对数','认可原标签','原标签分歧','诱发变化'],factor_rows,[1,1.7,1.1,1.4,1.4,1.2]),
 P('影响域包含全部受影响正关系；NONE按固定哈希最多抽取内部4项、跨边界4项，CDCP不会把已知联合源中的单成员机械登记为负关系。两路复核者同源而非统计独立，其一致性不等于准确性。所有结果保持“未检出”“待定”“检测到”三种状态，0个检出不是对总体漂移率为0的证明。'),
 P('候选构造分A—D四层，金标只在构造完成、输入与代码哈希冻结后用于覆盖核查。A为原v10池，B独立挽救可定位的旧成分，C追加新抽取及备选类型，D再作一次±1评价token边界扩展和CDCP相邻源组；保护原对象，补充64组件与4096槽位。D层为多源槽位预留1024个位置，剩余份额可回用于二元槽位。该固定距离排序与正式完整对象评分排序不同，结果只归属候选诊断。未用金标挑选类型或按正确率修改排序。'),
 P('求解比较读取v10原始候选、稀疏／显式评分和同一合法初始图；初始化失败保持空输出进入分母。全局ILP使用相同完整对象效用、重叠／端点／标签／源连续性约束和分项下界；记录主目标证书及净编辑破同分状态。局部与全局的净／累计预算差异明确保留。5项独立小规模枚举与接口检查通过，1536条输出通过原生金标和轨迹／可行性审计；已有v10接口检查另列，不把这些检查写成目标模型的训练验收。'),
 P('代码入口为prepare.py、prepare_judges.py、evaluate_drift.py、candidate_probe.py、solver_compare.py和evaluate_solver.py，模型输出、输入／输出冻结与评价记录随证据包保存。simulation目录独立保存人工计数、成员、OOF示例和配置假设。真实输出与模拟文件有各自身份，重复汇总不计为新增模型调用。')])

# Anonymous external rows complete the preview without fabricating a named competitor run.
external=read(S/'external_comparator_counts.json')['summary'];ext_rows=[]
for r in external:
 ext_rows.append([r['dataset'],'编码式对照' if r['method']=='SIM_encoder' else '生成式对照',fmt(r['component']['mean'])+'±'+fmt(r['component']['sd']),fmt(r['relation']['mean'])+'±'+fmt(r['relation']['sd'])])
before('附录H 关键诊断与综合证据记录',[
 P('为完整预览外部比较的写法，表G-3使用匿名外部系统的模拟输入；“编码式”“生成式”仅是比较职责，不绑定Kawarada、UniASA或任何已发表系统，也不引用为它们的成绩。各行使用与主情景相同的人工金标规模，保存逐文档整数计数；正式接入后整行替换。'),
 T('表G-3 外部比较的匿名预览结果（全部模拟）',['语料','对照职责','组件F1','关系F1'],ext_rows,[1,2,1.5,1.5]),
 P('该情景故意不保证本文在所有语料优于外部对照：CDCP的生成式对照关系值可高于本文主情景。比较结论应跟随同协议实际结果，而不是以外部行填满表格即认为定位完成。当前完成的是比较方案和数字预览，仍没有真实外部系统运行。')])
replace('未运行项目保持待填，不使用人工分数代替。','未运行项目保持未实测身份；新增匿名模拟行只用于预览版面与分析，不填入任何已发表系统名下。')
replace('尚未生成新的逐文档记录或计算置信区间，不能称为已完成的敏感性实验。','本版已为这些假设生成逐文档整数记录并核算实际差值（H.12）；它们是模拟敏感性分析，仍不是新增模型实验，也不以模拟区间推断真实方法效应。')
replace('核心验证仍未完成。第一阶段在固定的少量真实文档上复核监督漂移、端点相关错误、候选覆盖及裁剪前成本，保留来源、分层和全部失败记录；先确认复杂机制所针对的问题是否实际存在，再决定设计是否保留。模板和成本示例不提供该判断，结果不足时允许收缩主张或简化机制。','核心验证的第一阶段已增加少量真实改写、候选和求解诊断，结果见3.6.7、4.6.8及D.13；未检出关系漂移、集合动作无聚合增量及小图全局更快等不利结果全部保留。目标模型OOF、训练贡献和人工审核仍未完成；模拟补齐的是预览，不替代判断机制必要性的真实材料。')
replace('当前不在三者中预先定案，也不从成本函数选取有利阈值。','本版小图诊断支持优先比较更简单的单对象或全局选择；不能直接将这一局部结果推广为所有目标规模的结论，也不从成本函数选取有利阈值。')
replace('若第五章仍缺独立内容，压缩相应小节；不以更多集合定义代替发现。','本版已用与主表同计数的人工对象成员补齐第五章预览，实际综合发现仍须来自原生四格输出，不能用模拟成员重叠替代。')

# Synthetic details append after H.8, retaining all earlier example identities.
paired=read(S/'additional_paired_and_stress.json');oof=read(S/'oof_error_records.json')['rows'];cost=read(S/'candidate_cost_estimates.json')['rows'];bounds=read(S/'formal_prepruning_bounds.json')['rows']
pairrows=[]
for r in paired:
 if r.get('object')=='relation' and 'ci95' in r:
  label={'full_data_i0 - qos_i0':'T-B 数据构造','head_i0 - full_data_i0':'同数据头监督','t1_i0 - head_i0':'T-E 成对目标'}[r['comparison']]
  pairrows.append([r['dataset'],label,fmt(r['delta']),'['+fmt(r['ci95'][0])+', '+fmt(r['ci95'][1])+']'])
oofrows=[]
for ds in ['AAEC','CDCP']:
 rr=[r for r in oof if r['dataset']==ds];keys=['gold_R','initial_TP','missing_endpoint_span','wrong_endpoint_type','complete_slot_absent','score_or_label_error','budget_or_search'];v={k:sum(r[k] for r in rr) for k in keys}
 assert v['gold_R']-v['initial_TP']==sum(v[k] for k in keys[2:])
 oofrows.append([ds,len(rr),v['gold_R'],v['initial_TP'],v['missing_endpoint_span']+v['wrong_endpoint_type'],v['complete_slot_absent'],v['score_or_label_error']+v['budget_or_search']])
costrows=[]
for r in cost:
 if r['layer'] not in ['C_separate_extraction','D_boundary_and_joint']:continue
 costrows.append([corpus_names[r['corpus']]+(' C' if r['layer'].startswith('C') else ' D'),fmt(r['pre_slots_mean']),fmt(r['post_slots_mean']),fmt(r['enumeration_ms_mean_measured']),fmt(r['score_seconds_mean_estimated_at_500_2000_10000'][1]),fmt(r['score_seconds_P95_estimated_at_2000'])])
boundrows=[[r['dataset'],r['spans'],f"{r['loose_slot_bound']:,}",fmt(r['score_hours_at_2000']),fmt(r['object_GiB_at_512B'])] for r in bounds]
stressrows=[]
for ds in ['AAEC','CDCP']:
 for mechanism,label in [('paired','成对学习'),('component_change','允许组件变化'),('local_vs_global','局部减全局')]:
  rr=[r for r in paired if r['dataset']==ds and r['comparison']==mechanism];stressrows.append([ds,label,'／'.join(fmt(r['assumed_shift_pp']) for r in rr),'／'.join(fmt(r['actual_integer_delta']) for r in rr)])
appendix=[
 H('H.9 训练比较与OOF错误链的数字预览'),
 P('表H-5从保留的v7逐文档计数增加所需成对比较，先汇总每次重采样的TP、FP、FN，再计算三个固定模拟种子的平均差；2000次文档配对重采样仅表示该计数模型内部波动。数据构造、头监督与成对目标分别比较，不能把最后系统的总提升归给某一个模块。'),
 T('表H-5 关系F1的关键训练对照（模拟）',['语料','比较','差值pp','文档配对95%区间'],pairrows,[1,2,1.2,2.2]),
 P('OOF预览另生成AAEC 320篇、CDCP 580篇人工记录，划入3个互斥文档折。每条遗漏按端点跨度、端点类型、完整槽位、评分／标签、预算／搜索取首个阻断，互斥分类相加等于遗漏总数。该表没有运行持出模型，不可把模拟端点比例称为Qwen或Luna的真实错误率。'),
 T('表H-6 OOF原生关系错误链的示例计数（模拟）',['语料','文档','金标','初始TP','跨度／类型漏','槽位漏','评分／搜索漏'],oofrows,[1,1,1,1,1.6,1.1,1.6]),
 H('H.10 小池实测规模与裁剪成本推测'),
 P('表H-7使用4.6.8固定24篇的实际枚举计数。C为分离成分抽取后的池，D再增加边界与源组。枚举时间为开启tracemalloc后的本地槽位构造时间，内存记录只覆盖Python分配峰值，不是进程RSS或完整模型显存。最后两列假设每秒评分2000个完整对象，按组件数＋2×裁剪前槽位数计算，不含模型加载、文本编码、API调用和生成；该吞吐未校准为目标设备性能。'),
 T('表H-7 裁剪前后规模与评分成本（实测计数＋假设吞吐）',['语料／层','裁前均槽','裁后均槽','枚举均ms','估计均s','估计P95 s'],costrows,[1.5,1.2,1.2,1.2,1.2,1.3]),
 P('C到D使预计评分对象和枚举时间大幅增加，却没有增加正确关系入池数。2000对象／秒条件下，D层三套语料平均评分时间约3.06—3.48秒；若吞吐降到500，时间乘4，若达到10000则乘0.2。关系评分对象在裁剪前已经产生，最终4096补充槽位不能倒推准备时间。小样本P95仅是这8篇的经验分位数，不作为总体尾延迟保证。'),
 H('H.11 正式全类型候选的组合规模压力'),
 P('表H-8将4.2.5的宽松组合公式代入16、32、64个跨度，AAEC每跨度3类、CDCP每跨度5类、每槽2个正标签。这是忽略重叠互斥等限制的组合上界；上界超限只触发进一步资源检查，不能据此宣布实际枚举一定失败。评分时间继续假设2000对象／秒，对象存储假设每个标签对象512字节，均不是实测时长或内存。'),
 T('表H-8 全类型补充槽位的规模压力（上界与成本假设）',['语料','跨度','槽位上界','假设评分h','假设存储GiB'],boundrows,[1,1,2,1.5,1.6]),
 P('该推测说明CDCP的主要资源风险来自多源成员与类型的笛卡尔组合，远早于局部或全局求解。32跨度的宽松上界约9178万槽位，按假设吞吐需要约25.50小时；不能将小型Luna池数毫秒的求解结果外推为完整系统速度。工程上应流式计数、在实际合法槽位到达预检上限时停止，并优先比较由模型或原生分段提出的有限完整源组；新方案必须重测多源覆盖，不拆超边、不利用测试金标挑选。'),
 H('H.12 零增益与负增益情景的整数复算'),
 P('下表为H.5的效应假设生成6156条新的逐文档关系计数，保持各语料金标总量和三个种子，按目标精确率／召回率整数化。实际差值可能与输入差几个百分之一百分点。这里不使用Luna低分线性推算目标Qwen模型的F1：前者只提供候选和评分瓶颈的方向性依据，不能识别模型变强后的收益幅度。'),
 T('表H-9 关键效应的负、零与正情景（全部模拟）',['语料','效应','假设差值pp','整数复算差值pp'],stressrows,[1,1.8,2.1,2.3]),
 P('若成对学习为零或负增益，则保留关系感知数据构造但移除或降权成对项；若允许组件变化无收益，优先RelationOnly或单对象；若全局在真实规模下更快且误改相近，采用全局选择。当前Luna求解诊断已经出现“集合与单对象聚合相同、全局较快”的条件，因此预览不把局部优先写成固定结论。对于正式主表中的正增益，仅展示该假设成立时应如何报告与解释。'),
 P('新增模拟文件统一登记为SIMULATED_PREVIEW。four_cell_membership.json含46212条人工成员记录并与保留主表逐文档计数精确一致；oof_error_records.json含900条人工文档记录；stress_document_counts.json含6156条关系计数。external_comparator_counts.json只记录匿名比较。所有模拟均可从明确种子与脚本复算，真实训练次数仍为0。')]
text=text.rstrip()+'\n\n'+md(appendix);changes['append_blocks']=appendix
replace('不将合并汇总当作新增模型调用。','不将合并汇总当作新增模型调用。新增试验及模拟的身份、哈希和入口见D.13。')
for a,b in changes['global']:text=text.replace(a,b)
(R/'report_1011_v11_full.md').write_text(text)
(W/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
build=read(R/'_revision_1011_v10/docx_build.json');build['headings']=[[len(m.group(1))-1,m.group(2)] for m in re.finditer(r'(?m)^(#{2,4}) (.+)$',text)]
allblocks=[b for s in changes['sections_before'] for b in s['blocks']]+changes['append_blocks']
build['captions'] += [b['caption'] for b in allblocks if b['type']=='table'];build['captions'].sort(key=lambda s:text.index(s));assert len(build['captions'])==len(set(build['captions']))
build.update(source_sha256=sha(R/'report_1011_v11_full.md'),output=str(R/'report_1011_v11_full.docx'),retained_template_sha256=sha(R/'report_1011_v10_full.docx'),rendered=False)
(W/'docx_build.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
plan={'base_md_sha256':sha(R/'report_1011_v10_full.md'),'base_docx_sha256':sha(R/'report_1011_v10_full.docx'),'new_model_tasks':30,'new_target_training_runs':0,'new_solver_records':1536,'word_count_change':{'unit':'Unicode characters including Markdown','before':len(source),'after':len(text)},'new_tables':sum(b['type']=='table' for b in allblocks),'new_heading_count':sum(b['type']=='heading' for b in allblocks),'terminology':{'实测':'only saved actual model/solver outputs with stated denominator','模型复核':'same-family separated contexts, no human adjudication','模拟':'explicit integer count assumptions','成本推测':'measured counts times uncalibrated throughput or combinatorial bound'},'major_boundary':'full preview completed; training and full-system empirical claims remain unverified'}
(W/'editorial_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n');print(json.dumps(plan,ensure_ascii=False,indent=2))
