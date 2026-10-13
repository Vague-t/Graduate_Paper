import json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
B={b['id']:b for b in json.loads((ROOT/'_source/manuscript_blocks.json').read_text())}
manifest=json.loads((ROOT/'_source/source_manifest.json').read_text())
def ev(bid,quote=None):return {'block_id':bid,'quote':quote or B[bid]['text']}
F=[]
def add(fid,p,cat,title,evidence,issue,rec,patches=None,auto=False):
 F.append(dict(id=fid,priority=p,classification=cat,title=title,evidence=evidence,issue=issue,recommendation=rec,patches=patches or [],safe_for_editorial_revision=auto))
add('C01','P1','确认错误','材料可得性声明与统计输入缺口不一致',[
 ev('B0965','随稿提供原始输入摘要、规范化语料、配置、逐对象计数、评分、事务、审核、成本和生成脚本。'),
 ev('B1170','原稿主结果尚缺少完整的文档×种子×方法计数输入，因此本轮不声称已经复现表3-6、表4-6或表5-3中的统计分布。')],
 '前者作出无条件随稿交付声明，后者明确主结果完整计数输入缺失。读者无法判断哪些材料已提供、哪些只是预定记录字段。',
 '按材料身份分开说明：模拟表与登记、教学输入和实际CPU记录；完整主结果联合计数及真实目标模型轨迹仍待补齐。先修正无条件声明，不补造文件或运行。',
 [{'block_id':'B0965','old':B['B0965']['text'],'new':'本稿列明原始输入摘要、规范化语料、配置、逐对象计数、评分、事务、审核及成本等材料的保存要求。现有模拟材料、教学输入与实际CPU诊断分别保留其来源身份；主结果仍缺少完整的文档×种子×方法计数输入，统计复算范围以附录J的S2.5为准。引用原文保持原拼写，不因语言错误擅自润色数据集内容。'}],True)
add('C02','P1','解释含糊','I0与G0及继承有界修正的执行边界未锁定',[
 ev('B0291','继承配置T0/I0在共同协议下重新评价，其增量作为后续主要比较的基准。'),ev('B0478','T0/I0为继承配置；Heads仅增加辅助头；'),ev('B0274'),
 ev('B0533','该步骤仅执行无歧义的坐标规范化、相同语义对象去重及ID重排，并同步更新引用；歧义ID、越界、非法类型或剩余结构冲突直接报失败，不额外猜测跨度、删除冲突组件或补边。'),
 ev('B0961','MCR-BR[34]的专项适配、线索提示、多候选整图重排序及有界修改作为已有基础。')],
 'T0/I0被称为继承配置，而G0由整图重排序和合法化定义；第四章以T1/I0为修正前统计。稿内没有直接说明I0是否执行原有BR，以及I1替换旧BR还是接续G0。它影响“推理增量”的执行含义。',
 '对照配置/代码后增加一句I0、I1、G0的明确关系。没有执行证据时，只沿用“继承推理配置”和“依赖闭合完整推理配置”的层级定义，并在修改建议中保留此待核实项。不得替用户推断或改变实验定义。')
add('C03','P1','解释含糊','摘要与综合结论缺少就地说明模拟证据身份',[
 ev('B0004'),ev('B0010','在AAEC和CDCP官方测试集上，完整配置的严格关系F1分别为73.29和52.02，相对继承配置提高8.10和13.26个百分点。'),ev('B0323'),ev('B0516'),ev('B0808')],
 '封面已明确全稿模拟用途，第三、四章也在本地保留边界；摘要、第五章和第六章却使用完成式实证语气。单独阅读或引用这些部分时容易误认为真实目标模型实验。不是判定已经隐瞒，而是需把证据身份一致地带到独立可读部分。',
 '在中英文摘要结果句、第五章章首和第六章总结各给一次简短模拟限定；保留全部已有披露，不把CPU案例、教学事务或文档QA当主模型证据。',
 [{'block_id':'B0010','old':'在AAEC和CDCP官方测试集上，完整配置的严格关系F1分别为73.29和52.02','new':'在依据AAEC和CDCP官方测试划分构造的模拟评审结果中，完整配置的严格关系F1分别为73.29和52.02'},
 {'block_id':'B0017','old':'On the official AAEC and CDCP test splits, the complete configuration reaches','new':'In the simulated review results constructed for the official AAEC and CDCP test splits, the complete configuration reaches'},
 {'block_id':'B0808','old':'完整系统在AAEC与CDCP上的关系F1分别达到','new':'在本稿的模拟评审结果中，完整系统在AAEC与CDCP上的关系F1分别为'}],True)
