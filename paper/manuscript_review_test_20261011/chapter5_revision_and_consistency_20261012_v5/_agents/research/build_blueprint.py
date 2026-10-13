import json
from pathlib import Path
base=Path('/Users/channtang/Downloads/paper/manuscript_review_test_20261011/chapter5_revision_and_consistency_20261012_v5')
out=base/'_agents/research'
manifest=json.loads((base/'_source/reference_manifest.json').read_text())
names={'temporal_kg':'基于结构增强语言模型的时序知识图谱推理方法研究','contrastive':'基于对比式自监督学习的结构语义融合知识推理研究','style_transfer':'现代汉语与文言文风格的迁移方法研究','transformer':'基于层内分组和层间选择的Transformer优化技术研究','prior_0405':'面向可解释性与鲁棒推理的大语言模型分子性质预测方法研究'}
layouts={
 'temporal_kg':{'chapter_count':5,'chapter5_role':'总结与展望','functional_analysis_location':['3.4 实验与分析','4.5 实验与分析'],'priority':'primary_transition_and_analysis_reference','chapters':[
  (1,[14,24],'背景、现状、两项研究及组织架构','物理22—24页按准确性与解释性区分两项研究'),
  (2,[25,32],'任务定义、相关方法与高效微调基础','章首列基础选择；2.4回收其对后续方法的支撑'),
  (3,[33,50],'结构增强预训练模型及独立实验','章首聚焦结构/历史不足；3.5按方法、主结果和专题分析收束'),
  (4,[51,73],'解释性基准、结构感知生成模型及独立实验','前章准确性基础→尚缺显式推理→数据/方法两条线；4.6分别回收'),
  (5,[74,75],'总结与未来研究','5.1回顾两项工作，5.2从局限进入展望')],
  'anchors':[{'physical_pages':[51],'section':'第四章章首','claim':'短导语位于4.1之前，先连接第三章再引入解释性问题','visual_verified':True},{'physical_pages':[62],'section':'4.5','claim':'结果分析节先说明主比较和多维分析的目的','visual_verified':True}]},
 'contrastive':{'chapter_count':5,'chapter5_role':'总结与展望','functional_analysis_location':['3.6 实验设计与结果分析','4.6 实验设计与结果分析'],'priority':'primary_chapter_structure_reference','chapters':[
  (1,[13,20],'背景、现状、研究内容、组织','1.4按两个信息融合问题组织后文'),
  (2,[21,30],'任务定义、异质信息、自监督基础','短导语限定理论范围；2.4回收基础并映射第三/四章'),
  (3,[31,48],'schema、多视图、对比预训练、微调及实验','章首短导语衔接前两章；3.7按问题/方法/结果收束'),
  (4,[49,67],'时序双塔、输入、编码、目标及实验','由静态条件的限制转向时序动态；4.7总结独立研究'),
  (5,[68,70],'总结与展望','依次回顾研究再列后续问题')],
  'anchors':[{'physical_pages':[49],'section':'第四章章首','claim':'上一章静态图任务→动态条件→本章时序建模','visual_verified':True},{'physical_pages':[38,48,54,67],'section':'3.6、4.6及小结','claim':'任务/设置→主结果→消融/性能分析→收束','visual_verified':False}]},
 'style_transfer':{'chapter_count':5,'chapter5_role':'总结与展望','functional_analysis_location':['3.4 实验对比与分析','4.4 实验对比与分析'],'priority':'primary_transition_reference','chapters':[
  (1,[13,24],'背景、现状、内容、贡献、组织','1.5按小模型与大模型场景分章'),
  (2,[25,32],'任务、语言模型、强化学习、提示与指令','短导语从生成任务入手；2.5将理论映射到方法章'),
  (3,[33,49],'提示热启动、多维强化学习及实验','章首先限定资源受限小模型场景；3.5按粗监督到精细反馈收束'),
  (4,[50,68],'指令微调、上下文学习及实验','章首改变资源/模型条件；4.5分别总结两种路径'),
  (5,[69,71],'总结与展望','无编号短导语说明总结/展望顺序；后续方向回应具体限制')],
  'anchors':[{'physical_pages':[50],'section':'第四章章首','claim':'资源受限的小模型→资源充足的大模型，范围变化明确','visual_verified':True},{'physical_pages':[69],'section':'第五章章首','claim':'总结章也可有简短无编号导语','visual_verified':False}]},
 'transformer':{'chapter_count':6,'chapter5_role':'集中实验设计与分析','functional_analysis_location':['第五章 实验设计与分析'],'priority':'primary_chapter5_reference','chapters':[
  (1,[10,17],'背景、优化现状、研究内容、组织','图1.2两条方法路线汇入第五章实验'),
  (2,[18,27],'模型架构/复杂度、通用与结构优化','章首说明服务第三/四章；2.4总结基础'),
  (3,[28,38],'层内分组、融合与复杂度','3.1直接承担动机导入；3.5回收设计'),
  (4,[39,46],'贡献度、全局融合、长度缩减、复杂度','由前章局部分组连接跨组/层间问题；4.6区分效果/效率'),
  (5,[47,62],'设置、总体结果、消融、参数、可视化','章首说明目标/顺序/公平条件；5.6按证据类型收束'),
  (6,[63,64],'总结与展望','回收效果/效率目标，未来方向对应局限')],
  'anchors':[{'physical_pages':[47],'section':'第五章章首与5.1','claim':'章首导语→设置；先说明综合评估任务','visual_verified':True},{'physical_pages':[62],'section':'5.6','claim':'小结按主结果/消融/参数/可视化收束','visual_verified':False},{'physical_pages':[39],'section':'4.1','claim':'动机可以直接放在编号首节，不必重复前导语','visual_verified':False}]},
 'prior_0405':{'chapter_count':5,'chapter5_role':'仅有总结与展望标题，正文空缺','functional_analysis_location':['3.5 实验对比与分析','4.5 实验对比与分析（未完整展开）'],'priority':'limited_local_reference_only','chapters':[
  (1,[13,25],'背景、现状、内容、组织','图1.3含股票趋势预测主题，与正文不符'),
  (2,[26,33],'任务、图网络、大模型、对齐、检索、训练基础','章首和小结将技术对应到后续模型'),
  (3,[34,49],'CoT数据、融合模型、训练、实验','3.1结构较清楚；实验表后无本章小结即进第四章'),
  (4,[50,61],'反思/探索、协同数据、强化学习','4.1由前章能力引出剩余鲁棒性问题；4.5只有标题/参数表'),
  (5,[62,62],'总结与展望标题','无实质总结/展望正文')],
  'anchors':[{'physical_pages':[24],'section':'图1.3','claim':'股票趋势预测模板残留','visual_verified':True},{'physical_pages':[62],'section':'5.1/5.2','claim':'仅标题、无正文','visual_verified':True},{'physical_pages':[50],'section':'4.1','claim':'已完成基础→剩余问题→后续方法，可局部借鉴','visual_verified':False}]}}
