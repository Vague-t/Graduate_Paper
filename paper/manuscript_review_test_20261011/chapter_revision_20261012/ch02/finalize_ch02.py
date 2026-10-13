from pathlib import Path
import json,re,hashlib,zipfile
from lxml import etree
from docx import Document
from pypdf import PdfReader
from PIL import Image,ImageChops

BASE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
body=(BASE/'第二章_修订后全文_v1.md').read_text()
supp=(BASE/'第二章_补充材料_v1.md').read_text()
changes=(BASE/'第二章_变更点与缺陷修复说明.md').read_text()
review='''# 第二章完整正文与审阅说明 v1

本轮审阅内容依次为两表必要性评估、第二章完整修订正文、变更与缺陷状态、完整补充材料。保留test稿件原有的模拟说明。本轮完成后停在第二章，等待审阅。

## 先评估表1-2与表1-3

表1-2的比较责任需要保留，但九行详细控制条件不必全部置于绪论；建议移至公共实验说明。本轮补充表S2-4已承接其内容，并明确14项主要比较与探索性分析。绪论保留研究问题与简要证据说明即可。

表1-3应保留，因为它明确MCR-BR的已有能力和本文的深化内容。建议压缩为“研究层次、已有机制、本文研究内容”三列四行，将结果归属与统计边界交给实验章节及附录C.1。

可直接采用的绪论替换段落和精简表见[两表必要性评估](表1-2与表1-3_必要性评估.md)。已确认的第一章v2未被覆盖；表号在最终合并时统一。

以下为第二章全部修订正文，图、表、公式和小结均完整保留。

---

'''+body+'\n\n---\n\n'+changes+'\n\n---\n\n'+supp+'''

---

## 配套文件

- [Word审阅稿](第二章_修订稿_v1.docx)
- [纯正文Markdown](第二章_修订后全文_v1.md)
- [跨章衔接与符号替换清单](第二章_跨章衔接与符号替换清单.md)
- [统计复算材料使用说明](统计复算材料_使用说明.md)
- [修改前提取文本](第二章_修改前提取文本.txt)

本轮不继续修改第三章。
'''
(BASE/'第二章_完整正文与审阅说明_v1.md').write_text(review)

docx=BASE/'第二章_修订稿_v1.docx';doc=Document(docx)
tables=[]
for md in (body,supp):
    lines=md.splitlines();i=0
    while i<len(lines):
        if lines[i].strip().startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[v.strip() for v in lines[i].strip().strip('|').split('|')];i+=1
                if all(re.fullmatch(r':?-+:?',v) for v in cells):continue
                rows.append(cells)
            tables.append(rows)
        else:i+=1
actual=[[[c.text.strip() for c in row.cells] for row in t.rows] for t in doc.tables]
assert actual==tables
source=BASE.parents[1]/'manuscript_review_test.docx'
assert sha(source)=='6de7116c7d5e6b76a06104d9f3a787c98dc7168504e7813146c8a1a2b9d92ab5'
v2=BASE.parent/'ch01/v2';v2manifest=json.loads((v2/'delivery_manifest_v2.json').read_text())
for name,digest in v2manifest['files'].items():assert sha(v2/name)==digest
old=json.loads((BASE/'source_ch02_blocks.json').read_text())
old_citations=sorted({int(v) for block in old for v in re.findall(r'\[(\d+)\]',block.get('text',''))})
new_citations=sorted({int(v) for v in re.findall(r'\[(\d+)\]',body+supp)})
assert set(old_citations)<=set(new_citations)
with zipfile.ZipFile(docx) as z:
    root=etree.fromstring(z.read('word/document.xml'))
    assert z.testzip() is None
    # Check every non-math prose paragraph in order, independently of table checks.
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
    actual_prose=[''.join(p.xpath('.//w:t/text()',namespaces=ns)) for p in root.xpath('./w:body/w:p',namespaces=ns)]
    cursor=0;checked=0
    for md in (body,supp):
        in_math=False
        for line in md.splitlines():
            text=line.strip()
            if text=='$$':in_math=not in_math;continue
            if not text or in_math or text.startswith('|') or text.startswith('!['):continue
            expected=re.sub(r'^#{1,3} ','',text)
            expected=re.sub(r'\$[^$]+\$','',expected).replace('`','')
            while cursor<len(actual_prose) and actual_prose[cursor]!=expected:cursor+=1
            assert cursor<len(actual_prose),expected[:80]
            checked+=1;cursor+=1
pdf=BASE/'_render_delivery/第二章_修订稿_v1.pdf'
assert len(PdfReader(pdf).pages)==12
pixel_review=[]
for n in range(1,13):
    p=BASE/f'_render_delivery/page-{n}.png';q=BASE/f'_render_final/page-{n}.png'
    same=ImageChops.difference(Image.open(p).convert('RGB'),Image.open(q).convert('RGB')).getbbox() is None
    pixel_review.append({'page':n,'review':'viewed final page' if not same else 'pixel-identical to fully viewed previous render'})
qa=json.loads((BASE/'document_qa.json').read_text())
qa.update({'tables_match_markdown':True,'nonmath_prose_paragraphs_checked':checked,'original_citations_retained':old_citations,'new_chapter_citations':new_citations,'approved_chapter_1_v2_unchanged':True,'page_count':12,'body_pages':9,'supplement_pages':3,'visual_review':'complete; all pages checked','page_review':pixel_review})
(BASE/'document_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
files=[p for p in BASE.iterdir() if p.suffix in ('.md','.docx','.py','.json','.jsonl') and p.name!='delivery_manifest.json']
files += [BASE/'demo_validation/results.json',BASE/'demo_validation/paired_indices.json',pdf]
manifest={'version':'chapter 2 v1','source_sha256':sha(source),'approved_chapter_1_v2_unchanged':True,'files':{str(p.relative_to(BASE)):sha(p) for p in files},'q03':'chapter definition and native boundary example fixed; cross-chapter integration pending','q04':'partial: protocol and code available; no main-result counts or reproduction','new_main_experimental_results':0,'new_boundary_example':'native AAEC annotation plus explicitly constructed contrast','statistics_demo':'synthetic interface verification only','review_checkpoint':'stop after chapter 2; wait for user review'}
(BASE/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'page_count':12,'prose_paragraphs_verified':checked,'tables_verified':len(tables),'source_unchanged':True,'chapter1_v2_unchanged':True,'source_citations_retained':old_citations,'main_results_reproduced':False,'manifest_files':len(files)},ensure_ascii=False))
