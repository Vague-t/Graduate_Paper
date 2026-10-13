"""Add observed diagnostic statistics to a preserved v7 manuscript."""
from pathlib import Path
import hashlib
import json
import re
import shutil

W=Path(__file__).resolve().parent
R=W.parent
P=R/'_revision_1010_v7'
old=(R/'report_1010_v7_full.md').read_text()
stats=json.loads((W/'diagnostic_supplement.json').read_text())
data=stats['data']
blocks=[]
def paragraph(text):
    blocks.append({'type':'paragraph','text':text})
def table(caption,headers,rows,widths):
    blocks.append({'type':'table','caption':caption,'headers':headers,'rows':[[str(x) for x in r] for r in rows],'widths':widths})
def pct(x):
    return f'{x:.2f}'
def ci(p):
    a,b=p['group_bootstrap95_pp']
    return f'[{a:+.2f}, {b:+.2f}]'

paragraph('本节补充统计来自2026年9月20日已经完成的CPU轻量诊断。此次读取原始语料压缩包、固定划分、182篇审计文档的候选预测及38928条编辑提议，核对文本哈希后复算；未重新拟合模型、调用目标大模型或执行ILP。AAEC的66篇文档对应64个全文哈希组，CDCP的116篇对应116组。下列观察仅描述该次弱模型运行，不并入第三至第五章的估算主表，也不替代目标模型诊断。')
paragraph('初始组件先匹配跨度与类型均正确的对象，再匹配同跨度异类型对象；剩余对象按token交并比不低于0.5、交并比降序及坐标类型键破同分进行一对一贪心配对。该事后描述规则沿用H.1的诊断口径，不改变严格评价。边界配对又按类型是否相同分开；未配对项只表示在本规则下未匹配，不能直接认定为独立的遗漏或多检成因。')
labels=[('严格跨度与类型命中','strict_typed'),('同跨度异类型配对','same_span_wrong_type'),('边界差异且类型相同','boundary_only'),('边界与类型均有差异','boundary_and_type'),('未配对金标组件','unmatched_gold'),('未配对预测组件','unmatched_prediction')]
rows=[[label,data['aaec']['component_decomposition'][key],data['cdcp']['component_decomposition'][key]] for label,key in labels]
rows += [['金标组件总数',986,723],['初始预测组件总数',1689,2794]]
table('表D-1 初始组件的错误配对分解（既存CPU诊断）',['计数项目','AAEC','CDCP'],rows,[3.5,1,1])
paragraph('表D-1中，严格命中、三类错误配对及未配对金标之和等于金标总数；将末项换成未配对预测，则等于预测总数。每个错误配对同时贡献一个FP和一个FN，不能把两者当作两次独立事件。由此还原的AAEC计数为TP=340、FP=1349、FN=646，CDCP为86、2708、637。')
paragraph('按原生金标关系检查初始端点，AAEC的627条关系中，全部端点跨度和类型正确的有43条（6.86%），跨度齐全但至少一个类型错误的有116条（18.50%），至少一个跨度缺失的有468条（74.64%）；CDCP的200条对应4条（2.00%）、1条（0.50%）、195条（97.50%）。CDCP其中19条为多前提关系。这一互斥分组仅检查端点条件，没有判断关系标签和方向是否预测正确；低正确率也反映弱模型的过度分割，不能外推为目标LLM的错误比例。')
paragraph('候选覆盖按保存的跨度排序依次截取0、64、128、256、512个补充位置，与初始跨度去重合并。精确跨度覆盖的分母为986／723个金标组件，全部端点跨度覆盖的分母为627／200条原生关系；两者均不要求候选类型或关系标签正确。候选均值和P95按文档计算，有向对均值逐文档按n(n−1)计算后取均值，表示未施加类型及合法性约束的二元组合规模，不是实际评分对象数或实测耗时。')
rows=[]
for item in stats['coverage']:
    rows.append([item['dataset'].upper(),item['extra_budget'],pct(item['span_recall_pct']),pct(item['endpoint_span_recall_pct']),f"{item['mean_candidates']:.2f}／{item['p95_candidates']:.2f}",f"{item['mean_directed_pair_combinations']:.0f}"])
