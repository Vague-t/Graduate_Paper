"""Check bounded v3 source edits and the synthetic joint-repair arithmetic.

This is document QA, not an experiment or a formal ARS certification.
"""
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
import difflib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'report_1007_v2_full.md'
NEW = ROOT / 'report_1008_v3_full.md'
EXPECTED_BASE = {
    'report_1007_v2_full.md': 'd7b1e7d15a6751a3e3335b1eba8d38d0d1d6e4c752c7bd225c41446d0946696c',
    'report_1007_v2_full.docx': 'e3c136b8791e792da9a4d04debdbdd1cb35497be9550b0cd6cbaf85d66794d12',
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def region(s, begin, end):
    return s.split(begin, 1)[1].split(end, 1)[0]


def synthetic_check():
    kc, kr, delta = F('0.4'), F('0.2'), F('0.02')
    old_c = 2 * F('0.20') - kc
    old_r = sum(2 * q - kr for q in (F('0.18'), F('0.16')))
    result = {}
    for name, cq, rq in [('a', F('0.45'), (F('0.40'), F('0.35'))),
                         ('b', F('0.35'), (F('0.11'), F('0.05')))]:
        dc = 2 * cq - kc - old_c
        candidates = []
        for bits in product((0, 1), repeat=2):
            dr = sum((2 * q - kr) * bit for q, bit in zip(rq, bits)) - old_r
            cost_r = 2 + sum(bits)  # Delete both old semantic edges; add new edges.
            passes = dc >= 0 and dr >= 0 and dc + dr > delta and cost_r <= 4
            candidates.append({'selected': list(bits), 'delta_C': float(dc),
                               'delta_R': float(dr), 'delta_total': float(dc + dr),
                               'cost_C': 2, 'cost_R': cost_r, 'passes': passes})
        best = max(candidates, key=lambda c: (c['delta_total'], -c['cost_R']))
        result[name] = {'all_two_slot_completions': candidates, 'unconstrained_best': best,
                        'has_acceptable_completion': any(c['passes'] for c in candidates)}
    assert result['a']['unconstrained_best']['delta_C'] == 0.5
    assert result['a']['unconstrained_best']['delta_R'] == 0.82
    assert result['a']['unconstrained_best']['delta_total'] == 1.32
    assert result['a']['has_acceptable_completion']
    assert result['b']['unconstrained_best']['delta_C'] == 0.3
    assert result['b']['unconstrained_best']['delta_R'] == -0.26
    assert result['b']['unconstrained_best']['delta_total'] == 0.04
    assert not result['b']['has_acceptable_completion']
    assert F('0.20') + F('0.45') + F('0.35') == 1  # Conflicting component marginals.
    return result


def main():
    old, new = BASE.read_text(), NEW.read_text()
    for name, expected in EXPECTED_BASE.items():
        assert digest(ROOT / name) == expected, f'Baseline changed: {name}'
    old_math = re.findall(r'\$\$(.*?)\$\$', old, re.S)
    new_math = re.findall(r'\$\$(.*?)\$\$', new, re.S)
    assert new_math == old_math and len(new_math) == 32
    refs = lambda s: region(s, '## 参考文献', '## 附录A')
    assert refs(old) == refs(new)
    assert len(re.findall(r'^\[\d+\]', refs(new), re.M)) == 46
    historical = lambda s: region(s, '## 附录E', '## 附录F')
    assert historical(old) == historical(new)
    pt = r'(?<![\d.])\d+(?:\.\d+)?%?P%?'
    old_p, new_p = re.findall(pt, old), re.findall(pt, new)
    assert old_p == new_p and len(new_p) == 125
    old_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', old)
    new_images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', new)
    assert old_images == new_images and len(new_images) == 7
    for dead in ['5.1.1', '5.1.2', '5.3.1', '5.3.2', '6.2.1', '6.2.2', '6.2.3']:
        assert dead not in new, f'Obsolete section reference: {dead}'
    old_cites = Counter(re.findall(r'<!--ref:[^>]+-->', old))
    new_cites = Counter(re.findall(r'<!--ref:[^>]+-->', new))
    assert old_cites == new_cites
    diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        fromfile=BASE.name, tofile=NEW.name))
    (WORK / 'source.diff').write_text(diff)
    report = {'source_sha256': digest(NEW), 'baseline_hashes': EXPECTED_BASE,
              'display_equations_identical': 32, 'references_identical': 46,
              'placeholder_tokens': len(new_p), 'historical_appendix_identical': True,
              'citations_preserved': sum(new_cites.values()),
              'table_count': len(re.findall(r'^表[A-F0-9]+-\d+P?\s+[^\n]*$', new, re.M)),
              'images': [{'alt': alt, 'path': path} for alt, path in new_images],
              'old_headings': len(re.findall(r'^#{2,4} ', old, re.M)),
              'new_headings': len(re.findall(r'^#{2,4} ', new, re.M)),
              'synthetic_example': synthetic_check(),
              'scope': 'Source preservation and synthetic arithmetic only; empirical validation pending.'}
    (WORK / 'content_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({key: val for key, val in report.items()
                      if key not in ('synthetic_example', 'images')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
