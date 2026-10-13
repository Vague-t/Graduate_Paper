"""Deterministic manuscript examples; no model, corpus or network calls."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'argument_mining_0914'))
from am.augment import local_units, rewrite_slots, augmentation_prompt
from am.config import DEFAULT
from am.metrics import compare, scores
from am.repair import Scorer, repair, actions, detect
from am.schema import tokenize, sentence_spans, issues


def node(i, typ, span=None):
    return {'id': i, 'type': typ, 'span': span or [i, i]}


def edge(i, j, typ='Support'):
    return {'source': i, 'target': j, 'type': typ}


class FixedVerifier:
    def edge(self, doc, graph, relation):
        return int(relation['type'] == 'Support')


def measures(g, gold, scorer):
    match = compare(g, gold)
    score = scorer.score(g)
    return {**{k: score[k] for k in ('total', 'density', 'coherence', 'validity')},
            'component_f1': scores(match['component'])['f1'],
            'relation_f1': scores(match['relation'])['f1'],
            'coverage_node_indices': list(score['coverage'])}


cfg = deepcopy(DEFAULT['inference'])
doc = {'id': 'constructed-score-example', 'text': 'a b c d', 'tokens': ['a', 'b', 'c', 'd']}
gold = {'components': [node(1, 'Claim'), node(2, 'Claim'), node(3, 'Premise'), node(4, 'Premise')],
        'relations': [edge(3, 2), edge(4, 2)]}
scorer = Scorer(doc, 'aaec', cfg, FixedVerifier())
assert not issues(gold, 4, 'aaec')
out, history, termination = repair(gold, [gold], scorer)
before, after = measures(gold, gold, scorer), measures(out, gold, scorer)
assert before['total'] == 0.8 and after['total'] == 1.0
assert before['component_f1'] == 100 and after['component_f1'] == 75
assert out['relations'] == gold['relations'] and after['relation_f1'] == 100
assert history[0]['action'] == 'Promote/Demote' and history[0]['accepted']

simple_gold = {'components': [node(1, 'Claim'), node(2, 'Premise'), node(3, 'Premise')],
               'relations': [edge(2, 1)]}
simple_initial = deepcopy(simple_gold)
simple_initial['relations'].append(edge(3, 1, 'Attack'))
simple_scorer = Scorer(doc, 'aaec', cfg, FixedVerifier())
event = detect(simple_initial, simple_scorer.score(simple_initial))[0]
name, proposal = next(actions(simple_initial, event, [simple_initial], 'aaec'))
success_before = measures(simple_initial, simple_gold, simple_scorer)
success_after = measures(proposal, simple_gold, simple_scorer)
assert name == 'RemoveEdge' and not issues(proposal, 4, 'aaec')
assert abs(success_before['total'] - 0.6) < 1e-12 and success_after['total'] == 0.8
assert abs(success_before['relation_f1'] - 200 / 3) < 1e-12
assert success_after['relation_f1'] == 100
assert any(e[-1] == 'DENS' for e in detect(proposal, simple_scorer.score(proposal)))

text = 'Libraries should stay open longer. Students need study space. Campus services need investment.'
tokens, offsets = tokenize(text)
training = {'id': 'constructed-augmentation', 'source_id': 'constructed-augmentation',
            'split': 'train', 'corpus': 'aaec', 'text': text, 'tokens': tokens,
            'token_offsets': offsets, 'sentences': sentence_spans(tokens),
            'graph': {'components': [node(1, 'Claim', [1, 5]), node(2, 'Premise', [7, 10]),
                                     node(3, 'Claim', [12, 15])],
                      'relations': [edge(2, 1), edge(2, 3)]}}
unit = next(local_units(training))
assert unit == [1, 2]
request = json.loads(augmentation_prompt(training, unit, 'structure')[1]['content'])
assert request['local_relations'] == [edge(2, 1)]
rewritten = rewrite_slots(training, [{'id': 1, 'text': 'Libraries ought to remain open longer'},
                                     {'id': 2, 'text': 'Students require space for studying'}],
                          unit, 'constructed-augmentation-rewritten')
assert [c['span'] for c in rewritten['graph']['components']] == [[1, 6], [8, 12], [14, 17]]
assert rewritten['graph']['relations'] == training['graph']['relations']

result = {
    'scope': 'constructed examples only; no empirical performance or novelty validation',
    'counterexample': {'before': before, 'after': after, 'accepted_action': history[0],
                      'termination': termination, 'algorithm_changed': False},
    'successful_single_action': {'before': success_before, 'after': success_after,
                                'action': name, 'density_anomaly_remains': True},
    'augmentation': {'original_tokens': tokens, 'rewritten_tokens': rewritten['tokens'],
                     'rewritten_graph': rewritten['graph'], 'boundary_edge_preserved': True},
    'source_sha256': {name: hashlib.sha256((ROOT / 'argument_mining_0914/am' / name).read_bytes()).hexdigest()
                      for name in ('repair.py', 'augment.py', 'metrics.py', 'schema.py', 'config.py')},
    'all_assertions_passed': True,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
