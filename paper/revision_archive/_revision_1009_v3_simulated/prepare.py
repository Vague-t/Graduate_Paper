"""Prepare a separately named synthetic-data manuscript; never overwrite v2."""
from pathlib import Path
import hashlib
import json
import zipfile
from lxml import etree

W = Path(__file__).resolve().parent
R = W.parent
P = R / '_revision_1009_v2'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ['render_document.py', 'fonts.conf', 'cache_pages.py', 'algorithm_splits.json', 'table_splits.json', 'final_audit.py']:
    content = (P / name).read_text().replace('1009_v2', '1009_v3_simulated').replace('1009-v2', '1009-v3')
    (W / name).write_text(content)
# The v2 reference has already been rendered and every page reviewed in this task.
template = R / 'report_1009_v2_full.docx'
parts = []
with zipfile.ZipFile(template) as z:
    for name in z.namelist():
        preserve = name.startswith(('word/media/', 'word/theme/', 'customXml/')) or name in {
            'word/fontTable.xml', 'word/numbering.xml', 'word/webSettings.xml', 'docProps/app.xml', 'docProps/custom.xml'}
        parts.append({'name': name, 'sha256': hashlib.sha256(z.read(name)).hexdigest(),
                      'policy': 'preserve-only' if preserve else 'editable'})
    body = etree.fromstring(z.read('word/document.xml'))
    sections = [etree.tostring(x, encoding='unicode') for x in body.xpath('//w:sectPr', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
baseline = ['report_1009_v2_full.docx', 'report_1009_v2_full.md', '1009_v2逐项修改与证据闭环说明.md',
            '1009_v2复审后完整修改建议与实施方案.md', '_revision_1009_v2/validate_mechanisms.py',
            '_revision_1009_v2/mechanism_results.json', '_revision_1009_v2/validate_interfaces.py',
            '_revision_1009_v2/interface_results.json']
evidence = {'reference': str(template), 'sha256': sha(template), 'reference_render': str(P / 'render_delivery'),
            'reference_render_pages': 90, 'parts': parts, 'sections': sections,
            'baseline_hashes': {f: sha(R / f) for f in baseline}}
(W / 'template-evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
(W / 'artifact.md').write_text('''# 1009 v3 模拟数据演示稿排版契约

保留模板为 report_1009_v2_full.docx，哈希和节参数见 template-evidence.json；其90页参考渲染已全页检查。新输出名为 report_1009_v3_simulated_full.docx。继承A4三节、原页边距、正文12pt、中文与Times New Roman字体、三级黑色标题、原生数学、可点击目录和编号图表。保留六章、两项研究、32个陈列公式、46条文献、七幅方法图和附录E历史正文。

按用户明确同意的方案，仅在开头给出模拟数据统一说明，封面版本名为模拟数据演示稿；移除页眉重复警示，页眉保留原学校名称和分隔线。正文中的实验表、解释、摘要与总结使用一套生成脚本和数据索引，不宣称材料来自真实训练、真实人员盲审或真实求解日志。新增两幅结果图。附录中的原有有限程序执行记录保留其准确身份。表格内容更新不压缩字体，按需设置续表。

可编辑部分：封面说明、摘要、公共配置、训练与推理结果、四格与成本分析、总结、材料说明和S01/S02规约。保留部分：未涉及的方法推导、全部参考文献、附录E、包中旧媒体、主题、编号及自定义XML。缓存目录后重新渲染，逐页视觉核验；文档质量不等于真实研究完成。
''')
print('Prepared separate synthetic draft workspace; template SHA-256', sha(template))
