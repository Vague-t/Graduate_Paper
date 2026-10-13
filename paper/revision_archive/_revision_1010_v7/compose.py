"""Synchronize explicitly hypothetical numbers in Markdown and a retained DOCX.

This script makes no empirical claims and performs no model or solver run.
The actual package patch is performed by patch_docx.py after figure export.
"""
from pathlib import Path
import hashlib,json,re,shutil
import numpy as np
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v6'
source=(R/'report_1010_v6_full.md').read_text(); original=source
r=json.loads((W/'scenario_results.json').read_text())
ops=[];tables={};insertions=[]
DS=['AAEC','CDCP'];OB=['component','relation']
def mean(ds,m,o='relation'):return r['metrics'][ds][m][o]['mean']
def delta(ds,a,b,o='relation'):return mean(ds,a,o)-mean(ds,b,o)
def fmt(x):return f'{x:.2f}'
def ci(ds,pair,o='relation'):
 lo,hi=r['paired'][ds][pair][o]['ci95'];return f'[{lo:+.2f}, {hi:+.2f}]'
def diffpair(a,b):return '和'.join(fmt(delta(ds,a,b)) for ds in DS)
def ms(ds,m,o):
 v=r['metrics'][ds][m][o];return f"{v['mean']:.2f}±{v['sd']:.2f}"
def replace(old,new):
 global source
 assert source.count(old)==1,(old[:70],source.count(old))
 source=source.replace(old,new);ops.append({'old':old,'new':new})
def para(prefix,new):
 line=next(x for x in source.splitlines() if x.startswith(prefix));replace(line,new)
def append_after(prefix,paragraphs):
 global source
 line=next(x for x in source.splitlines() if x.startswith(prefix))
 source=source.replace(line,line+'\n\n'+'\n\n'.join(paragraphs),1)
 insertions.append({'anchor':line,'paragraphs':paragraphs})
def table(num,new_rows):
 global source
 pat=rf'(^表{re.escape(num)} [^\n]+\n\n)(\|[^\n]+\n(?:\|[^\n]+\n)+)'
 mt=re.search(pat,source,re.M);assert mt,num
 rows=[x.strip('|').split('|') for x in mt[2].strip().splitlines()]
 oldrows=rows[2:];assert len(oldrows)==len(new_rows),(num,len(oldrows),len(new_rows))
 newtext='\n'.join('|'+ '|'.join(row)+'|' for row in rows[:2]+new_rows)+'\n'
 source=source[:mt.start(2)]+newtext+source[mt.end(2):]
 tables['表'+num]={'old':oldrows,'new':new_rows}
def metrics_table(num,pairs):
 table(num,[[label]+[ms(ds,m,o) for ds in DS for o in OB] for label,m in pairs])

metrics_table('3-5',[('T0','t0_i0'),('无增强＋头监督','noaug_head_i0'),('普通增强','plain_i0'),('QOS式适配','qos_i0'),('去跨边界正关系','no_boundary_i0'),('去NONE检查','no_none_i0'),('T1完整训练','t1_i0')])
metrics_table('3-6',[('完整增强＋基础损失','full_data_i0'),('完整增强＋头监督','head_i0'),('T1完整训练','t1_i0')])
metrics_table('3-8',[('结论中心','t1_i0'),('匹配随机中心','random_i0')])
metrics_table('4-3',[('I0（T1初始图）','t1_i0'),('BR-O','br_o'),('BR-C','br_c'),('RelationOnly','relation_only'),('组件优先分步','sequential'),('单对象动作','single_object'),('未校准评分','uncalibrated'),('BR-J','t1_i1'),('全局ILP等求解预算','global_equal'),('全局ILP大预算','global_long'),('等token额度重生成','regenerate')])
metrics_table('5-1',[('T0＋I0','t0_i0'),('T1＋I0','t1_i0'),('T0＋I1','t0_i1'),('T1＋I1','t1_i1')])
rows=[]
for ds in DS:
 for label,m in [('分步','sequential'),('BR-J','t1_i1'),('全局等求解预算','global_equal')]:
  z=r['risk'][ds][m]['relation'];rows.append([ds+' '+label]+[str(z[k]) for k in ['recovered','lost_tp','removed_fp','added_fp']]+[fmt(z['tp_retention'])])
table('4-7',rows)
rows=[]
net=[]
for ds in DS:
 for o,label in zip(OB,['组件','关系']):
  vals=[delta(ds,a,b,o) for a,b in [('t1_i0','t0_i0'),('t0_i1','t0_i0'),('t1_i1','t1_i0'),('t1_i1','t0_i1')]]+[r['interaction'][ds][o]['value']]
  rows.append([ds+' '+label]+[f'{v:+.2f}' for v in vals])