add('C04','P2','确认错误','条件增量被称为主效应',[
 ev('B0778'),ev('B0801'),ev('B0777','AAEC | T1I0 − T0I0 | 3.63；AAEC | T1I1 − T1I0 | 4.48；CDCP | T1I0 − T0I0 | 4.89；CDCP | T1I1 − T1I0 | 8.37'),ev('B1165','主要1 整套训练 | T1/I0 对 T0/I0；主要3 整套推理 | T1/I1 对 T1/I0')],
 '固定I0计算训练差值、固定T1计算推理差值，是条件增量/简单效应。它们未对另一因素水平平均，不宜在四格交互上下文中称为主效应。',
 '统一为“条件增量”或“主要比较中的正向差值”；不改表格数字，不把交互区间跨零解释成证实协同。',
 [{'block_id':'B0778','old':'不能把两条主效应相加就称为协同','new':'不能仅凭两个阶段的条件增量均为正便认定存在协同增益'},
 {'block_id':'B0801','old':'训练和推理均形成双语料正向主效应','new':'在当前模拟条件下，整套训练和整套推理的主要比较在两种语料上均呈正向差值'}],True)
add('C05','P2','确认错误','表5-5b最后一列的指代错误',[
 ev('B0790','表头末两列为“联合约束／接受门 | 超时”'),ev('B0791')],
 '最后一列实际是“超时”，不能解释为可行域、预算和接受门。',
 '直接按列名引用，避免表格调整后再产生位置性错误。',
 [{'block_id':'B0791','old':'最后一列包含可行域、预算与接受门，不统一称为求解错误','new':'“联合约束／接受门”列汇总可行域、预算及接受条件造成的阻断，不统一称为求解错误'}],True)
add('C06','P2','确认错误','附录H残留旧表1-2交叉引用',[
 ev('B1121','重生成与风险比较遗漏 | 纳入表1-2、表4-6和14项Holm主要族'),ev('B0217'),ev('B1164')],
 '现表1-2比较MCR-BR已有机制与本文工作，不是重生成/风险主要比较的责任表；现有对应位置为补充表S2-4。',
 '替换为现版本的表号。',
 [{'block_id':'B1121','old':'纳入表1-2、表4-6和14项Holm主要族','new':'纳入补充表S2-4、表4-6和14项Holm主要比较族'}],True)
add('C07','P2','解释含糊','CDCP提案64与256的层级未对齐',[
 ev('B0541','CDCP默认由关系提案器输出最多64个完整源组与目标，并补充预测分段中相邻2／3成员的源组，每文档补充源组上限256。'),
 ev('B0545','本文将有限原生提案作为默认入口：补充跨度64、每跨度前2类型、CDCP完整源组与目标提案最多256，受保护对象另计。')],
 '前一段可以读成关系模型64项、邻接补充256项，后一段又将全部完整源组与目标提案称为256项。未说明256是否包含64项、去重前后及目标配对阶段。',
 '保留两个数值，需配置依据明确它们分别限制哪个阶段。未核实前不要把64擅改为256，也不要推导总额320。')
