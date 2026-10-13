"""New-version only setup; v1 is the retained, immutable template."""
from pathlib import Path
import hashlib,json,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1009_v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ['build_docx.py','render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','table_splits.json','final_audit.py']:
    text=(P/name).read_text().replace('1009_v1','1009_v2').replace('1009-v1','1009-v2')
    if name=='build_docx.py':text=text.replace("template=R/'report_1008_v4_full.docx'","template=R/'report_1009_v1_full.docx'").replace("'v5_'","'v6_'")
    (W/name).write_text(text)
# Unmodified reference program copied before re-execution. It writes only here.
(W/'validate_mechanisms.py').write_bytes((P/'validate_mechanisms.py').read_bytes())
cfg=json.loads((P/'reference_config.json').read_text())
cfg['configuration_id']='1009-v2-selfmatch-conditional-reverse-outer-proposal'
cfg['matching'].update(allow_self_match=True,length_difference_denominator='reference_region_chars',valid_reference_unmatched=False,self_match_rate_denominator='valid_reference_documents',report_heterocenter_subset=True)
cfg['candidates']['reverse_policy']='binary_both_frozen_slots_and_current_legal_endpoints'
cfg['queue'].update(attempt_unit='outer_proposal',accept_unit='outer_proposal_with_at_least_one_committed_stage',cursor_scope='state_across_rounds',rejected_cache_scope='state_across_rounds')
cfg['sequential'].update(companion_after_accept_cap=True,max_stage_commits_per_outer=2,batch_rank='weighted_first_stage_gain_then_actual_edits_then_key',stage2_only_for_committed_winner=True,resource_and_edit_cost_refund=False)
cfg['solver_tie_policy']={'optimal':'max_utility_then_min_actual_edits_then_lexicographic_state_key','implementation':'successive_objectives_not_arbitrary_epsilon','timeout':'revalidate_incumbent_record_tie_status_no_unique_optimum_claim'}
(W/'reference_config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
old=R/'report_1009_v1_full.docx'
parts=[]
with zipfile.ZipFile(old) as z:
    for name in z.namelist():
        preserve=name.startswith(('word/media/','word/theme/','customXml/')) or name in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'}
        parts.append({'name':name,'sha256':hashlib.sha256(z.read(name)).hexdigest(),'policy':'preserve-only' if preserve else 'editable'})
    body=etree.fromstring(z.read('word/document.xml'))
    sections=[etree.tostring(x,encoding='unicode') for x in body.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
baseline=['report_1009_v1_full.docx','report_1009_v1_full.md','1009_v1逐项修改与证据闭环说明.md','1009_v1复审后完整修改建议与实施方案.md','_revision_1009_v1/validate_mechanisms.py','_revision_1009_v1/mechanism_results.json']
record={'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_delivery'),'reference_render_pages':89,'parts':parts,'sections':sections,'baseline_hashes':{f:sha(R/f) for f in baseline}}
(W/'template-evidence.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1009 v2 排版契约

沿用1009-v1 Word作为保留模板，另存v2。A4三节、原页边距、中文字体和Times New Roman、三级标题、正文12pt、原生数学与可点击目录均继承。六章、两项研究、七幅方法图、46条文献和附录E历史存档保留。授权修改剩余接口、测试身份、实验归因与版本标识；不填写无来源的任务成绩。预算图如更新，仍保留模板旧媒体。附录E正文逐字保持，逐项哈希见template-evidence.json。

算法在语义块边界分页，长表有续题和表头，不压缩字体迁就页数。仅使用bundled运行时及LibreOffice。先渲染再逐页检查，缓存目录与最终PDF一致。参考程序验证不等于真实模块验收；缺少的语料运行继续明确列出。
''')
print('prepared v2; immutable v1 reference',sha(old))
