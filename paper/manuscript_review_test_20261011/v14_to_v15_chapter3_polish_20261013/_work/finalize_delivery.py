from pathlib import Path
from collections import Counter
from zipfile import ZipFile
from lxml import etree as E
import json,hashlib,shutil,re

O=Path(__file__).resolve().parents[1];R=Path('/Users/channtang/Downloads/paper')
V=json.loads((O/'_work/verification.json').read_text());P=json.loads((O/'_work/patches.json').read_text())
M=json.loads((O/'_work/revision_manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R/'论文规范排版稿_v14.docx')==V['source_sha256']
assert sha(R/'论文规范排版稿_v14.pdf')=='ca9bf77e8fe269a4e653fe30a087fdb03e6b184e244093b2f02b68032a32a41a'
assert sha(O/'论文规范排版稿_v15.docx')==V['docx_sha256']
assert sha(O/'论文规范排版稿_v15.pdf')==V['pdf_sha256']
assert V.get('visual_qa_passed') and V['remaining_visual_check_pages']==[]
assert len(P)==64
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+N['w']+'}';MM='{'+N['m']+'}'
X=lambda e,q:e.xpath(q,namespaces=N)
T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
with ZipFile(R/'论文规范排版稿_v14.docx') as z:old=E.fromstring(z.read('word/document.xml')).find(W+'body')
with ZipFile(O/'论文规范排版稿_v15.docx') as z:new=E.fromstring(z.read('word/document.xml')).find(W+'body')
def linear(e):
    tag=E.QName(e).localname
    if tag=='t':return e.text or ''
    if tag in ['rPr','sSubPr','sSupPr','sSubSupPr','dPr']:return ''
    if tag in ['oMath','r','e','sub','sup']:return ''.join(linear(c) for c in e)
    if tag in ['sSub','sSup','sSubSup']:
        s=linear(e.find(MM+'e'))
        for part,symbol in [('sub','_'),('sup','^')]:
            c=e.find(MM+part)
            if c is not None:s+=symbol+'{'+linear(c)+'}'
        return s
    if tag=='d':
        pr=e.find(MM+'dPr')
        def val(k,default):
            x=pr.find(MM+k) if pr is not None else None
            return x.get(MM+'val',default) if x is not None else default
        return val('begChr','(')+val('sepChr','|').join(linear(c) for c in e.findall(MM+'e'))+val('endChr',')')
    raise ValueError(tag)
def paragraph(e):
    return ''.join('`'+linear(n)+'`' if n.tag==MM+'oMath' else (n.text or '') for n in X(e,'.//w:t|.//m:oMath'))

text='''# v14 → v15 第三章详细润色说明

日期：2026年10月13日

本轮基于《论文规范排版稿_v14.docx》，继续使用你指定的 [chinese-thesis-polish skill](/Users/channtang/Downloads/paper/writing_style_research_20261013/skill/chinese-thesis-polish/SKILL.md)，润色第三章“关系影响域约束的增强与成对学习”，另存为 v15。v14 的 Word 和 PDF 均保留。

第三章已有较完整的方法定义、审核规则、训练目标及实验记录。本轮重点是让这些内容按读者理解方法的顺序展开：先说明问题，再解释对象与操作，随后给出使用条件、实验比较和结论。以下“改后好在哪里”指表达、论证组织及阅读上的改善，不表示本轮新增了方法或实验效果。

## 一、主要改了哪里，为什么这样改

共修改64个正文段落，覆盖章首及3.1—3.7节。保留原有标题层级、段落顺序、公式、算法步骤与图表结构。

| 位置 | 修改段数 | 原有阅读障碍 | 本轮处理 | 改后更容易理解什么 |
| --- | ---: | --- | --- | --- |
| 章首与3.1引言 | 4 | 问题、术语和章节预告较集中，局部改写为什么会影响监督还可更直接。 | 用组件角色与关系状态的变化引出审核，再定义视图、因素和成对学习。 | 本章要解决的具体问题，以及增强构造与成对比较为什么需要相互配合。 |
| 3.2总体框架与基础模型 | 4 | 构造输出、掩码、门控、提示及继承配置交叉出现。 | 先明确构造与学习的接口，再按输出字段顺序解释门控，区分提示触发和赋予标签。 | 哪些内容是继承基础，哪些是本章新增设计，模型在各阶段允许看到什么。 |
| 3.3增强、坐标与审核 | 25 | 位置分类、关系标签、审核状态、语义未知和完整筛选交织，长段内概念切换较快。 | 按选择槽位、生成、迁移、检查和决定监督资格的顺序说明，将相近概念放在一起辨析。 | 坐标正确不等于语义保持；掩码为零不等于NONE；保存输运图不等于所有标签都用于训练。 |
| 3.4成对学习 | 11 | 输入、辅助头、损失目标和梯度路径信息密集，分布一致容易被误读为预测正确。 | 用同一案例引出关系独立审核和金标锚定，明确输入隔离、空集合处理及源文档归一化。 | 每个目标使用哪些监督、更新哪些参数，哪些比较包含原文权重变化。 |
| 3.5算法及性质 | 5 | 算法阶段、参数更新及形式性质的适用对象需要更清楚地区分。 | 理顺预算与更新说明，以条件、推导和适用范围解释两项性质。 | 标注结构保持和单因素稳定分别保证什么，为什么不能直接推出完整图语义或生成分布的保证。 |
| 3.6实验结果与分析 | 13 | 对照配置、配对差值、显著性、审核比例及成本口径较密集。 | 按比较目的介绍配置，把统计判断放在具体比较旁边，集中解释分母、权重和资源单位。 | 整体配置收益与成对目标独立贡献如何区分，分层风险为何不能被总体比例替代。 |
| 3.7本章小结 | 2 | 方法总结、统计结果和下一章问题之间的连接还可更紧密。 | 按机制作用、证据范围与后续问题收束。 | 本章解决到哪一步，以及推理阶段为何仍需处理组件变化引起的关系变化。 |

## 二、贯穿本轮的六项修改重点

### 1. 从操作依赖组织说明，让术语有具体落点

原稿的技术信息完整，但部分段落把对象定义、执行条件、异常分支和效果限制同时列出。改稿尽量沿“输入是什么—对它做什么—什么条件下保留或拒绝—产物怎样用于训练”的顺序解释。比如，组件对应先解释版本与字符区间，再说明只读组件也须更新位置，最后说明双射的作用对象及拒绝条件。这样读者可沿处理流程理解方法，而不必先记住全部术语。

### 2. 保留必要区别，减少后文回溯

本轮反复检查了几组容易混淆的概念：文字不改与位置不变、组件双射与字符双射、坐标输运与语义保持、掩码为零与关系NONE、未审核与语义未知、完整对象不匹配与语义上无关系。这些差别没有合并为笼统的“可靠性”，而是在实际影响判断的地方解释清楚。读者据此能够判断某个因素为什么参与监督、为什么被屏蔽，以及某个负例只对哪项任务成立。

### 3. 将学习目标、监督入口和更新路径对齐

增强全文进入生成器，不代表其全部输运标签都可作为完整生成答案；辅助头的类别分布，也不等于第四章完整对象正确率。改稿明确了原文生成、增强侧掩码监督、双视图对齐、标签锚定及独立推理评分的分工，并保留空关系集合、无增强视图和梯度累积末批的处理条件。这样公式前后的解释可与算法步骤相互对应。

### 4. 区分设计意图、形式性质与实验结论

对于已确定的操作，直接写“检查”“保留”“拒绝”“更新”；对于形式性质，保留其前提和作用对象。标注输运保持只说明对象结构，单因素稳定条件也不等同于平均JS降低就能保证每项预测正确。改稿没有把这些性质写成自然改写语义可靠或完整生成图严格等变的证明。

### 5. 把统计判断放在它所支持的比较旁边

主结果仍明确：整体训练配置的均值增量在两种语料上均为正，但多重比较校正后的显著性结论不同；成对目标的独立贡献由固定视图、掩码与辅助头的比较判断。改稿还保留主要与探索性比较的身份，以及单项区间和校正p值的不同用途。审核部分则将不安全率与漂移率的分母、逆概率加权和源聚类区间放在一起解释，避免读者将不同统计量互相替代。

### 6. 清晰度优先，不追求统一句长或机械删字

没有为了减少字数而删掉完整源成员规则、未知真子集例外、资源不足分支、模型配置或统计限定。已有清楚的公式定义、表格、算法步骤和计算例子保持原样。需要减少理解负担的地方拆开条件和动作；需要防止误读的地方则保留或展开必要解释。

## 三、全部64段的修改对照与理由

按正文顺序列出，每项均包含原文、改后、为什么改和改后好在哪里，可按所在小节及原文首句定位。对照中的原生公式以线性写法显示，保留括号及上下标标记；正式版式以Word和PDF为准。

'''
section=None
for n,p in enumerate(P,1):
    i=int(p['block_id'][1:]);assert T(old[i])==p['old_text'] and T(new[i])==p['new_text']
    if p['section']!=section:
        section=p['section'];text+=f'### {section}\n\n'
    text+=f'#### {n:02d}. {p["title"]}\n\n'
    text+='**原文**\n\n> '+paragraph(old[i])+'\n\n'
    text+='**改后**\n\n> '+paragraph(new[i])+'\n\n'
    text+='**为什么改：** '+p['problem']+p['reason']+'\n\n'
    text+='**改后好在哪里：** '+p['benefit']+'\n\n'

changed=V['visual_qa_pages'];same=V['pixel_identical_to_v14']
text+=f'''## 四、内容与版式核对

- **修改范围：** 64个改写段落均位于第三章。摘要、第一二章、第四章至第六章、参考文献及附录的正文保持原样；目录仅按实际分页同步了{V['toc_page_cache_changed_vs_source']}项页码。
- **研究信息：** 修改段落的数字与引文编号逐段核对，保留模型、生成和审核设置、预算、配对差值、区间、p值及成本信息；另行核查操作条件与结论强度，未增加机制或效果主张。
- **公式与图表：** 全文380个原生公式对象、83张表和全部{V['media_parts_identical']}个图像资源与v14一致，算法3-1的全部步骤及正文交叉引用保留。
- **样式与结构：** 沿用原稿字体、字号、标题层级、段落顺序和图表尺寸，没有通过缩小字号容纳内容。
- **文字落版：** 64段改写文字均已在最终PDF中核对；含原生公式的段落同时核对公式结构及公式前后的文字顺序。
- **页面复核：** 最终PDF共{V['pages']}页，149条目录条目与正文位置对应。第三章位于PDF物理第{V['chapter3_physical_pages'][0]}—{V['chapter3_physical_pages'][1]}页。本轮逐页查看了{len(changed)}个发生像素变化的页面，其余{len(same)}页与已完成视觉复核的v14页面逐像素一致。未发现新增缺字、内容裁切、公式重叠或章末空白页。

本轮为语言与局部组织润色，没有新增实验、数值或文献。后续章节保留v14表述。

## 五、交付文件与版本对应

- [v15 Word](/Users/channtang/Downloads/paper/论文规范排版稿_v15.docx)
- [v15 PDF](/Users/channtang/Downloads/paper/论文规范排版稿_v15.pdf)
- [保留的v14 Word原稿](/Users/channtang/Downloads/paper/论文规范排版稿_v14.docx)

| 文件 | SHA-256 |
| --- | --- |
| v14 Word原稿 | `{V['source_sha256']}` |
| v15 Word | `{V['docx_sha256']}` |
| v15 PDF | `{V['pdf_sha256']}` |
'''
name='论文规范排版稿_v14至v15_第三章详细润色说明.md'
assert len(re.findall(r'^#### \d+\.',text,flags=re.M))==64
assert text.count('**为什么改：**')==text.count('**改后好在哪里：**')==64
assert text.count('**原文**')==text.count('**改后**')==64
(O/name).write_text(text)
for n in ['论文规范排版稿_v15.docx','论文规范排版稿_v15.pdf',name]:
    source=O/n;target=R/n
    if target.exists():assert target.read_bytes()==source.read_bytes(),f'Unexpected existing output: {target}'
    else:shutil.copy2(source,target)
    assert sha(source)==sha(target)
assert sha(R/'论文规范排版稿_v14.docx')==V['source_sha256']
print(json.dumps({'outputs':[str(R/n) for n in ['论文规范排版稿_v15.docx','论文规范排版稿_v15.pdf',name]],'source_preserved':True,'changed_paragraphs':64,'detailed_comparisons':64,'report_characters':len(text),'pages':V['pages']},ensure_ascii=False,indent=2))
