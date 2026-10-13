from pathlib import Path
import json, hashlib, re
import pdfplumber

work=Path(__file__).resolve().parent; root=work.parent
expected={'report_0914_v3.md':'3b1b22db1df8113e260d7d9a033b140876cb19413ae80c50792f2b29457305f7','report_0914_v3.docx':'2d84af152fb226efda7523a88146148dcfb8b4bb21f69e52cecdc2ae79264dcb'}
for name,digest in expected.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
meta=json.loads((work/'render_stable/structural_verification.json').read_text())
assert hashlib.sha256((root/'report_0915_v1.docx').read_bytes()).hexdigest()==meta['docx_sha256']
coverage=json.loads((work/'visual_coverage.json').read_text())
assert len(coverage['pages'])==55 and not coverage['requiring_final_visual_review']
norm=lambda x:re.sub(r'\s+','',x)
with pdfplumber.open(work/'render_stable/report_0915_v1.pdf') as pdf:
    toc=norm(pdf.pages[4].extract_text())
    for head,page in meta['toc'].items():assert norm(head)+str(page) in toc,(head,page)
    for i,page in enumerate(pdf.pages[5:],1):
        footer=page.crop((0,page.height-50,page.width,page.height)).extract_text().strip()
        assert footer==str(i),(i,footer)
report={'source_files_unchanged':True,'final_docx_matches_render':True,'all_55_page_bodies_visually_reviewed_or_pixel_identical':True,'toc_all_11_entries_correct':True,'footer_sequence_1_to_50':True,'docx_sha256':meta['docx_sha256'],'md_sha256':hashlib.sha256((root/'report_0915_v1.md').read_bytes()).hexdigest()}
(work/'final_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
