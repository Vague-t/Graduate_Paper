from pathlib import Path
import json
W=Path('/Users/channtang/Downloads/paper')
D=W/'manuscript_review_test_20261011/protocol_identity_audit_20261012_v6'
O=D/'_agents/execution'
B={x['id']:x for x in json.loads((D/'_source/blocks.json').read_text())}
patches=[]
def add(b,new,reason,refs,priority='required'):
    assert B[b]['kind']=='p' and not B[b]['math_objects'],b
    patches.append({'block_id':b,'op':'replace_text','old_text':B[b]['text'],'new_text':new,'reason':reason,'priority':priority,'source_evidence':[{'path':str(W/p),'lines':lines} for p,lines in refs]})
raw=('manuscript_review_test_20261011/_source_audit/source_blocks.json','6434-6593')
v13=('research_1011_v13/acceptance_scenario/assumed_implementation_acceptance.json','1-61')
gen=('research_1011_v13/supplement_acceptance.py','75-89')
count=('research_1011_v13/simulation/manifest.json','1-15')
data=('research_1011_v13/data/manifest.json','50-80')
stats=('manuscript_review_test_20261011/chapter_revision_20261012/ch02/recompute_statistics.py','1-7,12-27,39-65')
add('B0230',B['B0230']['text'].replace('实现验收','实现检查方案与模拟记录'),'使绪论的附录定位与实际材料状态一致，不提前宣告实现通过。',[raw,v13], 'recommended')
add('B0952','附录B 评分与事务记录规范','本附录主要给出目标运行的记录要求，已列验收数为模拟稿列示，标题不应将其一概表述为真实执行记录。',[raw,v13], 'recommended')
add('B0955','目标运行的输入快照应保存C0、R0、完整候选V/P、qC/qR、未校准分数、κ、种子及文档来源；决策函数只接收候选、冻结分数和约束，金标仅用于离线评价。模型、分词器、OOF折与校准身份须通过文件摘要关联。本段规定真实运行的隔离要求；历史模拟允许按金标构造对象或分数，其材料须另标身份，不能据此认定已满足盲预测协议。','将运行规范与金标知情模拟区分，避免把设计约束写成已完成的运行事实。', [('research_1011_v13/generate_graph_scenario.py','1-5,97-121,157-162'),('research_1011_v13/supplement_acceptance.py','31-52')])
add('B0966','B.4 实现检查方案与模拟记录','“实现一致性验收”容易把模拟PASS解释为模块已实现；保留章节编号并限定其证据层级。',[raw,v13])
add('B0969','原稿列示8970条图记录、6900条终态和3131次接受账本，并给出合法性检查、严格计数和重放通过的模拟结论。本轮未定位到与本稿数值及版本绑定的逐条输入、输出和重放报告，故保留这些数量作为模拟稿列示值，不确认相应检查已实际执行。历史图模拟、构造输入上的程序检查和实际CPU诊断分别具有独立材料身份，不能互相替代；本版统计输入的绑定要求见附录J的S2.5。','8970/6900/3131在当前输入原稿中出现，现存v12/v13记录与其数量、协议、结果均不匹配；撤销未经证实的重放完成语气，亦不误称磁盘无任何历史记录。',[raw,count,data,('manuscript_review_test_20261011/_source_audit/source_manifest.json','1-11')])
add('B0973','表B-1 接口检查与故障注入的模拟记录','表题直接披露表内输入数、通过数和数值观察为模拟列示，防止脱离封面后被当作实测验收。',[raw,v13])
add('B0975','表B-1按模拟情景列示各类检查的预期输入数、通过数及判定；其数值尚未与本稿版本匹配的训练日志、故障输入和逐条输出建立绑定。真实验收须保存输入身份、配置、输出身份与判定，并核验词内边界、回答隔离、共享LoRA梯度及冻结参数。故障检查的“通过”应表示已按预期回退或恢复，不能由预设PASS字段推定。','旧稿“每类检查保存”“梯度到达”混淆目标接口与已观测行为；历史脚本明确直接构造PASS及梯度值。',[v13,gen,raw])
add('B0979','表B-1的资源边界情景包括12个候选溢出输入、60个超时输入（38个有incumbent、22个无incumbent）、40个提交失败输入、24个中断恢复输入、60个缺分输入和240个破同分输入。列示的合法回退、语义哈希一致、缺分保护及固定次序通过均为模拟记录；“主评价无超时、最优gap为0”也未由本版绑定的求解日志确认。真实报告应另存求解返回、约束复核及各级最优性状态，故障挑战集不并入正常评价的时限比例。','保留全部既有数量但不将模拟故障和求解证书当作已执行事实；补上可以关闭该缺口的日志要求。',[raw,v13,gen])
add('B1002','本稿列明原始输入摘要、规范化语料、配置、逐对象计数、评分、事务、审核及成本材料的保存要求。磁盘保留旧版模拟计数及构造程序记录，教学输入与实际CPU诊断也分别具有来源身份；但尚未建立与本版主表相匹配的完整“文档×种子×方法”输入及文件摘要绑定。旧版存在数据不等于本版可复算，统计复核范围以附录J的S2.5为准。引用原文保持原拼写，不因语言错误擅自润色数据集内容。','将“缺少输入”限定为当前结果的版本绑定，承认旧版完整数据确实存在，同时避免把旧版当作本版复算证据。',[count,data,('_revision_1011_v12/simulation/manifest.json','1-12'),stats])
add('B1006','主结果模拟、失败分析、原稿已发表表及实际CPU案例应分别登记材料身份。修订保留前版文稿；文稿文件清单与实验材料清单分开管理，各自记录版本和SHA-256。仅当正文表格与计数输入、图对象、配置和复算脚本逐项绑定后，才能说明该表已具备相应复算条件。','原文笼统声称读者可由表格定位记录及复算，与当前本版输入未绑定冲突；改成可执行的材料管理要求。',[stats,('manuscript_review_test_20261011/_source_audit/source_manifest.json','1-11')])
add('B1207','随本章提供的统计脚本与DEMO教学输入只验证计数、配对和重采样接口，不参与论文主结果。历史v12保留人工计数情景，v13保留319篇AAEC与580篇CDCP训练文本上的构造图及逐文档计数；二者与本稿80篇AAEC、150篇CDCP测试划分背景及主表数值不同，不能直接替换本版输入。本版尚未完成主表、逐文档计数、比较族及共同抽样索引的文件摘要绑定，因此不声称已经复现表3-6、表4-6或表5-3中的统计分布。','明确旧模拟可复算与当前稿不可据此复算之间的版本和协议边界；避免不准确的绝对缺失表述。',[('_revision_1011_v12/generate_scenario.py','11-41,54-67,94-100'),data,('research_1011_v13/generate_graph_scenario.py','157-162'),stats])
(O/'patches.json').write_text(json.dumps({'source_version':'v5','source_sha256':'177c90ce5327cc7cf258d576fbb478a5e766065dcedfa1dfde61448f8c56f3fa','scope':'执行状态矛盾定向审查；未修改DOCX；未执行真实实验','patches':patches},ensure_ascii=False,indent=2)+'\n')
print('patches',len(patches))
