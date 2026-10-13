from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
import hashlib, json, re

O=Path(__file__).resolve().parents[1]
S=Path('/Users/channtang/Downloads/论文规范排版稿_v7.docx')
D=O/'论文规范排版稿_v8.docx'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'pic':'http://schemas.openxmlformats.org/drawingml/2006/picture'}
W='{'+NS['w']+'}'; M='{'+NS['m']+'}'
X=lambda e,q:e.xpath(q,namespaces=NS)
T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S)=='3a0cb0e7f210d494f5f793d498dae50bf61886cd09987f8184beaefcf3871e66'
with ZipFile(S) as z: data={n:z.read(n) for n in z.namelist()}
root=E.fromstring(data['word/document.xml']); body=root.find(W+'body')
blocks={f'B{i:04d}':e for i,e in enumerate(body)}
patches=json.loads((O/'_agents/protocol/patches.json').read_text())
patches+=json.loads((O/'_agents/statistics/patches.json').read_text())['patches']
for patch in patches:
    if patch['block_id']=='B0961':patch['new_text']=patch['new_text'].replace('来源，；','来源；')
    if patch['block_id']=='B0714':
        patch['new_text']='相同候选、评分和时限的比较需同时报告预算语义及求解证书。R_DC表示追加阶段的依赖闭合决策及固定路由，完整I1由继承I0与R_DC串接而成；集合局部BR-J是其中的可选子程序。I1相对I0衡量完整继承结果上追加修正的收益，不能据此评价R_DC替代BR-O的效果，也不能将总收益全部归于BR-J。'
patches.append({'block_id':'B0003','op':'replace_text','old_text':'2026年10月 · v7','new_text':'2026年10月 · v8','reason':'封面更新为文稿v8，保留全部实验与记录版本标识。'})
changes=[]

def replace_fragment(e,old,new):
    nodes=X(e,'.//w:t|.//m:t'); whole=''.join(n.text or '' for n in nodes)
    assert whole.count(old)==1,(old,whole)
    start=whole.index(old); end=start+len(old); pos=0; inserted=False
    for node in nodes:
        text=node.text or ''; a=pos; b=pos+len(text); pos=b
        if b<=start or a>=end:continue
        assert node.tag==W+'t',('would overwrite native math',old,E.tostring(node))
        lo=max(start-a,0);hi=min(end-a,len(text))
        node.text=text[:lo]+(new if not inserted else '')+text[hi:]
        node.set('{http://www.w3.org/XML/1998/namespace}space','preserve');inserted=True
    assert T(e)==whole[:start]+new+whole[end:]

def math_run(text,normal=False,size='23'):
    r=E.Element(M+'r');wp=E.SubElement(r,W+'rPr');E.SubElement(wp,W+'sz',{W+'val':size})
    if normal:E.SubElement(E.SubElement(r,M+'rPr'),M+'nor')
    E.SubElement(r,M+'t',{'{http://www.w3.org/XML/1998/namespace}space':'preserve'}).text=text
    return r

def sub(base,subscript,size='23'):
    s=E.Element(M+'sSub');E.SubElement(s,M+'e').append(math_run(base,size=size))
    E.SubElement(s,M+'sub').append(math_run(subscript,normal=True,size=size));return s

def set_plain(e,text):
    p=e if e.tag==W+'p' else e.find(W+'p')
    oldr=p.find(W+'r'); rpr=deepcopy(oldr.find(W+'rPr')) if oldr is not None and oldr.find(W+'rPr') is not None else None
    for child in list(p):
        if child.tag!=W+'pPr':p.remove(child)
    r=E.SubElement(p,W+'r')
    if rpr is not None:r.append(rpr)
    E.SubElement(r,W+'t').text=text
    if e.tag==W+'tc':
        for other in list(e.findall(W+'p'))[1:]:e.remove(other)

for patch in patches:
    e=blocks[patch['block_id']];before=T(e);op=patch['op']
    if op in ('replace_text','replace_text_fragment'):
        replace_fragment(e,patch['old_text'],patch['new_text'])
    elif op=='replace_cell':
        candidates=[c for c in X(e,'.//w:tc') if T(c)==patch['old_text']]
        assert len(candidates)==1,(patch,candidates)
        if patch['old_text']=='修正前固定；P在此不是精确率':
            replace_fragment(candidates[0],'修正前固定；','追加R_DC前固定；')
            replace_fragment(candidates[0],'在此不是精确率','为候选集合，非提案模块代号或Precision')
        else:replace_fragment(candidates[0],patch['old_text'],patch['new_text'])
    elif op=='replace_math':
        om=e.find(M+'oMath');assert om is not None
        parts=list(om); assert T(om)=='Grank=argmaxG∈SErank(G),    G0=LA(Grank).'
        # Retain native argmax and L_A notation, split across two centered lines.
        for n in parts:om.remove(n)
        arr=E.SubElement(om,M+'eqArr')
        pr=E.SubElement(arr,M+'eqArrPr');E.SubElement(pr,M+'baseJc',{M+'val':'center'})
        line1=E.SubElement(arr,M+'e');line2=E.SubElement(arr,M+'e')
        for n in parts[:8]:line1.append(n)
        line2.append(sub('G','pre'))
        for n in parts[10:15]:line2.append(n)
        line2.append(math_run(',    '));line2.append(sub('G','0'))
        line2.append(math_run('=BR-O(',True));line2.append(sub('G','pre'));line2.append(math_run(').'))
    elif op=='insert_table_rows':
        rows=e.findall(W+'tr');target=next(r for r in rows if T(r.find(W+'tc'))==patch['after_row_key'])
        at=e.index(target)+1
        for rowdata in patch['new_rows']:
            values=rowdata[-3:];row=deepcopy(target);cells=row.findall(W+'tc');assert len(cells)==3
            for cell,value in zip(cells,values):set_plain(cell,value)
            sym=values[0];p=cells[0].find(W+'p')
            for child in list(p):
                if child.tag!=W+'pPr':p.remove(child)
            math=E.SubElement(p,M+'oMath')
            base,idx={'Grank':('G','rank'),'Gpre':('G','pre'),'I0':('I','0'),'R_DC':('R','DC'),'I1':('I','1')}[sym]
            math.append(sub(base,idx,size='20'))
            # A cloned row must never duplicate bookmark identities.
            for bm in X(row,'.//w:bookmarkStart|.//w:bookmarkEnd'):bm.getparent().remove(bm)
            e.insert(at,row);at+=1
    else:raise ValueError(patch)
    changes.append({'block_id':patch['block_id'],'op':op,'before':before,'after':T(e),'reason':patch['reason']})

