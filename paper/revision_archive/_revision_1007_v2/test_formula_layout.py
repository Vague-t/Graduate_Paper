"""Layout-only stress test of all retained display equations, never a deliverable."""
from pathlib import Path
import re
import sys

import build_docx as build

assert Path(sys.executable).resolve() == build.base.BUNDLED_PYTHON.resolve()
source = build.ROOT / 'report_1007_v1_full.md'
lines = build.base.load_manuscript(source)
builder = build.Builder(build.TEMPLATE, lines, {})
builder.doc.add_paragraph('独立公式排版压力测试', style='Title')
builder.furniture(builder.doc.sections[0])
chapter, count = '0', 0
for kind, value, _ in build.base.blocks(lines):
    if kind == 'heading' and value[0] == 1:
        match = re.match(r'^第([一二三四五六])章', value[1])
        if match:
            chapter = str('一二三四五六'.index(match[1]) + 1)
            count = 0
    elif kind == 'math':
        count += 1
        builder.doc.add_paragraph(f'以下为原稿独立公式 {chapter}-{count}，仅测试原生公式宽度与编号。')
        builder.display_math(value, f'{chapter}-{count}')
builder.save(build.WORK / 'formula_fixture.docx')
print('Retained native display equations:', len(builder.equation_records))
