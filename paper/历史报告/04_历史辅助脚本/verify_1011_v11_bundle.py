from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
m=json.loads((root/'1011_v11交付清单.json').read_text())
for name,expected in m['files'].items():
    p=root/name
    assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
print('PASS:',len(m['files']),'files; read-only, no model calls')
