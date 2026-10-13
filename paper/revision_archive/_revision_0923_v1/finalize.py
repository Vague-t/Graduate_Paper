"""Add review comments, extract rendered TOC pages, and audit the 0923 draft.

This script never launches LibreOffice. Any render must use the packaged
renderer and the bundled absolute LibreOffice path documented in build_docx.py.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

from lxml import etree
from pypdf import PdfReader

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent
spec = importlib.util.spec_from_file_location('placeholder_0923_builder', WORK / 'build_docx.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
DOCX, MD = build.OUTPUT, build.SOURCE
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
      'r': 'http://schemas.openxmlformats.org/package/2006/relationships',
      'ct': 'http://schemas.openxmlformats.org/package/2006/content-types'}


def selected_comments():
    """Read only the legacy constant; importing its CLI would run argparse."""
    tree = ast.parse((ROOT / '_revision_0920_v1/finalize.py').read_text(encoding='utf-8'))
    legacy = next(ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == 'COMMENTS'
                          for target in node.targets))
    text = MD.read_text(encoding='utf-8')
    chosen = [(anchor, note) for anchor, note in legacy if anchor in text]
    tables = build.placeholder_tables(text)
    chosen.extend([
        (build.WARNING, '本文件是作者授权的预期数值占位稿。P表示placeholder，所有新增P值均为人为设定且非实测；不得据此判断性能、显著性或送审成熟度。'),
        (tables[0]['caption'], '表5-5及以后的预期情景表仅用于组织结果与讨论。逐个P单元格替换为可追溯的实测值后，才能重新分析、删除占位标识并形成正式结论；附录E历史值未改动。'),
    ])
    return chosen


def comments():
    build.source_audit()
    with ZipFile(DOCX) as current:
        if 'word/comments.xml' in current.namelist():
            xml = etree.fromstring(current.read('word/comments.xml'))
            if xml.xpath('//w:comment', namespaces=NS):
                raise SystemExit('Comments already exist; rebuild before applying this deterministic step again')
    chosen = selected_comments()
    helper = '/Users/channtang/.codex/plugins/cache/openai-primary-runtime/documents/26.909.61513/skills/documents/scripts/comments_add.py'
    staged = WORK / 'commented.docx'
    args = [sys.executable, helper, str(DOCX), '--out', str(staged),
            '--author', 'Codex 0923-v1 占位稿修订', '--require_all']
    for anchor, note in chosen:
        args += ['--add', anchor + '=' + note]
    subprocess.run(args, check=True)
    with ZipFile(staged) as source:
        root = etree.fromstring(source.read('word/document.xml'))
        for paragraph in root.xpath('//w:p[w:pPr]', namespaces=NS):
            prop = paragraph.find('{' + NS['w'] + '}pPr')
            if paragraph.index(prop):
                paragraph.remove(prop)
                paragraph.insert(0, prop)
        body = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        with ZipFile(DOCX, 'w') as output:
            for info in source.infolist():
                output.writestr(info, body if info.filename == 'word/document.xml'
                                else source.read(info.filename))
    (WORK / 'comment_log.json').write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Added {len(chosen)} review comments')


def pdf_toc(path):
    pdf = PdfReader(path)
    heads = [x for x in re.findall(r'^## (.+)$', MD.read_text(encoding='utf-8'), re.M)
             if re.match(r'^第.+章 |^附录[A-E] |^参考文献$', x)]
    compact = lambda value: re.sub(r'\s+', '', value)
    candidates, unlabelled = {}, []
    for index, page in enumerate(pdf.pages):
        content = compact(page.extract_text() or '')
        if compact(build.WARNING) not in content:
            unlabelled.append(index + 1)
        if '第一章绪论' in content and '第二章任务表示' in content:
            continue
        for head in heads:
            if compact(head) in content:
                candidates.setdefault(head, []).append(index)
    if unlabelled:
        raise AssertionError('Rendered pages without required placeholder warning: ' + repr(unlabelled))
    if not all(head in candidates for head in heads):
        raise AssertionError(candidates)
    starts = {head: values[0] for head, values in candidates.items()}
    first = starts['第一章 绪论']
    mapping = {head: index - first + 1 for head, index in starts.items()}
    (WORK / 'toc_pages.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {'physical_pages': len(pdf.pages), 'body_start_physical': first + 1,
               'all_pages_labelled_nonmeasured': True, 'toc': mapping}
    (WORK / 'pagination.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def audit():
    result = build.source_audit()
    source_text = MD.read_text(encoding='utf-8')
    source_tables = build.placeholder_tables(source_text)
    with ZipFile(DOCX) as archive:
        xml = etree.fromstring(archive.read('word/document.xml'))
        visible = ''.join(xml.xpath('//w:t/text() | //m:t/text()', namespaces=NS))
        if any(marker in visible for marker in ('<!--', '-->', 'anchor:section', 'ref:tang')):
            raise AssertionError('Source-only HTML or anchor marker leaked into visible DOCX text')
        if re.search(r'</?(?:a|br|div|span|section|sup|sub|p|b|strong|em|i|table|tr|td|th)(?:\s+[^<>]{0,300})?\s*/?>', visible, re.I):
            raise AssertionError('Raw HTML leaked into visible DOCX text')
        if build.WARNING not in visible:
            raise AssertionError('Cover lacks explicit non-measured warning')
        expected_math = build.base.preflight(build.base.load_manuscript(MD))
        math_count = len(xml.xpath('//m:oMath', namespaces=NS))
        assert math_count == expected_math['display_equations'] + expected_math['inline_equations']
        assert not xml.xpath('//w:sectPr/w:titlePg[not(@w:val="0" or @w:val="false" or @w:val="off")]', namespaces=NS), 'First-page headers must not be hidden'
        settings = etree.fromstring(archive.read('word/settings.xml'))
        assert not settings.xpath('//w:evenAndOddHeaders[not(@w:val="0" or @w:val="false" or @w:val="off")]', namespaces=NS), 'Unexpected separate odd/even headers'
        rels = etree.fromstring(archive.read('word/_rels/document.xml.rels'))
        targets = {rel.get('Id'): rel.get('Target') for rel in rels}
        headers = []
        for section in xml.xpath('//w:sectPr', namespaces=NS):
            size = section.find('{' + NS['w'] + '}pgSz')
            assert size is not None
            assert abs(int(size.get('{' + NS['w'] + '}w')) - 11906) <= 2
            assert abs(int(size.get('{' + NS['w'] + '}h')) - 16838) <= 2
            refs = section.xpath('./w:headerReference[@w:type="default"]', namespaces=NS)
            assert len(refs) == 1, 'Each section needs an explicit default warning header'
            rid = refs[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            target = targets[rid]
            part = target.lstrip('/') if target.startswith('/') else 'word/' + target
            header = etree.fromstring(archive.read(part))
            assert build.WARNING in ''.join(header.xpath('//w:t/text()', namespaces=NS))
            headers.append(part)
        field_text = []
        for name in archive.namelist():
            if re.fullmatch(r'word/footer\d+\.xml', name):
                footer = etree.fromstring(archive.read(name))
                field_text.extend(footer.xpath('//w:fldSimple/@w:instr | //w:instrText/text()', namespaces=NS))
        assert any(re.search(r'\bPAGE\b', text) for text in field_text), 'Native page field is missing'
        children = list(xml.find('{' + NS['w'] + '}body'))
        for table in source_tables:
            caption = next((i for i, item in enumerate(children)
                            if table['caption'] == ''.join(item.xpath('.//w:t/text()', namespaces=NS))), None)
            assert caption is not None, table['caption']
            actual = next(item for item in children[caption + 1:] if item.tag == '{' + NS['w'] + '}tbl')
            actual_rows = [[ ''.join(cell.xpath('.//w:t/text() | .//m:t/text()', namespaces=NS))
                            for cell in row.findall('{' + NS['w'] + '}tc')]
                           for row in actual.findall('{' + NS['w'] + '}tr')]
            for expected, actual_row in zip(table['rows'], actual_rows, strict=True):
                for expected_cell, actual_cell in zip(expected, actual_row, strict=True):
                    expected_values = Counter(re.findall(r'\d+(?:\.\d+)?%?P%?', expected_cell))
                    actual_values = Counter(re.findall(r'\d+(?:\.\d+)?%?P%?', actual_cell))
                    assert expected_values == actual_values, (table['number'], expected_cell, actual_cell)
        comment_xml = etree.fromstring(archive.read('word/comments.xml'))
        comment_ids = comment_xml.xpath('//w:comment/@w:id', namespaces=NS)
        assert len(comment_ids) == len(selected_comments())
        for kind in ('commentRangeStart', 'commentRangeEnd', 'commentReference'):
            ids = xml.xpath('//w:' + kind + '/@w:id', namespaces=NS)
            assert Counter(ids) == Counter(comment_ids), (kind, ids)
        assert any(rel.get('Type', '').endswith('/comments') for rel in rels)
        types = etree.fromstring(archive.read('[Content_Types].xml'))
        assert types.xpath('ct:Override[@PartName="/word/comments.xml"]', namespaces=NS)
        result.update({'native_equations': math_count, 'comments': len(comment_ids),
                       'warning_headers': headers, 'all_placeholder_cells_preserved': True,
                       'native_page_field_present': True, 'html_markers_hidden': True,
                       'output_md_sha256': build.sha256(MD), 'output_docx_sha256': build.sha256(DOCX)})
    (WORK / 'final_content_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comments', action='store_true')
    parser.add_argument('--toc', type=Path)
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--check-only', action='store_true', help='Audit Markdown only; write nothing')
    args = parser.parse_args()
    if Path(sys.executable).resolve() != build.BUNDLED_PYTHON.resolve():
        raise SystemExit('Use the bundled Python interpreter: ' + str(build.BUNDLED_PYTHON))
    if args.check_only:
        if args.comments or args.toc or args.audit:
            raise SystemExit('--check-only cannot be combined with write actions')
        print(json.dumps(build.source_audit(), ensure_ascii=False, indent=2))
        return
    if args.comments:
        comments()
    if args.toc:
        pdf_toc(args.toc)
    if args.audit:
        audit()


if __name__ == '__main__':
    main()
