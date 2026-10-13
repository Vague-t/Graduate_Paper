"""Run all mandatory figure audits and retain each exit status without masking failures."""
from pathlib import Path
import os,sys,json,subprocess
W=Path(__file__).resolve().parent;S=Path('/Users/channtang/.codex/skills/nature-figure/scripts')
env=os.environ.copy();env['PYTHONPATH']=str(W/'vendor')
names=[r['name'] for r in json.loads((W/'figure_exports.json').read_text())]
selected=set(sys.argv[1:]); results=[]
for name in names:
    if selected and name not in selected:continue
    p=W/'figures'/name
    for kind,args in [('glyph',[str(S/'audit_pdf_text.py'),str(p)+'.pdf','--min-pt','5','--json']),('collision',[str(S/'audit_figure_collisions.py'),str(p)+'.pdf','--json-out',str(p)+'.collision.json','--overlay-pdf',str(p)+'.collision-overlay.pdf'])]:
        r=subprocess.run([sys.executable]+args,env=env,capture_output=True,text=True)
        (W/'figures'/f'{name}.{kind}.log').write_text(r.stdout+r.stderr)
        if kind=='glyph' and r.stdout.strip():
            try:(W/'figures'/f'{name}.glyph.json').write_text(json.dumps(json.loads(r.stdout),ensure_ascii=False,indent=2))
            except json.JSONDecodeError:pass
        results.append({'name':name,'audit':kind,'exit_code':r.returncode})
        print(name,kind,r.returncode,flush=True)
old=json.loads((W/'figure_audit_runs.json').read_text()) if (W/'figure_audit_runs.json').exists() else []
selected_names={r['name'] for r in results}
(W/'figure_audit_runs.json').write_text(json.dumps([r for r in old if r['name'] not in selected_names]+results,ensure_ascii=False,indent=2)+'\n')
sys.exit(1 if any(r['exit_code'] for r in results) else 0)
