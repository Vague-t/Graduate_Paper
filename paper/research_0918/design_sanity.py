"""Synthetic design checks only: no trained model, real corpus, or ILP solver.

Execute: python research_0918/design_sanity.py
Frozen factors are hand-assigned. These tests establish neither performance
nor novelty; they check algebra, endpoint identity, commit rules and a failure.
"""
from dataclasses import dataclass
from math import isclose, isfinite, log
import unittest


@dataclass(frozen=True)
class State:
    # (start, end, type); edge endpoints refer to spans, never export IDs.
    components: frozenset
    edges: frozenset  # ((start, end), (start, end), relation)

    def types(self):
        return {(s, e): t for s, e, t in self.components}

    def semantic_edges(self):
        types = self.types()
        return frozenset(((*u, types[u]), (*v, types[v]), r)
                         for u, v, r in self.edges)


class Problem:
    def __init__(self, component_probs, relation_probs, lam=1.0,
                 eta_c=0.01, eta_r=0.01):
        self.pc = component_probs
        self.pr = relation_probs  # key: (source span, source type, target span, target type)
        self.lam, self.eta_c, self.eta_r = lam, eta_c, eta_r

    def legal(self, state):
        if len(state.types()) != len(state.components):
            return False
        spans = list(state.types())
        for i, u in enumerate(spans):
            if u not in self.pc or not 1 <= u[0] <= u[1]:
                return False
            if state.types()[u] not in self.pc[u] or state.types()[u] == 'NULL':
                return False
            if any(max(u[0], v[0]) <= min(u[1], v[1]) for v in spans[:i]):
                return False
        seen_pairs = set()
        for u, v, r in state.edges:
            if u not in spans or v not in spans or u == v or r == 'NONE':
                return False
            if (u, v) in seen_pairs:
                return False
            seen_pairs.add((u, v))
            key = (u, state.types()[u], v, state.types()[v])
            if key not in self.pr or r not in self.pr[key]:
                return False
        return True  # This toy does NOT implement corpus-specific constraints.

    def component_score(self, state):
        return sum(log(self.pc[(s, e)][t] / self.pc[(s, e)]['NULL'])
                   for s, e, t in state.components)

    def relation_probs(self, state, edge):
        u, v, _ = edge
        ty = state.types()
        return self.pr[(u, ty[u], v, ty[v])]

    def value(self, state):
        assert self.legal(state)
        return self.component_score(state) + self.lam * sum(
            log(self.relation_probs(state, edge)[edge[2]] /
                self.relation_probs(state, edge)['NONE'])
            for edge in state.edges)

    def score(self, state, anchor):
        return (self.value(state)
                - self.eta_c * len(state.components ^ anchor.components)
                - self.eta_r * len(state.semantic_edges() ^ anchor.semantic_edges()))

    def commit(self, before, candidate, anchor, *, budget=True, delta=1e-9,
               tau_c=0.5, tau_d=0.5, tau_r=0.5, standalone_delete=False):
        # Deliberately stateless: on any failure the exact before-state survives.
        if not budget:
            return before, 'budget'
        if not self.legal(candidate):
            return before, 'illegal'
        added = candidate.components - before.components
        if any(self.pc[(s, e)][t] < tau_c for s, e, t in added):
            return before, 'component_gate'
        if standalone_delete and any(
                self.pc[(s, e)]['NULL'] < tau_d
                for s, e, _ in before.components - candidate.components):
            return before, 'delete_gate'
        if self.component_score(candidate) < self.component_score(before) - 1e-12:
            return before, 'component_decrease'
        old_semantic = before.semantic_edges()
        ct = candidate.types()
        for edge in candidate.edges:
            u, v, r = edge
            semantic = ((*u, ct[u]), (*v, ct[v]), r)
            if semantic not in old_semantic:
                q = self.relation_probs(candidate, edge)
                if q[r] < tau_r or q[r] <= q['NONE']:
                    return before, 'edge_gate'
        if self.score(candidate, anchor) - self.score(before, anchor) <= delta:
            return before, 'no_strict_gain'
        return candidate, 'accepted'


A, B, C = (1, 3), (5, 8), (10, 12)
EMPTY = State(frozenset(), frozenset())


def fixture():
    pc = {A: {'NULL': .1, 'Premise': .3, 'Claim': .6},
          B: {'NULL': .1, 'Premise': .9}}
    pr = {(B, 'Premise', A, 'Premise'): {'NONE': .1, 'Support': .9},
          (B, 'Premise', A, 'Claim'): {'NONE': .05, 'Support': .95}}
    before = State(frozenset({(*A, 'Premise'), (*B, 'Premise')}),
                   frozenset({(B, A, 'Support')}))
    after = State(frozenset({(*A, 'Claim'), (*B, 'Premise')}), before.edges)
    return Problem(pc, pr), before, after


