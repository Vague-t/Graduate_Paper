import copy
import json
import tempfile
import unittest
from pathlib import Path

from am.config import load, merge, validate
from am.io import loads
from am.schema import parse_graph, issues, cycle_edges, tokenize, char_to_span
from am.data import split_audit, convert_brat, convert_cdcp
from am.metrics import compare, scores, evaluate, candidate_oracle
from am.prompts import claim_gate, cue_present
from am.backend import BudgetedBackend, BudgetExceeded, ReplayBackend
from am.repair import Scorer, select_graph, repair
from am.augment import rewrite_slots, local_units
from am.pipeline import public_document
from am.demo import fixture, demo


class TrueVerifier:
    def edge(self, doc, graph, edge):
        return int(edge["type"] != "Attack")


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.doc = fixture()
        self.g = self.doc["graph"]
        self.cfg = load()

    def test_config_defaults(self):
        self.assertEqual(self.cfg["inference"]["candidates"], 3)

    def test_config_unknown_rejected(self):
        with self.assertRaises(ValueError):
            merge(self.cfg, {"generation": {"temprature": 1}})

    def test_config_negative_budget(self):
        with self.assertRaises(ValueError):
            validate(merge(self.cfg, {"inference": {"max_calls": -1}}))

    def test_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            loads('{"a":1,"a":2}')

    def test_nan_json(self):
        with self.assertRaises(ValueError):
            loads('{"a":NaN}')

    def test_bool_not_integer_span(self):
        g = copy.deepcopy(self.g); g["components"][0]["span"][0] = True
        with self.assertRaises(ValueError):
            parse_graph(g)

    def test_strict_json_fence(self):
        with self.assertRaises(ValueError):
            parse_graph('```json\n'+json.dumps(self.g)+'\n```')

    def test_character_coordinates(self):
        tokens, offsets = tokenize("甲乙 supports café.")
        self.assertEqual(tokens, ["甲乙", "supports", "café", "."])
        self.assertEqual(char_to_span(offsets, 0, 2), [1, 1])
        with self.assertRaises(ValueError):
            char_to_span(offsets, 1, 2)

    def test_valid_graph(self):
        self.assertEqual(issues(self.g, len(self.doc["tokens"]), "aaec"), [])

    def test_cycle(self):
        g = copy.deepcopy(self.g); g["relations"].append({"source": 1, "target": 2, "type": "Support"})
        self.assertEqual(cycle_edges(g), [0, 1])

    def test_dangling_id(self):
        g = copy.deepcopy(self.g); g["relations"][0]["source"] = 999
        self.assertIn("invalid_reference", [x.detail for x in issues(g, 11, "aaec")])

    def test_id_permutation_invariant(self):
        g = copy.deepcopy(self.g)
        for c in g["components"]: c["id"] += 10
        for e in g["relations"]: e["source"] += 10; e["target"] += 10
        self.assertEqual(scores(compare(g, self.g)["relation"])["f1"], 100)

    def test_endpoint_type_protocol(self):
        g = copy.deepcopy(self.g); g["components"][0]["type"] = "MajorClaim"
        self.assertEqual(compare(g, self.g, endpoint_types=True)["relation"]["tp"], 0)
        self.assertEqual(compare(g, self.g, endpoint_types=False)["relation"]["tp"], 1)

    def test_coarse_mapping(self):
        g = copy.deepcopy(self.g); g["components"][0]["type"] = "Policy"; g["components"][1]["type"] = "Fact"; g["relations"][0]["type"] = "Reason"
        self.assertEqual(compare(g, self.g, coarse=True)["relation"]["tp"], 1)

    def test_direction_matters(self):
        g = copy.deepcopy(self.g); e = g["relations"][0]; e["source"], e["target"] = e["target"], e["source"]
        self.assertEqual(compare(g, self.g)["relation"], {"tp": 0, "fp": 1, "fn": 1})

    def test_duplicates_are_false_positives(self):
        g = copy.deepcopy(self.g); g["relations"].append(copy.deepcopy(g["relations"][0]))
        self.assertEqual(compare(g, self.g)["relation"], {"tp": 1, "fp": 1, "fn": 0})

    def test_parse_failure_keeps_gold_denominator(self):
        out = evaluate([self.doc], [{"id": self.doc["id"], "status": "parse_error", "graph": None}])
        self.assertEqual(out["relation"]["fn"], 1)
        self.assertEqual(out["component"]["fn"], 2)
        self.assertEqual(out["failures"], {"parse_error": 1})

    def test_missing_document_not_dropped(self):
        with self.assertRaises(ValueError):
            evaluate([self.doc], [])

    def test_oracle_tie_earliest(self):
        self.assertEqual(candidate_oracle(self.doc, [self.g, self.g]), 0)

    def test_split_source_leakage(self):
        d = copy.deepcopy(self.doc); d["id"] = "other"; d["split"] = "train"; d["text"] = self.doc["text"]
        with self.assertRaises(ValueError):
            split_audit([self.doc, d])

    def test_gold_removed_from_inference_view(self):
        public = public_document(self.doc)
        self.assertNotIn("graph", public)
        self.assertNotIn("split", public)

    def test_gate_is_causal(self):
        p = '{"components":[{"id":1,"type":"'
        self.assertEqual(claim_gate(p), 0)
        self.assertEqual(claim_gate(p+'Clai'), 0)
        self.assertEqual(claim_gate(p+'Claim"'), 1)
        self.assertEqual(claim_gate(p+'Claim","span":[1,'), 1)
        self.assertEqual(claim_gate(p+'Claim","span":[1,2]}'), 0)
        self.assertEqual(claim_gate('{"components":[],"relations":[{"type":"Claim"'), 0)

    def test_cue_word_boundaries(self):
        self.assertTrue(cue_present("Therefore, yes.", ["therefore"]))
        self.assertFalse(cue_present("nottherefore", ["therefore"]))

    def test_budget_calls(self):
        b = BudgetedBackend(ReplayBackend(["yes", "yes"]), 1, 5, self.cfg["generation"])
        b.call([], phase="test")
        with self.assertRaises(BudgetExceeded): b.call([], phase="test")

    def test_failed_call_is_counted(self):
        b = BudgetedBackend(ReplayBackend([ValueError("bad")]), 2, 5, self.cfg["generation"])
        with self.assertRaises(ValueError): b.call([], phase="test")
        self.assertEqual(b.usage()["failed_calls"], 1)
        self.assertEqual(b.usage()["output_tokens_charged"], 5)

    def test_scorer_density_excludes_majorclaim(self):
        g = copy.deepcopy(self.g); g["components"][0]["type"] = "MajorClaim"
        s = Scorer(self.doc, "aaec", self.cfg["inference"], TrueVerifier()).score(g)
        self.assertEqual(s["density"], 0)

    def test_scorer_cache(self):
        s = Scorer(self.doc, "aaec", self.cfg["inference"], TrueVerifier())
        self.assertIs(s.score(self.g), s.score(copy.deepcopy(self.g)))

    def test_single_invalid_edge_repair(self):
        g = copy.deepcopy(self.g); g["relations"][0]["source"] = 999
        s = Scorer(self.doc, "aaec", self.cfg["inference"], TrueVerifier())
        out, history, _ = repair(g, [g], s)
        self.assertTrue(any(h["accepted"] for h in history))
        self.assertEqual(len(out["components"]), 2)
        self.assertEqual(out["relations"], [])

    def test_two_invalid_edges_block_stepwise_repair(self):
        g = copy.deepcopy(self.g)
        g["relations"] = [{"source": 998, "target": 1, "type": "Support"}, {"source": 999, "target": 1, "type": "Support"}]
        s = Scorer(self.doc, "aaec", self.cfg["inference"], TrueVerifier())
        out, history, _ = repair(g, [g], s)
        self.assertEqual(out, g)
        self.assertFalse(any(h["accepted"] for h in history))

    def test_repair_attempt_bound(self):
        g = copy.deepcopy(self.g); g["relations"][0]["source"] = 999
        cfg = {**self.cfg["inference"], "max_attempts": 1}
        _, history, _ = repair(g, [g], Scorer(self.doc, "aaec", cfg, TrueVerifier()))
        self.assertLessEqual(len(history), 1)

    def test_augmentation_is_train_only(self):
        with self.assertRaises(ValueError): list(local_units(self.doc))

    def test_full_text_slot_coordinate_update(self):
        d = copy.deepcopy(self.doc); d["split"] = "train"
        out = rewrite_slots(d, [{"id": 1, "text": "Libraries should remain open much longer"}], [1], "aug")
        self.assertEqual(out["graph"]["components"][1]["span"], [8, 11])
        self.assertEqual(out["graph"]["relations"], d["graph"]["relations"])
        self.assertEqual(out["source_id"], d["source_id"])

    def test_brat_stance_is_not_a_relation(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"essay.txt"
            p.write_text("A claim. A reason.", encoding="utf-8")
            p.with_suffix(".ann").write_text("T1\tClaim 0 7\tA claim\nT2\tPremise 9 17\tA reason\nR1\tsupports Arg1:T2 Arg2:T1\nA1\tStance T1 For\n", encoding="utf-8")
            d = convert_brat(p, "train")
            self.assertEqual(len(d["graph"]["relations"]), 1)
            self.assertEqual(d["conversion"]["ignored_attribute_or_note_counts"], {"A": 1})

    def test_cdcp_multi_premise_needs_decision(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"00001.ann.json"
            p.with_name("00001.txt").write_text("A. B. C.", encoding="utf-8")
            p.write_text(json.dumps({"prop_offsets": [[0,1],[3,4],[6,7]], "prop_labels": ["fact","testimony","policy"], "reasons": [[[0,1],2]], "evidences": []}), encoding="utf-8")
            with self.assertRaises(ValueError): convert_cdcp(p, "train")
            d = convert_cdcp(p, "train", "expand")
            self.assertEqual(len(d["graph"]["relations"]), 2)
            self.assertEqual(d["conversion"]["expanded_relations"], 1)

    def test_synthetic_demo(self):
        with tempfile.TemporaryDirectory() as temp:
            result = demo(Path(temp)/"demo")
            self.assertTrue(result["fixture_only"])


if __name__ == "__main__":
    unittest.main()
