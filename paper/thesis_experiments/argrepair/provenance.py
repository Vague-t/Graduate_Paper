"""Bind local model artifacts to executable run identities."""
from pathlib import Path
import json
from .io import file_hash
from .schema import digest

def model_artifact_identity(model_id,requested_revision=None,resolved_revision=None):
    path=Path(model_id)
    result={'model_id':str(model_id),'requested_revision':requested_revision,'resolved_revision':resolved_revision}
    if not path.is_dir():return result
    files={str(p.relative_to(path)):file_hash(p) for p in sorted(path.glob('*'))
           if p.is_file() and (p.suffix in {'.safetensors','.bin','.json','.txt','.model','.tiktoken'} or p.name=='LICENSE')
           and p.name!='download_manifest.json'}
    manifest=path/'download_manifest.json'
    if manifest.exists():
        saved=json.loads(manifest.read_text())
        for name,expected in saved.get('files',{}).items():
            p=path/name
            if not p.is_file() or (files[name] if name in files else file_hash(p))!=expected:raise ValueError(f'local model differs from pinned download: {name}')
        result['resolved_revision']=saved['revision'];result['download_manifest_sha256']=file_hash(manifest)
    result.update(local_artifacts_sha256=digest(files),files=files)
    return result
