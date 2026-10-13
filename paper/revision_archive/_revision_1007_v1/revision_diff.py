"""Record the complete manuscript delta without changing either source."""
from collections import Counter
from difflib import unified_diff
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
OLD = ROOT / "report_0923_v1_placeholder.md"
NEW = ROOT / "report_1007_v1_full.md"
OUT = Path(__file__).resolve().parent
old = OLD.read_text(encoding="utf-8")
new = NEW.read_text(encoding="utf-8")
diff = list(unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                         fromfile=OLD.name, tofile=NEW.name))
(OUT / "revision.diff").write_text("".join(diff), encoding="utf-8")

def section(text, start, end=None):
    result = text.split(start, 1)[1]
    return result.split(end, 1)[0].strip() if end else result.strip()

refs_same = section(old, "## 参考文献", "## 附录A") == section(new, "## 参考文献", "## 附录A")
archive_same = section(old, "## 附录E") == section(new, "## 附录E", "## 附录F")
p_pattern = r"(?<![\d.])\d+(?:\.\d+)?P"
placeholder_same = Counter(re.findall(p_pattern, old)) == Counter(re.findall(p_pattern, new))
display_same = re.findall(r"\$\$(.*?)\$\$", old, re.S) == re.findall(r"\$\$(.*?)\$\$", new, re.S)
assert refs_same and archive_same and placeholder_same and display_same
assert "P值" not in new
images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", new)
assert len(images) == 3 and all((ROOT / path).is_file() for path in images)
table_counts = {}
for table_id in ("5-5", "5-6", "5-7", "5-8", "5-9", "5-10"):
    pattern = rf"^表{table_id}[^\n]*\n\n(?:\|[^\n]*\n)+"
    old_table = re.search(pattern, old, re.M).group(0)
    new_table = re.search(pattern, new, re.M).group(0)
    assert old_table == new_table
    table_counts[table_id] = len(re.findall(p_pattern, new_table))
assert sum(table_counts.values()) == 116
report = {
    "baseline": OLD.name,
    "baseline_sha256": sha256(OLD.read_bytes()).hexdigest(),
    "new": NEW.name,
    "new_sha256": sha256(NEW.read_bytes()).hexdigest(),
    "diff_added_lines": sum(line.startswith("+") and not line.startswith("+++") for line in diff),
    "diff_removed_lines": sum(line.startswith("-") and not line.startswith("---") for line in diff),
    "references_unchanged": refs_same,
    "appendix_E_unchanged": archive_same,
    "placeholder_values_unchanged": placeholder_same,
    "placeholder_occurrences": len(re.findall(p_pattern, new)),
    "placeholder_table_numeric_cells": table_counts,
    "display_equations_unchanged": display_same,
    "display_equations": len(re.findall(r"\$\$(.*?)\$\$", new, re.S)),
    "figures": images,
    "new_heading_count": len(re.findall(r"^#{1,6} ", new, re.M)),
    "new_lines": len(new.splitlines()),
    "new_characters": len(new),
    "scope": "Editorial and explanatory revision; no new experiments or literature re-search.",
}
(OUT / "revision_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
