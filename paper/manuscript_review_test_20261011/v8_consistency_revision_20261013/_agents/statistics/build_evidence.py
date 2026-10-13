from pathlib import Path
import json,hashlib,zipfile
from decimal import Decimal,ROUND_HALF_UP
from lxml import etree
W=Path('/Users/channtang/Downloads/paper');D=W/'manuscript_review_test_20261011/v8_consistency_revision_20261013';O=D/'_agents/statistics';B={x['id']:x for x in json.loads((D/'_source/blocks.json').read_text())}
root=Path('/Users/channtang/Downloads');wanted={'risk_grid_v7.json','extra_checks_v7.py','execution_status_v7.json','statistical_counts_v7.csv','complete_v7_records.py'}
files={n:[] for n in wanted}
for p in root.rglob('*'):
 if p.name in wanted and p.is_file():files[p.name].append(str(p))
zip_audit=[]
for p in root.rglob('*.zip'):
 if '/paper/' not in str(p) and p.parent!=root:continue
 with zipfile.ZipFile(p) as z:
  match=[n for n in z.namelist() if Path(n).name in wanted]
  zip_audit.append({'path':str(p),'entries':len(z.namelist()),'target_matches':match})
risk=[]
for i,row in enumerate(B['B1024']['rows'][1:],1):
 _,corpus,param,base,lost,pct,f1,passed=row
 rate=Decimal(lost)/Decimal(base)*100
 shown=rate.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
 risk.append({'data_row':i,'corpus':corpus,'parameters':param,'base_tp':int(base),'lost_tp':int(lost),'computed_percent':str(shown)+'%','shown_percent':pct,'arithmetic_matches':shown==Decimal(pct.strip('%')),'aggregate_f1':f1,'eligibility':passed,'eligibility_matches_threshold':(rate<=5)==(passed=='是')})
cost=[]
for i,row in enumerate(B['B0750']['rows'][1:],1):
 _,corpus,method,g,p,s,solve,p95,total,totalp95,timeout=row
 sumdisplay=sum(map(Decimal,[g,p,s,solve]));delta=Decimal(total)-sumdisplay
 cost.append({'data_row':i,'corpus':corpus,'method':method,'generation':g,'proposal':p,'scoring':s,'solver_mean':solve,'solver_p95':p95,'listed_total_mean':total,'listed_total_p95':totalp95,'sum_of_rounded_means':str(sumdisplay),'listed_minus_sum':str(delta),'compatible_with_rounding':abs(delta)<=Decimal('.025'),'BR_O_attribution':'unresolved; no separate stage field'})
p6=W/'manuscript_review_test_20261011/protocol_identity_audit_20261012_v6/论文规范排版稿_v6.docx';N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(p6) as z:r=etree.fromstring(z.read('word/document.xml'))
body=r.find('w:body',N);oldcost=None;oldrisk=None;oldpara=None
for i,e in enumerate(body):
 text=''.join(e.xpath('.//w:t/text()',namespaces=N))
 if text.startswith('降低κR至0.5仍使v0开发原TP损失达到41%'):oldpara=text
 if text.startswith('表4-12') or text.startswith('表D-1'):
  j=i+1
  while body[j].tag!='{'+N['w']+'}tbl':j+=1
  rows=[[''.join(c.xpath('.//w:t/text()',namespaces=N)) for c in row.findall('w:tc',N)] for row in body[j].findall('w:tr',N)]
  if text.startswith('表4-12'):oldcost=rows
  else:oldrisk=rows