class DesignChecks(unittest.TestCase):
    def test_delete_supported_isolated_component_loses_score(self):
        p, _, _ = fixture()
        initial = State(frozenset({(*B, 'Premise')}), frozenset())
        self.assertLess(p.score(EMPTY, initial), p.score(initial, initial))
        self.assertNotEqual(p.commit(initial, EMPTY, initial, standalone_delete=True)[1], 'accepted')

    def test_inactive_candidate_does_not_change_score(self):
        p, before, _ = fixture()
        old = p.score(before, before)
        p.pc[C] = {'NULL': .2, 'Claim': .8}
        self.assertEqual(old, p.score(before, before))

    def test_component_retype_changes_semantic_edge_identity(self):
        _, before, after = fixture()
        self.assertEqual(before.edges, after.edges)
        self.assertNotEqual(before.semantic_edges(), after.semantic_edges())

    def test_retyped_endpoint_cannot_inherit_old_edge_pass(self):
        p, before, after = fixture()
        p.pc[A] = {'NULL': .01, 'Premise': .01, 'Claim': .98}
        p.pr[(B, 'Premise', A, 'Claim')] = {'NONE': .6, 'Support': .4}
        self.assertGreater(p.score(after, before), p.score(before, before))
        self.assertEqual(p.commit(before, after, before)[1], 'edge_gate')

    def test_complete_transaction_can_cross_bad_intermediate(self):
        p, before, after = fixture()
        staged = State(after.components, frozenset())
        self.assertLess(p.score(staged, before), p.score(before, before))
        self.assertGreater(p.score(after, before), p.score(before, before))
        self.assertEqual(p.commit(before, after, before), (after, 'accepted'))

    def test_budget_failure_returns_exact_before_state(self):
        p, before, after = fixture()
        result, reason = p.commit(before, after, before, budget=False)
        self.assertIs(result, before)
        self.assertEqual(reason, 'budget')

    def test_dangling_edge_is_rejected_and_rolled_back(self):
        p, before, _ = fixture()
        candidate = State(frozenset({(*A, 'Claim')}), before.edges)
        result, reason = p.commit(before, candidate, before)
        self.assertIs(result, before)
        self.assertEqual(reason, 'illegal')

    def test_missing_candidate_is_not_recoverable(self):
        p, before, _ = fixture()
        candidate = State(before.components | {(*C, 'Claim')}, before.edges)
        self.assertEqual(p.commit(before, candidate, before)[1], 'illegal')

    def test_tie_is_not_accepted(self):
        p, before, _ = fixture()
        self.assertEqual(p.commit(before, before, before)[1], 'no_strict_gain')

    def test_empty_graph_has_finite_energy(self):
        p, _, _ = fixture()
        self.assertTrue(isfinite(p.score(EMPTY, EMPTY)))
        self.assertEqual(p.score(EMPTY, EMPTY), 0)

    def test_joint_delta_equals_changed_factors_and_anchored_penalty(self):
        p, before, after = fixture()
        expected = log(.6/.3) + log((.95/.05)/(.9/.1)) - 2*.01 - 2*.01
        self.assertTrue(isclose(p.score(after, before) - p.score(before, before), expected))

    def test_component_gate_blocks_relation_compensated_type_damage(self):
        p, before, after = fixture()
        p.pc[A] = {'NULL': .05, 'Premise': .55, 'Claim': .4}
        p.pr[(B, 'Premise', A, 'Claim')] = {'NONE': .001, 'Support': .999}
        self.assertGreater(p.score(after, before), p.score(before, before))
        self.assertEqual(p.commit(before, after, before, tau_c=.3)[1], 'component_decrease')

    def test_correct_isolated_component_can_be_inserted(self):
        p, before, _ = fixture()
        p.pc[C] = {'NULL': .1, 'Claim': .9}
        candidate = State(before.components | {(*C, 'Claim')}, before.edges)
        self.assertEqual(p.commit(before, candidate, before)[1], 'accepted')

    def test_wrong_verifier_can_increase_score_and_destroy_gold_match(self):
        # A deliberate counterexample to any semantic/F1 monotonicity claim.
        p = Problem({A: {'NULL': .8, 'Claim': .2}}, {})
        gold = State(frozenset({(*A, 'Claim')}), frozenset())
        result, reason = p.commit(gold, EMPTY, gold, standalone_delete=True)
        self.assertEqual(reason, 'accepted')
        self.assertGreater(p.score(result, gold), p.score(gold, gold))
        self.assertEqual(len(gold.components & result.components), 0)

    def test_fixed_factors_do_not_prevent_oversegmentation(self):
        long_span = (1, 8)
        p = Problem({long_span: {'NULL': .45, 'Claim': .55},
                     A: {'NULL': .2, 'Claim': .8},
                     B: {'NULL': .2, 'Claim': .8}}, {})
        gold = State(frozenset({(*long_span, 'Claim')}), frozenset())
        split = State(frozenset({(*A, 'Claim'), (*B, 'Claim')}), frozenset())
        result, reason = p.commit(gold, split, gold)
        self.assertEqual(reason, 'accepted')
        self.assertEqual(len(gold.components & result.components), 0)

    def test_edit_penalty_is_relative_to_fixed_anchor(self):
        p, before, after = fixture()
        self.assertAlmostEqual(p.value(after) - p.score(after, before), .04)
        # Resetting the anchor would erase .04 of penalty: explicitly forbidden.
        self.assertAlmostEqual(p.score(after, after) - p.score(after, before), .04)


if __name__ == '__main__':
    unittest.main(verbosity=2)
