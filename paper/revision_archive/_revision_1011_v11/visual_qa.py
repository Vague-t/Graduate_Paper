from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
import hashlib,json
W=Path(__file__).resolve().parent;R=W.parent;new=W/'render_release';old=W/'render_final';out=W/'visual_contacts_release';out.mkdir(exist_ok=True)
def num(p):return int(p.stem.split('-')[1])
def digest(p):
 im=Image.open(p).convert('RGB');return hashlib.sha256(im.crop((0,100,im.width,im.height-95)).tobytes()).hexdigest()
lookup={digest(p):num(p) for p in old.glob('page-*.png')};pages=sorted(new.glob('page-*.png'),key=num);matches={};changed=[]
for p in pages:
 k=digest(p)
 if k in lookup:matches[str(num(p))]=lookup[k]
 else:changed.append(num(p))
for offset in range(0,len(pages),6):
 batch=pages[offset:offset+6];thumbs=[]
 for p in batch:
  im=Image.open(p).convert('RGB');im.thumbnail((420,594));tile=Image.new('RGB',(444,630),'#e4e4e4');tile.paste(im,((444-im.width)//2,24));ImageDraw.Draw(tile).text((12,7),f'Physical page {num(p)}',fill='black');thumbs.append(tile)
 canvas=Image.new('RGB',(444*3,630*2),'white')
 for i,im in enumerate(thumbs):canvas.paste(im,((i%3)*444,(i//3)*630))
 canvas.save(out/f'contact-{offset//6+1:02d}.jpg',quality=90)
report={'reference_pdf_sha256':hashlib.sha256((old/'report_1011_v11_full.pdf').read_bytes()).hexdigest(),'current_pdf_sha256':hashlib.sha256((new/'report_1011_v11_full.pdf').read_bytes()).hexdigest(),'crop':'exclude top100px header and bottom95px footer; all body pixels compared exactly','exact_body_matches_to_reviewed_v11_pass':matches,'changed_body_pages':changed,'total_pages':len(pages)}
(W/'body_render_comparison_release.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'matched':len(matches),'changed':changed,'pages':len(pages)}))
