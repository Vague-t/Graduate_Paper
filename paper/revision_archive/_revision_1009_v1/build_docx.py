"""Inherit the v4 package; regenerate authorized content with native math."""
import importlib.util,sys
from pathlib import Path
import hashlib
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;R=W.parent
spec=importlib.util.spec_from_file_location('layout_v3_readonly',R/'_revision_1008_v3/build_docx.py')
v3=importlib.util.module_from_spec(spec);spec.loader.exec_module(v3)
template=R/'report_1008_v4_full.docx'
expected=hashlib.sha256(template.read_bytes()).hexdigest()
for mod in (v3,v3.v2):
    for k,v in {'WORK':W,'SOURCE':R/'report_1009_v1_full.md','TEMPLATE':template,'OUTPUT':R/'report_1009_v1_full.docx','WARNING':'1009-v1 修订稿　构造验证不替代语料实验'}.items():setattr(mod,k,v)
v3.TEMPLATE_SHA256=expected
class Builder(v3.Builder):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw)
        self.bookmarks={k:v.replace('v3_','v5_',1) for k,v in self.bookmarks.items()}
    def save(self,output):
        super().save(output)
        self.doc.core_properties.keywords='关系感知学习 依赖闭合修正 构造验证 语料实证未完成'
        self.doc.save(output)
if __name__=='__main__':
    v3.v2.Builder=Builder
    v3.v2.main()
