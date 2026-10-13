"""Independent read-only checks; outputs only to this review directory."""
from pathlib import Path
from hashlib import sha256
from collections import defaultdict
import csv
import json
import statistics

ROOT = Path('/Users/channtang/Downloads/paper')
W = ROOT/'_revision_1010_v4'
OUT = Path(__file__).resolve().parent
manifest = json.loads((W/'supplement_manifest.json').read_text())
assert sha256((W/'generate_supplement.py').read_bytes()).hexdigest() == manifest['generator_sha256']
for name, digest in manifest['files'].items():
    assert sha256((W/name).read_bytes()).hexdigest() == digest
with (W/'document_counts.csv').open() as f:
    old = {(r['dataset'], int(r['seed']), r['method'], r['object'], r['document']):
           [int(r[k]) for k in ['tp', 'fp', 'fn']] for r in csv.DictReader(f)}
objects = json.loads((W/'object_memberships.json').read_text())
bounds = defaultdict(lambda: defaultdict(int))
for row in objects:
    gold = set(row['gold'])
    p = {m:set(v) for m,v in row['predictions'].items()}
    for method, pred in p.items():
        actual = [len(pred & gold), len(pred-gold), len(gold-pred)]
        assert actual == old[row['dataset'], row['seed'], method, 'relation', row['document']]
    baseline = p['t0_i0'] & gold
    trained = (p['t1_i0'] & gold)-baseline
    repaired = (p['t0_i1'] & gold)-baseline
    outside = gold-baseline
    b = bounds[row['dataset']]
    b['observed_assigned_overlap'] += len(trained & repaired)
    b['minimum_overlap_same_marginals'] += max(0, len(trained)+len(repaired)-len(outside))
    b['maximum_overlap_same_marginals'] += min(len(trained),len(repaired))
    b['document_seed_records'] += 1
budget = []
with (W/'budget_outcomes.csv').open() as f:
    rows = list(csv.DictReader(f))
for ds in ['AAEC','CDCP']:
    for mult in [.5,1,2]:
        for method in ['local','global']:
            r = [x for x in rows if x['dataset']==ds and x['object']=='relation'
                 and float(x['budget_multiplier'])==mult and x['method']==method]
            values=[]
            for seed in [17,29,43]:
                sums=[sum(int(x[k]) for x in r if int(x['seed'])==seed) for k in ['tp','fp','fn']]
                tp,fp,fn=sums
                values.append(200*tp/(2*tp+fp+fn))
            budget.append(dict(dataset=ds,multiplier=mult,method=method,
                               mean_f1=statistics.mean(values),sd_f1=statistics.stdev(values)))
result = dict(supplement_hashes_verified=True, all_relation_memberships_match_counts=True,
              overlap_bounds=dict(bounds), budget_recomputed=budget,
              bounds_scope='Reassign only T0I1 newly recovered gold identities outside T0I0. Preserve its cardinality and retained baseline hits; keep other three cells and all FP objects unchanged. Therefore all four-cell metrics and T1-to-T1I1 risk counts are preserved. Not a complete graph feasibility result.')
(OUT/'independent_supplement_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
