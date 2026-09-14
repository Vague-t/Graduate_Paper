"""Render the revised text with the already reviewed manuscript layout and native math."""
from pathlib import Path
from zipfile import ZipFile
import json
import subprocess
import sys
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
source = (ROOT/'_revision_0913/build_docx.py').read_text()
source = source.replace('_revision_0913', '_revision_0914_v2').replace('report_0913', 'report_0914_v2')
source = source.replace('0913修订', '0914-v2修订').replace('2026年9月13日', '2026年9月14日').replace('[A-C0-9]', '[A-D0-9]')
namespace = {'__file__': str(__file__), '__name__': '__main__'}
exec(compile(source, str(ROOT/'_revision_0913/build_docx.py'), 'exec'), namespace)
doc = namespace['doc']
english = False
for p in doc.paragraphs:
    if p.text == '联合目标为：': p.paragraph_format.keep_with_next = True
    if p.text == 'Abstract':
        english = True
        continue
    if p.text == '目录': english = False
    if english:
        p.paragraph_format.line_spacing = namespace['Pt'](18)
        if p.text.startswith('Keywords:'):
            for r in p.runs: r.font.size = namespace['Pt'](11)
out = ROOT/'report_0914_v2.docx'
doc.save(out)
comments = json.loads((ROOT/'_revision_0914/comment_log.json').read_text())
comments += [
    ('本稿在0914修订稿基础上核对实验配置', '0914-v2：原项目缺失，新增代码为参考实现，不是原结果复现。真实实验表不改动。'),
    ('0914-v2新评价脚本默认将端点跨度和类型', '0914-v2：精确匹配与失败处理已编码；旧表评价口径仍未核实。重复预测不去重抬分，失败样本不移出分母。'),
    ('新实现固定id、type、span的字段顺序', '0914-v2：门控只使用可见前缀；全局与专项LoRA共同存在。新实现通过小模型测试，但需重训后验证收益。'),
    ('以下公式明确新参考实现的归一化方式', '0914-v2：生成项和句子辅助项均改为均值以对应新代码。历史求和尺度未核实，不沿用旧分数验证新公式。'),
    ('新参考实现补充每文档最多24次动作尝试', '0914-v2：将接受数、尝试数、模型调用数和输出token预算分开记录；候选缓存仍计逻辑生成成本。'),
    ('4.5.4 配置核对与新实验命名', '0914-v2：单次整图与单候选分阶段推理明确分开。81.67/77.82冲突不可仅凭新命名解决；保留R05。'),
    ('新实现把标签对齐限制在评价阶段的确定性映射', '0914-v2：新跨域协议继续输出AAEC源标签，评价时才映射粗标签；旧表是否相同仍需日志。'),
    ('D.3 当前验证范围与未完成工作', '0914-v2：55项软件测试通过，包含随机小模型的短训练和重载；未运行真实数据、7B效果或GPU效率实验。'),
]
helper = '/Users/channtang/.codex/plugins/cache/openai-primary-runtime/documents/26.909.12148/skills/documents/scripts/comments_add.py'
args = [sys.executable, helper, str(out), '--out', str(WORK/'commented.docx'), '--author', 'Codex 修订记录', '--require_all']
for anchor, note in comments: args += ['--add', anchor+'='+note]
subprocess.run(args, check=True)
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(WORK/'commented.docx') as zin:
    xml = etree.fromstring(zin.read('word/document.xml'))
    for p in xml.xpath('//w:p[w:pPr]', namespaces=ns):
        prop = p.find('{'+ns['w']+'}pPr')
        if p.index(prop): p.remove(prop); p.insert(0, prop)
    payload = etree.tostring(xml, xml_declaration=True, encoding='UTF-8', standalone=True)
    with ZipFile(out, 'w') as zout:
        for info in zin.infolist(): zout.writestr(info, payload if info.filename == 'word/document.xml' else zin.read(info.filename))
(WORK/'comment_log.json').write_text(json.dumps(comments, ensure_ascii=False, indent=2))
print('Added', len(comments), 'native Word comments')
