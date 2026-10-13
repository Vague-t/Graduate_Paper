"""Independent recomputation of v5 counts and unchanged method content."""
from pathlib import Path
from collections import defaultdict
import csv
import json
import re
import statistics
from hashlib import sha256

ROOT = Path('/Users/channtang/Downloads/paper')
W = ROOT/'_revision_1010_v5'
PREV = ROOT/'_revision_1010_v4'
OUT = Path(__file__).resolve().parent
with (W/'document_counts.csv').open() as f:
    rows = list(csv.DictReader(f))
sums = defaultdict(lambda: [0,0,0])
counts = {}
for row in rows:
    key = row['dataset'], row['method'], row['object'], int(row['seed'])
    values = [int(row[k]) for k in ['tp','fp','fn']]
    for i, value in enumerate(values): sums[key][i] += value
    counts[(row['dataset'],row['method'],row['object'],int(row['seed']),row['document'])] = values
groups = defaultdict(list)
for (ds,method,obj,seed),(tp,fp,fn) in sums.items():
    groups[ds,method,obj].append(200*tp/(2*tp+fp+fn))
metrics = {k:dict(mean=statistics.mean(v),sd=statistics.stdev(v)) for k,v in groups.items()}
expected = json.loads((W/'scenario_results.json').read_text())['metrics']
for (ds,method,obj), value in metrics.items():
    assert abs(value['mean']-expected[ds][method][obj]['mean']) < 1e-10
    expected_sd = expected[ds][method][obj].get('std', expected[ds][method][obj].get('sd'))
    assert expected_sd is not None, expected[ds][method][obj]
    assert abs(value['sd']-expected_sd) < 1e-10
ds_deltas = {}
for ds in ['AAEC','CDCP']:
    mean = lambda m: metrics[ds,m,'relation']['mean']
    ds_deltas[ds] = dict(brj_minus_relation_only=mean('t1_i1')-mean('relation_only'),
                        brj_minus_single_object=mean('t1_i1')-mean('single_object'))

supp = json.loads((W/'supplement_manifest.json').read_text())
assert sha256((W/'generate_supplement.py').read_bytes()).hexdigest() == supp['generator_sha256']
for name,digest in supp['files'].items():
    assert sha256((W/name).read_bytes()).hexdigest() == digest
    assert (W/name).read_bytes() == (PREV/name).read_bytes()
members = json.loads((W/'object_memberships.json').read_text())
bounds = defaultdict(lambda: defaultdict(int))
for row in members:
    gold = set(row['gold'])
    predictions = {method:set(objects) for method,objects in row['predictions'].items()}
    for method,pred in predictions.items():
        assert [len(pred&gold),len(pred-gold),len(gold-pred)] == counts[row['dataset'],method,'relation',row['seed'],row['document']]
    old = predictions['t0_i0']&gold
    train = (predictions['t1_i0']&gold)-old
    repair = (predictions['t0_i1']&gold)-old
    outside = gold-old
    minimum = max(0,len(train)+len(repair)-len(outside))
    maximum = min(len(train),len(repair))
    counter = bounds[row['dataset']]
    counter['records'] += 1
    counter['assigned'] += len(train&repair)
    counter['minimum'] += minimum
    counter['maximum'] += maximum
    for desired in [minimum,maximum]:
        new_hits = set(sorted(train)[:desired]) | set(sorted(outside-train)[:len(repair)-desired])
        assert len(new_hits)==len(repair) and len(new_hits&train)==desired
        fixed = (predictions['t0_i1']&old) | (predictions['t0_i1']-gold)
        changed = fixed | new_hits
        assert [len(changed&gold),len(changed-gold),len(gold-changed)] == counts[row['dataset'],'t0_i1','relation',row['seed'],row['document']]

old_md = (ROOT/'report_1010_v4_full.md').read_text()
new_md = (ROOT/'report_1010_v5_full.md').read_text()
equations = re.findall(r'\$\$(.*?)\$\$',new_md,re.S)
assert equations == re.findall(r'\$\$(.*?)\$\$',old_md,re.S)
algorithms = re.findall(r'```(?:algorithm|plaintext)\n(.*?)```',new_md,re.S)
assert algorithms == re.findall(r'```(?:algorithm|plaintext)\n(.*?)```',old_md,re.S)
figures = re.findall(r'^!\[[^]]*\]\(([^)]+)\)',new_md,re.M)
for path in figures:
    assert (ROOT/path).read_bytes() == (PREV/'figures'/Path(path).name).read_bytes()
chapter_chars = lambda md: len(md[md.index('## 第一章'):md.index('## 参考文献')])
result = dict(count_rows=len(rows),recomputed_metric_groups=len(metrics),
              direct_relation_deltas=ds_deltas,overlap_bounds=dict(bounds),
              supplement_hashes_and_v4_identity_verified=True,
              unchanged_display_equations=len(equations),unchanged_algorithms=len(algorithms),
              unchanged_used_figures=len(figures),chapter_characters=dict(v4=chapter_chars(old_md),v5=chapter_chars(new_md)),
              scope='Arithmetic, file identity, and abstract-set non-identifiability only; no empirical validation or complete graph feasibility.')
(OUT/'independent_data_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