sources=[]
for x in manifest:
 k=x['key']; z=layouts[k]
 c=[{'chapter':v[0],'physical_page_scope_or_anchors':v[1],'role':v[2],'transition_pattern':v[3]} for v in z.pop('chapters')]
 sources.append({'key':k,'title':names[k],'path':x['path'],'sha256':x['sha256'],'page_count':x['page_count'],'sha_matches_manifest':True,'structural_preflight':'PASS','preflight_sidecar':str(out/f'{k}_preflight.json'),'chapters':c,**z})
sections=[
 {'number':None,'title':'章首导语','role':'回收前两阶段的职责并提出组合分析问题；保留模拟证据身份','insert_after':'B0765','insert_before':'B0767','numbered':False},
 {'number':'5.1','title':'综合分析设置与比较范围','role':'解释四种组合、共同条件及不同对照能回答的问题','blocks':['B0767','B0768','B0769','B0770'],'assets':['表5-1'],'children':[]},
 {'number':'5.2','title':'两阶段组合结果与交互分析','role':'由总体指标到主要阶段增量，再讨论探索性交互','blocks':['B0773','B0774','B0775','B0776','B0777','B0778','B0779','B0780'],'children':[{'number':'5.2.1','title':'四种配置的总体结果','assets':['表5-2','图5-1']},{'number':'5.2.2','title':'阶段增量与交互效应','assets':['表5-3'],'boundary':'交互区间包含0，不把组合更高写成协同已证实'}]},
 {'number':'5.3','title':'关系恢复来源与漏检成因','role':'从总体F1转为同身份对象的恢复来源与剩余错误','blocks':['B0783','B0784','B0785','B0786','B0787','B0788','B0789','B0790','B0791'],'children':[{'number':'5.3.1','title':'同一关系身份的恢复分解','assets':['表5-4'],'boundary':'三种子合计计数不等于均值F1，也不当成独立样本'},{'number':'5.3.2','title':'端点缺失与决策阻断分析','assets':['表5-5a','表5-5b'],'boundary':'首个阻断按优先级互斥归类；候选入池不等于终态被选'}]},
 {'number':'5.4','title':'多源关系的分组结果与局限','role':'按CDCP完整源集合解释困难与小样本边界','blocks':['B0794','B0795','B0796','B0797'],'assets':['表5-6'],'children':[]},
 {'number':'5.5','title':'本章小结','role':'组合结果、对象解释、未被独立支持的机制及适用边界','blocks':['B0800','B0801'],'children':[]}]
