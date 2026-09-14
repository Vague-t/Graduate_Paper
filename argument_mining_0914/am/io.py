"""Strict JSON and provenance helpers; no network access."""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"Duplicate JSON key: {k}")
        out[k] = v
    return out


def loads(text):
    return json.loads(text, object_pairs_hook=_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def read_json(path):
    return loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    result = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            result.append(loads(line))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{path}:{n}: {exc}") from exc
    return result


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+"\n")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_hashes():
    root = Path(__file__).parent
    return {p.name: file_hash(p) for p in sorted(root.glob("*.py"))}


def manifest(config, inputs=()):
    return {"implementation": "0914-reference-v1", "historical_reproduction": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "python": sys.version, "platform": platform.platform(),
            "config": config, "config_sha256": fingerprint(config),
            "source_sha256": source_hashes(),
            "input_sha256": {str(p): file_hash(p) for p in inputs}}


def fresh_dir(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite run directory: {path}")
    path.mkdir(parents=True)
    return path
