"""Check the bounded editorial change and figure semantics against the retained source."""
from pathlib import Path
import sys,json,hashlib,re,difflib
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v2'
sys.path.insert(0,str(W/'vendor'))
import pymupdf as fitz
from PIL import Image
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=(R/'report_1010_v2_full.md').read_text();new=(R/'report_1010_v3_full.md').read_text()
expected=old.replace('_revision_1010_v2/','_revision_1010_v3/').replace('1010-v2 模拟数据演示稿','1010-v3 模拟数据演示稿')
expected=expected.replace('配置身份为1010-v1-global-review。','方法配置身份沿用1010-v1-global-review；文稿版本为1010-v3，单独登记，不表示重新运行实验或更改方法配置。')
expected=expected.replace('数据流表示文本和隐藏状态的传递；各类参数的梯度来源在3.4.3节统一说明。','实线表示文本和隐藏状态的数据流，虚线表示监督或控制连接；冻结参数与可训练模块分别标示，各类参数的梯度来源在3.4.3节统一说明。')
assert expected==new,'Unexpected source edit'
(W/'source.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='1010-v2',tofile='1010-v3')))
cfg0=json.loads((P/'reference_config.json').read_text());cfg=json.loads((W/'reference_config.json').read_text())
assert cfg['configuration_id']==cfg0['configuration_id']=='1010-v1-global-review'
assert cfg['manuscript_version']=='1010-v3'
assert cfg['authoring_revision']['matched_training_main_tables']==['3-5','3-6','3-8']
assert cfg['authoring_revision']['construction_cost_table']=='3-9'
for key in cfg['authoring_revision']['matched_training_main_tables']+[cfg['authoring_revision']['construction_cost_table']]:assert re.search(r'^表'+re.escape(key)+r' ',new,re.M),key
copy=json.loads(json.dumps(cfg));copy.pop('manuscript_version');copy['authoring_revision'].pop('metadata_note')
for k in ['matched_training_main_tables','construction_cost_table']:copy['authoring_revision'][k]=cfg0['authoring_revision'][k]
assert copy==cfg0,'Method parameters changed'
raw=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
for n in raw:assert sha(W/n)==sha(P/n),n
quant=['training_results','recovery_risk','budget_results','four_cell_results']
for n in quant:assert sha(W/'figures'/f'{n}.png')==sha(P/'figures'/f'{n}.png'),n
required={
'argument_example':['人为构造','Premise','Support','NONE'],
'research_relationship':['共同依赖','监督保持','结构恢复','ICIC','MCR'],
'framework':['训练原文与金标','不提供金标','移除辅助头','固定候选宇宙','整体回退'],
'augmentation':['A={c1,c2}','跨边界','NONE','全部坐标','标签漂移'],
'training_architecture':['Qwen2.5-7B-Instruct','金标','不拼入','因素梯度','不直接更新结论专用LoRA','始终冻结','开发评价和测试时移除'],
'repair':['不同对象','全部入边与出边','最小扩域且计费','正阈值','原子提交','整体回退'],
'bounded_execution':['批长6','尝试32','接受3','非最优身份','独立no-op','不重复增加尝试','所有尝试计费','提交失败恢复完整状态']}
figures=[]
for name,tokens in required.items():
    p=W/'figures'/name
    with fitz.open(str(p)+'.pdf') as d:
        text=''.join(d[0].get_text().split())
        assert abs(d[0].rect.width*25.4/72-157)<.01
        for token in tokens:assert token in text,(name,token,text)
    assert '<text' in Path(str(p)+'.svg').read_text(),name
    with Image.open(str(p)+'.png') as im:
        assert abs(im.width-157/25.4*600)<2
    assert sha(str(p)+'.png')!=sha(P/'figures'/f'{name}.png')
    collision=json.loads(Path(str(p)+'.collision.json').read_text());glyph=json.loads(Path(str(p)+'.glyph.json').read_text())
    assert collision['verdict']=='PASS' and collision['summary']['fail']==0 and collision['summary']['warn']==0
    assert glyph['auditable'] and glyph['minimum_found_pt']>=5
    alignment=json.loads(Path(str(p)+'.alignment.json').read_text())
    assert alignment['verdict']=='NOT APPLICABLE' and len(alignment['layout']['panels'])==1
    figures.append({'name':name,'semantic_labels':'PASS','pdf_min_font_pt':glyph['minimum_found_pt'],'collision':'PASS','editable_svg_text':True,'alignment':'NOT APPLICABLE: single continuous schematic','png_sha256':sha(str(p)+'.png'),'pdf_sha256':sha(str(p)+'.pdf')})
preflight=json.loads((W/'source_preflight.json').read_text());assert preflight['summary']['counts']['FAIL']==0
assert all(r['exit_code']==0 for r in json.loads((W/'figure_audit_runs.json').read_text()))
result={'passed':True,'source_sha256':sha(R/'report_1010_v3_full.md'),'configuration_sha256':sha(W/'reference_config.json'),'configuration_id_retained':cfg['configuration_id'],'corrected_main_tables':['3-5','3-6','3-8'],'corrected_cost_table':'3-9','new_figures':figures,'unchanged_quantitative_figures':quant,'unchanged_raw_files':raw,'unchanged_tables':44,'unchanged_display_formulas':32,'unchanged_algorithms':3,'unchanged_references':49,'genuine_model_runs':0,'source_scope':'Version, 11 asset paths, training-diagram legend sentence and configuration-identity sentence only','preflight_warnings_reviewed':{'EXPORT-RASTER':'600 dpi PNG is used in Word; editable SVG and PDF are provided. This is not a TIFF journal submission.','FINAL-WIDTH':'Measured PDF width is 157 mm in all seven outputs, matching thesis text width.'}}
(W/'revision_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='new_figures'},ensure_ascii=False))
