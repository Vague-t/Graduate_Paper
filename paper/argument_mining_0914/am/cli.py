"""Run `python -m am --help` from the project directory."""
import argparse
import statistics
import sys
from pathlib import Path
from . import config
from .io import read_jsonl, read_json, dump, jsonl, manifest, fresh_dir, fingerprint, file_hash
from .data import prepare, stats, split_audit
from .metrics import evaluate


def load_backend(cfg, checkpoint=None):
    from .model import load_local, HFBackend, seed_all
    seed_all(cfg["seed"])
    model, identity = load_local(cfg, checkpoint)
    # Newly initialized nonzero soft prompts/classifiers must not masquerade as trained.
    if not checkpoint and any(cfg["modules"][k] for k in ("claim_lora", "cue_prompt", "auxiliary")):
        raise ValueError("Enabled research modules require --checkpoint; use a trained adapter")
    return HFBackend(model, identity, checkpoint)


def infer(args):
    from .pipeline import infer_document
    cfg = config.load(args.config)
    docs = read_jsonl(args.input)
    split_audit(docs)
    if len({d["split"] for d in docs}) != 1:
        raise ValueError("Inference input must be one named split")
    backend = load_backend(cfg, args.checkpoint)
    cached = None
    if args.cache:
        if cfg["inference"]["strategy"] in {"single_pass", "staged_k1"}:
            raise ValueError("Single-pass/staged-k1 cannot be inferred from a multi-candidate cache")
        cache_rows = read_jsonl(args.cache)
        if len({r["id"] for r in cache_rows}) != len(cache_rows) or {r["id"] for r in cache_rows} != {d["id"] for d in docs}:
            raise ValueError("Candidate cache document IDs mismatch")
        for row in cache_rows:
            if row.get("generator_identity") != backend.identity or row.get("generation_config") != cfg["generation"] or row.get("generation_seed") != cfg["seed"] or row.get("prediction_schema") != cfg["corpus"] or row.get("requested_candidates") != cfg["inference"]["candidates"]:
                raise ValueError("Cached generation identity/config differs; do not mix checkpoints or pools")
        cached = {r["id"]: r for r in cache_rows}
    out = fresh_dir(args.out)
    meta = manifest(cfg, [args.input]+([args.cache] if args.cache else []))
    meta.update(backend_identity=backend.identity, checkpoint=args.checkpoint, status="running",
                cache_reused=bool(args.cache), gold_used_in_inference=False)
    if args.checkpoint:
        parent_path = Path(args.checkpoint).parent/"manifest.json"
        parent = read_json(parent_path)
        if parent.get("status") != "completed":
            raise ValueError("Checkpoint must belong to a completed training run")
        meta["training_binding"] = {"config_without_seed": {k:v for k,v in parent["config"].items() if k != "seed"},
                                    "input_sha256": parent["input_sha256"], "base_model_sha256": parent["base_model_sha256"]}
        meta["training_seed"] = parent["config"]["seed"]
        if meta["training_seed"] != cfg["seed"]:
            raise ValueError("Training and inference seeds must match this experiment matrix")
    else:
        meta["training_binding"] = None
    dump(out/"manifest.json", meta)
    traces = []
    for doc in docs:
        trace = infer_document(doc, cfg, backend, cached.get(doc["id"]) if cached else None)
        trace.update(generator_identity=backend.identity, generation_config=cfg["generation"],
                     generation_seed=cfg["seed"], prediction_schema=cfg["corpus"], requested_candidates=cfg["inference"]["candidates"])
        traces.append(trace)
        jsonl(out/"traces.jsonl", traces)
        jsonl(out/"candidates.jsonl", [{k: r[k] for k in ("id", "document_sha256", "candidates", "generator_identity", "generation_config", "generation_seed", "prediction_schema", "requested_candidates", "generation_usage") if k in r} for r in traces])
        jsonl(out/"predictions.jsonl", [{"id": r["id"], "status": r["status"], "graph": r["graph"]} for r in traces])
        print(f"{doc['id']}: {trace['status']} ({trace['usage']['calls']} calls)", flush=True)
    meta.update(status="completed", completed_documents=len(traces), failed_documents=sum(t["status"] != "ok" for t in traces),
                predictions_sha256=file_hash(out/"predictions.jsonl"))
    dump(out/"manifest.json", meta)
    return {"out": str(out), "documents": len(traces), "failures": meta["failed_documents"]}


