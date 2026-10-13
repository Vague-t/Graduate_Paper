from pathlib import Path
from collections import Counter
from zipfile import ZipFile
from lxml import etree as E
import json,hashlib,shutil,re

O=Path(__file__).resolve().parents[1];R=Path('/Users/channtang/Downloads/paper')
V=json.loads((O/'_work/verification.json').read_text());P=json.loads((O/'_work/patches.json').read_text())
M=json.loads((O/'_work/revision_manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R/'论文规范排版稿_v15.docx')==V['source_sha256']
assert sha(R/'论文规范排版稿_v15.pdf')=='a313e0f9dcf427289902bbb1bba451a688941d9eec0e8100a7e2356498fdf94c'
assert sha(O/'论文规范排版稿_v16.docx')==V['docx_sha256']
assert sha(O/'论文规范排版稿_v16.pdf')==V['pdf_sha256']
assert V.get('visual_qa_passed') and V['remaining_visual_check_pages']==[]
assert len(P)==76
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+N['w']+'}';MM='{'+N['m']+'}'
X=lambda e,q:e.xpath(q,namespaces=N)
T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
with ZipFile(R/'论文规范排版稿_v15.docx') as z:old=E.fromstring(z.read('word/document.xml')).find(W+'body')
with ZipFile(O/'论文规范排版稿_v16.docx') as z:new=E.fromstring(z.read('word/document.xml')).find(W+'body')
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

text='''# v15 → v16 第四章详细润色说明

日期：2026年10月13日

本轮基于《论文规范排版稿_v15.docx》，继续使用你指定的 [chinese-thesis-polish skill](/Users/channtang/Downloads/paper/writing_style_research_20261013/skill/chinese-thesis-polish/SKILL.md)，润色第四章“多候选驱动的依赖闭合论辩图修正”，另存为 v16。v15 的 Word、PDF 及此前版本均保留。

本章已有完整的方法定义、候选和资源规则、求解模型与实验记录。此次主要改善这些信息的组织顺序和解释方式：先让读者知道一次修改涉及哪些对象，再说明如何计分、何时接受、如何求解，以及不同结果能够支持什么结论。下文所说“改后好在哪里”均指表达、局部论证和阅读上的改善，不表示本轮增加了机制、实验或性能收益。

## 一、主要改了哪些地方

共润色76个正文段落，覆盖章首及4.1—4.7节。沿用原有标题、段落顺序、公式、算法步骤和图表结构。

| 位置 | 修改段数 | 原有阅读障碍 | 本轮主要处理 | 改后好在哪里 |
| --- | ---: | --- | --- | --- |
| 章首与4.1引言 | 5 | 问题、流程缩写、方法定位和记录要求集中出现，继承部分与追加部分的层级不够醒目。 | 用组件变化引起关系身份变化提出问题，按I0、I1、R_DC和BR-J逐层说明。 | 更容易理解本章改什么、为何共同接受，以及完整方法与局部子程序的关系。 |
| 4.2候选生成与初始图 | 13 | 候选来源、保护规则、裁剪上限、失败返回和反向操作条件交织。 | 按生成、解析、合法化、候选保护、资源预检和冻结的顺序解释；区分未入池与搜索拒绝。 | 每个阶段的输入和输出更明确，读者可判断某对象为何能或不能进入修正范围。 |
| 4.3对象评分与接受准则 | 10 | 固定评分、缺分、OOF监督、经验门限和代理效用的限制集中于长段。 | 分开说明评分对象、跨状态可比性、缺分准入条件、策略选择和效用解释。 | 不易混淆低分与未知评分，也不会由代理效用上升推出真实F1上升。 |
| 4.4依赖闭合与事务构造 | 8 | 冲突闭合、关系补全、最小合法化扩域和事务案例信息较密集。 | 按组件冲突、关系身份失效、完整补全、一次接受的操作次序展开；保留非接触新合法槽位的范围限制。 | 可以顺着实际操作理解一次事务为何必须整体判断，以及哪些关系并不会自动进入事务。 |
| 4.5求解算法及性质 | 17 | 局部/全局模型、累计/净编辑、外层/阶段预算、最优/可行返回容易混读。 | 先说明两条路径分别决定什么，再解释约束、预算单位、终止性质和规模路由。 | 可行域差异有具体原因，算法规约、实际路由及求解返回状态各自清楚。 |
| 4.6实验与分析 | 21 | 方法缩写密集，显著性套语重复，质量、校准、成本与不同实验身份之间切换频繁。 | 按共同起点、变化项、观察结果及统计判断组织；明确完整I1、局部消融、CPU规则和弱评分诊断的证据归属。 | 更容易判断每项比较说明什么，不将总体收益归为某个子程序的独立贡献，也不将诊断案例当成主系统效果。 |
| 4.7本章小结 | 2 | 方法、统计结果、路径限制和下一章任务并列，收束重点较分散。 | 按共同决策机制、已支持结果、比较边界和后续分析收束。 | 本章贡献及其适用条件更明确，与第五章的衔接也更自然。 |

## 二、为什么这样改，改后具体改善了什么

### 1. 让章节沿一次修正的操作顺序展开

原稿的技术条件比较充分，但部分段落同时交代对象定义、执行步骤、资源例外和结论限制，读者需要自行排序。此次把段落内部的解释调整为“当前对象是什么—提议怎样改变它—哪些关系因此受影响—满足什么条件才提交”。例如，参考事务先说明同跨度类型替换造成冲突，再说明旧关系删除和新关系加入，最后解释为何字符不变仍会产生新完整键。这样公式、表格与自然语言说明更容易相互对应。

### 2. 区分候选范围、输入完整性与事务接受

未进入固定候选池的对象不能在搜索中临时补回；已入池但缺失评分的对象也不能简单当作低分；分数齐备后，事务仍要经过合法性、效用门和预算检查。这三类情况处在不同阶段，原文较密集的写法容易使它们都被理解成“未被接受”。改稿把条件放到对应操作旁边，尤其说明二元反向入队要求、受保护对象的保留、裁剪前资源预检和缺分事务的拒绝。读者据此可以定位失败发生在哪一步。

### 3. 解释依赖闭合处理什么，也保留它的范围边界

本章的闭合针对完整端点身份变化，并不自动枚举所有新合法的非接触槽位，也不宣称自然语言语义影响只发生在一跳。改稿将端点变化造成的关系失效、事务外已选关系的最小合法化扩域、未选槽位后来变得合法这几种情况分开说明。原有CDCP连续性例子及其后续恢复条件保持原样。这样既突出共同决策的必要性，也不会为了语言简洁扩大方法的处理范围。

### 4. 把两条求解路径的差异写成可追踪的原因

局部路径固定组件提议后求关系补全，每次相对当前状态检查分项门，并累计编辑；全局路径同时选择组件和关系，以G0为参照计算净编辑与分项门。此次明确说明，局部终态满足全局限制，并不意味着全局最优解一定能通过局部单调动作到达。外层提议数与实际阶段提交、模型规约与主参考实现也分别解释。读者因此不会将两条路径的差别全部归为搜索效率，或把相同外层额度当成相同计算成本。

### 5. 让实验结论紧贴它所支持的比较

完整I1相对I0的收益、允许组件变化相对RelationOnly的差异、Single相对Sequential的差异，以及SetLocal相对Single的额外贡献，回答的是不同问题。改稿减少重复统计套语，但保留各自的比较身份、点估计和校正p值。主条件690个输入全部走Global、SetLocal与Single当前计数相同、代理最优证书不代表真实F1最优，以及主参考实现未执行三级词典序破同分，均继续明确陈述。结论更容易阅读，但没有变强。

### 6. 分开成功、代价与不同来源的诊断

真实F1提升可以伴随少量正确关系误删，因此新增正确率、原TP损失、逐文档下降和总成本仍分别报告。CPU规则诊断、主条件真实文档事务、原生关系结构例子与弱评分v0保留独立身份；事后选例不写成代表性统计，强制修正诊断不写成实际策略输出。这样既能利用案例帮助理解机制，也避免用一个层面的证据代替另一个层面的结论。

### 7. 保留清楚的原文，不为改写而改写

公式、算法、表格、标题和已清楚的计算例子保持原样。4.3.1中原有拟合、校准和策略划分表述也没有被润色擅自改成新的实验协议。本轮没有为追求短句删除条件，也没有把全文统一改成固定句式；必要时适度展开说明。按含标点与字母的字符口径，76段由11165增至11597字符，增长主要用于补足动作主体、条件归属和段内衔接，目的在于降低理解成本。

## 三、全部76段的修改对照与理由

以下按正文顺序列出，每项包含原文、改后、为什么改、改后好在哪里，可按小节及段落首句定位。对照中的原生公式以线性形式显示，保留括号及上下标；正式排版以Word和PDF为准。

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

changed=V['visual_qa_pages'];same=V['pixel_identical_to_v15']
text+=f'''## 四、内容与版式核对

- **范围：** 76个改写段落均位于第四章，摘要、第一至三章、第五至六章、参考文献及附录的正文保持原样。目录页码经复核与v15一致，无需调整。
- **研究信息：** 修改段落的数字和引文编号逐段核对；模型配置、候选数量、预算、效用参数、事务计数、区间及p值保留，操作条件和结论强度另作对照检查。
- **公式、算法与图表：** 全文380个原生公式对象、83张表及{V['media_parts_identical']}个图像资源与v15一致。算法4-1、4-2的全部步骤及交叉引用保持原样。
- **样式：** 沿用原稿字体、字号、标题层级、段落顺序和图表尺寸，没有通过缩小字号容纳改写。
- **文字落版：** 76段改写均在最终PDF中核对，含公式段落同时核查公式结构及前后文字顺序。
- **分页与视觉：** 最终PDF共{V['pages']}页，149条目录条目与正文位置对应；第四章为PDF物理第{V['chapter4_physical_pages'][0]}—{V['chapter4_physical_pages'][1]}页。逐页查看本轮发生像素变化的{len(changed)}页，其余{len(same)}页与已完成视觉复核的v15页面逐像素一致。未发现新增缺字、裁切、公式重叠或章末空白页。

本轮完成语言和局部组织润色及文档核对，没有新增实验、数据、文献或方法机制；其余章节保留v15表述。

## 五、交付文件与版本对应

- [v16 Word](/Users/channtang/Downloads/paper/论文规范排版稿_v16.docx)
- [v16 PDF](/Users/channtang/Downloads/paper/论文规范排版稿_v16.pdf)
- [保留的v15 Word原稿](/Users/channtang/Downloads/paper/论文规范排版稿_v15.docx)

| 文件 | SHA-256 |
| --- | --- |
| v15 Word原稿 | `{V['source_sha256']}` |
| v16 Word | `{V['docx_sha256']}` |
| v16 PDF | `{V['pdf_sha256']}` |
'''
name='论文规范排版稿_v15至v16_第四章详细润色说明.md'
assert len(re.findall(r'^#### \d+\.',text,flags=re.M))==76
assert text.count('**为什么改：**')==text.count('**改后好在哪里：**')==76
assert text.count('**原文**')==text.count('**改后**')==76
(O/name).write_text(text)
for n in ['论文规范排版稿_v16.docx','论文规范排版稿_v16.pdf',name]:
    source=O/n;target=R/n
    if target.exists():assert target.read_bytes()==source.read_bytes(),f'Unexpected existing output: {target}'
    else:shutil.copy2(source,target)
    assert sha(source)==sha(target)
assert sha(R/'论文规范排版稿_v15.docx')==V['source_sha256']
print(json.dumps({'outputs':[str(R/n) for n in ['论文规范排版稿_v16.docx','论文规范排版稿_v16.pdf',name]],'source_preserved':True,'changed_paragraphs':76,'detailed_comparisons':76,'report_characters':len(text),'pages':V['pages']},ensure_ascii=False,indent=2))

