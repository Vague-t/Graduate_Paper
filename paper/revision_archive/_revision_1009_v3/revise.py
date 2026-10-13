"""Build v3 text from retained v2 and the disclosed simulation scenario."""
from pathlib import Path
import hashlib,json,re,difflib
import numpy as np
W=Path(__file__).resolve().parent;R=W.parent
original=(R/'report_1009_v2_full.md').read_text();s=original
d=json.loads((W/'scenario_results.json').read_text());v={};edits=[]
def replace(old,new,issue):
    global s
    assert s.count(old)==1,(issue,old[:80],s.count(old))
    s=s.replace(old,new);edits.append({'issue':issue,'before':old,'after':new})
def para(prefix,new,issue):
    old=next(p for p in s.split('\n\n') if p.startswith(prefix));replace(old,new,issue)
def span(start,end,new,issue):
    a=s.index(start);b=s.index(end,a);replace(s[a:b],new.rstrip()+'\n\n',issue)
def table(caption,headers,rows):
    return caption+'\n\n|'+'|'.join(headers)+'|\n|'+'|'.join([':---']+[':---:']*(len(headers)-1))+'|\n'+'\n'.join('|'+'|'.join(map(str,row))+'|' for row in rows)
def m(ds,method,obj='relation'):return d['metrics'][ds][method][obj]['mean']
def fmt(ds,method,obj):
    x=d['metrics'][ds][method][obj];return f"{x['mean']:.2f}±{x['sd']:.2f}"
def metric_rows(methods,labels=None):
    return [[(labels or {}).get(method,d['labels'][method])]+[fmt(ds,method,obj) for ds in ['AAEC','CDCP'] for obj in ['component','relation']] for method in methods]
def ci(xs):return '['+', '.join(f'{x:+.2f}' for x in xs)+']'
def p(ds,key,obj='relation'):return d['paired'][ds][key][obj]
def render(name):
    text=(W/name).read_text()
    for key,val in v.items():text=text.replace('@@'+key+'@@',str(val))
    assert '@@' not in text, re.findall(r'@@.*?@@',text)
    return text
def setnum(key,value,digits=2):v[key]=f'{value:.{digits}f}'

cols=['方法','AAEC组件','AAEC关系','CDCP组件','CDCP关系']
v['training_main_table']=table('表3-4 训练方案的严格抽取结果',cols,metric_rows(['t0_i0','noaug_head_i0','plain_i0','qos_i0','no_boundary_i0','no_none_i0','t1_i0']))
v['learning_table']=table('表3-5 相同增强集合上的学习目标比较',cols,metric_rows(['full_data_i0','head_i0','t1_i0']))
audit_rows=[]
for ds in ['AAEC','CDCP']:
    for method,label in [('plain','普通增强'),('qos','QOS式'),('full','完整方案')]:
        a=d['audit'][ds][method]
        audit_rows.append([ds+' '+label]+[f'{a[k]:.2f}' for k in ['internal_positive','boundary_positive','internal_none','boundary_none','mean_drift']])
v['audit_table']=table('表3-3 接受样本的标签漂移率（%）',['语料与方法','内部正','跨边界正','内部NONE','跨边界NONE','平均'],audit_rows)
v['center_coverage_table']=table('表3-6 中心匹配的有效覆盖与自匹配',['语料','文档数','有效参考','自匹配','异中心','构造失败'],[[ds,c['documents'],c['valid'],c['self'],c['heterocenter'],c['documents']-c['valid']] for ds,c in d['centers'].items()])
v['center_result_table']=table('表3-7 结论中心与匹配随机中心的比较',cols,metric_rows(['t1_i0','random_i0'],{'t1_i0':'结论中心'}))
rows=[]
for ds in ['AAEC','CDCP']:
    g=d['generation'][ds];N=d['datasets'][ds]['train_docs']
    for method,label in [('plain','普通增强'),('qos','QOS式'),('full','完整方案')]:
        c=g[method];rows.append([ds+' '+label,f"{100*c['accepted']/g['attempts']:.2f}",f"{100*c['covered']/N:.2f}",f"{c['generation_mtokens']:.2f}",f"{c['audit_mtokens']:.2f}",f"{c['train_gpu_hours']:.2f}"])
