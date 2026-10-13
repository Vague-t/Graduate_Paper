"""Deliver the reviewed manuscript, a bounded response, and portable figure sources."""
from pathlib import Path
import hashlib,json,zipfile,re
W=Path(__file__).resolve().parent;R=W.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda n:json.loads((W/n).read_text())
audit=read('final_audit.json');rev=read('revision_audit.json');num=read('numerical_audit.json');visual=read('visual_review.json')
assert audit['mechanical_checks']=='PASS' and rev['passed'] and num['passed']
assert audit['source_sha256']==rev['source_sha256']==num['source_sha256']==sha(R/'report_1010_v3_full.md')
assert visual['all_pages_reviewed'] and visual['pages']==audit['pages'] and visual['pdf_sha256']==audit['pdf_sha256']
assert len(visual['reviewed_pages'])==audit['pages']
for p in visual['reviewed_pages']:assert sha(W/'render_final'/f"page-{p['page']}.png")==p['sha256']
figqa={'figure_count':7,'archetype':'schematic-led composite','backend':'Python matplotlib','width_mm':157,'statistics':'not applicable: method schematics, no empirical results','manually_reviewed':True,'minimum_pdf_glyph_pt':min(x['pdf_min_font_pt'] for x in rev['new_figures']),'figures':rev['new_figures'],'source_preflight_warnings':rev['preflight_warnings_reviewed'],'semantic_scope':'Existing manuscript mechanisms and explicitly constructed teaching examples only'}
(W/'figure_qa.json').write_text(json.dumps(figqa,ensure_ascii=False,indent=2)+'\n')
bundle=R/'1010_v3模型框架流程图源文件.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    for n in ['draw_figures.py','figure_contract.md','figure_qa.json','requirements.txt']:
        z.write(W/n,n)
    z.write(W/'figure_bundle_README.md','README.md')
    z.write(W/'qa_tools/audit_panel_alignment.py','qa_tools/audit_panel_alignment.py')
    for fig in rev['new_figures']:
        for ext in ['svg','pdf','png']:z.write(W/'figures'/f"{fig['name']}.{ext}",f"figures/{fig['name']}.{ext}")
with zipfile.ZipFile(bundle) as z:assert z.testzip() is None and len(z.namelist())==27
source=R/'report_1010_v3_full.md';lines=source.read_text().splitlines()
def link(label,needle):
    matches=[i for i,l in enumerate(lines,1) if needle in l]
    assert matches,(label,needle)
    return f'[{label}]({source}:{matches[0]})'
