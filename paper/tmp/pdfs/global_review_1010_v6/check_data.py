"""Independently check v6 arithmetic and preservation, not empirical performance."""
from pathlib import Path
from collections import defaultdict
from hashlib import sha256
import csv
import json
import re
import statistics

ROOT = Path('/Users/channtang/Downloads/paper')
W = ROOT/'_revision_1010_v6'
PREV = ROOT/'_revision_1010_v5'
OUT = Path(__file__).resolve().parent
with (W/'document_counts.csv').open() as stream:
    rows = list(csv.DictReader(stream))
sums = defaultdict(lambda: [0, 0, 0])
counts = {}
for row in rows:
    key = row['dataset'], row['method'], row['object'], int(row['seed'])
    values = [int(row[k]) for k in ['tp', 'fp', 'fn']]
    assert all(v >= 0 for v in values)
    for i, value in enumerate(values):
        sums[key][i] += value
    full_key = (*key, row['document'])
    assert full_key not in counts
    counts[full_key] = values
groups = defaultdict(list)
for (ds, method, obj, seed), (tp, fp, fn) in sums.items():
    groups[ds, method, obj].append(200*tp/(2*tp+fp+fn))
metrics = {k:dict(mean=statistics.mean(v), sd=statistics.stdev(v)) for k,v in groups.items()}
expected = json.loads((W/'scenario_results.json').read_text())['metrics']
for (ds, method, obj), value in metrics.items():
    target = expected[ds][method][obj]
    assert abs(value['mean']-target['mean']) < 1e-10
    assert abs(value['sd']-target.get('std', target.get('sd'))) < 1e-10
deltas = {}
for ds in ['AAEC', 'CDCP']:
    mean = lambda method: metrics[ds, method, 'relation']['mean']
    deltas[ds] = dict(data_construction=mean('full_data_i0')-mean('qos_i0'),
                     paired_learning=mean('t1_i0')-mean('head_i0'),
                     brj_minus_relation_only=mean('t1_i1')-mean('relation_only'),
                     brj_minus_single_object=mean('t1_i1')-mean('single_object'),
                     brj_minus_global=mean('t1_i1')-mean('global_equal'))
supplement = json.loads((W/'supplement_manifest.json').read_text())
assert sha256((W/'generate_supplement.py').read_bytes()).hexdigest() == supplement['generator_sha256']
for name, digest in supplement['files'].items():
    assert sha256((W/name).read_bytes()).hexdigest() == digest
    assert (W/name).read_bytes() == (PREV/name).read_bytes()
members = json.loads((W/'object_memberships.json').read_text())
bounds = defaultdict(lambda: defaultdict(int))
for row in members:
    gold = set(row['gold'])
    predictions = {method:set(objects) for method,objects in row['predictions'].items()}
    for method, pred in predictions.items():
        assert [len(pred&gold),len(pred-gold),len(gold-pred)] == counts[row['dataset'],method,'relation',row['seed'],row['document']]
    old = predictions['t0_i0'] & gold
    train = (predictions['t1_i0'] & gold)-old
    repair = (predictions['t0_i1'] & gold)-old
    outside = gold-old
    low, high = max(0,len(train)+len(repair)-len(outside)), min(len(train),len(repair))
    counter = bounds[row['dataset']]
    counter['records'] += 1
    counter['assigned'] += len(train&repair)
    counter['minimum'] += low
    counter['maximum'] += high
    for overlap in [low, high]:
        new_hits = set(sorted(train)[:overlap]) | set(sorted(outside-train)[:len(repair)-overlap])
        assert len(new_hits) == len(repair) and len(new_hits&train) == overlap
        changed = (predictions['t0_i1']&old) | (predictions['t0_i1']-gold) | new_hits
        assert [len(changed&gold),len(changed-gold),len(gold-changed)] == counts[row['dataset'],'t0_i1','relation',row['seed'],row['document']]
old_md = (ROOT/'report_1010_v5_full.md').read_text()
new_md = (ROOT/'report_1010_v6_full.md').read_text()
equations = re.findall(r'\$\$(.*?)\$\$', new_md, re.S)
assert equations == re.findall(r'\$\$(.*?)\$\$', old_md, re.S)
algorithms = re.findall(r'```(?:algorithm|plaintext)\n(.*?)```', new_md, re.S)
old_algorithms = re.findall(r'```(?:algorithm|plaintext)\n(.*?)```', old_md, re.S)
assert algorithms == [a.replace('按源文档等权取训练批次', '按源文档等频取训练批次') for a in old_algorithms]
figures = re.findall(r'^!\[[^]]*\]\(([^)]+)\)', new_md, re.M)
for path in figures:
    assert (ROOT/path).read_bytes() == (PREV/'figures'/Path(path).name).read_bytes()
section = lambda md, start, end: md[md.index(start):md.index(end)]
assert section(old_md, '## 参考文献', '## 附录A') == section(new_md, '## 参考文献', '## 附录A')
assert section(old_md, '## 附录E', '## 附录F') == section(new_md, '## 附录E', '## 附录F')
numbered_tables = lambda md: [line for line in md.splitlines() if re.match(r'^表[A-H0-9]+-\d+ ', line)]
result = dict(count_rows=len(rows), recomputed_metric_groups=len(metrics), direct_relation_deltas=deltas,
              overlap_bounds=dict(bounds), supplement_hashes_and_v5_identity_verified=True,
              unchanged_display_equations=len(equations), algorithms_with_only_sampling_wording_change=len(algorithms),
              unchanged_used_figures=len(figures), numbered_tables=len(numbered_tables(new_md)),
              references_and_historical_appendix_unchanged=True,
              chapter_characters={version:len(section(md,'## 第一章','## 参考文献')) for version,md in [('v5',old_md),('v6',new_md)]},
              scope='Count arithmetic, file identity, and abstract-set non-identifiability; no empirical run, complete graph feasibility, or new bootstrap CI recomputation.')
(OUT/'independent_data_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
