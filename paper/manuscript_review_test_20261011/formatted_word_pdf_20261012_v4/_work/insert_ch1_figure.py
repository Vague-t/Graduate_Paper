from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
from PIL import Image
import hashlib, json

OUTDIR = Path(__file__).resolve().parents[1]
SOURCE = OUTDIR.parent/'formatted_word_pdf_20261012_v3/论文规范排版稿_v3.docx'
OUT = OUTDIR/'论文规范排版稿_v4.docx'
FIG = OUTDIR/'图1-2_总体研究框架_简化版.png'
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}
xp = lambda el,q: el.xpath(q,namespaces=NS)
text = lambda el: ''.join(xp(el,'.//w:t/text()'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
old_caption = '图1-2 组件关系依赖下的两项研究内容'
new_caption = '图1-2 端到端论辩挖掘的总体研究框架'
source_sha = sha(SOURCE)
with ZipFile(SOURCE) as zin:
    data = {name:zin.read(name) for name in zin.namelist()}
root = etree.fromstring(data['word/document.xml'])
paragraphs = xp(root,'.//w:body/w:p')
caps = [p for p in paragraphs if text(p)==old_caption]
assert len(caps)==1
caption = caps[0]
figure_p = caption.getprevious()
rid = xp(figure_p,'.//a:blip/@r:embed')
assert len(rid)==1
assert len(xp(root,'.//a:blip[@r:embed="'+rid[0]+'"]'))==1
rels = etree.fromstring(data['word/_rels/document.xml.rels'])
target = next(r.get('Target') for r in rels if r.get('Id')==rid[0])
part = 'word/'+target
assert part.endswith('.png')
with Image.open(FIG) as im:
    assert im.format=='PNG'
    width_px, height_px = im.size
    assert width_px>=1500
old_ext = xp(figure_p,'.//wp:extent')[0]
width = int(old_ext.get('cx'))
old_height = int(old_ext.get('cy'))
height = round(width*height_px/width_px)
for extent in xp(figure_p,'.//wp:extent|.//a:xfrm/a:ext'):
    extent.set('cx',str(width));extent.set('cy',str(height))
docpr = xp(figure_p,'.//wp:docPr')[0]
docpr.set('name','第一章总体研究框架简化图')
docpr.set('descr','上部为关系感知的可靠成对学习，下部为依赖闭合的结构修正；训练后的生成器用于候选图生成，推理阶段原文保持不变。')
texts = xp(caption,'.//w:t')
texts[0].text=new_caption
for t in texts[1:]:t.text=''
data['word/document.xml']=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
data[part]=FIG.read_bytes()
with ZipFile(OUT,'w',compression=ZIP_DEFLATED) as zout:
    for name,content in data.items():zout.writestr(name,content)
assert sha(SOURCE)==source_sha
manifest={'source':str(SOURCE),'output':str(OUT),'figure':str(FIG),
          'source_sha256':source_sha,'output_sha256':sha(OUT),'figure_sha256':sha(FIG),
          'location':'第一章 1.3 研究问题与主要研究工作','figure_number':'图1-2',
          'replaced_media_part':part,'caption_before':old_caption,'caption_after':new_caption,
          'figure_pixels':[width_px,height_px],'figure_extent_emu':[width,height],
          'prior_figure_extent_emu':[width,old_height],
          'allowed_changed_parts':['word/document.xml',part]}
(OUTDIR/'_work/figure_insertion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps(manifest,ensure_ascii=False))
