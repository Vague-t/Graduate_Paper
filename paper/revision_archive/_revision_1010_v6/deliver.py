from pathlib import Path
import hashlib,json,re,zipfile
W=Path(__file__).resolve().parent;R=W.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda n:json.loads((W/n).read_text())
a=read('final_audit.json');r=read('revision_audit.json');n=read('numerical_audit.json');v=read('visual_review.json');d=read('author_decisions.json')
assert a['mechanical_checks']=='PASS' and r['passed'] and n['passed']
source=R/'report_1010_v6_full.md';old=R/'report_1010_v5_full.md';word=R/'report_1010_v6_full.docx'
assert a['source_sha256']==r['source_sha256']==n['source_sha256']==sha(source)
assert d['comparison_priority']=='A1' and d['cost_scope']=='B1'
assert v['all_pages_reviewed'] and v['pdf_sha256']==a['pdf_sha256'] and v['pages']==a['pages']
assert sorted(x['page'] for x in v['reviewed_pages'])==list(range(1,a['pages']+1))
for x in v['reviewed_pages']:assert sha(W/'render_final'/f"page-{x['page']}.png")==x['sha256']
lines=source.read_text().splitlines()
def link(label,needle):
    found=[i for i,x in enumerate(lines,1) if needle in x];assert found,(label,needle)
    return f'[{label}]({source}:{found[0]})'
def main_chars(p):
    t=p.read_text();return len(t[t.index('## 第一章'):t.index('## 参考文献')])
