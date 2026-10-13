"""Build the complete 1007 manuscript with inherited A4 styles and native OMML.

Only this task's output files may change. Rendering must use the packaged
render_docx.py and bundled LibreOffice, never the desktop application:
/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/MacOS/soffice
The parent has already run the single artifact-operation marker.
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
SOURCE = ROOT / 'report_1007_v1_full.md'
OUTPUT = ROOT / 'report_1007_v1_full.docx'
TEMPLATE = ROOT / 'report_0923_v1_placeholder.docx'
WARNING = '1007-v1 完整修订稿 含非实测占位 勿送审'
spec = importlib.util.spec_from_file_location('retained_0923', ROOT / '_revision_0923_v1/build_docx.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
legacy.WARNING = WARNING
base = legacy.base
BUNDLED_PYTHON = base.BUNDLED_PYTHON
BASELINE_HASHES = {
    **legacy.BASELINE_HASHES,
    'report_0923_v1_placeholder.md': '1bc8e3639f0008f55c9695c3c550ae9a07264d0f9669d644238f76d6ce99e6bd',
    'report_0923_v1_placeholder.docx': 'b66943d2eb8c7f8c899f723c5f9f70529929daf33790bee0d8422907055956b5',
}
IMAGE = re.compile(r'^!\[([^\]]*)\]\(([^)]+)\)$')
PLACEHOLDER = re.compile(r'(?<![\d.])\d+(?:\.\d+)?%?P%?')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def baseline_check():
    hashes = {name: sha256(ROOT / name) for name in BASELINE_HASHES}
    assert hashes == BASELINE_HASHES, hashes
    return hashes


def section(text, begin, end=None):
    found = re.search(r'^' + re.escape(begin) + r'.*$', text, re.M)
    assert found is not None, begin
    rest = text[found.start():]
    if end:
        match = re.search(r'^' + re.escape(end) + r'.*$', rest, re.M)
        assert match is not None, end
        rest = rest[:match.start()]
    return rest.rstrip('\n')


def source_audit():
    hashes = baseline_check()
    old = (ROOT / 'report_0923_v1_placeholder.md').read_text(encoding='utf-8')
    text = SOURCE.read_text(encoding='utf-8')
    assert section(text, '## 参考文献', '## 附录A') == section(old, '## 参考文献', '## 附录A')
    assert section(text, '## 附录E', '## 附录F') == section(old, '## 附录E')
    refs = set(map(int, re.findall(r'^\[(\d+)\] ', text, re.M)))
    assert refs == set(range(1, 47)), refs
    prose = text.split('## 参考文献')[0] + text.split('## 附录A')[1]
    citations = set(map(int, re.findall(r'\[(\d+)\]', prose)))
    assert not citations - refs
    new_tables, old_tables = legacy.placeholder_tables(text), legacy.placeholder_tables(old)
    assert len(new_tables) == len(old_tables) == 6
    for new, retained in zip(new_tables, old_tables):
        assert new['number'] == retained['number'] and new['rows'] == retained['rows'], new['number']
        assert '预期情景占位' in new['caption']
        assert '全部为人为设定的占位值，非实测' in new['note']
    p_values = Counter(PLACEHOLDER.findall(text))
    assert p_values == Counter(PLACEHOLDER.findall(old)), 'A placeholder value or suffix changed'
    figures = []
    for line in text.splitlines():
        image = IMAGE.fullmatch(line.strip())
        if image:
            path = (ROOT / image[2]).resolve()
            assert path.is_relative_to(WORK / 'figures'), path
            assert path.is_file(), path
            figures.append({'alt': image[1], 'path': str(path), 'sha256': sha256(path)})
    assert len(figures) == 3, figures
    return {'original_hashes': hashes, 'references': len(refs),
            'references_text_unchanged': True, 'appendix_E_verbatim': True,
            'placeholder_tables_unchanged': [item['number'] for item in new_tables],
            'all_placeholder_values_unchanged': True, 'placeholder_value_count': sum(p_values.values()),
            'missing_citations': sorted(citations - refs), 'unused_references': sorted(refs - citations),
            'figures': figures, 'source_sha256': sha256(SOURCE)}


class Builder(legacy.Builder):
    def cover(self):
        super().cover()
        for paragraph in self.doc.paragraphs:
            if paragraph.text == '2026年9月23日':
                paragraph.clear()
                base.font_run(paragraph.add_run('2026年10月7日'))

    def inline(self, paragraph, text, size=None):
        image = IMAGE.fullmatch(text.strip())
        if not image:
            return super().inline(paragraph, text, size)
        path = (ROOT / image[2]).resolve()
        if not path.is_relative_to(WORK / 'figures'):
            raise ValueError('Image is outside the task figures directory')
        fmt = paragraph.paragraph_format
        fmt.first_line_indent = base.Pt(0)
        fmt.line_spacing = 1
        fmt.space_before, fmt.space_after = base.Pt(6), base.Pt(4)
        fmt.keep_with_next = True
        paragraph.alignment = base.WD_ALIGN_PARAGRAPH.CENTER
        shape = paragraph.add_run().add_picture(str(path), width=self.text_width)
        shape._inline.docPr.set('descr', image[1] + '。方法机制示意，非实测案例。')
        shape._inline.docPr.set('name', path.name)

    def toc(self):
        heads = [value[1] for kind, value, _ in base.blocks(self.lines)
                 if kind == 'heading' and value[0] == 1
                 and (re.match(r'^第.+章\s', value[1])
                      or re.match(r'^附录[A-F](?:\s|$)', value[1])
                      or value[1] == '参考文献')]
        self.doc.add_heading('目录', 1)
        for name in heads:
            paragraph = self.doc.add_paragraph()
            fmt = paragraph.paragraph_format
            fmt.first_line_indent = base.Pt(0)
            fmt.space_after = base.Pt(11)
            fmt.line_spacing = 1.4
            fmt.tab_stops.add_tab_stop(base.Mm(150), base.WD_TAB_ALIGNMENT.RIGHT)
            self.inline(paragraph, name)
            if name in self.toc_pages:
                base.font_run(paragraph.add_run('\t' + str(self.toc_pages[name])), 12)

    def table(self, rows):
        super().table(rows)
        table = self.doc.tables[-1]
        count, first = len(rows[0]), rows[0][0]
        widths = {
            ('组件', 4): [15, 25, 86, 31],
            ('符号或术语', 3): [32, 56, 69],
            ('方法', 3): [37, 49, 71],
            ('要回答的问题', 3): [56, 34, 67],
        }.get((first, count))
        if widths:
            for col, width in zip(table.columns, widths):
                col.width = base.Mm(width)
            for row in table.rows:
                for cell, width in zip(row.cells, widths):
                    cell.width = base.Mm(width)

    def body(self):
        super().body()
        paragraphs = self.doc.paragraphs
        for index, paragraph in enumerate(paragraphs):
            text = paragraph.text
            if text.startswith('表4-1概括容易混淆的推理版本'):
                paragraph.paragraph_format.widow_control = True
                paragraph.paragraph_format.keep_together = True
            if (len(text.strip()) <= 24 and re.search(r'(?:定义|写为|可得|即|：|:)$', text.strip())
                    and index + 1 < len(paragraphs)
                    and paragraphs[index + 1]._p.xpath('.//m:oMath')):
                paragraph.paragraph_format.keep_with_next = True
            if re.match(r'^图\d+-\d+(?:\s|$)', text):
                paragraph.paragraph_format.keep_with_next = False
                paragraph.paragraph_format.keep_together = True
                paragraph.paragraph_format.space_after = base.Pt(8)
            if re.match(r'^表F-\d+(?:\s|$)', text):
                paragraph.alignment = base.WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.first_line_indent = base.Pt(0)
                paragraph.paragraph_format.keep_with_next = True
                for run in paragraph.runs:
                    base.font_run(run, 11)

    def save(self, output):
        update = self.doc.settings.element.find(base.qn('w:updateFields'))
        if update is None:
            update = base.OxmlElement('w:updateFields')
            self.doc.settings.element.append(update)
        update.set(base.qn('w:val'), 'true')
        super().save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    assert Path(sys.executable).resolve() == BUNDLED_PYTHON.resolve()
    base.self_test()
    lines = base.load_manuscript(SOURCE)
    counts = base.preflight(lines)
    audit = source_audit()
    if args.check_only:
        print(json.dumps({'status': 'OK', **counts, **audit}, ensure_ascii=False, indent=2))
        return
    mapping = WORK / 'toc_pages.json'
    toc = json.loads(mapping.read_text(encoding='utf-8')) if mapping.exists() else {}
    builder = Builder(TEMPLATE, lines, toc)
    builder.cover()
    builder.body()
    builder.save(OUTPUT)
    baseline_check()
    report = {'output': str(OUTPUT), 'template': str(TEMPLATE), 'warning': WARNING,
              'native_equations': builder.math_count, 'tables': len(builder.doc.tables),
              'images': len(builder.doc.inline_shapes), 'toc_page_map_loaded': bool(toc),
              'rendered_or_visually_verified': False, **counts, **audit}
    (WORK / 'docx_build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
