"""Final mechanical 1010-v6 checks; every page must also receive visual review."""
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
P_PATTERN = r'(?<![\d.])\d+(?:\.\d+)?%?P%?'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(root):
    return [{name: [dict(element.attrib) for element in section.xpath('./w:' + name, namespaces=NS)]
             for name in ['pgSz', 'pgMar', 'cols', 'pgNumType', 'type']}
            for section in root.xpath('//w:sectPr', namespaces=NS)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('render_dir', type=Path)
    args = parser.parse_args()
    docx = ROOT / 'report_1010_v6_full.docx'
    source = ROOT / 'report_1010_v6_full.md'
    pdf = args.render_dir / 'report_1010_v6_full.pdf'
    text = source.read_text()
    build = json.loads((WORK / 'docx_build.json').read_text())
    evidence = json.loads((WORK / 'template-evidence.json').read_text())
    page_map = json.loads((WORK / 'page_map.json').read_text())
    page_audit = json.loads((WORK / 'page_map_audit.json').read_text())
    headings = [entry[1] for entry in build['headings']]
    captions = build['captions']
    all_labels = headings + captions
    cached_labels = headings + [label for prefix in ['图', '表']
                               for label in captions if label.startswith(prefix)]
    assert Path(page_audit['pdf']).resolve() == pdf.resolve()
    assert page_audit['matched'] == len(page_map) == len(all_labels)
    assert not page_audit['unresolved']
    assert sha(source) == build['source_sha256']
    for name, old_hash in evidence['baseline_hashes'].items():
        assert sha(ROOT / name) == old_hash, name
    assert sha(Path(evidence['reference'])) == evidence['sha256'] == build['retained_template_sha256']
    refs = re.findall(r'^\[(\d+)\] ', text, re.M)
    assert refs == [str(number) for number in range(1, 50)]
    images = re.findall(r'^!\[[^\]]*\]\(([^)]+)\)$', text, re.M)
    assert len(images) == 11
    expected_formulas = [formula.strip() for formula in re.findall(r'\$\$(.*?)\$\$', text, re.S)]
    assert len(expected_formulas) == 32
    assert expected_formulas == [item['source'].strip() for item in build['display_equations']]
    with zipfile.ZipFile(docx) as archive, zipfile.ZipFile(evidence['reference']) as retained:
        for part in evidence['parts']:
            if part['policy'] == 'preserve-only':
                assert hashlib.sha256(archive.read(part['name'])).hexdigest() == part['sha256'], part['name']
        body = etree.fromstring(archive.read('word/document.xml'))
        styles = etree.fromstring(archive.read('word/styles.xml'))
        original_body = etree.fromstring(retained.read('word/document.xml'))
        assert geometry(body) == geometry(original_body)
        assert len(geometry(body)) == 3
        paragraphs = [''.join(p.xpath('.//w:t/text()', namespaces=NS))
                      for p in body.xpath('//w:p', namespaces=NS)]
        all_text = '\n'.join(paragraphs)
        fields = body.xpath('//w:instrText/text()', namespaces=NS)
        toc = [s for s in fields if s.strip().startswith('TOC ')]
        assert len(toc) == 3
        settings = etree.fromstring(archive.read('word/settings.xml'))
        assert settings.xpath('//w:updateFields/@w:val', namespaces=NS) == ['true']
        displays, display_numbers = [], []
        for table in body.xpath('//w:tbl', namespaces=NS):
            rows = table.xpath('./w:tr', namespaces=NS)
            cells = rows[0].xpath('./w:tc', namespaces=NS) if len(rows) == 1 else []
            if len(cells) != 3:
                continue
            label = ''.join(cells[2].xpath('.//w:t/text()', namespaces=NS))
            equations = cells[1].xpath('.//m:oMath', namespaces=NS)
            if re.fullmatch(r'\([A-F0-9]+-\d+\)', label) and equations:
                displays.append(equations)
                display_numbers.append(label)
        maths = body.xpath('//m:oMath', namespaces=NS)
        assert len(displays) == len(expected_formulas)
        assert display_numbers == ['(' + item['number'] + ')' for item in build['display_equations']]
        assert len(maths) == build['native_equations']
        cached = body.xpath('//w:p[w:pPr/w:pStyle[@w:val="TOC1" or @w:val="TOC2" or @w:val="TOC3" or @w:val="FigureList" or @w:val="TableList"]]', namespaces=NS)
        assert len(cached) == len(cached_labels)
        for paragraph, label in zip(cached, cached_labels):
            visible = paragraph.xpath('.//w:t/text()', namespaces=NS)
            assert visible[-1].strip() == page_map[label], (label, visible[-1], page_map[label])
        bookmark_names = body.xpath('//w:bookmarkStart/@w:name', namespaces=NS)
        assert len(bookmark_names) == len(set(bookmark_names))
        assert not set(body.xpath('//w:hyperlink/@w:anchor', namespaces=NS)) - set(bookmark_names)
        continuation_texts = [''.join(p.xpath('.//w:t/text()', namespaces=NS))
                              for p in body.xpath('//w:p[w:pPr/w:pStyle[@w:val="ContinuationCaption"]]', namespaces=NS)]
        expected_continuations = Counter()
        for record in build['tables']:
            expected_continuations[record['caption'].split(' ', 1)[0] + '（续）'] += record['parts'] - 1
        for record in build['algorithms']:
            expected_continuations[record['caption'].split(' ', 1)[0] + '（续）'] += len(record['split_before_steps'])
        assert Counter(continuation_texts) == +expected_continuations
        table_parts = sum(record['parts'] for record in build['tables'])
        assert len(body.xpath('//w:tbl', namespaces=NS)) == len(displays) + table_parts
        assert len(body.xpath('//a:blip', namespaces=NS)) == len(images)
        algorithm_lines = body.xpath('//w:p[w:pPr/w:pStyle[@w:val="AlgorithmLine"]]', namespaces=NS)
        expected_lines = [line for algorithm in build['algorithms'] for line in algorithm['source_lines']]
        assert len(algorithm_lines) == len(expected_lines)
        for paragraph, line in zip(algorithm_lines, expected_lines):
            if line['number'] is not None:
                assert paragraph.xpath('./w:r[1]/w:t/text()', namespaces=NS) == [f"{line['number']:02d}"]
            indent = paragraph.xpath('./w:pPr/w:ind', namespaces=NS)[0]
            expected_twips = round((7 + line['depth'] * 4) * 1440 / 25.4)
            for attribute in ['left', 'hanging']:
                assert abs(int(indent.attrib['{%s}%s' % (NS['w'], attribute)]) - expected_twips) <= 1
        expected_p = Counter(re.findall(P_PATTERN, text))
        observed_p = Counter(re.findall(P_PATTERN, all_text))
        assert not expected_p and not observed_p
        for token in ['<!--ref:', '<!--anchor:', '\\begin{', '\\mathcal',
                      '训练增强不是对论文正文的润色', '表4-4的P值', '真实病例', 'CRediT']:
            assert token not in all_text, token
        assert all(name in styles.xpath('//w:style/@w:styleId', namespaces=NS)
                   for name in ['Heading1', 'Heading2', 'Heading3'])
        embedded = {hashlib.sha256(archive.read(name)).hexdigest()
                    for name in archive.namelist() if name.startswith('word/media/')}
        for image_path in images:
            assert sha(ROOT / image_path) in embedded
    with pdfplumber.open(pdf) as document:
        page_texts = [page.extract_text() or '' for page in document.pages]
        no_warning = [n for n, value in enumerate(page_texts, 1)
                      if any(token not in value.replace(' ', '')
                             for token in ['1010-v6'])]
        assert not no_warning, no_warning
        assert not [n for n, value in enumerate(page_texts, 1) if not value.strip()]
        assert all((args.render_dir / f'page-{n}.png').exists()
                   for n in range(1, len(document.pages) + 1))
        outside = []
        for number, page in enumerate(document.pages, 1):
            chars = [char for char in page.chars if char['text'].strip()
                     and (char['x0'] < 0 or char['x1'] > page.width + 1
                          or char['top'] < 0 or char['bottom'] > page.height + 1)]
            if chars:
                outside.append({'page': number, 'text': ''.join(c['text'] for c in chars)})
        assert not outside, outside
        page_count = len(document.pages)
    result = {
        'source_sha256': sha(source), 'docx_sha256': sha(docx), 'pdf_sha256': sha(pdf),
        'render_directory': str(args.render_dir.resolve()), 'pages': page_count,
        'native_math_objects': len(maths), 'native_display_equations': len(displays),
        'toc_fields': len(toc), 'numbered_tables': len(build['tables']),
        'verified_page_labels': len(page_map), 'toc_cached_entries': len(cached_labels),
        'toc_cache_matches_final_pdf': True, 'continuation_captions': continuation_texts,
        'algorithms': len(build['algorithms']), 'figures': len(images),
        'references': len(refs), 'placeholder_tokens': sum(observed_p.values()),
        'all_images_match_final_assets': True, 'baseline_files_unchanged': True,
        'preserve_only_package_parts_unchanged': True, 'section_geometry_unchanged': True,
        'algorithm_semantic_indent_and_line_numbers': 'PASS',
        'simulation_disclosure_on_cover': '模拟数据演示稿' in page_texts[0] and '不代表真实实验' in page_texts[0], 'all_pages_have_version': True,
        'page_images_complete': True, 'text_outside_page': [],
        'mechanical_checks': 'PASS', 'visual_checks': 'see per-page review record',
        'limits': 'Does not certify empirical results, external citations, school compliance or all Word versions.'}
    (WORK / 'final_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
