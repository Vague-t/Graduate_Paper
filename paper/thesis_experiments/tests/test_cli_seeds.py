"""Seeds must bind head initialization, not just post-initialization minibatches."""
import torch
import pytest
from test_cli_integration import configuration,fixture_document,pool_files,run_cli
from argrepair.io import write_jsonl,read_json

@pytest.mark.parametrize('stage',['span-train','scorer-train'])
def test_head_initialization_is_reproducible_across_fresh_processes(tmp_path,stage):
    cfg,_=configuration(tmp_path);doc=fixture_document('train' if stage=='span-train' else 'fit')
    data=tmp_path/'source.jsonl';write_jsonl(data,[doc.to_dict()])
    extra=[] if stage=='span-train' else ['--pools',*pool_files(tmp_path,[doc])]
    checkpoints=[]
    for name in ('a','b'):
        out=tmp_path/name
        run_cli(stage,'--config',cfg,'--data',data,'--corpus','aaec','--seed','29','--out',out,*extra)
        assert read_json(out/'manifest.json')['effective_seed']==29
        checkpoints.append(torch.load(out/('span' if stage=='span-train' else 'scorer'),weights_only=True))
    fields=['boundary_head','type_head'] if stage=='span-train' else ['component_head','relation_head']
    for field in fields:
        assert all(torch.equal(value,checkpoints[1][field][key]) for key,value in checkpoints[0][field].items())
