"""Hermetic mechanism/engineering tests, not empirical model results."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from argparse import Namespace
from am.config import load, merge, validate
from am.data import make_document
from am.demo import fixture
from am.augment import augment_document, augmentation_prompt, center_units
from am.controls import make_plan, validate_plan, planned_for_document, match_runs
from am.repair import Scorer, repair
from am.repair_audit import audit_repair
from am.metrics import compare, scores
from am.pipeline import infer_document, public_document
from am.backend import ReplayBackend
from am.io import dump, jsonl, read_json, read_jsonl, fingerprint, file_hash
from am.cli import augment, main


class V:
    def edge(self, doc, graph, edge):
        return int(edge["type"] == "Support")


def counterexample():
    return make_document("constructed", "aaec", "A B C D",
                         [{"id": i, "type": "Claim" if i < 3 else "Premise", "span": [i, i]} for i in range(1, 5)],
                         [{"source": i, "target": 2, "type": "Support"} for i in (3, 4)], "dev")


def conservative():
    return validate(merge(load(), {"inference": {"fix_components": True, "freeze_coverage": True,
                          "strict_improvement": True, "require_new_edge_support": True}}))


class ControlsTests(unittest.TestCase):
    def test_original_counterexample_preserved_and_conservative_blocks(self):
        doc = counterexample(); g = doc["graph"]
        original, history, _ = repair(g, [g], Scorer(doc, "aaec", load()["inference"], V()))
        self.assertEqual(scores(compare(original, g)["component"])["f1"], 75)
        self.assertEqual(history[0]["candidate_score"], 1)
        fixed, history, _ = repair(g, [g], Scorer(doc, "aaec", conservative()["inference"], V()))
        self.assertEqual(fixed, g); self.assertFalse(history)

    def test_coverage_freezes_types_and_thresholds(self):
        d = counterexample(); g = d["graph"]
        s = Scorer(d, "aaec", conservative()["inference"], V())
        s.begin_repair(g)
        changed = copy.deepcopy(g); changed["components"][0]["type"] = "MajorClaim"
        self.assertEqual(s.score(changed)["density"], .5)
        changed = copy.deepcopy(g)
        changed["relations"] = [{"source": 3, "target": 2, "type": "Support"}, {"source": 2, "target": 1, "type": "Support"}]
        self.assertEqual(s.score(changed)["coverage"][1], .5)
        s.begin_repair(changed)
        self.assertEqual(s.score(changed)["coverage"][1], 1)

    def test_fixed_denominator_survives_missing_node(self):
        d = counterexample(); s = Scorer(d, "aaec", conservative()["inference"], V()); s.begin_repair(d["graph"])
        g = copy.deepcopy(d["graph"]); g["components"].pop(0)
        self.assertEqual(s.score(g)["density"], .5)

    def test_frozen_empty_coverage_is_zero(self):
        d = fixture(); g = copy.deepcopy(d["graph"]); g["components"][0]["type"] = "Premise"
        s = Scorer(d, "aaec", conservative()["inference"], V()); s.begin_repair(g)
        self.assertEqual(s.score(g)["density"], 0)

    def test_frozen_duplicate_ids_rejected(self):
        d = counterexample(); g = copy.deepcopy(d["graph"]); g["components"][1]["id"] = 1
        with self.assertRaises(ValueError):
            repair(g, [g], Scorer(d, "aaec", conservative()["inference"], V()))

    def test_all_action_paths_cannot_change_components(self):
        d = counterexample(); g = d["graph"]
        other = copy.deepcopy(g); other["components"][0]["type"] = "MajorClaim"
        def malicious(*args): return other
        final, history, _ = repair(g, [other], Scorer(d, "aaec", conservative()["inference"], V()), malicious)
        self.assertEqual(final, g)
        self.assertTrue(any(e["reason"] == "fixed_components_changed" for e in history))
        self.assertFalse(any(e["action"] in ("Replace", "Promote/Demote") for e in history))

    def test_equal_score_rejected(self):
        d = fixture(); g = d["graph"]
        cfg = conservative()["inference"]; cfg["weights"] = [0, 0, 1]
        def rerun(current, sources):
            new = copy.deepcopy(current); new["relations"] = []; return new
        final, history, _ = repair(g, [g], Scorer(d, "aaec", cfg, V()), rerun)
        self.assertEqual(final, g)
        self.assertTrue(any(e["reason"] == "no_strict_improvement" for e in history))

    def test_new_unsupported_edge_rejected_even_with_gain(self):
        d = counterexample(); g = d["graph"]
        def rerun(current, sources):
            new = copy.deepcopy(current)
            new["relations"] += [{"source": 3, "target": 1, "type": "Support"},
                                  {"source": 4, "target": 1, "type": "Support"},
                                  {"source": 3, "target": 4, "type": "Attack"}]
            return new
        final, history, _ = repair(g, [g], Scorer(d, "aaec", conservative()["inference"], V()), rerun)
        self.assertEqual(final, g)
        self.assertTrue(any(e["reason"] == "new_edge_not_supported" for e in history))

    def test_false_edge_removal_still_works(self):
        d = counterexample(); g = copy.deepcopy(d["graph"])
        g["relations"][1]["type"] = "Attack"
        final, history, _ = repair(g, [g], Scorer(d, "aaec", conservative()["inference"], V()))
        self.assertEqual(len(final["relations"]), 1)
        self.assertEqual(final["components"], g["components"])
        self.assertIn("before_graph", next(e for e in history if e["accepted"]))

    def test_plan_deterministic_train_only_and_tamper_rejected(self):
        d = counterexample(); d["split"] = "train"
        p = make_plan([d]); self.assertEqual(p, make_plan([d])); validate_plan(p, [d])
        for pair in p["pairs"]:
            for key in ("components", "relations", "token_bin"):
                self.assertEqual(pair["conclusion_footprint"][key], pair["random_footprint"][key])
        p["pairs"][0]["random"]["unit"] = [999]
        with self.assertRaises(ValueError): validate_plan(p, [d])
        d["split"] = "dev"
        with self.assertRaises(ValueError): make_plan([d])

    def test_no_conclusions_reported(self):
        d = fixture(); d["split"] = "train"
        for c in d["graph"]["components"]: c["type"] = "Premise"
        p = make_plan([d]); self.assertEqual(p["pairs"], [])
        self.assertEqual(p["exclusions"][0]["reason"], "no_conclusion_center")

    def test_plain_hides_only_local_edges(self):
        d = fixture()
        plain = json.loads(augmentation_prompt(d, [1, 2], "plain")[1]["content"])
        structure = json.loads(augmentation_prompt(d, [1, 2], "structure")[1]["content"])
        self.assertNotIn("local_relations", plain)
        self.assertIn("local_relations", structure)
        self.assertEqual(plain["components"], structure["components"])

    def test_random_unplanned_is_repeatable(self):
        d = counterexample(); d["split"] = "train"
        cfg = merge(load(), {"augmentation": {"center_policy": "random", "attempts_per_unit": 1}})
        _, log1, _ = augment_document(d, cfg, ReplayBackend(["{}"]*4))
        _, log2, _ = augment_document(d, cfg, ReplayBackend(["{}"]*4))
        self.assertEqual(log1, log2)
        self.assertEqual({x["center_id"] for x in log1}, {1, 2, 3, 4})

    def test_invalid_control_config(self):
        for changes in ({"augmentation": {"center_policy": "nonclaim"}}, {"inference": {"fix_components": "true"}}):
            with self.assertRaises(ValueError): validate(merge(load(), changes))

    def test_all_shipped_configs_validate(self):
        for p in (Path(__file__).resolve().parents[1]/"configs").glob("*.json"):
            load(p)

    def test_four_arm_cli_matching_and_no_overwrite(self):
        d = counterexample(); d["split"] = "train"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); jsonl(root/"input.jsonl", [d]); dump(root/"plan.json", make_plan([d]))
            runs = []
            for i, (policy, strategy) in enumerate((("conclusion", "plain"), ("conclusion", "structure"), ("random", "structure"), ("random", "plain"))):
                cfg = merge(load(), {"augmentation": {"center_policy": policy, "strategy": strategy}})
                dump(root/f"cfg{i}.json", cfg)
                plan = read_json(root/"plan.json")
                units = planned_for_document(plan, d["id"], policy)
                replies = []
                for unit in units:
                    replies.extend([json.dumps({"replacements": [{"id": n, "text": f"Rewritten arm {i} component {n}"} for n in unit["unit"]]}), '{"valid":true}'])
                args = Namespace(config=root/f"cfg{i}.json", input=root/"input.jsonl", plan=root/"plan.json", checkpoint=None, out=root/f"run{i}")
                with patch("am.cli.load_backend", return_value=ReplayBackend(replies)):
                    augment(args)
                runs.append(args.out)
            r = match_runs(root/"input.jsonl", root/"plan.json", runs, root/"matched")
            self.assertEqual(r["jointly_accepted_pairs"], 2)
            self.assertEqual(len(read_jsonl(root/"matched/A0/train.jsonl")), 1)
            self.assertEqual(len(read_jsonl(root/"matched/A3/train.jsonl")), 3)
            with self.assertRaises(FileExistsError): match_runs(root/"input.jsonl", root/"plan.json", runs, root/"matched")
            with self.assertRaises(ValueError): match_runs(root/"input.jsonl", root/"plan.json", [runs[0]]*4, root/"bad")
            rows = read_jsonl(runs[0]/"generated.jsonl")
            jsonl(runs[0]/"generated.jsonl", rows[:1])
            meta = read_json(runs[0]/"manifest.json"); meta["generated_sha256"] = file_hash(runs[0]/"generated.jsonl")
            dump(runs[0]/"manifest.json", meta)
            partial = match_runs(root/"input.jsonl", root/"plan.json", runs, root/"partial")
            self.assertEqual(partial["jointly_accepted_pairs"], 1)
            self.assertEqual(partial["dropped_pairs"][0]["missing_arms"], ["A1"])
            jsonl(runs[0]/"generated.jsonl", [])
            with self.assertRaises(ValueError): match_runs(root/"input.jsonl", root/"plan.json", runs, root/"bad")
            meta = read_json(runs[0]/"manifest.json"); meta["generated_sha256"] = file_hash(runs[0]/"generated.jsonl")
            dump(runs[0]/"manifest.json", meta)
            with self.assertRaisesRegex(ValueError, "No jointly accepted"):
                match_runs(root/"input.jsonl", root/"plan.json", runs, root/"empty")

    def test_posthoc_audit_catches_counterexample(self):
        d = counterexample(); g = d["graph"]; s = Scorer(d, "aaec", load()["inference"], V())
        out, history, _ = repair(g, [g], s)
        trace = {"id": d["id"], "document_sha256": fingerprint(public_document(d)), "initial_graph": g,
                 "graph": out, "status": "ok", "initial_repair_score": s.score(g), "final_score": s.score(out), "repair_history": history}
        r = audit_repair([d], [trace])
        self.assertEqual(r["proxy_up_task_down_documents"]["component"]["count"], 1)
        self.assertEqual(r["object_transitions"]["component"]["correct_loss_rate"], .25)
        trace["document_sha256"] = "wrong"
        with self.assertRaises(ValueError): audit_repair([d], [trace])

    def test_audit_failures_not_dropped(self):
        d = fixture()
        t = {"id": d["id"], "document_sha256": fingerprint(public_document(d)), "graph": None, "status": "verification_failed"}
        r = audit_repair([d], [t]); self.assertEqual(r["after"]["component"]["fn"], 2)
        self.assertEqual(r["cost_documents_observed"], {})
        self.assertIsNone(r["object_transitions"]["component"]["correct_loss_rate"])
        with self.assertRaises(ValueError): audit_repair([d], [])

    def test_pipeline_keeps_selection_separate_from_frozen_repair(self):
        d = counterexample(); g = d["graph"]
        cfg = conservative(); cfg["inference"]["candidates"] = 1
        backend = ReplayBackend([json.dumps({"components": g["components"], "relations": []}),
                                 json.dumps(g), '{"supported":true}', '{"supported":true}', json.dumps(g)])
        trace = infer_document(d, cfg, backend)
        self.assertEqual(trace["status"], "ok")
        self.assertEqual(trace["graph"], g)
        self.assertEqual(trace["repair_coverage_anchor"], {1: 2, 2: 2})
        self.assertEqual(trace["candidate_scores"][0]["total"], trace["initial_repair_score"]["total"])
        self.assertEqual(trace["usage"]["calls"], 5)
        self.assertEqual(audit_repair([d], [trace])["after"]["component"]["f1"], 100)


if __name__ == "__main__":
    unittest.main()
