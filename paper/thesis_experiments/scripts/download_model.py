"""Download a pinned public HF model; no corpus or manuscript is uploaded."""
import argparse,json,hashlib
from pathlib import Path
from huggingface_hub import HfApi,snapshot_download
p=argparse.ArgumentParser();p.add_argument('--model',default='Qwen/Qwen2.5-0.5B-Instruct');p.add_argument('--output',required=True);p.add_argument('--revision',default='main');a=p.parse_args()
info=HfApi().model_info(a.model,revision=a.revision);revision=info.sha
snapshot_download(a.model,revision=revision,local_dir=a.output,allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.tiktoken','LICENSE','README.md'],max_workers=2)
hashes={}
for f in sorted(Path(a.output).glob('*')):
    if not f.is_file() or f.name=='download_manifest.json':continue
    h=hashlib.sha256()
    with f.open('rb') as src:
        for b in iter(lambda:src.read(8*1024*1024),b''):h.update(b)
    hashes[f.name]=h.hexdigest()
(Path(a.output)/'download_manifest.json').write_text(json.dumps({'model':a.model,'revision':revision,'files':hashes},indent=2)+'\n')
print(json.dumps({'model':a.model,'revision':revision,'files':len(hashes),'output':a.output}))
