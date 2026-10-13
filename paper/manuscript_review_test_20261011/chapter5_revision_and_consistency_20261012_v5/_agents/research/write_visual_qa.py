from pathlib import Path
from PIL import Image
import json,hashlib
base=Path('/Users/channtang/Downloads/paper/manuscript_review_test_20261011/chapter5_revision_and_consistency_20261012_v5')
root=base/'_render_v4'; out=base/'_agents/research'
notes={
29:'第三章章标题、无编号导语、3.1引言与3.2均完整；标题后有正文，未见孤立标题。',
30:'3.2.1/3.2.2标题、式(3-1)及中英文正文正常；公式编号位于右侧且无重叠。',
31:'式(3-2)/(3-3)、3.3及3.3.1层次清楚；表3-1标题与首部分表体同页。',
32:'表3-1续表重复表头；图3-1完整，图题与说明正常，未被跨页拆分。',
33:'完整正文及式(3-4)正常；页底公式无裁切。',
34:'3.3.2、式(3-5)、3.3.3均完整；页尾标题下保留实质正文。',
35:'审核掩码与语义未知因素连续正文正常，数学符号未见方框/缺字。',
36:'式(3-6)、3.3.4、表3-2及下方文字完整。',
37:'表3-3完整；3.4标题后保留正文，末行自然续下页。',
38:'图3-2及图题完整，细节文字较密但无碰撞或裁切；3.4.1及正文正常。',
39:'式(3-7)—(3-11)均可见；(3-11)在页底但公式和编号完整。',
40:'式(3-12)—(3-14)完整；3.4.2标题层次及公式间距正常。',
41:'3.5、算法3-1标题与输入/输出及前11行完整，算法自然跨页。',
42:'算法3-1从12行续至37行，缩进和行号可辨；算法后解释文字正常。',
43:'性质说明、3.6/3.6.1、表3-4标题及首两行完整。',
44:'表3-4续页重复表头；3.6.2及表3-5完整，数据/解释未重叠。',
45:'表3-6完整，负值/区间和种子列换行可辨；后续说明完整。',
46:'3.6.3、表3-7和表3-8完整；窄列内换行未裁切。',
47:'表3-9及说明正常；3.6.4、表3-10标题/表头及首行同页。',
48:'表3-10续表重复表头；3.7标题和小结开始部分完整，小结续下页。',
49:'第三章小结剩余段落和章间过渡完整；下方留白来自章节结束，非空白漏页。',
50:'第四章标题、无编号导语与4.1引言完整；下方留白与下页大图安放相容。',
51:'图4-1全图、图题及后续说明完整；4.2/4.2.1标题与正文正常。',
52:'式(4-1)—(4-3)和说明正常，数学符号/编号未见碰撞。',
53:'4.2.2和候选资源边界正文完整，行内符号无裁切。',
54:'候选边界连续正文正常；底部文字未越过版心。',
55:'4.3/4.3.1、式(4-4)及正文完整，标题无孤立。',
56:'4.3.2、式(4-5)及推导引入正常，页末自然续页。',
57:'式(4-6)/(4-7)、4.4/4.4.1与式(4-8)完整。',
58:'4.4.2、式(4-9)及正文正常；页尾句子自然续页，未截字。',
59:'4.4.3、表4-1标题和首部分完整。',
60:'表4-1续表重复表头；表4-2合并/多行单元格内容完整，未重叠。',
61:'4.5/4.5.1、式(4-10)—(4-12)及多行约束完整，编号对齐。',
62:'式(4-13)及局部执行说明完整，无文本/公式溢出。',
63:'算法4-1标题、输入输出、全部本页伪代码完整；末行与页码保持间隔。',
66:'4.5.2、式(4-14)—(4-16)完整，多行约束与编号清楚。',
67:'表4-3完整，多行表格内容未裁切；表后破同分说明自然续页。',
68:'4.5.3、式(4-17)及三个命题正文完整，符号可辨。',
69:'式(4-18)、4.5.4及正文完整，长段未越界。',
70:'4.6/4.6.1、表4-4及表4-5首部分完整；表4-5续至71页，续页不在本次分工范围。'
}
pages=list(range(29,64))+list(range(66,71));assert len(pages)==40 and set(pages)==set(notes)
records=[]
for n in pages:
 p=root/f'page-{n}.png'
 with Image.open(p) as im: dims=list(im.size)
 records.append({'physical_page':n,'printed_body_page':n-8,'image':str(p),'image_dimensions':dims,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'opened_at_full_native_size':True,'visual_inspection_completed':True,'result':'PASS','notes':notes[n],'defects':[]})
