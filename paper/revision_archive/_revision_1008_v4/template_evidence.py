"""Record v3 package fidelity evidence without changing the reference."""
import hashlib
import json
from pathlib import Path
import zipfile

from lxml import etree

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent
TEMPLATE = ROOT / 'report_1008_v3_full.docx'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
PRESERVE = {'word/numbering.xml', 'word/fontTable.xml', 'word/webSettings.xml',
            'docProps/app.xml', 'docProps/custom.xml'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    expected = 'e3cda7c0e31b57f908b6c89c685967c1b713c85646565de1a59ecc7968a752f1'
    assert sha(TEMPLATE) == expected
    parts = []
    with zipfile.ZipFile(TEMPLATE) as archive:
        for name in archive.namelist():
            data = archive.read(name)
            preserve = name in PRESERVE or name.startswith(('word/media/', 'word/theme/', 'customXml/'))
            parts.append({'name': name, 'bytes': len(data),
                          'sha256': hashlib.sha256(data).hexdigest(),
                          'policy': 'preserve-only' if preserve else 'authorized-layout-or-content'})
        body = etree.fromstring(archive.read('word/document.xml'))
        sections = [etree.tostring(section, encoding='unicode')
                    for section in body.xpath('//w:sectPr', namespaces=NS)]
        style_xml = etree.fromstring(archive.read('word/styles.xml'))
        styles = [etree.tostring(style, encoding='unicode')
                  for style in style_xml.xpath('//w:style', namespaces=NS)
                  if style.attrib.get('{%s}styleId' % NS['w']) in
                  ('Normal', 'Title', 'Heading1', 'Heading2', 'Heading3',
                   'TOC1', 'TOC2', 'TOC3', 'AlgorithmLine')]
    result = {'reference': str(TEMPLATE), 'sha256': sha(TEMPLATE),
              'reference_render': str(ROOT / '_revision_1008_v3/v3_10_withdrawal/render'),
              'reference_render_pages': 88, 'sections': sections,
              'styles': styles, 'parts': parts,
              'baseline_hashes': {name: sha(ROOT / name) for name in
                                  ['report_1008_v3_full.docx', 'report_1008_v3_full.md',
                                   '1008_v3问题清单.md', '1008_v3逐项修改对照.md']}}
    (WORK / 'template-evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'reference_sha256': result['sha256'], 'sections': len(sections),
                      'parts': len(parts), 'preserve_only': sum(p['policy'] == 'preserve-only' for p in parts)}, indent=2))


if __name__ == '__main__':
    main()
