#!/usr/bin/env python3
"""Restore only the exact files listed by this organization operation; never overwrite."""
from pathlib import Path
import hashlib,json,argparse
A=Path(__file__).resolve().parent
M=json.loads((A/'归档清单_20261013.json').read_text())
R=Path(M['root'])
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
if M['status']=='restored':raise SystemExit('Already restored.')
issues=[]
for e in M['records']:
 src=A/e['archived'];dst=R/e['original']
 if dst.exists() or dst.is_symlink():issues.append('Original location occupied: '+str(dst))
 if not src.is_file() or src.is_symlink():issues.append('Archived file missing or replaced: '+str(src))
 elif sha(src)!=e['sha256']:issues.append('Archived contents changed: '+str(src))
if issues:raise SystemExit('\n'.join(issues))
print('Preflight passed:',len(M['records']),'files. No overwrite.')
if not args.apply:raise SystemExit('Dry run only. Add --apply to restore.')
moved=[]
try:
 for e in M['records']:
  src=A/e['archived'];dst=R/e['original']
  if dst.exists() or dst.is_symlink():raise RuntimeError('New collision: '+str(dst))
  src.rename(dst);moved.append((src,dst))
except Exception:
 for src,dst in reversed(moved):
  if dst.exists() and not src.exists():dst.rename(src)
 raise
M['status']='restored'
(A/'归档清单_20261013.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))
print('Restored. Archive index and organization record retained.')
