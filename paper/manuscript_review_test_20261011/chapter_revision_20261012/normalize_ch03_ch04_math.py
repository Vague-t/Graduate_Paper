from copy import deepcopy
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def normalize_math_layout(element):
    """Normalize source notation and remove empty alignment cells, not mathematics."""
    for token in element.iter(qn('m:t')):
        if token.text:
            token.text = token.text.replace('\\', '∖')
    # The source used nested lower limits to draw descriptive underbraces.
    # These are labels only; the following prose already names both terms.
    for limit in list(element.iter(qn('m:limLow'))):
        base = limit.find(qn('m:e'))
        label = limit.find(qn('m:lim'))
        label_text = ''.join(t.text or '' for t in label.iter(qn('m:t'))) if label is not None else ''
        if label_text not in ('组件项', '关系项') or base is None or len(base) != 1:
            continue
        inner = base[0]
        if inner.tag != qn('m:limLow'):
            continue
        brace = inner.find(qn('m:lim'))
        if brace is None or ''.join(t.text or '' for t in brace.iter(qn('m:t'))) != '⏟':
            continue
        parent = limit.getparent()
        position = parent.index(limit)
        core = inner.find(qn('m:e'))
        for child in list(core):
            parent.insert(position, deepcopy(child))
            position += 1
        parent.remove(limit)
    for matrix in list(element.iter(qn('m:m'))):
        rows = matrix.findall(qn('m:mr'))
        cells = [cell for row in rows for cell in row.findall(qn('m:e'))]
        if not any(not list(cell) for cell in cells):
            continue
        before = ''.join(t.text or '' for t in matrix.iter(qn('m:t')))
        array = OxmlElement('m:eqArr')
        for cell in cells:
            if list(cell):
                array.append(deepcopy(cell))
        after = ''.join(t.text or '' for t in array.iter(qn('m:t')))
        assert before == after
        matrix.getparent().replace(matrix, array)
    return element
