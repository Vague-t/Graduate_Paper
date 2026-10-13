from copy import deepcopy
from lxml import etree as E

def apply_layout(r, blocks, X, T, NS):
    W='{'+NS['w']+'}'; M='{'+NS['m']+'}'
    changes=[]
    # LibreOffice misparses an OMML matrix nested inside limLow; flatten its
    # two conjunctive conditions without changing their symbols or meaning.
    e=blocks['B0420']; lim=X(e,'.//m:limLow/m:lim')[0]
    matrix=lim.find(M+'m'); rows=matrix.findall(M+'mr')
    assert len(rows)==2
    before=T(e)
    children=[]
    for i,row in enumerate(rows):
        if i:
            sep=E.Element(M+'r'); E.SubElement(sep,M+'t').text=', '
            children.append(sep)
        children.extend(deepcopy(c) for c in row.find(M+'e'))
    lim.remove(matrix)
    for c in children:lim.append(c)
    base=X(e,'.//m:limLow/m:e/m:r')[0]
    rp=base.find(M+'rPr');rp.clear();E.SubElement(rp,M+'nor')
    combined=X(lim,'.//m:r[m:t="≠NONE"]')[0]
    combined.find(M+'t').text='≠'
    plain=E.Element(M+'r');rp=E.SubElement(plain,M+'rPr');E.SubElement(rp,M+'nor')
    E.SubElement(plain,M+'t').text='NONE'
    combined.addnext(plain)
    assert T(e).replace(', ','')==before
    changes.append({'block_id':'B0420','kind':'math_layout','reason':'式3-9并集的两个下标条件改为同行并列；符号、限制与含义保持。'})

    # Match the previously added appendix K and bibliography entry to peers.
    for target,source in [('B1110','B1067'),('B0905','B0904')]:
        p=blocks[target];old=p.find(W+'pPr');p.remove(old);p.insert(0,deepcopy(blocks[source].find(W+'pPr')))
        changes.append({'block_id':target,'kind':'paragraph_format'})
    for e in X(blocks['B1110'],'.//w:r'):
        rp=e.find(W+'rPr')
        if rp is None:rp=E.SubElement(e,W+'rPr');e.remove(rp);e.insert(0,rp)
        for tag,val in [('sz','36'),('szCs','36'),('b','1'),('color','000000')]:
            n=rp.find(W+tag)
            if n is None:n=E.SubElement(rp,W+tag)
            n.set(W+'val',val)
    for key in ['B1111','B1116','B1124']:
        p=blocks[key]
        # Only actual K section headings.
        if not T(p).startswith(('K.1','K.2','K.3')):continue
        old=p.find(W+'pPr');p.remove(old);p.insert(0,deepcopy(blocks['B1070'].find(W+'pPr')))
        for run in X(p,'.//w:r'):
            rp=run.find(W+'rPr')
            if rp is None:rp=E.Element(W+'rPr');run.insert(0,rp)
            for tag,val in [('sz','30'),('szCs','30'),('b','1'),('color','000000')]:
                n=rp.find(W+tag)
                if n is None:n=E.SubElement(rp,W+tag)
                n.set(W+'val',val)
        changes.append({'block_id':key,'kind':'heading_format'})
    for key in ['B1110','B1111','B1116','B1124']:
        for run in X(blocks[key],'.//w:r'):
            rp=run.find(W+'rPr');rf=rp.find(W+'rFonts')
            if rf is None:rf=E.SubElement(rp,W+'rFonts')
            for a,v in [('ascii','Times New Roman'),('hAnsi','Times New Roman'),('eastAsia','黑体'),('cs','Times New Roman')]:rf.set(W+a,v)

    # Long immutable revision strings must not stretch neighboring Chinese.
    p=blocks['B1084'];pp=p.find(W+'pPr');j=pp.find(W+'jc')
    if j is None:j=E.SubElement(pp,W+'jc')
    j.set(W+'val','left');changes.append({'block_id':'B1084','kind':'left_align_revision'})

    # Keep method names legible in the dense timing table.
    t=blocks['B0750'];grid=t.find(W+'tblGrid');widths=[int(c.get(W+'w')) for c in grid]
    total=sum(widths); widths[0]+=360; delta=360
    for i in range(1,len(widths)):
        take=delta//(len(widths)-i);widths[i]-=take;delta-=take
    assert sum(widths)==total
    for c,w in zip(grid,widths):c.set(W+'w',str(w))
    for row in t.findall(W+'tr'):
        for cell,w in zip(row.findall(W+'tc'),widths):
            cell.find('./'+W+'tcPr/'+W+'tcW').set(W+'w',str(w))
    changes.append({'block_id':'B0750','kind':'column_width','widths':widths})

    # Bring newly inserted cross-backbone tables into the retained gray style.
    exemplar=blocks['B0750'].find('./'+W+'tblPr/'+W+'tblBorders')
    for key in ['B0833','B0836']+[k for k,v in blocks.items() if int(k[1:])>=1110 and v.tag==W+'tbl']:
        t=blocks[key];pr=t.find(W+'tblPr')
        old=pr.find(W+'tblBorders')
        if old is not None:pr.remove(old)
        pr.append(deepcopy(exemplar))
        for cell in t.findall(W+'tr')[0].findall(W+'tc'):
            cp=cell.find(W+'tcPr');shade=cp.find(W+'shd')
            if shade is None:shade=E.SubElement(cp,W+'shd')
            shade.set(W+'val','clear');shade.set(W+'color','auto');shade.set(W+'fill','E7E7E7')
        changes.append({'block_id':key,'kind':'table_style'})
    return changes