before,after=main_chars(old),main_chars(source)
report=f'''# 1010 v6 评审修改概览与未改事项

本轮依据[1010-v5评审]({R/'1010_v5全局评审与完整修改建议.md'})，先逐段通读v5全文2099行，覆盖中英文摘要、六章、49条参考文献及附录A—H，再做局部修订。作者明确选择“两项均按推荐”，因此按A1统一核心比较职责，按B1将第五章限定为训练完成后的在线取舍。所有旧版正文、Word、评审及原始情景记录保留。

本轮主要技术意见均有正文依据，没有需要直接否决的条目。局部求解是否退为可选方案、第五章是否合并，仍属于真实结果取得后的条件判断，本次没有提前改变章节主线。真实训练、语义审核、外部系统运行与实际ILP均未新增，文字问题的解决不计作实证完成。

## 一 作者决策与落实

|作者选择|本版落实|解释范围|
|:---|:---|:---|
|A1 按现有贡献统一关键比较|训练侧以T-B检验数据构造整体，以T-E检验同数据学习增量；推理侧以RelationOnly和单对象动作检验组件可变性与集合表达，全局ILP检验求解策略取舍，分步策略作为共同决策的补充比较|保留分步结果及区间；未新增模拟显著性。关键比较的正式报告须包含效应量、配对区间、错误代价和成本。|
|B1 限定为训练完成后的在线取舍|5.3标题、开头、解释与相关摘要和总结同步；在训练检查点已经可用时比较关系F1和在线平均时间|不回答训练摊销、服务规模或全生命周期总成本；不将H.2旧固定尝试轨成本填入匹配主成绩。|

## 二 修改概览

精确变更记录包含29组局部替换，另有版本与图片路径更新；没有增加方法、表图或模拟成绩。第一至六章由{before:,}字符调整为{after:,}字符，净增加{after-before:,}字符，包含Markdown标记，不是Word字数。增加主要用于补齐配置状态与核心比较的报告职责，其余通过替换原句完成。

|评审问题或通读发现|处理结果|新版位置|
|:---|:---|:---|
|摘要、统计方案和第四章的关键比较不一致|已同步A1，区分贡献检验、求解采用和补充策略比较|{link('中英文摘要','## 摘要')}、{link('2.6.3','#### 2.6.3')}、{link('3.6','### 3.6')}、{link('4.6','### 4.6')}、{link('6.1','### 6.1')}与{link('H.5','### H.5')}|
|有区间的分步比较占据优先位置|职责已调整，原数字和区间保留。RelationOnly与单对象动作现有人工材料只有均值差，明确正式运行时补齐同口径报告|{link('4.6.2','#### 4.6.2')}；不以是否已有区间决定比较重要性，不把未校正区间合并为机制确认|
|2.3让人误以为可找到实际权重和环境|已改为正式运行前登记，骨干名称明确为参考设置|{link('2.3','### 2.3')}、{link('3.2.1','#### 3.2.1')}|
|表2-2与完整运行配置混同|明确表中为人工情景参考值，集中列出未绑定检查点、损失系数及选择方案|{link('2.6.2','#### 2.6.2')}；配套配置增加明确待绑定字段，未填造实际值|
|损失系数描述像已完成开发选择|改为正式运行前登记候选范围与选择规则，经开发选择后冻结|{link('3.4.3','#### 3.4.3')}；公式与原有源权重含义保持|
|算法中等权取批次可能混淆目标权重|第27行改为按源文档等频取批次；有增强文档仍保留1＋ρ的基础目标系数总和|{link('算法3-1','**算法3-1')}；仅措辞澄清，不改变梯度路径或算法步骤|
|T-A表述可能把普通增强收益全归给新文本|改为普通增强的整体作用，与T-B的源选择及重加权解释一致|{link('表3-2','表3-2 训练侧')}|
|5.3承诺训练投入与成本选择，但表中只有在线平均时间|已按B1收窄任务承诺；保留给定条件下的数值和无法直接外推的限制|{link('第五章','## 第五章')}、{link('5.3','### 5.3')}、{link('5.4','### 5.4')}，并同步摘要、1.4、6.1与F.3|
|旧资料核查的本轮措辞随版本重复|改为前次资料核查及既有记录|{link('G.2','### G.2')}；未将旧核查冒充本轮重新验证|

本版关键比较的职责为：

|比较|直接回答的问题|不能据此单独推出的结论|
|:---|:---|:---|
|T-B 完整增强基础损失对QOS式适配|数据构造整体是否有作用|新表达独立于源选择和额外曝光的收益|
|T-E 同增强集合的基础、加头和加对齐|辅助监督与成对项各自的增量|整套T1总差值全由对齐产生|
|BR-J对RelationOnly|允许组件变化的修正策略是否有作用|每个候选、评分或闭合模块的独立贡献|
|BR-J对单对象动作|集合动作的额外表达是否有作用|集合动作在所有自然错误中均必要|
|BR-J对同目标全局ILP|质量、错误代价及资源条件下如何选择求解策略|局部和全局同可达域，或局部必然更快更安全|
|BR-J对组件优先分步策略|共同决策与该分步策略的整体差异|仅执行顺序的独立因果效应|

## 三 未修改和未执行的事项

|事项|本轮处理及原因|完成条件|
|:---|:---|:---|
|真实监督漂移与目标系统的初始错误|未执行。已有H.1采集方案，无需再增加问题规模小节；现有模板不能补出真实发生率|固定真实文档、普通改写及OOF输出，保留盲审、裁决、分层与全部失败；诊断不支持时收缩设计|
|完整可运行配置和贯通验收|仍未闭合。增强和验证模型、评分器等检查点及新增系数未绑定，本轮只能使文字与这一状态一致|冻结数据及折清单、模型身份、提示采样、系数选择、校准、优化器和资源上限；用非零损失检查实际梯度，运行真实求解及失败回退|
|裁剪前资源与局部全局采用价值|未执行。4096补充槽位不限制裁剪前枚举和评分；预算函数不是实际优化器|测量准备、枚举、评分、求解、尾延迟、失败和误改，保留求解证书及有效界，再决定采用策略|
|任务兼容的外部系统比较|未执行。不恢复具名假想成绩，也不换成匿名假想分数|完成至少一个任务兼容系统的版本固定、转换核查及真实输出评价|
|第五章独立综合认识及同文档案例|未取得。四格总分与H.8非唯一性说明不足以识别真实对象作用|复用同批真实输出，对齐完整对象并取得一项可核查的综合认识，保留少量原文和前后案例，不预设互补或正交互|
|训练投入、服务规模与摊销阈值|按B1不纳入本轮第五章的结论职责|以后若要研究，应另取得匹配训练轨及部署成本；当前不调用H.2的旧轨成本补位|
|同源原文重复曝光对照|未新增。现有T-B只解释数据构造整体，评审也认可无需强制增加|只有重新主张新表达独立收益时，才需固定来源、权重与更新数做相应对照|
|预算模拟敏感性和更多模拟结果|不追加。本稿不把模拟模型本身作为研究对象，也不从其排序确定采用价值|后续优先取得真实输入输出；不为维护局部主方案寻找有利假设|
|删除局部方案或合并第五章|暂不实施，这是实测后的条件建议|真实结果不支持当前职责时，再由作者决定简化或合并；篇幅本身不作为判断依据|
|新增文献认证及四篇参考论文再审|未执行。本轮已通读自身论文，未另做49条参考文献逐字段或四篇PDF的独立复审|保留原引用身份，不声称取得新的穷尽性新颖性结论或正式学位评定依据|

两项研究与六章结构继续保留。影响域、NONE、原生超边、完整对象、累计与净编辑预算、分步提交、最小合法化扩域、代理效用与真实F1的边界没有重新定义。术语沿用原稿，不为句式变化引入新的方法名。

## 四 核验结果

|核验|结果及范围|
|:---|:---|
|全文阅读与改动来源|[阅读记录]({W/'full_read_record.json'})绑定v5 SHA-256及完整行范围；[29组变更]({W/'changes.json'})和[文本差异]({W/'revision.diff'})定位实际替换|
|原始材料保留|[保留性核验]({W/'revision_audit.json'})通过：v5正文、Word、评审不变；13个主／补充情景数据文件及生成器不变|
|公式、图表与引用|32个陈列公式逐字保持；11张使用中PNG字节保持；47张编号表数值不变；49条参考文献及附录E保持。3段算法仅有第27行采样措辞变化|
|数值复算|[数值核验]({W/'numerical_audit.json'})通过，28,728行计数、84个均值／标准差单元、28个配对及交互区间一致；没有生成新成绩|
|Word结构与排版|最终{a['pages']}页、{a['native_math_objects']}个原生数学对象、{a['verified_page_labels']}个标题／题注页码及{a['toc_cached_entries']}个目录缓存条目核对通过；全部{a['pages']}页实际逐页查看，未见裁切、重叠或缺字|
|证据范围|以上检查验证文稿、算术及排版，不证明模型效果、局部采用价值或研究已经完成；本轮真实模型／求解器运行增量为0|

## 五 版本记录

|文件|SHA-256|
|:---|:---|
|v5 Markdown 保留|{sha(old)}|
|v5 Word 保留|{sha(R/'report_1010_v5_full.docx')}|
|本轮评审 保留|{sha(R/'1010_v5全局评审与完整修改建议.md')}|
|v6 Markdown|{sha(source)}|
|v6 Word|{sha(word)}|

交付为v6 Word、对应Markdown与本说明。此前待决策说明作为过程记录留存，两项选择现已落实，不再有本轮待定的写作范围事项；正式实验的模型和资源选择仍应在启动时另行冻结。
'''
out=R/'1010_v6评审修改概览与未改事项.md';out.write_text(report)
interim=R/'1010_v6全文润色判断与待决策事项.md'
intro=f'> 状态更新：作者已选择A1＋B1，两项已落实。最终修改、未执行事项及核验结果以[本版修改概览]({out})为准；下文保留决策前记录。\n\n'
old_interim=interim.read_text()
if not old_interim.startswith('> 状态更新：'):interim.write_text(intro+old_interim)
for target in re.findall(r'\]\((/[^)]+)\)',report):
    m=re.match(r'^(.*?):(\d+)$',target);p=Path(m.group(1) if m else target);assert p.is_file(),p
    if m:assert 1<=int(m.group(2))<=len(p.read_text().splitlines())
files=[source,word,out,interim]+[W/x for x in ['prepare.py','compose_revision.py','audit_revision.py','audit_scenario.py','build_docx.py','deliver.py','revision_audit.json','numerical_audit.json','final_audit.json','visual_review.json','writing_audit.json','revision.diff','reference_config.json','template-evidence.json','page_map.json','page_map_audit.json','table_splits.json','author_decisions.json','full_read_record.json','changes.json']]
(W/'delivery_manifest.json').write_text(json.dumps({'version':'1010-v6','real_model_runs':0,'files':{str(p.relative_to(R)):sha(p) for p in files}},ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(word) as z:assert z.testzip() is None
print(json.dumps({'overview':str(out),'pages':a['pages'],'main_chars_before':before,'main_chars_after':after,'manifest_files':len(files)},ensure_ascii=False))