result={'schema':'thesis_structure_research/1','target_version':'formatted_word_pdf_20261012_v4','date':'2026-10-12','scope':'Read-only reference structure research; no manuscript or numeric mutations','page_number_system':'physical_page is 1-based PDF page index','sources':sources,'decision':{'retain_chapter_title':'第五章 两阶段框架的综合分析','chapter5_function':'cross-stage synthesis, not another primary experiment chapter','why':'第三、四章已分别含独立实验，第五章应提供组合、恢复重叠与剩余错误的增量解释','section_plan':sections},'global_chapter_roles':{'1':'问题、研究路线与继承边界','2':'共同任务对象、理论、评价、公共条件及接口','3':'训练文本变化后的可靠监督与成对学习','4':'原文不变时预测组件修改的依赖完整性与接受','5':'训练与推理组合的总体结果、对象恢复和剩余错误','6':'方法/证据状态总结、适用局限和对应后续工作'},'transition_rules':['先回收上一章已解决的范围，再说明未覆盖的问题，再界定本章任务','章首短导语和编号引言可以共存，但不要重复同一背景','章末小结优先收束当前问题、方法和证据，不要求机械预告下一章','保持模拟主比较、构造示例、实际CPU诊断、待验证目标模型的区分'], 'do_not_copy':[{'source':'prior_0405','physical_pages':[24],'reason':'图1.3是股票趋势预测模板残留'},{'source':'prior_0405','physical_pages':[60,61,62],'reason':'实验分析未完整展开，末章只有空标题'},{'source':'all','reason':'参考论文中的显著/验证措辞和实验清单不能代替本稿的证据'}], 'target_issues':[{'id':'R01','blocks':['B0765','B0767'],'issue':'缺第五章总领导语'},{'id':'R02','blocks':['B0783','B0794'],'issue':'节标题像实现标签，未表达分析问题'},{'id':'R03','blocks':['B0791'],'issue':'最后一列实际是超时，指代联合约束/接受门列错误'},{'id':'R04','blocks':['B0801','B0808'],'issue':'第五/六章总结需与第三/四章模拟结果身份保持一致'},{'id':'R05','blocks':['B0221'],'issue':'长段目录说明可按章分段并更新第五章职能'}], 'memory_used':[{'path':'MEMORY.md','lines':[28,30],'purpose':'preserve versioned review advice and explicit simulation disclosure'}],'limitations':['仅核查结构与衔接，不全面审计参考论文实验真实性','结构预检PASS不等于内容正确','temporal_kg用pdfplumber/PDFium解决本轮pypdf/Poppler中文显示异常']}
(out/'research_blueprint.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('sources',len(sources),'sections',len(sections),'blueprint_bytes',(out/'research_blueprint.json').stat().st_size)