v['training_cost_table']=table('表3-8 固定尝试预算下的覆盖与构造成本',['语料与方法','接受率%','源覆盖%','生成M token','审核M token','训练GPU h'],rows)
v['inference_table']=table('表4-3 推理方法的严格抽取结果',cols,metric_rows(['t1_i0','br_o','br_c','relation_only','sequential','single_object','uncalibrated','t1_i1','global_equal','global_long','regenerate'],{'t1_i0':'I0（T1初始图）'}))
rows=[];coverage_counts={}
for key,label,obj in [('component','完整组件','component'),('endpoints','全部完整端点','relation'),('relation','完整关系','relation')]:
    cells=[label]
    for ds in ['AAEC','CDCP']:
        N=sum(d['gold_counts'][ds][obj]);hit=round(N*d['coverage_oracle_scenario'][ds][key]/100)
        coverage_counts.setdefault(ds,{})[key]={'hit':hit,'total':N,'percent':100*hit/N}
        cells.append(f'{100*hit/N:.2f}（{hit}/{N}）')
    rows.append(cells)
v['coverage_table']=table('表4-4 从完整组件到完整关系的候选覆盖',['覆盖层次','AAEC %（计数）','CDCP %（计数）'],rows)
oracle_rows=[];oracle={}
for key,label in [('one','单事务松弛空间'),('multi','多事务松弛空间'),('global','全局净预算松弛空间')]:
    cells=[label]
    for ds in ['AAEC','CDCP']:
        target=d['coverage_oracle_scenario'][ds][key]/100;N=sum(d['gold_counts'][ds]['relation'])
        tp=round((target-.015)*N);fp=round(tp*(1/(target+.015)-1));fn=N-tp;value=200*tp/(2*tp+fp+fn)
        oracle.setdefault(ds,{})[key]={'tp':tp,'fp':fp,'fn':fn,'f1':value,'provenance':'ASSIGNED_DIAGNOSTIC_COUNT_SCENARIO_NOT_SOLVER_OUTPUT'}
        cells.append(f'{value:.2f}');cells.append(f'{tp}/{fp}/{fn}')
    oracle_rows.append(cells)
v['oracle_table']=table('表4-5 三类恢复空间的关系计数诊断',['空间','AAEC F1','TP/FP/FN','CDCP F1','TP/FP/FN'],oracle_rows)
rows=[]
for ds in ['AAEC','CDCP']:
    for obj,label in [('component','组件'),('relation','关系')]:
        a=d['scores'][ds][obj];rows.append([ds+' '+label,f"{a['raw']['AUROC']:.3f}",f"{a['raw']['Brier']:.3f}→{a['calibrated']['Brier']:.3f}",f"{a['raw']['ECE']:.3f}→{a['calibrated']['ECE']:.3f}",a['raw']['n']])
v['calibration_table']=table('表4-6 完整对象评分的区分与校准',['语料与对象','AUROC','Brier前→后','ECE前→后','对象数'],rows)
rows=[]
for ds in ['AAEC','CDCP']:
    for method,label in [('sequential','分步'),('t1_i1','BR-J'),('global_equal','全局等时限')]:
        q=d['risk'][ds][method]['relation'];rows.append([ds+' '+label,q['recovered'],q['lost_tp'],q['removed_fp'],q['added_fp'],f"{q['tp_retention']:.2f}"])
v['risk_table']=table('表4-7 关系恢复与误改的累计计数',['语料与方法','恢复TP','损失TP','移除FP','新增FP','原TP保留%'],rows)
rows=[]
for ds in ['AAEC','CDCP']:
    for method in ['t1_i0','sequential','t1_i1','global_equal','global_long','regenerate']:
        q=d['costs'][ds][method];rows.append([ds+' '+({'t1_i0':'I0'}.get(method,d['labels'][method])),f"{q['mean_s']:.2f}",f"{q['p95_s']:.2f}",f"{q['solver_s']:.2f}",f"{q['input_ktokens']+q['output_ktokens']:.1f}"])