table('表D-2 补充跨度预算与候选覆盖（既存CPU诊断）',['语料','补充上限','跨度覆盖%','端点覆盖%','候选均值／P95','有向对均值'],rows,[.75,.8,1,1,1.55,1.05])
paragraph('从128增至512个补充跨度，AAEC覆盖增加28个组件，CDCP增加15个；对应二元有向组合均值约由2.35万／2.32万升至28.85万／28.02万。该统计展示覆盖与组合规模之间的取舍，但没有测量这些组合的实际枚举、完整超边评分或求解成本；第四章候选保护和裁剪前资源诊断仍须按目标实现执行。')
paragraph('候选入池与一步可达进一步分开。这里的“初始跨度缺失”不含同跨度异类型；在128补充池内，逐个遗漏金标跨度统计它与当前预测组件的重叠数，并在保存的编辑提议中查找该完整类型对象。原诊断仅允许插入，或替换至多一个冲突旧组件；与两个及以上旧组件重叠时不会枚举该加入动作。下表尚未检查接受阈值、关系重建及多步路径，不能视作最终恢复率。')
rows=[]
for ds,d in data.items():
    entered=d['missing_covered_pool128'];reachable=d['missing_single_action_reachable']
    rows.append([ds.upper(),d['initial_missing_spans'],entered,entered-reachable,reachable,f'{100*reachable/entered:.2f}'])
table('表D-3 已入池遗漏跨度的一步动作限制（既存CPU诊断）',['语料','初始跨度缺失','进入128池','重叠至少2项','一步可加入','可加入／入池%'],rows,[.7,1.2,1.05,1.2,1.05,1.3])
paragraph('AAEC入池的526个遗漏跨度中，268个（50.95%）受到上述一步动作限制；CDCP为530／586（90.44%）。这支持在该弱模型诊断中继续检查集合动作，但未证明目标LLM存在相同规模，也未证明BR-J能够合法恢复这些对象。仅扩大候选池不会自动解除当前动作的重叠限制。')
paragraph('全部38928条编辑提议均依据保存的修改前后对象与金标重新计算TP、FP、FN和逐文档F1，复算值与原记录一致。表D-4的“升／平／降”按逐文档F1变化定义；“平”不等于对象完全不变，也不等于对汇总micro-F1没有影响。提议来自同一批文档且相互依赖，因此以下是组成统计，不能将提议条数当作独立样本量。')
op_names={'insert':'插入','delete':'删除','retype':'换类型','respan':'换跨度'}
rows=[]
for item in stats['proposal_actions']:
    rows.append([item['dataset'].upper()+' '+op_names[item['action']],item['proposals'],item['document_f1_increase'],item['document_f1_equal'],item['document_f1_decrease'],'—' if item['increase_pct'] is None else pct(item['increase_pct'])])
table('表D-4 全部编辑提议的逐文档效果组成（既存CPU诊断）',['语料与动作','提议数','F1升','F1平','F1降','升%'],rows,[1.8,1.05,.85,.85,.85,.8])
paragraph('非删除提议中，AAEC有益提议为337／12459（2.70%），CDCP为84／21986（0.38%）；分别有65／66篇和52／116篇文档至少存在一个此类提议。较多文档存在可改善提议，并不意味着评分器能选中它。CDCP没有插入提议，是该次初始分割与动作冲突规则共同形成的观察，不能据此判断真实文本不存在遗漏组件。')
paragraph('策略复算固定原校准阈值4.0，不在审计文档上重新选阈值。主策略允许删除；禁用删除对照在其他保存提议中重新选择最高分且超过同一阈值的一项，每篇至多接受一次。置信区间是本次事后重分析：按全文哈希组配对重采样2000次，种子10108，每次汇总计数后计算micro-F1。AAEC的重复文本共同抽取；区间仅反映这一次已保存模型的文档组不确定性，不包含重训种子变化，也不是多个比较校正后的确认性检验。')
rows=[]
for ds,d in data.items():
    b=d['initial_counts']; before=d['policies']['main']['before_f1_pct']
    rows.append([ds.upper()+' 初始','—','／'.join(map(str,b)),pct(before),'—','—'])
    for name,label in [('main','主策略'),('no_delete_same_threshold','禁删除')]:
        p=d['policies'][name]
        rows.append([ds.upper()+' '+label,p['accepted'],'／'.join(map(str,p['after_counts'])),pct(p['after_f1_pct']),f"{p['delta_f1_pp']:+.2f}",ci(p)])
table('表D-5 固定阈值策略的组件效果（既存CPU诊断）',['语料与策略','接受数','TP／FP／FN','组件F1','ΔF1','95%区间'],rows,[1.7,.7,1.55,.9,.7,1.25])
paragraph('AAEC主策略的组件F1由25.42升至26.06，CDCP由4.89升至5.06；接受的66／115次操作均为删除。禁用删除后，AAEC接受32次换跨度与1次换类型，新增3个严格正确对象，F1提高0.22个百分点且区间包含0；CDCP没有提议超过同一阈值。该对照没有重新校准，回答的是在原评分和阈值下移除删除选项的结果，不是禁用删除方案经独立调优后的最佳性能。')
rows=[]
for ds,d in data.items():
    for name,label in [('main','主策略'),('no_delete_same_threshold','禁删除')]:
        p=d['policies'][name]['object_transitions']
        rows.append([ds.upper()+' '+label,*[p[k] for k in ['correct_added','correct_lost','false_added','false_removed']]])
