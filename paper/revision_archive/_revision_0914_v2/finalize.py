"""Record completed visual inspection and package the new reference project."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent
PROJECT = ROOT / 'argument_mining_0914'
FINAL = Path('/private/tmp/paper_0914_v2_render_v3')
PREVIOUS = Path('/private/tmp/paper_0914_v2_render_v2')
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

# Human/model visual observations were performed using view_image at original
# resolution before this record was authored. Hash equality transfers only
# unchanged page images, never an unobserved changed page.
direct_final = {14, 21, 22, *range(41, 51)}
prior_inspected = set(range(1, 41))
coverage = []
for page in range(1, 51):
    final_png = FINAL / f'page-{page}.png'
    if page in direct_final:
        evidence = 'direct final PNG inspection at original resolution'
    else:
        assert page in prior_inspected
        assert digest(final_png) == digest(PREVIOUS / final_png.name)
        evidence = 'previously inspected V2 PNG; SHA-256 identical to final V3 PNG'
    coverage.append({'physical_page': page, 'sha256': digest(final_png),
                     'inspection': evidence, 'result': 'no blocking layout defect observed'})
(WORK / 'page_coverage.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=2))
verification = json.loads((WORK / 'verification.json').read_text())
assert verification['rendered_pages'] == len(coverage) == 50
assert verification['docx_sha256'] == digest(ROOT / 'report_0914_v2.docx')
assert verification['md_sha256'] == digest(ROOT / 'report_0914_v2.md')
verification['visual_review'] = 'completed_all_50_pages'
verification['page_coverage_record'] = 'page_coverage.json'
verification['rendered_pdf_sha256'] = digest(FINAL / 'report_0914_v2.pdf')
(WORK / 'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2))
(WORK / 'visual_qa.md').write_text('''# 0914-v2 Word 视觉检查

最终渲染：50 页；最终 DOCX 与 Markdown 哈希见 verification.json。
全部页面以原分辨率检查。V2 的第 1—40 页已逐页查看；最终 V3 的第
14、21、22、41—50 页重新/首次查看；其余最终页面与已查看的 V2 图像
SHA-256 完全一致。逐页证据见 page_coverage.json。

检查范围：封面、双语摘要、目录页码、标题、页眉页脚、147 个原生公式、
13 个表格、参考文献、附录与 19 条批注的 XML 锚定。正文未发现文字重叠、
裁切、缺字或表格行裁断。跨页表保留重复表头；章节尾部留白为正常分页。

已修复：第三章小结溢出的孤立尾页；联合目标引导语与公式跨页分离；
JSON 示例字段顺序与新代码不一致。最终目录与正文起始页核对通过。

这只是当前草稿的文件结构和渲染检查，不是武汉大学正式模板认证、
历史实验复现或论文送审资格认定。内部 PDF/PNG 不作为额外交付件。
''')

test_report = json.loads((PROJECT / 'validation/test_report.json').read_text())
assert test_report['successful'] and test_report['tests_run'] == 55 and test_report['skipped'] == 0
for key, folder in [('source_sha256', 'am'), ('tests_sha256', 'tests')]:
    for name, value in test_report[key].items():
        assert digest(PROJECT / folder / name) == value, name

allowed_top = {'README.md', 'pyproject.toml', '.gitignore'}
allowed_dirs = {'am', 'configs', 'docs', 'scripts', 'tests', 'validation'}
files = []
for path in sorted(PROJECT.rglob('*')):
    rel = path.relative_to(PROJECT)
    if rel.parts[0] not in allowed_top | allowed_dirs:
        continue
    if any(part == '__pycache__' or part.endswith('.egg-info') for part in rel.parts):
        continue
    if path.is_symlink():
        raise ValueError(f'Unexpected symlink in source package: {rel}')
    if path.is_file() and path.suffix not in {'.pyc', '.pyo'}:
        files.append(path)
assert sum(path.parent.name == 'configs' and path.suffix == '.json' for path in files) == 19
archive = ROOT / 'argument_mining_0914_source.zip'
assert not archive.exists(), 'Refusing to overwrite an existing delivery archive'
with ZipFile(archive, 'x', ZIP_DEFLATED) as z:
    for path in files:
        z.write(path, str(Path(PROJECT.name) / path.relative_to(PROJECT)))
with ZipFile(archive) as z:
    assert z.testzip() is None
    assert all('/.venv/' not in n and '/runs/' not in n and '/models/' not in n for n in z.namelist())
    with tempfile.TemporaryDirectory(prefix='am0914-package-check-') as temp:
        z.extractall(temp)
        extracted = Path(temp) / PROJECT.name
        environment = os.environ.copy()
        environment.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1')
        environment.pop('PYTHONPATH', None)
        command = [str(PROJECT / '.venv/bin/python'), '-m', 'unittest', 'discover', '-s', 'tests', '-v']
        result = subprocess.run(command, cwd=extracted, env=environment, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        (WORK / 'package_test_output.txt').write_text(result.stdout)
        assert result.returncode == 0, result.stdout
        assert 'Ran 55 tests' in result.stdout and 'skipped=' not in result.stdout
package = {
    'archive': archive.name, 'sha256': digest(archive), 'bytes': archive.stat().st_size,
    'files': {str(p.relative_to(PROJECT)): digest(p) for p in files},
    'clean_extraction_tests': {'passed': 55, 'skipped': 0, 'network': 'offline',
                             'scope': 'synthetic software tests only',
                             'environment': 'existing isolated Python/ML dependencies'},
    'excludes': ['.venv', 'runs', 'data', 'models', '__pycache__'],
    'historical_reproduction': False,
}
(WORK / 'package_manifest.json').write_text(json.dumps(package, ensure_ascii=False, indent=2))
print(json.dumps({'visual_pages_checked': 50, 'source_files_packaged': len(files),
                  'zip_bytes': archive.stat().st_size, 'clean_extraction_tests_passed': 55,
                  'archive': str(archive)}, ensure_ascii=False, indent=2))
