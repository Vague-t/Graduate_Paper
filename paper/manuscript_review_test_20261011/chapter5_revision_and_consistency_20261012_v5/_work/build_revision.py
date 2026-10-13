from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
from collections import defaultdict
from lxml import etree as E
import json, hashlib, re

O = Path(__file__).resolve().parents[1]
S = O.parent/'formatted_word_pdf_20261012_v4/论文规范排版稿_v4.docx'
D = O/'论文规范排版稿_v5.docx'
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W = '{'+NS['w']+'}'
xp = lambda e,q:e.xpath(q,namespaces=NS)
txt = lambda e:''.join(xp(e,'.//w:t/text()|.//m:t/text()'))
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash = '1cee5133ade6a560b86d5d8dcd3f17b650dcaccc11d95c77ce92b9763f992361'
assert sha(S)==source_hash
with ZipFile(S) as z: data={n:z.read(n) for n in z.namelist()}
root=E.fromstring(data['word/document.xml']);body=root.find(W+'body')
blocks=json.loads((O/'_source/manuscript_blocks.json').read_text())
nodes={b['id']:body[b['body_index']] for b in blocks}
sources={b['id']:b for b in blocks}
for key,node in nodes.items():assert txt(node)==sources[key]['text'],key
def style(p):
    s=p.find('./'+W+'pPr/'+W+'pStyle')
    return s.get(W+'val') if s is not None else 'Normal'
templates={s:deepcopy(next(p for p in body if p.tag==W+'p' and style(p)==s))
           for s in ['BodyText','Heading3','TOC1','TOC2','TOC3']}
templates['BodyText']=deepcopy(nodes['B0768'])
def new_p(text, sty='BodyText'):
    template=templates[sty]
    p=E.Element(W+'p');pr=template.find(W+'pPr')
    if pr is not None:p.append(deepcopy(pr))
    r=E.SubElement(p,W+'r');rp=template.find('./'+W+'r/'+W+'rPr')
    if rp is not None:r.append(deepcopy(rp))
    t=E.SubElement(r,W+'t');t.text=text;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    return p
edits=[]
def replace(block_id,old,new,reason,change_id):
    node=nodes[block_id]
    assert old in txt(node),(block_id,old)
    if node.tag==W+'tbl':
        candidates=[p for p in xp(node,'.//w:p') if old in txt(p)]
        assert len(candidates)==1,(block_id,old,len(candidates))
        node=candidates[0]
    if block_id=='B1052' and old=='x或D':
        before=txt(node)
        maths=xp(node,'.//m:oMath');assert [txt(m) for m in maths]==['x','D']
        maths[1].getparent().remove(maths[1])
        for t in xp(node,'.//w:t'):t.text=''
        edits.append(dict(change_id=change_id,block_id=block_id,op='replace_text',before=before,after=txt(node),reason=reason))
        return
    if block_id=='B1052' and old=='推理修正不改写原文；第四章D另指删除集合':
        before=txt(node);assert [txt(m) for m in xp(node,'.//m:oMath')]==['D']
        ts=xp(node,'.//w:t');assert len(ts)==2
        ts[0].text=new+'；删除集合';ts[1].text='另列'
        edits.append(dict(change_id=change_id,block_id=block_id,op='replace_text',before=before,after=txt(node),reason=reason))
        return
    assert not xp(node,'.//m:oMath|.//w:drawing'),block_id
    ts=xp(node,'.//w:t');assert ts
    before=txt(node);after=before.replace(old,new)
    assert before.count(old)==1,(block_id,old)
    ts[0].text=after;ts[0].set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    for t in ts[1:]:t.text=''
    edits.append(dict(change_id=change_id,block_id=block_id,op='replace_text',before=before,after=after,reason=reason))
insertions=defaultdict(list)
def insert(block_id,where,text,reason,change_id,sty='BodyText'):
    insertions[(block_id,where)].append((new_p(text,sty),dict(change_id=change_id,block_id=block_id,op='insert_'+where,after=text,style=sty,reason=reason)))

proposal=json.loads((O/'_agents/revision/ch5_patch_proposal.json').read_text())
for op in proposal['operations']:
    if op['change_id']=='C5-001':
        op['new_text']=op['new_text'].replace('并以CDCP多源关系考察完整对象恢复的局限。','并分析CDCP多源关系的恢复局限。')
    if op['op']=='replace_text':
        replace(op['block_id'],op['old_text'],op['new_text'],op['reason'],op['change_id'])
    else:
        assert op['op'] in ['insert_before','insert_after']
        insert(op['block_id'],op['op'][7:],op['new_text'],op['reason'],op['change_id'],op['style'])
