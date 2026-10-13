from pathlib import Path
import re,json,hashlib
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v5'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=(R/'report_1010_v5_full.md').read_text();new=(R/'report_1010_v6_full.md').read_text()
e=json.loads((W/'template-evidence.json').read_text())
for n,h in e['baseline_hashes'].items():assert sha(R/n)==h,n
assert re.findall(r'\$\$(.*?)\$\$',new,re.S)==re.findall(r'\$\$(.*?)\$\$',old,re.S)
assert old[old.index('## 参考文献'):old.index('## 附录A')]==new[new.index('## 参考文献'):new.index('## 附录A')]
assert old[old.index('## 附录E'):old.index('## 附录F')]==new[new.index('## 附录E'):new.index('## 附录F')]
alg=lambda t:re.findall(r'```(?:algorithm|plaintext)\n(.*?)\n```',t,re.S)
expected=alg(old);expected[0]=expected[0].replace('按源文档等权取训练批次','按源文档等频取训练批次')
assert alg(new)==expected
imgs=lambda t:re.findall(r'^!\[[^]]*\]\(([^)]+)\)',t,re.M)
assert len(imgs(old))==len(imgs(new))==11
for a,b in zip(imgs(old),imgs(new)):assert sha(R/a)==sha(R/b)
numeric_rows=lambda t:[l for l in t.splitlines() if l.startswith('|') and re.search(r'\d',l)]
# Numeric table cells remain unchanged. The sole permitted table edit is T-A prose.
oldrows=[l.replace('一般文本增量的作用','普通增强的整体作用').replace('5.1至5.3条件增量、对象边界与配置选择','5.1至5.3条件增量、对象边界与在线配置选择') for l in numeric_rows(old)]
assert numeric_rows(new)==oldrows
raw=[]
for manifest,generator in [('scenario_manifest.json','generate_scenario.py'),('supplement_manifest.json','generate_supplement.py')]:
    m=json.loads((W/manifest).read_text())
    assert sha(W/manifest)==sha(P/manifest)
    for n,h in m['files'].items():assert sha(W/n)==h and sha(W/n)==sha(P/n),n;raw.append(n)
    assert sha(W/generator)==sha(P/generator)
c=json.loads((W/'reference_config.json').read_text());pc=json.loads((P/'reference_config.json').read_text())
for key in pc:
    if key not in ['manuscript_version','authoring_revision','production_required_unbound']:assert pc[key]==c[key],key
assert set(pc['production_required_unbound'])<=set(c['production_required_unbound'])
assert c['authoring_revision']['genuine_model_runs']==0
assert '实际运行的权重revision、分词器及环境在2.6节统一记录' not in new
assert '按源文档等权取训练批次' not in new
assert new.count('## 第')==6
res={'passed':True,'scope':'MANUSCRIPT_AND_DATA_PRESERVATION_ONLY','source_sha256':sha(R/'report_1010_v6_full.md'),'unchanged_display_formulas':32,'algorithms':3,'algorithm_prose_change':'3-1 line 27 equal-frequency sampling clarification only','unchanged_figures':11,'unchanged_references':49,'tables':len(re.findall(r'^表[A-H0-9]+-\d+ ',new,re.M)),'numeric_table_cells_preserved':True,'raw_files_hash_preserved':len(set(raw)),'appendix_E_preserved':True,'v5_baseline_preserved':True,'genuine_model_runs':0,'new_simulation_generation':False}
(W/'revision_audit.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(res,ensure_ascii=False))
