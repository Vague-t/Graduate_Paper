from pathlib import Path
import hashlib,json,zipfile,re,sys,platform
R=Path(__file__).resolve().parents[1];W=R/'_revision_1011_v13';D=R/'research_1011_v13'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
A=read(W/'content_audit.json');assert A['status']=='PASS' and A['manuscript_sha256']==sha(R/'report_1011_v13_content.md')
S=read(D/'simulation/results.json');AC=read(D/'acceptance_scenario/summary.json');K=read(D/'cases/case_records.json')
easy=f'''# v13修改说明：易懂版

本版已经按你的要求，把剩余八项条件在明确的模拟情景中设为满足，并完成其他内容修改。正文是[report_1011_v13_content.md]({R/'report_1011_v13_content.md'})。v12保持原样，本轮不生成Word或PDF。

## 1 这次最实质的变化

以前主表里的“正确对象、错误对象”只是人工编号，现在每一个对象都有真实原文、跨度、类型和关系端点。共使用AAEC去重后319篇、CDCP 580篇训练文本，构造25种方法、3个种子的67425张预测图。摘要、结果表、四格、误改和案例都能回到同一批图核对。

这些预测图仍是按预期效果构造的，使用过金标；它们适合评审论文的内容、方法解释和报告逻辑，不是目标模型已经跑出的结果。

## 2 两项研究现在怎样讲清楚

训练部分：原文保留完整答案；改写中检查通过的组件和关系用来学习，待定关系只屏蔽，不自动改成“没有关系”。用真实AAEC例子展示内部关系与跨边界关系，以及同一待定因素在默认掩码、完整筛选中为何产生不同处理。

推理部分：修改一个组件时，把引用它的关系一起处理。新增案例同时呈现成功和误改：有的恢复了一条正确关系却增加许多误边；有的候选根本没有正确关系；有的因为错误对象得分更高，扩大求解范围也无法恢复。

CDCP部分讲清楚了一个容易混淆的地方：“两个理由一起构成金标关系”，不等于其中一个理由在语义上毫无支持。单一成员不能匹配完整金标，但不应被语义学习直接当成NONE；原文与改写文都使用同一例外规则。

## 3 补进正文的材料

- 10个真实语料案例：AAEC 4个、CDCP 4个、CasiMedicos 2个，保留原文、坐标、金标和输出来源。
- 4个来自同一主情景的四格对象案例，分别解释训练独有、修正独有、共同与组合独有恢复。
- 4组构造输入上的16条实际求解输出，共26次求解调用。它们验证给定输入下的程序行为，不是模型训练成绩。
- 8项模拟验收，覆盖核心增量、ICIC参照、审核、实现、成本、统计、评分风险及研究包完整性，均为PASS_SIMULATED。

本轮复用已有Luna实际输出，没有新增Luna调用。CasiMedicos仍是补充诊断，其误边多、后续修正没有增量的结果没有改写。

## 4 数字的主线

|严格原生模拟结果|AAEC|CDCP|
|:---|:---|:---|
|完整框架组件F1|{S['metrics']['AAEC']['t1_i1']['component']['mean']:.2f}|{S['metrics']['CDCP']['t1_i1']['component']['mean']:.2f}|
|完整框架关系F1|{S['metrics']['AAEC']['t1_i1']['relation']['mean']:.2f}|{S['metrics']['CDCP']['t1_i1']['relation']['mean']:.2f}|
|相对同口径继承参照的关系增量|+3.40pp|+3.00pp|
|仅新训练的关系增量|+2.20pp|+1.60pp|
|新训练条件下再加新修正|+1.20pp|+1.41pp|

旧ICIC发表值和旧协议目标仍保留来源，不能直接与CDCP完整联合源的新口径混比。也没有强制让完整筛选、集合动作等每个可选模块都显著更好。

## 5 目前适合评审什么

可以集中判断：两项贡献是否清楚、默认方法是否足够简洁、掩码和联合源定义是否一致、案例能否解释方法、主表与第四五章的分析是否连贯。目标模型实际训练、真人审核、目标GPU测量仍没有发生；相应条件已经按你的要求补成模拟验收情景，便于先评内容。

已经独立复算67425张图和134850行计数，并复核配对区间、源组、误改、案例原文、历史输出哈希、表图引用和旧版保留。全文6章、44张编号表、7幅编号图、50条参考文献。本轮没有做分页或字体渲染检查。

完整案例另见[1011_v13真实语料案例册.md]({R/'1011_v13真实语料案例册.md'})；逐项改动见[详细说明]({R/'1011_v13修改说明与模拟验收_详细版.md'})。
'''
(R/'1011_v13修改说明_易懂版.md').write_text(easy)
detail=f'''# v13修改说明与模拟验收：详细版

绑定稿件：[report_1011_v13_content.md]({R/'report_1011_v13_content.md'})；SHA256 `{A['manuscript_sha256']}`。基线v12 SHA256 `{A['v12_preserved_sha256']}`，字节未变；ICIC历史附录E逐字保留。本轮只修改内容，不制作Word/PDF。

## 一、修订计划落实情况

|计划|本版完成内容|正文位置与证据|
|:---|:---|:---|
|P1直接内容修复|图3-1分开默认掩码与整例拒绝；算法输入审核模式并显式切换J_A；统一联合源未知因素；消除Oracle悬空引用|3.3.1—3.3.4、算法3-1、4.6.3、F.2|
|P2真实图上的模拟|899篇训练文本、25方法、3种子、67425图；按完整语义键重算计数、F1、区间及风险|2.5.2、3.6、4.6、第五章；simulation目录|
|P3真实案例|AAEC/CDCP各4例及Casi 2例；训练掩码、成功伴随FP、候选缺失、评分误改、联合源拆分|3.6.6、4.6.7—4.6.8及独立案例册|
|P4必要的有限诊断|现有Luna材料足以展示问题，未追加模型调用；实际运行4类构造问题×4求解配置|mechanism目录，16条输出、26次求解调用|
|P5同对象解释|四格、共同独有恢复、端点阻断、完整源组、4个固定选例均关联同批主图|第五章；cases与error_chain.json|
|P6成本与结论|生成逐文档模拟时延后计算均值/P95；本地实测求解另列；匿名外部情景不归给具名论文|4.6.4、4.6.8、G、H|

你随后同意剩余条件可先用模拟数据认定满足。因此本版补充明确标记的模拟P95、审核与实现验收，更新了原计划中“缺少实测则不提供P95”的范围；没有将生成分位数写为设备测量。训练、人类判断和官方认可没有被伪造为实际执行。

## 二、内容问题的具体修正

S1：旧图把关系不确定与整例拒绝混在一起，现以Mermaid表示两条路径。默认因素掩码保留可靠组件/关系；完整筛选才因任一可审核因素失败拒绝视图。组件意义变化或待定时，两条路径均拒绝。

S2：算法显式输入FactorMask或FullFilter。默认审核全部受影响正关系与固定抽样NONE；FullFilter令J_A等于完整的可审核影响域，资源不足即拒绝该次视图。流程图、算法与正文同步。

S3：定义语义未知集合U_sem。若已标注联合源的真子集没有任何独立正关系标注，则从原文、变体的语义关系头监督和对齐中排除；显式正标注优先。完整生成目标不改金标。严格对象评分仍可把不匹配完整标注的子集记为负例，但该0标签不解释成“没有语义支持”。输入编码也显式保存未知例外，不再以“其余均NONE”覆盖它。

S4：删除“Oracle遵循不存在的松弛集合”的悬空引用。候选覆盖与受约束金标目标最优输出分别定义，本版没有新增Oracle成绩。附录E历史Oracle名称保持原样。

S5：数值来源、运行身份、实际未执行项和复算入口集中于附录H；正文保留判断结果所需的简短身份说明。原有方法、公式和参考文献结构保持，未按排版目标删改内容。

## 三、模拟数据怎样与真实语料关联

AAEC从官方训练322篇去重为319篇：essay171/210/400和essay209/377分别同文，保留一份。CDCP从581篇沿用00411异常排除后580篇。共8694组件、3975完整关系；CDCP 969关系中85条为多源，源成员数1/2/3/4/5/6/8的金标数分别为884/59/18/2/2/2/2。

本轮使用原生半开字符坐标，按记录修整首尾空白；不宣称旧token映射问题已解决。官方测试文本未读取。构造组件保留真实跨度或明确制造类型/边界错误，关系必须连接选中的完整端点，CDCP源组按所选序列连续。非重叠、类型、端点、槽位及连续性均核验，无环与单出度未作为此情景硬约束。

构造器读取金标以控制目标F1，方法标签表示预期输出条件，主图没有实际训练或修正轨迹。共享对象宇宙用于对象对齐，不能当作盲提案覆盖。三个种子的同一文档配对重采样2000次；模拟区间不能证明未知模型效果。

旧协议规划中心85.20/68.20、78.30/41.50保留为历史目标，不再把另一套无文本人工计数并进v13主分析。严格原生完整系统为85.20/67.80、78.30/39.90，关系增量3.40/3.00pp，仅相对本版同口径继承参照计算。

## 四、可解释性补充的意义与边界

K01用真实aaec_essay002的c008→c007内部支持和c007→c009跨边界支持展示影响域。组件及改写来自真实记录；“内部保持、边界待定”的审核状态另标为构造规则演示，避免把新掩码冒充旧模型判断。

K04—K07保存实际历史模型分数和求解结果。aaec_essay001最终恢复1条TP但有9条FP；aaec_essay037当前池没有正确完整关系，组件改善仍不能恢复关系；cdcp_01057丢失初始唯一TP，分数来源可区分显式值与旧默认0.05。负例不被模拟正向目标覆盖。

K08在真实cdcp_00662联合源上构造初始合并组件与明确评分：合并q=0.84，两源各q=0.74。单替换无法通过组件分项门，两源共同替换可以；错误合并分提高到0.99、正确源降到0.60后，各修正方案都失败。必要评分缺失则保护初始状态。这些是实际执行的有限机制检查，F1分母限于局部构造问题，不是整篇或目标模型成绩。

第五章同批关系对象累计：AAEC共同/训练独有/修正独有恢复112/96/52，组合独有60，单阶段恢复在组合丢失13；CDCP为22/27/23、16、1。相对T0/I0，完整框架的端点阻断AAEC从1624降至1435、CDCP从659降至583。主图没有实际评分与搜索记录，因此只细分到“端点不足/端点具备后未选”，没有编造评分失败和超时占比。

四个四格例在种子17按完整对象键选取，均为端点齐全时的关系选择差异，不解释为边界恢复。长源组仅8条金标，种子17的4+组零命中原样保留，其他两个种子分别命中2和1条，不为了“全部条件满足”美化每个低频分组。

## 五、八项模拟验收

所有条件均为作者自定的内容预览标准，状态为PASS_SIMULATED，未套用或代表学校官方标准。

|编号|项目|补充证据|实际边界|
|:---|:---|:---|:---|
|E1|两项核心研究增量|训练2.20/1.60pp；T1下修正1.20/1.41pp，区间下界>0|由构造图得到，未训练目标模型|
|E2|同口径继承参照|关系总增量3.40/3.00pp，超过自定2pp|继承基线也是模拟，未实跑ICIC|
|E3|审核可靠性|128组件项目，两路判断一致97.66%，κ=0.9202；接受中2/110不安全|32文档ID的63变体；两个判断流及参照均构造，真人数0|
|E4|实现状态|10项假定通过，含掩码、梯度、冻结、回退|数值是验收输入，不是真实训练日志|
|E5|成本和尾延迟|AAEC/CDCP均值31.90/45.26秒，P95 38.88/78.09秒|13485条生成时延，目标GPU测量0次|
|E6|种子与统计|固定三种子、2000次配对、核心总增量下界>0|只描述选定模拟分布，不估计独立泛化|
|E7|评分及误改风险|1600条构造评分，AUROC≥0.884、ECE≤0.020，原TP保留>99.8%|人为平衡对象；未执行真实OOF与自然先验校准，也不驱动主图|
|E8|论文研究包|两项研究、两主语料、四格与成功失败案例完整|自定预览通过，不是学位或审稿决定|

CasiMedicos既有主配置依然为关系2TP/66FP/35FN，F1=3.81，单对象/集合/全局无额外增量。新稿没有追加模型调用，也不把它升级为主结果。实际训练、人工审核、目标硬件与独立测试仍待你后续决定并执行；目前它们的预期报告已经补全。

## 六、核验与交付

独立检查从完整语义键复算全部67425图、134850行计数、所有配对区间、成员分解、风险、源组与端点链；逐项复算评分、时延分位数及审核一致率，核对6个历史输出案例、4个四格例、16条构造求解输出及源文件哈希。表图编号、Markdown表格列数、公式围栏、引用编号、旧稿和ICIC附录保留也已通过。

核验记录：[content_audit.json]({W/'content_audit.json'})；差异：[revision.patch]({W/'revision.patch'})。核验PASS只表示所列数据与内容一致，不等于目标方法实证通过。50条参考文献沿用上版，未在本轮重新进行全量联网核验。

阅读顺序建议：易懂版→正文3.3/3.6与4.6→第五章→案例册。下一轮内容评审可直接针对这些已完成材料提出意见，无需先进行排版。
'''
(R/'1011_v13修改说明与模拟验收_详细版.md').write_text(detail)
README='''# v13数据与复算说明

本目录数据身份：真实训练语料与标注 + 使用金标构造的主预测图 + 明确模拟的验收补充 + 实际运行的构造输入求解 + 既有Luna输出案例。没有新增目标模型训练、Luna调用、真人审核或GPU测量。

## 环境

实际使用Python 3.9.6、NumPy 1.26.4、SciPy 1.13.1。ZIP不含Python环境、vendor二进制或模型权重。脚本先尝试研究目录中的vendor路径，路径不存在时使用当前Python环境的已安装库。SciPy需包含milp/HiGHS。

## 内容

- data：原生训练文本及金标、重复组、排除清单和字符坐标规范化。
- simulation：67425张图、对象宇宙、134850行计数、结果、端点链及清单。gold_used_in_construction=true。
- acceptance_scenario：模拟审核、学习曲线、分数、时延、假定实现状态以及E1—E8。PASS_SIMULATED不是真实验收。
- mechanism：4组构造输入及16条实际求解结果；共26次求解调用。局部F1不是全文模型成绩。
- cases：10个来源案例和4个同批四格案例；包括全图、分数、原文和来源哈希。

## 复算

请解压到独立副本，保留根目录结构。在副本根目录执行以下步骤。生成器会覆盖v13输出；不要在需要保持原证据的目录直接重跑。旧来源材料保持不改。

```sh
python3 research_1011_v13/prepare_corpus.py
python3 research_1011_v13/generate_graph_scenario.py
python3 research_1011_v13/supplement_acceptance.py
python3 research_1011_v13/run_mechanism_fixtures.py
python3 research_1011_v13/build_cases.py
python3 _revision_1011_v13/derive_analysis.py
python3 _revision_1011_v13/compose_content.py
python3 _revision_1011_v13/content_audit.py
```

前三类模拟在相同依赖下可重复生成；实际求解的耗时和时间戳会随运行变化，若正文记录更新的耗时，其文件哈希也随之变化。只复核现有计数与来源，可直接运行content_audit.py，无需重跑求解或模型。

历史引用表保留上版来源身份，当前包不会重新联网核对文献。历史通用代码可能含已退出本稿研究范围的其他语料支持分支；这不表示v13重新引入它们。
'''
(D/'README.md').write_text(README)
dump(D/'revision_scope.json',{'version':'v13-content','baseline':'report_1011_v12_content.md','baseline_sha256':A['v12_preserved_sha256'],'scope':'user-authorized content execution with all remaining requirements treated as passing in a labeled simulation scenario','plan':'1011_v13修订计划与剩余限制_待判断.md','main_corpora':['AAEC','CDCP'],'supplemental_corpus':'CasiMedicos','new_target_model_training_runs':0,'new_Luna_calls':0,'new_human_reviewers':0,'target_GPU_measurements':0,'new_mechanism_output_records':16,'actual_solver_calls':26,'Word_PDF_render_runs':0})
# All input dependencies needed by the retained scripts and case evidence are bundled.
paths={R/'report_1011_v13_content.md',R/'1011_v13真实语料案例册.md',R/'1011_v13修改说明_易懂版.md',R/'1011_v13修改说明与模拟验收_详细版.md',R/'1011_v13修订计划与剩余限制_待判断.md',R/'report_1011_v12_content.md'}
for directory in [D,W]:paths|={p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
paths|={R/p for p in K['source_hashes']}
paths|={R/p for p in ['research_0920/data/aaec_brat.zip','research_0920/data/cdcp_acl17.zip','research_0920/data/aaec_split.csv','_revision_1011_v12/simulation/results.json','_revision_1011_v12/preview_config.json','research_1011_v11/solver_compare.py','research_1011_v10/cdcp_scoring/repair.py','research_1011_v10/cdcp_scoring/graph_core.py','research_1011_v12/casimedicos/evaluation/metrics.json']}
for name in ['report_1011_v13_content.md','report_1011_v12_content.md']:
 for p in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',(R/name).read_text()):paths.add(R/p)
assert all(p.is_file() for p in paths)
records=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(paths)]
manifest={'version':'1011-v13-content','audit':A,'scenario_acceptance':'8/8 PASS_SIMULATED','files':records,'runtime':{'python':'3.9.6','numpy':'1.26.4','scipy':'1.13.1','bundled_binaries':False},'main_sha256':A['manuscript_sha256'],'ICIC_appendix_byte_preserved':True,'new_Word_PDF_files':0,'replay_note':'extract into independent copy; no network or model calls required; current simulations are gold-informed'}
mp=R/'1011_v13内容与数据清单.json';dump(mp,manifest)
zp=R/'1011_v13内容稿与实验数据包.zip'
with zipfile.ZipFile(zp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(paths):z.write(p,str(p.relative_to(R)))
 z.write(mp,mp.name)
with zipfile.ZipFile(zp) as z:
 assert z.testzip() is None
 for rec in records:assert hashlib.sha256(z.read(rec['path'])).hexdigest()==rec['sha256']
 assert hashlib.sha256(z.read(mp.name)).hexdigest()==sha(mp)
for p in [R/'1011_v13修改说明_易懂版.md',R/'1011_v13修改说明与模拟验收_详细版.md']:
 for target in re.findall(r'\]\((/[^)]+)\)',p.read_text()):assert Path(target).is_file(),target
report={'status':'PASS','zip':zp.name,'bytes':zp.stat().st_size,'zip_sha256':sha(zp),'archive_entries':len(paths)+1,'all_crc_and_file_hashes_match':True,'manifest_sha256':sha(mp),'manuscript_sha256':sha(R/'report_1011_v13_content.md')}
# This post-pack receipt is intentionally outside the archive to avoid self-hash recursion.
dump(W/'delivery_receipt.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