patches=json.loads((O/'_agents/compare/editorial_patches.json').read_text())['patches']
for i,p in enumerate(patches,1):
    if 765 <= int(p['block_id'][1:]) <=801:continue
    replace(p['block_id'],p['old'],p['new'],p['reason'],f'GLOBAL-{i:02}')
replace('B0770','实际训练输出、固定处理规则','训练侧拟合后的测试预测、固定后处理规则','明确CPU案例材料与主模型模拟结果的区别','GLOBAL-CPU')
replace('B0265','本章补充配置表','附录J的补充配置表','补充配置表已经移入附录J','GLOBAL-S2')

replace('B0221',sources['B0221']['text'],
        '本文共分为六章。第一章介绍研究背景与相关工作，提出研究问题并说明主要研究内容。其余各章安排如下。',
        '按参考论文逐章说明职责，避免将整篇组织压缩为一个长句','FLOW-01')
for i,t in enumerate([
    '第二章介绍论辩挖掘的任务表示、相关理论与技术，统一对象身份、评价规则及公共实验协议，为两阶段方法建立共同基础。',
    '第三章研究局部改写后的监督保持，依次说明关系影响域、可靠对应、学习目标和算法性质，并分析整套训练配置、成对目标及审核成本。',
    '第四章研究原文不变时的预测图修正，给出候选与评分、依赖闭合事务及求解过程，随后从受控比较、资源成本和实际案例分析其适用条件。',
    '第五章在共同评价条件下分析两阶段组合，依次讨论总体表现与交互、关系恢复来源、漏检成因及多源关系的局限。',
    '第六章总结两项研究及其组合分析，区分配置变化与机制贡献，并据此说明适用条件、证据局限和后续研究方向。附录集中保存数据坐标、实现验收、实验登记、外部对照、逐种子记录、案例定位与公共配置。'
],1):insert('B0221','after',t,'与修订后的各章实际职责逐项对应',f'FLOW-01-{i}')
insert('B0317','after',
       '第二章明确了完整对象表示和共同评价条件。在此基础上，本章首先讨论训练文本发生局部改写时，哪些组件与关系监督能够继续使用。下文依次介绍总体框架、增强构造、学习目标及算法性质，再通过受控比较分析整套训练配置、成对目标和审核成本。',
       '借鉴章首承接，将原3.1中的章节路线提到章题后','FLOW-02')
replace('B0322','本章依次介绍总体框架、增强构造、学习目标及算法性质，再通过受控比较讨论整套训练配置、成对目标和审核成本。','',
        '章节路线已移到章首，避免导语与引言重复','FLOW-03')
replace('B0323','本章沿用test稿件的模拟评审用途。','本章沿用本稿的模拟评审用途。','规范中文学术表述','FLOW-04')
insert('B0511','after',
       '训练阶段的监督保持并不直接保证预测图中所有组件及其关系都正确。下一章转向原文不变的推理场景，讨论组件修改后如何同步处理受影响关系。',
       '从训练监督的边界自然转入推理结构修正','FLOW-05')
insert('B0512','after',
       '第三章讨论训练文本改变后哪些监督可以继承，本章转向原文保持不变时的预测图修正。下文先说明候选和初始图，再给出评分及接受准则，随后用完整事务解释依赖闭合，最后介绍局部与全局求解、方法性质和实验分析。',
       '提炼现有引言中的承接和章节路线置于章题后','FLOW-06')
replace('B0514','第三章处理训练文本改变后哪些监督可以继承，本章转向推理阶段：在原文保持不变时，如何修改预测组件及其关系。','',
        '承接语已置于章首，引言直接展开技术动机','FLOW-07')
replace('B0516','下文先说明候选和初始图，再给出评分及接受准则，随后用完整事务解释依赖闭合，最后介绍局部与全局求解、方法性质和实验分析。本章沿用test稿件的模拟主结果；',
        '本章沿用本稿的模拟主结果；','章节路线已移到章首并规范中文表述','FLOW-08')
insert('B0764','after',
       '前两章分别分析了训练与推理配置的作用，尚需在相同关系身份下判断二者恢复对象的重叠及组合后的剩余错误。第五章据此开展两阶段框架的综合分析。',
       '说明独立综合分析章的必要性','FLOW-09')
insert('B0804','after',
       '前文分别研究了训练监督保持与推理结构修正，并分析了两阶段组合的表现及局限。本章据此归纳主要研究内容，区分现有材料能够支持的判断与尚待补齐的证据，最后讨论后续研究方向。',
       '用简短导语连接综合分析与研究总结','FLOW-10')

