"""1007 comments, static TOC page extraction, and structural fidelity checks."""
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
spec = importlib.util.spec_from_file_location('complete_1007', WORK / 'build_docx.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
DOCX, MD = build.OUTPUT, build.SOURCE
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
      'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
      'ct': 'http://schemas.openxmlformats.org/package/2006/content-types'}
SKILL = Path('/Users/channtang/.codex/plugins/cache/openai-primary-runtime/documents/26.1005.12141/skills/documents')


def selected_comments():
    tree = ast.parse((ROOT / '_revision_0920_v1/finalize.py').read_text(encoding='utf-8'))
    old = next(ast.literal_eval(item.value) for item in tree.body
               if isinstance(item, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'COMMENTS' for t in item.targets))
    text = MD.read_text(encoding='utf-8')
    chosen = [(anchor, note) for anchor, note in old if anchor in text]
    chosen.extend([
        (build.WARNING, '完整修订稿指文本与方法框架合并完整。第五章的P数值仍为人工写作占位，所有方法图均为机制示意；本版没有增加正式实验或送审认证。'),
        ('图2-1', '训练与测试分列；辅助分类头仅参与训练，不将推理修正结果回传为测试时训练监督。'),
        ('图3-1', '内部/跨边界是位置维度，Support/NONE是状态维度。NONE在图中只作标签说明，不输出为关系边。'),
        ('图4-1', '旧短跨度和新完整跨度是不同语义对象。旧组件全部关联关系失效，新关系重新判断，不能默认继承Support。'),
        ('附录F 符号与阅读索引', '新增阅读与实现核查入口，不改变原有数学定义、历史数值或证据等级。'),
    ])
    return chosen


def comments():
    build.source_audit()
    with ZipFile(DOCX) as current:
        if 'word/comments.xml' in current.namelist():
            existing = etree.fromstring(current.read('word/comments.xml'))
            assert not existing.xpath('//w:comment', namespaces=NS), 'Rebuild before adding comments again'
    chosen = selected_comments()
    staged = WORK / 'commented.docx'
    args = [sys.executable, str(SKILL / 'scripts/comments_add.py'), str(DOCX), '--out', str(staged),
            '--author', 'Codex 1007-v1 修订', '--require_all']
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
                output.writestr(info, body if info.filename == 'word/document.xml' else source.read(info.filename))
    (WORK / 'comment_log.json').write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Added {len(chosen)} comments')


