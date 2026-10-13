"""Train-only paired augmentation controls; no model loading or gold test access."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import random
from .augment import center_units, is_conclusion
from .data import split_audit, stats
from .io import fingerprint, read_json, read_jsonl, dump, jsonl, fresh_dir, manifest, file_hash

ARMS = {"A1": ("conclusion", "plain"), "A2": ("conclusion", "structure"),
        "A3": ("random", "structure"), "A4": ("random", "plain")}


def footprint(doc, item, width):
    ids = set(item["unit"])
    lengths = sum(c["span"][1]-c["span"][0]+1 for c in doc["graph"]["components"] if c["id"] in ids)
    edges = sum(e["source"] in ids and e["target"] in ids for e in doc["graph"]["relations"])
    return {"components": len(ids), "relations": edges, "token_bin": lengths//width,
            "original_slot_tokens": lengths}


def make_plan(docs, seed=17, max_pairs=4, token_bin_width=32):
    split_audit(docs)
    if not docs or any(d["split"] != "train" or "augmentation" in d for d in docs):
        raise ValueError("Plan requires nonempty original training documents only")
    if len({d["corpus"] for d in docs}) != 1:
        raise ValueError("One corpus per plan required")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Seed must be a uint32")
    if any(type(n) is not int or n < 1 for n in (max_pairs, token_bin_width)):
        raise ValueError("Pair count and bin width must be positive integers")
    pairs, exclusions = [], []
    for doc in docs:
        rng = random.Random(fingerprint([seed, doc["id"], "matched-centers-v1"]))
        units = list(center_units(doc))
        anchors = [u for u in units if is_conclusion(doc, u)]
        rng.shuffle(anchors)
        used = set()
        for anchor in anchors[:max_pairs]:
            shape = footprint(doc, anchor, token_bin_width)
            candidates = [u for u in units if u["center_id"] not in used and all(
                footprint(doc, u, token_bin_width)[k] == shape[k]
                for k in ("components", "relations", "token_bin"))]
            # Same center is intentionally eligible: random does not mean non-conclusion.
            if not candidates:
                exclusions.append({"document_id": doc["id"], "center_id": anchor["center_id"], "reason": "no_unused_matched_random_center"})
                continue
            selected = rng.choice(candidates)
            used.add(selected["center_id"])
            pair_id = fingerprint([doc["id"], anchor["center_id"], seed])
            pairs.append({"pair_id": pair_id, "document_id": doc["id"], "source_id": doc["source_id"],
                          "conclusion": anchor, "random": selected, "eligible_random_centers": len(candidates),
                          "conclusion_footprint": shape, "random_footprint": footprint(doc, selected, token_bin_width),
                          "random_is_conclusion": is_conclusion(doc, selected),
                          "same_center": anchor["center_id"] == selected["center_id"],
                          "same_unit": anchor["unit"] == selected["unit"]})
        if not anchors:
            exclusions.append({"document_id": doc["id"], "reason": "no_conclusion_center"})
    return {"protocol": "matched-centers-v1", "seed": seed, "max_pairs": max_pairs,
            "token_bin_width": token_bin_width, "input_documents_sha256": fingerprint(docs),
            "corpus": docs[0]["corpus"], "pairs": pairs, "exclusions": exclusions,
            "random_sampling": "uniform among unused same-document size/edge-count/token-bin matched centers; conclusions included",
            "formal_experiments": "NOT_RUN"}


def validate_plan(plan, docs):
    expected = make_plan(docs, plan["seed"], plan["max_pairs"], plan["token_bin_width"])
    if plan != expected:
        raise ValueError("Plan does not replay exactly against these original documents")


def planned_for_document(plan, doc_id, policy):
    return [{**p[policy], "pair_id": p["pair_id"]} for p in plan["pairs"] if p["document_id"] == doc_id]


def match_runs(original_path, plan_path, run_paths, out_path):
    docs, plan = read_jsonl(original_path), read_json(plan_path)
    validate_plan(plan, docs)
    if len(run_paths) != 4:
        raise ValueError("Provide exactly four completed augmentation runs (A1-A4)")
    pairs = {p["pair_id"]: p for p in plan["pairs"]}
    originals = {d["id"]: d for d in docs}
    arms, bindings, input_paths, reports = {}, [], [original_path, plan_path], {}
    for directory in run_paths:
        root = Path(directory)
        meta = read_json(root/"manifest.json")
        cfg = meta["config"]
        settings = cfg["augmentation"]
        arm = next((a for a, v in ARMS.items() if v == (settings["center_policy"], settings["strategy"])), None)
        if arm is None or arm in arms:
            raise ValueError("Duplicate or unknown augmentation arm")
        if meta.get("status") != "completed" or meta.get("plan_sha256") != fingerprint(plan):
            raise ValueError("Run not completed or bound to this plan")
        if meta.get("generated_sha256") != file_hash(root/"generated.jsonl"):
            raise ValueError("Generated artifact hash mismatch")
        if meta.get("usage_sha256") != file_hash(root/"usage.jsonl"):
            raise ValueError("Usage artifact hash mismatch")
        normalized = deepcopy(cfg)
        normalized["augmentation"].pop("center_policy")
        normalized["augmentation"].pop("strategy")
        bindings.append({"config": normalized, "backend": meta["backend_identity"], "source": meta["source_sha256"]})
        rows = read_jsonl(root/"generated.jsonl")
        split_audit(rows)
        by_pair = {}
        hashes = {fingerprint(d["text"]) for d in docs}
        for row in rows:
            info = row["augmentation"]
            pid = info.get("pair_id")
            if pid not in pairs or pid in by_pair:
                raise ValueError("Unknown/duplicate accepted pair ID")
            pair = pairs[pid]; original = originals[pair["document_id"]]
            unit = pair[settings["center_policy"]]
            if any(info.get(k) != v for k, v in unit.items()) or info.get("parent_id") != original["id"]:
                raise ValueError("Accepted augmentation does not match planned slots")
            if (row["source_id"] != original["source_id"] or row["split"] != "train"
                    or row["corpus"] != original["corpus"]
                    or info.get("center_policy") != settings["center_policy"]
                    or info.get("strategy") != settings["strategy"]
                    or info.get("backend") != meta["backend_identity"]
                    or info.get("parent_text_sha256") != fingerprint(original["text"])
                    or row["graph"]["relations"] != original["graph"]["relations"]
                    or [(c["id"], c["type"]) for c in row["graph"]["components"]] != [(c["id"], c["type"]) for c in original["graph"]["components"]]):
                raise ValueError("Augmentation provenance/topology mismatch")
            h = fingerprint(row["text"])
            if h in hashes:
                raise ValueError("Duplicate accepted text in arm")
            hashes.add(h); by_pair[pid] = row
        arms[arm] = by_pair
        usage = read_jsonl(root/"usage.jsonl")
        reports[arm] = {"accepted_before_matching": len(rows),
                        "calls_all_attempts": sum(x["calls"] for x in usage),
                        "output_tokens_all_attempts": sum(x["output_tokens_charged"] for x in usage)}
        input_paths += [root/"manifest.json", root/"generated.jsonl", root/"usage.jsonl"]
    if any(b != bindings[0] for b in bindings):
        raise ValueError("Arms differ beyond center/strategy (config/backend/code)")
    retained = sorted(set.intersection(*(set(v) for v in arms.values())))
    if not retained:
        raise ValueError("No jointly accepted pairs; refusing to label original-only files as matched augmentation")
    out = fresh_dir(out_path)
    jsonl(out/"A0"/"train.jsonl", docs)
    for arm, rows in arms.items():
        selected = [rows[p] for p in retained]
        combined = docs+selected
        split_audit(combined)
        jsonl(out/arm/"train.jsonl", combined)
        dump(out/arm/"statistics.json", stats(combined))
        reports[arm].update(retained=len(selected), dropped_after_matching=len(rows)-len(selected),
                           dataset_tokens=sum(len(d["tokens"]) for d in combined))
    dropped = [{"pair_id": p, "missing_arms": [a for a in ARMS if p not in arms[a]]}
               for p in pairs if p not in retained]
    report = {"planned_pairs": len(pairs), "jointly_accepted_pairs": len(retained), "arms": reports,
              "retained_pair_ids": retained, "dropped_pairs": dropped,
              "retained_per_document": dict(Counter(pairs[p]["document_id"] for p in retained)),
              "same_center_pairs": sum(pairs[p]["same_center"] for p in retained),
              "same_unit_pairs": sum(pairs[p]["same_unit"] for p in retained),
              "random_conclusion_pairs": sum(pairs[p]["random_is_conclusion"] for p in retained),
              "human_semantic_audit": "NOT_PERFORMED", "training": "NOT_RUN",
              "limitations": ["Joint acceptance selects a subset; inspect differential rejection.",
                              "Matched original token bins do not equal generated tokens or FLOPs.",
                              "Random arms may have identical centers; inspect effective contrast."]}
    dump(out/"matching_report.json", report)
    dump(out/"manifest.json", {**manifest({"protocol": "matched-centers-v1"}, input_paths),
                              "status": "completed", "training": "NOT_RUN",
                              "output_sha256": {a: file_hash(out/a/"train.jsonl") for a in ["A0", *ARMS]}})
    return report