table('5-2',rows)
rows=[]
for ds in DS:
 for o,label in zip(OB,['组件','关系']):
  fields={}
  for key,a,b in [('training','t1_i0','t0_i0'),('repair_t0','t0_i1','t0_i0'),('repair_t1','t1_i1','t1_i0')]:
   ac=np.sum(r['metrics'][ds][a][o]['counts'],axis=0);bc=np.sum(r['metrics'][ds][b][o]['counts'],axis=0)
   diff=(ac-bc).tolist();fields[key]={'tp':diff[0],'fp':diff[1],'fn':diff[2]}
  net.append({'dataset':ds,'object':o,**fields})
  rows.append([ds+' '+label]+[f"{fields[k]['tp']:+d}／{fields[k]['fp']:+d}" for k in ['training','repair_t0','repair_t1']])
table('5-3',rows)
rows=[]
for group,gold in [('1',556),('2',252),('3',121)]:
 vals=[]
 for method in ['t0_i0','t1_i0','t0_i1','t1_i1']:
  c=np.array(r['cdcp_source_strata'][method][group]);v=200*c[:,0]/(2*c[:,0]+c[:,1]+c[:,2]);vals.append(f'{v.mean():.2f}±{v.std(ddof=1):.2f}')
 rows.append([f'{group}个／{gold}']+vals)
table('5-4',rows+[['超过3个／0','—','—','—','—']])
rows=[]
for label,m,times in [('T0＋I0','t0_i0',[0.,0.]),('T1＋I0','t1_i0',[1.,1.]),('T0＋I1','t0_i1',[14.,22.16]),('T1＋I1','t1_i1',[15.,23.16])]:
 rows.append([label]+[v for ds,t in zip(DS,times) for v in [f'{delta(ds,m,"t0_i0"):+.2f}',fmt(t)]])
table('5-5',rows)