def pdf_toc(path):
    pdf = PdfReader(path)
    heads = [item for item in re.findall(r'^## (.+)$', MD.read_text(encoding='utf-8'), re.M)
             if re.match(r'^第.+章 |^附录[A-F] |^参考文献$', item)]
    compact = lambda value: re.sub(r'\s+', '', value)
    candidates, unlabelled = {}, []
    pages = []
    for index, page in enumerate(pdf.pages):
        text = page.extract_text() or ''
        content = compact(text)
        pages.append({'page': index + 1, 'characters': len(content)})
        if compact(build.WARNING) not in content:
            unlabelled.append(index + 1)
        if '第一章绪论' in content and '第二章任务表示' in content:
            continue
        for head in heads:
            if compact(head) in content:
                candidates.setdefault(head, []).append(index)
    assert not unlabelled, unlabelled
    assert all(head in candidates for head in heads), candidates
    starts = {head: values[0] for head, values in candidates.items()}
    first = starts['第一章 绪论']
    mapping = {head: index - first + 1 for head, index in starts.items()}
    map_path = WORK / 'toc_pages.json'
    previous = json.loads(map_path.read_text(encoding='utf-8')) if map_path.exists() else None
    map_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    result = {'pdf': str(path), 'physical_pages': len(pdf.pages), 'body_start_physical': first + 1,
              'all_pages_labelled_nonmeasured': True, 'mapping_stable': previous == mapping,
              'toc': mapping, 'pages': pages}
    (WORK / 'pagination.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'pages'}, ensure_ascii=False, indent=2))


def audit():
    result = build.source_audit()
    expected = build.base.preflight(build.base.load_manuscript(MD))
    with ZipFile(DOCX) as z, ZipFile(build.TEMPLATE) as retained:
        xml = etree.fromstring(z.read('word/document.xml'))
        visible = ''.join(xml.xpath('//w:t/text() | //m:t/text()', namespaces=NS))
        assert all(token not in visible for token in ('<!--', '-->', 'anchor:section', 'ref:tang', '!['))
        assert not re.search(r'</?(?:a|br|div|span|section|sup|sub|p|b|strong|em|i)(?:\s+[^<>]{0,300})?\s*/?>', visible, re.I)
        assert build.WARNING in visible
        math_count = len(xml.xpath('//m:oMath', namespaces=NS))
        assert math_count == expected['display_equations'] + expected['inline_equations']
        drawings = xml.xpath('//wp:inline', namespaces=NS)
        assert len(drawings) == 3 and not xml.xpath('//wp:anchor', namespaces=NS)
        assert all(int(item.find('{' + NS['wp'] + '}extent').get('cx')) <= 5654000 for item in drawings)
        assert all(item.find('{' + NS['wp'] + '}docPr').get('descr') for item in drawings)
        # Keep paragraph/cell boundaries; concatenating T0 with the next cell's
        # 84.0P would manufacture an 084.0P token. Placeholder data is prose,
        # never a native mathematical P symbol.
        prose = '\n'.join(''.join(item.xpath('.//w:t/text()', namespaces=NS))
                          for item in xml.xpath('//w:p', namespaces=NS))
        assert Counter(build.PLACEHOLDER.findall(prose)) == Counter(build.PLACEHOLDER.findall(MD.read_text(encoding='utf-8')))
        assert not xml.xpath('//w:sectPr/w:titlePg[not(@w:val="0" or @w:val="false" or @w:val="off")]', namespaces=NS)
        assert '附录F 符号与阅读索引' in visible
        rels = etree.fromstring(z.read('word/_rels/document.xml.rels'))
        targets = {item.get('Id'): item.get('Target') for item in rels}
        headers = []
        sections = xml.xpath('//w:sectPr', namespaces=NS)
        assert len(sections) == 2
        for section in sections:
            size = section.find('{' + NS['w'] + '}pgSz')
            assert abs(int(size.get('{' + NS['w'] + '}w')) - 11906) <= 2
            assert abs(int(size.get('{' + NS['w'] + '}h')) - 16838) <= 2
            refs = section.xpath('./w:headerReference[@w:type="default"]', namespaces=NS)
            assert len(refs) == 1
            rid = refs[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            target = targets[rid]
            part = target.lstrip('/') if target.startswith('/') else 'word/' + target
            assert build.WARNING in ''.join(etree.fromstring(z.read(part)).xpath('//w:t/text()', namespaces=NS))
            headers.append(part)
        assert any(b'PAGE' in z.read(name) for name in z.namelist() if re.fullmatch(r'word/footer\d+\.xml', name))
        comments_xml = etree.fromstring(z.read('word/comments.xml'))
        ids = comments_xml.xpath('//w:comment/@w:id', namespaces=NS)
        assert len(ids) == len(selected_comments())
        for element in ('commentRangeStart', 'commentRangeEnd', 'commentReference'):
            assert Counter(ids) == Counter(xml.xpath('//w:' + element + '/@w:id', namespaces=NS))
        assert any(item.get('Type', '').endswith('/comments') for item in rels)
        types = etree.fromstring(z.read('[Content_Types].xml'))
        assert types.xpath('ct:Override[@PartName="/word/comments.xml"]', namespaces=NS)
        preserved_parts = [name for name in ('word/styles.xml', 'word/stylesWithEffects.xml', 'word/numbering.xml', 'word/theme/theme1.xml') if name in retained.namelist()]
        assert all(z.read(name) == retained.read(name) for name in preserved_parts)
        result.update({'native_equations': math_count, 'comments': len(ids), 'inline_figures': len(drawings),
                       'warning_headers': headers, 'preserved_package_parts': preserved_parts,
                       'html_markers_hidden': True, 'output_md_sha256': build.sha256(MD),
                       'output_docx_sha256': build.sha256(DOCX)})
    (WORK / 'final_content_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comments', action='store_true')
    parser.add_argument('--toc', type=Path)
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    assert Path(sys.executable).resolve() == build.BUNDLED_PYTHON.resolve()
    if args.check_only:
        assert not (args.comments or args.toc or args.audit)
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
