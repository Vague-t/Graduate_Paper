"""Apply the bounded placeholder-draft additions; never edit the 0920 originals."""
from pathlib import Path
import difflib
import hashlib
import json
import re

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent
SOURCE = ROOT / 'report_0920_v1.md'
OUTPUT = ROOT / 'report_0923_v1_placeholder.md'
source = SOURCE.read_text()
expected = '14cf8e89acc1f118ec21667b29b041dd8caca06cf580ab34c228a8c7743d0ad1'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == expected
text = source.replace('0920-v1修订稿　2026年9月20日', '0923-v1预期数值占位稿　2026年9月23日　非实测，勿送审', 1)
old = '本次修订建立方法与验证协议，不把预期结果写成已测得成绩。'
new = '本次修订在第五章5.8增加六张预期情景占位表及条件式分析，P后缀表示人工设定的placeholder，不是实测值、统计预测或显著性p值。占位用于检查写作与比较逻辑，正式报告前须整体替换数值和分析，不能只删去标记。本次仍建立方法与验证协议，不把预期结果写成已测得成绩。'
assert text.count(old) == 1
text = text.replace(old, new, 1)
old = '现有公开成果与轻量诊断用于说明研究基础和适用边界，新增方法的实证结论仍需与相应运行记录及严格评价结果绑定。'
new = '现有成果与轻量诊断用于说明研究基础；第五章预期情景值仅为写作占位，新增方法的实证结论仍需与运行记录及严格评价绑定。'
assert text.count(old) == 1
text = text.replace(old, new, 1)
old = 'Published prior results and lightweight diagnostics establish the research basis and its limits; empirical claims for the new methods require their own reproducible runs and strict evaluation.'
new = 'Prior results and diagnostics establish the research basis. Numerical scenarios in Chapter 5 are writing placeholders, not measurements; new empirical claims require reproducible runs and strict evaluation.'
assert text.count(old) == 1
text = text.replace(old, new, 1)
start = text.index('### 5.8 本章小结')
end = text.index('## 第六章 总结与展望', start)
text = text[:start] + (WORK / 'results_placeholder.md').read_text().strip() + '\n\n' + text[end:]
anchor = '### 6.1 研究总结\n\n'
assert text.count(anchor) == 1
notice = '本版第五章的预期情景值只用于展示表格和条件式分析，不构成两项方法有效性的证据。本节保留方法设计层面的总结，不将占位差值写成实测提升；是否支持独立贡献及其适用条件，应依据新增方法的正式预测、运行记录和匹配对照判断。\n\n'
text = text.replace(anchor, anchor + notice, 1)
def region(s, left, right=None):
    part = s.split(left, 1)[1]
    return part if right is None else part.split(right, 1)[0]
checks = {
    'chapters_1_to_4_unchanged': region(source, '## 第一章 绪论', '## 第五章') == region(text, '## 第一章 绪论', '## 第五章'),
    'references_and_appendices_unchanged': region(source, '## 参考文献') == region(text, '## 参考文献'),
    'prior_experiment_protocol_unchanged': region(source, '## 第五章', '### 5.8 ') == region(text, '## 第五章', '### 5.8 '),
}
assert all(checks.values()), checks
OUTPUT.write_text(text)
(WORK / 'revision.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True), text.splitlines(True), fromfile=SOURCE.name, tofile=OUTPUT.name)))
record = {
    'source_md_sha256': expected,
    'source_docx_sha256': hashlib.sha256((ROOT / 'report_0920_v1.docx').read_bytes()).hexdigest(),
    'output_md_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'checks': checks,
    'placeholder_tables': re.findall(r'^表(5-(?:5|6|7|8|9|10)) (.+)$', text, re.M),
    'status': 'synthetic_scenario_placeholder_not_measured',
}
(WORK / 'assembly_audit.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
print(json.dumps(record, ensure_ascii=False))
