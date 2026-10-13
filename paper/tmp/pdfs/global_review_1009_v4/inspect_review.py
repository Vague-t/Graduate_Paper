"""Read-only source verification and bounded PDF extraction for the v4 review."""
from pathlib import Path
from hashlib import sha256
import argparse
import json
import re
import subprocess
import sys

ROOT = Path('/Users/channtang/Downloads/paper')
OUT = Path(__file__).resolve().parent
CACHE = ROOT / 'tmp/pdfs/comparison_1009'
CURRENT = ROOT / '_revision_1009_v4/render_verified/report_1009_v4_full.pdf'
ATTACHMENTS = Path('/Users/channtang/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_cqn98y9b01mm12_58e7/msg/file/2026-10')

def source_path(meta):
    original=Path(meta['source'])
    return original if original.is_file() else ATTACHMENTS/original.name

def verify():
    rows = []
    for slug in ['contrastive', 'style_transfer', 'transformer', 'temporal_kg', 'prior_0405']:
        meta = json.loads((CACHE / f'{slug}_metadata.json').read_text())
        preflight = json.loads((CACHE / f'{slug}_preflight.json').read_text())
        source=source_path(meta)
        digest = sha256(source.read_bytes()).hexdigest()
        assert digest == meta['sha256'] == preflight['sha256'], slug
        rows.append(dict(slug=slug, source=str(source), sha256=digest,
                         pages=meta['page_count'], structural_preflight=preflight['verdict']))
    scenario = ROOT / '_revision_1009_v4'
    manifest = json.loads((scenario / 'scenario_manifest.json').read_text())
    assert sha256((scenario / 'generate_scenario.py').read_bytes()).hexdigest() == manifest['generator_sha256']
    for name, digest in manifest['files'].items():
        assert sha256((scenario / name).read_bytes()).hexdigest() == digest
    result = dict(references=rows, scenario_hashes_verified=True,
                  manuscript_sha256=sha256((ROOT/'report_1009_v4_full.md').read_bytes()).hexdigest(),
                  docx_sha256=sha256((ROOT/'report_1009_v4_full.docx').read_bytes()).hexdigest())
    (OUT/'source_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))

def current():
    import pdfplumber
    check = Path('/Users/channtang/.codex/skills/academic-research-suite/ars/scripts/pdf_read_preflight.py')
    subprocess.run([sys.executable,str(check),str(CURRENT),'--output',str(OUT/'current_preflight.json')],check=True)
    with pdfplumber.open(CURRENT) as pdf:
        pages=[dict(physical_page=i+1,text=p.extract_text() or '') for i,p in enumerate(pdf.pages)]
    (OUT/'current_pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2))
    (OUT/'current_text.txt').write_text('\n\n'.join(f'===== PHYSICAL PAGE {p["physical_page"]} =====\n{p["text"]}' for p in pages))
    print(json.dumps(dict(pages=len(pages),source=str(CURRENT),sha256=sha256(CURRENT.read_bytes()).hexdigest()),ensure_ascii=False))

def pages(slug, selected):
    path=(OUT/'current_pages.json') if slug=='current' else (CACHE/f'{slug}_pages.json')
    data=json.loads(path.read_text())
    for p in data:
        if p['physical_page'] in selected:
            print(f'===== {slug} PHYSICAL PAGE {p["physical_page"]} =====\n{p["text"]}\n')

def locate(slug, pattern):
    path=(OUT/'current_pages.json') if slug=='current' else (CACHE/f'{slug}_pages.json')
    for p in json.loads(path.read_text()):
        lines=[line for line in p['text'].splitlines() if re.search(pattern,line)]
        if lines: print(p['physical_page'], ' | '.join(lines)[:1800])

def render(slug, selected):
    import pypdfium2 as pdfium
    path=CURRENT if slug=='current' else source_path(json.loads((CACHE/f'{slug}_metadata.json').read_text()))
    doc=pdfium.PdfDocument(str(path))
    for number in selected:
        target=OUT/f'{slug}_p{number:03d}.png'
        doc[number-1].render(scale=1.5).to_pil().save(target)
        print(target)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['verify','current','pages','locate','render'])
    parser.add_argument('slug',nargs='?')
    parser.add_argument('values',nargs='*')
    args=parser.parse_args()
    if args.action=='verify': verify()
    elif args.action=='current': current()
    elif args.action=='locate': locate(args.slug,args.values[0])
    elif args.action=='render': render(args.slug,list(map(int,args.values)))
    else: pages(args.slug,list(map(int,args.values)))
