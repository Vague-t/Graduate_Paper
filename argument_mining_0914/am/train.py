"""Single-device training; fixed split, response-only loss, dev-only selection."""
import math
import random
from pathlib import Path
import torch
from .model import load_local, seed_all, encode_example
from .data import split_audit
from .io import read_jsonl, dump, jsonl, manifest, fresh_dir


def train(config, train_path, dev_path, out_path):
    train_docs, dev_docs = read_jsonl(train_path), read_jsonl(dev_path)
    if not train_docs or not dev_docs:
        raise ValueError("Nonempty training and development sets required")
    if any(d["split"] != "train" for d in train_docs) or any(d["split"] != "dev" for d in dev_docs):
        raise ValueError("Training accepts train/dev only, never test documents")
    if any(d["corpus"] != config["corpus"] for d in train_docs+dev_docs):
        raise ValueError("Training corpus must match config")
    split_audit(train_docs+dev_docs)
    seed_all(config["seed"])
    model, identity = load_local(config)
    if config["training"]["gradient_checkpointing"]:
        model.base.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    examples = [encode_example(model.tokenizer, d, config, task) for d in train_docs for task in config["training"]["tasks"]]
    development = [encode_example(model.tokenizer, d, config, task) for d in dev_docs for task in config["training"]["tasks"]]
    params = [p for p in model.parameters() if p.requires_grad]
    if not params:
        raise ValueError("No trainable modules enabled")
    out = fresh_dir(out_path)
    meta = manifest(config, [train_path, dev_path])
    meta.update(base_model_sha256=identity, trainable_parameters=sum(p.numel() for p in params),
                train_examples=len(examples), dev_examples=len(development),
                micro_batch=1, effective_example_batch=config["training"]["gradient_accumulation"],
                checkpoint_selection="minimum_development_generation_loss", torch_version=torch.__version__)
    dump(out/"manifest.json", meta)
    optimizer = torch.optim.AdamW(params, lr=config["training"]["learning_rate"], weight_decay=config["training"]["weight_decay"])
    best, stale, step, records = float("inf"), 0, 0, []
    accumulation = config["training"]["gradient_accumulation"]
    step_limit = config["training"]["max_optimizer_steps"]
    termination = "epoch_limit"
    for epoch in range(config["training"]["epochs"]):
        model.train()
        order = list(range(len(examples))); random.Random(config["seed"]+epoch).shuffle(order)
        totals = []
        for start in range(0, len(order), accumulation):
            if step_limit is not None and step >= step_limit:
                break
            group = order[start:start+accumulation]
            optimizer.zero_grad(set_to_none=True)
            for index in group:
                losses = model(examples[index])
                if not torch.isfinite(losses["loss"]):
                    raise FloatingPointError("Nonfinite loss; run aborted, not retried")
                (losses["loss"]/len(group)).backward()
                totals.append({k: float(v.detach()) for k, v in losses.items()})
            torch.nn.utils.clip_grad_norm_(params, config["training"]["max_grad_norm"])
            optimizer.step(); step += 1
        model.eval()
        with torch.no_grad():
            dev_loss = sum(float(model(e)["gen_loss"]) for e in development)/len(development)
        record = {"epoch": epoch+1, "optimizer_step": step, "train_loss": sum(v["loss"] for v in totals)/len(totals), "dev_generation_loss": dev_loss}
        records.append(record); jsonl(out/"training_log.jsonl", records)
        print(record, flush=True)
        if dev_loss < best:
            best, stale = dev_loss, 0
            model.save_adapter(out/"best", identity)
            dump(out/"best_selection.json", record)
        else:
            stale += 1
        if step_limit is not None and step >= step_limit:
            termination = "optimizer_step_limit"
            break
        if config["training"]["early_stopping"] and stale >= config["training"]["patience"]:
            termination = "early_stopping"
            break
    meta.update(status="completed", optimizer_steps=step, epochs_completed=len(records), termination=termination,
                cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_available() and config["model"]["device"] == "cuda" else None)
    dump(out/"manifest.json", meta)
    return meta
