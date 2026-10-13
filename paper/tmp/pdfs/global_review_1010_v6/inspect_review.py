"""Read-only checks for the exact v6 files; outputs stay in this review directory."""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import json
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path('/Users/channtang/Downloads/paper')
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('review_base', ROOT/'tmp/pdfs/global_review_1009_v4/inspect_review.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.OUT = OUT
base.CURRENT = ROOT/'_revision_1010_v6/render_final/report_1010_v6_full.pdf'

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
    scenario = ROOT/'_revision_1010_v6'
    manifest = json.loads((scenario/'scenario_manifest.json').read_text())
    assert sha256((scenario/'generate_scenario.py').read_bytes()).hexdigest() == manifest['generator_sha256']
    for name, digest in manifest['files'].items():
        assert sha256((scenario/name).read_bytes()).hexdigest() == digest
    previous = ROOT/'_revision_1010_v5'
    preserved = {name:(scenario/name).read_bytes() == (previous/name).read_bytes()
                 for name in manifest['files'] if (previous/name).is_file()}
    ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
          'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
    with zipfile.ZipFile(ROOT/'report_1010_v6_full.docx') as archive:
        assert archive.testzip() is None
        root = ET.fromstring(archive.read('word/document.xml'))
        text = '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns))
                         for p in root.findall('.//w:p',ns))
        (OUT/'docx_text.txt').write_text(text)
        package_counts = dict(tables=len(root.findall('.//w:tbl',ns)),
                              math=len(root.findall('.//m:oMath',ns)))
    result = dict(references=references, source_hashes={str(p):sha256(p.read_bytes()).hexdigest()
        for p in [ROOT/'report_1010_v6_full.md', ROOT/'report_1010_v6_full.docx', base.CURRENT]},
        scenario_hashes_verified=True, manifest_files=len(manifest['files']),
        preserved_from_v5=preserved, docx_package_counts=package_counts)
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
