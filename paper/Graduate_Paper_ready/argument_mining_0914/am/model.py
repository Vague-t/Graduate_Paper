"""Local Hugging Face causal-LM path with explicit task modules.

This correctness-first implementation uses batch size one and uncached decoding
so training and inference share the same prefix-derived conditional gates.
It is not a speed-optimized inference engine or the lost historical code.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import math
import random
import torch
from torch import nn
from torch.nn import functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer
from safetensors.torch import load_file, save_file
from .backend import Generated
from .io import dump, read_json, fingerprint, file_hash
from .prompts import prompt, graph_text, claim_gate, cue_present, PROMPT_VERSION
from .schema import SCHEMAS


class GateContext:
    mask = None


class ConditionalLinear(nn.Module):
    def __init__(self, base, cfg, context):
        super().__init__()
        self.base, self.context = base, context
        self.scale = cfg["alpha"]/cfg["rank"]
        self.dropout = nn.Dropout(cfg["dropout"])
        self.branches = nn.ModuleDict()
        for name, active in (("global", cfg["global_lora"]), ("claim", cfg["claim_lora"])):
            if active:
                branch = nn.ModuleDict({"A": nn.Linear(base.in_features, cfg["rank"], bias=False, dtype=torch.float32, device=base.weight.device),
                                        "B": nn.Linear(cfg["rank"], base.out_features, bias=False, dtype=torch.float32, device=base.weight.device)})
                nn.init.kaiming_uniform_(branch["A"].weight, a=math.sqrt(5))
                nn.init.zeros_(branch["B"].weight)
                self.branches[name] = branch

    def forward(self, x):
        result = self.base(x)
        for name, branch in self.branches.items():
            delta = branch["B"](branch["A"](self.dropout(x.float()))) * self.scale
            if name == "claim":
                mask = self.context.mask
                if mask is None or tuple(mask.shape) != tuple(x.shape[:-1]):
                    raise RuntimeError("Conditional LoRA gate/sequence shape mismatch")
                delta = delta * mask.unsqueeze(-1)
            result = result + delta.to(result.dtype)
        return result


@dataclass
class Encoded:
    input_ids: list
    labels: list
    gates: list
    cue: bool
    sentence_positions: list
    sentence_labels: list


def output_gates(tokenizer, target_ids, corpus="aaec"):
    # Gate at each hidden-state position sees its token, not the target it predicts.
    types = ("MajorClaim", "Claim") if corpus == "aaec" else SCHEMAS[corpus]["conclusions"]
    return [claim_gate(tokenizer.decode(target_ids[:i+1], skip_special_tokens=False), types) for i in range(len(target_ids))]


def encode_example(tokenizer, doc, cfg, task):
    fixed = doc["graph"]["components"] if task == "relations" else None
    messages = prompt(doc, cfg["corpus"], task, components=fixed)
    rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    encoded_prompt = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True)
    target = {"components": doc["graph"]["components"], "relations": [] if task == "components" else doc["graph"]["relations"]}
    target_ids = tokenizer.encode(graph_text(target), add_special_tokens=False)
    if tokenizer.eos_token_id is None:
        raise ValueError("Tokenizer needs an explicit EOS token")
    target_ids.append(tokenizer.eos_token_id)
    prompt_ids = encoded_prompt["input_ids"]
    all_ids = prompt_ids+target_ids
    cue = cue_present(doc["text"], cfg["modules"]["cues"])
    extra = cfg["modules"]["prompt_length"] if cfg["modules"]["cue_prompt"] and cue else 0
    if len(all_ids)+extra > cfg["model"]["max_context"]:
        raise ValueError(f"{doc['id']} exceeds context; no silent text/label truncation")
    sentence_positions, labels = [], []
    if cfg["modules"]["auxiliary"]:
        escaped = json.dumps(doc["text"], ensure_ascii=False)[1:-1]
        marker = '"document": "'+escaped+'"'
        start = rendered.find(marker)
        if start < 0:
            raise ValueError("Cannot locate source-text region for auxiliary pooling")
        start += len('"document": "')
        for lo, hi in doc["sentences"]:
            a, b = doc["token_offsets"][lo-1][0], doc["token_offsets"][hi-1][1]
            a = start+len(json.dumps(doc["text"][:a], ensure_ascii=False)[1:-1])
            b = start+len(json.dumps(doc["text"][:b], ensure_ascii=False)[1:-1])
            positions = [i for i, (s, e) in enumerate(encoded_prompt["offset_mapping"]) if s < b and e > a and e > s]
            if not positions:
                raise ValueError("Sentence has no model tokens")
            sentence_positions.append(positions)
            labels.append(int(any(c["type"] in {"Claim", "MajorClaim", "Policy", "Value"} and max(lo, c["span"][0]) <= min(hi, c["span"][1]) for c in doc["graph"]["components"])))
    return Encoded(all_ids, [-100]*len(prompt_ids)+target_ids,
                   [0]*len(prompt_ids)+output_gates(tokenizer, target_ids, cfg["corpus"]), cue, sentence_positions, labels)


class GraphModel(nn.Module):
    def __init__(self, base, tokenizer, cfg):
        super().__init__()
        self.base, self.tokenizer, self.cfg = base, tokenizer, cfg
        self.gate_context = GateContext()
        for p in base.parameters():
            p.requires_grad_(False)
        modules = cfg["modules"]
        self.adapted_names = []
        if modules["global_lora"] or modules["claim_lora"]:
            all_modules = dict(base.named_modules())
            matched = {suffix: 0 for suffix in modules["targets"]}
            for name, layer in list(all_modules.items()):
                suffixes = [s for s in modules["targets"] if name.endswith("."+s)]
                if suffixes and isinstance(layer, nn.Linear):
                    parent, attr = name.rsplit(".", 1)
                    setattr(all_modules[parent], attr, ConditionalLinear(layer, modules, self.gate_context))
                    self.adapted_names.append(name)
                    for suffix in suffixes:
                        matched[suffix] += 1
            if not all(matched.values()):
                raise ValueError(f"Unmatched LoRA targets: {matched}")
        hidden = base.config.hidden_size
        device = next(base.parameters()).device
        self.soft_prompt = nn.Parameter(torch.empty(modules["prompt_length"], hidden, dtype=torch.float32, device=device)) if modules["cue_prompt"] else None
        if self.soft_prompt is not None:
            nn.init.normal_(self.soft_prompt, std=0.02)
        self.aux_head = nn.Linear(hidden, 1, device=device, dtype=torch.float32) if modules["auxiliary"] else None

    @property
    def device(self):
        return next(self.base.parameters()).device

    def forward(self, encoded, with_loss=True):
        ids = torch.tensor([encoded.input_ids], dtype=torch.long, device=self.device)
        embedded = self.base.get_input_embeddings()(ids)
        gates = torch.tensor([encoded.gates], dtype=embedded.dtype, device=self.device)
        extra = 0
        if self.soft_prompt is not None and encoded.cue:
            extra = self.soft_prompt.shape[0]
            embedded = torch.cat([self.soft_prompt.to(embedded.dtype).unsqueeze(0), embedded], dim=1)
            gates = torch.cat([torch.zeros(1, extra, dtype=gates.dtype, device=gates.device), gates], dim=1)
        self.gate_context.mask = gates
        output = self.base(inputs_embeds=embedded, attention_mask=torch.ones(embedded.shape[:2], dtype=torch.long, device=self.device),
                           use_cache=False, output_hidden_states=bool(self.aux_head is not None and with_loss), return_dict=True)
        if not with_loss:
            return output.logits[:, -1, :]
        labels = torch.tensor([[-100]*extra+encoded.labels], device=self.device)
        shifted = labels[:, 1:]
        if not (shifted != -100).any():
            raise ValueError("No supervised response tokens")
        gen_loss = F.cross_entropy(output.logits[:, :-1, :].float().reshape(-1, output.logits.size(-1)), shifted.reshape(-1), ignore_index=-100, reduction="mean")
        aux_loss = gen_loss.new_zeros(())
        if self.aux_head is not None and encoded.sentence_positions:
            hidden = output.hidden_states[-1][0]
            pooled = torch.stack([hidden[torch.tensor(positions, device=self.device)+extra].float().mean(0) for positions in encoded.sentence_positions])
            logits = self.aux_head(pooled).squeeze(-1)
            aux_loss = F.binary_cross_entropy_with_logits(logits, torch.tensor(encoded.sentence_labels, dtype=logits.dtype, device=self.device), reduction="mean")
        return {"loss": gen_loss+self.cfg["modules"]["lambda_aux"]*aux_loss, "gen_loss": gen_loss, "aux_loss": aux_loss}

    def trainable_state(self):
        return {n: p.detach().cpu().contiguous() for n, p in self.named_parameters() if p.requires_grad}

    def save_adapter(self, directory, provenance):
        directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
        save_file(self.trainable_state(), str(directory/"adapter.safetensors"))
        dump(directory/"adapter_config.json", {"modules": self.cfg["modules"], "prompt_version": PROMPT_VERSION,
                                              "model_identity": provenance, "loss_reduction": self.cfg["training"]["loss_reduction"],
                                              "trainable_parameters": sum(p.numel() for p in self.parameters() if p.requires_grad),
                                              "adapted_layers": self.adapted_names})

    def load_adapter(self, directory, model_identity):
        directory = Path(directory)
        meta = read_json(directory/"adapter_config.json")
        if meta["modules"] != self.cfg["modules"] or meta["prompt_version"] != PROMPT_VERSION or meta["model_identity"] != model_identity:
            raise ValueError("Checkpoint base model, modules or prompt version differs")
        values = load_file(str(directory/"adapter.safetensors"), device="cpu")
        expected = {n for n, p in self.named_parameters() if p.requires_grad}
        if set(values) != expected:
            raise ValueError("Adapter tensor names differ from implementation")
        params = dict(self.named_parameters())
        with torch.no_grad():
            for name, tensor in values.items():
                if tensor.shape != params[name].shape:
                    raise ValueError(f"Adapter shape mismatch: {name}")
                params[name].copy_(tensor.to(params[name].device))


def load_local(cfg, adapter=None):
    settings = cfg["model"]
    path = Path(settings["path"])
    if not settings["local_files_only"]:
        raise ValueError("This project loads local weights only; download them separately with explicit consent")
    if not path.is_dir():
        raise FileNotFoundError(f"Local model directory not found: {path}. No model is downloaded automatically.")
    # Strong binding rather than a model-name-only provenance record.
    selected = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix in {".json", ".safetensors", ".bin", ".model", ".txt"})
    identity = fingerprint({str(p.relative_to(path)): file_hash(p) for p in selected})
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False, use_fast=True)
    if not tokenizer.is_fast or not tokenizer.chat_template:
        raise ValueError("A fast tokenizer with chat template is required")
    dtype = getattr(torch, settings["dtype"])
    if settings["device"] == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if settings["device"] == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS requested but unavailable")
    base = AutoModelForCausalLM.from_pretrained(path, local_files_only=True, trust_remote_code=False,
                                               torch_dtype=dtype, attn_implementation="sdpa").to(settings["device"])
    model = GraphModel(base, tokenizer, cfg)
    if adapter:
        model.load_adapter(adapter, identity)
    return model, identity


def seed_all(seed):
    random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class HFBackend:
    def __init__(self, model, base_identity, adapter=None):
        self.model = model.eval()
        self.tokenizer = model.tokenizer
        self.identity = fingerprint({"base": base_identity, "modules": model.cfg["modules"],
                                     "adapter": file_hash(Path(adapter)/"adapter.safetensors") if adapter else None,
                                     "prompt_version": PROMPT_VERSION})

    @torch.no_grad()
    def generate(self, messages, config, model_context=None):
        rendered = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        prompt_ids = self.tokenizer.encode(rendered, add_special_tokens=False)
        target_ids = []
        doc = (model_context or {}).get("doc", {})
        cue = cue_present(doc.get("text", ""), self.model.cfg["modules"]["cues"])
        extra = self.model.cfg["modules"]["prompt_length"] if self.model.soft_prompt is not None and cue else 0
        if len(prompt_ids)+config["max_new_tokens"]+extra > self.model.cfg["model"]["max_context"]:
            raise ValueError("Input plus generation reservation exceeds context; no silent truncation")
        gates, logprob_sum, reason = [], 0.0, "length"
        for _ in range(config["max_new_tokens"]):
            encoded = Encoded(prompt_ids+target_ids, [], [0]*len(prompt_ids)+gates, cue, [], [])
            logits = self.model(encoded, with_loss=False)[0].float()
            model_logp = F.log_softmax(logits, dim=-1)
            if config["temperature"] <= 0:
                token = int(logits.argmax())
            else:
                probabilities = torch.softmax(logits/config["temperature"], dim=-1)
                ordered, indices = torch.sort(probabilities, descending=True)
                remove = torch.cumsum(ordered, dim=-1)-ordered > config["top_p"]
                ordered[remove] = 0
                token = int(indices[torch.multinomial(ordered/ordered.sum(), 1)])
            logprob_sum += float(model_logp[token])
            target_ids.append(token)
            types = ("MajorClaim", "Claim") if self.model.cfg["corpus"] == "aaec" else SCHEMAS[self.model.cfg["corpus"]]["conclusions"]
            gates.append(claim_gate(self.tokenizer.decode(target_ids, skip_special_tokens=False), types) if model_context else 0)
            if token == self.tokenizer.eos_token_id:
                reason = "eos"; break
        return Generated(self.tokenizer.decode(target_ids, skip_special_tokens=True), len(prompt_ids)+extra,
                         len(target_ids), logprob_sum, reason)