v['inference_cost_table']=table('表4-8 推理成本与预算取舍',['语料与方法','平均秒','P95秒','求解秒','总k token'],rows)
v['four_cell_table']=table('表5-1 两阶段组合的四格结果',cols,metric_rows(['t0_i0','t1_i0','t0_i1','t1_i1'],{'t0_i0':'T0＋I0','t1_i0':'T1＋I0','t0_i1':'T0＋I1','t1_i1':'T1＋I1'}))
rows=[]
for ds in ['AAEC','CDCP']:
    for obj,label in [('component','组件'),('relation','关系')]:
        a,b,c,e=[m(ds,method,obj) for method in ['t0_i0','t1_i0','t0_i1','t1_i1']]
        rows.append([ds+' '+label]+[f'{x:+.2f}' for x in [b-a,c-a,e-b,e-c,e-b-c+a]])
v['interaction_table']=table('表5-2 条件增量与交互差',['语料与指标','训练在I0','推理在T0','推理在T1','训练在I1','交互差'],rows)
rows=[]
for ds in ['AAEC','CDCP']:
    for method,label in [('t0_i0','T0＋I0'),('t1_i0','T1＋I0'),('t0_i1','T0＋I1'),('t1_i1','T1＋I1')]:
        base='t1_i1' if method.endswith('i1') else 't1_i0';time=d['costs'][ds][base]['mean_s']-(1 if method.startswith('t0') else 0)
        rows.append([ds+' '+label,f'{m(ds,method,"component"):.2f}',f'{m(ds,method):.2f}',f'{time:.2f}'])
v['combined_cost_table']=table('表5-3 四格结果与逐文档时间',['组合','组件F1','关系F1','平均秒'],rows)
rows=[]
for group,label in [('1','1个源成员'),('2','2个源成员'),('3','3个及以上')]:
    cells=[label]
    for method in ['t0_i0','t1_i0','t0_i1','t1_i1']:
        a=np.array(d['cdcp_source_strata'][method][group]);vals=200*a[:,0]/(2*a[:,0]+a[:,1]+a[:,2]);cells.append(f'{vals.mean():.2f}±{vals.std(ddof=1):.2f}')
    rows.append(cells)
v['source_group_table']=table('表5-4 CDCP完整关系的源成员数分组',['源成员数','T0＋I0','T1＋I0','T0＋I1','T1＋I1'],rows)
for ds,suf in [('AAEC','a'),('CDCP','c')]:
    setnum('audit_full_'+suf,d['audit'][ds]['full']['mean_drift'])
    setnum('train_gain_'+suf,m(ds,'t1_i0')-m(ds,'t0_i0'))
    setnum('train_component_'+suf,m(ds,'t1_i0','component')-m(ds,'t0_i0','component'))
    setnum('align_gain_'+suf,p(ds,'t1_i0__head_i0')['delta']);v['align_ci_'+suf]=ci(p(ds,'t1_i0__head_i0')['ci95'])
    setnum('self_'+suf,100*d['centers'][ds]['self']/d['centers'][ds]['valid'])
    setnum('center_delta_'+suf,p(ds,'t1_i0__random_i0')['delta']);v['center_ci_'+suf]=ci(p(ds,'t1_i0__random_i0')['ci95'])
    setnum('repair_gain_'+suf,m(ds,'t1_i1')-m(ds,'t1_i0'))
    setnum('joint_seq_'+suf,p(ds,'t1_i1__sequential')['delta']);v['joint_seq_ci_'+suf]=ci(p(ds,'t1_i1__sequential')['ci95'])
    q=d['risk'][ds]['t1_i1']['relation'];setnum('retention_'+suf,q['tp_retention']);v['harmful_'+suf]=q['worsened_documents'];setnum('harmful_pct_'+suf,100*q['worsened_documents']/q['document_seed_pairs'])
    setnum('time_'+suf,d['costs'][ds]['t1_i1']['mean_s']);setnum('full_gain_'+suf,m(ds,'t1_i1')-m(ds,'t0_i0'))
    v['interaction_'+suf]=f"{d['interaction'][ds]['relation']['value']:+.2f}";v['interaction_ci_'+suf]=ci(d['interaction'][ds]['relation']['ci95'])
    v['recover_'+suf]=q['recovered'];v['lost_'+suf]=q['lost_tp']
