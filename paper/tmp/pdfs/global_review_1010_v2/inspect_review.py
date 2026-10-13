"""Read-only source verification and bounded PDF inspection for 1010 v2."""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import json

ROOT = Path('/Users/channtang/Downloads/paper')
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('review_base', ROOT/'tmp/pdfs/global_review_1009_v4/inspect_review.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.OUT = OUT
base.CURRENT = ROOT/'_revision_1010_v2/render_final/report_1010_v2_full.pdf'

def verify():
    references = []
    for slug in ['contrastive', 'style_transfer', 'transformer', 'temporal_kg']:
        meta = json.loads((base.CACHE/f'{slug}_metadata.json').read_text())
        preflight = json.loads((base.CACHE/f'{slug}_preflight.json').read_text())
        source = base.source_path(meta)
        digest = sha256(source.read_bytes()).hexdigest()
        assert digest == meta['sha256'] == preflight['sha256']
        references.append(dict(slug=slug, source=str(source), sha256=digest,
                               structural_preflight=preflight['verdict']))
    manuscript = ROOT/'report_1010_v2_full.md'
    docx = ROOT/'report_1010_v2_full.docx'
    scenario = ROOT/'_revision_1010_v2'
    manifest = json.loads((scenario/'scenario_manifest.json').read_text())
    assert sha256((scenario/'generate_scenario.py').read_bytes()).hexdigest() == manifest['generator_sha256']
    for name, digest in manifest['files'].items():
        assert sha256((scenario/name).read_bytes()).hexdigest() == digest
    reused = {}
    for name in ['generate_scenario.py', 'document_counts.csv', 'scenario_results.json', 'score_records.json', 'audit_judgements.json']:
        reused[name] = (scenario/name).read_bytes() == (ROOT/'_revision_1010_v1'/name).read_bytes()
    result = dict(references=references, manuscript_sha256=sha256(manuscript.read_bytes()).hexdigest(),
                  docx_sha256=sha256(docx.read_bytes()).hexdigest(),
                  scenario_hashes_verified=True, scenario_byte_identical_to_1010_v1=reused)
    (OUT/'source_verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['verify', 'current', 'pages', 'locate', 'render'])
    parser.add_argument('slug', nargs='?')
    parser.add_argument('values', nargs='*')
    args = parser.parse_args()
    if args.action == 'verify': verify()
    elif args.action == 'current': base.current()
    elif args.action == 'pages': base.pages(args.slug, list(map(int, args.values)))
    elif args.action == 'locate': base.locate(args.slug, args.values[0])
    else: base.render(args.slug, list(map(int, args.values)))