def augment(args):
    from .augment import augment_document
    cfg = config.load(args.config)
    docs = read_jsonl(args.input)
    split_audit(docs)
    if any(d["split"] != "train" or d["corpus"] != cfg["corpus"] for d in docs):
        raise ValueError("Augmentation input must be matching-corpus training data")
    plan = None
    if getattr(args, "plan", None):
        from .controls import validate_plan, planned_for_document
        plan = read_json(args.plan)
        validate_plan(plan, docs)
        if cfg["seed"] != plan["seed"] or cfg["augmentation"]["variants_per_unit"] != 1 or cfg["augmentation"]["max_units_per_document"] < plan["max_pairs"]:
            raise ValueError("Planned runs require matching seed, one variant per unit and sufficient unit cap")
    backend = load_backend(cfg, args.checkpoint)
    out = fresh_dir(args.out)
    generated, logs, usage = [], [], []
    hashes = {fingerprint(d["text"]) for d in docs}
    for doc in docs:
        units = planned_for_document(plan, doc["id"], cfg["augmentation"]["center_policy"]) if plan else None
        new, log, costs = augment_document(doc, cfg, backend, units)
        for d in new:
            h = fingerprint(d["text"])
            if h in hashes:
                logs.append({"result_id": d["id"], "accepted": False, "reason": "global_text_duplicate"})
            else:
                generated.append(d); hashes.add(h)
        logs.extend(log); usage.append({"id": doc["id"], **costs})
    combined = docs+generated
    split_audit(combined)
    jsonl(out/"train.jsonl", combined); jsonl(out/"generated.jsonl", generated)
    jsonl(out/"augmentation_log.jsonl", logs); jsonl(out/"usage.jsonl", usage)
    dump(out/"statistics.json", stats(combined))
    dump(out/"manifest.json", {**manifest(cfg, [args.input]+([args.plan] if plan else [])), "backend_identity": backend.identity,
                              "status": "completed", "plan_sha256": fingerprint(plan) if plan else None,
                              "generated_sha256": file_hash(out/"generated.jsonl"),
                              "usage_sha256": file_hash(out/"usage.jsonl"),
                              "original_documents": len(docs), "accepted_augmented_documents": len(generated),
                              "actual_augmented_to_original_ratio": len(generated)/len(docs) if docs else 0,
                              "human_semantic_audit": "not_performed"})
    return {"out": str(out), "accepted": len(generated)}