add('C08','P2','解释含糊','第五章缺少分析问题与逐节解释，表格承担过多论述',[
 ev('B0765'),ev('B0767'),ev('B0773'),ev('B0783'),ev('B0794'),ev('B0801')],
 '章题后直接进入基线参照，5.2、5.3和5.4均直接摆表。表5-2至5-6虽可支撑综合分析，但缺少从两阶段条件增量到对象恢复、漏检与长源边界的提问顺序；现小结一段未充分回答本章为何独立。',
 '借鉴参考论文的章首定位、节前问题、表后解释、小结回扣结构：本章专门回答系统组合的条件增量、恢复对象的互补与重叠、剩余瓶颈。建议5.1分析目标与比较条件；5.2整体结果与交互分析；5.3对象恢复与剩余误差（可分成员、端点/首阻断两小节）；5.4多前提关系分组分析；5.5小结。保持现有全部表格和模拟边界，不重复第三四章推导或重做主表。')
add('C09','P3','解释含糊','方法章有引言但缺少参考论文式章题后短承接，章末未明确引向综合分析',[
 ev('B0317'),ev('B0318'),ev('B0322'),ev('B0512'),ev('B0513'),ev('B0514'),ev('B0511'),ev('B0764'),ev('B0804'),ev('B0806')],
 '第三、四章不是没有引言，而是承接文字均放在3.1/4.1；参考论文常在章题后先给一段承上启下，随后引言展开具体问题。第四章小结已经有证据边界，却没有点明第五章为何继续。第六章也可先说明总结组织。',
 '可以将现有承接内容提炼或移到章题后，避免重复新增同义段。第二章B0223已是良好章首。第一章按绪论常规直接1.1即可，无需机械补“第一章小结”。第三章末补“下章转向原文不变时预测结构的依赖维护”；第四章末补“第五章在同一对象身份下分析两阶段组合及剩余误差”；第五章末承接第六章限制与展望。')
add('C10','P3','确认错误','符号表残留输入文档D别名',[
 ev('B1052','x或D | 输入原始文档 | 推理修正不改写原文；第四章D另指删除集合'),
 ev('B0577','本章的D0和D均为待删除组件的集合，输入文档始终记为x。'),ev('B0227','记固定文本版本的文档为 x，其标识为 d。')],
 '正文已经将输入文档统一为x，符号表仍保留“x或D”，给跨章阅读留下不必要双义。',
 '符号表输入文档行只保留x；D在第四章删除集合行说明。',
 [{'block_id':'B1052','old':'x或D','new':'x'}, {'block_id':'B1052','old':'推理修正不改写原文；第四章D另指删除集合','new':'推理修正不改写原文；文档标识记为d'}],True)
add('C11','P2','材料不足','部分附录回指声称的算法细则尚未在所指位置展开',[
 ev('B0616','排序、状态键、缓存游标和分项计费统一列于附录B.3，预算边界见附录B.4.3。'),ev('B0926'),
 ev('B0537','坐标转换、排序和异常细则见附录A.6，边界分仅用于召回排序。'),ev('B0910'),ev('B0911')],
 'B.3现仅一段预算与回退摘要，没有完整排序、状态键及缓存游标定义；A.6现为序列化样例及身份说明，没有完整补充候选排序规则。是回指覆盖范围过大的文稿问题，不据此断定实现不存在。',
 '本轮安全做法是把回指缩到附录实际包含的内容；若确需复现级细则，应另以真实配置/代码补充。',
 [{'block_id':'B0616','old':'排序、状态键、缓存游标和分项计费统一列于附录B.3，预算边界见附录B.4.3。','new':'预算计费与回退原则见附录B.3，资源边界检查见附录B.4.3；队列排序、状态键和缓存游标的完整实现仍需结合配套执行记录核对。'},
 {'block_id':'B0537','old':'坐标转换、排序和异常细则见附录A.6，边界分仅用于召回排序。','new':'原文序列化与对象身份说明见附录A.6；边界分仅用于补充候选的召回排序。'}],True)
checks=[]
C={}
for r in B['B1116']['rows'][1:]:
 ds,m,s,tp,fp,fn,f=r;tp,fp,fn=map(int,(tp,fp,fn));v=100*2*tp/(2*tp+fp+fn); C.setdefault((ds,m),[]).append(v)
 assert f'{v:.2f}'==f
