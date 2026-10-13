"""Release only after independent numerical, document and full-page visual QA."""
from pathlib import Path
import hashlib,json,zipfile,re
W=Path(__file__).resolve().parent;R=W.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda n:json.loads((W/n).read_text())
a=read('final_audit.json');s=read('supplement_audit.json');n=read('numerical_audit.json');v=read('visual_review.json');repro=read('portable_verification.json')
assert a['mechanical_checks']=='PASS' and s['passed'] and n['passed'] and repro['passed']
assert a['source_sha256']==s['source_sha256']==n['source_sha256']==sha(R/'report_1010_v4_full.md')
assert v['all_pages_reviewed'] and v['pages']==a['pages'] and v['pdf_sha256']==a['pdf_sha256']
assert sorted(p['page'] for p in v['reviewed_pages'])==list(range(1,a['pages']+1))
for p in v['reviewed_pages']:assert sha(W/'render_final'/f"page-{p['page']}.png")==p['sha256']
glyph=read('budget_glyph_audit.log');collision=read('figures/budget_conditions.collision.json');alignment=read('figures/budget_conditions.alignment.json');pre=read('budget_source_audit.log')
assert glyph['auditable'] and glyph['minimum_found_pt']>=5
assert collision['verdict']==alignment['verdict']=='PASS'
assert pre['summary']['counts']['FAIL']==0
fq={'backend':'Python matplotlib','evidence':'SIM-1010-V4','width_mm':157,'height_mm':80,'png_dpi':600,'editable_svg_text':True,'minimum_pdf_glyph_pt':glyph['minimum_found_pt'],'collision':'PASS','alignment':'PASS','manually_reviewed':True,'preserved_old_pngs':11,'preflight_warnings_reviewed':{'EXPORT-RASTER':'Thesis uses 600 dpi PNG and editable SVG/PDF. No TIFF submission requested.','FINAL-WIDTH':'Static parser misread arithmetic units; actual PDF width is measured as 157 mm, matching the manuscript.'}}
(W/'figure_qa.json').write_text(json.dumps(fq,ensure_ascii=False,indent=2)+'\n')
readme='''# 1010 v4 模拟记录复算包

全部新增记录的身份为SIM-1010-V4。没有真实语料模型输出、训练、人工语义标注或优化器执行。Kawarada_proxy、UniASA_proxy是人工参数生成的外部路线占位，不能归为作者成绩。关系对象键是与旧计数相容的一种补全，不是真实文档坐标。

## 复算记录

解压后保留目录结构，使用Python 3及numpy，在解压目录执行：

```bash
python _revision_1010_v4/generate_supplement.py
python _revision_1010_v4/audit_supplement.py --portable
python _revision_1010_v4/audit_scenario.py
```

生成程序会覆盖包内的新增模拟记录和汇总；原件已在本包保留，可另解压一份用于比较。supplement_manifest.json登记生成器与9份结果文件的SHA-256。脚本仅需本包内数据，不访问网络或外部系统。

portable模式跳过对本地上一版资产目录的逐字节比较，但继续核对记录、统计、四格对象、表格、公式和两版Markdown。完整工作区审计的旧文件及11图保留结果见supplement_audit.json；portable模式输出独立的portable_audit.json，不伪称检查了缺失资产。

## 绘图

新增图的PNG、SVG、PDF与draw_budget.py均在_revision_1010_v4中。安装requirements.txt中的绘图库后，可执行绘图程序；中文字体默认使用macOS的Arial Unicode字体路径，其他系统需修改addfont路径与相应字体族。七张机制图和四张既有结果图未重复打包，继续使用上一版图源包及工作区资产。

## 文件说明

- augmentation_text_pairs.json、augmentation_screening.csv：80个模板源文档、320个共同候选、960个筛选决定。
- resource_envelope.csv、budget_outcomes.csv：228文档的规模和成本函数，以及8,208条预算、方法、种子、对象记录。状态来自设定，没有求解证书。
- external_placeholders.csv：2,736条外部占位计数。
- object_memberships.json、object_transitions.csv、synthetic_object_cases.json：684组四格关系对象集合、集合变化和3个模拟例子。
- supplement_results.json：全部规模组、预算点、汇总与配对区间。
- document_counts.csv等7份旧情景文件：原有人工成绩的可复算输入；未重新定义其来源。
- 两版Markdown用于表号、表值和公式身份审计；本包不重复全部论文图片资产。

本包的可复现性表示同一生成假设可重建相同记录，不能证明真实方法有效。正式研究须整体替换模拟结果、模型输出、成本、案例和结论。
'''
(W/'simulation_bundle_README.md').write_text(readme)
bundle=R/'1010_v4模拟实验记录与复算脚本.zip'
names=s['preserved_raw_files']+list(read('supplement_manifest.json')['files'])+['generate_supplement.py','supplement_manifest.json','supplement_audit.json','numerical_audit.json','portable_verification.json','audit_supplement.py','audit_scenario.py','reference_config.json','draw_budget.py','requirements.txt','figure_contract.md','figure_qa.json','qa_tools/audit_panel_alignment.py']
names+=['figures/budget_conditions.'+ext for ext in ['png','svg','pdf']]
names+=['budget_source_audit.log','budget_glyph_audit.log','figures/budget_conditions.collision.json','figures/budget_conditions.alignment.json']
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(W/'simulation_bundle_README.md','README.md')
    for name in names:z.write(W/name,'_revision_1010_v4/'+name)
    for version in ['v3','v4']:z.write(R/f'report_1010_{version}_full.md',f'report_1010_{version}_full.md')
