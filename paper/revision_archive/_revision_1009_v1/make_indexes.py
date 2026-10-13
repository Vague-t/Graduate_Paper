"""Evidence index and honest delivery notes for the v1 revision."""
from pathlib import Path
import json,hashlib,difflib
W=Path(__file__).resolve().parent;R=W.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
results=json.loads((W/'mechanism_results.json').read_text())
assert results['code_sha256']==sha(W/'validate_mechanisms.py')
index={'evidence_type':results['evidence_type'],'formal_corpus_experiments':'not_run','artifact_version':'1009-v1','results_file':'mechanism_results.json','code':'validate_mechanisms.py','checks_passed':results['passed'],
 'tables':{'3-3':['center_determinism','empty_and_fallback','long_gold_hyperedge','region_budget_no_truncation','coordinate_transport','four_factor_classes','source_weights'],'4-3':['sequential_vs_joint','stage2_failure_keeps_intermediate'],'4-4':['oracle_set_inclusions','oracle_exact_values','nonincident_new_slot'],'4-6':['sequential_vs_joint','cumulative_vs_net'],'5-1':'not_run','D.5':['micro_oracle_counterexample']},
 'unimplemented_or_unverified':['full_neural_training','tokenizer_offset_roundtrip','gradient_paths','trained_span_head','production_candidate_enumeration','production_transaction_engine','ILP_solver_integration','semantic_blind_audit','OOF_calibration','real_multiseed_predictions','end_to_end_costs'],
 'files':{name:sha(W/name) for name in ['validate_mechanisms.py','mechanism_results.json','reference_config.json']}}
(W/'results_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
diff=''.join(difflib.unified_diff((R/'report_1008_v4_full.md').read_text().splitlines(True),(R/'report_1009_v1_full.md').read_text().splitlines(True),fromfile='1008-v4',tofile='1009-v1'))
(W/'source.diff').write_text(diff)
(W/'文献核验记录.md').write_text('''# 本轮关键来源核验

核验日期：2026年10月9日。以下仅列本轮实际回查的来源，不代表全稿46条文献已重新全文审计。未向外部模型上传未发表论文；检索仅使用题名及公共来源。

|来源|本轮阅读范围|用于校准的判断|
|:---|:---|:---|
|[QOS原文](https://aclanthology.org/2025.emnlp-main.1351.pdf)|方法4.1，PDF第3页|输入分离上下文和组件，均可改写；关系未显式给生成模型。正文把“沿用局部改写”改为“沿用槽位化改写”。不据此断言其没有所有形式的关系检查|
|[Re-Cent](https://aclanthology.org/2025.coling-main.491/)|官方摘要；检索返回的原文方法片段|关系标签引导跨度对抽取及相关性修正已是近邻工作，不声称首次把关系用于对象修正|
|[F-measure决策](https://jmlr.org/papers/v15/waegeman14a.html)|JMLR官方摘要与书目|普通代理风险和F1优化不等价，保留本稿有限性质的限制；本文micro计数反例为独立构造推导|
|[概率校准](https://proceedings.mlr.press/v70/guo17a.html)|PMLR官方摘要与书目|校准关注置信度与正确率对应，不推出搜索接受动作的无害性|

未新增无法核实的引用，不把继承的文献阅读标记记作本轮已全文阅读。所有正文引用仍使用原参考文献编号。
''')
print(json.dumps({'checks':results['passed'],'indexed_tables':len(index['tables'])},ensure_ascii=False))
