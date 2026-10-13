"""Assemble the approved structural revision and audit preserved evidence.

This is a local mechanical assembly/audit, not an ARS authorization or academic
verification certificate. All old sources remain byte-identical.
"""
from __future__ import annotations

from collections import Counter
import difflib
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'report_1007_v1_full.md'
OUT = ROOT / 'report_1007_v2_full.md'
BASE_HASHES = {
    'report_1007_v1_full.md': '47f6736ae3d5f699f950d459d766bd36a42561f362aefa7f8d5952573f75127a',
    'report_1007_v1_full.docx': 'e7e86b26385e5e2a858cc54830817ea7c11d3652a76c3a85103a328161db51e9',
    '打印论文版本.pdf': 'f9a6a7775eb64d6309d4733fa8afbf30f2a03f3a2dbe29500ffceedf58bfbcab',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(text, start, end=None):
    begin = text.index(start)
    finish = text.index(end, begin) if end else len(text)
    return text[begin:finish].strip()


def table(text, number):
    # Captions are independent lines, not prose mentions.
    found = re.search(r'^表' + re.escape(number) + r'\s+[^\n]+\n\s*\n((?:\|[^\n]+\n)+)', text, re.M)
    if found is None:
        raise AssertionError('Missing table ' + number)
    return found[1].rstrip()


def main():
    for name, expected in BASE_HASHES.items():
        assert digest(ROOT / name) == expected, 'Baseline modified: ' + name
    old = BASE.read_text(encoding='utf-8')
    archive_sections = [
        ('版本说明', '## 版本说明', '## 摘要'),
        ('原5.1证据状态', '### 5.1 ', '### 5.2 '),
        ('原5.5组合与验收标准', '### 5.5 ', '### 5.6 '),
        ('原5.6.2诊断说明', '#### 5.6.2 ', '### 5.7 '),
        ('原5.8.7转实证稿待办', '#### 5.8.7 ', '### 5.9 '),
        ('原附录A核验清单', '## 附录A ', '## 附录B '),
        ('原附录D工程状态', '## 附录D ', '## 附录E '),
        ('原附录F.3阅读与待办', '### F.3 ', None),
    ]
    archive = ['# 1007-v1工作记录保留档',
               '以下为结构重组中移出或改写的工作性记录原文，按旧稿位置保存，'
               '仅用于修订追溯；其中旧章节和表号不作为新版正文交叉引用。'
               '与正文仍有重合的历史事实以新版相应章节界定其使用范围。']
    for label, start, end in archive_sections:
        archive.extend(['## 保留项 ' + label, extract(old, start, end)])
    (WORK / 'retained_work_notes.md').write_text('\n\n'.join(archive) + '\n', encoding='utf-8')
    names = ['front_chapter1.md', 'chapter2.md', 'chapter3.md', 'chapter4.md', 'chapter5_6.md']
    parts = [(WORK / name).read_text(encoding='utf-8').strip() for name in names]
    references = extract(old, '## 参考文献', '## 附录A')
    appendix_e = extract(old, '## 附录E', '## 附录F')
    parts.extend([references, (WORK / 'appendix_ad.md').read_text(encoding='utf-8').strip(),
                  appendix_e, (WORK / 'appendix_f.md').read_text(encoding='utf-8').strip()])
    new = '\n\n'.join(parts) + '\n'
    assert extract(new, '## 参考文献', '## 附录A') == references
    assert extract(new, '## 附录E', '## 附录F') == appendix_e
    old_equations = re.findall(r'\$\$(.*?)\$\$', old, re.S)
    new_equations = re.findall(r'\$\$(.*?)\$\$', new, re.S)
    assert old_equations == new_equations, 'A display formula changed or was reordered'
    migrations = {'5-2': '3-2', '5-3': '4-2', '5-5': '5-1',
                  '5-6': '3-3', '5-7': '4-3', '5-8': '4-4',
                  '5-9': '4-5', '5-10': '4-6'}
    for original, revised in migrations.items():
        assert table(old, original) == table(new, revised), (original, revised)
    for preserved in ['3-1', '4-1'] + [f'E-{i}' for i in range(1, 10)]:
        assert table(old, preserved) == table(new, preserved), preserved
    numeric_p = r'(?<![\d.])\d+(?:\.\d+)?%?P%?'
    old_p, new_p = Counter(re.findall(numeric_p, old)), Counter(re.findall(numeric_p, new))
    assert old_p == new_p, {'old': old_p, 'new': new_p}
    refs = set(map(int, re.findall(r'^\[(\d+)\] ', new, re.M)))
    prose = new.split('## 参考文献')[0] + new.split('## 附录A')[1]
    cited = set(map(int, re.findall(r'\[(\d+)\]', prose)))
    assert refs == set(range(1, 47))
    assert not (cited - refs), sorted(cited - refs)
    assert not (refs - cited), sorted(refs - cited)
    headings = re.findall(r'^(#{2,}) (.+)$', new, re.M)
    assert all(len(level) <= 4 for level, _ in headings)
    captions = re.findall(r'^(表|图)([1-6A-F]-\d+)\s+(.+)$', new, re.M)
    caption_ids = [kind + number for kind, number, _ in captions]
    assert len(caption_ids) == len(set(caption_ids)), 'Duplicate captions'
    prose_refs = set(re.findall(r'(?:表|图)[1-6A-F]-\d+', re.sub(r'^\[\d+\].*$', '', new, flags=re.M)))
    missing = sorted(prose_refs - set(caption_ids))
    assert not missing, missing
    numeric_heads = [title.split()[0] for _, title in headings if re.match(r'^[1-6]\.\d', title)]
    assert len(numeric_heads) == len(set(numeric_heads)), 'Duplicate numbered headings'
    images = re.findall(r'^!\[([^]]*)\]\(([^)]+)\)$', new, re.M)
    assert len(images) == 7, images
    for _, path in images:
        assert path.startswith('_revision_1007_v2/figures/'), path
    assert '训练增强不是对论文正文的润色' not in new
    assert '## 版本说明' not in new
    assert '#### 5.8.7' not in new
    OUT.write_text(new, encoding='utf-8')
    diff = ''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile=BASE.name, tofile=OUT.name))
    (WORK / 'revision.diff').write_text(diff, encoding='utf-8')
    report = {
        'baseline_hashes': BASE_HASHES, 'output': str(OUT), 'source_sha256': digest(OUT),
        'old_sources_unchanged': True, 'references_count': len(refs),
        'references_verbatim': True, 'appendix_E_verbatim': True,
        'display_equations_verbatim_in_order': len(new_equations),
        'table_migrations_body_verbatim': migrations,
        'placeholder_tokens_unchanged': sum(new_p.values()),
        'missing_citations': [], 'unused_references': [], 'missing_figure_table_targets': [],
        'heading_levels': dict(Counter(len(level) - 1 for level, _ in headings)),
        'table_count': sum(kind == '表' for kind, _, _ in captions),
        'figure_count': len(images), 'images': [{'alt': alt, 'path': path} for alt, path in images],
        'line_count': len(new.splitlines()),
        'layout_checked': False, 'empirical_results_added': False,
        'authority_boundary': 'Explicit user-authorized structural revision; not an ARS formal authorization PASS',
    }
    (WORK / 'content_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
