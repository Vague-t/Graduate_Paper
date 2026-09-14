"""Backend contract and auditable, per-document generation budgets."""
from dataclasses import dataclass
from time import monotonic
from .io import fingerprint, loads
from .prompts import edge_prompt


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Generated:
    text: str
    input_tokens: int
    output_tokens: int
    logprob_sum: float = 0.0
    finish_reason: str = "eos"


class BudgetedBackend:
    def __init__(self, backend, max_calls, max_output_tokens, generation, cached_usage=None):
        self.backend = backend
        self.max_calls = max_calls
        self.max_output_tokens = max_output_tokens
        self.generation = generation
        self.events = []
        self.output_tokens = 0
        self.cached_calls = (cached_usage or {}).get("calls", 0)
        self.cached_output_tokens = (cached_usage or {}).get("output_tokens_charged", 0)
        if any(type(n) is not int or n < 0 for n in (self.cached_calls, self.cached_output_tokens)):
            raise ValueError("Invalid cached generation cost")
        if self.cached_calls > max_calls or self.cached_output_tokens > max_output_tokens:
            raise ValueError("Cached generation already exceeds this logical experiment budget")

    def call(self, messages, *, phase, greedy=False, max_new_tokens=None, model_context=None):
        remaining = self.max_output_tokens-self.output_tokens-self.cached_output_tokens
        if len(self.events)+self.cached_calls >= self.max_calls or remaining <= 0:
            raise BudgetExceeded("Per-document model-call/output-token budget exhausted")
        cap = min(max_new_tokens or self.generation["max_new_tokens"], remaining)
        config = {**self.generation, "max_new_tokens": cap}
        if greedy:
            config["temperature"] = 0.0
        event = {"phase": phase, "request_sha256": fingerprint(messages),
                 "generation": config, "backend": self.backend.identity, "status": "running"}
        self.events.append(event)
        start = monotonic()
        try:
            result = self.backend.generate(messages, config, model_context=model_context)
            if not 0 <= result.output_tokens <= cap:
                raise ValueError("Backend violated output-token limit")
            self.output_tokens += result.output_tokens
            event.update(status="ok", input_tokens=result.input_tokens, output_tokens=result.output_tokens,
                         output_sha256=fingerprint(result.text), finish_reason=result.finish_reason)
            return result
        except Exception as exc:
            # Unknown work on failure is charged at its allocated upper bound.
            self.output_tokens += cap
            event.update(status="failed", charged_output_token_upper_bound=cap, error=type(exc).__name__+": "+str(exc))
            raise
        finally:
            event["seconds"] = monotonic()-start

    def usage(self):
        return {"calls": len(self.events), "input_tokens_observed": sum(e.get("input_tokens", 0) for e in self.events),
                "output_tokens_charged": self.output_tokens, "seconds": sum(e["seconds"] for e in self.events),
                "failed_calls": sum(e["status"] != "ok" for e in self.events),
                "cached_calls": self.cached_calls, "cached_output_tokens_charged": self.cached_output_tokens,
                "logical_calls": len(self.events)+self.cached_calls,
                "logical_output_tokens_charged": self.output_tokens+self.cached_output_tokens,
                "max_calls": self.max_calls, "max_output_tokens": self.max_output_tokens}


class SemanticVerifier:
    def __init__(self, backend):
        self.backend = backend
        self.cache = {}
        self.cache_hits = 0

    def edge(self, doc, g, e):
        messages = edge_prompt(doc, g, e)
        key = fingerprint({"backend": self.backend.backend.identity, "messages": messages})
        if key not in self.cache:
            raw = self.backend.call(messages, phase="edge_verification", greedy=True, max_new_tokens=32)
            value = loads(raw.text)
            if not isinstance(value, dict) or set(value) != {"supported"} or type(value["supported"]) is not bool:
                raise ValueError("Semantic verifier failed to return a boolean judgment")
            self.cache[key] = int(value["supported"])
        else:
            self.cache_hits += 1
        return self.cache[key]


class ReplayBackend:
    """Offline fixture responses ONLY; not a trained model or real experiment."""
    identity = "synthetic-fixture-replay-v1"

    def __init__(self, responses):
        self.responses = iter(responses)

    def generate(self, messages, config, model_context=None):
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        n = max(1, len(value.split()))
        if n > config["max_new_tokens"]:
            raise ValueError("Fixture exceeds mock token limit")
        return Generated(value, len(str(messages).split()), n, -float(n))
