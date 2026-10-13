"""Create the version-bound change overview after all document checks pass."""
from pathlib import Path
import hashlib,json,re,zipfile
W=Path(__file__).resolve().parent;R=W.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda n:json.loads((W/n).read_text())
a=read('final_audit.json');r=read('revision_audit.json');n=read('numerical_audit.json');v=read('visual_review.json')
assert a['mechanical_checks']=='PASS' and r['passed'] and n['passed']
source=R/'report_1010_v5_full.md';old=R/'report_1010_v4_full.md'
assert a['source_sha256']==r['source_sha256']==n['source_sha256']==sha(source)
assert v['all_pages_reviewed'] and v['pdf_sha256']==a['pdf_sha256'] and v['pages']==a['pages']
assert sorted(x['page'] for x in v['reviewed_pages'])==list(range(1,a['pages']+1))
for x in v['reviewed_pages']:assert sha(W/'render_final'/f"page-{x['page']}.png")==x['sha256']
lines=source.read_text().splitlines()
def link(label,needle):
    found=[i for i,x in enumerate(lines,1) if needle in x];assert found,(label,needle)
    return f'[{label}]({source}:{found[0]})'
def file(label,name):return f'[{label}]({W/name})'
def main_chars(p):
    t=p.read_text();return len(t[t.index('## 第一章'):t.index('## 参考文献')])
