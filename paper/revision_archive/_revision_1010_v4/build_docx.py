"""Build the simulation edition from the retained v2 package."""
import importlib.util,sys,re
from pathlib import Path
import hashlib
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;R=W.parent
spec=importlib.util.spec_from_file_location('layout_v3_readonly',R/'_revision_1008_v3/build_docx.py')
v3=importlib.util.module_from_spec(spec);spec.loader.exec_module(v3)
template=R/'report_1010_v3_full.docx'
for mod in (v3,v3.v2):
    for k,v in {'WORK':W,'SOURCE':R/'report_1010_v4_full.md','TEMPLATE':template,'OUTPUT':R/'report_1010_v4_full.docx','WARNING':'1010-v4 模拟数据演示稿'}.items():setattr(mod,k,v)
v3.v2.CAPTION=re.compile(r'^(表|图|算法)([A-H0-9]+-\d+P?)\s+(.+)$')
v3.TEMPLATE_SHA256=hashlib.sha256(template.read_bytes()).hexdigest()
class Builder(v3.Builder):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw)
        self.bookmarks={k:v.replace('v3_','v12_',1) for k,v in self.bookmarks.items()}
        # Keep the newly added final contents entry on the preceding page.
        for level in [2,3]:
            self.doc.styles[f'TOC {level}'].paragraph_format.space_after=v3.base.Pt(.6)
    def furniture(self,section,numbered=True,roman=False):
        super().furniture(section,numbered,roman)
        for p in section.header.paragraphs:
            for run in p.runs:
                if '1010-v4' in run.text:run.text='1010-v4'
    def cover(self):
        super().cover()
        source=(R/'report_1010_v4_full.md').read_text()
        disclosure=re.search(r'^稿件说明：(.+)$',source,re.M).group(1)
        p=self.doc.add_paragraph('稿件说明：'+disclosure)
        p.paragraph_format.first_line_indent=v3.base.Pt(0)
        p.paragraph_format.space_before=v3.base.Pt(22)
        p.paragraph_format.space_after=v3.base.Pt(0)
        p.paragraph_format.line_spacing=v3.base.Pt(16)
        p.paragraph_format.keep_together=True
        for run in p.runs:v3.base.font_run(run,10)
        date=next(x for x in self.doc.paragraphs if x.text=='2026年10月')
        date._p.addnext(p._p)
    def inline(self,paragraph,text,size=None):
        before=len(self.doc.inline_shapes)
        super().inline(paragraph,text,size)
        if len(self.doc.inline_shapes)>before:
            shape=self.doc.inline_shapes[-1]
            label=re.match(r'!\[([^]]*)\]',text)
            if label:shape._inline.docPr.set('descr',label.group(1))
    def table(self,rows):
        first=len(self.doc.tables)
        super().table(rows)
        key=self.table_caption.split(' ',1)[0]
        widths={'表4-9':[22,50,42.5,42.5],
                '表3-10':[35,21,24,21,26,30],
                '表4-10':[41,29,29,29,29],
                '表4-11':[31,18,27,27,33,21],
                '表4-12':[24,25,25,29,32,22],
                '表5-4':[20,23,23,23,23,23,22],
                '表5-5':[81,19,19,19,19],
                '表5-3':[38,40,39.5,39.5], '表5-6':[41,29,29,29,29],
                '表5-7':[32,31.25,31.25,31.25,31.25],
                '表G-1':[28,43,31,55], '表G-2':[26,61,70],
                '表H-1':[82,75]}.get(key)
        for table in self.doc.tables[first:]:
            if key=='表5-3':self.style_data_table(table,rows,True)
            if widths:
                assert len(table.columns)==len(widths),key
                for col,width in zip(table.columns,widths):col.width=v3.base.Mm(width)
                for row in table.rows:
                    for cell,width in zip(row.cells,widths):cell.width=v3.base.Mm(width)
    def save(self,output):
        super().save(output)
        self.doc.core_properties.keywords='模拟数据演示稿 关系感知学习 依赖闭合修正'
        self.doc.core_properties.subject='1010-v4 模拟数据演示稿；模拟身份见封面、摘要与实验表图'
        self.doc.save(output)
if __name__=='__main__':
    v3.v2.Builder=Builder
    v3.v2.main()
