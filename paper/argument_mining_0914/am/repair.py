"""Complete-graph scoring and finite, strict-step local repair."""
from copy import deepcopy
from dataclasses import asdict
from .schema import SCHEMAS, issues
from .io import fingerprint
from .backend import BudgetExceeded


class Scorer:
    def __init__(self, doc, corpus, config, verifier):
        self.doc, self.corpus, self.config, self.verifier = doc, corpus, config, verifier
        self.cache = {}
        self.coverage_anchor = None

    def begin_repair(self, initial):
        """Only anchor within one repair run, never during pool selection."""
        self.coverage_anchor = None
        if self.config.get("freeze_coverage", False):
            ids = [c["id"] for c in initial["components"]]
            if len(ids) != len(set(ids)):
                raise ValueError("Frozen coverage requires unique initial component IDs")
            self.coverage_anchor = {
                c["id"]: self.config["other_threshold"] if any(
                    e["source"] == c["id"] for e in initial["relations"]
                ) else self.config["root_threshold"]
                for c in initial["components"]
                if c["type"] in SCHEMAS[self.corpus]["conclusions"]}
        self.cache.clear()

    def score(self, g):
        key = fingerprint(g)
        if key in self.cache:
            return self.cache[key]
        bad = issues(g, len(self.doc["tokens"]), self.corpus, self.config["require_acyclic"])
        invalid_nodes = {i.index for i in bad if i.kind == "node" and i.detail != "overlap"}
        nodes = {c["id"]: c for i, c in enumerate(g["components"]) if i not in invalid_nodes}
        judgments = []
        for e in g["relations"]:
            safe = e["source"] in nodes and e["target"] in nodes and e["source"] != e["target"] and e["type"] in SCHEMAS[self.corpus]["relations"]
            judgments.append(self.verifier.edge(self.doc, g, e) if safe else 0)
        coverage = {}
        for i, c in enumerate(g["components"]):
            if self.coverage_anchor is not None:
                if c["id"] not in self.coverage_anchor:
                    continue
                threshold = self.coverage_anchor[c["id"]]
            elif c["type"] not in SCHEMAS[self.corpus]["conclusions"]:
                continue
            else:
                has_outgoing = any(e["source"] == c["id"] for e in g["relations"])
                threshold = self.config["other_threshold"] if has_outgoing else self.config["root_threshold"]
            indegree = sum(p for e, p in zip(g["relations"], judgments) if e["target"] == c["id"])
            coverage[i] = min(indegree/threshold, 1.0)
        denominator = len(self.coverage_anchor) if self.coverage_anchor is not None else len(coverage)
        dens = sum(coverage.values())/denominator if denominator else 0.0
        coh = sum(judgments)/len(judgments) if judgments else 0.0
        valid = int(not bad)
        value = sum(w*x for w, x in zip(self.config["weights"], (dens, coh, valid)))
        result = {"total": value, "density": dens, "coherence": coh, "validity": valid,
                  "coverage": coverage, "edge_judgments": judgments,
                  "issues": [asdict(i) for i in bad]}
        self.cache[key] = result
        return result


def select_graph(candidates, scorer):
    if not candidates:
        raise ValueError("No parsed candidate graphs")
    values = [scorer.score(g) for g in candidates]
    policy = scorer.config["selection"]
    return max(range(len(candidates)), key=lambda i: ((values[i]["validity"] if policy == "valid_first" else 0), values[i]["total"], -i))


def detect(g, score):
    events = [(1.0, 0, i["kind"], i["index"], "VAL:"+i["detail"]) for i in score["issues"]]
    events += [(1.0, 1, "edge", i, "COH") for i, p in enumerate(score["edge_judgments"]) if p == 0]
    events += [(1-v, 2, "node", i, "DENS") for i, v in score["coverage"].items() if v < 1]
    return sorted(set(events), key=lambda x: (-x[0], x[1], x[2], x[3], x[4]))


