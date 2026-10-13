"""Re-run local software checks, persist evidence, never load/download real weights."""
import io
import json
import platform
import sys
import time
import unittest
import argparse
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from am.config import load
from am.io import dump, source_hashes, file_hash

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="New directory for checks; preserve historical validation artifacts")
    args = parser.parse_args()
    if args.out:
        from am.io import fresh_dir
        output = fresh_dir(args.out)
    else:
        output = ROOT/"validation"; output.mkdir(exist_ok=True)
    configs = {p.name: load(p) for p in sorted((ROOT/"configs").glob("*.json"))}
    suite = unittest.defaultTestLoader.discover(str(ROOT/"tests"))
    log = io.StringIO(); start = time.monotonic()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    environment = {}
    for name in ("torch", "transformers", "safetensors", "tokenizers", "numpy"):
        try: environment[name] = version(name)
        except PackageNotFoundError: environment[name] = "not_installed"
    (output/"test_output.txt").write_text(log.getvalue(), encoding="utf-8")
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "scope": "synthetic_software_validation_only",
              "historical_reproduction": False, "real_dataset_training": "NOT_RUN", "real_model_training": "NOT_RUN",
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "successful": result.wasSuccessful(), "seconds": time.monotonic()-start,
              "validated_configurations": sorted(configs), "python": sys.version, "platform": platform.platform(),
              "packages": environment, "source_sha256": source_hashes(),
              "tests_sha256": {p.name: file_hash(p) for p in sorted((ROOT/"tests").glob("*.py"))}}
    dump(output/"test_report.json", report)
    print(log.getvalue()); print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