disclosure='稿件说明：本稿为估算演示版。正文主结果由明确假设的目标值生成计数，并统一复算表图、差值与区间，不代表真实实验记录或经验证的效果预测。附录D.2—D.3引用已保存的CPU轻量诊断，附录E保留前期存档，两者均不替代新增方法实验。附录H.6—H.8保留独立旧情景；本版假设与压力条件见H.5。正式稿须以同口径实测材料整体替换。'
para('稿件说明：',disclosure)
abstract=next(x for x in source.splitlines() if x.startswith('本版使用AAEC'))
new=abstract.replace('本版使用AAEC与CDCP规模的人工计数演示评价，不代表真实模型实验。','本版采用AAEC与CDCP规模的假设计数形成估算演示，不代表真实模型实验。')
new=new.replace('1.92／1.88','／'.join(fmt(delta(ds,'t1_i0','head_i0')) for ds in DS)).replace('3.59／4.39','／'.join(fmt(delta(ds,'t1_i1','relation_only')) for ds in DS))
replace(abstract,new)
eng=next(x for x in source.splitlines() if x.startswith('Artificial counts at'))
new=eng.replace('Artificial counts at AAEC and CDCP scales illustrate evaluation rather than empirical model performance.','Explicitly assumed counts at AAEC and CDCP scales illustrate hypothetical outcomes, not empirical model performance or validated forecasts.')
new=new.replace('1.92/1.88','/'.join(fmt(delta(ds,'t1_i0','head_i0')) for ds in DS)).replace('3.59/4.39','/'.join(fmt(delta(ds,'t1_i1','relation_only')) for ds in DS));replace(eng,new)
para('T1相对T0的严格关系',f'T1相对T0的严格关系F1分别增加{diffpair("t1_i0","t0_i0")}个百分点，这一总差值包含数据构造、头监督和成对学习。T-B中QOS式适配与完整增强均采用基础损失：对照表3-6首行，AAEC为{fmt(mean("AAEC","qos_i0"))}对{fmt(mean("AAEC","full_data_i0"))}，CDCP为{fmt(mean("CDCP","qos_i0"))}对{fmt(mean("CDCP","full_data_i0"))}，差值为{diffpair("full_data_i0","qos_i0")}个百分点。该差值同时包含文本、接受源分布与源重加权，故解释为数据构造整体效应。过滤消融固定生成池与学习配置，仍可能改变接受覆盖；其情景差值不单独证明某项检查通过表达变化产生收益。')
para('表3-6的三行使用',f'表3-6的三行使用完全相同的增强文本、来源权重和更新条件。增加头监督先建立组件与完整关系因素的输入表示；加入成对对齐后，AAEC与CDCP的关系F1分别再增加{diffpair("t1_i0","head_i0")}个百分点，情景文档配对95%区间为{ci("AAEC","t1_i0__head_i0")}和{ci("CDCP","t1_i0__head_i0")}。完整结果同时包含数据构造、辅助监督和成对目标三部分，不能将总增量全部归给对齐项。区间只反映既定计数模型内的重采样变化，不是实际方法效应的置信区间。')
para('结论中心相对匹配随机',f'结论中心相对匹配随机中心的关系差值为AAEC {fmt(delta("AAEC","t1_i0","random_i0"))}、CDCP {fmt(delta("CDCP","t1_i0","random_i0"))}个百分点，情景配对95%区间分别为{ci("AAEC","t1_i0__random_i0")}、{ci("CDCP","t1_i0__random_i0")}。区间均含0；即使在这一设定中，也不能把完整方案增量归因于中心角色。')
para('BR-J相对I0在',f'BR-J相对I0在AAEC和CDCP上的关系F1分别增加{diffpair("t1_i1","t1_i0")}个百分点。相对固定组件RelationOnly，高{diffpair("t1_i1","relation_only")}个百分点，情景配对95%区间为{ci("AAEC","t1_i1__relation_only")}、{ci("CDCP","t1_i1__relation_only")}；相对单对象动作，高{diffpair("t1_i1","single_object")}个百分点，区间为{ci("AAEC","t1_i1__single_object")}、{ci("CDCP","t1_i1__single_object")}。前一比较检验组件可变性，后一比较检验集合表达，均须结合编辑数量、误改及成本解释。这些区间由假设计数重采样得到，不确认真实端点错误上的收益，也不证明每项机制均有必要。')
para('作为共同决策的补充',f'作为共同决策的补充比较，BR-J相对于组件优先分步策略的关系增量为{diffpair("t1_i1","sequential")}个百分点，情景文档配对95%区间分别为{ci("AAEC","t1_i1__sequential")}和{ci("CDCP","t1_i1__sequential")}。这些结果演示两种策略整体差异的报告方式。两者同时改变信息使用、接受条件和批内排序，不能单独识别纯执行顺序的因果作用。')
a,c=[r['risk'][ds]['t1_i1']['relation'] for ds in DS]
para('表4-7累加三种子',f'表4-7累加三个情景种子的关系对象变化，恢复为新增真阳性，损失为初始真阳性消失；FP移除与新增分别计数。BR-J在AAEC和CDCP保留了{a["tp_retention"]:.2f}%和{c["tp_retention"]:.2f}%的初始关系真阳性。尽管总体关系F1提高，仍有{a["worsened_documents"]}和{c["worsened_documents"]}个文档与种子配对的关系F1下降，分别占{100*a["worsened_documents"]/a["document_seed_pairs"]:.2f}%和{100*c["worsened_documents"]/c["document_seed_pairs"]:.2f}%。因此，分项代理门不保证每篇文档的真实指标非下降；此处比例同样只是情景生成结果。')
para('BR-J相对等求解预算',f'BR-J相对等求解预算全局ILP节省的平均总时间为4.19%和4.73%，关系F1按未舍入值低{diffpair("global_equal","t1_i1")}个百分点。局部与全局的质量差异和TP保留须分别查看表4-3及表4-7，不能预设局部更安全。BR-J求解仅占总时间的5.00%和5.67%，主要成本仍在生成与评分。上述数值是设定成本下的算术关系，不支持突出的效率优势；采用判断须按附录H.3实测准备、求解、失败与尾延迟。')
replace('完整组合相对T0＋I0的关系增量为13.31和13.92个百分点。',f'完整组合相对T0＋I0的关系增量为{diffpair("t1_i1","t0_i0")}个百分点。')
it=[r['interaction'][ds]['relation'] for ds in DS]
para('AAEC关系交互差为',f'AAEC关系交互差为{it[0]["value"]:+.2f}，情景配对95%区间为[{it[0]["ci95"][0]:+.2f}, {it[0]["ci95"][1]:+.2f}]；CDCP为{it[1]["value"]:+.2f}，区间为[{it[1]["ci95"][0]:+.2f}, {it[1]["ci95"][1]:+.2f}]。两者均包含0，因此组合增量与稳定超加性应分别判断。组件交互也仅描述条件总分的变化，不能据此确定两阶段改变的是哪些对象。')
an,cn=[next(x for x in net if x['dataset']==ds and x['object']=='relation') for ds in DS]
para('AAEC在T1下修正的关系',f'AAEC在T1下修正的关系净TP增加{an["repair_t1"]["tp"]}，T0下为{an["repair_t0"]["tp"]}；CDCP相应为{cn["repair_t1"]["tp"]}与{cn["repair_t0"]["tp"]}。训练后剩余修正空间的变化须按语料分别解释。表4-7中BR-J的恢复减损失分别为{a["recovered"]}−{a["lost_tp"]}、{c["recovered"]}−{c["lost_tp"]}，恰好对应上述净增量；图4-3并列保留两类数量。')
replace('附录H.8在保持四格成绩及T1到组合风险计数不变时构造不同重叠，说明这一不可识别性。','附录H.8沿用旧情景的四格成绩及风险计数构造不同重叠，说明这一不可识别性；其具体范围不移用于本版主表。')
para('在这一条件下，T1＋I0',f'在这一条件下，AAEC的T1＋I0关系F1比T0＋I1高{delta("AAEC","t1_i0","t0_i1"):.2f}个百分点，在线平均时间少13.00秒；CDCP则低{abs(delta("CDCP","t1_i0","t0_i1")):.2f}个百分点，在线时间少21.16秒。后者在该情景中呈现近乎相同的质量与不同的时间，不能沿用旧版“两语料质量均更高”的结论。该比较以训练检查点已经可用为前提，不能直接回答重训或训练摊销条件下的总体选择。')
para('在T1上增加I1，',f'在T1上增加I1，关系F1的情景增量为{diffpair("t1_i1","t1_i0")}个百分点，在线时间增加14.00秒和22.16秒，并仍可能误改。是否采用组合应结合目标错误、质量收益与在线代价判断；实际部署还须检查尾延迟、失败及局部和全局求解取舍。')

