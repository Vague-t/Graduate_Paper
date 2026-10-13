"""Extract source-bound case cards. Never overwrite historical model outputs."""
from common import *
import re,copy
OUT=ROOT/'cases'

def cell(x):return str(x).replace('|','\\|').replace('\n',' ')
def table(heads,rows):return '|'+'|'.join(heads)+'|\n|'+'|'.join(':---' for _ in heads)+'|\n'+'\n'.join('|'+'|'.join(cell(x) for x in row)+'|' for row in rows)+'\n\n'
def semantic_relation(r,cs):return (tuple(sorted(ckey(cs[c]) for c in r['sources'])),ckey(cs[r['target']]),r['type'])
def old_gold(root,ident):
 corpus=ident.split('_')[0];v=read(root/'evaluation'/f'{corpus}_gold.json')['documents'];g=next(x for x in v if x['id']==ident)
 cs={f'g{i:03d}':{'start':c['char_start'],'end':c['char_end'],'type':c['type'],'quote':g['text'][c['char_start']:c['char_end']]} for i,c in enumerate(g['components'])}
 rs={f'gr{i:03d}':{'sources':[f'g{x:03d}' for x in r['sources']],'target':f'g{r["target"]:03d}','type':r['type']} for i,r in enumerate(g['relations'])}
 return {'id':ident,'text':g['text'],'components':cs,'relations':rs,'gold_C':list(cs),'gold_R':list(rs)}
def gold_sets(g):return {ckey(c) for c in g['components'].values()},{semantic_relation(r,g['components']) for r in g['relations'].values()}
def actual_counts(d,state,g):
 gc,gr=gold_sets(g);return {'C':counts([ckey(d['components'][c]) for c in state['C']],gc),'R':counts([semantic_relation(d['relations'][r],d['components']) for r in state['R']],gr)}
def relations_view(d,ids,q=None):
 out=[]
 for ident in ids:
  r=d['relations'][ident];ss=[{'id':c,**d['components'][c]} for c in r['sources']];t={'id':r['target'],**d['components'][r['target']]};v={'id':ident,'sources':ss,'target':t,'type':r['type']}
  if q is not None:
   if 'R' in q:v.update(q=q['R'].get(ident),score_origin='explicit')
   else:v.update(q=q['relation_score_overrides'].get(ident,q['default_relation_score']),score_origin='explicit' if ident in q['relation_score_overrides'] else 'historical_default_not_explicit')
  out.append(v)
 return out

