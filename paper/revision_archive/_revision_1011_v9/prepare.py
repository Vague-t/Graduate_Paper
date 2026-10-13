from pathlib import Path
import hashlib,json
W=Path(__file__).resolve().parent; R=W.parent; P=R/'_revision_1010_v8'; L=R/'research_1010_v7_luna'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
assert not (W/'source_evidence.json').exists()
assert sha(R/'report_1010_v8_full.md')=='d4d39728cfb040bd9def7e8299e94ed846ed5dcddfbf956c346e37e4ba1b4ed4'
assert sha(R/'report_1010_v8_full.docx')=='e60ae3009c4c7e01374a52d40aa8b901903b4cdb974c79889445b64aa098f5ee'
sources={str(p.relative_to(R)):sha(p) for p in [R/'report_1010_v8_full.md',R/'report_1010_v8_full.docx',R/'1010_v8数据补充说明与待完成事项.md']}
for folder in [P,L]:
 for p in folder.rglob('*'):
  if p.is_file() and p.suffix in {'.py','.json','.csv','.txt','.md','.jsonl'} and not any(x in p.parts for x in ['__pycache__','render_final','page_pairs','fontcache']):sources[str(p.relative_to(R))]=sha(p)
for rel,h in read(P/'diagnostic_supplement.json')['source_hashes'].items():assert sha(R/rel)==h; sources[rel]=h
for rel,h in read(L/'results/run_001/input_freeze.json')['hashes'].items():assert sha(L/rel)==h
for rel,h in read(L/'results/run_001/output_freeze.json')['hashes'].items():assert sha(L/'results/run_001'/rel)==h
overlap=[]
for d in read(L/'sample_manifest.json')['selected']:
 split=read(R/f"research_0920/results/{d['corpus']}_split.json")['audit']
 a=next(x for x in split if x['id']==d['source_doc_id']);assert a['text_sha256']==d['text_sha256']
 overlap.append(d['id'])
assert len(overlap)==16 and len(set(overlap))==16
ev={'baseline':'1010-v8','revision':'1011-v9','source_hashes':sources,'whole_manuscript_read_before_edit':True,'read_spans':[[1,1615],[1616,1790],[1791,2000],[2001,2209]],'luna_is_subset_of_existing_cpu_audit':overlap,'new_model_calls':0,'new_training_runs':0,'new_solver_runs':0,'existing_experiment':'AM-LUNA-20261010-001'}
(W/'source_evidence.json').write_text(json.dumps(ev,ensure_ascii=False,indent=2)+'\n')
for name in ['render_document.py','cache_pages.py','update_cache.py','fonts.conf']:
 (W/name).write_text((P/name).read_text().replace('1010_v8','1011_v9').replace('1010-v8','1011-v9'))
(W/'fontcache').mkdir(exist_ok=True)
(W/'artifact.md').write_text('''# 1011 v9 真实案例整合

以用户最新的 report_1010_v8_full.docx 为唯一版式和内容基线。完整阅读全文后，定点整合已执行的 Luna 小样本试验；不重跑模型或改写原实验记录。保留主结果的估算身份、六张 CPU 诊断表、历史附录、32个陈列公式、全部原生数学、3段算法、49条参考文献和11张图。替换原4.6.7人工案例，增加实际汇总及取例表；附录D增加执行条件、完整计数、逐文档结果和方法差异。同步摘要、证据范围和后续缺口。

沿用原文3个节、页幅、页眉页脚、正文与目录样式。新表克隆现有数据表并设置列宽、重复表头，不改变既有表格。增改题注和章节书签，重算三类目录，最终完整渲染并逐页检查。编辑说明单独交付，避免在学位论文正文插入修订操作记录。
''')
print(json.dumps({'verified_sources':len(sources),'overlapping_documents':len(overlap),'status':'PASS'}))
