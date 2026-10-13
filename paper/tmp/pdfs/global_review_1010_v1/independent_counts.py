"""Review-only recomputation; writes no manuscript or source experiment files."""
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
import csv
import json

ROOT = Path('/Users/channtang/Downloads/paper')
SRC = ROOT / '_revision_1010_v1'
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
source = (ROOT / 'report_1010_v1_full.md').read_text()
verified = {}
for key, values in results.items():
    rendered = f'{mean(values):.2f}±{stdev(values):.2f}'
    assert rendered in source, (key, rendered)
    verified['/'.join(key)] = rendered
report = {
    'scope': 'SIMULATED_COUNTS_ARITHMETIC_ONLY',
    'rows': rows,
    'recomputed_mean_sd_cells_present_in_manuscript': len(verified),
    'brj_time_saving_relative_to_equal_global_percent': {
        'AAEC': (33.4 - 32) / 33.4 * 100,
        'CDCP': (47.4 - 45.16) / 47.4 * 100,
    },
    'verified_values': verified,
    'real_model_or_solver_runs_performed': 0,
}
(OUT / 'independent_counts.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'verified_values'}, ensure_ascii=False))