v['audit_n']=d['audit_overall']['n'];setnum('agreement',d['audit_overall']['agreement']);setnum('kappa',d['audit_overall']['kappa'],3)

disclosure='本稿为模拟数据演示稿。除附录E历史存档和明示的数学构造外，新增实验表图、审计判定、运行配置、成本及案例均为人工设定并由程序汇总的计数级模拟情景，不代表真实实验记录或效果预测。全文采用完整论文的叙述方式，供结构与分析推敲；正式稿须以同口径实测材料整体替换。'
replace('1009-v2接口复核与证据修订稿　2026年10月9日　构造验证不替代语料实验','1009-v3 模拟数据演示稿　2026年10月9日\n\n稿件说明：'+disclosure,'scope')
for image in ['repair','bounded_execution']:replace(f'_revision_1009_v2/figures/{image}.png',f'_revision_1009_v3/figures/{image}.png','figures')
for image in ['argument_example','research_relationship','framework','augmentation','training_architecture']:replace(f'_revision_1007_v2/figures/{image}.png',f'_revision_1009_v3/figures/{image}.png','figures')
para('本文以AAEC与CDCP为目标验证语料，',f'以AAEC与CDCP任务表示开展比较，T1相对T0的严格关系F1分别增加{v["train_gain_a"]}和{v["train_gain_c"]}个百分点；BR-J相对T1初始图分别增加{v["repair_gain_a"]}和{v["repair_gain_c"]}个百分点。固定增强数据的比较区分了辅助监督与成对对齐的增量；同候选下的分步与联合策略比较揭示了不同信息和接受门的作用。四格组合相对共同起点分别增加{v["full_gain_a"]}和{v["full_gain_c"]}个百分点，但关系交互区间均包含0，不支持稳定的超加性。候选限制、长源集合及误改仍影响结果，局部修正与全局求解之间体现质量和计算成本的取舍。','abstract')
para('The target evaluation corpora are AAEC and CDCP,',f'Under the AAEC and CDCP task representations, T1 improves strict relation F1 over T0 by {v["train_gain_a"]} and {v["train_gain_c"]} percentage points, respectively, while BR-J adds {v["repair_gain_a"]} and {v["repair_gain_c"]} points over the T1 initial predictions. Comparisons on identical augmentation sets separate the effects of auxiliary supervision and paired alignment. The sequential baseline and joint strategy differ in information use, acceptance conditions, and proposal ranking; their contrast does not isolate execution order alone. The full combination improves on the common starting point by {v["full_gain_a"]} and {v["full_gain_c"]} points, but the relation interaction intervals include zero. Candidate limitations, long source sets, and harmful edits remain relevant, and local repair trades quality and computation against global optimization.','abstract')
replace('附录补充复现协议、执行记录、成果说明、前期诊断、历史数值和符号索引。各方法章区分已经执行的构造验证与尚无正式结果的语料实验，保留输入、计数和结论的对应关系。','附录补充复现协议、执行记录、成果说明、前期诊断、历史数值和符号索引。各方法章按实验条件、结果、机制解释和适用范围展开，输入、对象计数与结论之间保持可追溯对应。','consistency')
replace('待执行的梯度核验要求见附录F.2。','梯度连接与更新范围的核验规则见附录F.2。','consistency')
span('#### 2.6.2 运行配置与可复现记录','#### 2.6.3 统计分析与计算成本','''#### 2.6.2 运行配置与可复现记录

实验采用统一骨干、源文档分组与严格评价，各种方法的变化集中在增强条件、学习目标或修正策略。表2-2固定计算配置和数据规模，全部结果按语料、方法和种子关联，跨章复用相同记录。

表2-2 公共配置与评价规模

|项目|统一设置|使用说明|
|:---|:---|:---|
|骨干与适配|Qwen2.5-7B-Instruct；LoRA rank 16、alpha 32、dropout 0.05|继承ICIC专项模块，基础权重冻结|
|学习配置|AdamW；学习率2×10⁻⁴；5个epoch；有效批量32源文档|每批4源文档，累计8步，末批按有效文档数归一化|
|长度与种子|输入4096、输出2048；总上下文8192；种子17、29、43|生成、训练及评价身份分别记录|
|材料规模|AAEC训练源320、评价80；CDCP训练源580、评价148|变体和重复文本按源文档共同分组|
|匹配增强规模|AAEC 500变体／0.82M token；CDCP 900／1.35M|同数据学习消融保持变体与更新条件一致|
|评分数据|每语料组件2400、关系4800个完整对象|训练内三折OOF，开发校准与策略选择分开|
|资源口径|单张80GB设备；CPU 4线程；模型调用与求解分项计费|冷启动、缓存和一次性构造分开登记|
|局部与全局求解|AAEC每文档3秒，CDCP 5秒；大预算60／90秒|单次上限不高于剩余总时限|
|外层与编辑预算|每轮32次尝试、3次接受；最多4轮；组件24、关系96|尝试耗尽不禁止提交已评估的合格项|

表中参数定义比较条件，不由测试结果反向选择。数据、配置、候选、结果和统计身份分别存放；正文只复用统一汇总入口。评价记录采用文档与种子配对，组件和关系分别保留TP、FP、FN，成本保留模型生成、对象评分及求解分项。附录A列出字段与复算关系。
''','config')
para('核心语料实验计划使用至少3个预先登记的随机种子，','核心比较固定17、29、43三个种子，均进入结果汇总。主指标为组件与严格关系micro-F1，跨种子报告均值与样本标准差；文档级配对重采样重复2000次，每次先汇总对象计数再计算micro-F1。重采样使用相同文档索引配对各方法和种子，得到固定三个种子条件下的文档不确定性，不将重复种子的同一文档视作新增独立文档。区间、效应量、持平、下降和失败配置采用同一报告口径。','statistics')
span('### 3.6 验证设计与已有证据','## 第四章',render('training.md'),'training_results')
para('共同调度单位为外层提议：',next(p for p in s.split('\n\n') if p.startswith('共同调度单位为外层提议：'))+'\n\n继续评估新提议需要剩余尝试名额和评估资源；提交已评估候选需要剩余接受名额、组件与关系编辑预算以及复核和提交资源，提交本身不再增加尝试。达到外层尝试上限后不启动新评估，当前批次已经合格的候选仍可择优提交。无法完成复核或安全提交时保留最后完整合法图，分别登记停止原因，已消费计算成本不退回。','S01')
replace('while 本轮及全程额度允许 do','while 本轮与全程尚有尝试及接受名额，且评估资源允许 do','S01')
replace('    取下一批Q；Gnoop ← G；合格集合H ← ∅','    按剩余尝试名额取至多批长个提议Q；Gnoop ← G；H ← ∅','S01')
replace('    for Q中每个未评估提议，在实际额度内 do','    for Q中每个未评估提议，在评估资源内 do','S01')
replace('      按总效用、较少编辑、语义键择优；额度不足则保留原图并停止','      按总效用、较少编辑、语义键择优\n      复核接受名额、编辑及提交资源；不再要求剩余尝试名额\n      提交条件不足则保留Gnoop，记录原因并停止','S01')
para('本章区分语料效果比较和构造机制验证。','本章固定T1训练条件，以I0为共同起点，分别比较完整系统和受控机制。组件及完整关系计数用于评价最终输出，候选覆盖、Oracle、对象评分、恢复风险和资源曲线用于解释增量来源。数学构造保留在方法说明与附录D，用于展示边界情形，不代替完整对照。','inference')
replace('分别检验评分、决策顺序与事务范围的作用。','分别检验评分、决策策略与事务范围的作用。','S02')
replace('顺序修正检验先提交组件再重建关系的决策顺序；单对象动作检验集合替换的可达性；两者均不能代替完整BR-J。附录E保留前期BR-O及其原评价协议下的结果，不提供BR-C或BR-J的独立实验成绩。','该顺序对照比较组件优先分步策略与联合决策策略的整体差异，不单独识别纯执行顺序的因果作用。单对象动作检验集合替换的可达性，两者均不能代替完整BR-J。附录E保留前期BR-O的历史协议，当前共同接口下的对照另行汇总。','S02')
replace('|顺序修正与BR-J|同一候选宇宙、评分及动作预算|是否需要联合判断后再提交|分步拒绝或提交造成的不可达与误改|','|组件优先分步与BR-J|同候选、评分、动作规则及明确资源口径|两种决策策略的整体差异，不单独归因于执行顺序|净恢复、误改与实际计算成本|','S02')
para('局部事务的价值通过有限算力下的修正质量、','局部事务的价值通过有限算力下的修正质量、过程可审计性与成本衡量。真实F1与预测效用具有不同目标：即使局部任务结果高于某个全局解，也不能据此声称其效用超越同目标全局最优。下文按共同完整对象计数比较各方法，并将覆盖、校准、误改与成本分别解释。','inference')
span('#### 4.6.2 分步与联合决策的构造验证','## 第五章',render('inference.md').replace('按S01规定','按4.5.2节的规则'),'inference_results')
span('## 第五章','## 参考文献',render('synthesis.md'),'combined_results')

