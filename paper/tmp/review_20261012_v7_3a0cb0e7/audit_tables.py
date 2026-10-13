from pathlib import Path
import json
import statistics
from collections import defaultdict

base = Path(__file__).parent
tables = {item['block']: item['rows'] for item in json.loads((base / 'tables.json').read_text())}
groups = defaultdict(list)
row_errors = []
for row in tables[1160][1:]:
    dataset, method, seed, tp, fp, fn, displayed = row
    tp, fp, fn = map(int, (tp, fp, fn))
    score = 200 * tp / (2 * tp + fp + fn)
    if abs(score - float(displayed)) > 0.005001:
        row_errors.append(row)
    groups[(dataset, method)].append(score)
summaries = {f'{dataset}/{method}': {'mean': statistics.mean(values), 'sd': statistics.stdev(values)} for (dataset, method), values in groups.items()}
audit = {
    'scope': 'Arithmetic on manuscript tables only; no model or bootstrap reproduction',
    'h5_rows_checked': len(tables[1160]) - 1,
    'h5_rounding_errors': row_errors,
    'h5_summaries': summaries,
    'four_grid_effects': {},
    'member_decomposition': {},
    'cardinality_rows_checked': 12,
    'cardinality_identity_errors': [],
    'printed_q_transaction_deltas': {'component': 2*(0.978410-0.924523), 'relation': 2*(0.970692-0.009229)},
    'note': 'Printed q values rounded to six decimals, so last-decimal differences from manuscript deltas are not an error.',
}
for dataset in ('AAEC', 'CDCP'):
    means = {method: summaries[f'{dataset}/{method}']['mean'] for method in ('T0I0','T1I0','T0I1','T1I1')}
    audit['four_grid_effects'][dataset] = {'training': means['T1I0']-means['T0I0'], 'inference': means['T1I1']-means['T1I0'], 'total': means['T1I1']-means['T0I0'], 'interaction': means['T1I1']-means['T1I0']-means['T0I1']+means['T0I0']}
for row in tables[814][1:]:
    values = list(map(int, row[1:]))
    audit['member_decomposition'][row[0]] = {'calculated': sum(values[:5])-sum(values[5:7]), 'displayed': values[7]}
for row in tables[1228][1:]:
    tp, fp, fn, pred, gold, diff = map(int, row[3:])
    if not (tp+fp == pred and tp+fn == gold and fp-fn == diff == pred-gold):
        audit['cardinality_identity_errors'].append(row)
(base / 'manuscript_arithmetic_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
print(json.dumps(audit, ensure_ascii=False, indent=2))