# Independent observed CPU diagnostics; compute every stated value from saved counts.
diag={ds:json.loads((R/f'research_0920/results/{ds.lower()}_summary.json').read_text()) for ds in DS}
aud=json.loads((R/'research_0920/results/posthoc_integrity_audit.json').read_text())
for ds,s in diag.items():
 p=s['calibrated_policy']
 for key,tag in [('before_counts','before_micro_f1'),('after_counts','after_micro_f1')]:
  t,f,n=p[key];assert abs(2*t/(2*t+f+n)-p[tag])<1e-12
def pp(ds,key):return 100*diag[ds]['calibrated_policy'][key]
dp1=f'已保存的CPU预实验中，AAEC组件TP／FP／FN由340／1349／646变为340／1283／646，严格typed component F1由{pp("AAEC","before_micro_f1"):.2f}升至{pp("AAEC","after_micro_f1"):.2f}；CDCP由86／2708／637变为86／2593／637，F1由{pp("CDCP","before_micro_f1"):.2f}升至{pp("CDCP","after_micro_f1"):.2f}。增量分别为{pp("AAEC","delta_micro_f1"):.2f}和{pp("CDCP","delta_micro_f1"):.2f}个百分点。两语料分别接受66和115次删除，TP没有增加，因此不能将其解释为遗漏组件恢复或闭合修正效果。'
dp2='在每文档最多增加128个跨度候选的条件下，AAEC精确跨度覆盖为945／986（95.84%），CDCP为700／723（96.82%）；原生关系全部端点覆盖分别为597／627（95.22%）和189／200（94.50%）。前者不要求类型正确，后者也不代表完整关系已经生成或可被接受，故均不能替换表4-4的严格完整对象覆盖。该预实验使用官方训练部分及单一seed=920；关系评分另给定金标端点且限单前提，不能填入本文的端到端关系主表。'
dp3='本版从既存运行清单、逐文档候选预测和结果汇总读取上述数值，并从TP／FP／FN复算F1；没有重新训练。已有文本分组重采样结果中，主策略组件F1增量的95%区间为AAEC [+0.58, +0.71]、CDCP [+0.12, +0.22]个百分点。它们属于该次轻量诊断，不是三个情景种子的标准差，也不支持新增方法的效应大小。运行清单记录完成耗时29.03秒，该值不是本文系统的逐文档推理延迟。'
append_after('### D.3 诊断的启示与限制',[dp1,dp2,dp3])