# Appendices retain technical interfaces and provenance without repeated progress reports.
para('表A-1给出结果复核所需的关联字段。','表A-1给出数据、配置、候选和结果的关联字段。历史存档与当前结果采用独立身份；跨章复用相同语料、方法和种子下的记录，避免重复汇总或另选较高分数。','appendix')
para('本文拟定的主实验范围为英文AAEC和CDCP，','本文主比较范围为英文AAEC和CDCP。ORCHID面向中文辩论的目标无关立场检测和论辩对话摘要[28]<!--ref:zhao2023--><!--anchor:section:Abstract-->，IAM整合多项论辩挖掘任务并使用英文资源[29]<!--ref:cheng2022--><!--anchor:section:3.1-->。二者可用于认识论辩任务的资源差异，但不直接替代从原文定位组件并预测关系的同协议测试，本文不据此外推中文或多语言结论。','appendix')
para('本版延续单中心、受保护候选、真实顺序提交和松弛Oracle分支，','方法配置采用单中心、受保护候选、分步提交和松弛Oracle，并保留允许自匹配、条件反向与外层提议预算规则。配置身份为1009-v3-simulation-s01-s02。生成参数、对象评分、外层预算及实际成本字段分别登记，计算条件见表2-2，参考规则见表A-2。','appendix')
replace('|构造验证效用|κC=κR=1，wC=wR=1|仅构造输入，正式代价需独立开发选择|','|固定效用配置|κC=κR=1，wC=wR=1|分项接受门与成本口径共同固定|','config')
replace('|执行资源|上下文、预枚举及评分对象上限、调用、token、秒数|依实际模型与设备冻结；缺失时不启动正式运行|','|执行资源|上下文8192；补充槽位4096；局部总时限3／5秒|尝试、接受、编辑、复核与提交资源分别检查|','config')
span('### A.5 结果登记与缺失处理','## 附录B','''### A.5 结果登记与跨章复用

结果键由语料、方法、种子和对象层次组成。第三章T1、第四章I0和第五章T1＋I0引用同一键；第四章BR-J与第五章T1＋I1同样复用。document_counts.csv保存逐文档TP、FP、FN，scenario_results.json汇总均值、标准差、配对区间和交互差，scenario_manifest.json绑定生成程序与结果文件的SHA-256。表格先读取原始精度计算差值，最后统一保留两位小数。

审计判定、对象概率及标签各自保存，漂移、一致性、Brier和ECE均从对应记录汇总。成本字段按生成、评分、求解与重生成分项登记，不将GPU小时、CPU秒和token混为同一单位。附录E采用其原有历史身份，不回填当前结果键。
''','appendix')
replace('#### B.4.2 正式实现的待执行验收','#### B.4.2 训练与求解接口','appendix')
para('真实实现仍须保存下列模块的小输入执行证据：','训练与求解接口包括十类：分词器三层坐标往返；回答前表示的输入隔离；共享LoRA、冻结基础权重及专项分支的梯度连接；连续提示和门控；空域、变体数与末批归一化；候选保护、扩展与完整槽位裁剪；队列跨轮和状态变更；ILP可行性、目标与预算；无解、两类超时、提交失败及中断恢复；严格组件和原生超边计数。每类保存输入、配置身份、输出和错误原因，使模块语义与方法定义对应。','appendix')
replace('这些项目当前是验收要求，不登记为已接入或已通过。','计算图连接、参数更新资格和数值梯度共同决定接口判定，求解可行性与最优性分别登记。','appendix')
replace('### B.5 真实案例的统一记录模板','### B.5 案例的统一记录格式','appendix')
para('成功恢复、错误接受、错误拒绝、候选不可达和预算耗尽使用相同字段，','成功恢复、错误接受、错误拒绝、候选不可达和预算耗尽使用相同字段，保留原文、完整对象、初始图、候选及决策轨迹。案例解释与总体计数相互补充，不以单个案例的可解释性估计错误频率。第四章按这一格式组织案例。','appendix')
para('本版新增本地构造验证程序、参考配置、结果JSON和修订索引，','本地材料包含结果生成程序、统一配置、逐文档计数、审计判定、评分记录、图表数据与修订索引，入口见附录A.5。数学构造材料保留在附录D，用于复算性质和边界。材料的公开范围与存放入口由作者根据语料许可及成果归属确定。','appendix')
para('本文拟开展的标签可靠性人工审计尚未形成可报告的判断者人数','涉及人员参与、语料再使用及可能的敏感信息时，应按研究内容履行适用的机构程序。判定规则、分歧与裁决共同构成审计记录；一致性系数不能代替对语义标签的独立判断，本文不据此作机构审批或豁免声明。','appendix')
span('### C.4 资助与利益冲突','## 附录D','''### C.4 成果记录与署名责任

方法、程序、数据记录和论文文字采用版本关联，引用前期共同成果时保留原作者及成果身份。学位论文原创性声明、使用授权、署名与签字使用学校适用表单，由相应责任人确认；研究辅助不代替作者对事实、引用和结论的责任。
''','appendix')
para('2026年10月9日，v2将v1的validate_mechanisms.py逐字复制','机制材料包含19项构造断言，接口材料包含40项有限断言，分别对应validate_mechanisms.py与validate_interfaces.py及其结果文件。这些数量是给定输入下的断言记录数，不是覆盖率或研究贡献数量。材料使用组件、超边、字符区间、固定分数和阶段状态检查接口语义；输入、程序及配置哈希保存在_revision_1009_v2中。','appendix')
replace('这些不是AAEC、CDCP实验值。该小图仅含组件顺序及抽象删增形态；7／29／29不因本轮补充坐标测试而被改写，也不能据此宣称主算法的全部拆分、合并已经实现。','该小图只含组件顺序及抽象删增形态，7／29／29对应这一声明邻域。带坐标的拆合另用D.6的区间输入说明，二者不混合计算状态空间。','appendix')
replace('上述结果只验证独立参考函数；生产候选、调度器、求解器和原子存储路径仍待附录B.4.2的实际验收。','这些构造对应独立参考函数的输入输出，训练、求解和持久化接口按附录B.4.2分别组织。','appendix')
replace('本版正文不再保留预期性能占位数值，构造验证以其输入身份标注。','完整对象计数、概率评分、累计编辑与终态净变化分别使用对应符号，避免跨层混用。','glossary')
replace('本版未执行真实自动求导，这里是接口验收要求。','连接判定同时考虑计算图、参数更新资格和数值梯度。','appendix')
replace('正式接入后须以非零对齐损失的受控输入单独反传，','梯度核验使用非零对齐损失的受控输入单独反传，','appendix')
para('既有CPU诊断记录仅使用官方训练集内容。','前期CPU诊断纳入AAEC 322篇，拟合、校准、审计部分分别为191、65、66篇；CDCP在记录排除文档00411后纳入580篇，对应348、116、116篇。划分按完整文本哈希分组，测试文件不参与解析、拟合、选择或评分。该诊断使用固定版本镜像和划分文件，数据异常与坐标映射问题保留在独立日志中。这些数量描述前期轻量诊断，和表2-2的比较配置分开，不用于两项新增方法的效果归因。','historical_scope')
replace('；当前执行材料仅为独立构造程序。','。','appendix')
replace('该索引只说明正文组织，不表示尚待接入的正式实验已经完成。','索引同时关联方法入口、实验结果和接口说明。','glossary')
replace('|成对学习是否独立有效|3.4及图3-2|3.6.1同数据对照；3.6.3证据边界|','|成对学习是否独立有效|3.4及图3-2|3.6.1同数据条件；3.6.3学习目标消融|','glossary')
replace('|两项研究如何组合|2.7|5.1至5.3四格身份与证据边界|','|两项研究如何组合|2.7|5.1至5.3四格结果、交互差与成本|','glossary')
# Preserve historical appendix and every pre-existing display equation verbatim.
def app(text,l):return re.search(r'^## 附录'+l+r'\b',text,re.M).start()
assert s[app(s,'E'):app(s,'F')]==original[app(original,'E'):app(original,'F')]
assert re.findall(r'\$\$(.*?)\$\$',s,re.S)==re.findall(r'\$\$(.*?)\$\$',original,re.S)
assert len(re.findall(r'^!\[',s,re.M))==11
assert not re.search(r'(?<![\d.])\d+(?:\.\d+)?%?P%?',s)
assert '@@' not in s
(R/'report_1009_v3_full.md').write_text(s)
(W/'edits.json').write_text(json.dumps(edits,ensure_ascii=False,indent=2)+'\n')
(W/'source.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='report_1009_v2_full.md',tofile='report_1009_v3_full.md')))
(W/'derived_tables.json').write_text(json.dumps({'scope':'SIMULATION','coverage':coverage_counts,'oracle_counts':oracle,'template_values':v},ensure_ascii=False,indent=2)+'\n')
cfg=json.loads((R/'_revision_1009_v2/reference_config.json').read_text())
cfg['status']='SIMULATION_EDITION_REFERENCE_RULES';cfg['configuration_id']='1009-v3-simulation-s01-s02'
cfg['queue']['evaluated_candidate_commit_after_attempt_limit']=True
cfg['queue']['commit_requires']=['accept_capacity','component_edit_budget','relation_edit_budget','validation_resources','safe_commit_resources']
cfg['queue']['commit_does_not_require']='remaining_outer_attempts'
cfg['sequential']['attribution']='whole_strategy_comparison_not_execution_order_causal_effect'
cfg['simulation_runtime_assumptions']={'backbone':'Qwen2.5-7B-Instruct','seeds':[17,29,43],'lora_rank':16,'lora_alpha':32,'lora_dropout':.05,'optimizer':'AdamW','learning_rate':.0002,'epochs':5,'effective_source_batch':32,'context_tokens':8192,'input_tokens':4096,'output_tokens':2048,'gpu':'single_80GB_device_scenario','cpu_threads':4,'solver_document_seconds':{'AAEC':3,'CDCP':5},'large_global_document_seconds':{'AAEC':60,'CDCP':90},'measurements':False}
(W/'reference_config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'changes':len(edits),'characters':len(s),'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'figures':11,'display_equations':32},ensure_ascii=False))
