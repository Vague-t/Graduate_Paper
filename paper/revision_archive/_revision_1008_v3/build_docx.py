"""Build 1008-v3 from the retained v2 package without changing old files.

The parent runs the sole artifact marker. Only bundled Python may execute
this builder. Final source is supplied separately; fixtures are QA-only.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
SOURCE = ROOT / 'report_1008_v3_full.md'
TEMPLATE = ROOT / 'report_1007_v2_full.docx'
OUTPUT = ROOT / 'report_1008_v3_full.docx'
WARNING = '1008-v3 修订稿　含非实测占位　勿送审'
TEMPLATE_SHA256 = 'e3c136b8791e792da9a4d04debdbdd1cb35497be9550b0cd6cbaf85d66794d12'

spec = importlib.util.spec_from_file_location('v2_layout_readonly', ROOT / '_revision_1007_v2/build_docx.py')
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)
base = v2.base
for key, value in {'WORK': WORK, 'SOURCE': SOURCE, 'TEMPLATE': TEMPLATE,
                   'OUTPUT': OUTPUT, 'WARNING': WARNING}.items():
    setattr(v2, key, value)

CONTROL = re.compile(r'(?<![A-Za-z_])(?:end (?:for|while|if)|else if|for|while|if|then|do|else|return|break|continue)(?![A-Za-z_])', re.I)
MANUAL = re.compile(r'^( *)(\d{1,3})[.)、]?( +)(.*)$')
IO = re.compile(r'^(?:输入|输出|Input|Output)[：:]', re.I)


def parse_algorithm(code):
    """Return semantic lines: no indent is inferred from prose or keywords.

    Preferred input is unnumbered pseudocode with exactly two spaces per
    nesting level. Existing line-number prefixes are accepted if continuous.
    Initial Input/Output lines and their indented continuations are unnumbered.
    """
    visible = [line.rstrip() for line in code if line.strip()]
    if any('\t' in line for line in visible):
        raise ValueError('Algorithm source must use two spaces per level, not tabs')
    matches = [MANUAL.match(line) for line in visible]
    separators = [len(match[3]) for match in matches if match]
    separator = min(separators) if separators else 1
    result, step, io_block = [], 0, False
    for line, match in zip(visible, matches):
        if match:
            indent = len(match[1]) + len(match[3]) - separator
            text, supplied = match[4], int(match[2])
        else:
            indent = len(line) - len(line.lstrip(' '))
            text, supplied = line.lstrip(' '), None
        if indent % 2:
            raise ValueError(f'Algorithm indentation is not a multiple of two: {line!r}')
        is_io = bool(IO.match(text))
        continuation = io_block and step == 0 and indent > 0 and supplied is None
        if is_io or continuation:
            io_block = True
            number = None
        else:
            io_block = False
            step += 1
            number = step
            if supplied is not None and supplied != step:
                raise ValueError(f'Algorithm line numbers must be consecutive: {supplied} != {step}')
        result.append({'number': number, 'depth': indent // 2, 'text': text,
                       'io': is_io or continuation})
    return result


class Builder(v2.Builder):
    def __init__(self, template, lines, page_map):
        assert v2.digest(template) == TEMPLATE_SHA256
        super().__init__(template, lines, page_map)
        self.bookmarks = {key: value.replace('v2_', 'v3_', 1)
                          for key, value in self.bookmarks.items()}
        splits = WORK / 'algorithm_splits.json'
        self.algorithm_splits = json.loads(splits.read_text()) if splits.exists() else {}

    def contents_field(self, title, entries, instruction):
        start = len(self.doc.paragraphs)
        super().contents_field(title, entries, instruction)
        if title == '目录':
            for paragraph in self.doc.paragraphs[start:]:
                if paragraph.style.name == 'TOC 1':
                    # Apply to the level-one TOC style so Word's later native
                    # update retains the grouping, not just cached text.
                    paragraph.paragraph_format.space_before = base.Pt(6)
                    paragraph.paragraph_format.keep_with_next = True
        elif title in ('图目录', '表目录'):
            style = self.doc.styles['Figure List' if title == '图目录' else 'Table List']
            for paragraph in self.doc.paragraphs[start:]:
                if paragraph.style.name == 'TOC 1':
                    paragraph.style = style

    def apply_styles(self):
        super().apply_styles()
        style = self.doc.styles['TOC 1']
        style.paragraph_format.space_before = base.Pt(6)
        style.paragraph_format.keep_with_next = True
        # Caption lists use the same cached style but do not need chapter gaps.
        for name in ('Figure List', 'Table List'):
            styles = self.doc.styles
            if name not in styles:
                styles.add_style(name, v2.WD_STYLE_TYPE.PARAGRAPH)
            styles[name].base_style = styles['TOC 1']
            styles[name].paragraph_format.space_before = base.Pt(0)
            styles[name].paragraph_format.keep_with_next = False

    def inline(self, paragraph, text, size=None):
        match = v2.IMAGE.fullmatch(text.strip())
        if not match:
            return super().inline(paragraph, text, size)
        path = (ROOT / match[2]).resolve()
        allowed = [WORK / 'figures', ROOT / '_revision_1007_v2/figures']
        assert path.is_file() and any(path.is_relative_to(folder) for folder in allowed), path
        fmt = paragraph.paragraph_format
        fmt.first_line_indent = base.Pt(0)
        fmt.line_spacing = 1
        fmt.space_before, fmt.space_after = base.Pt(4), base.Pt(3)
        fmt.keep_with_next = True
        paragraph.alignment = base.WD_ALIGN_PARAGRAPH.CENTER
        shape = paragraph.add_run().add_picture(str(path), width=self.text_width)
        shape._inline.docPr.set('descr', match[1] + '。机制示意，非实测案例。')
        shape._inline.docPr.set('name', path.name)

    def algorithm_text(self, paragraph, text):
        for part in base.INLINE.split(text):
            if not part:
                continue
            if part.startswith('$') and part.endswith('$'):
                self.inline(paragraph, part, 10.5)
                continue
            cursor = 0
            for match in CONTROL.finditer(part):
                if match.start() > cursor:
                    self.inline(paragraph, part[cursor:match.start()], 10.5)
                base.font_run(paragraph.add_run(match[0]), 10.5, True)
                cursor = match.end()
            if cursor < len(part):
                self.inline(paragraph, part[cursor:], 10.5)

    def algorithm(self, code, caption=''):
        lines = parse_algorithm(code)
        key = caption.split(' ', 1)[0]
        split_steps = self.algorithm_splits.get(key, [])
        assert split_steps == sorted(set(split_steps))
        split_indices = {index for index, line in enumerate(lines)
                         if line['number'] in split_steps}
        assert len(split_indices) == len(split_steps)
        for index, line in enumerate(lines):
            if index in split_indices:
                continuation = self.doc.add_paragraph(key + '（续）', style='Continuation Caption')
                continuation.paragraph_format.page_break_before = True
                continuation.paragraph_format.keep_with_next = True
            paragraph = self.doc.add_paragraph(style='Algorithm Line')
            fmt = paragraph.paragraph_format
            text_offset = 7 + line['depth'] * 4
            # All numbers align at the same left edge. Both the first text
            # line and wrapped lines start at the semantic indentation level.
            fmt.left_indent = base.Mm(text_offset)
            fmt.first_line_indent = base.Mm(-text_offset)
            fmt.tab_stops.clear_all()
            fmt.tab_stops.add_tab_stop(base.Mm(text_offset))
            fmt.line_spacing = base.Pt(15)
            fmt.space_after = base.Pt(0)
            fmt.keep_together = True
            fmt.keep_with_next = index < len(lines) - 1 and (
                len(lines) <= 35 or line['io'] or
                bool(re.match(r'^(?:for|while|if|else)\b', line['text'], re.I)) or
                index >= len(lines) - 3)
            prefix = '' if line['number'] is None else f"{line['number']:02d}"
            base.font_run(paragraph.add_run(prefix + '\t'), 10.5)
            self.algorithm_text(paragraph, line['text'])
            top = index == 0 or index in split_indices
            bottom = index == len(lines) - 1 or index + 1 in split_indices
            if top or bottom:
                border = v2.node('w:pBdr')
                for side, needed in [('top', top), ('bottom', bottom)]:
                    if needed:
                        border.append(v2.node('w:' + side, val='single', sz='4',
                                              color='000000', space='4'))
                paragraph._p.get_or_add_pPr().append(border)
        self.algorithm_records.append({'caption': caption,
                                       'lines': sum(line['number'] is not None for line in lines),
                                       'total_lines': len(lines),
                                       'split_before_steps': split_steps,
                                       'max_depth': max((line['depth'] for line in lines), default=0),
                                       'source_lines': lines})


def main():
    assert v2.digest(TEMPLATE) == TEMPLATE_SHA256
    v2.Builder = Builder
    v2.main()
    assert v2.digest(TEMPLATE) == TEMPLATE_SHA256


if __name__ == '__main__':
    main()
