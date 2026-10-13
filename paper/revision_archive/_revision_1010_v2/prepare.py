"""Preserve the reviewed version and initialize a bounded editorial revision."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'report_1010_v1_full.md')=='8d3a6ea43cb0f6c41144b9ec44cd5990dbba7a7dd59c5c9d85f3eb4d5f729b1a'
assert sha(R/'report_1010_v1_full.docx')=='989c0edf99b576d6e38d1a10e0cf0a77a0c58265b028e990d9429f42f9bca6c8'
for n in ['render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','table_splits.json','final_audit.py','build_docx.py','audit_scenario.py']:
    s=(P/n).read_text().replace('1010_v1','1010_v2').replace('1010-v1','1010-v2')
    if n=='build_docx.py':
        s=s.replace("template=R/'report_1009_v4_full.docx'","template=R/'report_1010_v1_full.docx'").replace("'v9_'","'v10_'")
        s=s.replace("'表3-1':[33,62,62], '表3-6':[29,65,63],\n                '表4-1':[47,64,46], '表4-10':[22,50,42.5,42.5],", "'表4-9':[22,50,42.5,42.5],")
    if n=='audit_scenario.py':s=s.replace("old=(W.parent/'report_1009_v4_full.md')","old=(W.parent/'report_1010_v1_full.md')")
    (W/n).write_text(s)
raw=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
for n in raw+['reference_config.json']:shutil.copy2(P/n,W/n)
shutil.copytree(P/'figures',W/'figures',dirs_exist_ok=True)
old=R/'report_1010_v1_full.docx'
with zipfile.ZipFile(old) as z:
    parts=[{'name':n,'sha256':hashlib.sha256(z.read(n)).hexdigest(),'policy':'preserve-only' if n.startswith(('word/media/','word/theme/','customXml/')) or n in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'} else 'editable'} for n in z.namelist()]
    body=etree.fromstring(z.read('word/document.xml'))
    sections=[etree.tostring(x,encoding='unicode') for x in body.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
baseline=['report_1010_v1_full.docx','report_1010_v1_full.md','1010_v1全局评审与完整修改建议.md','1010_v1全局评审逐项落实与核验说明.md']+[str((P/n).relative_to(R)) for n in raw]
(W/'template-evidence.json').write_text(json.dumps({'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_final'),'reference_render_pages':109,'parts':parts,'sections':sections,'baseline_hashes':{n:sha(R/n) for n in baseline}},ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1010-v2 修订排版契约

参考为已核验的 report_1010_v1_full.docx 及其109页最终渲染。原稿及评审文件保持原字节。继承三节A4、正文和数学字号、段落行距、页眉页脚、可点击目录及图表索引，具体XML和部件散列见 template-evidence.json。沿用现有段落、题注、三线表、原生数学及图像组件，不换设计系统。

本轮仅按2026年10月10日新评审作局部替换与收束：删除三张无结果的诊断方案表，压缩对应正文；第五章保留四格、净计数、在线配置和完整超边证据，标题与现有证据对齐；补清严格筛选可能排斥复杂文档的未决风险、局部累计与全局净预算不同域；将核心实验待办集中H.5，与6.3真正拓展分开；修正成绩轨道表号及独立简例引用。图表在各章内连续重新编号，全部引用同步。

32个陈列公式、11张图片、49条参考文献和附录E原文保持，所有原始人工情景文件原字节复用，不生成新的实验数字。封面、摘要与结果图表保留模拟身份。新版本页眉1010-v2；每页重渲染并检查，目录缓存与最终PDF页码核对，保留部件及三节几何结构必须一致。任何未获真实运行证据的问题在逐项说明中保持未完成，禁止以文字修改冒充实证完成。
''')
print('prepared',sha(old))
