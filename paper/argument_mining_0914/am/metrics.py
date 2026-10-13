"""Exact-match micro evaluation. Duplicates remain false positives."""
from collections import Counter
from .schema import parse_graph, coarse_graph, validate_document, SCHEMAS


def counts(pred, gold):
    tp = sum((pred & gold).values())
    return {"tp": tp, "fp": sum(pred.values())-tp, "fn": sum(gold.values())-tp}


def scores(c):
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    return {**c, "precision": 100*tp/(tp+fp) if tp+fp else 0.0,
            "recall": 100*tp/(tp+fn) if tp+fn else 0.0,
            "f1": 200*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0}


def objects(g, endpoint_types=True):
    components = Counter((c["span"][0], c["span"][1], c["type"]) for c in g["components"])
    by_id = {}
    for c in g["components"]:
        by_id.setdefault(c["id"], []).append(c)
    def endpoint(cid, edge_index, side):
        candidates = by_id.get(cid, [])
        if len(candidates) != 1:
            return ("INVALID_ENDPOINT", edge_index, side)
        c = candidates[0]
        return (*c["span"], c["type"]) if endpoint_types else tuple(c["span"])
    edges = Counter((endpoint(e["source"], i, "s"), endpoint(e["target"], i, "t"), e["type"]) for i, e in enumerate(g["relations"]))
    return components, edges


def compare(pred, gold, endpoint_types=True, coarse=False):
    if coarse:
        pred, gold = coarse_graph(pred), coarse_graph(gold)
    pc, pe = objects(pred, endpoint_types); gc, ge = objects(gold, endpoint_types)
    return {"component": counts(pc, gc), "relation": counts(pe, ge),
            "component_by_type": {t: counts(Counter({k:v for k,v in pc.items() if k[-1] == t}), Counter({k:v for k,v in gc.items() if k[-1] == t})) for t in sorted({k[-1] for k in pc | gc})},
            "relation_by_type": {t: counts(Counter({k:v for k,v in pe.items() if k[-1] == t}), Counter({k:v for k,v in ge.items() if k[-1] == t})) for t in sorted({k[-1] for k in pe | ge})}}


def evaluate(gold_docs, predictions, endpoint_types=True, coarse=False):
    if not gold_docs:
        raise ValueError("Cannot evaluate an empty corpus")
    gold_ids = [d["id"] for d in gold_docs]
    pred_ids = [d["id"] for d in predictions]
    if len(set(gold_ids)) != len(gold_ids) or len(set(pred_ids)) != len(pred_ids) or set(gold_ids) != set(pred_ids):
        raise ValueError("Prediction IDs must match gold exactly, once each; failures need explicit rows")
    pred_map = {d["id"]: d for d in predictions}
    aggregate = {k: Counter() for k in ("component", "relation")}
    by_type = {k: {} for k in ("component_by_type", "relation_by_type")}
    failures, per_doc = Counter(), []
    for doc in gold_docs:
        validate_document(doc)
        p = pred_map[doc["id"]]
        if p.get("status", "ok") != "ok":
            failures[p["status"]] += 1
            pred = {"components": [], "relations": []}
        else:
            pred = parse_graph(p["graph"])
        row = compare(pred, doc["graph"], endpoint_types, coarse)
        for key in aggregate:
            aggregate[key].update(row[key])
        for key in by_type:
            for typ, values in row[key].items():
                by_type[key].setdefault(typ, Counter()).update(values)
        per_doc.append({"id": doc["id"], **{k: scores(row[k]) for k in aggregate}})
    component_labels = {"Claim", "Premise"} if coarse else set().union(*(set(SCHEMAS[d["corpus"]]["components"]) for d in gold_docs))
    relation_labels = {"Link"} if coarse else set().union(*(set(SCHEMAS[d["corpus"]]["relations"]) for d in gold_docs))
    for key, labels in (("component_by_type", component_labels), ("relation_by_type", relation_labels)):
        for typ in labels:
            by_type[key].setdefault(typ, Counter(tp=0, fp=0, fn=0))
    return {"protocol": {"span": "one_based_inclusive", "aggregation": "object_micro",
                         "endpoint_types": endpoint_types, "coarse": coarse, "zero_denominator": 0,
                         "failed_output": "zero_predictions_with_failure_record; gold remains in denominator"},
            "documents": len(gold_docs), "failures": dict(failures),
            **{k: scores(dict(v)) for k, v in aggregate.items()},
            **{k: {t: scores(dict(v)) for t, v in value.items()} for k, value in by_type.items()},
            "per_document": per_doc}


def candidate_oracle(doc, candidates, endpoint_types=True, coarse=False):
    """Per-document relation F1 diagnostic; not a corpus-micro upper bound."""
    if not candidates:
        raise ValueError("Oracle needs a nonempty candidate pool")
    values = [scores(compare(g, doc["graph"], endpoint_types, coarse)["relation"])["f1"] for g in candidates]
    return max(range(len(candidates)), key=lambda i: (values[i], -i))
