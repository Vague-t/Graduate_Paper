"""Build the v3 manuscript using its established layout and native equations."""
from pathlib import Path
from zipfile import ZipFile
import json
import subprocess
import sys
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
source = (ROOT / '_revision_0913/build_docx.py').read_text()
source = source.replace('_revision_0913', '_revision_0914_v3').replace('report_0913', 'report_0914_v3')
source = source.replace('0913修订', '0914-v3修订').replace('2026年9月13日', '2026年9月14日').replace('[A-C0-9]', '[A-D0-9]')
source = source.replace("if rows[0][0]=='语料': widths=[18,52,30,57]", "if rows[0][0]=='语料': widths=[18,52,30,57]\n    if rows[0][0]=='异常对象': widths=[31,47,79]")
namespace = {'__file__': str(__file__), '__name__': '__main__'}
exec(compile(source, str(ROOT / '_revision_0913/build_docx.py'), 'exec'), namespace)
doc = namespace['doc']
english = False
compact_chapter_end = False
for p in doc.paragraphs:
    if p.text.startswith('3.4 实验设置'):
        compact_chapter_end = True
    if p.text.startswith('第四章 '):
        compact_chapter_end = False
    if compact_chapter_end and not p.style.name.startswith('Heading'):
        p.paragraph_format.space_after = namespace['Pt'](0)
    # Keep the short result table and chapter summary from spilling into an
    # otherwise empty page; retain body font size and line spacing.
    if p.style.name.startswith('Heading') and p.text.startswith(('3.4 ', '3.4.', '3.5 ', '3.6 ')):
        p.paragraph_format.space_before = namespace['Pt'](6)
        p.paragraph_format.space_after = namespace['Pt'](3)
    if p.text == '联合目标为：':
        p.paragraph_format.keep_with_next = True
    if p.text == 'Abstract':
        english = True
        continue
    if p.text == '目录':
        english = False
    if english:
        p.paragraph_format.line_spacing = namespace['Pt'](18)
        if p.text.startswith('Keywords:'):
            for r in p.runs:
                r.font.size = namespace['Pt'](11)
out = ROOT / 'report_0914_v3.docx'
doc.save(out)
comments = [
    ('本稿在0914-v2基础上澄清两项贡献', 'v3：已澄清方法和新增构造诊断，未更改历史成绩或运行正式实验。'),
    ('（1）设计结论中心的局部结构保持增强方法。', 'v3：贡献落实为输入、改写单位、保持对象与输出。独立增益仍需与普通改写和随机中心对照。'),
    ('邻域节点按结论的入边选取', 'v3：按现有代码补齐诱导边集合与边界边的处理，不再把邻域理解成只有中心入边的星形结构。'),
    ('新参考实现每接受一个变体便增加一篇完整文档。', 'v3：这是全文回填协议的正确计数单位，未改写组件也会随整篇样本再次进入训练。'),
    ('该因果门控更准确的含义是', 'v3：条件分支只在类型闭合后开启，不应解释为直接纠正当前类型字段。'),
    ('新参考实现对JSON或必需字段解析失败的候选', 'v3：解析失败不能交给图级BR；原表JSON错误变化的归因仍待核验。'),
    ('覆盖分量和连贯性分量复用同一组边判断', 'v3：两个聚合指标不是独立语义证据，需做各自消融。'),
    ('LocalRerun固定全部组件，只替换指定源节点的出边', 'v3：DENS的源集合可能包含几乎全图节点，不宜宣称只修改一跳邻域。'),
    ('反例四：改变覆盖集合可以提高代理分数而损害组件预测。', 'v3：已用现有BR代码复现接受错误类型修改的构造反例；不代表真实测试频率。'),
    ('B.5 覆盖评分投机的保守修订方向', 'v3：新接受条件及动作约束属于建议变体，未更改现有算法或以旧结果背书。'),
]
helper = '/Users/channtang/.codex/plugins/cache/openai-primary-runtime/documents/26.909.12148/skills/documents/scripts/comments_add.py'
args = [sys.executable, helper, str(out), '--out', str(WORK / 'commented.docx'), '--author', 'Codex 0914-v3 修订', '--require_all']
for anchor, note in comments:
    args.extend(['--add', anchor + '=' + note])
subprocess.run(args, check=True)
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(WORK / 'commented.docx') as zin:
    xml = etree.fromstring(zin.read('word/document.xml'))
    for p in xml.xpath('//w:p[w:pPr]', namespaces=ns):
        prop = p.find('{' + ns['w'] + '}pPr')
        if p.index(prop):
            p.remove(prop)
            p.insert(0, prop)
    payload = etree.tostring(xml, xml_declaration=True, encoding='UTF-8', standalone=True)
    with ZipFile(out, 'w') as zout:
        for info in zin.infolist():
            zout.writestr(info, payload if info.filename == 'word/document.xml' else zin.read(info.filename))
(WORK / 'comment_log.json').write_text(json.dumps(comments, ensure_ascii=False, indent=2))
print('Added', len(comments), 'v3 comments; prior comments retained in the unchanged v2 artifact')