assumption_text=[
 '本版主结果的估算原则是固定v6的T0情景起点、样本规模、随机扰动及成本口径，缩小假设训练和推理增量，再从整数TP、FP、FN重算全部主表。参数并未根据CPU诊断、历史论文或目标实验拟合；“增量较小”只表示相对旧演示的设定更克制，不意味着更接近实际结果。原始目标是生成器的平衡精确率／召回率中心，经过偏移和整数化后，与表中均值略有差别。',
 '具体假设中，AAEC／CDCP的关系F1中心依次为：T0 53.30／48.10，完整增强基础损失55.70／50.50，加头监督56.60／51.30，T1 57.80／52.50，RelationOnly 59.60／54.80，单对象60.70／55.90，BR-J 61.90／57.40，等求解预算全局62.30／57.90。固定组件对照严格复用T1组件计数；全局略高的排序是情景假设，不由可行域包含关系推出F1优越性。',
 '零增益和负增益也属于需要保留的备选条件。用于读表的压力假设为：成对学习相对加头监督的关系增量分别取−0.50、0.00、+1.20个百分点；允许组件变化相对RelationOnly取−0.50、0.00、+2.30；局部减全局取−1.50、−0.50、+0.50。它们逐项替换一个效应假设，尚未生成新的逐文档记录或计算置信区间，不能称为已完成的敏感性实验。零或负增益出现时，相应机制的采用结论须收缩，而不能保留正增益情景的文字。',
 '成本同样依赖假设。若只将共同对象评分时间乘以0.5、1、2，其他项保持表4-8设定，AAEC局部相对等求解预算全局的总时间节省率依次为5.15%、4.19%、3.06%，CDCP为5.96%、4.73%、3.34%。这只是总时间公式的重算，不包含评分误差、批量吞吐或求解轨迹变化；评分成本占比越大，单独加速求解的总收益越小。'
]
append_after('### H.5 模拟结果后的实证替换顺序',assumption_text)
replace('本节只演示怎样并列阅读变化、漂移与覆盖，不检验真实语义审核器。材料沿用SIM-1010-V4：','本节只演示怎样并列阅读变化、漂移与覆盖，不检验真实语义审核器。材料独立沿用SIM-1010-V4旧记录，与本版主表无训练绑定：')
append_after('### H.7 预算条件的假设推演',['本节数值及图H-1独立保留SIM-1010-V4旧成本与质量轨迹，终点沿用v6的情景主成绩；它们未改为v7主表的预算实验。为保留可追溯的条件示例，本节不与新版表4-3或表5-1拼接，也不用于估计新版效果。'])
para('既有object_memberships.json为','既有旧情景对象记录为684个文档种子记录赋予抽象关系键，匹配v6四格未分组TP、FP、FN及T1到组合的风险总量，并不匹配v7主表。坐标、类型与端点均由程序构造，未重建完整组件预测图，也未约束源成员数分组；该文件只保留作非唯一性示例，不承担关于两阶段互补性的研究发现。')
replace('本版核验程序独立构造上述最小与最大交集，逐项检查计数及风险不变；','旧版核验程序独立构造上述最小与最大交集，逐项检查旧计数及风险不变；')

global_edits=[('1010-v6 模拟数据演示稿','1010-v7 估算演示版'),('1010-v6','1010-v7'),('_revision_1010_v6/figures/','_revision_1010_v7/figures/'),('人工情景','估算情景')]
for old,new in global_edits:source=source.replace(old,new)
(R/'report_1010_v7_full.md').write_text(source)
(W/'changes.json').write_text(json.dumps({'text_replacements':ops,'tables':tables,'insertions':insertions,'global':global_edits},ensure_ascii=False,indent=2))
derived=json.loads((W/'derived_tables.json').read_text());derived['net_errors']=net
derived['template_values']={key:re.search(rf'^{re.escape(key)} [^\n]+\n\n(?:\|[^\n]+\n)+',source,re.M).group(0).strip() for key in tables}
(W/'derived_tables.json').write_text(json.dumps(derived,ensure_ascii=False,indent=2))
legacy=W/'legacy_supplement';legacy.mkdir(exist_ok=True)
names=['supplement_results.json','supplement_manifest.json','generate_supplement.py']+list(json.loads((P/'supplement_manifest.json').read_text())['files'])
for name in set(names):
 if (W/name).exists():shutil.move(str(W/name),legacy/name)
for name in ['document_counts.csv','scenario_results.json']:
 shutil.copy2(P/name,legacy/name)
print(json.dumps({'text_replacements':len(ops),'updated_tables':list(tables),'inserted_paragraphs':sum(len(x['paragraphs']) for x in insertions),'new_source_sha256':hashlib.sha256(source.encode()).hexdigest()},ensure_ascii=False))