for (key,where),group in insertions.items():
    anchor=nodes[key]
    if where=='before':
        for node,record in group:anchor.addprevious(node);edits.append(record)
    else:
        for node,record in group:anchor.addnext(node);anchor=node;edits.append(record)

# Preserve existing heading anchors and add anchors only for new subheadings.
headings=[]
next_id=max(int(b.get(W+'id')) for b in xp(root,'.//w:bookmarkStart'))+1
new_count=0
for p in body:
    if p.tag!=W+'p' or style(p) not in ['Heading1','Heading2','Heading3']:continue
    if not txt(p):continue
    bookmarks=xp(p,'.//w:bookmarkStart[starts-with(@w:name,"ThesisHeading_")]')
    if bookmarks: name=bookmarks[0].get(W+'name')
    else:
        new_count+=1;name=f'ThesisHeading_v5_{new_count:03}'
        s=E.Element(W+'bookmarkStart');s.set(W+'id',str(next_id));s.set(W+'name',name)
        e=E.Element(W+'bookmarkEnd');e.set(W+'id',str(next_id));next_id+=1
        p.insert(1,s);p.append(e)
    headings.append({'title':txt(p),'bookmark':name,'level':int(style(p)[-1])})
old_toc=[p for p in body if p.tag==W+'p' and style(p).startswith('TOC')]
old_cache={xp(p,'.//w:hyperlink')[0].get(W+'anchor'):txt(xp(p,'.//w:fldSimple')[0]) for p in old_toc}
after_toc=old_toc[-1].getnext()
for p in old_toc:body.remove(p)
for h in headings:
    p=deepcopy(templates[f"TOC{h['level']}"])
    p.find('./'+W+'pPr/'+W+'spacing').set(W+'after','40')
    for child in list(p):
        if child.tag!=W+'pPr':p.remove(child)
    link=E.SubElement(p,W+'hyperlink');link.set(W+'anchor',h['bookmark'])
    E.SubElement(E.SubElement(link,W+'r'),W+'t').text=h['title']
    E.SubElement(E.SubElement(p,W+'r'),W+'tab')
    f=E.SubElement(p,W+'fldSimple');f.set(W+'instr',f" PAGEREF {h['bookmark']} \\h ")
    E.SubElement(E.SubElement(f,W+'r'),W+'t').text=old_cache.get(h['bookmark'],'1')
    after_toc.addprevious(p)
data['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(D,'w',ZIP_DEFLATED) as z:
    for n,b in data.items():z.writestr(n,b)
manifest={'source':str(S),'output':str(D),'source_sha256':source_hash,'output_sha256':sha(D),'edits':edits,'headings':headings,
          'new_heading_bookmarks':new_count,'changed_parts':['word/document.xml']}
(O/'_work/revision_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
assert sha(S)==source_hash

out=[];ch5=[];chapter='';rendered_blocks=[]
for i,node in enumerate(body):
    if node.tag not in [W+'p',W+'tbl']:continue
    if node.tag==W+'p' and style(node).startswith('TOC'):continue
    text=txt(node)
    if node.tag==W+'p' and style(node)=='Heading1':chapter=text
    rec={'body_index':i,'text':text,'kind':'tbl' if node.tag==W+'tbl' else 'p','chapter':chapter,'style':style(node) if node.tag==W+'p' else ''}
    rendered_blocks.append(rec)
    if node.tag==W+'tbl':
        rows=[[txt(c) for c in xp(r,'./w:tc')] for r in xp(node,'./w:tr')]
        lines=['| '+' | '.join(r)+' |' for r in rows];lines.insert(1,'| '+' | '.join(['---']*len(rows[0]))+' |')
        formatted='\n'.join(lines)
    elif style(node).startswith('Heading'):formatted='#'*int(style(node)[-1])+' '+text
    elif xp(node,'.//w:drawing'):formatted='[原稿图片保留]'
    else:formatted=text
    if formatted:out.append(formatted)
    if chapter.startswith('第五章') and formatted:ch5.append(formatted)
(O/'_work/revised_full_text.md').write_text('\n\n'.join(out))
(O/'_work/revised_blocks.json').write_text(json.dumps(rendered_blocks,ensure_ascii=False,indent=2))
(O/'第五章修订稿_v5.md').write_text('\n\n'.join(ch5)+'\n')
print(json.dumps({'output':str(D),'edits':len(edits),'new_headings':new_count,'toc_entries':len(headings),'sha256':sha(D)},ensure_ascii=False))