checks.append({'check':'附录H逐种子关系F1','blocks':['B1116'],'status':'pass','detail':'24行整数计数重新计算，与显示F1全部相符。'})
rows=B['B0775']['rows'];ds_metrics=[]
for row in rows[1:]:
 m=row[0]
 for ds,col in [('AAEC',2),('CDCP',4)]:
  v=C[ds,m];calc=f'{statistics.mean(v):.2f} ± {statistics.stdev(v):.2f}';assert calc==row[col];ds_metrics.append({'dataset':ds,'method':m,'computed':calc})
checks.append({'check':'四格关系F1均值及样本SD','blocks':['B0775','B1116'],'status':'pass','values':ds_metrics})
for r in B['B0785']['rows'][1:]:
 vals=list(map(int,r[1:]));assert sum(vals[:5])-sum(vals[5:7])==vals[7]
checks.append({'check':'对象成员分解恒等式','blocks':['B0785'],'status':'pass','detail':'AAEC 1582+1+93+36+1−0−9=1704；CDCP 293+2+35+26+3−0−1=358。'})
for r in B['B0788']['rows'][1:]:assert int(r[2])==sum(map(int,r[3:]))
for r in B['B0790']['rows'][1:]:assert int(r[1])==sum(map(int,r[2:]))
checks.append({'check':'端点与首个阻断分解','blocks':['B0788','B0790'],'status':'pass','detail':'所有行TP加互斥未命中类别均等于对应三种子金标总量。'})
for m in ['T0I0','T1I0','T0I1','T1I1']:
 rr=[r for r in B['B0796']['rows'][1:] if r[1]==m];sums=[sum(int(r[i]) for r in rr) for i in [2,3,4]];h=[r for r in B['B1116']['rows'][1:] if r[:2]==['CDCP',m]];total=[sum(int(r[i]) for r in h) for i in [3,4,5]];assert sums==total
checks.append({'check':'CDCP源数分组加总','blocks':['B0796','B1116'],'status':'pass','detail':'各配置TP/FP/FN按四组加总，与逐种子整数计数合计一致；组内逐种子方差缺乏分种子行，不在本轮声称复算。'})
checks.append({'check':'联合重采样CI和Holm p','blocks':['B0487','B0709','B0777','B1170'],'status':'not_reproduced','detail':'缺少完整逐文档联合计数输入，不能仅凭种子总表重建；只核对重复报告与主要/探索身份。'})
out=dict(source=manifest,scope='v4全文只读逻辑结构和一致性审查；未改DOCX；未重新运行主实验',reference_reading=[{'key':'contrastive','physical_pages':[11,12,31,49,68],'observation':'方法章题后先承接前文并定位问题，随后引言、模块、实验、小结；第五章为总结，不机械套用本稿章节编号。'},{'key':'style_transfer','physical_pages':[10,11,12,33,50],'observation':'第四章先承接第三章小模型情境再引入大模型研究场景；章首用于区分研究点。'},{'key':'transformer','physical_pages':[7,8,47],'observation':'第五章独立综合实验，以章首交代比较、消融、参数和可视化分析的次序；是本稿综合分析章更直接的结构参照。'}],findings=F,numeric_checks=checks,do_not_change=['表5-2/5-3的F1点估计及种子差值','主比较14项和探索性身份','模拟/教学/CPU证据边界','CDCP完整源对象身份','I1并不等同集合局部BR-J，主测试全部Global的限制','成对项和共同接受未获独立稳定优势的结论'],memory_used=[{'path':'MEMORY.md','lines':'29-30','use':'版本绑定建议文档和模拟披露偏好；当前证据身份另由B0004等现场确认。'}])
(ROOT/'_agents/compare/consistency_findings.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(ROOT/'_agents/compare/numeric_check_results.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print('Wrote',len(F),'findings;',len(checks),'check groups')
