"""Create a self-contained evidence archive; no rewriting frozen source files."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,zipfile

ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=read(ROOT/'combined_metrics.json');integrity=read(ROOT/'integrity_audit.json')
assert integrity['status']=='PASS' and read(ROOT/'replay_all.json')['all_replay_invariants_passed']
files=set()
for name in m['verified_wave_hashes']:
    files.update(p for p in (WORK/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files.update(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='package_audit.json')
for name in ['1011_Luna扩样分析与正例核验记录.md','1011_Luna扩样正例与反例核验.md','report_1011_v9_full.md','report_1011_v9_full.docx','research_0920/run_feasibility.py','research_0920/data/aaec_brat.zip','research_0920/data/aaec_split.csv','research_0920/data/cdcp_acl17.zip']:
    files.add(WORK/name)
for rootname in m['verified_wave_hashes']:
    root=WORK/rootname
    if (root/'source_freeze.json').exists():
        files.update(WORK/name for name in read(root/'source_freeze.json')['old_files'])
assert all(p.is_file() for p in files)
members={str(p.relative_to(WORK)):p.read_bytes() for p in sorted(files)}
members['requirements-replay.txt']=b'numpy==1.26.4\nscipy==1.13.1\n'
verifier='''"""Read-only hash check for the extracted evidence package."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parent
lines=(root/'SHA256SUMS').read_text().splitlines()
for line in lines:
    expected,name=line.split('  ',1)
    p=(root/name).resolve()
    assert root in p.parents and p.is_file(),name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
print('PASS',len(lines),'archived file hashes')
'''
members['verify_bundle.py']=verifier.encode()
readme=f'''# Luna扩样分析证据包

日期：2026-10-11。AAEC {m['aggregate']['aaec']['documents']}篇，CDCP {m['aggregate']['cdcp']['documents']}篇，共{len(m['documents'])}个唯一文本，包含原16篇。新增模型任务数为{integrity['new_model_tasks']}，请求模型为gpt-5.6-luna、推理强度low；底层API调用次数和采样参数未暴露。

先读根目录的《1011_Luna扩样分析与正例核验记录.md》和《1011_Luna扩样正例与反例核验.md》。全部逐篇结果、停止依据、候选评分诊断和核验记录在research_1011_luna_expansion_analysis目录。

本包包含原生数据压缩包、冻结模型输出、评分、候选、全部修正轨迹、代码以及未改动的v9论文。论文作为版本参照，仍保留其模拟主实验披露；本次新增结果尚未写入论文。没有把扩样案例搜索改称独立测试或完整BR-J实验。原16篇位于research_1010_v7_luna；新增第一波48篇位于research_1011_luna_expanded；其后目录w02至w07分别是CDCP扩展波次。

## 完整性校验

解压后在本目录运行：

```sh
python3 verify_bundle.py
```

## 冻结分数的本地重放

原环境为macOS arm64、Python 3.9.6、NumPy 1.26.4、SciPy 1.13.1及其内置HiGHS。Python依赖不包含在包内，请在独立环境安装requirements-replay.txt中的版本。不同平台、求解器或负载可能影响限时求解结果；本次实际重放只验证了记录中的本地环境。

```sh
python3 research_1011_luna_expansion_analysis/replay_all.py --output /tmp/luna_expansion_replay_new.json
```

输出路径必须尚不存在。重放不读金标、不再调用Luna，逐文档检查终态、提交索引和显式失败是否复现。本次296个运行的终态／失败一致，但6组提交路径不同；差异与完整诊断重放记录一并保留。它不是模型随机重采样，也不验证训练可复现性。不要直接再次运行prepare、pipeline、run_wave或evaluate覆盖既有冻结目录。

## 路径与保存规则

报告和历史JSON中的绝对路径保留原运行来源，未为打包改写；在另一台机器上请按相同相对目录定位文件。SHA256SUMS记录包内除自身以外每个文件。包内所有原始文件与本地来源字节一致。部分继承元数据仍描述原8篇/三批次上下文；真实文档与任务数以每波sample_manifest、model_dispatch_manifest及逐篇结果为准。

已有报告记载了输入失败评价约定、第4波非法组件类型的解析失败保留处理、同一次回答生成两个候选图、共享文件系统指令式盲法和未校准启发式分数。所有失败和负例保留。
'''
members['README.md']=readme.encode()
sums={name:hashlib.sha256(b).hexdigest() for name,b in members.items()}
members['SHA256SUMS']=''.join(f'{sums[name]}  {name}\n' for name in sorted(sums)).encode()
target=WORK/'1011_Luna扩样分析证据包.zip'
with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name,b in sorted(members.items()):z.writestr('luna_expansion_20261011/'+name,b)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(members)
    for name,h in sums.items():assert hashlib.sha256(z.read('luna_expansion_20261011/'+name)).hexdigest()==h,name
audit={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS','zip':str(target),'zip_sha256':sha(target),'bytes':target.stat().st_size,'members':len(members),'sha256sum_entries':len(sums),'zip_crc_check':'PASS','all_member_hashes':'PASS','source_files_preserved_byte_for_byte':len(files),'dependencies_bundled':False}
with (ROOT/'package_audit.json').open('x') as f:json.dump(audit,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(audit,ensure_ascii=False,indent=2))