before,after=main_chars(old),main_chars(source)
report=f'''# 1010 v5 评审修改概览与未改事项

本说明对应用户提供的《1010 v4 全局评审与完整修改建议》，修订基线为1010-v4，交付为1010-v5。此次重点是调整材料职责与结论强度：删去具名外部假想成绩，将模板与预算示例移入附录，将对象补全改为非唯一性说明，并压缩重复论述。没有继续按意见新增模拟成绩表；v4正文、Word、评审和全部原始记录保留。

本版仍是模拟数据演示稿。真实训练、语义审核、外部系统推理及优化器运行均未新增。下表中的“已改”表示对应文稿处理完成，不表示实证研究缺口关闭。

## 一 修改概览

正文第一至六章由{before:,}字符压缩为{after:,}字符，减少{before-after:,}字符；该口径包含Markdown标记，不等于Word字数。全稿表格由50张减为47张，图由12幅减为11幅；最终Word为{a['pages']}页。六章框架及两项方法的分工保留。

|评审主题|处理结果|新版位置与具体变化|
|:--|:--|:--|
|具名外部占位不承担方法定位|已改|删除原4.6.7与表4-10，摘要、章末和第六章不再使用假想外部分数、假想排名或“有更强占位系统”作论据；{link('附录G.2—G.4','### G.2')}只保留接入候选、兼容核查及待取得结果的要求|
|预算假设不能升级为采用结论|已改|{link('4.6.6','#### 4.6.6')}改为“预算条件的分析示例”，原资源表、预算表和曲线移至{link('H.7','### H.7')}；明确时间斜率、完成度插值及其未模拟的搜索过程，不在摘要或总结中选定36秒大图优势或局部策略的优先级|
|对象补全不是独立综合发现|已改|删除原表5-4、5-5及重叠比例、合成坐标案例的正文论证；{link('5.2','### 5.2')}说明聚合计数的可识别边界，{link('H.8','### H.8')}用交集范围证明对象补全非唯一，不再把353／505当作方法发现|
|模板筛选与主成绩不构成同源证据链|已改|原表3-10移为{link('表H-2','表H-2 共同池')}；{link('3.6.2—3.6.6','#### 3.6.2')}区分因素审计、模板池和训练成绩。正文保留联合阅读变化、漂移与覆盖的方法，不以0.75或0/65证明多样性或审核安全|
|源筛选与目标重加权混合|已改解释，保留目标|{link('3.4.3','#### 3.4.3')}及T-B将结论限定为文本、源选择与重加权的整体效应；T-E继续固定增强集合、源权重及更新条件。没有将等频采样改称目标等权|
|第四章需突出复杂度换来的作用|已改写作，实测待完成|{link('4.6.2','#### 4.6.2')}优先解释BR-J相对RelationOnly的3.59／4.39及相对单对象动作的1.99／3.01个关系F1百分点。数值从原人工主表重算，分别对应组件可变性与集合表达，不新增成绩|
|执行语义重复挤占主线|已改|{link('4.5.2','#### 4.5.2')}保留动作、额度与提交边界，将具体排序、状态键、缓存游标及计费规则集中到{link('B.3','### B.3')}；三段算法原文不变。删除与表4-8重复且控制量不同的旧轮数—时间图4-4，图源在v4继续存档|
|第五章需三个相互连贯的问题|已改|{link('第五章','## 第五章')}重组为5.1条件增量、5.2对象作用与聚合边界、5.3配置取舍；旧5.3解释边界和5.5源成员分组并入5.2。配置节不再重复局部／全局预算推演，章末改为5.4|
|主张应少于表格，不能以让步代替产出|已改|{link('摘要','## 摘要')}、英文摘要及{link('3.7','### 3.7')}、{link('4.7','### 4.7')}、{link('5.4','### 5.4')}、{link('6.1','### 6.1')}先说明两项设计处理的具体问题，再交代比较职责与尚未验证的效应；不将“非全面领先”“条件选项”“不能协同”列作独立发现|
|章节介绍与模拟附录职责|已改|{link('1.4','### 1.4')}及附录F索引同步更新；附录H将正式采集方案与模板指标、预算假设、对象非唯一性示例分开；{link('H.5','### H.5')}取消“当前模拟已选择条件选项”的预设|
|等时限名称及续表|已改|原“全局等时限”“全局ILP等时限”统一为“全局等求解预算”“全局ILP等求解预算”；同端到端时限仅用于另行定义的预算轨。表4-3跨页处增加明确续表题注，更新表图清单及交叉引用|

## 二 未改与未执行的事项

|项目|本轮决定及原因|后续完成条件|
|:--|:--|:--|
|真实监督漂移和端点相关错误诊断|未执行。现有材料没有本轮所需的真实改写、审核判断与目标模型OOF输出；文稿修订不能据模板生成器补出问题发生率。1.1、3.1、4.1保留这一未验证前提|按H.1固定真实文档、来源及分层，保存因素标签、原始预测和候选缺失；诊断不足时简化机制|
|真实增强学习及同源质量—收益连接|未执行。旧主成绩和模板筛选使用不同生成机制，本轮明确拆开其结论职责，未改写数据来源|绑定同一接受清单、实际训练输入、源权重、模型与评价输出，分别完成T-B和T-E|
|实际BR-J／全局求解及采用优先级|未执行、未定案。预算函数没有实际搜索轨迹、合法图或求解证书；本轮只保留框架及比较要求，不承诺紧预算大图时局部必优|共同候选、评分及明确资源下，记录全部准备、失败、质量、误改、尾延迟与求解状态；允许选择全局或简化局部|
|至少一个真实外部系统比较|未执行。原作者实现、权重、转换器及共同任务输出尚未形成可核查运行。本轮删除假想表，未用匿名假想分数补位|按G.2—G.4固定版本、核查原生任务兼容性，完成原配置核对及共同任务运行；不兼容时保留限制|
|同批四格实际对象发现和真实前后案例|未执行。抽象关系键不是原文预测，不能将其改名为真实对象。第五章目前只解释条件增量、对象识别边界和配置成本|从同文档四格预测对齐完整对象，保留原文及运行身份后报告重叠、损害和案例，不预设互补比例|
|同源原文重加权／重复曝光对照|未新增。评审允许“收窄解释”与“补针对性对照”按主张择需；本轮选择前者，保留现有目标公式，不再把T-B整体差值归给新表达|只有进一步主张新表达独立有效时，固定接受源与权重，用同源原文替换增强视图做直接比较|
|预算模型的速度／质量轨迹敏感性实验|未新增。没有把模拟模型本身设为研究对象，也不再依赖它确定方法定位；继续扩展模拟优势不符合本轮内容取舍重点|若后续研究模拟模型本身，则检查相对速度和质量轨迹的多种设定，并继续区分模拟稳健性与实际求解|
|扩张外部基线、增加第三项创新或强行配平章节|不采用。评审明确不要求上述扩张；六章和两项研究保留，压缩第五章重复内容，不为页数添加结果|两项贡献各有直接比较，综合分析提供额外理解后即可，不以模型或表格数量为完成标准|
|四篇参考学位论文的再次独立审查|未另做。本轮根据用户评审采用问题—设计—比较—结论的组织建议，没有重新核验其学位评定、引用其分数作标准或声称完成新的文献审计|若需逐篇复核，另按原文证据检查；这不影响本轮对自身稿件的内容修订|

以上实证缺口没有被归入已完成研究，也没有转移成一般未来展望；第六章与H.5继续将其列为当前核心验证。

## 三 明确保留的规约

评审第六节认可的内容未因本轮修订反复重设：

1. 训练改变文本、推理改变预测图；组合不是第三项算法创新。
2. 原生组件、完整关系、CDCP超边与历史投影成绩分开；训练辅助概率和推理完整对象概率分开。
3. T-B与T-E职责分开，源目标权重含义保持，32个陈列公式逐字一致。
4. 超边闭合包含组件插入导致事务外已选超边失效的情况，最小合法化扩域规则保持。
5. 顺序基线仍为阶段提交，阶段二失败保留阶段一；对比解释为整体策略，未缩成纯执行顺序因果效应。
6. 全局终态净预算与局部累计编辑预算、有效上界与可行解、代理效用与真实F1的区别保持。
7. 预检失败保留分母，超过3个源成员的空组不填成绩；构造测试不当作模型实验。
8. 模拟披露、不同数据轨的身份、原始计数与旧版本可复查性保持。具名外部占位原记录只作为v4档案留存，不再进入v5论文的研究论证。

## 四 非唯一性复算与文档核验

独立程序没有直接采用评审给出的区间作为结果，而是读取684组对象集合，为每组构造最小及最大共同新增命中集合。保持T0I0、T1I0、T1I1及T0I1的原命中、FP不变，逐项检查四格TP／FP／FN和T1到组合风险不变。得到AAEC范围26—434、CDCP范围158—550，与评审复算一致。见{file('非唯一性核验','nonuniqueness_audit.json')}及{file('构造端点记录','overlap_extremes.json')}。这只支持抽象关系集合上的不可识别性，不证明完整预测图合法或真实语料可行。

|核验项目|结果|
|:--|:--|
|表格与原始数据|{file('修订审计','revision_audit.json')}通过；47张保留表的载荷逐项核对，允许的变化仅为标签、T-B解释和阅读索引；删去的3张表明确登记；全部旧模拟记录及生成器保持原字节|
|旧成绩复算|{file('数值审计','numerical_audit.json')}通过，28,728条计数、84个均值／标准差单元、28个区间保持；新增正文直接差值由原始均值重算|
|核心内容|32个陈列公式、3段算法及附录E逐字保持，49条参考文献保持；11张使用中的PNG与上一版字节一致|
|Word结构|{a['pages']}页、47表、11图、3算法、49条参考文献、{a['native_math_objects']}个原生数学对象；模板页面几何和保留包部件核对通过|
|目录与排版|{a['verified_page_labels']}个标题／题注页码、{a['toc_cached_entries']}个缓存条目一致；全部{a['pages']}页实际逐页查看，未发现裁切、重叠或缺字|
|实证范围|新增真实训练、语义审核、模型推理和求解器运行均为0；本次核验不证明创新性、学位评审通过或未执行的真实效果|

## 五 版本与交付

|文件|SHA-256|
|:--|:--|
|v4 Markdown 保留|{sha(old)}|
|v4 Word 保留|{sha(R/'report_1010_v4_full.docx')}|
|本次依据的评审 保留|{sha(R/'1010_v4全局评审与完整修改建议.md')}|
|v5 Markdown|{sha(source)}|
|v5 Word|{sha(R/'report_1010_v5_full.docx')}|

交付包括修订Word、对应Markdown和本概览。逐项变更可从本说明定位正文，完整文本差异保存在{file('版本差异','source.diff')}。后续实测若改变主要结果，应同时替换对应表图、摘要、结论和采用判断，保留本模拟版本；当前不把逐条写作处理等同于全部研究问题关闭。
'''
out=R/'1010_v5评审修改概览与未改事项.md';out.write_text(report)
for target in re.findall(r'\]\((/[^)]+)\)',report):
    p=Path(re.sub(r':\d+$','',target));assert p.exists(),p
files=[source,R/'report_1010_v5_full.docx',out]+[W/x for x in ['prepare.py','compose_revision.py','audit_revision.py','audit_scenario.py','build_docx.py','deliver.py','revision_audit.json','numerical_audit.json','nonuniqueness_audit.json','overlap_extremes.json','final_audit.json','visual_review.json','writing_audit.json','source.diff','reference_config.json','template-evidence.json','page_map.json','page_map_audit.json','table_splits.json']]
(W/'delivery_manifest.json').write_text(json.dumps({'version':'1010-v5','real_model_runs':0,'files':{str(p.relative_to(R)):sha(p) for p in files}},ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(R/'report_1010_v5_full.docx') as z:assert z.testzip() is None
print(json.dumps({'overview':str(out),'pages':a['pages'],'main_chars_before':before,'main_chars_after':after,'manifest_files':len(files)},ensure_ascii=False))
