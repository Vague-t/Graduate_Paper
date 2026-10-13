"""Test the approved numbered algorithm and six-column case matrix in isolation."""
from pathlib import Path
import sys

import build_docx as build

assert Path(sys.executable).resolve() == build.base.BUNDLED_PYTHON.resolve()
lines = (build.WORK / 'chapter3.md').read_text(encoding='utf-8').splitlines()
builder = build.Builder(build.TEMPLATE, lines, {})
builder.furniture(builder.doc.sections[0])
pending = ''
for kind, value, _ in build.base.blocks(lines):
    if kind == 'text':
        label = build.base.clean_inline(value).replace('**', '')
        if build.CAPTION.fullmatch(label):
            pending = label
    elif kind == 'code' and pending.startswith('算法3-1'):
        builder.doc.add_paragraph(pending, style='Algorithm Caption')
        builder.algorithm(value[1], pending)
        pending = ''
    elif kind == 'table' and pending.startswith('表3-4'):
        paragraph = builder.doc.add_paragraph(pending, style='Table Caption')
        paragraph.paragraph_format.page_break_before = True
        builder.table_caption = pending
        builder.table(value)
builder.save(build.WORK / 'algorithm_fixture.docx')
print(builder.algorithm_records)
