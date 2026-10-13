"""Locate changed rendered pages and detect conspicuous red formula errors."""
from pathlib import Path
import argparse, json, hashlib
from PIL import Image
from pypdf import PdfReader

parser=argparse.ArgumentParser()
parser.add_argument('directory',type=Path)
parser.add_argument('--compare',type=Path)
args=parser.parse_args()
pages=sorted(args.directory.glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
red_pages=[]
changed=[]
for path in pages:
    number=int(path.stem.split('-')[-1])
    im=Image.open(path).convert('RGB')
    red=sum(1 for r,g,b in im.getdata() if r>100 and g<r*.55 and b<r*.55)
    if red>3: red_pages.append({'page':number,'red_pixels':red})
    if args.compare:
        prior=args.compare/path.name
        if not prior.exists() or hashlib.sha256(path.read_bytes()).digest()!=hashlib.sha256(prior.read_bytes()).digest():
            changed.append(number)
pdf=PdfReader(args.directory/'report_0920_v1.pdf')
text='\n'.join(page.extract_text() for page in pdf.pages)
result={'page_count':len(pages),'pdf_page_count':len(pdf.pages),'red_error_candidates':red_pages,'changed_pages':changed,'inverted_question_mark_in_text':'¿' in text,'png_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pages}}
(args.directory/'layout_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='png_sha256'},ensure_ascii=False))
