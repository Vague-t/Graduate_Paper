from pathlib import Path
from PIL import Image
import hashlib, json, sys

work=Path(__file__).resolve().parent
sources={}
for dirname, pages in [('render_initial', range(1,5)), ('render_review', range(5,55)), ('render_layout_final',[24,54,55]), ('render_stable',[24,51]), ('render_deliver_final',[5])]:
    for n in pages:
        p=work/dirname/f'page-{n}.png'
        im=Image.open(p).convert('RGB')
        body=im.crop((0,0,im.width,im.height-130))
        digest=hashlib.sha256(body.tobytes()).hexdigest()
        sources.setdefault(digest, []).append(str(p.relative_to(work)))
mapped=[]; unmatched=[]
target=sys.argv[1] if len(sys.argv)>1 else 'render_deliver_final'
for p in sorted((work/target).glob('page-*.png'), key=lambda x:int(x.stem.split('-')[1])):
    im=Image.open(p).convert('RGB')
    body=im.crop((0,0,im.width,im.height-130))
    digest=hashlib.sha256(body.tobytes()).hexdigest()
    record={'page':int(p.stem.split('-')[1]), 'pixel_identical_body_to':sources.get(digest,[])}
    mapped.append(record)
    if not record['pixel_identical_body_to']:unmatched.append(record['page'])
(work/'visual_coverage.json').write_text(json.dumps({'pages':mapped,'requiring_final_visual_review':unmatched},indent=2))
print('Total pages:',len(mapped),'New or reflowed pages needing visual review:',unmatched)
