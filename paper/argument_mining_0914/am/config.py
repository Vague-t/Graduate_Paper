"""Versioned choices for NEW runs, never reconstructed historical settings."""
from copy import deepcopy
import math
from .io import read_json

DEFAULT = {
    "schema_version": "0914-reference-v1", "corpus": "aaec", "seed": 17,
    "model": {"path": "models/Qwen2.5-7B-Instruct", "device": "cpu", "dtype": "float32",
              "max_context": 8192, "local_files_only": True},
    "modules": {"global_lora": True, "claim_lora": False, "cue_prompt": False, "auxiliary": False,
                "rank": 16, "alpha": 32, "dropout": 0.05, "targets": ["q_proj", "v_proj"],
                "prompt_length": 4, "lambda_aux": 0.5,
                "cues": ["therefore", "thus", "in conclusion", "consequently", "hence", "to conclude"]},
    "training": {"epochs": 3, "learning_rate": 0.0002, "weight_decay": 0.01,
                 "gradient_accumulation": 8, "max_grad_norm": 1.0, "patience": 2,
                 "loss_reduction": "per_example_token_mean", "gradient_checkpointing": True,
                 "max_optimizer_steps": None, "early_stopping": True,
                 "tasks": ["components", "relations", "joint"]},
    "generation": {"max_new_tokens": 1024, "temperature": 0.7, "top_p": 0.9},
    "inference": {"strategy": "rerank_br", "candidates": 3, "require_acyclic": True,
                  "selection": "weighted", "weights": [0.4, 0.4, 0.2],
                  "root_threshold": 2, "other_threshold": 1,
                  "rounds": 3, "accepted_per_round": 2, "max_attempts": 24,
                  "actions_per_error": 4, "max_calls": 128, "max_total_output_tokens": 32768},
    "evaluation": {"endpoint_types": True, "coarse": False},
    "augmentation": {"variants_per_unit": 1, "attempts_per_unit": 2,
                     "max_units_per_document": 4, "max_calls": 128,
                     "max_total_output_tokens": 32768, "strategy": "structure"},
}

# Opt-in 0915 controls. Omitted fields preserve the original algorithm.
DEFAULT["inference"].update(fix_components=False, freeze_coverage=False,
                            strict_improvement=False, require_new_edge_support=False)
DEFAULT["augmentation"]["center_policy"] = "conclusion"
DEFAULT["training"]["eval_every_steps"] = None


def merge(base, update):
    if not isinstance(update, dict):
        raise ValueError("Configuration node must be an object")
    out = deepcopy(base)
    for key, value in update.items():
        if key not in base:
            raise ValueError(f"Unknown configuration field: {key}")
        out[key] = merge(base[key], value) if isinstance(base[key], dict) else value
    return out


def validate(c):
    if c["schema_version"] != DEFAULT["schema_version"] or c["corpus"] not in {"aaec", "cdcp", "coarse"}:
        raise ValueError("Unknown config/schema")
    if type(c["seed"]) is not int or not 0 <= c["seed"] < 2**32:
        raise ValueError("seed must be a uint32")
    for group, names in {"model": ["max_context"], "modules": ["rank", "alpha", "prompt_length"],
                         "training": ["epochs", "gradient_accumulation", "patience"],
                         "generation": ["max_new_tokens"],
                         "inference": ["candidates", "root_threshold", "other_threshold", "rounds", "accepted_per_round", "max_attempts", "actions_per_error", "max_calls", "max_total_output_tokens"],
                         "augmentation": ["variants_per_unit", "attempts_per_unit", "max_units_per_document", "max_calls", "max_total_output_tokens"]}.items():
        for key in names:
            if type(c[group][key]) is not int or c[group][key] <= 0:
                raise ValueError(f"{group}.{key} must be positive integer")
    for group, names in {"modules": ["global_lora", "claim_lora", "cue_prompt", "auxiliary"],
                         "model": ["local_files_only"], "inference": ["require_acyclic", "fix_components", "freeze_coverage", "strict_improvement", "require_new_edge_support"],
                         "evaluation": ["endpoint_types", "coarse"], "training": ["gradient_checkpointing", "early_stopping"]}.items():
        if any(type(c[group][key]) is not bool for key in names):
            raise ValueError(f"Invalid boolean in {group}")
    steps = c["training"]["max_optimizer_steps"]
    if steps is not None and (type(steps) is not int or steps <= 0):
        raise ValueError("training.max_optimizer_steps must be null or positive integer")
    cadence = c["training"]["eval_every_steps"]
    if cadence is not None and (type(cadence) is not int or cadence <= 0):
        raise ValueError("training.eval_every_steps must be null or positive integer")
    w = c["inference"]["weights"]
    if not isinstance(w, list) or len(w) != 3 or any(not isinstance(x, (float, int)) or not math.isfinite(x) or x < 0 for x in w) or not 0 < sum(w) <= 1.00000001:
        raise ValueError("Three nonnegative weights with sum in (0,1] are required")
    if c["inference"]["strategy"] not in {"single_pass", "staged_k1", "logprob", "rerank", "rerank_br"}:
        raise ValueError("Unknown inference strategy")
    if c["inference"]["selection"] not in {"weighted", "valid_first"}:
        raise ValueError("Unknown selection policy")
    if c["model"]["device"] not in {"cpu", "cuda", "mps"} or c["model"]["dtype"] not in {"float32", "bfloat16", "float16"}:
        raise ValueError("Unknown device/dtype")
    if c["model"]["device"] == "cpu" and c["model"]["dtype"] != "float32":
        raise ValueError("CPU reference path requires float32")
    if c["model"]["max_context"] <= c["generation"]["max_new_tokens"] + c["modules"]["prompt_length"]:
        raise ValueError("Context must reserve room for prompt and generated tokens")
    if c["training"]["loss_reduction"] != "per_example_token_mean":
        raise ValueError("Only the explicitly documented mean-reduction implementation is supported")
    if not c["training"]["tasks"] or len(set(c["training"]["tasks"])) != len(c["training"]["tasks"]) or not set(c["training"]["tasks"]) <= {"joint", "components", "relations"}:
        raise ValueError("Invalid training tasks")
    if not c["modules"]["targets"] or not all(isinstance(t, str) and t for t in c["modules"]["targets"]):
        raise ValueError("LoRA targets must be nonempty strings")
    for group, key, low, high in [("modules", "dropout", 0, 1), ("generation", "top_p", 0, 1), ("generation", "temperature", 0, 10), ("modules", "lambda_aux", 0, 100)]:
        value = c[group][key]
        if not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Invalid {group}.{key}")
    if c["generation"]["top_p"] == 0 or c["modules"]["dropout"] == 1:
        raise ValueError("top_p > 0 and dropout < 1 required")
    for key in ["learning_rate", "weight_decay", "max_grad_norm"]:
        value = c["training"][key]
        if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0 or (key != "weight_decay" and value == 0):
            raise ValueError(f"Invalid training.{key}")
    if c["augmentation"]["strategy"] not in {"structure", "plain"}:
        raise ValueError("Unknown augmentation strategy")
    if c["augmentation"]["center_policy"] not in {"conclusion", "random"}:
        raise ValueError("Unknown center policy")
    return c


def load(path=None):
    return validate(merge(DEFAULT, read_json(path) if path else {}))
