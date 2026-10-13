"""Reuse the reviewed 0913 layout and native-math path; add local revision comments."""
from pathlib import Path
import json
import subprocess
import sys
from zipfile import ZipFile
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / '_revision_0914'
old_builder = ROOT / '_revision_0913/build_docx.py'
source = old_builder.read_text().replace('_revision_0913', '_revision_0914').replace('report_0913', 'report_0914').replace('0913修订', '0914修订').replace('2026年9月13日', '2026年9月14日')
namespace = {'__file__': str(__file__), '__name__': '__main__'}
exec(compile(source, str(old_builder), 'exec'), namespace)

# English uses 1.5-line spacing so Keywords stay with the abstract on one page.
doc = namespace['doc']
english_abstract = False
for paragraph in doc.paragraphs:
    if paragraph.text == 'Abstract':
        english_abstract = True
        continue
    if paragraph.text == '目录': english_abstract = False
    if english_abstract:
        paragraph.paragraph_format.line_spacing = namespace['Pt'](18)
        if paragraph.text.startswith('Keywords:'):
            for run in paragraph.runs: run.font.size = namespace['Pt'](11)
doc.save(ROOT / 'report_0914.docx')

comments = [
    ('论辩挖掘旨在从非结构化文本中识别论辩组件', '0914修改：中英文摘要统一为训练阶段局部结构保持增强、推理阶段候选图评估与局部修正。保留现有实验数值，不将Full结果重复归因于某一模块。'),
    ('1.2 国内外研究现状', '0914修改：相关工作由五节调整为六节，增加9篇文献（8篇为2025—2026年），区分原始文本抽取、给定组件分类、话轮分割与系统演示。'),
    ('1.3.2 主要研究工作与贡献', '0914修改：两项方法贡献加一项验证工作。LoRA、连续提示、辅助损失不各自作为独立创新；跨语料映射不称为新算法。'),
    ('2.6 训练增强与推理修正的接口', '0914新增：两个阶段共享任务表示，但未定义验证器反馈反向传播的联合训练；明确固定训练配置与候选池的归因条件。'),
    ('本章据此设计面向结论类组件的局部论辩结构保持增强方法', '0914修改：第三章聚焦结论中心局部子图及监督保持机制，Adapter等作为配套模块；门控与增强配置仍需代码核验。'),
    ('3.3 面向结论组件的配套表示增强', '0914修改：补充DENIM及关联关键短语方法的相邻关系，避免将结构或线索利用作宽泛原创主张。'),
    ('本章提出基于完整候选图评估与异常驱动局部修正的MCR-BR方法', '0914修改：第四章与创新点二同步；有界指轮数和接受动作限制，不代表全部模型调用上界，也不保证遗漏节点恢复。'),
    ('4.5.3 近期相关方法的比较边界', '0914新增：区分优先补做的同协议基线与只能作机制讨论的相邻研究。未向实验表格添加未经运行的新方法分数。'),
    ('本章在训练域与测试域不一致的条件下分析第三', '0914修改：第五章补入MT-AM与2025泛化研究，区分辅助语料训练和源域零样本迁移；映射表与实验数值保持不变。'),
    ('6.1 工作总结', '0914修改：总结对应两项方法贡献和验证工作，保留独立消融、配置追踪及预算匹配的未决条件。'),
    ('0914版在0913版基础上，参照academic-research-suite', '0914修改：更新辅助工具使用与修订可追溯性说明；未运行新实验，不声称完成ARS全套逐块授权或研究完整性认证。'),
]
helper = '/Users/channtang/.codex/plugins/cache/openai-primary-runtime/documents/26.909.12148/skills/documents/scripts/comments_add.py'
out = ROOT / 'report_0914.docx'
args = [sys.executable, helper, str(out), '--out', str(WORK/'commented.docx'), '--author', 'Codex 0914修订', '--require_all']
for anchor,note in comments: args += ['--add', anchor+'='+note]
subprocess.run(args, check=True)
# Keep paragraph properties first in CT_P even when the comment helper prepends anchors.
ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(WORK/'commented.docx') as zin:
    xml = etree.fromstring(zin.read('word/document.xml'))
    for p in xml.xpath('//w:p[w:pPr]', namespaces=ns):
        prop = p.find('{'+ns['w']+'}pPr')
        if p.index(prop): p.remove(prop); p.insert(0,prop)
    payload = etree.tostring(xml,xml_declaration=True,encoding='UTF-8',standalone=True)
    with ZipFile(out,'w') as zout:
        for info in zin.infolist(): zout.writestr(info,payload if info.filename=='word/document.xml' else zin.read(info.filename))
(WORK/'comment_log.json').write_text(json.dumps(comments,ensure_ascii=False,indent=2))
print('Added',len(comments),'native Word comments')
