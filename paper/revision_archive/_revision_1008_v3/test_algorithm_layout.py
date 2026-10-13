"""Build and structurally test a v3-only semantic-indentation fixture."""
import json
import re
from pathlib import Path
import sys

import build_docx as build

WORK = Path(__file__).resolve().parent
CODE = '''输入：训练文档 D，候选集合 U，预算 B 与固定评分器 f
输出：满足合法性检查的完整图 G
初始化当前合法图 G 与事务日志 L
for 每个文档 x in D do
  设置剩余预算 b ← B
  while b > 0 do
    构造依赖闭合事务 T
    if 事务非法 then
      记录拒绝原因
      continue
    else
      求解并复核完整新图 G_new
    end if
    if 分项非下降且总效用增益大于阈值 then
      原子提交 G ← G_new
    else
      整体回退并保留当前合法图
    end if
    递减剩余预算 b
  end while
end for
return G 与日志 L'''.splitlines()


def main():
    assert Path(sys.executable).resolve() == build.base.BUNDLED_PYTHON.resolve()
    parsed = build.parse_algorithm(CODE)
    assert [line['number'] for line in parsed[2:]] == list(range(1, 21))
    assert max(line['depth'] for line in parsed) == 3
    numbered = CODE[:2] + [f'{i:02d} ' + line for i, line in enumerate(CODE[2:], 1)]
    assert build.parse_algorithm(numbered) == parsed
    try:
        build.parse_algorithm(['if 条件 then', ' 操作', 'end if'])
    except ValueError:
        pass
    else:
        raise AssertionError('Odd source indentation must not be silently accepted')
    builder = build.Builder(build.TEMPLATE, [], {})
    builder.doc.add_paragraph('算法缩进与控制结构验证', style='Heading 1')
    p = builder.doc.add_paragraph('算法X-1 版式夹具（非论文内容）', style='Algorithm Caption')
    builder.algorithm(CODE, p.text)
    destination = WORK / 'algorithm_fixture.docx'
    builder.save(destination)
    paragraphs = [p for p in builder.doc.paragraphs if p.style.name == 'Algorithm Line']
    assert len(paragraphs) == len(CODE)
    for source, paragraph in zip(parsed, paragraphs):
        expected = 7 + source['depth'] * 4
        assert abs(paragraph.paragraph_format.left_indent.mm - expected) < .01
        assert abs(paragraph.paragraph_format.first_line_indent.mm + expected) < .01
        assert paragraph.text.split('\t', 1)[1] == source['text']
        for run in paragraph.runs:
            if build.CONTROL.fullmatch(run.text):
                assert run.bold and run.font.size.pt == 10.5
    print(json.dumps({'fixture': str(destination), 'semantic_lines': parsed,
                      'structural_checks': 'PASS'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
