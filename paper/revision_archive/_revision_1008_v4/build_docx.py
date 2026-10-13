"""Build v4 with the retained v3 package and its tested native-math layout.

The parent ran the sole artifact marker. Old source/packages/scripts remain
read-only. Execute only with the bundled Python runtime.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
SOURCE = ROOT / 'report_1008_v4_full.md'
TEMPLATE = ROOT / 'report_1008_v3_full.docx'
OUTPUT = ROOT / 'report_1008_v4_full.docx'
WARNING = '1008-v4 逐项润色稿　含非实测占位　勿送审'
TEMPLATE_SHA256 = 'e3cda7c0e31b57f908b6c89c685967c1b713c85646565de1a59ecc7968a752f1'

spec = importlib.util.spec_from_file_location('v3_layout_readonly', ROOT / '_revision_1008_v3/build_docx.py')
v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v3)
for module in (v3, v3.v2):
    for key, value in {'WORK': WORK, 'SOURCE': SOURCE, 'TEMPLATE': TEMPLATE,
                       'OUTPUT': OUTPUT, 'WARNING': WARNING}.items():
        setattr(module, key, value)
v3.TEMPLATE_SHA256 = TEMPLATE_SHA256


class Builder(v3.Builder):
    def __init__(self, template, lines, page_map):
        super().__init__(template, lines, page_map)
        self.bookmarks = {key: value.replace('v3_', 'v4_', 1)
                          for key, value in self.bookmarks.items()}


def main():
    assert v3.v2.digest(TEMPLATE) == TEMPLATE_SHA256
    v3.v2.Builder = Builder
    v3.v2.main()
    assert v3.v2.digest(TEMPLATE) == TEMPLATE_SHA256


if __name__ == '__main__':
    main()
