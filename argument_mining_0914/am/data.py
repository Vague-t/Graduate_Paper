"""Explicit split manifests and conservative raw-data conversion."""
from collections import Counter
from pathlib import Path
from .io import read_json, read_jsonl, jsonl, dump, file_hash, fingerprint, fresh_dir
from .schema import tokenize, sentence_spans, char_to_span, validate_document, TOKENIZER_VERSION, issues


def make_document(doc_id, corpus, text, components, relations, split, source_id=None):
    tokens, offsets = tokenize(text)
    doc = {"id": doc_id, "source_id": source_id or doc_id, "split": split,
           "corpus": corpus, "text": text, "tokens": tokens, "token_offsets": offsets,
           "sentences": sentence_spans(tokens), "tokenizer": TOKENIZER_VERSION,
           "graph": {"components": components, "relations": relations}}
    return validate_document(doc)


def read_exact(path):
    with Path(path).open(encoding="utf-8", newline="") as f:
        return f.read()


def convert_brat(text_path, split):
    path = Path(text_path)
    text = read_exact(path)
    _, offsets = tokenize(text)
    components, relations, mapping = [], [], {}
    lines = read_exact(path.with_suffix(".ann")).splitlines()
    ignored = Counter()
    for line in lines:
        if line.startswith("T"):
            key, spec, annotated = line.split("\t", 2)
            if ";" in spec:
                raise ValueError(f"Discontinuous BRAT span unsupported: {path}:{key}")
            typ, start, end = spec.split()
            start, end = int(start), int(end)
            if text[start:end] != annotated:
                raise ValueError(f"BRAT character text mismatch: {path}:{key}")
            if key in mapping:
                raise ValueError("Duplicate BRAT id")
            mapping[key] = len(components)+1
            components.append({"id": mapping[key], "type": typ, "span": char_to_span(offsets, start, end)})
    for line in lines:
        if line.startswith("R"):
            _, spec = line.split("\t", 1)
            typ, src, tgt = spec.split()
            labels = {"supports": "Support", "attacks": "Attack", "Support": "Support", "Attack": "Attack"}
            if typ not in labels:
                raise ValueError(f"Unknown BRAT relation: {typ}")
            relations.append({"source": mapping[src.split(":", 1)[1]], "target": mapping[tgt.split(":", 1)[1]], "type": labels[typ]})
        elif line and not line.startswith("T"):
            # BRAT stance attributes and annotator notes are not relation edges.
            if line[0] not in {"A", "M", "#"}:
                raise ValueError(f"Unsupported BRAT annotation: {line}")
            ignored[line[0]] += 1
    doc = make_document(path.stem, "aaec", text, components, relations, split)
    doc["conversion"] = {"input_sha256": {path.name: file_hash(path), path.with_suffix('.ann').name: file_hash(path.with_suffix('.ann'))}, "ignored_attribute_or_note_counts": dict(ignored)}
    return doc


def convert_cdcp(annotation_path, split, multi_premise="reject"):
    """CDCP JSON dialect: prop_offsets, prop_labels, reasons/evidences.

    Each relation is [[source_start, source_end], target], 0-based proposition IDs.
    No implicit merging/expansion; unsupported dialects fail visibly.
    """
    path = Path(annotation_path)
    raw = read_json(path)
    doc_id = path.name.removesuffix(".ann.json")
    text_path = path.with_name(doc_id+".txt")
    text = read_exact(text_path)
    _, offsets = tokenize(text)
    spans, labels = raw["prop_offsets"], raw["prop_labels"]
    if len(spans) != len(labels):
        raise ValueError("CDCP offset/label count mismatch")
    allowed = {x.lower(): x for x in ("Fact", "Testimony", "Value", "Policy", "Reference")}
    components = [{"id": i+1, "type": allowed[t.lower()], "span": char_to_span(offsets, *s)} for i, (s, t) in enumerate(zip(spans, labels))]
    relations, expansions = [], 0
    for key, typ in (("reasons", "Reason"), ("evidences", "Evidence")):
        for source_range, target in raw[key]:
            lo, hi = source_range
            if any(type(x) is not int for x in (lo, hi, target)) or not (0 <= lo <= hi < len(components) and 0 <= target < len(components)):
                raise ValueError("Invalid CDCP proposition reference")
            if lo != hi:
                if multi_premise != "expand":
                    raise ValueError(f"{doc_id}: multi-proposition premise requires an explicit preprocessing decision")
                expansions += 1
            for source in range(lo, hi+1):
                relations.append({"source": source+1, "target": target+1, "type": typ})
    doc = make_document(doc_id, "cdcp", text, components, relations, split)
    doc["conversion"] = {"multi_premise_policy": multi_premise, "expanded_relations": expansions,
                         "input_sha256": {path.name: file_hash(path), text_path.name: file_hash(text_path)}}
    return doc