def summarize(paths, output):
    runs = [read_json(p) for p in paths]
    if len(runs) < 2:
        raise ValueError("At least two independent run reports are needed for sample SD")
    bindings = [r["run_binding"] for r in runs]
    if len({b["seed"] for b in bindings}) != len(bindings):
        raise ValueError("Duplicate seeds: these are not independent seed runs")
    comparable = [{k: v for k, v in b.items() if k != "seed"} for b in bindings]
    if any(v != comparable[0] for v in comparable):
        raise ValueError("Different data, metric or non-seed configuration; cannot aggregate")
    result = {"n_runs": len(runs), "seeds": [b["seed"] for b in bindings], "uncertainty": "sample_standard_deviation_ddof1", "significance_test": "not_performed", "binding_without_seed": comparable[0]}
    for key in ("component", "relation"):
        values = [r[key]["f1"] for r in runs]
        result[key] = {"values": values, "mean": statistics.mean(values), "sample_sd": statistics.stdev(values)}
    dump(output, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="0914 argument mining NEW reference project")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="Convert raw AAEC/CDCP with explicit split IDs")
    p.add_argument("--corpus", choices=["aaec", "cdcp"], required=True); p.add_argument("--raw-dir", required=True)
    p.add_argument("--splits", required=True); p.add_argument("--out", required=True)
    p.add_argument("--multi-premise", choices=["reject", "expand"], default="reject")
    p = sub.add_parser("audit-data")
    p.add_argument("inputs", nargs="+"); p.add_argument("--out", required=True)
    p = sub.add_parser("config", help="Resolve and validate a configuration, no model needed")
    p.add_argument("--config"); p.add_argument("--out")
    for command in ("train", "infer", "augment"):
        p = sub.add_parser(command); p.add_argument("--config", required=True); p.add_argument("--out", required=True)
        if command == "train":
            p.add_argument("--train", required=True); p.add_argument("--dev", required=True)
        else:
            p.add_argument("--input", required=True); p.add_argument("--checkpoint")
            if command == "infer":
                p.add_argument("--cache", help="Frozen candidates.jsonl for matched-pool comparison")
            if command == "augment":
                p.add_argument("--plan", help="Frozen matched-center plan; train-only")
    p = sub.add_parser("plan-augmentation", help="Offline matched-center selection; does not generate text")
    p.add_argument("--input", required=True); p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=17); p.add_argument("--max-pairs", type=int, default=4)
    p.add_argument("--token-bin-width", type=int, default=32)
    p = sub.add_parser("match-augmentation", help="Retain the same jointly accepted pairs across four arms")
    p.add_argument("--original", required=True); p.add_argument("--plan", required=True)
    p.add_argument("--runs", nargs=4, required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("audit-repair", help="Offline gold-based before/after audit; never used in inference")
    p.add_argument("--gold", required=True); p.add_argument("--traces", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("evaluate")
    p.add_argument("--gold", required=True); p.add_argument("--predictions", required=True); p.add_argument("--out", required=True)
    p.add_argument("--coarse", action="store_true"); p.add_argument("--span-only-endpoints", action="store_true")
    p.add_argument("--run-manifest", help="Bind real outputs to a run for multi-seed summaries")
    p = sub.add_parser("summarize")
    p.add_argument("reports", nargs="+"); p.add_argument("--out", required=True)
    p = sub.add_parser("demo", help="Synthetic offline fixture only, never a benchmark")
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.corpus, args.raw_dir, args.splits, args.out, args.multi_premise)
        elif args.command == "audit-data":
            docs = [d for p in args.inputs for d in read_jsonl(p)]
            result = stats(docs); dump(args.out, result)
        elif args.command == "config":
            result = config.load(args.config)
            if args.out:
                dump(args.out, result)
        elif args.command == "train":
            from .train import train
            result = train(config.load(args.config), args.train, args.dev, args.out)
        elif args.command == "infer":
            result = infer(args)
        elif args.command == "augment":
            result = augment(args)
        elif args.command == "plan-augmentation":
            from .controls import make_plan
            result = make_plan(read_jsonl(args.input), args.seed, args.max_pairs, args.token_bin_width)
            out = fresh_dir(args.out)
            dump(out/"plan.json", result)
            dump(out/"manifest.json", {**manifest({"protocol": result["protocol"]}, [args.input]), "status": "completed", "generation": "NOT_RUN"})
        elif args.command == "match-augmentation":
            from .controls import match_runs
            result = match_runs(args.original, args.plan, args.runs, args.out)
        elif args.command == "audit-repair":
            from .repair_audit import audit_repair
            result = audit_repair(read_jsonl(args.gold), read_jsonl(args.traces))
            out = fresh_dir(args.out)
            dump(out/"audit.json", result)
            dump(out/"manifest.json", {**manifest({"protocol": result["protocol"]}, [args.gold, args.traces]), "status": "completed"})
        elif args.command == "evaluate":
            gold = read_jsonl(args.gold)
            result = evaluate(gold, read_jsonl(args.predictions), not args.span_only_endpoints, args.coarse)
            result["input_sha256"] = {"gold": file_hash(args.gold), "predictions": file_hash(args.predictions)}
            if args.run_manifest:
                meta = read_json(args.run_manifest)
                if meta.get("status") != "completed" or meta.get("predictions_sha256") != file_hash(args.predictions):
                    raise ValueError("Run manifest does not bind these completed predictions")
                if file_hash(args.gold) not in meta["input_sha256"].values():
                    raise ValueError("Gold/input file differs from the inference document artifact")
                cfg = meta["config"]
                comparable = {k: v for k, v in cfg.items() if k != "seed"}
                result["run_binding"] = {"seed": cfg["seed"], "configuration_without_seed_sha256": fingerprint(comparable),
                                         "gold_sha256": file_hash(args.gold), "protocol": result["protocol"],
                                         "source_sha256": meta["source_sha256"], "training_binding": meta.get("training_binding")}
                result["run_manifest_sha256"] = file_hash(args.run_manifest)
            dump(args.out, result)
        elif args.command == "summarize":
            result = summarize(args.reports, args.out)
        else:
            from .demo import demo
            result = demo(args.out)
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError, FileExistsError, KeyError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
