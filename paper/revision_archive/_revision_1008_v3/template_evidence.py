"""Inventory the immutable reference package for the v3 fidelity gate."""
import hashlib
import json
from pathlib import Path
import zipfile

from lxml import etree

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent
TEMPLATE = ROOT / 'report_1007_v2_full.docx'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
PRESERVE = {'word/numbering.xml', 'word/fontTable.xml', 'word/webSettings.xml',
            'docProps/app.xml', 'docProps/custom.xml'}


def main():
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
    result = {'reference': str(TEMPLATE),
              'sha256': hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
              'reference_render': str(ROOT / '_revision_1007_v2/render_final5'),
              'reference_render_pages': 86, 'sections': sections,
              'styles': styles, 'parts': parts}
    (WORK / 'template-evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'reference_sha256': result['sha256'], 'sections': len(sections),
                      'parts': len(parts), 'preserve_only': sum(p['policy'] == 'preserve-only' for p in parts)}, indent=2))


if __name__ == '__main__':
    main()
