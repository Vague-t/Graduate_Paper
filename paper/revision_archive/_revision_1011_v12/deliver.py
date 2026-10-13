from pathlib import Path
import json,hashlib,zipfile,re
R=Path(__file__).resolve().parent.parent;W=R/'_revision_1011_v12';A=json.loads((W/'content_audit.json').read_text());assert A['status']=='PASS'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'report_1011_v12_content.md')==A['manuscript_sha256']
easy=f'''# v12内容改进说明：易懂版

本版在v11基础上修改内容，保留旧版本；没有制作或渲染Word/PDF。完整正文为[report_1011_v12_content.md]({R/'report_1011_v12_content.md'})。

## 1. 论文现在主要讲什么

仍是两项研究：训练时，学习“不同说法里的同一个论辩作用”；推理时，修改一个组件后，把受影响的关系一起处理。现在不再要求复杂筛选、集合动作或局部搜索每一项都必须胜过简单方案。

训练部分有一处实质修改：不能确认的改写关系不拿来教模型，也不当作“没有关系”。原文继续提供完整答案，改写文只提供检查通过的组件和关系因素。这样可以保留有用的表达变化，减少一项审核待定就丢掉整篇改写的情况。这是本版的新设计，尚未完成Qwen训练。

推理部分先改善输入：组件和关系分别解析，关系格式错误不再连带丢弃合法组件；保留原生类型，CDCP直接提出完整联合源。未评分的对象保持未知，不能用默认低分驱动删除。小池可以直接全局选择，大池再考虑局部预算，单对象足够时就不强制使用集合动作。

## 2. ICIC数值怎样对齐

现在的共同起点是ICIC完整训练和修正系统；四格分别为继承系统、仅新训练、仅新修正、二者结合。模拟数字从整数计数重新生成，摘要、主表、差值、区间及第五章成员分析一起更新。

旧协议尺度的正向目标情景中，新框架的AAEC组件／关系F1为85.18／68.17，CDCP为78.27／41.46，均高于对应ICIC引用值。它们围绕此前讨论的85.20／68.20、78.30／41.50目标中心生成，整数化后略有偏差。

严格原生关系另列一套结果，尤其CDCP必须匹配完整联合源，不能直接与旧38.17混比。所有新主结果仍是模拟预览，不是由Luna低分推算出的Qwen成绩。

## 3. 数据集如何处理

ArgUNSC已经从v12全文、表格、引用和后续实验计划中移除，旧历史文件保留归档。主实验集中AAEC、CDCP。

CasiMedicos已进一步做真实评分和最终输出验证。固定同一8篇，对166个组件和6390个完整关系逐项给分，再运行冻结规则。

|指标|旧初始图|新主配置|
|:---|:---|:---|
|组件F1|8.25|23.60|
|关系F1|0.00|3.81|
|正确关系TP|0|2|
|错误关系FP|4|66|
|遗漏关系FN|37|35|

候选修复确实让少量正确关系进入最终输出，但误判仍很多。单对象、集合局部和全局没有再带来收益；预先登记的较高阈值0.65反而把两条正确关系也去掉了。因此现在保留为补充诊断，不升级为主结果或继续盲目扩样。下一步若继续，优先学习原生边界、类型和评分。

本次初始化已在候选池中最大化组件代理分数，分项非降门又限制后续替换，因此“修正无增量”只说明这一具体起点，不能解释为三个算法通常等价。

## 4. 本轮省去了什么、检查了什么

没有排版、分页、目录更新或整篇图片渲染。完成了{A['synthetic_count_rows']:,}条模拟计数复算、人工对象成员核对、真实输出严格计数、公式与配置一致性、交叉引用及旧版本保留检查。全文为6章、41张有编号表、50条参考文献；这些文档检查不等于正式模型训练完成。
'''
detail=f'''# v12逐项修改与后续建议：详细版

绑定稿件：[report_1011_v12_content.md]({R/'report_1011_v12_content.md'})；SHA256 `{A['manuscript_sha256']}`。本轮范围为内容修订及CasiMedicos补充诊断，不制作Word/PDF。旧v11字节未变，ICIC历史表完整保留。

## 一、已落实的修改

|问题|v12改动|正文位置|
|:---|:---|:---|
|完整筛选缺少额外收益证据|降为可选整例拒绝对照；默认建立可靠因素掩码|3.3.3、3.6.5|
|简化检查后如何避免继续学习未知关系|默认只对原文计算完整图生成损失；变体只参与掩码内头监督及对齐|3.4.2—3.4.3、算法3-1|
|新增学习收益难以归因|同数据比较无成对、仅组件成对、组件及关系成对；推理I0固定|3.6.1—3.6.3|
|关系解析失败损失所有成分|组件独立解析并保护有效原生对象；关系失败单列|4.2.1—4.2.3|
|全类型多源组合过大|默认有限跨度／类型及完整源组提案；全组合保留为规模界和消融|4.2.4—4.2.5|
|默认低分可能触发误删|评分缺失拒绝相关事务；有效低分由OOF和校准解决|4.4.1—4.4.2|
|不必坚持集合局部胜过全局|依赖闭合为共同接口；规模路由和动作粒度由冻结开发规则选择|4.5.6|
|ICIC参照不清楚|T0/I0改为完整继承系统；历史引用、兼容目标、严格原生轨分开|2.5.1、第五章|
|移除ArgUNSC|本版全文及引用中移除，未删除历史证据|全文及本修改记录|
|Casi候选入池不等于输出改善|完成逐项评分、最终输出、阈值敏感性和逐篇计数|4.6.6、D.3|

## 二、训练设计的关键边界

默认关系审核包含全部受影响正关系及内部／跨边界各最多4个NONE，记录审核覆盖。原标签获认可、改写状态保持且完整端点对应有效时，关系掩码才为1；分歧和未审核都不重标为NONE，原文金标保持不变。只读端点也在全文上下文中检查角色。

默认完整图生成目标只作用于原文；增强视图仍进入共享表示，但仅提供有效因素监督。这个改动避免“正文说不学习未确认标签，生成目标却继续使用完整输运图”的矛盾。增强整图生成只作为全部因素确认后的另命名版本，本版不默认启用。

现有64个Luna变体没有检出关系漂移，完整和简化筛选拒绝同一成分疑似变化例。v12因素掩码属于据此提出的设计调整，并非旧诊断已经验证其训练收益。完整筛选在模拟中也没有被强制安排为最佳。

## 三、推理设计与未完成实现

补充跨度64、每跨度前2类型、CDCP补充完整源组与目标最多256、裁前50000槽位及小池2500对象变量阈值均为内容稿设计假设。原始保护对象不因补充上限被裁掉。正式数值须从训练侧资源与覆盖测量固定；这些字段不构成已部署配置。

开发侧同时选择质量、原TP损失及成本，预览TP损失目标为5%，不足以评估或没有合格配置时选择不修正。阈值不在测试集重调。该规则是经验约束，不提供测试F1单调保证。

局部采用累计编辑，全局采用终态净编辑；相同24／96数值不意味着相同可行域。本文保留包含关系及证书口径，不把大预算自动称为全局最优。

## 四、数值重建与ICIC比较

共重建{A['synthetic_count_rows']:,}条逐文档整数计数和{A['synthetic_identity_records']}组人工对象成员记录。四格、消融、TP恢复／损失、CDCP源成员分组、文档配对区间与交互从同批记录读取。固定三个模拟种子条件下重采样2000次，区间不解释为真实训练的置信度。

严格原生轨的完整框架AAEC组件／关系为85.19／67.78，CDCP为78.29／39.86；相对同轨继承基线，关系增量为3.43和2.99个百分点。兼容旧协议尺度的结果另为85.18／68.17、78.27／41.46。这两套人工对象不是同一图的投影，不能跨表计算提升。ICIC原表值只作来源引用，尚未在共同代码上复跑。

匿名外部对照也重新生成整数记录，只代表对照职责，不绑定具名论文。旧OOF人工错误链保留为独立指标示例，不与v12主表合并；成本秒数为显式假设，不编造P95或目标GPU测量。旧版本的独立压力情景继续归档。

## 五、CasiMedicos真实验证结果

冻结同一8篇、C层候选、11项gpt-5.6-luna／low任务；166组件和3195槽位全部显式评分，每槽Attack／Support各一分，共6390关系对象。评分者未读取金标、初始图或期望增益，拆批没有取高分重采样。模型精确快照、温度、采样种子及token未由工具暴露。

两个事先固定阈值0.50／0.65，各运行初始化、SingleObject、BRJ-lite、GlobalILP-lite：共64条输出记录，其中16条初始化、48条修正运行。主配置组件TP/FP/FN为19/52/71、关系为2/66/35；旧初始图为4/3/86和0/4/37。只有318_140的关系F1提高，其他7篇不变。

组件评分AUROC为0.393，正确对象均分0.658低于错误对象0.725，说明模型未可靠识别严格边界和类型。关系AUROC为0.756，但6390候选中只有13个正例；大于0.5的分数包括7个正例、337个负例。不能用较好的排序值掩盖最终低精确率。

三个修正器在主配置均无额外增量。该初始化先最大化组件分项，而分项非降门把后续变化限制在同组件效用替换中，因此结论只适用于这个受限起点。更高阈值丢掉两条正确关系，也没有形成稳健的改进。当前不把Casi升级为主实验，后续必须先改善监督评分，并在独立文档上检验。

## 六、核验与后续修改建议

已独立复算全部人工计数及成员、真实8篇的完整对象计数，并检查冻结文件哈希、初始组件优化的三个穷举例、表图引用、50条参考文献编号及旧版保留。核验记录：[content_audit.json]({W/'content_audit.json'})；文本差异：[revision.patch]({W/'revision.patch'})。

最优先完成AAEC/CDCP的ICIC继承复现、原生候选和OOF评分，再运行同数据学习、同候选修正及四格。没有完成目标Qwen训练、人工审核、旧协议转换验收或v12全部新模块实现。不要求真实实验复制正向模拟，结果不足时采用简化方案。

本轮Word/PDF渲染次数为0。对方法和数字达成稳定版本后，再集中排版、更新目录和做视觉核验，避免内容调整反复触发全篇分页返工。
'''
paths=[]
for name,body in [('1011_v12修改说明_易懂版.md',easy),('1011_v12修改说明与后续建议_详细版.md',detail)]:
 p=R/name;p.write_text(body);paths.append(p)