with zipfile.ZipFile(bundle) as z:assert z.testzip() is None
source=R/'report_1010_v4_full.md';lines=source.read_text().splitlines()
def link(label,needle):
    found=[i for i,line in enumerate(lines,1) if needle in line];assert found,(label,needle)
    return f'[{label}]({source}:{found[0]})'
def file(label,name):return f'[{label}]({W/name})'
report=f'''# 1010 v4 四项模拟实验补充与核验说明

根据“增强是否有用、局部方案采用条件、外部系统比较、两阶段综合发现仍按模拟实验结果修改”的要求，本版补入四组可复算模拟材料，并同步修改中英文摘要、第三至五章、结论和附录。新增6张表及1张预算图；已绘制的七张方法示意图、四张旧结果图和旧表数据保留。

本版仍是模拟数据演示稿。封面、摘要、相关小节和表图明确披露来源；真实模型训练、推理、人工语义审阅和求解器实验次数均为0。四项“模拟分析与写作”已完成；这不等于四项实证研究已完成。外部方法仅有占位成绩，不是原论文结果或真实复现。

## 一 四项修改与结论

|用户指定问题|新增材料及位置|当前可写的模拟结论|不能据此断言|
|:--|:--|:--|:--|
|增强是否有用|{link('3.6.6与表3-10','#### 3.6.6')}；复用表3-5、3-6的受控学习比较|完整筛选保留非复制改写，并减少设定漂移；高复杂度源覆盖下降，须同时检查变化、漂移、覆盖和学习增量|模板变化不能证明真实语义多样性；低漂移不自动等于真实训练有效|
|局部方案采用条件|{link('4.6.8、表4-11—4-12及图4-5','#### 4.6.8')}；共同准备、预检失败及三个端到端时限|局部在CDCP大规模组的36秒情景有条件优势，放宽至72秒后消失；整体差值区间包含0|不能宣称局部普遍胜过全局，也不能把人工成本函数当实测部署阈值|
|外部系统比较|{link('4.6.7与表4-10','#### 4.6.7')}；两个具名路线的占位计数|占位结果保留强于本方法的系统；内部受控增量不等于领域全面领先|未运行作者实现或转换器，不能判断真实公平性、排名或归因差异|
|两阶段综合发现|{link('5.2、表5-4与表5-5','### 5.2')}；四格完整关系对象集合及三个例子|部分共同修复与独有修复并存，组合有新增也有损害；聚合增量无需稳定超加|对象是与旧计数相容的一种构造，不是旧计数唯一隐含的分布，更不是机制因果证明|

{link('摘要','## 摘要')}和{link('第六章','## 第六章')}已使用以上条件结论。{link('H.5','### H.5')}保留正式实证替换顺序，{link('H.6','### H.6')}集中说明生成假设、分母与复算边界。方法configuration_id沿用1010-v1-global-review，manuscript_version更新为1010-v4；新增数据使用独立身份SIM-1010-V4，避免与既有人工主成绩或真实运行混淆。

## 二 模拟输入、分母与复算范围

|材料|规模|生成方式与关键边界|
|:--|:--|:--|
|共同候选池|每语料40个源，每源4候选，共320条文本对|源文档使用模板，低／高组各20篇且因素数为4／12；三种筛选共用候选，每源最多接受2个|
|筛选决定|960条|漂移标签、检测率和误报率由程序设定；编辑距离从实际保存的槽位字符串计算|
|裁剪前资源|AAEC 80、CDCP 148，共228文档|合法槽位数为组合上界的60%；每槽位2个正标签评分对象；准备和求解成本均为声明函数|
|预算结果|8,208条|228文档×3种子×2方法×3时限×2评价对象；全部失败和回退保留分母|
|规模与预算汇总|48行及24个配对区间|整体、小、中、大组和全部预算点均保存；文档成对bootstrap 2,000次，再对三个种子的F1取平均|
|外部占位计数|2,736条|228文档×3种子×2外部路线×2对象；Bernoulli参数是公开人工设定，非从论文估计|
|四格关系对象|684组及2,736组方法计数|228文档×3种子；全部四格逐文档TP／FP／FN与既有主记录一致，并匹配T1到组合的风险总量|
|模拟案例|3个|固定类别与文档顺序取例，保存完整对象键及四格命中状态；没有真实原文或完整组件预测图|

三个种子为17、29、43。均值、样本标准差和配对区间均从记录重算，未将均值直接填入结果文件。随机序列由SIM-1010-V4及操作键的SHA-256确定；不使用一个与代码无关的“总随机种子”解释不同数据族。生成器及9份新增结果文件的哈希见{file('补充材料清单','supplement_manifest.json')}。

新增80个模板源与原训练构造成本轨、228个模拟评价文档分开。旧表3-9中的生成token成本未反推自新模板池。旧表4-8的平均时间也没有与新预算图拼成一条运行曲线。所有数据仍为人工情景，语料名称表示任务规模和规则背景，不能当作实际语料采样身份。

## 三 保留的不利结果与限定

增强方面，完整筛选在AAEC接受67个候选，其中59个非复制、2个有设定漂移；CDCP为65、54、0。高复杂度源覆盖分别为18／20和16／20，低复杂度均为20／20。零漂移不表示风险为零；两组同时改变因素数和漂移生成率，不能把覆盖差全部归因于检查数量。原有同基础损失的数据构造差值为1.79／1.83个关系F1百分点，同增强集合的成对项差值为1.92／1.88；它们仍属于旧人工学习成绩，没有新模型训练。

局部采用方面，AAEC在24秒预算内全局质量较高。CDCP在36秒时，整体局部／全局关系F1为61.53／61.07，配对差值区间[−0.35, +1.24]包含0；大规模组差值为+1.80，区间[+0.43, +3.19]，放宽至72秒后为−0.54，区间[−1.66, +0.50]。因此只写条件选项。CDCP预检失败10／148文档，两方法共同承担；失败所含金标数保存，未枚举对象的潜在可恢复覆盖保持未知。

表4-11的P95是所有文档“完整准备估计”的分位数。预检在枚举后进行，失败文档不再评分，实际到达的模拟耗时另计入表4-12。状态名只用于模拟调度分支，solver_certificate始终为NOT_EXECUTED，gap为空；返回计数不等于已验证完整预测图合法性。同候选、同评分和同时限仍不消除局部累计预算与全局净预算的可行域差别。

外部比较方面，UniASA式占位在两种语料均高于T1＋BR-J，避免为本方法制造全面获胜的叙述。这是比较写作的占位场景；代码不包含作者模型、解码器、权重或真实任务转换，不能借这些名称赋予分数实证来源。正式接入要求继续按附录G执行。

综合发现方面，共同修复占单阶段新增命中并集的51.91%／68.89%，组合新增96／68个关系对象，同时损害65／46个T1命中；共同、独有、新增、损害均保留。对象键的坐标、类型与端点由程序赋予，只支持声明的关系集合代数。补全约束未分组关系计数及风险总量，未约束类型、标签或源成员数分组，不能与表5-7的旧分组情景作逐对象对齐。正文与H.6已明确这一限制。此补全不是从旧聚合数值恢复真实对象，也不能确定候选变化或评分变化的因果贡献。

## 四 核验与修正记录

|检查|最终结果|
|:--|:--|
|新增记录与统计|{file('独立补充审计','supplement_audit.json')}通过；候选池、配额、编辑距离、候选规模、全预算F1、24个区间、外部均值及四格集合独立复算|
|既有人工成绩|{file('旧情景数值审计','numerical_audit.json')}通过；28,728条计数、84个均值／标准差单元和28个区间保持|
|可重建性|隔离目录重新生成全部9份结果，哈希逐个一致；portable模式及旧情景审计通过，见{file('可复算验证','portable_verification.json')}|
|旧版本与内容|v3 Word和Markdown未改；7份原始情景文件、11张PNG、原44表数值、附录E、49条参考文献及32个陈列公式保持|
|表号与交叉引用|第五章按正文出现顺序编号；原表5-4／5-5顺延为5-6／5-7，新增对象和案例为5-4／5-5|
|最终结构|{a['pages']}页、50表、12图、3算法、49条参考文献、32个陈列公式、{a['native_math_objects']}个原生数学对象|
|目录与布局|{a['verified_page_labels']}个标题／题注页码及{a['toc_cached_entries']}个缓存项核对通过；全部{a['pages']}页逐页查看|
|新增图|157×80 mm、600 dpi PNG及可编辑SVG／PDF；最小字形7.7 pt，碰撞与两面板对齐均PASS|
|绘图预检提示|0 FAIL；未出TIFF符合本次Word交付；静态宽度识别提示以实际PDF测量157 mm核实|

过程中拦截并修复了新表编号顺序、准备成本口径、配置中无对应代码依据的种子字段，以及初版预算图横轴说明与图例碰撞。布局检查进一步压缩重复解释，并将跨页资源表按语料分组设置明确续表题注，收紧目录条目的段后间距以消除末条独占一页。最终记录不存在未处理的生成或校验错误；真实研究没有执行，已明确保留该边界，未以文档核验代替实验。

## 五 版本绑定与交付

|文件|SHA-256|
|:--|:--|
|v3 Word（保留）|{sha(R/'report_1010_v3_full.docx')}|
|v3 Markdown（保留）|{sha(R/'report_1010_v3_full.md')}|
|v4 Word|{sha(R/'report_1010_v4_full.docx')}|
|v4 Markdown|{sha(source)}|
|模拟生成器|{sha(W/'generate_supplement.py')}|
|记录与复算脚本包|{sha(bundle)}|

Word和Markdown为论文正文，ZIP保存模拟记录、生成与复算程序、新图矢量文件及运行说明。本说明用于追踪本轮四项修改，不能作为真实实验完成或学位评审通过的证明。后续若改用实测结果，应整体更新相应记录、表图、案例、摘要与结论，并保留本版。
'''
report_path=R/'1010_v4四项模拟实验补充与核验说明.md';report_path.write_text(report)
files=[R/'report_1010_v4_full.docx',source,report_path,bundle]+[W/n for n in names]+[W/n for n in ['final_audit.json','visual_review.json','figure_qa.json','writing_audit.json','source.diff','build_docx.py','compose_supplement.py','deliver.py','figure_contract.md','simulation_bundle_README.md','template-evidence.json','page_map.json','page_map_audit.json']]
files=list(dict.fromkeys(files))
(W/'delivery_manifest.json').write_text(json.dumps({'version':'1010-v4','scope':'FOUR_REPRODUCIBLE_SYNTHETIC_SUPPLEMENTS_AND_MANUSCRIPT','genuine_model_runs':0,'files':{str(p.relative_to(R)):sha(p) for p in files}},ensure_ascii=False,indent=2)+'\n')
for target in re.findall(r'\]\((/[^)]+)\)',report):assert Path(re.sub(r':\d+$','',target)).exists(),target
print(json.dumps({'report':str(report_path),'bundle':str(bundle),'pages':a['pages'],'manifest_files':len(files)},ensure_ascii=False))
