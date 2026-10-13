"""Read-only PDF geometry and pagination evidence; not a visual-QA substitute."""
import argparse
import json
from pathlib import Path

import pdfplumber

WORK = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    args = parser.parse_args()
    pages, outside_page, outside_body = [], [], []
    with pdfplumber.open(args.pdf) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            chars = [char for char in page.chars if char.get('text', '').strip()]
            for char in chars:
                if char['x0'] < -1 or char['x1'] > page.width + 1 or char['top'] < -1 or char['bottom'] > page.height + 1:
                    outside_page.append({'page': number, 'text': char['text'], 'bbox': [char['x0'], char['top'], char['x1'], char['bottom']]})
                # Header/footer and the broad title line use a distinct layout.
                if number > 1 and 65 < char['top'] < page.height - 65 and (char['x0'] < 75 or char['x1'] > 528):
                    outside_body.append({'page': number, 'text': char['text'], 'bbox': [round(char['x0'], 2), round(char['top'], 2), round(char['x1'], 2), round(char['bottom'], 2)]})
            pages.append({'page': number, 'width_pt': page.width, 'height_pt': page.height,
                          'text_characters': len(chars), 'images': len(page.images),
                          'body_max_bottom_pt': max([c['bottom'] for c in chars if 65 < c['top'] < page.height - 65], default=None)})
    result = {'pdf': str(args.pdf.resolve()), 'page_count': len(pages),
              'outside_page': outside_page, 'outside_body_candidates': outside_body,
              'pages': pages, 'visual_review_required': True}
    (WORK / 'render_geometry.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'pages'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
