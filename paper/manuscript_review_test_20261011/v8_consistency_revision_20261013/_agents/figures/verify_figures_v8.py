"""Read exported figures, create a scaled QA-only PDF, and bind final artifacts."""
from pathlib import Path
import hashlib,json,subprocess,sys
import xml.etree.ElementTree as ET
from pypdf import PdfReader,PdfWriter
from PIL import Image
import pymupdf
HERE=Path(__file__).resolve().parent
QA=HERE/'_work'/'qa'
SKILL=Path('/Users/channtang/.codex/skills/nature-figure/scripts')
NAMES=['fig2_1_overall_v8','fig3_2_training_v8','fig4_1_inference_v8']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=HERE/'draw_editable_models_v8.py'
pre=subprocess.run([sys.executable,str(SKILL/'validate_figure.py'),str(source),'--json'],capture_output=True,text=True)
(QA/'source_preflight.json').write_text(pre.stdout)
assert pre.returncode==0,pre.stdout+pre.stderr
combined=PdfWriter();rows=[]
for name in NAMES:
    orig=HERE/(name+'.pdf'); reader=PdfReader(orig);page=reader.pages[0]
    orig_size=[float(page.mediabox.width)/72*25.4,float(page.mediabox.height)/72*25.4]
    page.scale_by(.8)
    scaled=QA/(name+'.160mm.pdf');one=PdfWriter();one.add_page(page)
    with scaled.open('wb') as f:one.write(f)
    combined.add_page(page)
    text_run=subprocess.run([sys.executable,str(SKILL/'audit_pdf_text.py'),str(scaled),'--min-pt','5','--json'],capture_output=True,text=True)
    (QA/(name+'.text-audit-160mm.json')).write_text(text_run.stdout)
    assert text_run.returncode==0,text_run.stdout+text_run.stderr
    collide=subprocess.run([sys.executable,str(SKILL/'audit_figure_collisions.py'),str(scaled),'--json-out',str(QA/(name+'.collision-160mm.json')),'--overlay-pdf',str(QA/(name+'.collision-160mm.pdf'))],capture_output=True,text=True)
    assert collide.returncode==0,collide.stdout+collide.stderr
    doc=pymupdf.open(scaled);page=doc[0]
    spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
    fontsize=min(s['size'] for s in spans if s['text'].strip())
    assert fontsize>=5,(name,fontsize)
    page.get_pixmap(dpi=200,alpha=False).save(str(QA/(name+'.160mm.png')))
    font_records=[]
    for f in doc.get_page_fonts(0):
        xref,ext,kind,base,*_=f;blob=doc.extract_font(xref)[3]
        assert blob,(name,base,'font not embedded')
        font_records.append({'font':base,'embedded':True,'type':kind})
    root=ET.parse(HERE/(name+'.svg')).getroot();ns={'s':'http://www.w3.org/2000/svg'}
    editable=root.findall('.//s:text',ns);images=root.findall('.//s:image',ns)
    visible='\n'.join(''.join(t.itertext()) for t in editable)
    assert 'Qwen2.5' not in visible and 'Qwen3.8-27B' in visible
    if name!='fig3_2_training_v8':
        for term in ['重排序','合法化','BR-O','I0终态','R_DC','I1终态']:
            assert term in visible,(name,term)
    if name=='fig3_2_training_v8':
        for term in ['全局 LoRA g','门控 LoRA c','仅16个全注意力块','q / k / v / o 投影','结论专项 LoRA']:
            assert term in visible,(name,term)
    if name=='fig4_1_inference_v8':
        for term in ['单对象局部','集合 BR-J：可选','合计≤256','≤64','可共享冻结编码','可训练头独立']:
            assert term in visible,(name,term)
    assert not images
    geom=json.loads((QA/(name+'.geometry.json')).read_text())
    assert not geom['outside_canvas']
    assert all(t['contained'] for t in geom['text_containment'])
    alignment=json.loads((QA/(name+'.subpanel-alignment.json')).read_text())
    assert alignment['verdict']=='PASS'
    collision=json.loads((QA/(name+'.collision-160mm.json')).read_text())
    assert collision['summary']['fail']==0 and collision['summary']['warn']==0
    with Image.open(HERE/(name+'.png')) as im: px=list(im.size)
    rows.append({'figure':name,'source':source.name,'source_sha256':sha(source),'svg':name+'.svg','png':name+'.png','qa_pdf':name+'.pdf','viewBox':root.get('viewBox'),'source_dimensions_mm':orig_size,'word_dimensions_mm':[round(v*.8,4) for v in orig_size],'word_extent_emu':[5760000,round(orig_size[1]/orig_size[0]*5760000)],'png_pixels':px,'png_dpi':300,'effective_png_dpi_at_160mm':375,'editable_text_elements':len(editable),'embedded_images':len(images),'minimum_font_at_160mm_pt':fontsize,'fonts':font_records,'alignment':'PASS, final rendered comparable candidate/dual-view subpanels, 1.5pt tolerance','collision_at_160mm':collision['summary'],'semantic_labels':'PASS','manual_visual_review':'Three final full PNGs opened and checked; final-size QA PNGs checked separately','files':{ext:{'path':str(HERE/(name+'.'+ext)),'sha256':sha(HERE/(name+'.'+ext)),'bytes':(HERE/(name+'.'+ext)).stat().st_size} for ext in ['svg','png','pdf']}})
with (HERE/'figures_qa_v8.pdf').open('wb') as f:combined.write(f)
manifest={'status':'READY_FOR_DOCUMENT_EMBEDDING','version':'v8','source':'draw_editable_models_v8.py','source_sha256':sha(source),'same_source_exports':True,'figure_order':['图2-1','图3-2','图4-1'],'figures':rows,'qa_combined_pdf':{'path':str(HERE/'figures_qa_v8.pdf'),'sha256':sha(HERE/'figures_qa_v8.pdf'),'physical_width_mm':160},'source_validation':json.loads(pre.stdout)['summary'],'source_warning_review':{'no_TIFF':'User requested SVG and PNG, provided native vector PDF for internal QA.','300dpi':'PNG exported at300dpi at200mm width; effective375dpi at160mm; SVG native vector.','dynamic_width':'PDF boxes measured200mm; QA PDFs scaled160mm and glyph floor verified.'},'scientific_scope':'Conceptual architecture only; no new model execution or experimental evidence.','preserved_style':'Network stacks, hidden-state matrices, graph nodes, typed vectors, blue training and orange decision frames.','semantic_scope':['I0 includes reranking, common legalization and BR-O; G0 is the final I0 graph.','R_DC is the appended repair operator; I1 denotes the complete inherited-plus-appended configuration.','Both LoRA branches are limited to16 full-attention q/k/v/o blocks; base weights remain frozen.','Factor/paired losses target global LoRA; gated conclusion branch learns through corresponding generation paths.','S and P may share frozen text representations; trainable heads are independent.','CDCP model proposals cap64; model plus rule supplement cap256.','Default large-pool route is single-object local; set BR-J remains optional.']}
(HERE/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
for r in rows:print(r['figure'],r['png_pixels'],r['word_extent_emu'],r['minimum_font_at_160mm_pt'])
