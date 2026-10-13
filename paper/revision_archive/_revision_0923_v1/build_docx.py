"""Build the explicitly labelled 0923 placeholder draft using the 0920 layout.

The retained 0920 files and scripts are never modified. ``--check-only`` is
read-only. Rendering/visual review belongs to the parent authoring workflow and
must use the packaged renderer and bundled LibreOffice, never desktop LO:
/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/MacOS/soffice
The parent has already recorded the single artifact-operation marker.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
SOURCE = ROOT / 'report_0923_v1_placeholder.md'
TEMPLATE = ROOT / 'report_0920_v1.docx'
OUTPUT = ROOT / 'report_0923_v1_placeholder.docx'
WARNING = '0923-v1 预期数值占位稿 非实测 勿送审'
BASELINE_HASHES = {
    'report_0920_v1.md': '14cf8e89acc1f118ec21667b29b041dd8caca06cf580ab34c228a8c7743d0ad1',
    'report_0920_v1.docx': '26bdd0a57e070959056856fa4f154b9d4ef641a6dd0dfa9b4320596ed5947d00',
}
spec = importlib.util.spec_from_file_location(
    'retained_0920_builder', ROOT / '_revision_0920_v1/build_docx.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
BUNDLED_PYTHON = base.BUNDLED_PYTHON
NUMBER = re.compile(r'(?<![A-Za-z0-9_\\.])[+-]?\d+(?:\.\d+)?(?![\d.])')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def baseline_check():
    found = {name: sha256(ROOT / name) for name in BASELINE_HASHES}
    if found != BASELINE_HASHES:
        raise AssertionError('A retained 0920 source changed: ' + repr(found))
    return found


def section(text, start, end=None):
    begin = re.search(r'^' + re.escape(start) + r'.*$', text, re.M)
    if begin is None:
        raise AssertionError('Missing section: ' + start)
    if end is None:
        return text[begin.start():]
    finish = re.search(r'^' + re.escape(end) + r'.*$', text[begin.end():], re.M)
    if finish is None:
        raise AssertionError('Missing section boundary: ' + end)
    return text[begin.start():begin.end() + finish.start()]


def placeholder_tables(text):
    """Return each added table with source rows and its immediately following note."""
    lines = base.COMMENT_RE.sub('', text).splitlines()
    tables = []
    for index, line in enumerate(lines):
        caption = re.match(r'^表5-(\d+)(?:P)?(?:\s|$)(.*)$', line)
        if not caption or int(caption[1]) < 5:
            continue
        pos = index + 1
        while pos < len(lines) and not lines[pos].strip():
            pos += 1
        row_lines = []
        while pos < len(lines) and lines[pos].strip().startswith('|'):
            row_lines.append(lines[pos])
            pos += 1
        if not row_lines:
            raise AssertionError('No table follows caption: ' + line)
        rows = [base.split_table_row(row) for row in row_lines]
        rows = [row for row in rows
                if not all(re.fullmatch(r':?-{3,}:?', cell) for cell in row)]
        while pos < len(lines) and not lines[pos].strip():
            pos += 1
        note = lines[pos].strip() if pos < len(lines) else ''
        tables.append({'number': '5-' + caption[1], 'caption': line,
                       'rows': rows, 'note': note, 'line': index + 1})
    return tables


def source_audit(source=SOURCE):
    old_hashes = baseline_check()
    text = Path(source).read_text(encoding='utf-8')
    retained = (ROOT / 'report_0920_v1.md').read_text(encoding='utf-8')
    comparisons = {
        'chapters_1_to_4_unchanged': ('## 第一章 ', '## 第五章 '),
        'references_text_unchanged': ('## 参考文献', '## 附录A '),
        'appendix_E_verbatim': ('## 附录E ', None),
    }
    preserved = {key: section(text, start, end) == section(retained, start, end)
                 for key, (start, end) in comparisons.items()}
    if not all(preserved.values()):
        raise AssertionError(preserved)
    refs = set(map(int, re.findall(r'^\[(\d+)\] ', text, re.M)))
    if refs != set(range(1, 47)):
        raise AssertionError('Expected unchanged references 1 through 46')
    prose = text.split('## 参考文献')[0] + text.split('## 附录A')[1]
    used = set(map(int, re.findall(r'\[(\d+)\]', prose)))
    if used - refs:
        raise AssertionError('Unresolved references: ' + repr(sorted(used - refs)))
    tables = placeholder_tables(text)
    if not tables or tables[0]['number'] != '5-5':
        raise AssertionError('Placeholder tables must begin with table 5-5')
    numbers = [int(table['number'].split('-')[1]) for table in tables]
    if numbers != list(range(5, numbers[-1] + 1)):
        raise AssertionError('Added table sequence has a gap or duplicate: ' + repr(numbers))
    tokens = []
    numeric_cells = 0
    for table in tables:
        if '预期情景占位' not in table['caption']:
            raise AssertionError('Caption lacks explicit placeholder label: ' + table['caption'])
        if '全部为人为设定的占位值，非实测' not in table['note']:
            raise AssertionError('Missing immediate non-measured table note: ' + table['number'])
        for row_index, row in enumerate(table['rows'][1:], 2):
            for col_index, cell in enumerate(row, 1):
                matches = list(NUMBER.finditer(base.clean_inline(cell)))
                numeric_cells += bool(matches)
                for match in matches:
                    rest = base.clean_inline(cell)[match.end():]
                    suffix = re.match(r'(?:%?P%?)', rest)
                    if suffix is None:
                        raise AssertionError(
                            f"Table {table['number']} row {row_index}, cell {col_index}: "
                            f'numeric value lacks P suffix: {cell!r}')
                    tokens.append(match[0] + suffix[0])
    if not tokens:
        raise AssertionError('No explicitly suffixed placeholder values were found')
    return {
        **preserved, 'references': len(refs), 'missing_citations': sorted(used - refs),
        'unused_references': sorted(refs - used), 'original_hashes': old_hashes,
        'placeholder_tables': [table['number'] for table in tables],
        'placeholder_numeric_cells': numeric_cells, 'placeholder_value_count': len(tokens),
        'placeholder_values': dict(Counter(tokens)),
        'source_sha256': sha256(source),
    }


class Builder(base.Builder):
    """Only the explicit placeholder labels and new table captions change layout."""

    def __init__(self, template, lines, toc_pages):
        super().__init__(template, lines, toc_pages)
        self.doc.settings.odd_and_even_pages_header_footer = False
        self.mark_header(self.doc.sections[0])

    def mark_header(self, section):
        section.different_first_page_header_footer = False
        section.header.is_linked_to_previous = False
        for child in list(section.header._element):
            section.header._element.remove(child)
        paragraph = section.header.add_paragraph()
        paragraph.alignment = base.WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = base.Pt(0)
        paragraph.paragraph_format.space_before = base.Pt(0)
        paragraph.paragraph_format.space_after = base.Pt(0)
        base.font_run(paragraph.add_run(WARNING), 9, True)

    def cover(self):
        super().cover()
        for paragraph in self.doc.paragraphs:
            if paragraph.text == '0920-v1修订稿':
                paragraph.clear()
                base.font_run(paragraph.add_run(WARNING), 12, True)
            elif paragraph.text == '2026年9月20日':
                paragraph.clear()
                base.font_run(paragraph.add_run('2026年9月23日'))

    def body_section(self):
        super().body_section()
        self.mark_header(self.doc.sections[-1])

    def body(self):
        super().body()
        for paragraph in self.doc.paragraphs:
            if re.match(r'^表5-\d+P(?:\s|$)', paragraph.text):
                paragraph.alignment = base.WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.keep_with_next = True
                paragraph.paragraph_format.first_line_indent = base.Pt(0)
                for run in paragraph.runs:
                    base.font_run(run, 11)

    def save(self, output):
        self.doc.core_properties.title = base.TITLE
        self.doc.core_properties.subject = WARNING
        self.doc.core_properties.author = 'Chen Tang'
        self.doc.core_properties.keywords = '预期数值占位稿 非实测 勿送审 P placeholder'
        for paragraph in self.doc._element.xpath('.//w:p'):
            prop = paragraph.find(base.qn('w:pPr'))
            if prop is not None and paragraph.index(prop):
                paragraph.remove(prop)
                paragraph.insert(0, prop)
        self.doc.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--template', type=Path, default=TEMPLATE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--toc-map', type=Path, default=WORK / 'toc_pages.json')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if Path(sys.executable).resolve() != BUNDLED_PYTHON.resolve():
        raise SystemExit('Use the bundled Python interpreter: ' + str(BUNDLED_PYTHON))
    base.self_test()
    if not args.source.exists():
        raise SystemExit('Manuscript is not available yet: ' + str(args.source))
    lines = base.load_manuscript(args.source)
    counts = base.preflight(lines)
    audit = source_audit(args.source)
    if args.check_only:
        print(json.dumps({'status': 'OK', 'source': str(args.source), **counts, **audit},
                         ensure_ascii=False, indent=2))
        return
    protected = {ROOT / name for name in BASELINE_HASHES} | {args.source, args.template}
    if args.output.resolve() in {path.resolve() for path in protected}:
        raise ValueError('A retained template/source must not be overwritten')
    template_hash = sha256(args.template)
    toc_pages = json.loads(args.toc_map.read_text(encoding='utf-8')) if args.toc_map.exists() else {}
    builder = Builder(args.template, lines, toc_pages)
    builder.cover()
    builder.body()
    builder.save(args.output)
    baseline_check()
    if sha256(args.template) != template_hash:
        raise AssertionError('Retained template changed unexpectedly')
    report = {
        'output': str(args.output), 'template': str(args.template),
        'template_sha256': template_hash, 'native_equation_count': builder.math_count,
        'table_count': len(builder.doc.tables), 'paragraph_count': len(builder.doc.paragraphs),
        'cjk_font': base.CN, 'math_font': base.MATH, 'warning': WARNING,
        'toc_page_map_loaded': bool(toc_pages), 'rendered_or_visually_verified': False,
        **counts, **audit,
    }
    (WORK / 'docx_build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
