"""Read-only arithmetic/provenance audit. Does not run any experiment or generator."""
from pathlib import Path
import csv
import hashlib
import json

ROOT = Path('/Users/channtang/Downloads/paper')
TASK = ROOT / 'manuscript_review_test_20261011/protocol_identity_audit_20261012_v6'
OUT = TASK / '_agents/counts'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def load(path):
    return json.loads(path.read_text())

def row_key(dataset, method, seed):
    return dataset, method.lower().replace('_', '').replace('/', ''), int(seed)

blocks = load(TASK / '_source/blocks.json')
table = next(b for b in blocks if b['id'] == 'B1153')
rows = []
for dataset, method, seed, tp, fp, fn, reported in table['rows'][1:]:
    tp, fp, fn = map(int, (tp, fp, fn))
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * tp / (2 * tp + fp + fn)
    rows.append(dict(dataset=dataset, method=method, seed=int(seed), tp=tp,
                     fp=fp, fn=fn, Npred=tp + fp, Ngold=tp + fn,
                     precision_percent=precision * 100, recall_percent=recall * 100,
                     f1_percent=f1 * 100, reported_f1=float(reported),
                     equal_counts=(fp == fn), f1_rounding_pass=(round(f1 * 100, 2) == float(reported))))
i0 = [r for r in rows if r['method'].endswith('I0')]
assert len(i0) == 12 and all(r['equal_counts'] for r in i0)
assert all(r['f1_rounding_pass'] for r in rows)
current = {row_key(r['dataset'], r['method'], r['seed']): [r['tp'], r['fp'], r['fn']] for r in i0}

# Confirm that counts already appeared in the uploaded manuscript, rather than
# having been introduced by the v5 chapter edit.
original_path = ROOT / 'manuscript_review_test_20261011/_source_audit/source_blocks.json'
original = load(original_path)
original_table = next(b for b in original if b.get('rows', [[]])[0] == table['rows'][0]
                      and len(b.get('rows', [])) == len(table['rows']))

result_paths = sorted(ROOT.glob('_revision_*/scenario_results.json'))
result_paths += [ROOT / '_revision_1011_v12/simulation/results.json',
                 ROOT / 'research_1011_v13/simulation/results.json']
history = []
for p in result_paths:
    data = load(p)
    metrics = data['metrics']
    metrics = metrics.get('strict_native', metrics)
    seeds = data['seeds']
    comparisons = []
    for ds in ['AAEC', 'CDCP']:
        for method in ['t0_i0', 't1_i0']:
            for seed, counts in zip(seeds, metrics[ds][method]['relation']['counts']):
                key = row_key(ds, method, seed)
                comparisons.append(dict(dataset=ds, method=method, seed=seed,
                    historical_counts=counts, current_counts=current[key],
                    exact_match=counts == current[key],
                    Npred=counts[0] + counts[1], Ngold=counts[0] + counts[2]))
    manifest_path = p.parent / ('manifest.json' if p.name == 'results.json' else 'scenario_manifest.json')
    manifest = load(manifest_path)
    generator = p.parent / 'generate_scenario.py'
    if p.parent.name == 'simulation':
        generator = p.parent.parent / ('generate_graph_scenario.py' if 'research_1011_v13' in str(p) else 'generate_scenario.py')
    manifest_checks = []
    for f in [p, p.parent / 'document_counts.csv']:
        actual = sha(f)
        expected = manifest.get('files', {}).get(f.name)
        manifest_checks.append(dict(path=str(f.relative_to(ROOT)), sha256=actual,
                                   recorded_sha256=expected, matches_manifest=actual == expected))
    actual = sha(generator)
    expected = manifest.get('generator_sha256')
    manifest_checks.append(dict(path=str(generator.relative_to(ROOT)), sha256=actual,
                               recorded_sha256=expected, matches_manifest=actual == expected))
    # Historical CSV must match its own metrics. This does not connect it to v5.
    sums = {}
    with (p.parent / 'document_counts.csv').open() as f:
        for r in csv.DictReader(f):
            if r['method'] not in ['t0_i0', 't1_i0'] or r['object'] != 'relation':
                continue
            if r.get('protocol') and r['protocol'] not in ['strict_native', 'strict_native_graph_scenario']:
                continue
            key = row_key(r['dataset'], r['method'], r['seed'])
            v = sums.setdefault(key, [0, 0, 0])
            for i, k in enumerate(['tp', 'fp', 'fn']):
                v[i] += int(r[k])
    csv_matches_own_metrics = all(sums[row_key(r['dataset'], r['method'], r['seed'])] == r['historical_counts'] for r in comparisons)
    history.append(dict(path=str(p.relative_to(ROOT)), evidence_type=data['evidence_type'],
                        match_rows=sum(r['exact_match'] for r in comparisons), expected_rows=12,
                        comparisons=comparisons, csv_matches_own_metrics=csv_matches_own_metrics,
                        manifest_checks=manifest_checks))

report = dict(
    audit_type='READ_ONLY_INTEGER_AND_PROVENANCE_AUDIT_NOT_A_MODEL_EXPERIMENT',
    source_manifest=load(TASK / '_source/manifest.json'),
    source_blocks_sha256=sha(TASK / '_source/blocks.json'),
    table_block_id='B1153',
    all_24_rows=rows, i0_12_rows=i0,
    original_source_table_unchanged=(original_table['rows'] == table['rows']),
    original_source_blocks_sha256=sha(original_path),
    current_table_canonical_sha256=hashlib.sha256(json.dumps(table['rows'], ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
    historical_outputs=history,
    conclusions=dict(
        i0_rows_with_equal_fp_fn=sum(r['equal_counts'] for r in i0),
        fixed_dataset_totals={'AAEC': 809, 'CDCP': 252},
        historical_versions_compared=len(history),
        historical_matching_versions=sum(h['match_rows'] == 12 for h in history),
        current_generator_bound=False,
        per_document_equal_counts_proven=False,
        one_for_one_replacement_proven=False,
        gold_informed_v13_generator_confirmed=True,
        real_target_model_leakage_proven=False,
        real_target_model_no_leakage_proven=False,
        arithmetic_validity_implies_empirical_validity=False))
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'i0_count_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report['conclusions'], ensure_ascii=False, indent=2))
print('original table unchanged:', report['original_source_table_unchanged'])
print('historical CSV-to-own-metrics pass:', all(x['csv_matches_own_metrics'] for x in history))
print('historical manifest failures:', [(x['path'], y['path']) for x in history for y in x['manifest_checks'] if not y['matches_manifest']])
