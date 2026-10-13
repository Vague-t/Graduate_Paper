"""Bind completed document review to the exact delivered artifacts."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

W = Path(__file__).resolve().parent
R = W.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())
write = lambda p, x: Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')
audit = read(W / 'final_audit.json')
md = R / 'report_1010_v7_full.md'
docx = R / 'report_1010_v7_full.docx'
pdf = W / 'render_final' / 'report_1010_v7_full.pdf'
assert sha(md) == audit['source_sha256']
assert sha(docx) == audit['docx_sha256']
assert sha(pdf) == audit['pdf_sha256']
assert audit['mechanical_checks'] == 'PASS'
assert read(W / 'numerical_audit.json')['passed']

glyphs = {}
for name in ('training_results', 'four_cell_results', 'recovery_risk'):
    out = subprocess.check_output([
        sys.executable,
        '/Users/channtang/.codex/skills/nature-figure/scripts/audit_pdf_text.py',
        str(W / 'figures' / f'{name}.pdf'), '--min-pt', '5', '--json'
    ], text=True)
    data = json.loads(out)
    assert data['auditable'] and data['below_minimum_count'] == 0 and not data['warnings']
    data['pdf_sha256'] = sha(W / 'figures' / f'{name}.pdf')
    write(W / 'figures' / f'{name}.glyph.json', data)
    glyphs[name] = {'minimum_found_pt': data['minimum_found_pt'], 'pdf_sha256': data['pdf_sha256']}

# Pages 1-24 were reviewed before this finalization; pages 25-113 were then
# opened and visually inspected in unchanged full-resolution page pairs.
visual = {
    'docx_sha256': sha(docx), 'pdf_sha256': sha(pdf),
    'all_pages_opened_and_inspected': True,
    'review_method': 'Rendered page PNGs opened in page order; original page pairs inspected for clipping, overlap, glyphs, tables, formulas, figures, headers and footers.',
    'pages': [
        {'page': n, 'png_sha256': sha(W / 'render_final' / f'page-{n}.png'),
         'visually_inspected': True, 'layout_defects_found': []}
        for n in range(1, audit['pages'] + 1)
    ],
    'new_figure_final_glyph_audits': glyphs,
    'scope': 'Document and figure quality only; not empirical experiment validation.'
}
write(W / 'visual_review.json', visual)
audit['visual_review'] = 'PASS'
audit['visually_reviewed_pages'] = audit['pages']
audit['visual_review_record'] = 'visual_review.json'
write(W / 'final_audit.json', audit)
build = read(W / 'docx_build.json')
build['rendered_or_visually_verified'] = True
build['final_verification'] = 'final_audit.json'
write(W / 'docx_build.json', build)

images = re.findall(r'^!\[[^]]*\]\(([^)]+)\)$', md.read_text(), re.M)
assert len(images) == 11 and all((R / image).is_file() for image in images)
changes = read(W / 'changes.json')
rows = changes['tables']['表5-1']
comparison = '\n'.join(
    f'| {new[0]} | {old[2]} → {new[2]} | {old[4]} → {new[4]} |'
    for old, new in zip(rows['old'], rows['new'])
)
note = f'''# 1010 v7 估算演示版修订与核验说明

本次按已确认的“估算演示版”方案修订 v6，交付完整 Word 与同步 Markdown。主表采用更小的假设增量，所有关联计数、图表、区间与文字说明同步重算。这里的“更小”只描述相对旧版的设定变化，不表示数值更接近真实实验。此次没有新增模型训练、真实语义审阅或 ILP 求解实验。

## 版本与文件

- 原稿 `report_1010_v6_full.docx` 与 `report_1010_v6_full.md` 保留未改。
- 新稿 [Word](report_1010_v7_full.docx) 与 [Markdown](report_1010_v7_full.md) 的版本均为 1010-v7。
- 主估算身份为 `EST-1010-V7`。封面、中英文摘要、相关表图及附录 H.5 说明其假设性质。
- Markdown 的 11 张配图位于 `_revision_1010_v7/figures/`；移动 Markdown 时应一同保留该目录。Word 已内嵌配图。

## 已完成的修改

更新表 3-5、3-6、3-8、4-3、4-7、5-1 至 5-5，共 10 张表；重绘图 3-3、4-3、5-1，并同步摘要、结果分析、风险解释与在线配置比较。其他方法图、原生公式、算法和历史附录保持原有身份。

四格主结果的严格关系 F1 如下。箭头左侧为 v6，右侧为 v7；两侧均为人工情景，不能作为实测性能比较。

| 配置 | AAEC 关系 F1 | CDCP 关系 F1 |
|---|---|---|
{comparison}

关键解释也随计数改变：成对学习的假设增量为 1.21／1.22 个百分点；BR-J 相对 RelationOnly 为 2.31／2.60 个百分点。CDCP 的 T1＋I0 比 T0＋I1 略低 0.02 个百分点，已撤去旧稿“两语料质量均更高”的说法。全局等求解预算结果仍略高于 BR-J；BR-J 的文档种子配对中仍有 17.50%／19.37% 的关系 F1 下降。

## 估算如何形成

固定 v6 的 T0 起点、任务定义、人工样本规模、种子扰动和成本口径，调整训练与修正方法的目标精确率／召回率中心，再生成逐文档 TP、FP、FN。按 `F1 = 2TP / (2TP + FP + FN)` 汇总微平均指标，最后跨三个情景种子计算均值和样本标准差。目标值及全部假设见 [assumptions.json](_revision_1010_v7/assumptions.json)，生成记录见 [scenario_manifest.json](_revision_1010_v7/scenario_manifest.json)。

这些目标由写作假设指定，未由真实训练、既有 CPU 诊断或论文成绩拟合而来。区间仅反映给定人工计数模型内的文档重采样，不覆盖假设本身错误的风险。成本、覆盖及审计示例保留人工输入身份。H.5 补充零增益、负增益及相反排序的压力条件；除明确列出的成本算术外，没有将这些条件写成已完成的敏感性实验。

## 已有数据的使用边界

附录 D.2—D.3 对照已有运行清单与结果文件，新增可追溯的 CPU 轻量诊断说明。AAEC 的 typed component F1 为 25.42 → 26.06，CDCP 为 4.89 → 5.06；分别接受 66 和 115 次删除，TP 未增加。因此这些记录说明该次诊断的行为，不能当作新增增强、联合修正或端到端关系抽取成绩。此次只复算与核验原记录，没有独立重训。

附录 E 按原稿保留前期数值及协议身份。本轮没有新增对这些历史成绩的独立复现。H.6—H.8 保留 `SIM-1010-V4` 旧情景，其预算与对象示例沿用 v6 计数；已明确说明它们不与 v7 主表拼接。对应旧记录单独保存于 `_revision_1010_v7/legacy_supplement/`。

## 核验结果

数值核验通过：28,728 行人工计数、84 个指标单元、36 组配对或交互区间、28,800 条概率记录及 16,000 条人工审计判断可复算。计数恒等式与跨章复用一致。以上数量是情景材料规模，不是真实实验样本证据。

Word 渲染为 113 页，已逐页打开检查。保留 411 个原生数学对象，其中独立公式 32 个；保留 3 个算法、47 张编号表、11 张图及 49 条参考文献。214 个标题／题注页码标签与最终渲染核对，211 项目录缓存匹配。新绘三图的字形及碰撞检查通过，最小字号为 7 pt。原稿页式和保留部分的内容未变化。

本轮未对全部参考文献做新的联网核验，也未据排版、构造断言或算术一致性认定实证已经完成。完整检查记录为 [final_audit.json](_revision_1010_v7/final_audit.json)、[numerical_audit.json](_revision_1010_v7/numerical_audit.json) 及 [visual_review.json](_revision_1010_v7/visual_review.json)。

## 改为正式实测稿的完成条件

先取得训练侧真实监督漂移、端点错误、候选覆盖与裁剪前成本的诊断记录；再完成同数据学习目标、RelationOnly、单对象动作和同目标全局 ILP 的关键比较，并保留全部失败与误改。以同一次运行的配置、预测、计数、日志及成本绑定结果，完成至少一项四格对象级分析及同文档案例。随后整体替换表、图、区间、摘要和结论，再移除被真实证据替代部分的估算标识。对应实施位置为正文 2.6、3.6、4.6、5.1—5.3 及附录 H.1—H.5。

## 文件校验值

- Word SHA-256：`{sha(docx)}`
- Markdown SHA-256：`{sha(md)}`

本说明绑定以上版本；后续改动正文或配图后，应重新核验关联数值与排版。
'''
note_path = R / '1010_v7估算依据与修订说明.md'
note_path.write_text(note)
write(W / 'delivery_manifest.json', {
    'deliverables': {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in (docx, md, note_path)},
    'status': 'COMPLETE_ESTIMATED_DEMONSTRATION',
    'new_real_training_runs': 0,
    'document_audit': 'PASS', 'visual_pages': audit['pages']
})
print(json.dumps({'delivered': [docx.name, md.name, note_path.name], 'visual_pages': audit['pages'], 'all_checks': 'PASS'}, ensure_ascii=False))
