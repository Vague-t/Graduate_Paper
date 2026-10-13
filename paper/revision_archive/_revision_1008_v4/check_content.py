"""Audit preservation and scope of the v4 editorial patch, not empirical validity."""
from collections import Counter
from hashlib import sha256
import difflib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'report_1008_v3_full.md'
NEW = ROOT / 'report_1008_v4_full.md'
EXPECTED_BASE = {
    'report_1008_v3_full.md': 'fb3f9b4895c0c0ba5e719af80d76f4af322a6a4b20e0856829ae56bd8ee55886',
    'report_1008_v3_full.docx': 'e3cda7c0e31b57f908b6c89c685967c1b713c85646565de1a59ecc7968a752f1',
    '1008_v3问题清单.md': '97f71c384f39aa286ca43ffdf5bfe087ef8187c136ed0f14577a3c3d236e8ed3',
    '1008_v3逐项修改对照.md': 'b30a7166fb403176ae886603c12238ef75b043e23de1d47308f054843a753f4c',
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def region(text, begin, end):
    return text.split(begin, 1)[1].split(end, 1)[0]


def main():
    old, new = BASE.read_text(), NEW.read_text()
    for name, expected in EXPECTED_BASE.items():
        assert digest(ROOT / name) == expected, f'Baseline changed: {name}'
    maths = lambda text: re.findall(r'\$\$(.*?)\$\$', text, re.S)
    assert maths(old) == maths(new) and len(maths(new)) == 32
    refs = lambda text: region(text, '## 参考文献', '## 附录A')
    assert refs(old) == refs(new)
    assert re.findall(r'^\[(\d+)\]', refs(new), re.M) == [str(i) for i in range(1, 47)]
    historical = lambda text: region(text, '## 附录E', '## 附录F')
    assert historical(old) == historical(new)
    placeholder = r'(?<![\d.])\d+(?:\.\d+)?%?P%?'
    old_p, new_p = re.findall(placeholder, old), re.findall(placeholder, new)
    assert old_p == new_p and len(new_p) == 125
    images = lambda text: re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', text)
    assert images(old) == images(new) and len(images(new)) == 7
    old_cites = Counter(re.findall(r'<!--ref:[^>]+-->', old))
    new_cites = Counter(re.findall(r'<!--ref:[^>]+-->', new))
    assert old_cites == new_cites
    headings = lambda text: re.findall(r'^#{2,4} .*$', text, re.M)
    assert headings(old) == headings(new)
    tables = lambda text: re.findall(r'^表[A-F0-9]+-\d+P?\s+[^\n]*$', text, re.M)
    assert tables(old) == tables(new) and len(tables(new)) == 27
    algorithms = lambda text: re.findall(r'```(?:algorithm|plaintext)\n(.*?)\n```', text, re.S)
    assert len(algorithms(old)) == len(algorithms(new)) == 2
    assert algorithms(old)[0] == algorithms(new)[0]
    for token in ['CRediT', '个人分工待确认', '前期BR-O、BR-C结果单列']:
        assert token not in new, token
    assert '不提供BR-C或BR-J的独立实验成绩' in new
    assert '包括未进入提交步骤的尝试' in new
    assert '若保持$h$的端点不变' in new
    diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                       fromfile=BASE.name, tofile=NEW.name))
    (WORK / 'source.diff').write_text(diff)
    report = {
        'source_sha256': digest(NEW), 'baseline_hashes': EXPECTED_BASE,
        'display_equations_byte_identical': 32, 'references_byte_identical': 46,
        'placeholder_sequence_identical': len(new_p),
        'historical_appendix_byte_identical': True,
        'citation_markers_preserved': sum(new_cites.values()),
        'headings_unchanged': len(headings(new)), 'numbered_tables_unchanged': len(tables(new)),
        'figure_references_unchanged': len(images(new)), 'algorithm_blocks': len(algorithms(new)),
        'editorial_items': ['V3-02', 'V3-04', 'V3-06', 'V3-08', 'V3-09'],
        'pending_author_design_choices': ['V3-01', 'V3-03', 'V3-05', 'V3-07'],
        'withdrawn_item': 'V3-10', 'empirical_item_pending': 'V3-11',
        'scope': 'Source-preservation and bounded editorial QA only; no empirical or formal ARS certification.',
    }
    (WORK / 'content_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
