"""Bind final artifacts and verify evidence identity without rebuilding the thesis."""
from pathlib import Path
import hashlib
import json
import re

W = Path(__file__).resolve().parent
R = W.parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(name):
    return json.loads((W / name).read_text())

baseline = read('template-evidence.json')['baseline_hashes']
for name, expected in baseline.items():
    assert sha(R / name) == expected, name

source = R / 'report_1009_v2_full.md'
docx = R / 'report_1009_v2_full.docx'
audit = read('final_audit.json')
assert audit['source_sha256'] == sha(source)
assert audit['docx_sha256'] == sha(docx)
assert audit['mechanical_checks'] == 'PASS'
assert audit['toc_cache_matches_final_pdf']

visual = read('visual_review.json')
assert visual['reviewed'] == audit['pages'] == 90
assert {e['page'] for e in visual['entries']} == set(range(1, 91))
for entry in visual['entries']:
    assert entry['status'] == 'PASS'
    assert sha(W / 'render_delivery' / f"page-{entry['page']}.png") == entry['final_png_sha256']

old = (R / 'report_1009_v1_full.md').read_text()
new = source.read_text()
def appendix_e(text):
    return text[text.index('# 附录E'):text.index('# 附录F')]
# Heading spacing is inherited from the source, so identify the exact headings.
def appendix(text, letter):
    return next(m.start() for m in re.finditer(r'^#+\s*附录\s*' + letter + r'\b', text, re.M))
assert old[appendix(old, 'E'):appendix(old, 'F')] == new[appendix(new, 'E'):appendix(new, 'F')]

mechanisms = read('mechanism_results.json')
interfaces = read('interface_results.json')
assert mechanisms['passed'] == len(mechanisms['checks']) == 19
assert interfaces['passed'] == len(interfaces['checks']) == 40
assert all(c['status'] == 'PASS' for c in mechanisms['checks'])
assert all(c['passed'] for c in interfaces['checks'])
assert mechanisms['code_sha256'] == sha(W / 'validate_mechanisms.py')
assert interfaces['code_sha256'] == sha(W / 'validate_interfaces.py')
assert interfaces['config_sha256'] == sha(W / 'reference_config.json')
for name in ['validate_mechanisms.py', 'mechanism_results.json']:
    assert sha(W / name) == sha(R / '_revision_1009_v1' / name)

index = read('results_index.json')
index['source_sha256'] = sha(source)
index['docx_sha256'] = sha(docx)
index['document_qa'] = {'pages': 90, 'mechanical': 'PASS', 'visual': 'PASS', 'formal_experiments': 'not_run'}
for artifact in index['artifacts']:
    assert artifact['sha256'] == sha(W / artifact['file'])
assert {r['id'] for r in index['revision_status']} == {f'R{i:02d}' for i in range(1, 12)}
(W / 'results_index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')

report = R / '1009_v2逐项修改与证据闭环说明.md'
assert sha(source) in report.read_text() and sha(docx) in report.read_text()
files = [source, docx, report] + [W / name for name in [
    'reference_config.json', 'validate_mechanisms.py', 'mechanism_results.json',
    'validate_interfaces.py', 'interface_results.json', 'results_index.json',
    'final_audit.json', 'visual_review.json', 'source.diff', 'edits.json',
    'template-evidence.json', 'finish_delivery.py',
]]
manifest = {
    'version': '1009-v2', 'date': '2026-10-09', 'baseline': '1009-v1',
    'baseline_files_unchanged': True, 'appendix_E_unchanged': True,
    'formal_corpus_experiments': 'not_run', 'production_integration': 'not_run',
    'constructed_checks': {'retained': 19, 'new_interfaces': 40},
    'document_pages': 90, 'visual_reviewed_pages': 90,
    'files': {str(path.relative_to(R)): sha(path) for path in files},
}
(W / 'delivery_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
for target in re.findall(r'\]\((/[^)]+)\)', report.read_text()):
    assert Path(target).exists(), target
print(json.dumps({'status': 'PASS', 'manifest_files': len(files), 'pages_reviewed': 90, 'baseline_unchanged': True}, ensure_ascii=False))
