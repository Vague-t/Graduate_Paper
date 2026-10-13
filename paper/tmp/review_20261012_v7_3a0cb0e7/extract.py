from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import json

SRC = Path('/Users/channtang/Downloads/论文规范排版稿_v7.docx')
OUT = Path(__file__).parent
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'm':'http://schemas.openxmlformats.org/officeDocument/2006/math', 'a':'http://schemas.openxmlformats.org/drawingml/2006/main', 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

def txt(e):
    if e is None: return ''
    n=etree.QName(e).localname
    if n in ('t','delText'): return e.text or ''
    if n=='tab': return '\t'
    if n in ('br','cr'): return '\n'
    if n in ('sSub','sSup','sSubSup'):
        b=txt(e.find('m:e',NS))
        for k,op in [('sub','_'),('sup','^')]:
            x=e.find('m:'+k,NS)
            if x is not None: b+=op+'{'+txt(x)+'}'
        return b
    if n=='f': return '('+txt(e.find('m:num',NS))+')/('+txt(e.find('m:den',NS))+')'
    if n=='nary':
        ch=e.find('m:naryPr/m:chr',NS)
        return (ch.get('{'+NS['m']+'}val') if ch is not None else '∫')+'_{'+txt(e.find('m:sub',NS))+'}^{'+txt(e.find('m:sup',NS))+'} '+txt(e.find('m:e',NS))
    if n=='d':
        def c(k,d):
            a=e.find('m:dPr/m:'+k,NS)
            return a.get('{'+NS['m']+'}val') if a is not None else d
        return c('begChr','(')+','.join(txt(a) for a in e.findall('m:e',NS))+c('endChr',')')
    if n=='rad': return 'root['+txt(e.find('m:deg',NS))+']('+txt(e.find('m:e',NS))+')'
    if n=='acc':
        c=e.find('m:accPr/m:chr',NS)
        return (c.get('{'+NS['m']+'}val') if c is not None else '^')+'('+txt(e.find('m:e',NS))+')'
    if n.endswith('Pr'): return ''
    if n=='drawing': return '[IMAGE '+','.join(e.xpath('.//a:blip/@r:embed',namespaces=NS))+']'
    if n=='del': return '[DELETED '+''.join(txt(c) for c in e)+']'
    return ''.join(txt(c) for c in e)

with ZipFile(SRC) as z:
    root=etree.fromstring(z.read('word/document.xml'))
    body=root.find('w:body',NS)
    lines=[]; tables=[]
    for i,e in enumerate(body,1):
        tag=etree.QName(e).localname
        if tag=='p':
            sty=e.xpath('./w:pPr/w:pStyle/@w:val',namespaces=NS)
            lines.append(f'[B{i:04d} P {sty[0] if sty else "Normal"}] '+txt(e))
        elif tag=='tbl':
            rows=[]; lines.append(f'[B{i:04d} TABLE]')
            for ri,r in enumerate(e.findall('w:tr',NS),1):
                vals=[' / '.join(txt(p) for p in c.findall('w:p',NS)) for c in r.findall('w:tc',NS)]
                rows.append(vals); lines.append(f'  R{ri:02d} | '+' | '.join(vals))
            tables.append({'block':i,'rows':rows}); lines.append('[END TABLE]')
    for member in z.namelist():
        if member.startswith(('word/footnotes','word/endnotes','word/comments','word/header','word/footer')) and member.endswith('.xml'):
            er=etree.fromstring(z.read(member)); lines.append('\n['+member+']')
            for p in er.findall('.//w:p',NS): lines.append(txt(p))
    (OUT/'source_ordered.txt').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'tables.json').write_text(json.dumps(tables,ensure_ascii=False,indent=2),encoding='utf-8')
    rels=etree.fromstring(z.read('word/_rels/document.xml.rels'))
    (OUT/'image_relationships.json').write_text(json.dumps([dict(e.attrib) for e in rels if 'image' in e.get('Type','')],ensure_ascii=False,indent=2),encoding='utf-8')
    meta={'source':str(SRC),'body_blocks':len(body),'tables':len(tables),'math_objects':len(root.findall('.//m:oMath',NS)),'insertions':len(root.findall('.//w:ins',NS)),'deletions':len(root.findall('.//w:del',NS)),'media_count':sum(m.startswith('word/media/') for m in z.namelist())}
    (OUT/'extraction_meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False,indent=2))
