"""Actual tensor tests with a randomly initialized tiny Qwen2, no downloads."""
import copy
import tempfile
import unittest
from pathlib import Path
try:
    import torch
    from transformers import Qwen2Config, Qwen2ForCausalLM, PreTrainedTokenizerFast
    from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "Optional ML dependencies not installed")
class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from am.config import load, merge, validate
        from am.demo import fixture
        from am.prompts import prompt, graph_text
        torch.set_num_threads(1)
        cls.cfg = validate(merge(load(), {"modules": {"claim_lora": True, "cue_prompt": True, "auxiliary": True, "rank": 2, "alpha": 4, "dropout": 0.0}, "model": {"max_context": 4096}}))
        cls.doc = fixture(); cls.doc["split"] = "train"
        cls.doc["text"] = cls.doc["text"].replace("Libraries", "Therefore")
        from am.schema import tokenize, sentence_spans
        cls.doc["tokens"], cls.doc["token_offsets"] = tokenize(cls.doc["text"])
        cls.doc["sentences"] = sentence_spans(cls.doc["tokens"])
        tokenizer = Tokenizer(models.BPE(unk_token="<unk>"))
        tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        tokenizer.decoder = decoders.ByteLevel()
        texts = [str(prompt(cls.doc, "aaec", "joint")), graph_text(cls.doc["graph"])]
        tokenizer.train_from_iterator(texts, trainers.BpeTrainer(vocab_size=350, special_tokens=["<unk>", "<eos>", "<pad>", "<user>", "<assistant>"]))
        cls.tokenizer = PreTrainedTokenizerFast(tokenizer_object=tokenizer, unk_token="<unk>", eos_token="<eos>", pad_token="<pad>")
        cls.tokenizer.chat_template = "{% for message in messages %}<user>{{ message['content'] }}{% endfor %}{% if add_generation_prompt %}<assistant>{% endif %}"

    def model(self):
        from am.model import GraphModel
        torch.manual_seed(4)
        base = Qwen2ForCausalLM(Qwen2Config(vocab_size=len(self.tokenizer), hidden_size=32, intermediate_size=64,
                                          num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=2,
                                          max_position_embeddings=4096, attention_dropout=0.0))
        return GraphModel(base, self.tokenizer, self.cfg)

    def test_loss_backward_and_frozen_base(self):
        from am.model import encode_example
        m = self.model()
        encoded = encode_example(self.tokenizer, self.doc, self.cfg, "joint")
        losses = m(encoded)
        self.assertTrue(torch.isfinite(losses["loss"]))
        self.assertGreater(float(losses["aux_loss"].detach()), 0)
        losses["loss"].backward()
        trainable = [p for p in m.parameters() if p.requires_grad]
        self.assertTrue(any(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in trainable))
        self.assertTrue(all(p.grad is None for p in m.parameters() if not p.requires_grad))

    def test_prompt_loss_mask_and_gate(self):
        from am.model import encode_example
        e = encode_example(self.tokenizer, self.doc, self.cfg, "joint")
        first = next(i for i, value in enumerate(e.labels) if value != -100)
        self.assertTrue(all(x == 0 for x in e.gates[:first]))
        self.assertIn(1, e.gates[first:])
        self.assertTrue(all(max(p) < first for p in e.sentence_positions))
        self.assertEqual(e.sentence_labels, [1, 0])

    def test_no_silent_truncation(self):
        from am.model import encode_example
        cfg = copy.deepcopy(self.cfg); cfg["model"]["max_context"] = 10
        with self.assertRaises(ValueError): encode_example(self.tokenizer, self.doc, cfg, "joint")

    def test_adapter_roundtrip(self):
        from am.model import encode_example
        m = self.model().eval()
        e = encode_example(self.tokenizer, self.doc, self.cfg, "joint")
        with torch.no_grad(): reference = m(e)["loss"].clone()
        with tempfile.TemporaryDirectory() as temp:
            m.save_adapter(temp, "tiny-random-test-model")
            second = self.model().eval()
            second.load_adapter(temp, "tiny-random-test-model")
            with torch.no_grad(): actual = second(e)["loss"]
            self.assertTrue(torch.equal(reference, actual))
            with self.assertRaises(ValueError): second.load_adapter(temp, "different-base")

    def test_one_optimizer_step(self):
        from am.model import encode_example
        m = self.model()
        opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=0.01)
        before = {k:v.clone() for k,v in m.trainable_state().items()}
        loss = m(encode_example(self.tokenizer, self.doc, self.cfg, "components"))["loss"]
        loss.backward(); opt.step()
        self.assertTrue(any(not torch.equal(v, before[k]) for k,v in m.trainable_state().items()))

    def test_uncached_generation_token_bound(self):
        from am.model import HFBackend
        m = self.model()
        backend = HFBackend(m, "tiny-random")
        result = backend.generate([{"role":"user", "content":"Libraries"}], {"max_new_tokens":3,"temperature":0.0,"top_p":0.9})
        self.assertLessEqual(result.output_tokens, 3)
        self.assertGreater(result.input_tokens, 0)

    def test_local_training_and_reload_without_network(self):
        from am.train import train
        from am.model import load_local
        from am.io import jsonl
        from am.schema import tokenize, sentence_spans
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local_model = root/"tiny-model"
            raw = Qwen2ForCausalLM(Qwen2Config(vocab_size=len(self.tokenizer), hidden_size=32, intermediate_size=64,
                                              num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=2,
                                              max_position_embeddings=4096, attention_dropout=0.0))
            raw.save_pretrained(local_model)
            self.tokenizer.save_pretrained(local_model)
            cfg = copy.deepcopy(self.cfg)
            cfg["model"]["path"] = str(local_model)
            cfg["training"].update(epochs=3, tasks=["components"], gradient_accumulation=2,
                                   max_optimizer_steps=1, early_stopping=False)
            a, b = copy.deepcopy(self.doc), copy.deepcopy(self.doc)
            b.update(id="synthetic-dev", source_id="synthetic-dev", split="dev")
            b["text"] = b["text"].replace("Students", "Readers")
            b["tokens"], b["token_offsets"] = tokenize(b["text"])
            b["sentences"] = sentence_spans(b["tokens"])
            jsonl(root/"train.jsonl", [a]); jsonl(root/"dev.jsonl", [b])
            result = train(cfg, root/"train.jsonl", root/"dev.jsonl", root/"run")
            self.assertEqual(result["optimizer_steps"], 1)
            self.assertEqual(result["termination"], "optimizer_step_limit")
            model, identity = load_local(cfg, root/"run/best")
            self.assertTrue(identity)
            self.assertTrue((root/"run/best/adapter.safetensors").is_file())


if __name__ == "__main__":
    unittest.main()
