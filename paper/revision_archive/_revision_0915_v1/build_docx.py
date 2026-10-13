"""Regenerate edited body inside a copy of the existing DOCX package and styles."""
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
import json, subprocess, sys
from lxml import etree

ROOT=Path(__file__).resolve().parent.parent
WORK=Path(__file__).resolve().parent
source=(ROOT/'_revision_0913/build_docx.py').read_text()
source=source.replace('_revision_0913','_revision_0915_v1').replace('report_0913','report_0915_v1')
source=source.replace('0913修订','0915-v1修订').replace('2026年9月13日','2026年9月15日').replace('[A-C0-9]','[A-D0-9]')
source=source.replace("SYMBOLS['lambda']='λ'", "SYMBOLS.update(epsilon='ϵ', varepsilon='ε'); SYMBOLS['lambda']='λ'")
source=source.replace("if rows[0][0]=='语料': widths=[18,52,30,57]", "if rows[0][0]=='语料': widths=[18,52,30,57]\n    if rows[0][0]=='异常对象': widths=[31,47,79]")
# Start from the source package. Preserve the established style and document
# settings rather than selecting a blank template. Body text follows exact MD
# patches; superseded comments remain available in the untouched v3 artifact.
source=source.replace('doc=Document(); sec=doc.sections[0]', '''doc=Document(ROOT/'report_0914_v3.docx')
initial_section=deepcopy(doc.sections[0]._sectPr)
for child in list(doc._element.body): doc._element.body.remove(child)
doc._element.body.append(initial_section)
for rel in list(doc.part.rels.values()):
    if rel.reltype.endswith('/comments'):
        doc.part.drop_rel(rel.rId)
sec=doc.sections[0]''')
ns={'__file__':str(__file__),'__name__':'__main__','deepcopy':deepcopy}
exec(compile(source,str(WORK/'inherited_layout.py'),'exec'),ns)
doc=ns['doc']; Pt=ns['Pt']
english=False
compact=False
compact_appendix=False
for p in doc.paragraphs:
    if p.text=='Abstract': english=True; continue
    if p.text=='目录': english=False
    if english:
        p.paragraph_format.line_spacing=Pt(18)
        if p.text.startswith('Keywords:'):
            for r in p.runs:r.font.size=Pt(11)
    if p.text.startswith('3.4 实验设置'):compact=True
    if p.text.startswith('第四章 '):compact=False
    if p.text=='附录D 新参考实现与复现实验接口':compact_appendix=True
    if compact_appendix:
        p.paragraph_format.space_after=Pt(0)
        if p.style.name.startswith('Heading') and not p.text.startswith('附录'):
            p.paragraph_format.space_before=Pt(6)
            p.paragraph_format.space_after=Pt(3)
    if compact:
        if p.style.name.startswith('Heading'):
            p.paragraph_format.space_before=Pt(6)
            p.paragraph_format.space_after=Pt(3)
        else:p.paragraph_format.space_after=Pt(0)
    if p.text in ['联合目标为：','论证连接覆盖得分为：','定义为：']:
        p.paragraph_format.keep_with_next=True
# Keep short tables together and avoid a lone final row on the next page.
for table in doc.tables:
    rows=table.rows
    keep_from=0 if len(rows)<=6 else max(0,len(rows)-2)
    for index,row in enumerate(rows):
        if keep_from<=index<len(rows)-1:
            for cell in row.cells:
                for p in cell.paragraphs:p.paragraph_format.keep_with_next=True
out=ROOT/'report_0915_v1.docx'
doc.save(out)
comments=[
 ('本稿采用保守关系修正版作为正文主方案','主方案决定：BR-C进入正文；BR-O保留对照。原数值不自动转为新成绩。'),
 ('RQ2：在固定检查点及候选池下','拆分选择器与修正器的归因；同一初始图的BR-C不能提高组件F1。'),
 ('（2）提出完整候选图评估与保守关系修正方法','贡献二强调固定对象、固定目标和可追踪接受过程，不把四个开关拆成独立创新。'),
 ('候选评分','4.3区分候选排序与冻结初始目标后的修正评分；选择阶段偏差仍保留。'),
 ('覆盖分母、成员及阈值固定','组件冻结与阈值冻结的作用不同，分别阻断改类型和改变出度重定义评分目标。'),
 ('新增边检查是模型支持检查','保护条件不保证关系正确；仍需误删、误加及P/R证据。'),
 ('原版反例：构造两个Claim','构造诊断不是测试集成绩；只证明一个错误增分路径及其被阻断。'),
 ('本节及4.7节的数值表来自','原版历史表原数字保留；待正式保守版结果接入后才能完成主方案定量结论。'),
 ('保守约束采用分步对照','最终消融同时加入严格增分和新增边验证，不能分开归因。'),
 ('0915-v1将已实现的保守关系修正版','原先附录建议已纳入主方法；与代码四个保护开关一致。')
]
helper='/Users/channtang/.codex/plugins/cache/openai-primary-runtime/documents/26.909.12148/skills/documents/scripts/comments_add.py'
args=[sys.executable,helper,str(out),'--out',str(WORK/'commented.docx'),'--author','Codex 0915-v1 修订','--require_all']
for anchor,note in comments:args+=['--add',anchor+'='+note]
subprocess.run(args,check=True)
wns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(WORK/'commented.docx') as zin:
    xml=etree.fromstring(zin.read('word/document.xml'))
    for p in xml.xpath('//w:p[w:pPr]',namespaces=wns):
        prop=p.find('{'+wns['w']+'}pPr')
        if p.index(prop):p.remove(prop);p.insert(0,prop)
    payload=etree.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True)
    with ZipFile(out,'w') as zout:
        for info in zin.infolist():zout.writestr(info,payload if info.filename=='word/document.xml' else zin.read(info.filename))
(WORK/'comment_log.json').write_text(json.dumps(comments,ensure_ascii=False,indent=2))
print('10 new review comments; source v3 unchanged')
