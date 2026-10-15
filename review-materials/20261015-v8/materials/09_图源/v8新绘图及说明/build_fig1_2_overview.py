from pathlib import Path
from xml.sax.saxutils import escape
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from lxml import etree
import json,hashlib

ROOT=Path(__file__).resolve().parent
W,H=830,590
WIDTH_CM=14.65
HEIGHT_CM=WIDTH_CM*H/W
fonts={
 'normal':TTFont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',fontNumber=2),
 'bold':TTFont('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',fontNumber=2)
}
text_records=[]
parts=[f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH_CM}cm" height="{HEIGHT_CM:.6f}cm" viewBox="0 0 {W} {H}">
<title>论文研究内容与章节逻辑</title>
<desc>第一章明确研究目标，第二章建立共同理论与表示，第三章和第四章分别研究增强监督的可靠学习与预测结构的联合修正，第五章总结研究结论。第三章所得模型可向第四章提供初始预测，第四章也可以独立使用基准模型。</desc>
<defs>
 <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto"><path d="M 0 0 L 10 5 L 0 10 Z" fill="#53697c"/></marker>
</defs>
<rect width="830" height="590" fill="#ffffff"/>
''']

def box(x,y,w,h,fill,stroke):
 parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

def text(x,y,s,size=20,weight='normal',anchor='start',max_width=None):
 font=fonts[weight]; cmap=font.getBestCmap(); hmtx=font['hmtx'].metrics
 width=sum(hmtx[cmap[ord(c)]][0] for c in s)*size/font['head'].unitsPerEm
 if max_width is not None:
  assert width <= max_width, (s,width,max_width)
 lo=x-width if anchor=='end' else x-width/2 if anchor=='middle' else x
 assert lo>=10 and lo+width<=W-10,(s,lo,width)
 text_records.append({'text':s,'x':x,'y':y,'size':size,'weight':weight,'anchor':anchor,'width':width,'max_width':max_width})
 parts.append(f'<text x="{x}" y="{y}" font-family="Noto Sans CJK SC" font-size="{size}" font-weight="{700 if weight=="bold" else 400}" text-anchor="{anchor}" fill="#203246">{escape(s)}</text>')

def arrow(d,dashed=False):
 dash=' stroke-dasharray="6 4"' if dashed else ''
 parts.append(f'<path d="{d}" fill="none" stroke="#53697c" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arrow)"{dash}/>')

# Introductory chapters establish the goal and common foundations.
box(25,14,780,68,'#f1f5f8','#71869a')
text(415,41,'第1章  研究目标与问题',22,'bold','middle',740)
text(415,67,'提高端到端论辩挖掘中组件与关系联合抽取的准确性',20,'normal','middle',740)
arrow('M 415 83 L 415 103')
box(25,108,780,68,'#f1f5f8','#71869a')
text(415,135,'第2章  共同理论与任务表示',22,'bold','middle',740)
text(415,161,'论辩图表示 · 生成式抽取 · 一致性学习 · 结构化预测',20,'normal','middle',740)

# Two independently meaningful research problems share the same foundations.
arrow('M 415 177 L 415 194 L 207.5 194 L 207.5 215')
arrow('M 415 194 L 622.5 194 L 622.5 215')
box(25,219,365,239,'#f4f8fc','#47769b')
box(440,219,365,239,'#fff8ef','#b28345')
parts.append('<path d="M 25 263 H 390" stroke="#a9bfd1" stroke-width="1.5"/>')
parts.append('<path d="M 440 263 H 805" stroke="#d8bd97" stroke-width="1.5"/>')
text(207.5,248,'第3章  可靠监督与一致性学习',21,'bold','middle',335)
text(622.5,248,'第4章  结构约束联合修正',21,'bold','middle',335)

for yy,ss in [
 (294,'输入：已标注文本及其改写'),
 (362,'问题：改写后原监督可能失效'),
 (412,'结果：训练后的抽取模型'),
]:text(45,yy,ss,20,max_width=325)
for yy,ss in [
 (294,'输入：初始预测'),
 (321,'（第3章模型或基准模型）'),
 (362,'问题：组件与关系需协调修改'),
 (412,'结果：修正后的完整论辩图'),
]:text(460,yy,ss,20,max_width=325)
# Optional model-to-prediction link: source aligns with chapter 3's result;
# destination aligns with chapter 4's input. It is not the only route into chapter 4.
arrow('M 390 412 L 415 412 L 415 294 L 437 294',dashed=True)

# Both studies support the concluding chapter.
arrow('M 207.5 459 L 207.5 482 L 415 482 L 415 501')
parts.append('<path d="M 622.5 459 L 622.5 482 L 415 482" fill="none" stroke="#53697c" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
box(25,506,780,68,'#f1f5f8','#71869a')
text(415,534,'第5章  总结与展望',22,'bold','middle',740)
text(415,560,'归纳研究结论，分析方法局限，讨论后续研究方向',20,'normal','middle',740)
parts.append('</svg>')
svg='\n'.join(parts)
editable=ROOT/'fig1_2_overview.svg';editable.write_text(svg)

# Deterministic outlined sibling; all positions and advances use the actual SC fonts.
root=etree.fromstring(svg.encode())
SVGNS='{http://www.w3.org/2000/svg}'
for elem,rec in zip(root.findall('.//'+SVGNS+'text'),text_records):
 font=fonts[rec['weight']];cmap=font.getBestCmap();glyphs=font.getGlyphSet();units=font['head'].unitsPerEm
 scale=rec['size']/units
 x=rec['x']-rec['width']/2 if rec['anchor']=='middle' else rec['x']-rec['width'] if rec['anchor']=='end' else rec['x']
 group=etree.Element(SVGNS+'g',{'fill':'#203246','aria-label':rec['text']})
 for ch in rec['text']:
  name=cmap[ord(ch)];pen=SVGPathPen(glyphs);glyphs[name].draw(pen);path=pen.getCommands()
  if path:etree.SubElement(group,SVGNS+'path',{'d':path,'transform':f'translate({x:.6f},{rec["y"]:.6f}) scale({scale:.8f},{-scale:.8f})'})
  x+=font['hmtx'].metrics[name][0]*scale
 elem.getparent().replace(elem,group)
outlined=ROOT/'fig1_2_overview.outlined.svg'
outlined.write_bytes(etree.tostring(root,encoding='utf-8',xml_declaration=True))

mapping={
 'figure':'1.2','recommended_caption':'图1.2 论文研究内容与章节逻辑',
 'role':'论文整体结构图，合并原图1.2研究内容总览与原图1.3章节逻辑职责；不展示具体技术步骤。',
 'source_document':'/workspace/thesis_v7_revision_20261015/论文_v7_结构压缩与格式修订_含模拟扩展.docx',
 'relationships':[
  {'id':'rIdRevisionfig1_2','target':'word/media/fig1_2.png','replacement':str(ROOT/'fig1_2_overview.png')},
  {'id':'rIdRevSVG1','target':'word/media/revised_1.svg','replacement':str(outlined)}
 ],
 'editable_svg':str(editable),'outlined_svg':str(outlined),'png':str(ROOT/'fig1_2_overview.png'),
 'viewBox':[0,0,W,H], 'recommended_extent_cm':[WIDTH_CM,round(HEIGHT_CM,6)],
 'recommended_extent_emu':{'cx':round(WIDTH_CM*360000),'cy':round(HEIGHT_CM*360000)},
 'minimum_printed_font_pt':round(20*(WIDTH_CM/2.54*72)/W,3),
 'font':'Noto Sans CJK SC','source_text_count':len(text_records),'all_text_within_boxes':True,
 'arrow_semantics':[
  '第1章→第2章：研究目标引出共同理论与任务表示。',
  '第2章→第3章、第4章：为两项研究分别提供共同基础，不代表两项研究必须串行。',
  '第3章结果→第4章输入（虚线）：训练所得模型可生成初始预测；第4章也可使用基准模型。',
  '第3章、第4章→第5章：两项研究共同支撑结论与展望。'
 ],
 'no_overflow_checks':text_records,
 'document_mutated':False
}
(ROOT.parent/'fig1_2_mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2))
print(json.dumps({'editable':str(editable),'outlined':str(outlined),'extent_cm':mapping['recommended_extent_cm'],'minimum_pt':mapping['minimum_printed_font_pt']},ensure_ascii=False))
