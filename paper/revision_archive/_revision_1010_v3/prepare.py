"""Initialize the figure and metadata revision while preserving the reviewed draft."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'report_1010_v2_full.md')=='a2aeb98935b8d7cb242644ad06034f4d2e7405998951e258fbdc3c67dae6a6b7'
assert sha(R/'report_1010_v2_full.docx')=='c03523d4d9d91837c88853ec46d46ace29bf44c8f9a8d03bdbeffdbd76a0d510'
for n in ['render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','table_splits.json','final_audit.py','build_docx.py','audit_scenario.py']:
    s=(P/n).read_text().replace('1010_v2','1010_v3').replace('1010-v2','1010-v3')
    if n=='build_docx.py':s=s.replace("template=R/'report_1010_v1_full.docx'","template=R/'report_1010_v2_full.docx'").replace("'v10_'","'v11_'")
    if n=='audit_scenario.py':s=s.replace("old=(W.parent/'report_1010_v1_full.md')","old=(W.parent/'report_1010_v2_full.md')")
    (W/n).write_text(s)
raw=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
for n in raw:shutil.copy2(P/n,W/n)
(W/'figures').mkdir(exist_ok=True)
for f in (P/'figures').glob('*.png'):shutil.copy2(f,W/'figures'/f.name)
c=json.loads((P/'reference_config.json').read_text())
c['manuscript_version']='1010-v3'
c['authoring_revision']['matched_training_main_tables']=['3-5','3-6','3-8']
c['authoring_revision']['construction_cost_table']='3-9'
c['authoring_revision']['metadata_note']='Manuscript/figure revision only; method configuration identity and all simulated observations unchanged.'
(W/'reference_config.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
s=(R/'report_1010_v2_full.md').read_text().replace('_revision_1010_v2/','_revision_1010_v3/').replace('1010-v2 模拟数据演示稿','1010-v3 模拟数据演示稿')
old='配置身份为1010-v1-global-review。'
new='方法配置身份沿用1010-v1-global-review；文稿版本为1010-v3，单独登记，不表示重新运行实验或更改方法配置。'
assert s.count(old)==1;s=s.replace(old,new)
old='数据流表示文本和隐藏状态的传递；各类参数的梯度来源在3.4.3节统一说明。'
new='实线表示文本和隐藏状态的数据流，虚线表示监督或控制连接；冻结参数与可训练模块分别标示，各类参数的梯度来源在3.4.3节统一说明。'
assert s.count(old)==1;s=s.replace(old,new)
(R/'report_1010_v3_full.md').write_text(s)
old=R/'report_1010_v2_full.docx'
with zipfile.ZipFile(old) as z:
    parts=[{'name':n,'sha256':hashlib.sha256(z.read(n)).hexdigest(),'policy':'preserve-only' if n.startswith(('word/media/','word/theme/','customXml/')) or n in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'} else 'editable'} for n in z.namelist()]
    body=etree.fromstring(z.read('word/document.xml'))
    sections=[etree.tostring(x,encoding='unicode') for x in body.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
baseline=['report_1010_v2_full.docx','report_1010_v2_full.md','1010_v2全局评审与完整修改建议.md','1010_v2逐项修改与未决事项说明.md']+[str((P/n).relative_to(R)) for n in raw+['reference_config.json']]
(W/'template-evidence.json').write_text(json.dumps({'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_final'),'reference_render_pages':107,'parts':parts,'sections':sections,'baseline_hashes':{n:sha(R/n) for n in baseline}},ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1010-v3 图示与元数据修订契约

保留参考Word及其107页已逐页核验的排版。三节A4、字体、行距、页眉页脚、题注、三线表、原生公式、目录、图表索引及续表组件沿用现有模板，具体几何和保留部件散列见template-evidence.json。父版artifact.md和此前样式证据仍适用。本轮页眉改为1010-v3，七张方法图重绘，四张定量图原字节复用；图像槽位仍位于对应正文与题注之间，宽157 mm。图注和方法边界保留，仅训练图的连线说明随实际图例同步。

正文只补清文稿与方法配置身份，正文32个陈列公式、407个原生数学对象、44表、11图、3算法、49参考文献和附录E保持。配置索引修正为训练主表3-5/3-6/3-8及构造成本3-9，原配置身份不改。原始人工情景7文件保持字节相同。未做真实实验，不修改模拟标识、不增加论文主张、不扩写诊断协议。最终每页重新渲染核验，目录缓存与最终PDF一致。旧版本不修改。
''')
print('Prepared 1010-v3; retained source and package hashes verified')
