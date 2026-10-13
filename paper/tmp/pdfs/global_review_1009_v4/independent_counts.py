"""Read-only recomputation of manuscript scenario counts for this review."""
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
import csv
import hashlib
import json
import math

ROOT = Path('/Users/channtang/Downloads/paper')
SRC = ROOT / '_revision_1009_v4'
OUT = Path(__file__).resolve().parent
counts = defaultdict(lambda: [0, 0, 0])
rows = 0
with (SRC / 'document_counts.csv').open() as stream:
    for row in csv.DictReader(stream):
        assert row['evidence_type'] == 'SIMULATED_COUNTS'
        key = row['dataset'], row['object'], row['method'], row['seed']
        for i, name in enumerate(('tp', 'fp', 'fn')):
            counts[key][i] += int(row[name])
        rows += 1
results = defaultdict(list)
for (dataset, obj, method, seed), (tp, fp, fn) in counts.items():
    results[dataset, obj, method].append(200 * tp / (2 * tp + fp + fn))
source = (ROOT / 'report_1009_v4_full.md').read_text()
verified = {}
for key, values in results.items():
    rendered = f'{mean(values):.2f}±{stdev(values):.2f}'
    assert rendered in source, (key, rendered)
    verified['/'.join(key)] = rendered
derived = json.loads((SRC / 'review_derived_tables.json').read_text())
for row in derived['net_error_rows']:
    for label, after, before in [('training', 't1_i0', 't0_i0'),
                                 ('repair_t0', 't0_i1', 't0_i0'),
                                 ('repair_t1', 't1_i1', 't1_i0')]:
        delta = [sum(counts[row['dataset'], row['object'], after, s][i]
                     - counts[row['dataset'], row['object'], before, s][i]
                     for s in ('17', '29', '43')) for i in range(3)]
        assert delta == [row[label][name] for name in ('tp', 'fp', 'fn')]
report = {
    'scope': 'ARITHMETIC_CHECK_OF_EXPLICITLY_SIMULATED_COUNTS_ONLY',
    'rows': rows,
    'recomputed_mean_sd_cells_present_in_manuscript': len(verified),
    'net_error_rows_checked': len(derived['net_error_rows']),
    'brj_time_saving_relative_to_equal_global_percent': {
        'AAEC': (33.4 - 32) / 33.4 * 100,
        'CDCP': (47.4 - 45.16) / 47.4 * 100,
    },
    'illustrative_three_source_one_target_slots_for_64_compatible_untyped_spans':
        math.comb(64, 3) * 61,
    'verified_values': verified,
    'manuscript_sha256': hashlib.sha256((ROOT / 'report_1009_v4_full.md').read_bytes()).hexdigest(),
    'docx_sha256': hashlib.sha256((ROOT / 'report_1009_v4_full.docx').read_bytes()).hexdigest(),
    'real_model_or_solver_runs_performed': 0,
}
(OUT / 'independent_counts.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'verified_values'}, ensure_ascii=False, indent=2))
