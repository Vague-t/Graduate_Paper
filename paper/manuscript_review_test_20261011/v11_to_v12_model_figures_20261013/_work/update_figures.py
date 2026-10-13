from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import hashlib, json, sys

O = Path(__file__).resolve().parents[1]
ROOT = Path('/Users/channtang/Downloads/paper')
SOURCE = ROOT / '论文规范排版稿_v11.docx'
OUTPUT = O / '论文规范排版稿_v12.docx'
ASSETS = O / '模型图_Qwen3.5-9B_v12'
ITEMS = [(3, 322, '图2-1_端到端论辩挖掘总体架构'),
         (5, 407, '图3-2_关系影响域约束的可靠成对学习'),
         (6, 533, '图4-1_多候选驱动的依赖闭合修正')]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == '47fd5bb42baae2d6e71746b7cf64cb24121aab6588c71496c332d6448c3ac600'
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
      'asvg':'http://schemas.microsoft.com/office/drawing/2016/SVG/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with ZipFile(SOURCE) as z:
    data = {n:z.read(n) for n in z.namelist()}

if sys.argv[1] == 'assets':
    ASSETS.mkdir(parents=True, exist_ok=True)
    manifest = []
    for idx, block, stem in ITEMS:
        before = data[f'word/media/image{idx}.svg'].decode('utf-8')
        after = before.replace('Qwen3.8','Qwen3.5').replace('27B','9B').replace('16全注意力块','8个全注意力块').replace('仅16个全注意力块','仅8个全注意力块')
        assert after != before and 'Qwen3.8' not in after and '27B' not in after
        root = E.fromstring(after.encode())
        texts = root.xpath('//*[local-name()="text"]/text()')
        assert not any('16' in t and '注意力' in t for t in texts)
        svg = ASSETS / (stem + '.svg')
        svg.write_text(after, encoding='utf-8')
        manifest.append({'source_media_index':idx,'block_index':block,'stem':stem,
                         'svg':str(svg),'png':str(svg.with_suffix('.png')),
                         'visible_model_tokens':sum('Qwen3.5' in t for t in texts),
                         'attention_labels':[t for t in texts if '注意力块' in t],
                         'text_objects':len(texts),'svg_sha256':sha(svg)})
    (O/'_work/figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
elif sys.argv[1] == 'docx':
    r = E.fromstring(data['word/document.xml'])
    body = r.find('{'+NS['w']+'}body')
    rel = E.fromstring(data['word/_rels/document.xml.rels'])
    RN = '{http://schemas.openxmlformats.org/package/2006/relationships}'
    for idx, block, stem in ITEMS:
        svg = ASSETS/(stem+'.svg'); png = svg.with_suffix('.png')
        assert svg.exists() and png.exists()
        data[f'word/media/image{idx}.svg'] = svg.read_bytes()
        data[f'word/media/image{idx}_v12.png'] = png.read_bytes()
        rid = f'rIdV12Fallback{idx}'
        assert not any(x.get('Id') == rid for x in rel)
        E.SubElement(rel,RN+'Relationship',Id=rid,
                     Type=NS['r']+'/image',Target=f'media/image{idx}_v12.png')
        drawing = body[block]
        svg_refs = drawing.xpath('.//asvg:svgBlip',namespaces=NS)
        assert len(svg_refs) == 1
        svg_rid = svg_refs[0].get('{'+NS['r']+'}embed')
        assert next(x for x in rel if x.get('Id') == svg_rid).get('Target') == f'media/image{idx}.svg'
        blips = drawing.xpath('.//a:blip',namespaces=NS)
        assert len(blips) == 1
        blips[0].set('{'+NS['r']+'}embed',rid)
        for dp in drawing.xpath('.//wp:docPr',namespaces=NS):
            dp.set('descr',stem.replace('_',' ')+'；Qwen3.5-9B；SVG矢量图及300 dpi PNG兼容预览。')
    data['word/document.xml'] = E.tostring(r,xml_declaration=True,encoding='UTF-8',standalone=True)
    data['word/_rels/document.xml.rels'] = E.tostring(rel,xml_declaration=True,encoding='UTF-8',standalone=True)
    ct = E.fromstring(data['[Content_Types].xml'])
    assert any(x.get('Extension')=='png' and x.get('ContentType')=='image/png' for x in ct)
    with ZipFile(OUTPUT,'w',ZIP_DEFLATED) as z:
        for n,d in data.items():z.writestr(n,d)
    print(json.dumps({'output':str(OUTPUT),'sha256':sha(OUTPUT)},ensure_ascii=False))
else:
    raise ValueError(sys.argv[1])
