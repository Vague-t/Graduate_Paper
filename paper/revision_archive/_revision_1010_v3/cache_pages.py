"""Read the latest render and cache verified page numbers for native fields.

The cached text is not a substitute for the Word TOC field: build_docx.py keeps
the field editable and sets updateFields. This script only reads a PDF and
writes task-local mapping/diagnostic JSON. Use bundled Python only.
"""
import argparse
import json
from pathlib import Path
import re
import sys

import pdfplumber

WORK = Path(__file__).resolve().parent
PYTHON = Path('/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3')


def norm(text):
    return re.sub(r'[\s$`*]+', '', text).replace('（', '(').replace('）', ')')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    args = parser.parse_args()
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    build = json.loads((WORK / 'docx_build.json').read_text())
    labels = [entry[1] for entry in build['headings']] + build['captions']
    pages, mapping, locations, missing = [], {}, {}, []
    with pdfplumber.open(args.pdf) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            lines = (page.extract_text(x_tolerance=2, y_tolerance=3) or '').splitlines()
            footer = lines[-1].strip() if lines else ''
            if not re.fullmatch(r'\d+|[IVXLCDM]+', footer):
                footer = ''
            pages.append({'physical': index, 'printed': footer, 'lines': lines})
    for label in labels:
        needle = norm(label)
        found = []
        for page in pages:
            lines = page['lines']
            for start in range(len(lines)):
                for length in range(1, 5):
                    if norm(''.join(lines[start:start + length])) == needle:
                        found.append(page)
                        break
                else:
                    continue
                break
        # Cached TOC lines include leaders/page numbers and do not compare equal.
        if len(found) == 1 and found[0]['printed']:
            mapping[label] = found[0]['printed']
            locations[label] = found[0]['physical']
        else:
            missing.append({'label': label, 'matching_physical_pages': [p['physical'] for p in found]})
    report = {'pdf': str(args.pdf.resolve()), 'pages': len(pages),
              'matched': len(mapping), 'unresolved': missing, 'physical_pages': locations,
              'warning_missing_pages': [p['physical'] for p in pages
                                        if '1010-v3' not in norm(''.join(p['lines']))]}
    (WORK / 'page_map.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    (WORK / 'page_map_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if missing or report['warning_missing_pages']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