def actions(g, error, pool, corpus, local_rerun=None, fix_components=False):
    _, _, kind, index, reason = error
    if kind == "edge":
        if index >= len(g["relations"]):
            return
        e = g["relations"][index]
        changed = deepcopy(g); changed["relations"].pop(index)
        yield "RemoveEdge", changed
        if local_rerun is not None and e["source"] in {c["id"] for c in g["components"]}:
            yield "LocalRerun", local_rerun(g, [e["source"]])
        return
    if index >= len(g["components"]):
        return
    current = g["components"][index]
    # Exact type-first output and overlapping-span matching are NEW explicit choices.
    if not fix_components and corpus == "aaec" and current["type"] in {"Claim", "MajorClaim"}:
        changed = deepcopy(g)
        changed["components"][index]["type"] = "MajorClaim" if current["type"] == "Claim" else "Claim"
        yield "Promote/Demote", changed
    replacements = []
    for candidate in ([] if fix_components else pool):
        for c in candidate["components"]:
            overlap = max(0, min(c["span"][1], current["span"][1])-max(c["span"][0], current["span"][0])+1)
            union = max(c["span"][1], current["span"][1])-min(c["span"][0], current["span"][0])+1
            if overlap and (c["span"] != current["span"] or c["type"] != current["type"]):
                replacements.append((-overlap/union, c["span"][0], c["span"][1], c["type"]))
    for _, start, end, typ in sorted(set(replacements)):
        changed = deepcopy(g)
        changed["components"][index] = {"id": current["id"], "type": typ, "span": [start, end]}
        yield "Replace", changed
    if local_rerun is not None:
        # For a low-coverage target, choose finite possible sources in text order.
        sources = [c["id"] for c in g["components"] if c["id"] != current["id"]]
        if sources:
            yield "LocalRerun", local_rerun(g, sources)


def repair(initial, pool, scorer, local_rerun=None):
    g = deepcopy(initial)
    cfg = scorer.config
    scorer.begin_repair(initial)
    score = scorer.score(g)
    history, attempts, accepted_total = [], 0, 0
    visited = {fingerprint(g)}
    attempted = set()
    termination = "round_limit"
    for round_no in range(1, cfg["rounds"]+1):
        accepted = 0
        while accepted < cfg["accepted_per_round"]:
            errors = detect(g, score)
            if not errors:
                termination = "no_anomalies"; break
            progress = False
            for error in errors:
                iterator = actions(g, error, pool, scorer.corpus, local_rerun,
                                   cfg.get("fix_components", False))
                for _ in range(cfg["actions_per_error"]):
                    if attempts >= cfg["max_attempts"]:
                        return g, history, "attempt_limit"
                    try:
                        name, candidate = next(iterator)
                    except StopIteration:
                        break
                    except (BudgetExceeded, ValueError) as exc:
                        attempts += 1
                        history.append({"round": round_no, "attempt": attempts, "action": "LocalRerun",
                                        "accepted": False, "reason": type(exc).__name__+": "+str(exc)})
                        if isinstance(exc, BudgetExceeded):
                            return g, history, "model_budget_exhausted"
                        break
                    attempts += 1
                    key = (fingerprint(g), fingerprint(candidate))
                    entry = {"round": round_no, "attempt": attempts, "action": name,
                             "error": list(error), "before_sha256": key[0], "candidate_sha256": key[1],
                             "before_score": score["total"], "accepted": False}
                    history.append(entry)
                    if cfg.get("fix_components", False) and candidate["components"] != initial["components"]:
                        entry["reason"] = "fixed_components_changed"; continue
                    if key in attempted or key[1] in visited:
                        entry["reason"] = "duplicate_or_visited"; continue
                    attempted.add(key)
                    bad = issues(candidate, len(scorer.doc["tokens"]), scorer.corpus, cfg["require_acyclic"])
                    if bad:
                        entry["reason"] = "candidate_not_fully_valid"; continue
                    try:
                        next_score = scorer.score(candidate)
                    except (BudgetExceeded, ValueError) as exc:
                        entry["reason"] = type(exc).__name__+": "+str(exc)
                        if isinstance(exc, BudgetExceeded):
                            return g, history, "model_budget_exhausted"
                        continue
                    entry["candidate_score"] = next_score["total"]
                    if cfg.get("require_new_edge_support", False):
                        old_edges = {(e["source"], e["target"], e["type"]) for e in g["relations"]}
                        unsupported = any(
                            (e["source"], e["target"], e["type"]) not in old_edges and judgment != 1
                            for e, judgment in zip(candidate["relations"], next_score["edge_judgments"]))
                        if unsupported:
                            entry["reason"] = "new_edge_not_supported"; continue
                    if cfg.get("strict_improvement", False) and next_score["total"] <= score["total"]+1e-12:
                        entry["reason"] = "no_strict_improvement"; continue
                    if next_score["total"]+1e-12 < score["total"]:
                        entry["reason"] = "score_decreased"; continue
                    entry.update(accepted=True, reason="accepted")
                    entry.update(before_graph=deepcopy(g), after_graph=deepcopy(candidate))
                    g, score = candidate, next_score
                    visited.add(key[1]); accepted += 1; accepted_total += 1
                    progress = True
                    break
                if progress:
                    break
            if not progress:
                termination = "no_acceptable_action"; break
        if accepted == 0 or termination == "no_anomalies":
            break
    assert accepted_total <= cfg["rounds"]*cfg["accepted_per_round"]
    return g, history, termination
