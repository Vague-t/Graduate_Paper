"""Inference, cached candidates and repair without gold access."""
from copy import deepcopy
from .backend import BudgetedBackend, SemanticVerifier, BudgetExceeded
from .prompts import prompt
from .schema import parse_graph, issues
from .repair import Scorer, select_graph, repair
from .io import fingerprint


def public_document(doc):
    return {k: deepcopy(doc[k]) for k in ("id", "text", "tokens")}


def build_candidates(doc, cfg, backend):
    strategy = cfg["inference"]["strategy"]
    k = 1 if strategy in {"single_pass", "staged_k1"} else cfg["inference"]["candidates"]
    rows = []
    for index in range(k):
        row = {"index": index, "status": "pending", "graph": None}
        rows.append(row)
        try:
            if strategy == "single_pass":
                result = backend.call(prompt(doc, cfg["corpus"], "joint"), phase="joint", greedy=True, model_context={"doc": doc, "task": "joint"})
                row["raw_joint"] = result.text
                graph = parse_graph(result.text)
                outputs = [result]
            else:
                greedy = strategy == "staged_k1"
                result = backend.call(prompt(doc, cfg["corpus"], "components", variant=index), phase="components", greedy=greedy, model_context={"doc": doc, "task": "components"})
                row["raw_components"] = result.text
                comp = parse_graph(result.text)
                if comp["relations"]:
                    raise ValueError("Components-only output contained relations")
                result_rel = backend.call(prompt(doc, cfg["corpus"], "relations", components=comp["components"]), phase="relations", greedy=greedy, model_context={"doc": doc, "task": "relations"})
                row["raw_relations"] = result_rel.text
                graph = parse_graph(result_rel.text)
                if graph["components"] != comp["components"]:
                    raise ValueError("Relation model changed fixed components")
                outputs = [result, result_rel]
            row.update(status="ok", graph=graph, output_tokens=sum(x.output_tokens for x in outputs),
                       mean_logprob=sum(x.logprob_sum for x in outputs)/max(1, sum(x.output_tokens for x in outputs)))
        except BudgetExceeded as exc:
            row.update(status="budget_exhausted", error=str(exc)); break
        except (ValueError, KeyError, TypeError) as exc:
            row.update(status="parse_error", error=str(exc))
    return rows


def infer_document(document, cfg, backend, cached=None):
    doc = public_document(document)
    conf = cfg["inference"]
    if cached is not None and not {"calls", "output_tokens_charged"} <= set(cached.get("generation_usage", {})):
        raise ValueError("Cached candidates require generation-cost provenance")
    budget = BudgetedBackend(backend, conf["max_calls"], conf["max_total_output_tokens"], cfg["generation"],
                             cached.get("generation_usage") if cached else None)
    if cached is not None:
        if cached["document_sha256"] != fingerprint(doc):
            raise ValueError("Cached candidates do not belong to this input")
        rows = deepcopy(cached["candidates"])
    else:
        rows = build_candidates(doc, cfg, budget)
    valid_rows = [r for r in rows if r["status"] == "ok"]
    trace = {"id": doc["id"], "document_sha256": fingerprint(doc), "candidates": rows,
             "cache_reused": cached is not None, "repair_history": []}
    if cached is not None:
        trace["cached_generation_usage"] = cached.get("generation_usage", {})
        trace["generation_usage"] = cached.get("generation_usage", {})
    else:
        trace["generation_usage"] = budget.usage()
    if not valid_rows:
        trace.update(status="no_parsed_candidate", graph=None, usage=budget.usage(), calls=budget.events)
        return trace
    pool = [parse_graph(r["graph"]) for r in valid_rows]
    strategy = conf["strategy"]
    if strategy in {"single_pass", "staged_k1", "logprob"}:
        selected = max(range(len(pool)), key=lambda i: (valid_rows[i].get("mean_logprob", 0), -i)) if strategy == "logprob" else 0
        trace.update(status="ok", graph=pool[selected], selected_index=valid_rows[selected]["index"], termination="selection_only")
    else:
        verifier = SemanticVerifier(budget)
        scorer = Scorer(doc, cfg["corpus"], conf, verifier)
        try:
            selected = select_graph(pool, scorer)
            graph = pool[selected]
            trace.update(selected_index=valid_rows[selected]["index"], initial_graph=deepcopy(graph), candidate_scores=[scorer.score(g) for g in pool])
            def local_rerun(current, sources):
                result = budget.call(prompt(doc, cfg["corpus"], "local_relations", components=current["components"], source_ids=sources), phase="local_rerun", greedy=True, model_context={"doc": doc, "task": "relations"})
                new = parse_graph(result.text)
                if new["components"] != current["components"] or any(e["source"] not in sources for e in new["relations"]):
                    raise ValueError("LocalRerun violated fixed-node/source restriction")
                return {"components": deepcopy(current["components"]), "relations": [deepcopy(e) for e in current["relations"] if e["source"] not in sources]+new["relations"]}
            if strategy == "rerank_br":
                try:
                    graph, history, termination = repair(graph, pool, scorer, local_rerun)
                    trace.update(repair_history=history, termination=termination)
                except (BudgetExceeded, ValueError) as exc:
                    # No unvalidated partial model output is accepted. Preserve selected graph.
                    trace.update(termination="repair_aborted", repair_error=str(exc))
            else:
                trace["termination"] = "rerank_only"
            trace.update(status="ok", graph=graph, final_score=scorer.score(graph), verifier_cache_hits=verifier.cache_hits)
        except (BudgetExceeded, ValueError) as exc:
            trace.update(status="verification_failed", graph=None, error=str(exc))
    if trace["graph"] is not None:
        trace["structurally_valid"] = not issues(trace["graph"], len(doc["tokens"]), cfg["corpus"], conf["require_acyclic"])
    trace.update(usage=budget.usage(), calls=budget.events)
    return trace
