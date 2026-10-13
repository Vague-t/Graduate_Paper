from pathlib import Path
import hashlib
import json
import subprocess
import sys

root = Path('/Users/channtang/Downloads/paper')
base = Path(__file__).parent
cache = root / 'tmp/pdfs/comparison_1009'
old_manifest = json.loads((root / 'manuscript_review_test_20261011/chapter5_revision_and_consistency_20261012_v5/_source/reference_manifest.json').read_text())
aliases = {item['key']: item['path'] for item in old_manifest}
preflight = '/Users/channtang/.codex/skills/academic-research-suite/ars/scripts/pdf_read_preflight.py'
records = []
for slug in ('temporal_kg', 'contrastive', 'style_transfer', 'transformer', 'prior_0405'):
    old = json.loads((cache / f'{slug}_preflight.json').read_text())
    candidates = [Path(old['file'])]
    if slug in aliases:
        candidates.append(Path(aliases[slug]))
    if slug == 'temporal_kg':
        candidates.append(root / '历史报告/01_论文历史版本/打印论文版本.pdf')
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        raise FileNotFoundError(f'Missing verified source: {slug}')
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha != old['sha256']:
        raise ValueError(f'Source changed: {slug}')
    destination = base / 'sources' / slug
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, preflight, str(source), '--output', str(destination / 'preflight.json')], check=True, capture_output=True, text=True)
    status = json.loads((destination / 'preflight.json').read_text())
    if status['verdict'] != 'PASS':
        raise ValueError(f'Preflight did not pass: {slug}: {status}')
    # The cached extraction is bound to the same verified PDF bytes; retain physical page locators.
    pages = json.loads((cache / f'{slug}_pages.json').read_text())
    for page in pages:
        (destination / f"p{page['physical_page']:03d}.txt").write_text(page['text'])
    (destination / 'all_pages.txt').write_text('\n\n'.join(f"===== PDF physical page {p['physical_page']} =====\n{p['text']}" for p in pages))
    record = {'slug': slug, 'path': str(source), 'sha256': sha, 'pages': len(pages), 'preflight': status['verdict'], 'extraction': str(destination / 'all_pages.txt'), 'status': 'Partial manuscript; use completed portions only' if slug == 'prior_0405' else 'Primary style reference; passed status supplied by user, not independently verified'}
    records.append(record)
(base / 'source_manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2))
print(json.dumps(records, ensure_ascii=False, indent=2))
