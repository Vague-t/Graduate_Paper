import copy
import json
import tempfile
import unittest
from pathlib import Path
from am.demo import fixture
from am.config import load, validate, merge
from am.schema import issues
from am.metrics import evaluate
from am.backend import SemanticVerifier, BudgetedBackend, ReplayBackend, BudgetExceeded
from am.repair import Scorer, select_graph, repair
from am.pipeline import infer_document
from am.io import dump
from am.cli import summarize


class ProtocolTests(unittest.TestCase):
    def test_cached_generation_still_consumes_logical_budget(self):
        b = BudgetedBackend(ReplayBackend(['{}']), 2, 10, load()["generation"],
                            {"calls": 2, "output_tokens_charged": 4})
        with self.assertRaises(BudgetExceeded): b.call([], phase="verify")
        self.assertEqual(b.usage()["calls"], 0)
        self.assertEqual(b.usage()["logical_calls"], 2)

    def test_invalid_training_step_limit(self):
        with self.assertRaises(ValueError): validate(merge(load(), {"training": {"max_optimizer_steps": 0}}))

    def test_all_four_action_interfaces(self):
        from am.repair import actions
        d = fixture(); g = d["graph"]
        other = copy.deepcopy(g); other["components"][0]["span"][1] -= 1
        calls = []
        def rerun(graph, sources):
            calls.append(sources); return copy.deepcopy(graph)
        node = list(actions(g, (1, 2, "node", 0, "DENS"), [other], "aaec", rerun))
        edge = list(actions(g, (1, 1, "edge", 0, "COH"), [other], "aaec", rerun))
        self.assertEqual({n for n, _ in node+edge}, {"Promote/Demote", "Replace", "LocalRerun", "RemoveEdge"})
        replacement = next(x for n, x in node if n == "Replace")
        self.assertEqual(replacement["components"][0]["id"], g["components"][0]["id"])
        self.assertEqual(len(replacement["components"]), len(g["components"]))

    def test_weighted_selection_not_a_hard_validity_guarantee(self):
        class S:
            config = {"selection": "weighted"}
            def score(self, g): return g
        s = S(); graphs = [{"validity": 0, "total": .8}, {"validity": 1, "total": .6}]
        self.assertEqual(select_graph(graphs, s), 0)
        s.config["selection"] = "valid_first"
        self.assertEqual(select_graph(graphs, s), 1)

    def test_zero_denominator_and_all_types(self):
        d = fixture(); d["graph"] = {"components": [], "relations": []}
        result = evaluate([d], [{"id": d["id"], "graph": d["graph"]}])
        self.assertEqual(result["relation"]["f1"], 0)
        self.assertEqual(set(result["component_by_type"]), {"Claim", "MajorClaim", "Premise"})

    def test_verifier_cache_uses_text(self):
        d = fixture(); cfg = load()
        b = BudgetedBackend(ReplayBackend(['{"supported":true}', '{"supported":false}']), 2, 100, cfg["generation"])
        v = SemanticVerifier(b); e = d["graph"]["relations"][0]
        self.assertEqual(v.edge(d, d["graph"], e), 1)
        self.assertEqual(v.edge(d, d["graph"], e), 1)
        different = copy.deepcopy(d); different["text"] += " Rejected."
        self.assertEqual(v.edge(different, d["graph"], e), 0)
        self.assertEqual(b.usage()["calls"], 2)

    def test_verifier_unknown_is_not_false_or_true(self):
        d = fixture(); cfg = load()
        b = BudgetedBackend(ReplayBackend(['{"supported":"true"}']), 1, 100, cfg["generation"])
        with self.assertRaises(ValueError): SemanticVerifier(b).edge(d, d["graph"], d["graph"]["relations"][0])

    def test_empty_candidates_status(self):
        cfg = validate(merge(load(), {"inference": {"strategy": "single_pass"}}))
        result = infer_document(fixture(), cfg, ReplayBackend(["bad JSON"]))
        self.assertEqual(result["status"], "no_parsed_candidate")
        self.assertIsNone(result["graph"])

    def test_relation_cannot_change_nodes(self):
        d = fixture(); cfg = validate(merge(load(), {"inference": {"strategy": "staged_k1"}}))
        comp = {"components": d["graph"]["components"], "relations": []}
        result = infer_document(d, cfg, ReplayBackend([json.dumps(comp), '{"components":[],"relations":[]}']))
        self.assertEqual(result["status"], "no_parsed_candidate")

    def test_majorclaim_stance_not_relation(self):
        d = fixture(); d["graph"]["components"][0]["type"] = "MajorClaim"
        self.assertIn("aaec_majorclaim_not_a_relation_endpoint", [x.detail for x in issues(d["graph"], 11, "aaec")])

    def test_micro_not_average_document_f1(self):
        d = fixture()
        second = copy.deepcopy(d); second["id"] = "empty-pred"; second["source_id"] = "empty-pred"
        second["graph"] = {"components": d["graph"]["components"][:1], "relations": []}
        r = evaluate([d, second], [{"id": d["id"], "graph": d["graph"]}, {"id": second["id"], "graph": {"components": [], "relations": []}}])
        self.assertEqual(r["component"]["f1"], 80)

    def test_aggregation_requires_independent_seeds(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            row = {"run_binding": {"seed": 17, "same_data": "x"}, "component": {"f1": 10}, "relation": {"f1": 20}}
            dump(p/"a.json", row); dump(p/"b.json", row)
            with self.assertRaises(ValueError): summarize([p/"a.json", p/"b.json"], p/"out.json")
            row["run_binding"]["seed"] = 29; row["component"]["f1"] = 12
            dump(p/"b.json", row)
            result = summarize([p/"a.json", p/"b.json"], p/"out.json")
            self.assertEqual(result["component"]["mean"], 11)
            self.assertAlmostEqual(result["component"]["sample_sd"], 2**0.5)

    def test_repair_budget_returns_last_accepted_state(self):
        from am.backend import BudgetExceeded
        class V:
            def edge(self, *args): return 1
        d = fixture(); g = copy.deepcopy(d["graph"])
        g["relations"].append({"source": 999, "target": 1, "type": "Support"})
        scorer = Scorer(d, "aaec", load()["inference"], V())
        def fail(*args): raise BudgetExceeded("test")
        final, history, status = repair(g, [g], scorer, fail)
        self.assertEqual(final, d["graph"])
        self.assertTrue(any(x["accepted"] for x in history))
        self.assertEqual(status, "model_budget_exhausted")


if __name__ == "__main__": unittest.main()
