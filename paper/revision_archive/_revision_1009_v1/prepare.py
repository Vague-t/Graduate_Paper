"""Prepare new-only configuration, rendering helpers and reference evidence."""
from pathlib import Path
import hashlib,json,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=R/'report_1008_v4_full.docx'
config={
 'status':'REFERENCE_SPECIFICATION_NOT_TRAINED_MODEL',
 'center':{'seed':17,'centers_per_document':1,'attempts':4,'accepted':2,'selection':'canonical_json_sha256','full_gold_sources':True},
 'matching':{'same_region_component_count':True,'same_in_degree':True,'max_relative_char_difference':0.2,'random_can_be_conclusion':True},
 'candidates':{'head_top_n':64,'max_supplementary_span_tokens':64,'supplementary_span_cap':64,'boundary_radius':1,'expansion_depth':1,'new_hyperedge_max_sources':3,'supplementary_slot_cap':4096,'protect_initial':True,'protect_parsed_candidates':True},
 'queue':{'order':['relation','insert','delete','replace','split','merge'],'schedule':'round_robin','batch':6,'attempts_per_round':32,'accepts_per_round':3,'rounds':4,'total_attempts':128,'total_accepts':12,'state_sensitive_dedup':True},
 'edits':{'per_transaction_components':3,'cumulative_components':24,'cumulative_relations':96,'legality_expansion':'invalid_selected_outside_slots_only'},
 'acceptance':{'delta':0.01,'tolerance':1e-9,'component_non_decrease':True,'relation_non_decrease':True},
 'sequential':{'stage1_component_delta':0.01,'stage2_relation_delta':0.01,'keep_stage1_on_stage2_failure':True},
 'constructed_fixture':{'kappa_component':1,'kappa_relation':1,'weight_component':1,'weight_relation':1,'oracle_max_transactions':3,'oracle_component_budget':3,'oracle_relation_budget':3},
 'production_required_unbound':['dataset_revision','split_manifest','tokenizer_revision','generator_checkpoint','span_head_checkpoint','scorer_checkpoint','calibration','optimizer','seeds','hardware','solver_version','context_limit','candidate_preflight_limit','max_scored_objects','calls','tokens','total_solver_seconds','per_call_solver_seconds']}
(W/'reference_config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
for fn in ('render_document.py','fonts.conf'):
    content=(R/'_revision_1008_v4'/fn).read_text().replace('_revision_1008_v4','_revision_1009_v1').replace('report_1008_v4_full','report_1009_v1_full')
    (W/fn).write_text(content)
cp=(R/'_revision_1007_v2/cache_pages.py').read_text().replace("'含非实测占位'", "'构造验证不替代语料实验'")
(W/'cache_pages.py').write_text(cp)
parts=[]
with zipfile.ZipFile(old) as z:
    for name in z.namelist():
        preserve=name.startswith(('word/media/','word/theme/','customXml/')) or name in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'}
        parts.append({'name':name,'sha256':hashlib.sha256(z.read(name)).hexdigest(),'policy':'preserve-only' if preserve else 'editable'})
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    body=etree.fromstring(z.read('word/document.xml'))
    sections=[etree.tostring(x,encoding='unicode') for x in body.xpath('//w:sectPr',namespaces=ns)]
record={'reference':str(old),'sha256':sha(old),'reference_render':str(R/'_revision_1008_v4/render_pass6'),'reference_render_pages':89,'parts':parts,'sections':sections,
 'baseline_hashes':{f:sha(R/f) for f in ['report_1008_v4_full.docx','report_1008_v4_full.md','1008_v4逐项处理记录.md','1009论文完整修改建议与实施方案.md']}}
(W/'template-evidence.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text(f'''# 1009修订稿排版契约

保留模板：{old}，SHA-256 {sha(old)}。原参考渲染89页见template-evidence.json，本版另存，不覆盖v4。使用原A4三节、宋体类中文和Times New Roman、正文12pt及20.5pt行距、三级18/14/12pt标题、原生OMML与可点击目录。封面无页码、前置罗马页码、正文阿拉伯页码。原页边距及部件逐项保存于template-evidence.json。

授权槽位：六章正文及附录中的方法定义、规约、算法、证据表、图4-1和4-2、目录页码和版本标识。既有7图中的5图原样保留，2图从原生绘图代码更新；原媒体部件仍保留。附录E全文字节不变，46条参考文献保留。移除125个无实验来源的P占位，新增明确标识的构造执行结果，不引入伪实测。

样式继承旧模板，表格重排允许分页并重复表头，算法只在语义块边界切分，不缩小字体追求页数。包内theme、numbering、fontTable、webSettings、customXml、原媒体和约定属性保持散列不变；正文、styles、settings、页眉页脚、关系及core属性允许按内容更新。新文件逐页渲染核查，目录缓存随最终PDF重算，Word后续仍保留updateFields=true。

仅使用bundled Python及packaged render_docx.py，LibreOffice限bundled路径。验证程序只覆盖构造对象，不作为正式训练或推理系统验收。最终答复必须明确语料实证未完成。
''')
print(json.dumps({'template_sha':sha(old),'parts':len(parts)},ensure_ascii=False))
