from pathlib import Path
import re, json, statistics
from collections import defaultdict
from PIL import Image, ImageOps, ImageDraw
from pypdf import PdfReader

BASE=Path(__file__).parent
s=(BASE/'source_ordered.txt').read_text()
tables={}
for b,body in re.findall(r'\[(B\d+) TABLE\]\n(.*?)\[END TABLE\]',s,re.S):
    tables[b]=[[x.strip() for x in l.split('|')[1:]] for l in body.strip().splitlines()]

by=defaultdict(list)
checks=[]
for r in tables['B1034'][1:]:
    corp,method,seed,tp,fp,fn,reported=r
    f=200*int(tp)/(2*int(tp)+int(fp)+int(fn))
    by[corp,method].append(f)
    checks.append({'corpus':corp,'method':method,'seed':seed,'derived_F1':f,'reported_F1':reported,'match_to_2dp':f'{f:.2f}'==reported})
summary={f'{c}/{m}':{'mean':statistics.mean(v),'SD':statistics.stdev(v)} for (c,m),v in by.items()}
contrasts={}
for c in ['AAEC','CDCP']:
    a,b,d,e=(by[c,m] for m in ['T0I0','T1I0','T0I1','T1I1'])
    contrasts[c]={'training':[y-x for x,y in zip(a,b)],'inference':[y-x for x,y in zip(b,e)],
                  'total':[y-x for x,y in zip(a,e)],'interaction':[ee-bb-dd+aa for aa,bb,dd,ee in zip(a,b,d,e)]}
audit={ 'F1_checks':checks,'summary':summary,'contrasts':contrasts,
        'scope':'Only arithmetic from printed manuscript. No raw-data, p-value, CI or authenticity validation.'}
(BASE/'arithmetic_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(json.dumps({'f1_rows':len(checks),'all_match':all(c['match_to_2dp'] for c in checks),'summary':summary,'contrasts':contrasts},ensure_ascii=False,indent=2))

reader=PdfReader(BASE/'render_fontconfig/manuscript_review_test.pdf')
page_text=[]
for i,p in enumerate(reader.pages,1):
    page_text.append(f'\n[RENDER PAGE {i}]\n'+p.extract_text())
(BASE/'render_pages.txt').write_text('\n'.join(page_text))
print('Render pages:',len(reader.pages))

pages=sorted((BASE/'render_fontconfig').glob('page-*.png'),key=lambda x:int(x.stem.split('-')[1]))
for group in range(0,len(pages),12):
    sheet=Image.new('RGB',(4*330,3*485),'#dddddd')
    d=ImageDraw.Draw(sheet)
    for j,path in enumerate(pages[group:group+12]):
        im=Image.open(path).convert('RGB')
        im.thumbnail((320,450))
        x=(j%4)*330+(330-im.width)//2
        y=(j//4)*485+25
        sheet.paste(im,(x,y))
        d.text(((j%4)*330+10,(j//4)*485+6),path.stem,fill='black')
    sheet.save(BASE/f'contact-{group//12+1:02d}.jpg',quality=90)