out={'scope':'v8统计/成本定向来源核对；只读，未执行模型/主实验/新统计生成','source':{'path':str(root/'论文规范排版稿_v7.docx'),'sha256':hashlib.sha256((root/'论文规范排版稿_v7.docx').read_bytes()).hexdigest(),'risk_table_block':'B1024','risk_prose_block':'B0774','cost_table_block':'B0750','cost_prose_block':'B0751'},'search':{'root':str(root),'target_files':files,'zip_audit':zip_audit,'v7_original_grid_obtained':any(files['risk_grid_v7.json']) or any(any(Path(n).name=='risk_grid_v7.json' for n in x['target_matches']) for x in zip_audit),'negative_result_scope':'未在本次Downloads文件名查找和所列ZIP成员目录中定位；不代表外部位置不存在'},'risk_arithmetic':risk,'risk_summary':{'all_12_percentages_correct':all(x['arithmetic_matches'] for x in risk),'all_12_eligibility_decisions_match_5_percent':all(x['eligibility_matches_threshold'] for x in risk),'CDCP_kappa1_delta_results_identical':False,'same_aggregate_f1_in_eligible_delta_grids':{'AAEC_kappa1':'76.90','CDCP_kappa0.5':'57.72'},'same_relation_sets_verified':False,'recommended_sync':'保留表D-1数值，以其列示值同步正文，修改说明披露未取得v7原始网格。'},'cost_arithmetic':cost,'cost_summary':{'no_numeric_change_recommended':True,'BR_O_in_I1_solver_column_verified':False,'reason':'表内求解为聚合列；无本版逐文档分阶段计时输入，均值或列和不能唯一识别BR-O是否已计入。','do_not_add_solver_means':{'AAEC':'0.68','CDCP':'1.11'},'p95_recomputed':False},'historical_v6':{'path':str(p6),'sha256':hashlib.sha256(p6.read_bytes()).hexdigest(),'old_prose':oldpara,'old_risk_table':oldrisk,'old_cost_table':oldcost,'old_prose_exactly_equals_v7_B0774':oldpara==B['B0774']['text'],'solver_mean_and_p95_all_12_rows_unchanged':all(oldcost[i+1][5:7]==B['B0750']['rows'][i+1][6:8] for i in range(12))},'independent_package_excluded':{'path':str(W/'thesis_experiments_20261013_v1.zip'),'evidence':['thesis_experiments/README.md:3-7,17','thesis_experiments/validation/summary.json:37-43'],'reason':'基于v6的独立实现及0.5B单训练样本诊断；不是v7主结果/开发网格，且该包推理接口仍为BR-O前共同起点。'}}
(O/'evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
patch=[]
def add(id,new,reason):patch.append({'block_id':id,'op':'replace_text','old_text':B[id]['text'],'new_text':new,'reason':reason,'source_evidence':[{'path':str(D/'_source/blocks.json'),'block_ids':['B1024','B0575'] if id in ['B0774','B1025'] else ['B0750','B0303','B0751']},{'path':str(O/'evidence.json'),'section':'risk_arithmetic and historical_v6' if id in ['B0774','B1025'] else 'cost_arithmetic and cost_summary'}]})
add('B0774','降低κR至0.5仍使旧版弱评分条件v0的开发原TP损失达到41%，因此保留不修正回退。当前主评分条件的列示结果见表D-1：CDCP在κR=1、δ=0.20时误删25条原有正确关系，原TP为135条，损失率18.52%，未满足5%的限制；κR=0.5时误删为0/135。AAEC在κR=1时误删为3/607，损失率0.49%。CDCP的κR=1条件随δ变化而呈现不同的损失率和F1；合格的AAEC κR=1与CDCP κR=0.5两组在所列δ网格上的汇总关系F1分别保持76.90和57.72，按预定平局规则选择δ=0.20。汇总值相同不意味着逐对象输出完全一致；旧版v0与当前主评分条件分别报告。','以本稿表D-1列示值同步旧段落，保留弱评分v0身份；δ平局仅用于有依据的合格条件，不宣称获得原始开发网格。')
add('B1025','表D-1中，CDCP的κR=1在全部δ条件下均未满足5%的原TP损失限制，κR=0.5则全部合格；AAEC的κR=1亦全部合格。参数选择保持相同的5%限制，先在合格条件中最大化汇总关系F1，再按4.3.1节的平局规则选择δ=0.20。开发F1由三个种子的计数汇总后计算，主测试分数则为逐种子F1均值。此处原TP以相应I0终态G0为参照，须在相同开发文档、种子和预测身份下比较。','与联合网格和本轮追加流程统一，避免把表格列示顺序写成已经核实的执行先后；保持开发汇总与测试均值口径区别。')
add('B0751','在本文追加流程中，I1与Regenerate均以相应I0终态G0为起点，采用相同的两次追加文本处理预算，累计输入上限8192、输出上限2048 token；这些是资源上限，不是逐文档实际消耗恒等式。P/S共享一次冻结文本编码，MLP和候选规则成本分别归入提案、评分；Regenerate在追加预算内返回两份完整图并重排序。完整推理成本应分别登记生成与重排序、共同合法化、BR-O及追加提案、评分和求解，共享部分只计一次，拒绝或回退仍保留已耗成本。表4-12保留既有汇总值，但未单列BR-O，现有汇总也缺少可核对其归属的逐文档阶段字段，因而不能确认I1求解列是否已包含BR-O；不据此反推或补加该阶段时延。','追加流程必须保留BR-O前置成本，但当前聚合字段不能判断已计入或漏计；保留所有原有时延与P95，补充阶段归属及证据边界。')
(O/'patches.json').write_text(json.dumps({'source_sha256':out['source']['sha256'],'patches':patch,'table_values_changed':False,'models_executed':False},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'risk_rows':len(risk),'risk_all_correct':out['risk_summary']['all_12_percentages_correct'],'original_grid_obtained':out['search']['v7_original_grid_obtained'],'zip_count':len(zip_audit),'old_prose_exact_match':out['historical_v6']['old_prose_exactly_equals_v7_B0774'],'cost_solver_columns_unchanged':out['historical_v6']['solver_mean_and_p95_all_12_rows_unchanged'],'patches':len(patch)},ensure_ascii=False))