def split_audit(docs):
    ids, sources, texts = set(), {}, {}
    for doc in docs:
        validate_document(doc)
        if doc["id"] in ids:
            raise ValueError(f"Duplicate document id: {doc['id']}")
        ids.add(doc["id"])
        for bucket, key in ((sources, doc["source_id"]), (texts, fingerprint(doc["text"]))):
            if key in bucket and bucket[key] != doc["split"]:
                raise ValueError(f"Cross-split source/text leakage: {doc['id']}")
            bucket[key] = doc["split"]
    return {"documents": len(docs), "splits": dict(Counter(d["split"] for d in docs)), "source_and_exact_text_disjoint": True}


def stats(docs):
    out = {"audit": split_audit(docs), "groups": {}}
    for corpus, split in sorted({(d["corpus"], d["split"]) for d in docs}):
        selected = [d for d in docs if (d["corpus"], d["split"]) == (corpus, split)]
        counts, lengths, doc_counts, edges = Counter(), Counter(), Counter(), Counter()
        cycle_documents = 0
        for d in selected:
            types = set()
            for c in d["graph"]["components"]:
                t = c["type"]; types.add(t); counts[t] += 1
                lengths[t] += c["span"][1]-c["span"][0]+1
            doc_counts.update(types)
            edges.update(e["type"] for e in d["graph"]["relations"])
            cycle_documents += any(i.detail == "cycle" for i in issues(d["graph"], len(d["tokens"]), corpus))
        out["groups"][f"{corpus}/{split}"] = {"documents": len(selected), "component_counts": dict(counts), "component_document_counts": dict(doc_counts), "mean_span_tokens": {t: lengths[t]/n for t, n in counts.items()}, "relation_counts": dict(edges), "IR_observed_nonzero_types": max(counts.values())/min(counts.values()) if counts else None, "documents_with_cycles": cycle_documents}
    return out


def prepare(corpus, raw_dir, splits_path, out_dir, multi_premise="reject"):
    split_map = read_json(splits_path)
    if set(split_map) != {"train", "dev", "test"}:
        raise ValueError("Split file must contain train/dev/test lists of exact document IDs")
    seen, docs = set(), []
    root = Path(raw_dir)
    for split, names in split_map.items():
        if not isinstance(names, list) or not names:
            raise ValueError(f"Empty or invalid split: {split}")
        for name in names:
            if not isinstance(name, str) or Path(name).name != name or name in {".", ".."}:
                raise ValueError("Split IDs must be plain filenames without suffix")
            if name in seen:
                raise ValueError(f"Document in multiple splits: {name}")
            seen.add(name)
            docs.append(convert_brat(root/(name+".txt"), split) if corpus == "aaec" else convert_cdcp(root/(name+".ann.json"), split, multi_premise))
    audit = stats(docs)
    out = fresh_dir(out_dir)
    for split in split_map:
        jsonl(out/(split+".jsonl"), [d for d in docs if d["split"] == split])
    dump(out/"statistics.json", audit)
    dump(out/"split_manifest.json", {"source_sha256": file_hash(splits_path), "splits": split_map, "tokenizer": TOKENIZER_VERSION, "multi_premise_policy": multi_premise, "historical_split_equivalence": "unverified"})
    return audit
