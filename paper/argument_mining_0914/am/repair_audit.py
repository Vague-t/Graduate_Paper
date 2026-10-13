"""Post-hoc gold audit only; not imported by inference or candidate selection."""
from collections import Counter
from .io import fingerprint
from .metrics import evaluate, compare, scores, objects
from .pipeline import public_document
from .schema import parse_graph

EMPTY = {"components": [], "relations": []}


def transitions(before, after, gold):
    result = {}
    for name, b, a, g in zip(("component", "relation"), objects(before), objects(after), objects(gold)):
        cb, ca = b & g, a & g
        lost = sum((cb-ca).values()); gained = sum((ca-cb).values())
        result[name] = {"correct_before": sum(cb.values()), "correct_lost": lost,
                        "correct_gained": gained, "false_positive_before": sum((b-g).values()),
                        "false_positive_after": sum((a-g).values())}
    return result


def audit_repair(docs, traces):
    if not docs or len({d["id"] for d in docs}) != len(docs):
        raise ValueError("Nonempty unique gold documents required")
    by_id = {r["id"]: r for r in traces}
    if len(by_id) != len(traces) or set(by_id) != {d["id"] for d in docs}:
        raise ValueError("Traces must include every document exactly once, including failures")
    before_rows, after_rows, details = [], [], []
    totals = {k: Counter() for k in ("component", "relation")}
    actions, action_accepts = Counter(), Counter()
    calls, cost_coverage = Counter(), Counter(); scored = 0; proxy_downstream = Counter()
    for doc in docs:
        trace = by_id[doc["id"]]
        if trace.get("document_sha256") != fingerprint(public_document(doc)):
            raise ValueError("Trace is not bound to the gold document text/tokens")
        initial = trace.get("initial_graph")
        final = trace.get("graph") if trace.get("status") == "ok" else None
        # Failure rows remain in the evaluation denominator, never silently excluded.
        before_rows.append({"id": doc["id"], "graph": initial, "status": "ok" if initial is not None else "no_initial_graph"})
        after_rows.append({"id": doc["id"], "graph": final, "status": trace.get("status", "unknown")})
        b = parse_graph(initial) if initial is not None else EMPTY
        a = parse_graph(final) if final is not None else EMPTY
        moved = transitions(b, a, doc["graph"])
        for name in totals:
            totals[name].update(moved[name])
        metrics_before, metrics_after = compare(b, doc["graph"]), compare(a, doc["graph"])
        delta = {name: scores(metrics_after[name])["f1"]-scores(metrics_before[name])["f1"] for name in totals}
        bs, fs = trace.get("initial_repair_score"), trace.get("final_score")
        proxy_delta = fs["total"]-bs["total"] if bs is not None and fs is not None else None
        if proxy_delta is not None:
            scored += 1
            for name in totals:
                proxy_downstream[name] += proxy_delta > 1e-12 and delta[name] < -1e-12
        action_details = []
        for event in trace.get("repair_history", []):
            actions[event["action"]] += 1
            if event["accepted"]:
                action_accepts[event["action"]] += 1
                if "before_graph" in event and "after_graph" in event:
                    action_details.append({"action": event["action"], "attempt": event["attempt"],
                                           "transitions": transitions(event["before_graph"], event["after_graph"], doc["graph"])})
                else:
                    action_details.append({"action": event["action"], "audit": "UNAVAILABLE_IN_LEGACY_TRACE"})
        for key in ("calls", "logical_calls", "input_tokens_observed", "output_tokens_charged", "logical_output_tokens_charged", "seconds", "failed_calls"):
            if key in trace.get("usage", {}):
                calls[key] += trace["usage"][key]
                cost_coverage[key] += 1
        details.append({"id": doc["id"], "status": trace.get("status"), "transitions": moved,
                        "f1_delta": delta, "proxy_delta_same_repair_scale": proxy_delta,
                        "accepted_actions": action_details})
    for name, total in totals.items():
        total["correct_loss_rate"] = total["correct_lost"]/total["correct_before"] if total["correct_before"] else None
    return {"protocol": "repair-audit-exact-typed-endpoints-v1", "gold_used_only_posthoc": True,
            "before": evaluate(docs, before_rows), "after": evaluate(docs, after_rows),
            "object_transitions": totals, "action_attempts": actions, "action_accepts": action_accepts,
            "costs_observed_sum": calls, "cost_documents_observed": cost_coverage,
            "total_documents": len(docs), "scored_documents": scored,
            "proxy_up_task_down_documents": {k: {"count": proxy_downstream[k], "denominator": scored,
                "rate": proxy_downstream[k]/scored if scored else None} for k in totals},
            "per_document": details,
            "definitions": {"correct_loss_rate": "Correct exact-match objects lost / all correct objects before repair; not a touched-object rate.",
                            "correct_gained": "Gold exact-match objects present after but absent before; not necessarily one-to-one edits.",
                            "proxy_up_task_down": "Same-scale repair score rises while document F1 falls; legacy traces without initial_repair_score excluded only from this diagnostic.",
                            "costs": "Sums cover only documents with that usage field; absent fields are unavailable, not zero. Cached logical generation is charged; cached wall time is not end-to-end time."}}
