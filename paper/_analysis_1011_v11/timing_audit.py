"""Read-only source audit; emit timing metadata without conversation contents."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
W=Path(__file__).resolve().parent;R=W.parent
source=Path('/Users/channtang/.codex/sessions/2026/10/09/rollout-2026-10-09T19-05-02-01a11ff5-f242-7350-a6d8-7fb6dd66ac45_01a12056-7f6f-7051-a745-485ee7f6b03f.jsonl')
turn='01a129bf-fcea-7373-9fd4-f390490af67b';events={}
for line in source.open():
 o=json.loads(line);p=o.get('payload',{})
 if o.get('type')=='event_msg' and p.get('turn_id')==turn and p.get('type') in ['task_started','task_complete']:
  events[p['type']]=datetime.fromisoformat(o['timestamp'].replace('Z','+00:00')).timestamp()
assert set(events)=={'task_started','task_complete'}
local=lambda t:datetime.fromtimestamp(t).isoformat(timespec='seconds')
st=lambda n: (R/n).stat()
times=[events['task_started'],st('research_1011_v11/candidate/evaluation/coverage.json').st_birthtime,st('_revision_1011_v11/render_pass1').st_birthtime,st('_revision_1011_v11/final_audit.json').st_mtime,events['task_complete']]
total=times[-1]-times[0]
phases=[]
for i,name in enumerate(['实验设计、模型任务、程序实现与首轮评价','模拟生成、结果解释和首版文稿编排','首版渲染后迭代、格式与内容一致性核验','最终说明、打包及交付']):
 d=times[i+1]-times[i];phases.append({'phase':name,'start_local':local(times[i]),'end_local':local(times[i+1]),'seconds':d,'minutes':d/60,'percent':100*d/total})
versions=[]
for v in ['1010_v7','1010_v8','1011_v9','1011_v10','1011_v11']:
 rows=[]
 for p in sorted((R/('_revision_'+v)).glob('render*')):
  images=list(p.glob('page-*.png')) if p.is_dir() else []
  if images:
   start=p.stat().st_birthtime;end=max(x.stat().st_mtime for x in images)
   rows.append({'directory':str(p.relative_to(R)),'pages':len(images),'start_local':local(start),'end_local':local(end),'file_production_seconds':end-start})
 versions.append({'version':v,'render_runs':len(rows),'rendered_page_images':sum(x['pages'] for x in rows),'render_file_production_seconds':sum(x['file_production_seconds'] for x in rows),'runs':rows})
f=R/'research_1011_v11/solver/results/run_001'
a=json.loads((f/'input_freeze.json').read_text())['at_utc'];b=json.loads((f/'output_freeze.json').read_text())['at_utc']
solver=(datetime.fromisoformat(b)-datetime.fromisoformat(a)).total_seconds()
out={'version':'1011-v11','timezone':'Asia/Shanghai','manuscript_sha256':hashlib.sha256((R/'report_1011_v11_full.md').read_bytes()).hexdigest(),'turn_start_local':local(times[0]),'turn_end_local':local(times[-1]),'turn_elapsed_minutes':total/60,'phase_method':'Non-overlapping wall-clock windows delimited by saved milestones; each window includes mixed activities. Not CPU time, model sampling time, or exclusive category attribution. Late independent recount and content fixes are included in the post-render window.','phases':phases,'render_method':'Directory creation to latest page PNG mtime; approximate output-production elapsed time, excludes thinking, inspection, revisions, TOC caching and inter-call gaps.','recent_versions':versions,'solver_batch_input_to_output_freeze_seconds':solver,'token_and_monetary_cost':'Not reliably attributable from this audit; no estimate reported.'}
(W/'timing_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'total_minutes':out['turn_elapsed_minutes'],'phases':phases,'render_runs':versions[-1]['render_runs'],'render_output_seconds':versions[-1]['render_file_production_seconds'],'solver_batch_seconds':solver},ensure_ascii=False,indent=2))
