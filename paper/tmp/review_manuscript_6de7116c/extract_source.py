from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import json

SRC = Path('/Users/channtang/Downloads/manuscript_review_test.docx')
OUT = Path(__file__).parent
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

def local(e): return etree.QName(e).localname
def txt(e):
    if e is None: return ''
    n=local(e)
    if n in ('t','delText'): return e.text or ''
    if n in ('tab',): return '\t'
    if n in ('br','cr'): return '\n'
    if n in ('sSub','sSup','sSubSup'):
        b=txt(e.find('m:e',NS))
        for k,op in [('sub','_'),('sup','^')]:
            x=e.find('m:'+k,NS)
            if x is not None: b+=op+'{'+txt(x)+'}'
        return b
    if n=='f': return '('+txt(e.find('m:num',NS))+')/('+txt(e.find('m:den',NS))+')'
    if n in ('pPr','rPr','tblPr','tcPr','trPr'): return ''
    if n=='drawing':
        ids=e.xpath('.//a:blip/@r:embed',namespaces=NS)
        return '[IMAGE '+','.join(ids)+']'
    if n=='del': return '[DELETED '+''.join(txt(c) for c in e)+']'
    return ''.join(txt(c) for c in e)

with ZipFile(SRC) as z:
    root=etree.fromstring(z.read('word/document.xml'))
    body=root.find('w:body',NS)
    lines=[]
    for i,e in enumerate(body,1):
        tag=local(e)
        if tag=='p':
            style=e.xpath('./w:pPr/w:pStyle/@w:val',namespaces=NS)
            lines.append(f'[B{i:04d} P {style[0] if style else "Normal"}] '+txt(e))
        elif tag=='tbl':
            lines.append(f'[B{i:04d} TABLE]')
            for ri,r in enumerate(e.findall('w:tr',NS),1):
                vals=[' / '.join(txt(p) for p in c.findall('w:p',NS)) for c in r.findall('w:tc',NS)]
                lines.append(f'  R{ri:02d} | '+' | '.join(vals))
            lines.append('[END TABLE]')
    for member in ['word/footnotes.xml','word/endnotes.xml','word/comments.xml']:
        if member in z.namelist():
            lines.append('\n['+member+']')
            er=etree.fromstring(z.read(member))
            for p in er.findall('.//w:p',NS): lines.append(txt(p))
    (OUT/'source_ordered.txt').write_text('\n'.join(lines),encoding='utf-8')
    ims=[]
    for member in z.namelist():
        if member.startswith('word/media/'):
            path=OUT/'media'/Path(member).name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(z.read(member))
            ims.append(str(path))
    meta={'source':str(SRC),'body_blocks':len(body),'tables':len(root.findall('.//w:tbl',NS)),
          'math_objects':len(root.findall('.//m:oMath',NS)),
          'insertions':len(root.findall('.//w:ins',NS)),'deletions':len(root.findall('.//w:del',NS)),
          'images':ims}
    (OUT/'extraction_meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False,indent=2))
