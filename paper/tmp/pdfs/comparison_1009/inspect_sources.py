"""Read-only source extraction and bounded page rendering for thesis comparison."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pdfplumber
import pypdfium2 as pdfium

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
WECHAT = Path('/Users/channtang/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_cqn98y9b01mm12_58e7/temp/RWTemp/2026-10')
SOURCES = {
    'contrastive': WECHAT / '7d1f24ca-f7dc-40d7-8a3c-304f65d1c057/基于对比式自监督学习的结构语义融合知识推理研究.pdf',
    'style_transfer': WECHAT / '1c71f5c7-1c7e-4464-83e7-00fe4e2d976c/现代汉语与文言文风格的迁移方法研究-答辩后修改.pdf',
    'transformer': WECHAT / 'c5c7b16c-f16f-4d0d-9774-b85c20f123ec/基于层内分组和层间选择的Transformer优化技术研究.pdf',
    'temporal_kg': ROOT / '打印论文版本.pdf',
    'prior_0405': Path('/Users/channtang/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_cqn98y9b01mm12_58e7/msg/file/2026-10/毕设论文0405.pdf'),
    'current_v4': ROOT / '_revision_1008_v4/render_pass6/report_1008_v4_full.pdf',
}
PREFLIGHT = Path('/Users/channtang/.codex/skills/academic-research-suite/ars/scripts/pdf_read_preflight.py')


def extract(slug):
    source = SOURCES[slug]
    run = subprocess.run([sys.executable, str(PREFLIGHT), str(source), '--output',
                          str(WORK / f'{slug}_preflight.json')], capture_output=True, text=True)
    pages = []
    with pdfplumber.open(source) as doc:
        for index, page in enumerate(doc.pages, 1):
            pages.append({'physical_page': index, 'width': float(page.width),
                          'height': float(page.height),
                          'text': (page.extract_text(layout=False) or '').replace('\x00', ''),
                          'image_count': len(page.images)})
        metadata = {str(key): str(value) for key, value in (doc.metadata or {}).items()}
    report = {'slug': slug, 'source': str(source), 'sha256': sha256(source.read_bytes()).hexdigest(),
              'page_count': len(pages), 'metadata': metadata,
              'preflight_exit_code': run.returncode, 'preflight_stdout': run.stdout,
              'preflight_stderr': run.stderr}
    (WORK / f'{slug}_pages.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2))
    (WORK / f'{slug}_metadata.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (WORK / f'{slug}_text.txt').write_text('\n\n'.join(
        f"===== PHYSICAL PAGE {page['physical_page']} =====\n{page['text']}" for page in pages))
    print(json.dumps(report, ensure_ascii=False, indent=2))


def render(slug, selected):
    document = pdfium.PdfDocument(str(SOURCES[slug]))
    for index in selected:
        page = document[index - 1]
        image = page.render(scale=1.6).to_pil()
        path = WORK / f'{slug}_p{index:03d}.png'
        image.save(path)
        print(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('slug', choices=SOURCES)
    parser.add_argument('--pages', nargs='+', type=int)
    args = parser.parse_args()
    render(args.slug, args.pages) if args.pages else extract(args.slug)
