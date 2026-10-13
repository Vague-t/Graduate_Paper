"""Completely synthetic test case, with scripted non-LLM responses."""
import json
from .backend import ReplayBackend
from .config import load, merge, validate
from .data import make_document
from .pipeline import infer_document
from .metrics import evaluate
from .io import fresh_dir, dump, jsonl


def fixture():
    components = [{"id": 1, "type": "Claim", "span": [1, 5]}, {"id": 2, "type": "Premise", "span": [7, 10]}]
    relations = [{"source": 2, "target": 1, "type": "Support"}]
    d = make_document("synthetic-demo-001", "aaec", "Libraries should stay open longer. Students need study space.", components, relations, "test")
    d["fixture_only"] = True
    return d


def demo(out_path):
    doc = fixture()
    c = doc["graph"]["components"]
    g0 = {"components": c[:1], "relations": []}
    g1 = {"components": c, "relations": doc["graph"]["relations"]+[{"source": 2, "target": 1, "type": "Attack"}]}
    responses = [json.dumps(g0), json.dumps(g0), json.dumps({"components": c, "relations": []}), json.dumps(g1), '{"supported":true}', '{"supported":false}']
    cfg = validate(merge(load(), {"inference": {"candidates": 2, "root_threshold": 1}}))
    trace = infer_document(doc, cfg, ReplayBackend(responses))
    assert trace["status"] == "ok" and trace["graph"] == doc["graph"]
    assert any(h["action"] == "RemoveEdge" and h["accepted"] for h in trace["repair_history"])
    result = evaluate([doc], [{"id": doc["id"], "status": "ok", "graph": trace["graph"]}])
    out = fresh_dir(out_path)
    jsonl(out/"fixture.jsonl", [doc]); jsonl(out/"trace.jsonl", [trace])
    dump(out/"synthetic_evaluation.json", {"fixture_only": True, "not_a_thesis_experiment": True, **result})
    summary = {"fixture_only": True, "not_a_thesis_experiment": True,
               "tested": ["component_and_relation_stages", "graph_rerank", "semantic_cache", "RemoveEdge_acceptance", "exact_match_evaluator"],
               "model_downloaded": False, "llm_training_performed": False, "out": str(out)}
    dump(out/"summary.json", summary)
    return summary
