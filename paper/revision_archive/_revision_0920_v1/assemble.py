"""Assemble the approved, separately reviewed chapter patches; preserve source."""
from pathlib import Path
import hashlib, re, json, difflib

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
SOURCE = ROOT / 'report_0915_v1.md'
EXPECTED = '1d3e02e849dd3c9c101c25e3af0bfb5efc02395d849ecc62d04a1a3be0fc7d5c'
old = SOURCE.read_text()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED

def between(text, start, end):
    assert text.count(start) == 1, start
    assert text.count(end) == 1, end
    return text.split(start, 1)[1].split(end, 1)[0]

def part(name):
    return (WORK / name).read_text().strip() + '\n\n'

literature = (WORK / 'literature_patch.md').read_text()
ch1 = '## 第一章 绪论' + between(old, '## 第一章 绪论', '### 1.3 研究问题与主要研究工作')
start = '#### 1.2.4 结构保持数据增强'
end = '#### 1.2.5 约束解码、多候选评估与局部修正'
replacement = start + between(literature, start, '## 2. §1.2.5 精确装配建议')
ch1 = ch1[:ch1.index(start)] + replacement.strip() + '\n\n' + ch1[ch1.index(end):]
start2 = 'Xiao和Li在2026年提出另一项名为ARGUS的研究'
end2 = '#### 1.2.6 中文资源、跨语料迁移与研究定位'
replacement2 = between(literature, '### 替换文本开始', '### 替换文本结束').strip()
ch1 = ch1[:ch1.index(start2)] + replacement2 + '\n\n' + ch1[ch1.index(end2):]
position = '综合以上研究，本文的研究位置是：'
replacement3 = between(literature, '## 3. §1.2.6 最后一段替换文本', '## 4. 可选的一句基础文献补充')
replacement3 = replacement3[replacement3.index('综合以上研究，本文围绕'):].strip()
ch1 = ch1[:ch1.index(position)] + replacement3 + '\n\n'
ch1 = ch1.replace('在明确的任务表示下覆盖所有受影响关系对象', '在明确的有限因素宇宙中覆盖按端点关联定义的影响对象')
ch1 = ch1.replace('第四章的逐边语义评分仍是模型判断', '第四章的完整对象评分仍是模型判断')

references = '## 参考文献' + between(old, '## 参考文献', '## 附录A 复现与证据核验清单')
new_refs = between((WORK / 'references_add.md').read_text(), '## 可装配书目', '## 装配与来源核查说明（不进入参考文献正文）')

captions = [
    ('3-1', 'AAEC组件分类别旧稿记录', '来源为旧稿补充记录；未在ICIC公开版中找到对应分类别表。Single-Pass的81.67与表E-2的77.82尚需run ID解释，不用于新增强的独立归因。'),
    ('4-2', 'ICIC原版AAEC域内结果记录', '对应ICIC公开版Table 1的AAEC部分[42]<!--ref:tang2026icic--><!--anchor:section:5.2-->。所有方法名及数值按旧稿保留；外部结果的评价差异需按原文核验，不能视为统一严格协议下的复现。'),
    ('4-3', 'ICIC原版CDCP域内结果记录', '对应ICIC公开版Table 1的CDCP部分[42]<!--ref:tang2026icic--><!--anchor:section:5.2-->。该表不证明本论文原生多前提超边的严格抽取性能。'),
    ('4-4', 'ICIC原版模块消融记录', '对应ICIC公开版Table 2[42]<!--ref:tang2026icic--><!--anchor:section:5.3-->。专项适配、线索、多候选及有效性消融不等于完整影响域、成对学习和事务闭合消融。'),
    ('4-5', 'ICIC原版验证器替换记录', '对应ICIC公开版Table 3[42]<!--ref:tang2026icic--><!--anchor:section:5.3-->。原二元验证器一致性不能替代新完整对象评分器的正确性校准；自比较的一致率不构成真实性证据。'),
    ('4-6', 'ICIC原版Oracle记录', '对应ICIC公开版Table 5[42]<!--ref:tang2026icic--><!--anchor:section:5.5-->。保留原名称，不改称新候选宇宙的可达率、原生超边上界或局部搜索最优值。'),
    ('4-7', 'ICIC原版修正行为记录', '对应ICIC公开版Table 6[42]<!--ref:tang2026icic--><!--anchor:section:5.6-->。Replace及Promote/Demote明确属于BR-O，不能移作BR-C或BR-J的行为分布；动作占比不等于真实错误分布。'),
    ('5-1', '前期粗粒度组件映射', '这是单独迁移协议的标签归约，不改变AAEC/CDCP的原生域内标签，也不证明标签在语义上天然等价。'),
    ('5-2', 'ICIC原版AAEC到CDCP迁移记录', '对应ICIC公开版Table 4[42]<!--ref:tang2026icic--><!--anchor:section:5.4-->。有向无标签Link-F1与严格原生关系F1分开；目标数据用途及多前提投影口径仍需历史材料核准。'),
]
archive = '## 附录E 前期数值与协议存档\n\n'
archive += '本附录逐表保留0915-v1稿件中的原始数字和方法行。除表E-1及协议映射表外，相应数值可在ICIC公开版本中找到；“可找到”不等于本次独立复现。所有结果均不属于0920-v1新增机制。旧表“±”的统计定义、划分及评价脚本仍按附录A核验，不由新协议追认。\n\n'
table_audit = []
for idx, (number, title, note) in enumerate(captions, 1):
    match = re.search(r'^表' + re.escape(number) + r'[^\n]*\n\n(\|[^\n]*\n(?:\|[^\n]*(?:\n|$))*)', old, re.M)
    assert match, number
    table = match.group(1).strip()
    archive += f'### E.{idx} {title}\n\n表E-{idx} {title}\n\n{table}\n\n{note}\n\n'
    table_audit.append({'old': number, 'new': f'E-{idx}', 'sha256': hashlib.sha256(table.encode()).hexdigest(), 'unchanged': True})

text = part('front.md') + ch1 + part('chapter1_end.md')
for chapter in range(2, 7):
    text += part(f'chapter{chapter}.md')
text += references.strip() + '\n\n' + new_refs.strip() + '\n\n' + part('appendices.md') + archive
# Single-pass citation mapping avoids cascading substitution of new numbers.
text = re.sub(r'\[(4[2-9]|5[0-4])\]', lambda m: '[' + str(int(m.group(1))-8) + ']', text)
text = re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'
out = ROOT / 'report_0920_v1.md'
out.write_text(text)
(WORK / 'revision.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True), text.splitlines(True), fromfile=SOURCE.name, tofile=out.name)))
refs = [int(x) for x in re.findall(r'^\[(\d+)\] ', text, re.M)]
assert refs == list(range(1, 47)), refs
assert text.count('## 第') == 6
assert len(re.findall(r'^## 附录', text, re.M)) == 5
for item in table_audit:
    assert item['unchanged']
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
report = {'source_md_sha256': EXPECTED, 'output_md_sha256': hashlib.sha256(out.read_bytes()).hexdigest(), 'historical_tables': table_audit, 'reference_count': len(refs), 'new_method_metrics_fabricated': False, 'ars_full_certification': 'NOT_CALIBRATED', 'chapters': 6, 'appendices': 5}
(WORK / 'assembly_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps({'output': str(out), 'chars': len(text), 'references': len(refs), 'unchanged_tables': len(table_audit)}, ensure_ascii=False))
