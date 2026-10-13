"""Package the completed preview and auditable evidence without altering old runs."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,zipfile
W=Path(__file__).resolve().parent;R=W.parent;E=R/'research_1011_v11'
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
audit=read(W/'final_audit.json');visual=read(W/'visual_review.json')
assert audit['mechanical_checks']=='PASS' and audit['visual_review']=='PASS'
assert audit['pdf_sha256']==visual['pdf_sha256'] and audit['pages']==visual['pages']
md=R/'report_1011_v11_full.md';word=R/'report_1011_v11_full.docx';pdf=R/'report_1011_v11_full.pdf'
assert sha(md)==audit['source_sha256'] and sha(word)==audit['docx_sha256']
shutil.copyfile(W/'render_release/report_1011_v11_full.pdf',pdf)
assert sha(pdf)==audit['pdf_sha256']
readme=R/'1011_v11证据包说明.md'
readme.write_text(f'''# 1011 v11 完整预览与证据包

日期：2026年10月11日。论文共{audit['pages']}页，保留旧v10，新增12张表。先阅读 report_1011_v11_full.pdf 或可编辑Word，再阅读易懂版／详细版说明。

## 四种证据身份

- 真实模型输出：30项新 gpt-5.6-luna / low 任务，包括64个改写、筛选与分离上下文复核、24篇成分抽取。两路判断同型号，未作独立人工裁决；精确部署快照、采样温度及API token数不可得。
- 真实求解：复用v10的96篇固定输入，CDCP有两种评分，128个文档/评分条件×4策略×3预算，共1536条日志。初始化失败留在分母。96个候选层与1536条求解计数有第二实现复算。
- 模拟：主训练结果、OOF、匿名外部比较、四格对象和正／零／负效应；均有标识、种子及整数记录，目标Qwen训练次数为0。
- 成本推测：实际候选规模或宽松组合上界，乘以明确吞吐／存储假设。槽位构造实测不含模型生成与评分，不能当完整系统成本。

## 阅读与检查入口

论文、三份说明、研究记录与文档QA均由 1011_v11交付清单.json 绑定SHA256。解压至独立目录，运行 `python3 verify_1011_v11_bundle.py` 可只读核验所有包内文件；此检查不调用模型、不写文件。

research_1011_v11/protocol.json 与 pre_model_freeze.json 为任务前冻结信息；model_execution_manifest.json 为完成后清单。drift 保存原/新标签判断与筛选，candidate 保存四层候选与覆盖，solver 保存每次求解，simulation 保存全部新增模拟和成本假设。

research_1011_v11/independent_recount.py 是独立计数复算入口；evaluate_drift.py、evaluate_solver.py 和 candidate_probe.py 的 evaluate 模式是对应评价入口。它们可能重写汇总，需在副本中运行。prepare.py、prepare_judges.py 与构造／求解入口使用排他写入，不能在归档目录上重跑；重新调用模型必须建新批次并重新登记身份，不能覆盖原始输出。

实际求解环境记录于 solver/results/run_001；本机使用Python 3、NumPy 1.26.4、SciPy 1.13.1与HiGHS。包不复制二进制依赖、模型权重或GPU环境。重新求解的时间、同分解和求解器行为可能变化，须保留新运行记录。DOCX渲染使用Codex捆绑Python、LibreOffice与中文字体；文档脚本保留本机运行路径，跨机器时需改运行位置。

## 包内范围

包含本版所有原始任务输出、指令、输入、金标评价、候选与求解日志、模拟记录、脚本、v10冻结依赖与语料发布文件，以及v7主模拟计数和生成器。旧v10文稿随包用于版本比对。保留的更早正文图表仍属于原版本情景；完整早期实验档案见既有v7/v10证据包，本包没有将所有历史图表重新记为v11实验。

文档QA保留审计JSON、最终页码定位、源码差异和视觉检查记录；137页量级的逐页PNG与临时渲染不进入压缩包，当前工作目录中仍可查阅。

## 本版结论

漂移小试未检出关系标签变化，尚未证实完整筛选的额外收益。分离成分抽取将CasiMedicos严格关系候选覆盖从0/37提高至13/37，但尚未评分或选入终图；ArgUNSC与CDCP仍低。单对象与集合修正聚合相同，小池全局平均更快，故保留简化选择。完整模拟预览不能替代目标模型的真实训练与端到端验证。
''')
files=[md,word,pdf,readme]+list(R.glob('1011_v11*说明_*.md'))+[R/'1011_v11修订落实与后续修改建议.md']
files += [R/f'report_1011_v10_full.{ext}' for ext in ['md','docx','pdf']]
for directory in [E,R/'research_1011_v10']:
 files += [p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
for directory in [W,R/'_revision_1011_v10']:
 files += [p for p in directory.iterdir() if p.is_file() and p.suffix in ['.py','.json','.md','.conf']]
files += [p for p in (R/'_revision_1010_v7').iterdir() if p.is_file() and p.suffix in ['.py','.csv','.json','.md']]
files += [R/'research_1010_v7_luna'/n for n in ['prepare_data.py','evaluate.py','graph_core.py','repair.py']]
files += [R/'research_1011_luna_expanded'/n for n in ['prepare.py','sample_manifest.json']]
files += [R/'research_0920'/n for n in ['run_feasibility.py','data/aaec_brat.zip','data/aaec_split.csv','data/cdcp_acl17.zip','sources/icic_2026_5295.txt','sources/icic_2026_5295.pdf']]
for p in [md,R/'report_1011_v10_full.md']:
 files += [R/n for n in re.findall(r'^!\[[^]]*\]\(([^)]+)\)$',p.read_text(),re.M)]
files=sorted(set(files));assert all(p.is_file() for p in files)
assert len([p for p in files if p.name in ['1011_v11逐项完善说明_易懂版.md','1011_v11逐项完善说明_详细版.md']])==2
manifest={'revision':'1011-v11','created_at_utc':datetime.now(timezone.utc).isoformat(),'pages':audit['pages'],'manuscript_sha256':sha(md),'docx_sha256':sha(word),'pdf_sha256':sha(pdf),'new_model_tasks':30,'new_solver_records':1536,'new_target_training_runs':0,'files':{str(p.relative_to(R)):sha(p) for p in files}}
manifest_path=R/'1011_v11交付清单.json';manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
verifier=R/'verify_1011_v11_bundle.py'
verifier.write_text('''from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
m=json.loads((root/'1011_v11交付清单.json').read_text())
for name,expected in m['files'].items():
    p=root/name
    assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
print('PASS:',len(m['files']),'files; read-only, no model calls')
''')
out=R/'1011_v11完整预览与实验模拟证据包.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files+[manifest_path,verifier]:z.write(p,str(p.relative_to(R)))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for name,h in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==h,name
summary={'status':'PASS','files':len(files),'zip_bytes':out.stat().st_size,'zip_sha256':sha(out),'pages':audit['pages'],'word':str(word),'pdf':str(pdf),'bundle':str(out)}
(R/'1011_v11交付核验.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
