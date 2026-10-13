"""Record completed visual inspection and byte-identical page reuse."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / '_revision_0914'
RENDER = Path('/private/tmp/paper_0914_render_v4')
EXPECTED_DOCX = 'e2957e658703d42646b45fe2d0257a2e3b550c6c7b85fff8a99417cde6ae2e84'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert digest(ROOT / 'report_0914.docx') == EXPECTED_DOCX
assert len(list(RENDER.glob('page-*.png'))) == 48
coverage = []
for page in range(1, 49):
    current = RENDER / f'page-{page}.png'
    if page <= 3:
        inspected = Path('/private/tmp/paper_0914_render_v1') / f'page-{page}.png'
    elif 5 <= page <= 14:
        inspected = Path('/private/tmp/paper_0914_render_v3') / f'page-{page+1}.png'
    else:
        inspected = current
    assert digest(current) == digest(inspected), f'Inspect current page {page}: image changed'
    coverage.append({'final_page': page, 'inspected_image': str(inspected),
                     'final_image_sha256': digest(current),
                     'inspection': 'direct' if inspected == current else 'identical_to_inspected_image'})

(WORK / 'page_coverage.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=2))
verification = json.loads((WORK / 'verification.json').read_text())
assert verification['docx_sha256'] == EXPECTED_DOCX
assert verification['rendered_pages'] == 48
verification.update(visual_review='completed_all_48_pages',
                    visual_qa_record='_revision_0914/visual_qa.md',
                    page_coverage_record='_revision_0914/page_coverage.json',
                    qualification='Revision and rendering checks only; not experiment replication or school-template certification.')
(WORK / 'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2))
print(json.dumps({'pages_covered': len(coverage), 'docx_sha256': EXPECTED_DOCX,
                  'status': verification['visual_review']}, ensure_ascii=False, indent=2))
