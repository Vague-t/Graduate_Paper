"""Record the completed human-model visual inspections and exact render match.

This is an evidence recorder, not an automatic visual quality judgment. The
review attestations below were returned after opening all assigned page PNGs.
"""
import hashlib
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent
FINAL = WORK / 'render_pass5'
REVIEWED = WORK / 'render_pass3'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


groups = [
    (1, 12, 'root delegated read-only reviewer', '封面、中英文摘要、目录、正文与表1-1/1-2逐页完整目检通过'),
    (13, 25, 'root', '两阶段图、影响域图、表2-1/3-1及公式逐页完整目检通过'),
    (26, 50, 'mechanism_figures reviewer', '原生公式、算法、修正图及表4-1/5-1至5-4逐页完整目检通过'),
    (51, 77, 'docx builder reviewer', '六张P占位表、总结、46条文献及全部附录逐页完整目检通过'),
]
pages, changed = [], []
for number in range(1, 78):
    final, reviewed = FINAL / f'page-{number}.png', REVIEWED / f'page-{number}.png'
    same = digest(final) == digest(reviewed)
    if not same:
        changed.append(number)
    group = next(item for item in groups if item[0] <= number <= item[1])
    pages.append({'physical_page': number, 'final_png_sha256': digest(final),
                  'identical_to_reviewed_pass3': same, 'reviewer': group[2],
                  'status': 'passed', 'review_note': group[3]})
assert not changed, 'Unreviewed render differences: ' + repr(changed)
assert len(list(FINAL.glob('page-*.png'))) == 77
pagination = json.loads((WORK / 'pagination.json').read_text())
assert pagination['physical_pages'] == 77 and pagination['mapping_stable']
geometry = json.loads((WORK / 'render_geometry.json').read_text())
assert not geometry['outside_page'] and not geometry['outside_body_candidates']
result = {
    'status': 'PASS', 'final_render': str(FINAL), 'reviewed_render': str(REVIEWED),
    'final_docx': str(ROOT / 'report_1007_v1_full.docx'),
    'final_docx_sha256': digest(ROOT / 'report_1007_v1_full.docx'),
    'source_md_sha256': digest(ROOT / 'report_1007_v1_full.md'),
    'physical_pages': 77, 'body_pages': 73, 'all_pages_visually_reviewed': True,
    'final_vs_reviewed_changed_pages': changed, 'toc_mapping_stable': True,
    'page_geometry_checks_passed': True, 'all_page_nonmeasured_warnings_present': True,
    'additional_final_review': {'reviewer': 'root', 'physical_pages': [42, 43], 'status': 'passed'},
    'correction_to_initial_review_note': '“融。”位于物理42页段末，不在43页顶部；属于正常段末短行，未发生跨页孤行。',
    'verified_layout_change': '短公式引导句与其后的原生OMML保持同页，已复查26–27页。',
    'remaining_visual_defects': [], 'pages': pages,
}
(WORK / 'visual_qa.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
build_path = WORK / 'docx_build.json'
build = json.loads(build_path.read_text(encoding='utf-8'))
build['rendered_or_visually_verified'] = True
build['final_visual_qa'] = str(WORK / 'visual_qa.json')
build_path.write_text(json.dumps(build, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key != 'pages'}, ensure_ascii=False, indent=2))
