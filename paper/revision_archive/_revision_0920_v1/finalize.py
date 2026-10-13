"""Deterministic comment insertion, rendered-TOC extraction and artifact checks."""
from pathlib import Path
from zipfile import ZipFile
import argparse, hashlib, json, re, subprocess, sys
from lxml import etree
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
DOCX = ROOT / 'report_0920_v1.docx'
MD = ROOT / 'report_0920_v1.md'
COMMENTS = [
    ('第一，设计面向结论组件的关系感知增强学习方法', '训练侧主线已升级为完整影响域增强与成对因素学习；ICIC专项训练作为基础，不把旧成绩归给新增机制。'),
    ('第二，提出多候选驱动的依赖闭合论辩图修正方法', '主方案改为BR-J；BR-O与BR-C保留对照。允许组件集合修改，但不承诺每次修正提高真实F1。'),
    ('原ICIC方法已经可以改变组件类型和候选跨度', '更正递进关系：新增是集合级恢复、依赖闭合和整体接受，不是首次允许组件修改。'),
    ('二元情形即', '完整性仅相对于声明宇宙的端点关联域；域外篇章语义影响另行审计。'),
    ('单纯复制标注没有显式约束原文与改写文本的预测行为', '补上模型子词映射和训练输入隔离，避免池化错位及金标条件泄漏。'),
    ('该效用具有明确的代价解释', '这是固定误检/漏检代价的期望风险解释，不是期望F1或一般最优性定理。'),
    ('全局ILP采用局部终态的松弛可行域', '全局末态约束较局部逐步门宽；包含关系建立目标上界，不能误称两者同域。'),
    ('原稿域内表、消融、验证器、Oracle', '9张历史数值/协议表保留在附录E，分类别表的81.67/77.82冲突未代为填改。'),
    ('本次正文修改不等于已将新增机制合入实验项目', '本文与已有参考工程的实现差距单列，避免方法设计被误读为已完成正式实验。'),
]

def comments():
    helper = '/Users/channtang/.codex/plugins/cache/openai-primary-runtime/documents/26.909.61513/skills/documents/scripts/comments_add.py'
    staged = WORK / 'commented.docx'
    args = [sys.executable, helper, str(DOCX), '--out', str(staged), '--author', 'Codex 0920-v1 修订', '--require_all']
    for anchor, note in COMMENTS:
        args += ['--add', anchor + '=' + note]
    subprocess.run(args, check=True)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with ZipFile(staged) as source:
        root = etree.fromstring(source.read('word/document.xml'))
        for paragraph in root.xpath('//w:p[w:pPr]', namespaces=ns):
            prop = paragraph.find('{' + ns['w'] + '}pPr')
            if paragraph.index(prop):
                paragraph.remove(prop)
                paragraph.insert(0, prop)
        body = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        with ZipFile(DOCX, 'w') as output:
            for info in source.infolist():
                output.writestr(info, body if info.filename == 'word/document.xml' else source.read(info.filename))
    (WORK / 'comment_log.json').write_text(json.dumps(COMMENTS, ensure_ascii=False, indent=2))
    print(f'Added {len(COMMENTS)} review comments')

def pdf_toc(path):
    pdf = PdfReader(path)
    heads = [x for x in re.findall(r'^## (.+)$', MD.read_text(), re.M)
             if re.match(r'^第.+章 |^附录[A-E] |^参考文献$', x)]
    compact = lambda s: re.sub(r'\s+', '', s)
    candidates = {}
    for index, page in enumerate(pdf.pages):
        content = compact(page.extract_text())
        if content.count('第一章绪论') and content.count('第二章任务表示'):
            continue
        for head in heads:
            if compact(head) in content:
                candidates.setdefault(head, []).append(index)
    assert all(h in candidates for h in heads), candidates
    starts = {h: values[0] for h, values in candidates.items()}
    first = starts['第一章 绪论']
    mapping = {h: index-first+1 for h,index in starts.items()}
    (WORK / 'toc_pages.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2))
    summary = {'physical_pages': len(pdf.pages), 'body_start_physical': first+1, 'toc': mapping}
    (WORK / 'pagination.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False))

def audit():
    text = MD.read_text()
    source = (ROOT/'report_0915_v1.md').read_text()
    mapping = [('3-1',1),('4-2',2),('4-3',3),('4-4',4),('4-5',5),('4-6',6),('4-7',7),('5-1',8),('5-2',9)]
    def table(content, number):
        return re.search(r'^表'+re.escape(number)+r'[^\n]*\n\n(\|[^\n]*\n(?:\|[^\n]*(?:\n|$))*)', content,re.M).group(1).strip()
    preserved = {old: table(source,old)==table(text,f'E-{new}') for old,new in mapping}
    assert all(preserved.values()), preserved
    refs = set(map(int,re.findall(r'^\[(\d+)\] ',text,re.M)))
    prose = text.split('## 参考文献')[0] + text.split('## 附录A')[1]
    used = set(map(int,re.findall(r'\[(\d+)\]',prose)))
    assert not used-refs, used-refs
    ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
    with ZipFile(DOCX) as z:
        xml = etree.fromstring(z.read('word/document.xml'))
        visible = ''.join(xml.xpath('//w:t/text() | //m:t/text()',namespaces=ns))
        assert '<!--' not in visible and 'anchor:section' not in visible and 'ref:tang' not in visible
        assert '版本说明' not in visible
        math_count = len(xml.xpath('//m:oMath',namespaces=ns))
        comment_count = len(etree.fromstring(z.read('word/comments.xml')).xpath('//w:comment',namespaces=ns))
        assert comment_count == len(COMMENTS)
    old_hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['report_0915_v1.md','report_0915_v1.docx']}
    assert old_hashes['report_0915_v1.md']=='1d3e02e849dd3c9c101c25e3af0bfb5efc02395d849ecc62d04a1a3be0fc7d5c'
    assert old_hashes['report_0915_v1.docx']=='f8505f9101865abccb6c1e27da7a4a016dd78318697d5c53f7b9934287516ecd'
    result={'historical_tables_unchanged':preserved,'references':len(refs),'missing_citations':sorted(used-refs),'unused_references':sorted(refs-used),'native_equations':math_count,'comments':comment_count,'original_hashes':old_hashes,'output_md_sha256':hashlib.sha256(MD.read_bytes()).hexdigest(),'output_docx_sha256':hashlib.sha256(DOCX.read_bytes()).hexdigest()}
    (WORK/'final_content_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))

parser=argparse.ArgumentParser()
parser.add_argument('--comments',action='store_true')
parser.add_argument('--toc',type=Path)
parser.add_argument('--audit',action='store_true')
args=parser.parse_args()
if args.comments: comments()
if args.toc: pdf_toc(args.toc)
if args.audit: audit()
