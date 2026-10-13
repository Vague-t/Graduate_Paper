"""Apply only the author-approved V3-10 withdrawal to the retained package."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

from lxml import etree

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent.parent
BEFORE = WORK / 'before'
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

CHANGES = [
    ('共同成果与个人分工的说明保留在附录C，最终成果页需依据正式材料由作者核准。',
     '前期共同成果的来源见附录C.1。'),
    ('本人分工、合作贡献及发表状态需依据正式材料核准，不仅根据署名顺序推断。', ''),
]
DELETE = '作者贡献说明采用研究构思、方法设计、软件、验证、数据整理、初稿和修订等角色描述实际工作。当前共同作者之间的具体分工尚未由作者确认，本版不代填个人贡献比例或CRediT角色归属。'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paragraph_text(p):
    return ''.join(p.xpath('.//w:t/text()', namespaces=NS))


def replace_text(p, old, new):
    original = paragraph_text(p)
    assert original.count(old) == 1
    start, stop = original.index(old), original.index(old) + len(old)
    offset, inserted = 0, False
    for node in p.xpath('.//w:t', namespaces=NS):
        s = node.text or ''
        end = offset + len(s)
        if offset < stop and end > start:
            left, right = max(0, start - offset), min(len(s), stop - offset)
            node.text = s[:left] + (new if not inserted else '') + s[right:]
            inserted = True
        offset = end
    assert paragraph_text(p) == original.replace(old, new)


def main():
    src = BEFORE / 'report_1008_v3_full.docx'
    dst = ROOT / src.name
    assert digest(src) == '53112cfaf0a0c48623f56c1e483aae43711d2d0d9fb685947d99c806632cf28e'
    assert digest(dst) == digest(src), 'Do not overwrite changes outside this run'
    with zipfile.ZipFile(src) as z:
        body = etree.fromstring(z.read('word/document.xml'))
        original_paragraphs = [paragraph_text(p) for p in body.xpath('//w:p', namespaces=NS)]
        for old, new in CHANGES:
            targets = [p for p in body.xpath('//w:p', namespaces=NS) if old in paragraph_text(p)]
            assert len(targets) == 1
            replace_text(targets[0], old, new)
        targets = [p for p in body.xpath('//w:p', namespaces=NS) if paragraph_text(p) == DELETE]
        assert len(targets) == 1
        targets[0].getparent().remove(targets[0])
        actual = [paragraph_text(p) for p in body.xpath('//w:p', namespaces=NS)]
        expected = []
        for p in original_paragraphs:
            if p == DELETE:
                continue
            for old, new in CHANGES:
                p = p.replace(old, new)
            expected.append(p)
        assert actual == expected
        xml = etree.tostring(body, xml_declaration=True, encoding='UTF-8', standalone=True)
        with zipfile.ZipFile(dst, 'w') as out:
            for item in z.infolist():
                out.writestr(item, xml if item.filename == 'word/document.xml' else z.read(item.filename))
    with zipfile.ZipFile(src) as old, zipfile.ZipFile(dst) as new:
        assert new.testzip() is None
        changed_parts = [n for n in old.namelist() if old.read(n) != new.read(n)]
        assert changed_parts == ['word/document.xml'], changed_parts
    old_md = (BEFORE / 'report_1008_v3_full.md').read_text()
    expected_md = old_md
    for old, new in CHANGES:
        expected_md = expected_md.replace(old, new)
    expected_md = expected_md.replace(DELETE + '\n\n', '')
    actual_md = (ROOT / 'report_1008_v3_full.md').read_text()
    assert expected_md == actual_md, 'Markdown has an unexpected edit'
    for token in ['本人分工', '个人分工', 'CRediT', '个人贡献比例']:
        assert token not in actual_md and token not in '\n'.join(actual)
    for pattern in [r'\$\$(.*?)\$\$', r'<!--ref:.*?-->', r'\d+(?:\.\d+)?%?P%?']:
        assert re.findall(pattern, old_md, re.S) == re.findall(pattern, actual_md, re.S)
    result = {
        'scope': 'V3-10 withdrawal only; not a formal ARS integrity verdict',
        'paragraphs_replaced': 2, 'paragraphs_deleted': 1,
        'all_other_paragraphs_unchanged': True,
        'changed_docx_parts': changed_parts,
        'md_matches_exact_approved_patch': True,
        'source_sha256': digest(ROOT / 'report_1008_v3_full.md'),
        'docx_sha256': digest(dst),
        'original_files_preserved': str(BEFORE),
    }
    (WORK / 'patch_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