table('表D-6 修改前后的严格组件对象变化（既存CPU诊断）',['语料与策略','新增正确','损失正确','新增错误','移除错误'],rows,[1.8,1,1,1,1])
paragraph('表D-6按文档内的完整跨度与类型键比较前后集合，新增／损失正确对象之差等于ΔTP，新增／移除错误对象之差等于ΔFP。主策略没有新增正确对象，也未损失原有正确对象，收益来自移除66／115个错误预测；AAEC禁删除对照虽然净增3个TP、净减3个FP，同时新增30个错误对象并移除33个错误对象。因而净成绩改善不能解释为每次修改都正确，单看净FP也会隐藏错误对象之间的替换。这里仅分析单次CPU诊断的组件，不承担第五章目标模型四格互补性的证据作用。')
paragraph('运行清单记载该次诊断使用Python 3.9.6、NumPy 1.26.4、SciPy 1.13.1和scikit-learn 1.6.1，在arm64 CPU上单线程执行，完整诊断耗时29.03秒；此时间包含两语料的诊断流程，不能换算为本文系统的单文档推理延迟。此次校验了语料压缩包、分组划分、程序及协议哈希，并精确重放两语料的两项固定阈值策略。新增复算脚本和逐文档统计与原始运行分开保存，记录入口见A.5。')
paragraph('上述补充提供了真实但有限的诊断依据：当前弱模型存在显著端点问题、入池后的动作限制，以及评分选择与潜在有益提议的差距。该模型与目标LLM的误差分布不同，关系评分又给定金标端点且限单前提；本节没有验证关系监督保持、完整关系重建、局部相对全局的采用价值或目标模型的四格对象作用。真实同文档展示案例仍待按H.4补充。软件可运行、形式性质成立与目标任务效果有效仍须分别验收。')

def markdown_blocks(items):
    output=[]
    for b in items:
        if b['type']=='paragraph':
            output.append(b['text'])
        else:
            output += [b['caption'],'\n'.join(['|'+'|'.join(b['headers'])+'|','|'+'|'.join([':---']*len(b['headers']))+'|']+['|'+'|'.join(row)+'|' for row in b['rows']])]
    return '\n\n'.join(output)+'\n\n'

changes={'source_version':'1010-v7','output_version':'1010-v8','scope':'Existing diagnostic statistics only; authentic case narratives deferred by user',
         'text_replacements':[], 'insertions':[], 'section_replacements':[],
         'global':[['1010-v7','1010-v8']]}

def replace(old_text,new_text):
    global old
    assert old.count(old_text)==1,(old_text[:60],old.count(old_text))
    changes['text_replacements'].append({'old':old_text,'new':new_text})
    old=old.replace(old_text,new_text)

def insert_after(anchor,text):
    global old
    assert old.count(anchor)==1,anchor[:80]
    changes['insertions'].append({'anchor':anchor,'paragraphs':[text]})
    old=old.replace(anchor,anchor+'\n\n'+text)

replace('1010-v7 估算演示版　2026年10月10日','1010-v7 估算演示版　2026年10月11日')
changes['text_replacements'][-1]['docx_skip']='Retained Word cover records October 2026 at month precision; no day field exists.'
replace('附录D.2—D.3引用已保存的CPU轻量诊断，附录E保留前期存档，两者均不替代新增方法实验。','附录D.2—D.3引用已保存的CPU轻量诊断，并补充逐文档复算统计；附录E保留前期存档，两者均不替代新增方法实验。')
replace('真实监督漂移、端点错误分布及方法运行仍待验证，','真实监督漂移、目标模型的端点错误分布及方法运行仍待验证，')
replace('Actual supervision drift, endpoint-related errors and method performance remain to be tested,','Actual supervision drift, endpoint-related errors in the target model and method performance remain to be tested,')
replace('当前材料没有真实错误分布，完整诊断方案见附录H.1。','附录D.3已补充既存CPU诊断的初始错误、端点条件及一步动作限制；该弱模型的过度分割不能代表目标LLM，目标模型的完整诊断仍按附录H.1执行。')
insert_after('上述净变化不确定共同修复、独有修复或损害的对象身份。同一组四格TP、FP、FN可对应不同的新增对象交集；附录H.8沿用旧情景的四格成绩及风险计数构造不同重叠，说明这一不可识别性；其具体范围不移用于本版主表。正式分析需从同文档预测中对齐原文坐标、类型及完整关系键，才能报告具体改对或改错了什么。',
             '既存CPU诊断的对象复算提供了一个有限观察：AAEC禁删除对照净增3个正确组件、净减3个错误组件，但同时新增30个错误对象并移除33个错误对象（表D-6）。净改善因此仍可能伴随错误对象之间的替换。该观察只属于弱模型的单阶段组件诊断，不能解释本章四格关系对象的互补性；目标模型的同批对象对齐与真实案例仍按H.4补充。')
