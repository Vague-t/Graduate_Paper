"""Public graph coordinates: 1-based inclusive evaluation-token spans."""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import re
from .io import loads

SCHEMAS = {
    "aaec": {"components": ["MajorClaim", "Claim", "Premise"], "relations": ["Support", "Attack"], "conclusions": ["Claim"]},
    "cdcp": {"components": ["Fact", "Testimony", "Value", "Policy", "Reference"], "relations": ["Reason", "Evidence"], "conclusions": ["Policy", "Value"]},
    "coarse": {"components": ["Claim", "Premise"], "relations": ["Link"], "conclusions": ["Claim"]},
}
COARSE = {"MajorClaim": "Claim", "Claim": "Claim", "Premise": "Premise",
          "Policy": "Claim", "Value": "Claim", "Fact": "Premise",
          "Testimony": "Premise", "Reference": "Premise"}
TOKEN_PATTERN = r"\w+|[^\w\s]"
TOKENIZER_VERSION = "unicode_regex_v1"


def tokenize(text):
    matches = list(re.finditer(TOKEN_PATTERN, text, flags=re.UNICODE))
    return [m.group() for m in matches], [[m.start(), m.end()] for m in matches]


def sentence_spans(tokens):
    """Deterministic punctuation rule, not a linguistic sentence parser."""
    result, start = [], 1
    for i, token in enumerate(tokens, 1):
        if token in {".", "!", "?", "。", "！", "？"}:
            result.append([start, i]); start = i+1
    if start <= len(tokens):
        result.append([start, len(tokens)])
    return result


def char_to_span(offsets, start, end):
    starts = {v[0]: i+1 for i, v in enumerate(offsets)}
    ends = {v[1]: i+1 for i, v in enumerate(offsets)}
    if start not in starts or end not in ends or starts[start] > ends[end]:
        raise ValueError(f"Character annotation [{start},{end}) is not aligned with evaluation tokens")
    return [starts[start], ends[end]]


def parse_graph(raw):
    """No regex JSON extraction, repairs, silent casting or removal of bad objects."""
    g = loads(raw) if isinstance(raw, str) else deepcopy(raw)
    if not isinstance(g, dict) or set(g) != {"components", "relations"}:
        raise ValueError("Graph must have exactly components and relations")
    if not all(isinstance(g[k], list) for k in g):
        raise ValueError("components and relations must be lists")
    for c in g["components"]:
        if not isinstance(c, dict) or set(c) != {"id", "type", "span"}:
            raise ValueError("Component must have id, type, span")
        if type(c["id"]) is not int or not isinstance(c["type"], str):
            raise ValueError("Invalid component id/type")
        if not isinstance(c["span"], list) or len(c["span"]) != 2 or any(type(x) is not int for x in c["span"]):
            raise ValueError("Span must contain two integers")
    for e in g["relations"]:
        if not isinstance(e, dict) or set(e) != {"source", "target", "type"}:
            raise ValueError("Relation must have source, target, type")
        if any(type(e[k]) is not int for k in ("source", "target")) or not isinstance(e["type"], str):
            raise ValueError("Invalid relation fields")
    return g


@dataclass(frozen=True)
class Issue:
    kind: str
    index: int
    detail: str


def cycle_edges(g):
    """Return every edge participating in a cycle; includes self-loops."""
    adjacency = {}
    for e in g["relations"]:
        adjacency.setdefault(e["source"], set()).add(e["target"])
    def reaches(start, goal):
        stack, seen = [start], set()
        while stack:
            node = stack.pop()
            if node == goal:
                return True
            if node not in seen:
                seen.add(node); stack.extend(adjacency.get(node, ()))
        return False
    return [i for i, e in enumerate(g["relations"]) if reaches(e["target"], e["source"])]


def issues(g, token_count, corpus, acyclic=True):
    schema = SCHEMAS[corpus]
    result = []
    ids = Counter(c["id"] for c in g["components"])
    for i, c in enumerate(g["components"]):
        s, e = c["span"]
        if c["id"] <= 0 or ids[c["id"]] != 1:
            result.append(Issue("node", i, "nonunique_or_nonpositive_id"))
        if not 1 <= s <= e <= token_count:
            result.append(Issue("node", i, "span_out_of_bounds"))
        if c["type"] not in schema["components"]:
            result.append(Issue("node", i, "component_type"))
        if any(max(s, q["span"][0]) <= min(e, q["span"][1]) for q in g["components"][:i]):
            result.append(Issue("node", i, "overlap"))
    edge_counts = Counter((e["source"], e["target"], e["type"]) for e in g["relations"])
    major_ids = {c["id"] for c in g["components"] if c["type"] == "MajorClaim"}
    for i, e in enumerate(g["relations"]):
        if ids[e["source"]] != 1 or ids[e["target"]] != 1:
            result.append(Issue("edge", i, "invalid_reference"))
        if e["source"] == e["target"]:
            result.append(Issue("edge", i, "self_loop"))
        if e["type"] not in schema["relations"]:
            result.append(Issue("edge", i, "relation_type"))
        if corpus == "aaec" and (e["source"] in major_ids or e["target"] in major_ids):
            result.append(Issue("edge", i, "aaec_majorclaim_not_a_relation_endpoint"))
        if edge_counts[(e["source"], e["target"], e["type"])] > 1:
            result.append(Issue("edge", i, "duplicate_edge"))
    if acyclic:
        result.extend(Issue("edge", i, "cycle") for i in cycle_edges(g))
    return result


def validate_document(doc):
    for key in ("id", "source_id", "split", "corpus", "text", "tokens", "token_offsets", "sentences", "graph"):
        if key not in doc:
            raise ValueError(f"Document missing {key}")
    if not isinstance(doc["id"], str) or not doc["id"] or not isinstance(doc["source_id"], str):
        raise ValueError("Document/source id must be nonempty strings")
    if doc["split"] not in {"train", "dev", "test"} or doc["corpus"] not in SCHEMAS:
        raise ValueError("Unknown split/corpus")
    tokens, offsets = tokenize(doc["text"])
    if tokens != doc["tokens"] or offsets != doc["token_offsets"]:
        raise ValueError("Token/character coordinate mismatch")
    if doc["sentences"] != sentence_spans(tokens):
        raise ValueError("Sentence rule mismatch")
    g = parse_graph(doc["graph"])
    bad = issues(g, len(tokens), doc["corpus"], acyclic=False)
    if bad:
        raise ValueError(f"Invalid gold annotation: {bad}")
    return doc


def coarse_graph(g):
    out = deepcopy(g)
    for c in out["components"]:
        c["type"] = COARSE.get(c["type"], c["type"])
    for e in out["relations"]:
        e["type"] = "Link" if e["type"] in {"Support", "Attack", "Reason", "Evidence", "Link"} else e["type"]
    return out
