from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import json,hashlib,shutil,re

O=Path(__file__).resolve().parents[1];R=Path('/Users/channtang/Downloads/paper')
M=json.loads((O/'_work/verification.json').read_text())
F=json.loads((O/'_work/figure_manifest.json').read_text())
assert M['remaining_visual_check_pages']==[28,39,51]
M['remaining_visual_check_pages']=[]
M['visual_review']={'changed_pages_reviewed':[28,39,51],
                    'unchanged_pages_reused_by_pixel_equality':124,
                    'standalone_png_figures_reviewed':[3,5,6],
                    'result':'三张图的模型、注意力块标签、线条与版面均清晰，无裁切或重叠。'}
(O/'_work/verification.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))

assets=O/'模型图_Qwen3.5-9B_v12'
readme='''# Qwen3.5-9B 论文模型图 v12

更新日期：2026-10-13。依据作者确认“以正文为准：Qwen3.5-9B”，统一图2-1、图3-2、图4-1的模型名称；图2-1和图3-2的全注意力块数量统一为8。

每张图提供可编辑SVG及300 dpi PNG。SVG保留文字和图形对象，适合继续修改或矢量排版；PNG可直接插入文档。SVG使用Arial Unicode MS并保留通用字体回退。

| 图号 | 内容 | PNG像素尺寸 |
|---|---|---|
| 图2-1 | 端到端论辩挖掘总体架构 | 2362 × 1476 |
| 图3-2 | 关系影响域约束的可靠成对学习 | 2362 × 1742 |
| 图4-1 | 多候选驱动的依赖闭合修正 | 2362 × 1771 |

已同步嵌入论文v12 Word，包含SVG矢量图与PNG兼容预览；PDF中对应物理页为28、39、51，印刷页码为20、31、43。
'''
(assets/'使用说明.md').write_text(readme)

src=R/'论文规范排版稿_v10至v11_逐章修改说明.md'
report=src.read_text()
report=report.replace('# 论文规范排版稿 v10 → v11：逐章修改说明与待确认事项',
                      '# 论文规范排版稿 v10 → v12：逐章修改说明与模型图统一')
report=report.replace('本次保留 v10，另存 v11 Word 与 PDF。',
    '逐章文字修订形成 v11；收到作者“以正文为准：Qwen3.5-9B”的确认后，进一步统一三张模型图，形成 v12 Word 与 PDF。v10、v11 及其原修改说明均保留。')
report=report.replace('**尚有实质信息需要确认，最优先是三张架构图与正文的主骨干冲突。** 以下事项已完整列出，未用语言润色代替运行事实的选择。',
    '**三张架构图与正文的主骨干冲突已依据作者确认解决。** v12 将11处模型标注统一为 Qwen3.5-9B，将3处全注意力块数量标注统一为8，另交付3份SVG和3份300 dpi PNG。其余运行材料及方法细节仍按第5节保留待核对状态。')
report=report.replace('## 5. 作者需要确认的事项','## 5. 已解决事项与仍待核对事项')
start=report.index('### 5.1 优先确认：主骨干及三张模型图')
end=report.index('### 5.2 新实跑与沿用 v9 名称的材料对应')
report=report[:start]+'''### 5.1 已解决：主骨干及三张模型图

**位置：图2-1、图3-2、图4-1；正文2.2.2、3.2.1、补充表S2-2、附录K。**

作者于2026-10-13确认“以正文为准：Qwen3.5-9B”。v12据此统一三张图中的生成器、冻结文本编码器和图下注记，将11处模型标注统一为Qwen3.5-9B；图2-1的一处及图3-2的两处全注意力块标注从16改为8，与正文q/k/v/o适配范围一致。

三张图分别导出保留文字与图形对象的SVG及300 dpi PNG，Word中同时嵌入SVG和PNG兼容预览。修订后DOCX包的XML、SVG及关系文件中未发现Qwen3.8或16个全注意力块的旧标注。所有绘图几何、颜色、箭头、正文、数据表和原生公式保持原样。

此次修订依据作者确认与正文配置完成，不等同于独立审计模型检查点、revision或运行日志。原说明关于图2-1中NONE=0掩码个例标注的优化建议仍保留；该图的具体取值不应解释为所有NONE因素统一排除。

'''+report[end:]
report=report.replace('## 6. 排版与保真处理','## 6. 排版与保真处理\n\n以下文字与排版修订继承v11；v12另外替换三张模型图并补齐PNG兼容预览。')
start=report.index('## 7. 版本绑定')
report=report[:start]+f'''## 7. 版本绑定与v12复核

v10与v11原文件均保留；最新文件为v12 Word、PDF及模型图资源包。

| 文件 | SHA-256 |
|---|---|
| 输入v10 Word | `2d694cab29d5862c9971f9d02a55843ac02cfbcb4774fdcebc2c5ded14172765` |
| 中间v11 Word | `{M['source_sha256']}` |
| 输出v12 Word | `{M['docx_sha256']}` |
| 输出v12 PDF | `{M['pdf_sha256']}` |

v12重新完整渲染为127页，与v11逐页像素比较，仅物理页28、39、51发生图中文字变化；这3页及3张单独导出的PNG均已实际查看，模型标注清晰，无裁切或重叠。其余124页与已逐张通过视觉复核的v11页面像素完全一致。149条目录及其页码保持一致，51种PDF字体均嵌入。

v12与v11的全部正文文字、83张表和380个原生数学对象XML完全一致，插图尺寸不变。此前v10至v11核查的3,825个表格单元格、54条参考文献及42个编号公式的保真结论继续适用。式（3-9）在v11中的等价显示修复原样保留。

模型图资源包包含3份SVG、3份300 dpi PNG和使用说明。PNG尺寸分别为2362×1476、2362×1742、2362×1771。SVG保留可编辑文字与图形对象。

第5.2—5.7节的运行材料绑定与方法细节仍待依据原始记录核对；本次没有新增实验或重新计算结果。逐章审读、合并、图稿生成和渲染核验记录保存在对应版本目录中。
'''
assert '交付时尚未收到' not in report and '保留三张原图' not in report
reportname='论文规范排版稿_v10至v12_逐章修改说明.md'
(O/reportname).write_text(report)

archive=O/'论文模型图_v12_Qwen3.5-9B.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for f in sorted(assets.iterdir()):z.write(f,arcname=f.name)
with ZipFile(archive) as z:
    assert z.testzip() is None and len(z.namelist())==7
for name in ['论文规范排版稿_v12.docx','论文规范排版稿_v12.pdf',reportname,archive.name]:
    target=R/name
    assert not target.exists(),target
    shutil.copy2(O/name,target)
asset_target=R/'论文模型图_v12_Qwen3.5-9B'
assert not asset_target.exists()
shutil.copytree(assets,asset_target)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R/'论文规范排版稿_v11.docx')==M['source_sha256']
assert sha(R/'论文规范排版稿_v10.docx')=='2d694cab29d5862c9971f9d02a55843ac02cfbcb4774fdcebc2c5ded14172765'
print(json.dumps({'delivered':[str(R/n) for n in ['论文规范排版稿_v12.docx','论文规范排版稿_v12.pdf',reportname,archive.name]],
                  'assets_directory':str(asset_target),'pages':127,'visual_qa':'passed'},ensure_ascii=False,indent=2))
