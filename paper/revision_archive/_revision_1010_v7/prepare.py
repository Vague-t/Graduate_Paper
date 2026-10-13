"""Prepare a separate, explicitly hypothetical revision. Never alter v6."""
from pathlib import Path
import ast, hashlib, json, shutil, zipfile
from lxml import etree

W=Path(__file__).resolve().parent; R=W.parent; P=R/'_revision_1010_v6'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'report_1010_v6_full.md')=='d49d4ef81440bee861e9ea4d6f24da112fda95d03f3dd80d6b110fada8eecebe'
assert sha(R/'report_1010_v6_full.docx')=='969fcf8f8956813283737520c9d6bc585c34a0e3fcc825d0a0a27a459562f510'
targets={
 't0_i0':[(.782,.533),(.702,.481)],
 'plain_i0':[(.788,.539),(.707,.487)],
 'qos_i0':[(.794,.550),(.713,.498)],
 'full_data_i0':[(.797,.557),(.718,.505)],
 'head_i0':[(.800,.566),(.723,.513)],
 't1_i0':[(.805,.578),(.728,.525)],
 'no_boundary_i0':[(.799,.563),(.720,.510)],
 'no_none_i0':[(.801,.567),(.723,.514)],
 'random_i0':[(.804,.576),(.726,.522)],
 'noaug_head_i0':[(.786,.537),(.705,.485)],
 't0_i1':[(.799,.573),(.718,.525)],
 'br_o':[(.811,.586),(.734,.534)],
 'br_c':[(.805,.590),(.728,.540)],
 'sequential':[(.813,.596),(.736,.546)],
 'relation_only':[(.805,.596),(.728,.548)],
 'single_object':[(.818,.607),(.741,.559)],
 't1_i1':[(.823,.619),(.748,.574)],
 'uncalibrated':[(.823,.601),(.748,.552)],
 'global_equal':[(.826,.623),(.752,.579)],
 'global_long':[(.829,.631),(.755,.587)],
 'regenerate':[(.814,.600),(.737,.549)],
}
source=(P/'generate_scenario.py').read_text()
tree=ast.parse(source)
assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TARGETS' for t in n.targets))
lines=source.splitlines(True)
lines[assignment.lineno-1:assignment.end_lineno]=['TARGETS='+repr(targets)+'\n']
source=''.join(lines).replace("('global_equal','t1_i1')]:", "('global_equal','t1_i1'),('t1_i1','relation_only'),('t1_i1','single_object')]:")
source=source.replace('Targets below are authoring assumptions.', 'Targets below are authoring assumptions for EST-1010-V7, not fitted estimates.\nThe v6 baseline and noise are retained to isolate the effect of smaller assumed gains.')
(W/'generate_scenario.py').write_text(source)
for n in ['derived_tables.json','score_records.json','audit_judgements.json','algorithm_splits.json','table_splits.json','reference_config.json']:
 shutil.copy2(P/n,W/n)
# The historical auxiliary track stays bound to its own original records.
for n in ['supplement_results.json','supplement_manifest.json','generate_supplement.py']+list(json.loads((P/'supplement_manifest.json').read_text())['files']):
 shutil.copy2(P/n,W/n)
for f in (P/'figures').iterdir():
 if f.suffix in ['.png','.svg','.pdf']:shutil.copy2(f,W/'figures'/f.name)
for n in ['render_document.py','fonts.conf','cache_pages.py']:
 (W/n).write_text((P/n).read_text().replace('1010_v6','1010_v7').replace('1010-v6','1010-v7'))
audit=(P/'audit_scenario.py').read_text().replace("source=(W.parent/'report_1010_v6_full.md')","source=(W.parent/'report_1010_v7_full.md')").replace("old=(W.parent/'report_1010_v5_full.md')","old=(W.parent/'report_1010_v6_full.md')").replace('稿件说明：本稿为模拟数据演示稿。','稿件说明：本稿为估算演示版。')
(W/'audit_scenario.py').write_text(audit)
with zipfile.ZipFile(R/'report_1010_v6_full.docx') as z:
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
 root=etree.fromstring(z.read('word/document.xml'))
 sections=[etree.tostring(x).decode() for x in root.xpath('//w:sectPr',namespaces=ns)]
 parts={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
evidence={'reference':str(R/'report_1010_v6_full.docx'),'sha256':sha(R/'report_1010_v6_full.docx'),'reference_render':str(P/'render_final'),'sections':sections,'parts':parts,'baseline_hashes':{str(p.relative_to(R)):sha(p) for p in [R/'report_1010_v6_full.md',R/'report_1010_v6_full.docx']}}
(W/'template-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
(W/'assumptions.json').write_text(json.dumps({'identity':'EST-1010-V7','status':'AUTHORING_ASSUMPTIONS_NOT_EMPIRICAL_ESTIMATES','targets':targets,'rationale':'Retain the v6 T0 baseline, task definition, noise and assigned resource costs; reduce assumed training and inference gains. No data-driven fit, literature transfer or estimate of genuine performance. Frozen-component controls retain T1 component counts. CPU diagnostics are quoted only as separate historical observations.','real_model_runs_added':0,'legacy_supplement_identity':'SIM-1010-V4','legacy_supplement_uses_v6_main_counts':True,'stress_tests':{'paired_learning_delta_relation_pp':[-0.5,0.0,1.2],'component_mutability_delta_relation_pp':[-0.5,0.0,2.3],'local_minus_global_relation_pp':[-1.5,-0.5,0.5],'scoring_cost_multiplier':[0.5,1.0,2.0]}},ensure_ascii=False,indent=2))
(W/'artifact.md').write_text('''# 1010 v7 估算演示修订契约

参考为 report_1010_v6_full.docx，SHA-256 969fcf8f8956813283737520c9d6bc585c34a0e3fcc825d0a0a27a459562f510。其已存在的112页渲染绑定同一文件。此次为定点文本、数值及三张统计图修改，直接修改保留包的相关XML节点，不重建正文和样式。

保留三个节的页幅、边距、字体与样式、段落和表格属性、411个数学对象、32个陈列公式、3段算法、49条文献及附录E。所有标题与题注编号、书签、超链接关系和3个目录域保持；缓存页码在最终渲染后按真实标题位置更新，Word更新标志保留。图像按原显示尺寸替换，其他媒体字节保持。

修改位置由 compose.py 的精确段落片段和表号映射登记。正文表3-5、3-6、3-8、4-3、4-7、5-1至5-5重算；图3-3、4-3、5-1重绘；摘要及所有相关差值同步。D.3增加已保存CPU诊断的来源绑定数值；H.5追加估算参数与压力情景解释。旧附录H.6至H.8独立存档，其旧计数不与新版主表混用。封面、摘要、页眉与表图保留估算身份。全部其余包部件逐字节核验，原稿不变。
''')
print('Prepared v7; no original files modified.')
