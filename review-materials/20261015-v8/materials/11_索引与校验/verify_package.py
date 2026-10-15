from pathlib import Path
import hashlib, json, sys
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'11_索引与校验/文件清单.json').read_text(encoding='utf-8'))
bad=[]
for row in manifest['files']:
    p=root/row['path']
    if not p.is_file() or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
        bad.append(row['path'])
print('Verified',len(manifest['files']),'indexed files; failures:',len(bad))
for path in bad: print(path)
sys.exit(bool(bad))
