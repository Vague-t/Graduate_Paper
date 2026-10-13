"""Reanalyse saved CPU predictions. No fitting, model calls, or solver execution.

The original loader is extracted by AST without importing the training module.
Only official training documents are parsed. Existing artifacts stay read-only.
"""
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import dataclass
import ast
import csv
import hashlib
import io
import json
import re
import zipfile
import numpy as np

W = Path(__file__).resolve().parent
R = W.parent
ROOT = R / 'research_0920'
SRC = ROOT / 'results'
TOKEN = re.compile(r'\w+|[^\w\s]', re.UNICODE)
BOOTSTRAP_SEED = 10108
BOOTSTRAP_REPEATS = 2000

source_files = [ROOT/'run_feasibility.py', ROOT/'预实验协议.md',
                ROOT/'data/aaec_brat.zip', ROOT/'data/aaec_split.csv',
                ROOT/'data/cdcp_acl17.zip'] + sorted(SRC.glob('*'))
source_hashes = {str(p.relative_to(R)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in source_files if p.is_file()}

original = ast.parse((ROOT/'run_feasibility.py').read_text())
names = {'sha', 'Doc', 'document', 'load_data', 'pool', 'count_match', 'f1', 'overlap'}
selected = [n for n in original.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
assert {n.name for n in selected} == names
exec(compile(ast.Module(body=selected, type_ignores=[]), str(ROOT/'run_feasibility.py'), 'exec'), globals())


def load(p):
    return json.loads(p.read_text())


def write_csv(name, rows):
    if not rows:
        return
    with (W/name).open('w', encoding='utf-8-sig', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def component_pairing(initial, gold):
    """Strict hits, equal-span mistypes, then greedy IoU>=0.5 matching.

    These are descriptive alignments only and never replace strict evaluation.
    Unmatched predictions/gold are not asserted to be unique causal errors.
    """
    p, g = set(initial), set(gold)
    strict = p & g
    p -= strict
    g -= strict
    out = Counter(strict_typed=len(strict), same_span_wrong_type=0,
                  boundary_only=0, boundary_and_type=0,
                  unmatched_gold=0, unmatched_prediction=0)
    for a, b in sorted((a, b) for a in p for b in g if a[:2] == b[:2]):
        if a in p and b in g:
            p.remove(a)
            g.remove(b)
            out['same_span_wrong_type'] += 1
    options = []
    for a in p:
        for b in g:
            inter = max(0, min(a[1], b[1])-max(a[0], b[0]))
            union = (a[1]-a[0])+(b[1]-b[0])-inter
            iou = inter/union if union else 0
            if iou >= .5:
                options.append((-iou, a, b))
    for _, a, b in sorted(options):
        if a in p and b in g:
            p.remove(a)
            g.remove(b)
            out['boundary_only' if a[2] == b[2] else 'boundary_and_type'] += 1
    out['unmatched_gold'] = len(g)
    out['unmatched_prediction'] = len(p)
    paired_wrong = sum(out[k] for k in ['same_span_wrong_type', 'boundary_only', 'boundary_and_type'])
    assert out['strict_typed']+paired_wrong+len(g) == len(set(gold))
    assert out['strict_typed']+paired_wrong+len(p) == len(set(initial))
    return out


def group_interval(docs, before, after):
    groups = defaultdict(list)
    for i, d in enumerate(docs):
        groups[sha(d.text.encode())].append(i)
    # The group order is fixed by SHA-256, independent of input iteration order.
    idx = [groups[k] for k in sorted(groups)]
    b = np.array([np.asarray(before)[v].sum(axis=0) for v in idx])
    a = np.array([np.asarray(after)[v].sum(axis=0) for v in idx])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    delta = []
    for _ in range(BOOTSTRAP_REPEATS):
        sample = rng.integers(0, len(idx), len(idx))
        delta.append(100*(f1(a[sample].sum(axis=0))-f1(b[sample].sum(axis=0))))
    return np.quantile(delta, [.025, .975]).tolist(), len(idx)


results = {}
doc_rows, coverage_rows, action_rows, policy_rows, endpoint_rows = [], [], [], [], []
transition_rows = []
checked_edits = 0
run = load(SRC/'run_manifest.json')
assert run['status'] == 'completed' and run['test_data_used'] is False
assert run['script_sha256'] == sha((ROOT/'run_feasibility.py').read_bytes())
assert run['protocol_sha256'] == sha((ROOT/'预实验协议.md').read_bytes())

for ds in ['aaec', 'cdcp']:
    all_docs, provenance = load_data(ds)
    saved_provenance = load(SRC/f'{ds}_data_manifest.json')
    assert provenance == saved_provenance
    by_id = {d.ident:d for d in all_docs}
    splits = load(SRC/f'{ds}_split.json')
    roles = {}
    for role, records in splits.items():
        for record in records:
            d = by_id[record['id']]
            assert sha(d.text.encode()) == record['text_sha256']
            assert d.ident not in roles
            roles[d.ident] = role
    assert set(roles) == set(by_id)
    group_roles = defaultdict(set)
    for d in all_docs:
        group_roles[sha(d.text.encode())].add(roles[d.ident])
    assert all(len(v) == 1 for v in group_roles.values())
    preds = load(SRC/f'{ds}_candidate_predictions.json')
    # JSON transports tuple spans as arrays; restore the original loader types.
    for prediction in preds:
        for field in ['initial', 'base', 'extra']:
            prediction[field] = [tuple(value) for value in prediction[field]]
    pred_by_id = {p['id']:p for p in preds}
    rows = [json.loads(s) for s in (SRC/f'{ds}_audit_edits.jsonl').read_text().splitlines()]
    row_by_id = {row['doc']:row for row in rows}
    assert len(pred_by_id) == len(preds) == len(rows) == len(row_by_id)
    assert set(pred_by_id) == set(row_by_id) == {r['id'] for r in splits['audit']}
    # Preserve the saved edit-row order for exact policy replay.
    docs = [by_id[row['doc']] for row in rows]
    summary = load(SRC/f'{ds}_summary.json')
    comp = Counter()
    endpoints = Counter()
    missing_histogram = Counter()
    missing = missing_in_pool = one_action_missing = 0
    beneficial_nondelete_docs = 0
    before = []
    for row, d in zip(rows, docs):
        p = pred_by_id[d.ident]
        initial = {tuple(x) for x in p['initial']}
        assert initial == {tuple(x) for x in row['initial']}
        gold = set(d.gold)
        assert len(gold) == len(d.gold) and not d.issues
        counts = count_match(initial, gold)
        assert counts == row['base_counts'] and len(gold) == row['gold_n']
        before.append(counts)
        decomposition = component_pairing(initial, gold)
        comp.update(decomposition)
        spans = {c[:2] for c in initial}
        e = Counter()
        for sources, target, label in d.edges:
            typed = all(d.gold[i] in initial for i in (*sources, target))
            span = all(d.gold[i][:2] in spans for i in (*sources, target))
            e['all_typed_endpoints' if typed else 'all_spans_wrong_type' if span else 'missing_endpoint_span'] += 1
        endpoints.update(e)
        doc_rows.append({'dataset':ds, 'document_id':d.ident, 'text_sha256':sha(d.text.encode()),
                         'gold_components':len(gold), 'initial_predictions':len(initial),
                         'tp':counts[0], 'fp':counts[1], 'fn':counts[2],
                         **{k:decomposition[k] for k in ['strict_typed','same_span_wrong_type','boundary_only','boundary_and_type','unmatched_gold','unmatched_prediction']},
                         'native_relations':len(d.edges),
                         **{k:e[k] for k in ['all_typed_endpoints','all_spans_wrong_type','missing_endpoint_span']}})
        u = set(pool(p, 128))
        for c in gold:
            if c[:2] not in spans:
                missing += 1
                if c[:2] in u:
                    missing_in_pool += 1
                    conflicts = sum(overlap(c, old) for old in initial)
                    missing_histogram[conflicts] += 1
                    can_add = any(c in {tuple(x) for x in edit['add']} for edit in row['edits'])
                    assert can_add == (conflicts <= 1)
                    one_action_missing += can_add
        good_nondelete = False
        for edit in row['edits']:
            assert edit['doc'] == d.ident
            removes, adds = {tuple(x) for x in edit['remove']}, {tuple(x) for x in edit['add']}
            assert removes <= initial
            after = (initial-removes)|adds
            actual_counts = count_match(after, gold)
            delta = f1(actual_counts)-f1(counts)
            truth = 'good' if delta > 1e-12 else 'bad' if delta < -1e-12 else 'neutral'
            assert actual_counts == edit['counts']
            assert abs(delta-edit['delta_f1']) < 1e-12 and truth == edit['truth']
            good_nondelete |= truth == 'good' and edit['op'] != 'delete'
            checked_edits += 1
        beneficial_nondelete_docs += good_nondelete

    ctot = np.array(before).sum(axis=0).tolist()
    assert ctot == summary['calibrated_policy']['before_counts']
    for budget in [0, 64, 128, 256, 512]:
        hits = ehits = extra_hit = 0
        sizes = []
        for d in docs:
            p = pred_by_id[d.ident]
            u = set(pool(p, budget))
            base = {tuple(s) for s in p['base']}
            sizes.append(len(u))
            hits += sum(c[:2] in u for c in d.gold)
            extra_hit += sum(c[:2] in u and c[:2] not in base for c in d.gold)
            ehits += sum(all(d.gold[i][:2] in u for i in (*src, dst)) for src, dst, label in d.edges)
        total_gold = sum(len(d.gold) for d in docs)
        total_rel = sum(len(d.edges) for d in docs)
        previous = next(x for x in summary['recoverability'] if x['extra_budget'] == budget)
        assert hits == previous['covered_components'] and ehits == previous['native_relation_endpoint_covered']
        assert extra_hit == previous['recovered_missing']
        assert np.isclose(np.mean(sizes), previous['mean_candidates'])
        assert np.isclose(np.quantile(sizes,.95), previous['p95_candidates'])
        coverage_rows.append({'dataset':ds, 'extra_budget':budget,
                              'gold_components':total_gold, 'covered_spans':hits, 'span_recall_pct':100*hits/total_gold,
                              'native_relations':total_rel, 'all_endpoint_spans_covered':ehits, 'endpoint_span_recall_pct':100*ehits/total_rel,
                              'mean_candidates':float(np.mean(sizes)), 'p95_candidates':float(np.quantile(sizes,.95)),
                              'mean_directed_pair_combinations':float(np.mean([n*(n-1) for n in sizes])),
                              'pair_count_is_combinatorial_not_measured_scoring':True})
    for op in ['insert','delete','retype','respan']:
        edits = [e for row in rows for e in row['edits'] if e['op'] == op]
        labels = Counter(e['truth'] for e in edits)
        old = summary['edit_discrimination'][op]
        assert len(edits) == old['n'] and labels == Counter(old['truth_counts'])
        action_rows.append({'dataset':ds, 'action':op, 'proposals':len(edits),
                            'document_f1_increase':labels['good'], 'document_f1_equal':labels['neutral'], 'document_f1_decrease':labels['bad'],
                            'increase_pct':100*labels['good']/len(edits) if edits else None})

    policies = {}
    for name, key, allow_delete in [('main','calibrated_policy',True),('no_delete_same_threshold','same_threshold_without_deletion',False)]:
        old = summary[key]
        threshold = old['threshold']
        assert threshold == 4.0 and not old['threshold_is_infinite']
        after, chosen = [], []
        totals = Counter()
        for row, d in zip(rows, docs):
            initial, gold = {tuple(x) for x in row['initial']}, set(d.gold)
            options = [e for e in row['edits'] if allow_delete or e['op'] != 'delete']
            best = max(options, key=lambda e:e['score'], default=None)
            final = initial.copy()
            if best is not None and best['score'] > threshold:
                final = (initial-{tuple(x) for x in best['remove']})|{tuple(x) for x in best['add']}
                chosen.append(best)
            counts = count_match(final, gold)
            after.append(counts)
            move = {'correct_added':len((final&gold)-initial), 'correct_lost':len((initial&gold)-final),
                    'false_added':len((final-gold)-initial), 'false_removed':len((initial-gold)-final)}
            totals.update(move)
            transition_rows.append({'dataset':ds, 'policy':name, 'document_id':d.ident, **move,
                                    'before_tp':row['base_counts'][0], 'before_fp':row['base_counts'][1], 'before_fn':row['base_counts'][2],
                                    'after_tp':counts[0], 'after_fp':counts[1], 'after_fn':counts[2]})
        atot = np.asarray(after).sum(axis=0).tolist()
        assert atot == old['after_counts'] and len(chosen) == old['accepted']
        assert chosen == old['selected_edits']
        assert atot[0]-ctot[0] == totals['correct_added']-totals['correct_lost']
        assert atot[1]-ctot[1] == totals['false_added']-totals['false_removed']
        ci, group_count = group_interval(docs, before, after)
        policies[name] = {'accepted':len(chosen), 'actions':dict(Counter(e['op'] for e in chosen)),
                          'document_delta_labels':dict(Counter(e['truth'] for e in chosen)),
                          'before_counts':ctot, 'after_counts':atot, 'before_f1_pct':100*f1(ctot), 'after_f1_pct':100*f1(atot),
                          'delta_f1_pp':100*(f1(atot)-f1(ctot)), 'group_bootstrap95_pp':ci,
                          'text_groups':group_count, 'object_transitions':dict(totals)}
        policy_rows.append({'dataset':ds, 'policy':name, 'threshold':threshold, 'accepted':len(chosen),
                            'tp':atot[0], 'fp':atot[1], 'fn':atot[2], 'f1_pct':100*f1(atot),
                            'delta_f1_pp':100*(f1(atot)-f1(ctot)), 'ci_low_pp':ci[0], 'ci_high_pp':ci[1], **dict(totals)})

    historical = load(SRC/'posthoc_integrity_audit.json')[ds]
    assert missing == historical['initial_missing_spans']
    assert missing_in_pool == historical['missing_covered_in_pool_128']
    assert one_action_missing == historical['missing_single_action_reachable']
    assert dict(sorted(missing_histogram.items())) == {int(k):v for k,v in historical['overlap_conflict_histogram_for_missing_covered'].items()}
    assert beneficial_nondelete_docs == historical['documents_with_beneficial_nondeletion']
    results[ds] = {'audit_documents':len(docs), 'audit_text_groups':len({sha(d.text.encode()) for d in docs}),
                    'gold_components':sum(len(d.gold) for d in docs), 'initial_predictions':sum(len(r['initial']) for r in rows),
                    'component_decomposition':dict(comp), 'initial_counts':ctot,
                    'native_relations':sum(len(d.edges) for d in docs), 'native_multi_source_relations':sum(len(src)>1 for d in docs for src,_,_ in d.edges),
                    'endpoint_partition':dict(endpoints), 'initial_missing_spans':missing, 'missing_covered_pool128':missing_in_pool,
                    'missing_single_action_reachable':one_action_missing, 'covered_missing_conflict_histogram':dict(sorted(missing_histogram.items())),
                    'beneficial_nondeletion_documents':beneficial_nondelete_docs,
                    'all_proposals':sum(len(row['edits']) for row in rows), 'policies':policies}
    endpoint_rows.append({'dataset':ds, 'native_relations':results[ds]['native_relations'],
                          **{k:endpoints[k] for k in ['all_typed_endpoints','all_spans_wrong_type','missing_endpoint_span']}})

for p, expected in source_hashes.items():
    assert sha((R/p).read_bytes()) == expected, p

out = {'evidence_type':'POSTHOC_REANALYSIS_OF_SAVED_CPU_RUN_NOT_TARGET_LLM_EXPERIMENT',
       'original_run':run, 'new_training_runs':0, 'new_solver_runs':0,
       'bootstrap':{'seed':BOOTSTRAP_SEED,'repeats':BOOTSTRAP_REPEATS,'unit':'exact_text_sha256_group','ci':'percentile 95%; paired counts aggregated before micro-F1', 'interpretation':'post-hoc exploratory interval conditional on one saved model run; not multiple-seed training uncertainty'},
       'component_pairing':{'order':['strict_typed','same_span_wrong_type','greedy_iou_at_least_0.5','unmatched'], 'tie':'descending IoU then prediction and gold coordinate/type tuple', 'purpose':'descriptive, never changes main strict evaluation'},
       'source_hashes':source_hashes, 'data':results,
       'coverage':coverage_rows, 'proposal_actions':action_rows, 'policies':policy_rows,
       'checks':{'saved_source_files_unchanged':True, 'all_saved_edits_recomputed':checked_edits,
                 'audit_documents':len(doc_rows), 'exact_archive_manifest_match':True,
                 'text_hashes_and_split_roles_verified':True, 'test_documents_parsed':0,
                 'historic_policies_replayed_exactly':4, 'coverage_budget_rows_recomputed':len(coverage_rows)}}
(W/'diagnostic_supplement.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
write_csv('diagnostic_document_statistics.csv',doc_rows)
write_csv('diagnostic_coverage.csv',coverage_rows)
write_csv('diagnostic_proposal_actions.csv',action_rows)
write_csv('diagnostic_policies.csv',policy_rows)
write_csv('diagnostic_endpoint_partition.csv',endpoint_rows)
write_csv('diagnostic_object_transitions.csv',transition_rows)
print(json.dumps({'checks':out['checks'],'data':results},ensure_ascii=False,indent=2))