def main():
 OUT.mkdir(exist_ok=True);cards=[];native={d['id']:d for d in load_jsonl(ROOT/'data/native_documents.jsonl')};used_files=set()
 drift=read(WORK/'research_1011_v11/drift/evaluation/source_gold.json')['documents'];judgments=read(WORK/'research_1011_v11/drift/analysis/metrics.json')['component_judgments'];variants={}
 for p in (WORK/'research_1011_v11/drift_generate/raw').glob('*.json'):
  used_files.add(p)
  for d in read(p)['documents']:variants[d['id']]=d['variants']
 descriptions={
  'aaec_essay002':('保持身份论据的改写与对应','原文把保持个人身份与联系原籍、传授原有价值联系起来。组件ID和原生类型保持，原始坐标随回填迁移；下表只展示已有改写，并不表示目标生成器已经训练。'),
  'cdcp_00377':('个人催收经历不能直接改成一般事实','原文的常见姓氏和多年来误接催收电话是作者的个人经历，原生标注为testimony。用更简洁的句子重述经历，可以改变措辞而保留该任务中的角色。'),
  'cdcp_00423':('obligation改为debt产生的审核分歧','fluent改写将obligation写成debt。既有两路模型都提出范围收窄问题，但全文本就在债务语境内，因此这里保留为模型识别的疑似变化，不将其升级为人工确认的错误。v13规则演示中，组件含义待定即拒绝该视图；这与仅屏蔽不确定关系的情形不同。')}
 for ident in ['aaec_essay002','cdcp_00377','cdcp_00423']:
  d=next(x for x in drift if x['id']==ident);title,analysis=descriptions[ident];rows=[]
  for i in d['editable_component_ids']:
   c=d['components'][i];cid=f'c{i:03d}';v={x['variant_id']:x['replacements'][cid] for x in variants[ident]}
   rows.append({'component':cid,'type':c['type'],'start':c['char_start'],'end':c['char_end'],'original':d['text'][c['char_start']:c['char_end']],'concise':v['concise'],'fluent':v['fluent']})
  cards.append({'case_id':'K'+str(len(cards)+1).zfill(2),'source_doc_id':ident,'title':title,'evidence_type':'ACTUAL_OLD_LUNA_PARAPHRASE_PLUS_V13_RULE_ILLUSTRATION','text':d['text'],'text_sha256':d['text_sha256'],'components':rows,'gold_relations':[r for r in d['relations'] if set(r['sources']+[r['target']])&set(d['editable_component_ids'])],'component_judgments':[x for x in judgments if x['id']==ident],'analysis':analysis,'model_training_evidence':False})
 # Four genuinely executed historical repair examples.
 descriptions={
  'aaec_essay001':('端点恢复让一条正确关系进入输出','初始图缺少严格匹配的关键端点。固定组件的RelationOnly没有恢复正确关系，BRJ-lite在恢复组件后命中一条关系；同时新增多条误边。该例说明端点可变性在这次运行中有作用，也说明恢复TP与增加FP可以同时发生。'),
  'aaec_essay078':('修正边界后仍须检查误边','既有边界候选使部分组件重新匹配金标，最终恢复一条关系；关系精确率仍低。历史方法使用稀疏评分与默认0.05，不能把它当作v13完整评分策略的成功验收。'),
  'aaec_essay037':('组件有所恢复但正确关系仍未入池','候选池没有任何严格正确的完整关系。局部修改能够恢复部分组件，但无法从当前池中选出不存在的正确关系。关系F1仍为零，不能归咎于求解范围太小。'),
  'cdcp_01057':('默认缺分与高分错误对象导致误改','初始图唯一命中的关系在修正后丢失。对照下列评分来源，可以区分显式模型低分与历史默认0.05；未评分对象被当作低分会使已有正确结构受到错误删除压力。v13将此类必要评分缺失改为保护相关事务，不对历史结果改写。')}
 for ident in ['aaec_essay001','aaec_essay078','aaec_essay037','cdcp_01057']:
  root=WORK/('research_1011_luna_expanded' if ident=='aaec_essay001' else 'research_1010_v7_luna');p=root/'candidate_pools.json';used_files.add(p)
  d=next(x for x in read(p)['documents'] if x['id']==ident);g=old_gold(root,ident);gc,gr=gold_sets(g);q=read(root/'scores'/f'{ident}.json');rp=root/'results/run_001'/f'{ident}__BRJ-lite.json';op=root/'results/run_001'/f'{ident}__RelationOnly.json';used_files|={rp,op,root/'scores'/f'{ident}.json'}
  run=read(rp);ro=read(op);states={'MCR-only':run['initial'],'RelationOnly':ro['final'],'BRJ-lite':run['final']};ct={k:actual_counts(d,s,g) for k,s in states.items()}
  reported=next(x for x in read(root/'results/evaluation_001/metrics.json')['documents'] if x['id']==ident)
  for k,v in ct.items():
   for axis in ['C','R']:assert v[axis]==[reported['metrics'][k][axis][x] for x in ['TP','FP','FN']],(ident,k,axis)
  bef=set(run['initial']['R']);aft=set(run['final']['R']);important=[]
  for tag,items in [('recovered_TP',[r for r in sorted(aft-bef) if semantic_relation(d['relations'][r],d['components']) in gr]),('lost_TP',[r for r in sorted(bef-aft) if semantic_relation(d['relations'][r],d['components']) in gr]),('added_FP',[r for r in sorted(aft-bef) if semantic_relation(d['relations'][r],d['components']) not in gr])]:
   for r in items[:2]:important.append({'change':tag,**relations_view(d,[r],q)[0]})
  if not important:
   important=[{'change':'gold_not_in_candidate_pool',**relations_view(g,g['gold_R'][:1])[0]}]
  title,analysis=descriptions[ident]
  cards.append({'case_id':'K'+str(len(cards)+1).zfill(2),'source_doc_id':ident,'title':title,'evidence_type':'ACTUAL_HISTORICAL_LUNA_OUTPUT_AND_SOLVER','text':d['text'],'text_sha256':hash_text(d['text']),'pool':d,'gold':g,'scores':q,'states':states,'counts':ct,'selected_relations':important,'coverage':reported['coverage'],'accepted_attempts':run['accepted_attempts'],'analysis':analysis,'source_files':[str(x.relative_to(WORK)) for x in [rp,op,p,root/'scores'/f'{ident}.json']]})
 # A real multi-premise annotation and actually executed constructed-score example.
 d=native['cdcp_00662'];r=next(x for x in d['gold_R'] if len(d['relations'][x]['sources'])==2);mech=read(ROOT/'mechanism/summary.json');fx=next(x for x in read(ROOT/'mechanism/inputs.json')['fixtures'] if x['id']=='native_cdcp_collective_split')
 cards.append({'case_id':'K08','source_doc_id':d['id'],'title':'完整联合源与集合拆分','evidence_type':'NATIVE_GOLD_PLUS_ACTUAL_SOLVER_ON_CONSTRUCTED_SCORES','text':d['text'],'text_sha256':d['text_sha256'],'gold_relation':relations_view(d,[r])[0],'fixture':fx,'runs':[x for x in mech['records'] if x['fixture'] in ['native_cdcp_collective_split','native_cdcp_score_failure','native_cdcp_missing_score']],'analysis':'原标注把“偏好邮件”和“不能确定邮件已送达”作为共同来源，支持“未确认收件就打电话”的建议。严格评价按整个源集合匹配，单独一个来源不是同一金标对象，也不据此断言它在语义上毫无支持。构造初始图把两段合成一个组件；单独换回一段无法通过组件效用门，而两段一起替换能够通过。这里只验证给定输入和分数下的程序行为。'})
 # Existing CasiMedicos dense-score evidence, no new prompts or retuning.
 ca=WORK/'research_1011_v12/casimedicos';goldall=read(WORK/'research_1011_v10/new_corpora/evaluation/casimedicos_gold.json')['documents'];qd=read(ca/'validated_scores.json');pools=read(ca/'candidate_pools.json')['documents']
 for ident in ['casimedicos_318_140','casimedicos_309_215']:
  d=next(x for x in pools if x['id']==ident);gg=next(x for x in goldall if x['id']==ident);cs={f'g{i:03d}':{'start':c['char_start'],'end':c['char_end'],'type':c['type'],'quote':gg['text'][c['char_start']:c['char_end']]} for i,c in enumerate(gg['components'])};rs={f'gr{i:03d}':{'sources':[f'g{x:03d}' for x in r['sources']],'target':f'g{r["target"]:03d}','type':r['type']} for i,r in enumerate(gg['relations'])};g={'components':cs,'relations':rs,'gold_C':list(cs),'gold_R':list(rs)};gc,gr=gold_sets(g)
  ip=next((ca/'results').glob(f'{ident}__0.50__component*json'));bp=ca/'results'/f'{ident}__0.50__BRJ-lite.json';states={'new_initial':read(ip)['final'],'BRJ-lite':read(bp)['final']};ct={k:actual_counts(d,s,g) for k,s in states.items()}
  output=states['new_initial']['R'];right=[r for r in output if semantic_relation(d['relations'][r],d['components']) in gr];wrong=[r for r in output if r not in right];chosen=right[:2]+wrong[:1]
  for p in [ip,bp,ca/'candidate_pools.json',ca/'validated_scores.json']:used_files.add(p)
  cards.append({'case_id':'K'+str(len(cards)+1).zfill(2),'source_doc_id':ident,'title':'少量命中与大量误选' if ident.endswith('318_140') else '候选与评分仍未转成正确输出','evidence_type':'ACTUAL_V12_LUNA_DENSE_SCORES_AND_SOLVER','text':d['text'],'text_sha256':hash_text(d['text']),'pool':d,'gold':g,'scores':qd[ident],'states':states,'counts':ct,'selected_relations':[{'change':'selected_TP' if r in right else 'selected_FP',**relations_view(d,[r],qd[ident])[0]} for r in chosen],'analysis':'阈值0.50及候选池在评分前冻结，BRJ-lite没有在新初始化上增加命中。这里解释数据集中已有论辩标注的抽取结果，不评价医学诊疗本身。原文、分数和输出全部来自既存文件；不把本批调试文档当作独立泛化测试。','source_files':[str(p.relative_to(WORK)) for p in [ip,bp]]})
 # Source-linked four-cell examples from the SAME main scenario graph records.
 universe={d['id']:d for d in load_jsonl(ROOT/'simulation/object_universes.jsonl')};four={}
 for row in load_jsonl(ROOT/'simulation/prediction_graphs.jsonl'):
  if row['seed']==17 and row['method'] in ['t0_i0','t1_i0','t0_i1','t1_i1']:four.setdefault(row['id'],{})[row['method']]=row
 groups={'training_only':[],'repair_only':[],'both':[],'combined_only':[],'baseline_lost':[]}
 for ident in sorted(four):
  d=universe[ident];gr=set(d['gold_R']);a,b,c,e=[set(four[ident][m]['R'])&gr for m in ['t0_i0','t1_i0','t0_i1','t1_i1']]
  sets={'training_only':(b-a)-(c-a),'repair_only':(c-a)-(b-a),'both':(b-a)&(c-a),'combined_only':e-(a|b|c),'baseline_lost':a-e}
  for name,items in sets.items():
   for r in sorted(items):groups[name].append((ident,r))
 quad=[]
 for name,items in groups.items():
  if not items:continue
  ident,r=items[0];d=universe[ident];obj=d['relations'][r];states=four[ident];details={}
  for m,s in states.items():
   selected=set(s['C']);details[m]={'C':s['C'],'R':s['R'],'relation_selected':r in s['R'],'gold_endpoints_selected':all(x in selected for x in obj['sources']+[obj['target']]),'missing_gold_endpoints':[x for x in obj['sources']+[obj['target']] if x not in selected]}
  quad.append({'category':name,'available_examples_in_seed17':len(items),'id':ident,'relation':relations_view(d,[r])[0],'seed':17,'states':details,'evidence_type':'CONSTRUCTED_FOUR_CELL_OUTPUT_ON_REAL_TEXT','selection':'lexicographic first complete object in this outcome category; illustrative, not representative'})
 # Source-linked illustrative masks: assumptions, not additional model judgments.
 d=next(x for x in drift if x['id']=='aaec_essay002');ctx=d['components'][9]
 cards[0]['mask_illustration']={'evidence_type':'CONSTRUCTED_VERIFIER_STATES_ON_REAL_RELATIONS','readonly_target':{'id':'c009','start':ctx['char_start'],'end':ctx['char_end'],'type':ctx['type'],'quote':d['text'][ctx['char_start']:ctx['char_end']]},'assumed_all_component_checks':'pass','factors':[{'sources':['c008'],'target':'c007','native_label':'supports','position':'internal','assumed_review':'stable','mask':1},{'sources':['c007'],'target':'c009','native_label':'supports','position':'boundary','assumed_review':'uncertain','mask':0}],'default_action':'keep component supervision and stable internal factor; mask boundary factor','full_filter_action':'reject this view; original gold and generation target retained'}
 used_files|={WORK/'research_1011_v11/drift/evaluation/source_gold.json',WORK/'research_1011_v11/drift/analysis/metrics.json',WORK/'research_1011_v10/new_corpora/evaluation/casimedicos_gold.json'}
 for rootname,corpora in [('research_1010_v7_luna',['aaec','cdcp']),('research_1011_luna_expanded',['aaec'])]:
  used_files.add(WORK/rootname/'results/evaluation_001/metrics.json')
  for corpus in corpora:used_files.add(WORK/rootname/'evaluation'/f'{corpus}_gold.json')
 dump(OUT/'case_records.json',{'cases':cards,'four_cell_cases':quad,'source_hashes':{str(p.relative_to(WORK)):sha(p) for p in sorted(used_files)},'new_Luna_calls':0,'human_adjudication':False,'selection':'existing case IDs chosen for distinct mechanisms; all negative outcomes retained','main_simulation_graph_sha256':sha(ROOT/'simulation/prediction_graphs.jsonl')})
 # Human-readable casebook, all original spans preserved.
 text='# v13真实语料案例与机制解释\n\n本册包含真实原文与金标、既有Luna实际输出，以及明确标记的构造预测或评分。它们用于解释不同层次的问题，不合并为目标模型的实测成绩。文档ID和半开字符坐标用于定位；中文说明是解释，不替代原始英文跨度。\n\n'
 index=[]
 for c in cards:
  index.append([c['case_id'],c['source_doc_id'],c['title'],c['evidence_type']])
 text+=table(['编号','原文ID','问题','证据类别'],index)
 for c in cards:
  text+=f"## {c['case_id']} {c['title']}\n\n原文：`{c['source_doc_id']}`；证据类别：`{c['evidence_type']}`。\n\n{c['analysis']}\n\n"
  if 'components' in c:
   text+=table(['组件与类型','原文及坐标','简洁改写','流畅改写'],[[x['component']+' / '+x['type'],f"[{x['start']},{x['end']}) "+x['original'],x['concise'],x['fluent']] for x in c['components']])
   text+='这些改写由既有Luna任务实际生成。v13的因素掩码和目标训练结果不由这些句子直接推出。\n\n'
  if 'mask_illustration' in c:
   z=c['mask_illustration'];v=z['readonly_target']
   text+=f"只读目标c009 [{v['start']},{v['end']}) / {v['type']}：{v['quote']}。原生金标含c008→c007及c007→c009两条supports，前者在改写集合内部，后者跨向只读目标。\n\n"
   text+='以下审核状态为**构造的规则演示**，不是对既有Luna判断的重标。假设三个端点的组件检查均通过，内部关系判为保持，跨边界关系仍待定：\n\n'
   text+=table(['真实金标因素','位置','假设审核状态','变体关系掩码'],[['c008→c007 / supports','内部','保持','1'],['c007→c009 / supports','跨边界','待定','0']])
   text+='默认掩码接纳视图的有效组件及内部关系，跨边界关系不参与变体头监督和对齐，也不改标NONE；完整筛选则拒绝该视图。两个版本都保留原文完整金标与生成监督。若任一组件含义变化或待定，则两个版本均拒绝整例，不沿用此处的部分保留分支。\n\n'
  if 'counts' in c:
   text+=table(['配置','组件TP/FP/FN','组件F1','关系TP/FP/FN','关系F1'],[[m,'/'.join(map(str,z['C'])),f"{float(f1(z['C'])):.2f}",'/'.join(map(str,z['R'])),f"{float(f1(z['R'])):.2f}"] for m,z in c['counts'].items()])
   text+='代表性完整关系：\n\n'
   for j,r in enumerate(c['selected_relations'],1):
    text+=f"{j}. `{r['change']}`，标签 `{r['type']}`"
    if 'q' in r:text+=f"，使用分数 {r['q']:.2f}（`{r['score_origin']}`）"
    text+='。\n\n'
    for k,v in enumerate(r['sources'],1):text+=f"   来源{k} [{v['start']},{v['end']}) / {v['type']}：{v['quote']}\n\n"
    v=r['target'];text+=f"   目标 [{v['start']},{v['end']}) / {v['type']}：{v['quote']}\n\n"
   text+='完整前后图、全部候选及具体对象分数保存在配套 `case_records.json`，此处摘录并不替代整篇计数。\n\n'
  if 'gold_relation' in c:
   r=c['gold_relation'];text+=table(['角色','原生类型','原文'],[[f'源{i+1}',x['type'],x['quote']] for i,x in enumerate(r['sources'])]+[['目标',r['target']['type'],r['target']['quote']]])
   text+=table(['构造输入条件','算法','关系F1','结果含义'],[[x['fixture'],x['mode'],f"{x['R_F1']:.2f}",'给定分数下实际求解'] for x in c['runs']])
   text+='在集合拆分情景，合并组件q=0.84，两个正确源各q=0.74；单独替换使组件效用从0.68降为0.48，两者一起替换则升为0.96。错误合并组件q提高至0.99且两个正确源各降为0.60时，组件门阻止替换，扩大求解范围也不恢复金标。评分缺失情景保留初始状态。这些分数是构造输入，不能当作Luna实测。\n\n'
 text+='## 同一主情景中的四格对象案例\n\n以下对象直接来自生成主表的种子17记录。原文与金标真实，四格预测为构造情景；按每类字典序首个对象选例，不据此估计真实发生比例。\n\n'
 for q in quad:
  r=q['relation'];text+=f"### {q['category']} {q['id']}\n\n同类对象数：{q['available_examples_in_seed17']}。标签：`{r['type']}`。\n\n"
  text+=table(['角色','类型','原文'],[[f'源{i+1}',x['type'],x['quote']] for i,x in enumerate(r['sources'])]+[['目标',r['target']['type'],r['target']['quote']]])
  text+=table(['配置','完整端点均选中','关系输出','缺失端点'],[[m,str(x['gold_endpoints_selected']),str(x['relation_selected']),','.join(x['missing_gold_endpoints']) or '无'] for m,x in q['states'].items()])
  if all(x['gold_endpoints_selected'] for x in q['states'].values()):text+='该例四个配置均具备正确端点，差别发生在关系选择层；不能将其解释为组件边界恢复。\n\n'
  else:text+='至少一个配置缺少完整正确端点；先补齐端点才可能输出这一严格关系。各状态可直接从记录检查，不将模拟转变解释为已验证的训练因果机制。\n\n'
 (WORK/'1011_v13真实语料案例册.md').write_text(text)
 dump(OUT/'summary.json',{'case_cards':len(cards),'four_cell_case_cards':len(quad),'case_ids':[{'case_id':c['case_id'],'source_doc_id':c['source_doc_id'],'title':c['title'],'evidence_type':c['evidence_type']} for c in cards],'casebook_sha256':sha(WORK/'1011_v13真实语料案例册.md'),'case_records_sha256':sha(OUT/'case_records.json'),'actual_new_model_calls':0})
 print(json.dumps({'cards':len(cards),'four_cell':len(quad),'casebook_chars':len(text)},ensure_ascii=False))
if __name__=='__main__':main()
