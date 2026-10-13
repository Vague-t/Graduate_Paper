from pathlib import Path
from collections import Counter
from zipfile import ZipFile
from lxml import etree as E
import json,hashlib,shutil,re

O=Path(__file__).resolve().parents[1];R=Path('/Users/channtang/Downloads/paper')
V=json.loads((O/'_work/verification.json').read_text());P=json.loads((O/'_work/patches.json').read_text())
M=json.loads((O/'_work/revision_manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R/'论文规范排版稿_v16.docx')==V['source_sha256']
assert sha(R/'论文规范排版稿_v16.pdf')=='82e71fdf2395254b90c977af1173ddc72c20a3837b5014a339e12393a518a672'
assert sha(O/'论文规范排版稿_v17.docx')==V['docx_sha256']
assert sha(O/'论文规范排版稿_v17.pdf')==V['pdf_sha256']
assert V.get('visual_qa_passed') and V['remaining_visual_check_pages']==[]
assert len(P)==91
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+N['w']+'}';MM='{'+N['m']+'}'
X=lambda e,q:e.xpath(q,namespaces=N)
T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
with ZipFile(R/'论文规范排版稿_v16.docx') as z:old=E.fromstring(z.read('word/document.xml')).find(W+'body')
with ZipFile(O/'论文规范排版稿_v17.docx') as z:new=E.fromstring(z.read('word/document.xml')).find(W+'body')
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

text=(O/'_work/report_intro.md').read_text()
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

changed=V['visual_qa_pages'];same=V['pixel_identical_to_v16']
before=sum(len(p['old_text']) for p in P);after=sum(len(p['new_text']) for p in P)
toc=V['toc_page_cache_changed_vs_source']
text+=f'''## 四、内容与版式核对

- **修改范围：** 91段均在第五章、第六章及附录A—K。摘要、第一至四章和参考文献正文保持v16原样；标题、题注及章节顺序未变。
- **研究信息：** 逐段核对数字与引文编号，全部保持一致；另对照检查比较对象、操作条件、统计单位、执行状态与结论强度。代码样例、文件名、固定模型版本及来源标识保留。
- **公式与图表：** 全文380个原生公式对象、83张表和{V['media_parts_identical']}个图像资源与v16一致，交叉引用与书签结构完整。
- **文字组织：** 按含标点与字母的字符口径，91段由{before}增至{after}字符。必要处补足动作与条件，冗余处适度压紧，不以删字比例评价润色。
- **原稿样式：** 沿用字体、字号、标题层级、段落格式和图表尺寸，没有缩小字号或挤压行距。
- **落版与目录：** 91段改文均在最终PDF中核对。全文共{V['pages']}页，149条目录条目与正文对应；其中{toc}条页码缓存随最终分页更新，标题和链接保持不变。全部{V['fonts_embedded']}种PDF字体已嵌入。
- **页码范围：** 第五章为PDF物理第{V['chapter5_physical_pages'][0]}—{V['chapter5_physical_pages'][1]}页，第六章为第{V['chapter6_physical_pages'][0]}—{V['chapter6_physical_pages'][1]}页，附录为第{V['appendices_physical_pages'][0]}—{V['appendices_physical_pages'][1]}页。物理页码包括封面与前置页，与正文印刷页码不同。
- **视觉复核：** 逐页检查相对v16发生像素变化的{len(changed)}页，其余{len(same)}页与已核对的v16页面逐像素一致。末轮文字调整后重新渲染，并复核所有新变化页面。未发现新增缺字、裁切、公式重叠或仅少量文字溢出的尾页。

本轮完成语言与局部组织润色及文档核对，没有新增实验、数据、文献或机制。上述核对是本次文档编辑的验收，不替代研究实验执行或结果复现。

## 五、交付文件与版本对应

- 修改稿：[论文规范排版稿_v17.docx](/Users/channtang/Downloads/paper/论文规范排版稿_v17.docx)
- 排版预览：[论文规范排版稿_v17.pdf](/Users/channtang/Downloads/paper/论文规范排版稿_v17.pdf)
- 本说明：[论文规范排版稿_v16至v17_剩余内容详细润色说明.md](/Users/channtang/Downloads/paper/论文规范排版稿_v16至v17_剩余内容详细润色说明.md)

v16原文件的内容摘要在编辑前后保持一致，所有修改均另存到v17。以下摘要用于识别本轮对应版本。

| 文件 | SHA-256 |
| --- | --- |
| v16 Word（原稿） | `{V['source_sha256']}` |
| v17 Word（改稿） | `{V['docx_sha256']}` |
| v17 PDF（排版预览） | `{V['pdf_sha256']}` |
'''

assert len(re.findall(r'^#### \d+\.',text,re.M))==91
assert text.count('**原文**')==text.count('**改后**')==text.count('**为什么改：**')==text.count('**改后好在哪里：**')==91
name='论文规范排版稿_v16至v17_剩余内容详细润色说明.md'
(O/name).write_text(text)
for name in ['论文规范排版稿_v17.docx','论文规范排版稿_v17.pdf',name]:
    src=O/name;dst=R/name
    if dst.exists():assert sha(dst)==sha(src),('Refuse to overwrite different final artifact',dst)
    else:shutil.copy2(src,dst)
    assert sha(src)==sha(dst)
assert sha(R/'论文规范排版稿_v16.docx')==V['source_sha256']
assert sha(R/'论文规范排版稿_v16.pdf')=='82e71fdf2395254b90c977af1173ddc72c20a3837b5014a339e12393a518a672'
print(json.dumps({'report_characters':len(text),'paragraph_comparisons':len(P),'output_docx':str(R/'论文规范排版稿_v17.docx'),'output_pdf':str(R/'论文规范排版稿_v17.pdf'),'output_report':str(R/'论文规范排版稿_v16至v17_剩余内容详细润色说明.md'),'source_preserved':True},ensure_ascii=False,indent=2))

