"""Materialize reviewable NEW-run configs; never launch an experiment."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from am.config import load, merge, validate
from am.io import dump

root = Path(__file__).resolve().parents[1]/"configs"
full = {"claim_lora": True, "cue_prompt": True, "auxiliary": True}
definitions = {
    "aaec_baseline_single": {"inference": {"strategy": "single_pass"}},
    "aaec_full_single": {"modules": full, "inference": {"strategy": "single_pass"}},
    "aaec_full_staged_k1": {"modules": full, "inference": {"strategy": "staged_k1", "candidates": 1}},
    "aaec_full_logprob_k3": {"modules": full, "inference": {"strategy": "logprob"}},
    "aaec_full_rerank_k3": {"modules": full, "inference": {"strategy": "rerank"}},
    "aaec_full_br_k3": {"modules": full},
    "aaec_no_claim": {"modules": {**full, "claim_lora": False}},
    "aaec_no_cue": {"modules": {**full, "cue_prompt": False}},
    "aaec_no_auxiliary": {"modules": {**full, "auxiliary": False}},
    "aaec_global_rank32": {"modules": {**full, "claim_lora": False, "rank": 32, "alpha": 64}},
    "aaec_no_density": {"modules": full, "inference": {"weights": [0.0, 0.4, 0.2]}},
    "aaec_no_coherence": {"modules": full, "inference": {"weights": [0.4, 0.0, 0.2]}},
    "aaec_no_validity_score": {"modules": full, "inference": {"weights": [0.4, 0.4, 0.0]}},
    "aaec_valid_first": {"modules": full, "inference": {"selection": "valid_first"}},
    "cdcp_full_br_k3": {"corpus": "cdcp", "modules": full},
    "aaec_to_cdcp": {"modules": full, "evaluation": {"coarse": True, "endpoint_types": True}},
    "augment_structure": {"augmentation": {"strategy": "structure"}},
    "augment_plain": {"augmentation": {"strategy": "plain"}},
    "augment_random_plain": {"augmentation": {"strategy": "plain", "center_policy": "random"}},
    "augment_random_structure": {"augmentation": {"strategy": "structure", "center_policy": "random"}},
    "aaec_br_conservative": {"modules": full, "inference": {"fix_components": True, "freeze_coverage": True, "strict_improvement": True, "require_new_edge_support": True}},
    "aaec_br_fixed_components_only": {"modules": full, "inference": {"fix_components": True}},
    "aaec_br_frozen_coverage_only": {"modules": full, "inference": {"freeze_coverage": True}},
    "aaec_br_both_frozen": {"modules": full, "inference": {"fix_components": True, "freeze_coverage": True}},
    "aaec_controls_train_single": {"modules": full, "training": {"epochs": 100, "max_optimizer_steps": 1000, "early_stopping": False, "eval_every_steps": 100}, "inference": {"strategy": "single_pass"}},
}
for name, changes in definitions.items():
    resolved = validate(merge(merge(load(), {"model": {"device": "cuda", "dtype": "bfloat16"}}), changes))
    dump(root/(name+".json"), resolved)
dump(root/"cpu_inspection.json", load())
print(f"Wrote {len(definitions)+1} configs. No experiments launched.")