# Bring the three references newly appended in v7 into the existing bibliography style.
layout_changes=[]
for bid in ['B0913','B0914','B0915']:
    e=blocks[bid];ppr=e.find(W+'pPr');e.replace(ppr,deepcopy(blocks['B0863'].find(W+'pPr')))
    sample=blocks['B0863'].find(W+'r').find(W+'rPr')
    for run in X(e,'.//w:r'):
        rpr=run.find(W+'rPr')
        if rpr is not None:run.remove(rpr)
        run.insert(0,deepcopy(sample))
    layout_changes.append({'block_id':bid,'change':'沿用参考文献既有10.5pt字号、悬挂缩进和1.25倍行距，保留条目文字。'})

# Normalize only the seven v7 tables still carrying the generic black TableGrid style.
style_table_ids=['B0397','B1140','B1217','B1220','B1224','B1227','B1231']
border_template=blocks['B0225'].find(W+'tblPr').find(W+'tblBorders')
for bid in style_table_ids:
    table=blocks[bid];pr=table.find(W+'tblPr')
    borders=pr.find(W+'tblBorders')
    if borders is not None:pr.remove(borders)
    pr.append(deepcopy(border_template))
    for cell in table.find(W+'tr').findall(W+'tc'):
        cp=cell.find(W+'tcPr');shd=cp.find(W+'shd')
        if shd is None:shd=E.SubElement(cp,W+'shd')
        shd.set(W+'fill','E7E6E6')
    layout_changes.append({'block_id':bid,'change':'边线与表头底色匹配全文既有灰色表样式；不改文字、列宽或字号。'})

# Update both linked image representations, maintaining each figure's natural ratio.
figures=[]
for idx,name,block_id in [(1,'fig2_1_overall_v8','B0322'),(2,'fig3_2_training_v8','B0407'),(3,'fig4_1_inference_v8','B0533')]:
    folder=O/'_agents/figures';svg=folder/(name+'.svg');png=folder/(name+'.png')
    sr=E.parse(str(svg)).getroot(); vb=[float(x) for x in sr.get('viewBox').split()]
    cx=5760000;cy=round(cx*vb[3]/vb[2])
    for tag in ['.//wp:extent','.//pic:spPr/a:xfrm/a:ext']:
        for ext in X(blocks[block_id],tag):ext.set('cx',str(cx));ext.set('cy',str(cy))
    data[f'word/media/image{idx}.png']=png.read_bytes()
    data[f'word/media/model_architecture_{idx}.svg']=svg.read_bytes()
    figures.append({'figure':name,'block_id':block_id,'cx':cx,'cy':cy,'svg_sha256':sha(svg),'png_sha256':sha(png)})

# Preserve TOC hyperlinks and replace page-number cache runs with PAGEREF fields.
headings=[]
for p in list(body):
    hyperlinks=X(p,'./w:hyperlink[starts-with(@w:anchor,"v7_toc_")]')
    if not hyperlinks:continue
    hl=hyperlinks[0];anchor=hl.get(W+'anchor');runs=hl.findall(W+'r');last=runs[-1]
    title=''.join(T(r) for r in runs[:-1]);field=E.Element(W+'fldSimple',{W+'instr':f' PAGEREF {anchor} \\h '})
    hl.replace(last,field);field.append(last)
    headings.append({'title':title,'bookmark':anchor})
assert len(headings)==145,len(headings)
data['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(D,'w',ZIP_DEFLATED) as z:
    for name,content in data.items():z.writestr(name,content)
manifest={'source':str(S),'source_sha256':sha(S),'output':str(D),'output_sha256':sha(D),'patches':len(patches),
          'edits':changes,'layout_changes':layout_changes,'style_table_ids':style_table_ids,'figures':figures,'headings':headings,'models_executed':False}
(O/'_work/revision_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(O/'_work/v8_fulltext.txt').write_text('\n'.join(f'{bid}\t{T(e)}' for bid,e in blocks.items() if T(e)))
print(json.dumps({'docx':str(D),'patches':len(patches),'math_objects':len(X(root,'.//m:oMath')),'toc_entries':len(headings),'figures':figures},ensure_ascii=False))
