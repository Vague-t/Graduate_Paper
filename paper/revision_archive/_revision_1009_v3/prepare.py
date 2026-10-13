"""Prepare the user-authorized simulation edition, preserving v2."""
from pathlib import Path
import hashlib,json,zipfile,shutil
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1009_v2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ['render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','table_splits.json','final_audit.py']:
    text=(P/name).read_text().replace('1009_v2','1009_v3').replace('1009-v2','1009-v3')
    if name=='cache_pages.py':
        text=text.replace("'构造验证不替代语料实验' not in norm(''.join(p['lines']))", "'1009-v3' not in norm(''.join(p['lines']))")
    if name=='final_audit.py':
        text=text.replace('assert len(images) == 7','assert len(images) == 11')
        text=text.replace("for token in ['1009-v3', '构造验证', '语料实验']", "for token in ['1009-v3']")
        text=text.replace("'all_pages_have_evidence_boundary': True", "'simulation_disclosure_on_cover': '模拟数据演示稿' in page_texts[0] and '不代表真实实验' in page_texts[0], 'all_pages_have_version': True")
    (W/name).write_text(text)
(W/'figures').mkdir(exist_ok=True)
for name in ['repair.png','bounded_execution.png']:
    shutil.copy2(P/'figures'/name,W/'figures'/name)
old=R/'report_1009_v2_full.docx';parts=[]
with zipfile.ZipFile(old) as z:
    for name in z.namelist():
        preserve=name.startswith(('word/media/','word/theme/','customXml/')) or name in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'}
        parts.append({'name':name,'sha256':hashlib.sha256(z.read(name)).hexdigest(),'policy':'preserve-only' if preserve else 'editable'})
    body=etree.fromstring(z.read('word/document.xml'))
    sections=[etree.tostring(x,encoding='unicode') for x in body.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
baseline=['report_1009_v2_full.docx','report_1009_v2_full.md','1009_v2逐项修改与证据闭环说明.md','1009_v2复审后完整修改建议与实施方案.md','_revision_1009_v2/validate_mechanisms.py','_revision_1009_v2/mechanism_results.json','_revision_1009_v2/validate_interfaces.py','_revision_1009_v2/interface_results.json']
record={'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_delivery'),'reference_render_pages':90,'parts':parts,'sections':sections,'baseline_hashes':{f:sha(R/f) for f in baseline}}
(W/'template-evidence.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1009 v3 模拟数据演示稿排版契约

参考为 report_1009_v2_full.docx，90页，三节A4，现有标题、字体、行距、页边距、原生公式和可点击目录沿用。参考渲染和完整逐页记录在 _revision_1009_v2/render_delivery 与 visual_review.json，包与基准哈希见 template-evidence.json。

授权变化：开头统一说明模拟数据身份；正文不反复显示未运行或占位提醒；改写结果与讨论，纳入完整数值、四格、成本和失败解释；落实S01尝试与提交分离、S02策略比较归因；增加四幅结果图。六章、两研究、32陈列公式、46文献保留，附录E历史正文逐字保留。构造机制材料保留适用范围。真实作者签名、资助和伦理信息不编造。

页眉第二行只保留1009-v3版本，明确模拟身份的完整说明仅置中文封面。所有正文数据来自本目录中可复算的计数级情景文件，没有真实模型或求解器运行含义。所有历史媒体、主题、customXML与原页面几何保留；Word原生结构和正文字号继承，不缩字挤页。新增长表按语义分页并加续题与重复表头。最终重新渲染、检查全部页面、更新目录缓存，交付新的Word与Markdown以及简洁替换说明。
''')
print('v3 prepared',sha(old))