replace('现有主成绩、审计判断和成本均为估算情景，未完成真实语料训练、语义审阅及求解比较。','正文主成绩、增强审计判断和设定成本均为估算情景，新增方法尚未完成真实语料训练、语义审阅及求解比较。附录D.3的既存CPU输出复算提供了有限的真实诊断统计，其模型、对象范围及运行条件与主实验分开。')
insert_after('审计判定、对象概率及标签各自保存，漂移、一致性、Brier和ECE均从对应记录汇总。成本字段按生成、评分、求解与重生成分项登记，不将GPU小时、CPU秒和token混为同一单位。附录E采用其原有历史身份，不回填当前结果键。',
             '附录D.3另以research_0920/results中的既存运行清单、候选预测与编辑记录为输入，由_revision_1010_v8/analyze_saved_diagnostics.py复算；diagnostic_supplement.json保存输入哈希、判定口径和汇总，六份diagnostic_*.csv保存文档错误、端点、覆盖、提议、策略及对象变化统计。该入口不生成第三至第五章的估算计数，也不进行模型训练或求解。')

start='### D.3 诊断的启示与限制\n\n'
end='### D.4 本版构造验证及复算入口'
a=old.index(start)+len(start);b=old.index(end,a)
changes['section_replacements'].append({'start':'D.3 诊断的启示与限制','end':'D.4 本版构造验证及复算入口','old_markdown':old[a:b],'blocks':blocks})
old=old[:a]+markdown_blocks(blocks)+old[b:]
for a,b in changes['global']:
    old=old.replace(a,b)
(R/'report_1010_v8_full.md').write_text(old)
(W/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
build=json.loads((P/'docx_build.json').read_text())
new_captions=[b['caption'] for b in blocks if b['type']=='table']
caption_insert=next(i for i,c in enumerate(build['captions']) if c.startswith('表E-1 '))
build['captions'][caption_insert:caption_insert]=new_captions
assert len(build['captions']) == 67  # 53 tables, 11 figures, 3 algorithms
build['source_sha256']=hashlib.sha256(old.encode()).hexdigest()
build['output']=str(R/'report_1010_v8_full.docx')
build['retained_template_sha256']=hashlib.sha256((R/'report_1010_v7_full.docx').read_bytes()).hexdigest()
build['rendered']=False
(W/'docx_build.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
for name in ['render_document.py','cache_pages.py','update_cache.py']:
    (W/name).write_text((P/name).read_text().replace('1010_v7','1010_v8').replace('1010-v7','1010-v8'))
(W/'fonts.conf').write_text((P/'fonts.conf').read_text().replace('1010_v7','1010_v8'))
(W/'fontcache').mkdir(exist_ok=True)
(W/'reference_config.json').write_bytes((P/'reference_config.json').read_bytes())
inventory={'target_method_configuration_status':'UNBOUND_FIELDS_REMAIN',
           'target_method_unbound':json.loads((P/'reference_config.json').read_text())['production_required_unbound'],
           'existing_finite_mechanism_checks':json.loads((R/'_revision_1009_v2/mechanism_results.json').read_text())['passed'],
           'existing_finite_interface_checks':json.loads((R/'_revision_1009_v2/interface_results.json').read_text())['passed'],
           'not_executed':json.loads((R/'_revision_1009_v2/interface_results.json').read_text())['not_executed'],
           'scope':'Read-only inventory of saved check records; no new production acceptance run',
           'real_case_narratives':'Deferred to author per current request'}
(W/'execution_evidence_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1010 v8 既存诊断统计补充

参考为 report_1010_v7_full.docx，保持页幅、三个节、原样式、图像、数学对象、算法和历史附录。定点补充D.3六张既存CPU诊断统计表，相关正文只调整证据范围与引用，主实验估算数据保持原值。原v7文件保留不变。

保留411个原生数学对象、32个陈列公式、3段算法、49条参考文献、11张图和原47张表；新增表D-1至D-6，克隆原表格及题注风格并登记新书签。表目录插入对应条目，三个目录域保持可更新，最终页码按渲染更新。所有既有包部件除文档、页眉页脚和版本元数据外逐字节保持。真实案例不新增。
''')
print(json.dumps({'output_markdown':str(R/'report_1010_v8_full.md'),'new_tables':len([b for b in blocks if b['type']=='table']),'new_paragraphs':len([b for b in blocks if b['type']=='paragraph']),'captions':len(build['captions'])},ensure_ascii=False))