def local(label,p):return f'[{label}]({p})'
text=f'''# 1010 v3 评审处理与图示重绘说明

本版完成参考配置表号修正、文稿与方法配置身份分离，以及七张模型、框架和流程示意图的重绘。正文主线、方法、结果、评价口径与模拟身份保持。上一轮已解决的文字问题不再列为缺陷；本轮评审提出的四项研究问题仍需真实材料，不能由重绘或措辞调整关闭。

采用nature-writing约束修改范围与证据边界，采用nature-figure的Python流程重绘并检查图示。保留中文学位论文格式；这不是Nature投稿认证，也不代表完成了真实模型实验。原v2文稿、配置、评审和原始情景文件均保持原字节。

## 一 新评审的处理范围

|评审部分|本轮处理|状态|
|:--|:--|:--|
|一 总体判断|保留两项工作及共同依赖主线；停止围绕同组人工数字扩写|已落实编辑范围；研究完成度未提升|
|二 四篇参照论文|采用问题规模、外部比较、同输入输出案例及负面结果的证据组织原则；不照搬其数字、篇章数量或结论强度|作为研究收尾依据；本轮未重新复现或认证四篇论文|
|三 两项工作的价值|保留关系影响域与成对学习、集合事务与联合决策；未改名、加损失或把常规性质拆成新贡献|保留；实际价值仍待验证|
|四 四个核心问题|见下一节逐项证据需求和不支持时的处理|四项均未由本次编辑关闭|
|五 可认可的八项改动|逐项确认保留，见第三节；不将已修正表述重复记为未解决|文字问题维持关闭|
|六 元数据与有限整理|修正训练主表和成本表索引，增加独立文稿版本；5.3暂保留现有短段落|元数据已修正；可选结构合并未执行|
|七 逐章收尾|保留已有组织，后续改动由真实数据和方案去留触发|不再为形式扩写|
|八 最小推进顺序|沿用H.5中诊断→核心比较→复用输出综合分析的三步顺序|规约已存在，正式执行未发生|
|九 核验与版本绑定|独立核验本轮文件、图示、数值身份、Word布局及目录，记录新旧版本哈希|见第五、六节|

## 二 四项研究问题仍然未决

|问题|保留位置|最低需要的真实材料|结果不支持时如何收束|
|:--|:--|:--|:--|
|严格关系保持是否得到有用增强|{link('第三章','## 第三章')}及{link('H.1—H.2','### H.1')}|同一批真实原文与改写、因素漂移判断、变化幅度和源覆盖；固定基础损失的数据构造比较；同增强数据上的学习项比较|若近似复制或主要排斥复杂文档，收缩影响域主张或简化筛选；不能只以低漂移率自证价值|
|局部事务在何种条件下值得采用|{link('4.2.5','#### 4.2.5')}、{link('4.6.5','#### 4.6.5')}及{link('H.3','### H.3')}|共同候选与评分下的裁剪前资源、失败、质量和误改记录；少量预定预算点或规模组的局部／全局完整成本|只在子集有用则降为条件选项；没有稳定收益则简化，或保留恢复框架而将局部／全局作为求解选择|
|相对领域系统的定位|{link('1.2','### 1.2')}及{link('附录G','# 附录G')}|至少一个与目标任务可解释对齐的外部端到端系统；记录转换、额外数据及无法表达对象|不能兼容原生超边则单列兼容任务；不修改主任务金标，不以转换失败贬低外部方法|
|两项工作的综合认识|{link('第五章','## 第五章')}及{link('H.4','### H.4')}|复用四格完整输出，形成一项对象级或明确配置条件的结论，配少量真实同输入案例|允许重叠、有限互补及条件性损害；若只支持较窄配置结论则缩短综合章|

本轮没有真实训练、模型推理、人工语义复核或求解器预算实验。当前材料不足以决定局部方案最终保留为主方法、条件选项还是需要简化；也不足以断言更严格的增强筛选必然有用。没有把以上不确定项静默记为“完成”。

同候选、同评分和同时限不等于同可行域：局部累计编辑预算与全局净编辑预算的差别继续保留。若研究目标是系统选择，可按声明条件比较；无需为本次编辑追加昂贵的纯搜索因果实验。既有人工数字和不利结果全部保留。

## 三 已认可内容与可选整理

|已认可事项|本轮决定|
|:--|:--|
|正文无结果诊断表已删除，计划集中H|不恢复到正文，不新增同类空结果表|
|摘要压缩并保留模拟身份、不利结果|原文保持，等待真实结果再重写|
|5.2、5.3、5.5标题与当前证据一致|保持，不将改标题冒充综合发现|
|端点依赖闭合不覆盖全部新合法非接触槽位|保留范围；图示只写失效已选槽位的最小扩域|
|局部累计预算与全局净预算及可行域区别|保留策略比较边界|
|3.6.1成绩表引用、4.6.2独立算例来源|两处已解决，未重新列为缺陷|
|6.3区分核心缺口与未来方向|保持，不增添未来方向|
|中心区间跨0、交互不确定、强全局结果|保持全部现有数值与解释|

5.3合并至相邻小节是评审给出的可选整理，不是本轮必须修正的错误。当前短段落已经限定解释边界，因此保留五个问题的现有结构；待正式对象级输出确定可支持的综合发现后，再决定合并或缩短。这样避免在没有新证据时继续调整小节编号和重复压缩限制语。

逐章的下一次修改触发点保持为：摘要与第一章由真实问题规模、主结果和局部方案定位触发；第二章由冻结的划分、模型、评分器、硬件与预算身份触发；第三章由真实可靠性、变化、覆盖、学习增量和成本触发；第四章由裁剪前可行性及局部采用条件触发；第五章由完整输出支持的综合发现触发；第六章据真实发现回答RQ1／RQ2并收缩无效主张；附录以真实日志替代计划，保留必要历史身份与归属。

推进顺序不扩张：先做能改变设计去留的有限文档诊断；再运行保留主张直接需要的核心比较和至少一个适当外部对照；最后复用输出形成综合认识、案例和配置选择，并统一更新表图、摘要、结论。每个保留机制有直接依据、失败及不利结果不被排除、结论能追到真实完整输出后，再进入实证成稿。

## 四 已关闭的元数据问题与七张新图

|字段|原v2记录|v3记录|
|:--|:--|:--|
|匹配训练主表|3-7、3-8、3-10|3-5、3-6、3-8|
|构造成本表|3-11|3-9|
|方法configuration_id|1010-v1-global-review|沿用，方法参数未更改|
|文稿manuscript_version|未单列|1010-v3|

已核对四个目标表号在正文真实存在。{link('A.4','### A.4')}同步说明文稿版本与方法配置身份的区别；新版本的{local('配置文件',W/'reference_config.json')}单独保存，未覆盖旧版或伪造新实验身份。

|图|重绘重点|必须保留的含义|
|:--|:--|:--|
|{link('图1-1','图1-1 原始文本')}|原文、组件识别与关系图分区；类型与关系直接标注|人为构造；c2完整理由；Support有边，NONE无边|
|{link('图1-2','图1-2 组件关系')}|训练与推理并列，由共同依赖连接|两项研究各有对象；ICIC和MCR为继承基础|
|{link('图2-1','图2-1 训练监督')}|两阶段路径、训练后生成器及调用关系|测试不提供金标；辅助头移除；完整事务提交或回退|
|{link('图3-1','图3-1 可改写')}|可改写域与只读域、内部及跨边界关系|位置与标签状态独立；NONE也检查；更新全部坐标和端点|
|{link('图3-2','图3-2 关系影响域')}|输入与监督隔离，冻结／可训练模块分层，继承和新增损失分支|W0冻结；因素梯度不直接更新结论专用LoRA；开发和测试移除辅助头|
|{link('图4-1','图4-1 组件替换')}|新旧完整对象、关系重建、接受门与分支|不按显示ID继承旧边；最小扩域计费；整图检查后原子提交|
|{link('图4-2','图4-2 多候选')}|四阶段执行、状态循环与停止路径|独立no-op；超时可行解保留非最优身份；失败计费；提交不重复计尝试|

统一使用低饱和蓝、青、灰和橙色，配合文字和线型区分含义。七图宽157 mm；高度92—148 mm；PNG为600 dpi，SVG保留文字与线条可编辑，PDF嵌入字体。Word中使用PNG，矢量源文件另包交付，不能把Word中的图片误称为可逐节点编辑的形状。未对四张定量图换数据、改曲线或调整呈现结论。

## 五 核验结果与边界

|核验|结果|
|:--|:--|
|源稿变更范围|仅版本、11条图像路径、训练图线型说明、A.4配置身份句；无其他正文改写|
|原始情景文件|7份原字节保持，包括生成程序；未生成新计数|
|数值复算|28,728行计数、84个均值／标准差单元及28个区间核验通过；只证明人工情景一致性|
|结构保留|44表、11图、3算法、49条参考文献、32个陈列公式及407个原生数学对象保留|
|新图语义|逐图对照正文与原图；输入／监督、NONE、依赖域、事务与预算边界已核对|
|图中文字与线条|7张PDF碰撞检查均PASS，无FAIL和WARN；最小PDF字形{figqa['minimum_pdf_glyph_pt']:.1f} pt|
|自动面板对齐|七图均为单个连续机制图，自动记录为NOT APPLICABLE；不虚报为可比面板对齐PASS|
|源代码预检|0 FAIL；两个非阻断提示已解释：无需TIFF投稿文件，实际PDF宽度均测得157 mm|
|Word与目录|{audit['pages']}页逐页查看；{audit['verified_page_labels']}个标题／题注页码匹配；{audit['toc_cached_entries']}个目录缓存项匹配；图注、原生公式、续表和跨页布局已核对|
|模板保留|三节页面几何和声明为只读的包部件保持；旧版Word、Markdown、配置和评审哈希未变|

处理过程中发现绘图依赖缺失，已安装到本轮工作目录。首轮源码预检未识别循环中的SVG/PDF导出，并把180 dpi预览视为低分辨率输出；现已改为显式矢量导出和300 dpi预览，正式PNG始终为600 dpi，最终预检重新通过。当前无未解决的生成或核验错误。

上述检查不认证真实方法增益、外部方法公平性、学位授予条件或所有Word版本的显示效果。参考文献内容未在本轮做穷尽复核，四篇参照论文和近邻方法的具体效果不据此获得新的认证。

## 六 版本与交付

- {local('Word论文',R/'report_1010_v3_full.docx')}
- {local('Markdown正文',source)}
- {local('七张图的矢量与绘图源文件',bundle)}

|文件|SHA-256|
|:--|:--|
|v3 Markdown|{audit['source_sha256']}|
|v3 Word|{audit['docx_sha256']}|
|v3 QA PDF|{audit['pdf_sha256']}|
|v3 参考配置|{rev['configuration_sha256']}|
|v2 Markdown（保留）|a2aeb98935b8d7cb242644ad06034f4d2e7405998951e258fbdc3c67dae6a6b7|
|v2 Word（保留）|c03523d4d9d91837c88853ec46d46ace29bf44c8f9a8d03bdbeffdbd76a0d510|

本轮可关闭的是配置追溯错误和图示重绘任务。四项研究问题、局部方案最终定位及正式实证结论仍然开放。
'''
report=R/'1010_v3评审处理与图示重绘说明.md';report.write_text(text)
files=[source,R/'report_1010_v3_full.docx',report,bundle]
files += [W/n for n in ['reference_config.json','draw_figures.py','figure_contract.md','figure_qa.json','requirements.txt','prepare.py','audit_revision.py','audit_figures.py','revision_audit.json','numerical_audit.json','final_audit.json','visual_review.json','template-evidence.json','artifact.md','source.diff','build_docx.py','render_document.py','cache_pages.py','deliver.py','source_preflight.json']]
files += [W/n for n in rev['unchanged_raw_files']]
files += [W/'figures'/f"{n}.{ext}" for n in [x['name'] for x in rev['new_figures']] for ext in ['png','svg','pdf']]
files += [W/'figures'/f'{n}.png' for n in rev['unchanged_quantitative_figures']]
manifest={'version':'1010-v3','genuine_model_runs':0,'files':[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
(W/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Delivered',report.name,'and',bundle.name,'with',len(files),'manifest entries')
