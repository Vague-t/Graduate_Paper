from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
import json
base=Path(__file__).parent
pages=sorted((base/'render').glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
for start in range(0,len(pages),12):
    out=Image.new('RGB',(1600,1720),'#cccccc'); draw=ImageDraw.Draw(out)
    for k,p in enumerate(pages[start:start+12]):
        im=Image.open(p).convert('RGB'); im.thumbnail((392,536))
        x=(k%4)*400+(400-im.width)//2; y=(k//4)*570+28
        out.paste(im,(x,y)); draw.text(((k%4)*400+10,(k//4)*570+5),p.stem,fill='black')
    out.save(base/f'contact-{start//12+1:02d}.jpg',quality=90)
print(json.dumps({'pages':len(pages),'contact_sheets':(len(pages)+11)//12}))
