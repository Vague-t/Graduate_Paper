"""Persist constructed mechanism diagnostics; no real model/dataset claim."""
import argparse
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from am.config import load, merge, validate
from am.data import make_document
from am.repair import Scorer, repair
from am.repair_audit import audit_repair
from am.pipeline import public_document
from am.controls import make_plan
from am.io import dump, jsonl, fresh_dir, fingerprint, manifest


class ConstructedVerifier:
    def edge(self, doc, graph, edge):
        return int(edge["type"] == "Support")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = fresh_dir(args.out)
    d = make_document("constructed-counterexample", "aaec", "A B C D",
                      [{"id": i, "type": "Claim" if i < 3 else "Premise", "span": [i, i]} for i in range(1, 5)],
                      [{"source": i, "target": 2, "type": "Support"} for i in (3, 4)], "dev")
    configs = {"original": load(), "conservative": validate(merge(load(), {"inference": {
        "fix_components": True, "freeze_coverage": True, "strict_improvement": True,
        "require_new_edge_support": True}}))}
    jsonl(out/"fixture.jsonl", [d])
    summaries = {}
    for name, cfg in configs.items():
        s = Scorer(public_document(d), "aaec", cfg["inference"], ConstructedVerifier())
        graph, history, termination = repair(d["graph"], [d["graph"]], s)
        trace = {"id": d["id"], "document_sha256": fingerprint(public_document(d)), "initial_graph": d["graph"],
                 "graph": graph, "status": "ok", "repair_history": history, "termination": termination,
                 "initial_repair_score": s.score(d["graph"]), "final_score": s.score(graph)}
        jsonl(out/f"{name}_traces.jsonl", [trace])
        result = audit_repair([d], [trace]); dump(out/f"{name}_audit.json", result)
        summaries[name] = {"before_component_f1": result["before"]["component"]["f1"],
                           "after_component_f1": result["after"]["component"]["f1"],
                           "before_score": trace["initial_repair_score"]["total"],
                           "after_score": trace["final_score"]["total"], "accepted": sum(h["accepted"] for h in history)}
    train = copy.deepcopy(d); train["split"] = "train"
    jsonl(out/"train_fixture.jsonl", [train]); dump(out/"plan.json", make_plan([train]))
    summary = {"scope": "constructed_software_diagnostics_only", "real_data": "NOT_RUN", "cases": summaries,
               "claims": "This reproduces one mechanism failure and its guard, not empirical performance or frequency."}
    dump(out/"summary.json", summary)
    dump(out/"manifest.json", {**manifest(configs), "status": "completed", "fixture_only": True})
    print(summary)


if __name__ == "__main__":
    main()
