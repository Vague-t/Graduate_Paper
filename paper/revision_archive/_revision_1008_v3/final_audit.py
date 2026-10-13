"""Mechanical release checks; visual review is recorded separately."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from lxml import etree
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('render_dir', type=Path)
    args = parser.parse_args()
    docx = ROOT / 'report_1008_v3_full.docx'
    source = ROOT / 'report_1008_v3_full.md'
    pdf = args.render_dir / 'report_1008_v3_full.pdf'
    audit = json.loads((WORK / 'content_audit.json').read_text())
    build = json.loads((WORK / 'docx_build.json').read_text())
    page_map = json.loads((WORK / 'page_map.json').read_text())
    page_audit = json.loads((WORK / 'page_map_audit.json').read_text())
    assert Path(page_audit['pdf']).resolve() == pdf.resolve()
    assert page_audit['matched'] == len(page_map) == 167
    assert not page_audit['unresolved']
    assert sha(source) == audit['source_sha256'] == build['source_sha256']
    for name, old_hash in audit['baseline_hashes'].items():
        assert sha(ROOT / name) == old_hash, name
    with zipfile.ZipFile(docx) as archive:
        template_evidence = json.loads((WORK / 'template-evidence.json').read_text())
        assert sha(Path(template_evidence['reference'])) == template_evidence['sha256']
        for part in template_evidence['parts']:
            if part['policy'] == 'preserve-only':
                assert hashlib.sha256(archive.read(part['name'])).hexdigest() == part['sha256'], part['name']
        body = etree.fromstring(archive.read('word/document.xml'))
        styles = etree.fromstring(archive.read('word/styles.xml'))
        paragraphs = [''.join(p.xpath('.//w:t/text()', namespaces=NS))
                      for p in body.xpath('//w:p', namespaces=NS)]
        all_text = '\n'.join(paragraphs)
        fields = body.xpath('//w:instrText/text()', namespaces=NS)
        toc = [s for s in fields if s.strip().startswith('TOC ')]
        displays = []
        display_numbers = []
        for table in body.xpath('//w:tbl', namespaces=NS):
            rows = table.xpath('./w:tr', namespaces=NS)
            cells = rows[0].xpath('./w:tc', namespaces=NS) if len(rows) == 1 else []
            if len(cells) != 3:
                continue
            label = ''.join(cells[2].xpath('.//w:t/text()', namespaces=NS))
            equations = cells[1].xpath('.//m:oMath', namespaces=NS)
            if re.fullmatch(r'\([2-4]-\d+\)', label) and equations:
                displays.append(equations)
                display_numbers.append(label)
        maths = body.xpath('//m:oMath', namespaces=NS)
        assert len(toc) == 3, toc
        cached_paragraphs = body.xpath('//w:p[w:pPr/w:pStyle[@w:val="TOC1" or @w:val="TOC2" or @w:val="TOC3" or @w:val="FigureList" or @w:val="TableList"]]', namespaces=NS)
        cached_labels = [entry[1] for entry in build['headings']]
        cached_labels += [label for prefix in ['图', '表']
                          for label in build['captions'] if label.startswith(prefix)]
        assert len(cached_paragraphs) == len(cached_labels) == 165
        for paragraph, label in zip(cached_paragraphs, cached_labels):
            texts = paragraph.xpath('.//w:t/text()', namespaces=NS)
            assert texts[-1].strip() == page_map[label], (label, texts[-1], page_map[label])
        continuation_texts = [''.join(p.xpath('.//w:t/text()', namespaces=NS))
                              for p in body.xpath('//w:p[w:pPr/w:pStyle[@w:val="ContinuationCaption"]]', namespaces=NS)]
        assert continuation_texts == ['表2-2（续）', '算法4-1（续）', '表E-7（续）', '表F-1（续）']
        assert len(body.xpath('//w:tbl', namespaces=NS)) == 62  # 32 equations + 27 tables + 3 continuation parts
        assert len(displays) == 32, len(displays)
        assert display_numbers == ['(' + item['number'] + ')' for item in build['display_equations']]
        expected_formulas = [formula.strip() for formula in re.findall(r'\$\$(.*?)\$\$', source.read_text(), re.S)]
        assert expected_formulas == [item['source'].strip() for item in build['display_equations']]
        assert len(body.xpath('//a:blip', namespaces=NS)) == 7
        algorithm_lines = body.xpath('//w:p[w:pPr/w:pStyle[@w:val="AlgorithmLine"]]', namespaces=NS)
        expected_lines = [line for algorithm in build['algorithms'] for line in algorithm['source_lines']]
        assert len(algorithm_lines) == len(expected_lines)
        assert len(build['algorithms']) == 2
        for paragraph, line in zip(algorithm_lines, expected_lines):
            if line['number'] is not None:
                assert paragraph.xpath('./w:r[1]/w:t/text()', namespaces=NS) == [f"{line['number']:02d}"]
            indent = paragraph.xpath('./w:pPr/w:ind', namespaces=NS)[0]
            expected_twips = round((7 + line['depth'] * 4) * 1440 / 25.4)
            assert abs(int(indent.attrib['{%s}left' % NS['w']]) - expected_twips) <= 1
            assert abs(int(indent.attrib['{%s}hanging' % NS['w']]) - expected_twips) <= 1
        pattern = r'(?<![\d.])\d+(?:\.\d+)?%?P%?'
        expected = Counter(re.findall(pattern, source.read_text()))
        observed = Counter(re.findall(pattern, all_text))
        assert sum(expected.values()) == 125
        assert expected == observed, {'expected': expected, 'observed': observed}
        for token in ['<!--ref:', '<!--anchor:', '\\begin{', '\\mathcal',
                      '训练增强不是对论文正文的润色', '表4-4的P值', '真实病例']:
            assert token not in all_text, token
        style_ids = styles.xpath('//w:style/@w:styleId', namespaces=NS)
        for name in ['Heading1', 'Heading2', 'Heading3']:
            assert name in style_ids, name
        embedded_hashes = {hashlib.sha256(archive.read(name)).hexdigest()
                           for name in archive.namelist() if name.startswith('word/media/')}
        for entry in audit['images']:
            assert sha(ROOT / entry['path']) in embedded_hashes, entry['path']
    with pdfplumber.open(pdf) as doc:
        page_texts = [page.extract_text() or '' for page in doc.pages]
        no_warning = [n for n, text in enumerate(page_texts, 1)
                      if '1008-v3' not in text.replace(' ', '') or '非实测' not in text.replace(' ', '') or '勿送审' not in text.replace(' ', '')]
        assert not no_warning, no_warning
        assert not [n for n, text in enumerate(page_texts, 1) if not text.strip()]
        assert all((args.render_dir / f'page-{n}.png').exists()
                   for n in range(1, len(doc.pages) + 1))
        outside = []
        for n, page in enumerate(doc.pages, 1):
            chars = [c for c in page.chars if c['text'].strip()
                     and (c['x0'] < 0 or c['x1'] > page.width + 1
                          or c['top'] < 0 or c['bottom'] > page.height + 1)]
            if chars:
                outside.append({'page': n, 'text': ''.join(c['text'] for c in chars)})
        assert not outside, outside
        page_count = len(doc.pages)
    result = {
        'source_sha256': sha(source), 'docx_sha256': sha(docx), 'pdf_sha256': sha(pdf),
        'render_directory': str(args.render_dir.resolve()), 'pages': page_count,
        'native_math_objects': len(maths), 'native_display_equations': len(displays),
        'toc_fields': len(toc), 'numbered_tables': audit['table_count'],
        'verified_page_labels': len(page_map), 'toc_cached_entries': len(cached_labels),
        'toc_cache_matches_final_pdf': True,
        'continuation_captions': continuation_texts,
        'figures': 7, 'references': 46, 'placeholder_tokens': sum(observed.values()),
        'all_images_match_final_assets': True, 'baseline_files_unchanged': True,
        'preserve_only_package_parts_unchanged': True,
        'algorithm_semantic_indent_and_line_numbers': 'PASS',
        'all_pages_have_non_empirical_warning': True,
        'page_images_complete': True, 'text_outside_page': [],
        'mechanical_checks': 'PASS', 'visual_checks': 'see per-page review record',
        'limits': 'Does not certify empirical results, external citations, school compliance or all Word versions.'}
    (WORK / 'final_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