r={'schema':'document_visual_qa/1','reviewer':'ch5_reference_research','target_version':'chapter5_revision_and_consistency_20261012_v5','reviewed_render_directory':str(root),'scope':'physical pages 29-63 and 66-70 only','inspection_method':'Each of 40 native PNG images opened with view_image, read at its full 827x1170 source size; not contact-sheet-only inspection.','page_count':40,'opened_pages':pages,'defect_count':0,'blocking_defect_count':0,'result':'PASS_WITH_SCOPE_LIMIT','records':records,'normal_layout_observations':[{'pages':[31,32,43,44,47,48,59,60],'observation':'Spanning tables retain repeated headers; normal pagination accepted.'},{'pages':[48,49],'observation':'Chapter 3 summary spans pages; page 49 has chapter-end whitespace. No isolated title or missing content observed.'},{'pages':[50,51],'observation':'Chapter 4 opening precedes a large figure on the next page. Whitespace on page 50 is not clipping or missing content.'},{'pages':[70,71],'observation':'Table 4-5 continues beyond reviewed page 70. Page 71 must be covered by another reviewer.'}],'limitations':['No source DOCX/PDF was modified.','This record covers _render_v4 only. Parent must confirm final-body pixel identity or recheck any changed pages.','Pages 64-65 and all other unassigned pages were not opened in this QA pass.','Visual rendering review does not independently validate mathematical derivations, empirical evidence or numeric reproducibility.']}
(out/'visual_qa_v5.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
lines=['# v5 排版目视QA：物理页29—63、66—70','','## 范围与结论','','已逐张打开40页原尺寸PNG（827×1170），完整阅读页面内容与布局；未仅依赖缩略图。未发现裁切、重叠、缺字、标题孤立、图题错位或公式编号脱离等具体缺陷。未修改任何稿件或渲染文件。','','- 检查目录：`_render_v4`。','- 已打开页：'+', '.join(map(str,pages))+'。','- 明确缺陷：0；阻断缺陷：0。','- 结论限定：这40页的目视布局通过；最终渲染的正文像素一致性由主agent验证。','','## 正常布局观察','','- 表3-1（31—32）、表3-4（43—44）、表3-10（47—48）、表4-1（59—60）跨页且重复表头，均正常。','- 48—49页第三章小结跨页；49页为章末留白，无孤立标题或缺失内容。','- 50页为第四章导语与引言，51页放置大幅模型图；50页下方留白不构成裁切或漏排。','- 70页表4-5延续至71页；本分工只核对70页，71页需由其他分工覆盖。','','## 逐页记录','','| PDF物理页 | 正文页 | 结果 | 核对内容 |','|---|---:|---|---|']
for n in pages:lines.append(f'| {n} | {n-8} | 通过 | {notes[n]} |')
lines+=['','## 限制','','本轮没有检查64—65页或其他未分配页面，也未把目视排版核对当作公式推导、实验真实性或数值复现验证。JSON记录保留每张已打开图片的SHA-256，便于主agent确认最终稿正文一致性。']
(out/'visual_qa_v5.md').write_text('\n'.join(lines)+'\n')
print('Written',len(records),'page records; defects',r['defect_count'])
