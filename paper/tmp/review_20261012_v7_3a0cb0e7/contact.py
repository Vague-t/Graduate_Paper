from pathlib import Path
from PIL import Image, ImageDraw
import json

base = Path(__file__).parent
pages = sorted((base / 'render').glob('page-*.png'), key=lambda p: int(p.stem.split('-')[-1]))
for start in range(0, len(pages), 12):
    sheet = Image.new('RGB', (1600, 1720), '#cccccc')
    draw = ImageDraw.Draw(sheet)
    for k, path in enumerate(pages[start:start + 12]):
        picture = Image.open(path).convert('RGB')
        picture.thumbnail((392, 536))
        x = (k % 4) * 400 + (400 - picture.width) // 2
        y = (k // 4) * 570 + 28
        sheet.paste(picture, (x, y))
        draw.text(((k % 4) * 400 + 10, (k // 4) * 570 + 5), path.stem, fill='black')
    sheet.save(base / f'contact-{start // 12 + 1:02d}.jpg', quality=90)
print(json.dumps({'pages': len(pages), 'contact_sheets': (len(pages) + 11) // 12}))
