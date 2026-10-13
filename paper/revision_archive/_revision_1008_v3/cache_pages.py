"""Reuse the audited page-cache scanner, writing only the v3 work directory."""
import importlib.util
from pathlib import Path

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('v2_page_cache_readonly', WORK.parent / '_revision_1007_v2/cache_pages.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
previous.WORK = WORK

if __name__ == '__main__':
    previous.main()
