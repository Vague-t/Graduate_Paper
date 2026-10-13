"""Preserve v4 and initialize the authorized global revision."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1009_v4'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for n in ['render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','table_splits.json','final_audit.py','build_docx.py','audit_scenario.py']:
    s=(P/n).read_text().replace('1009_v4','1010_v1').replace('1009-v4','1010-v1')
    if n=='build_docx.py':
        s=s.replace("template=R/'report_1009_v3_full.docx'","template=R/'report_1009_v4_full.docx'").replace("'v8_'","'v9_'")
    if n=='final_audit.py':s=s.replace('range(1, 47)','range(1, 50)')
    if n=='audit_scenario.py':s=s.replace("old=(W.parent/'report_1009_v3_full.md')","old=(W.parent/'report_1009_v4_full.md')")
    (W/n).write_text(s)
for n in ['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json','reference_config.json']:
    shutil.copy2(P/n,W/n)
shutil.copytree(P/'figures',W/'figures',dirs_exist_ok=True)
old=R/'report_1009_v4_full.docx'
with zipfile.ZipFile(old) as z:
    parts=[{'name':n,'sha256':hashlib.sha256(z.read(n)).hexdigest(),'policy':'preserve-only' if n.startswith(('word/media/','word/theme/','customXml/')) or n in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'} else 'editable'} for n in z.namelist()]
    body=etree.fromstring(z.read('word/document.xml'))
    sections=[etree.tostring(x,encoding='unicode') for x in body.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
baseline=['report_1009_v4_full.docx','report_1009_v4_full.md','1009_v4全局评审与完整修改建议.md','1009_v4复审意见落实与核验说明.md']
baseline += [str((P/n).relative_to(R)) for n in ['document_counts.csv','scenario_results.json','score_records.json','audit_judgements.json','scenario_manifest.json']]
(W/'template-evidence.json').write_text(json.dumps({'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_verified'),'reference_render_pages':99,'parts':parts,'sections':sections,'baseline_hashes':{n:sha(R/n) for n in baseline}},ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1010-v1 全局修订排版契约

使用 report_1009_v4_full.docx 及其99页已验收渲染作为保留模板，保持三节A4、字号行距、原生公式、页眉和可点击目录。保留既有包部件和历史附件E。新版本落实八项全局意见及逐章要求，保持两项研究和六章结构，调整贡献定位、外部研究和第五章分析，集中实现规约到附录。

本版为已授权模拟演示稿；中英文摘要、实验开头、独立表图添加轻量身份。已有人工计数不重新生成，不填造对象交集、表达变化或真实求解状态。新增诊断以具体可执行协议呈现；新派生数值只从既有模拟记录复算。

继承32个陈列公式和11幅图；恢复风险图移第四章，第五章避免重复。所有新增表设置合理列宽与重复表头，附录长表采用续表。最终逐页检查，再交付Word、Markdown和逐项落实说明。
''')
print('prepared',sha(old))