files={R/'report_1011_v12_content.md',base if False else R/'report_1011_v11_full.md',*paths}
for root in [W,R/'research_1011_v12']:
 files|={p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.zip','.png']}
deps=['research_1011_v10/cdcp_scoring/graph_core.py','research_1011_v10/cdcp_scoring/repair.py','research_1011_v10/new_corpora/candidate_pools.json','research_1011_v10/new_corpora/results/run_001/common_initial_states.json','research_1011_v11/candidate/evaluation/source_gold.json','research_1011_v11/candidate/evaluation/coverage.json','research_1011_v11/solver_compare.py','research_1011_v11/solver/evaluation/metrics.json','research_1011_v11/simulation/oof_error_records.json','research_1011_v11/simulation/preview_config.json']
files|={R/p for p in deps};files|=set((R/'research_1011_v11/candidate/constructed').glob('casimedicos_*.json'))
files|={R/p for p in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',(R/'report_1011_v12_content.md').read_text())}
manifest={'status':'CONTENT_AND_DATA_AUDITED_NO_RENDERING','files':{str(p.relative_to(R)):sha(p) for p in sorted(files)},'audit':A,'runtimes':'Python 3, NumPy, SciPy; vendor/runtime binaries excluded','scope':'new v12 plus exact prior files referenced for comparison/recount; historical mixed-corpus files preserved as dependencies, no new retired-corpus work','replay':'Scores are immutable. run_casi/evaluate_casi use exclusive output creation; replay in a separate copy with new result directory. Do not rerun model scoring to reproduce existing outputs.'}
mp=R/'1011_v12内容与数据清单.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');files.add(mp)
zip_path=R/'1011_v12内容稿与实验数据包.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(files):z.write(p,str(p.relative_to(R)))
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 for p,h in manifest['files'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
print(json.dumps({'manuscript':str(R/'report_1011_v12_content.md'),'reports':[str(p) for p in paths],'zip':str(zip_path),'files':len(files),'zip_bytes':zip_path.stat().st_size,'sha256':sha(zip_path)},ensure_ascii=False,indent=2))
