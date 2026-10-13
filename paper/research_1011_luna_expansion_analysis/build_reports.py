"""Generate complete descriptive results and source-linked case evidence."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import json,hashlib

ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
m=read(ROOT/'combined_metrics.json');cases=read(ROOT/'case_source_objects.json');rows=m['documents'];agg=m['aggregate'];replay=read(ROOT/'replay_all.json')
stop_record=read(ROOT/'stop_decision.json');diag=read(ROOT/'candidate_score_diagnostics.json')
assert read(ROOT/'integrity_audit.json')['status']=='PASS'
assert replay['all_replay_invariants_passed'] and replay['runs']==2*len(rows)
assert not replay['final_object_differences']
fmt=lambda x:f'{100*x:.2f}'
esc=lambda x:str(x).replace('|','\\|').replace('\n','<br>')
def table(headers,body):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(esc(c) for c in row)+' |' for row in body])
def link(p,label=None):return f'[{label or Path(p).name}]({p})'
def countstr(s):return f"{s['TP']} / {s['FP']} / {s['FN']}"
def cdesc(c):return f"[{c['start']},{c['end']}) {c['type']}：{c['quote']}"
def rdesc(d,r):return ' + '.join(cdesc(d['components'][c]) for c in r['sources'])+' → '+cdesc(d['components'][r['target']])+'；'+r['type']

positive=[r for r in rows if r['relation_outcome']=='improvement']
secondary=[r for r in rows if r['corpus']=='cdcp' and r['run_status']['BRJ-lite']=='completed' and r['metrics']['BRJ-lite']['C']['F1']>=r['metrics']['MCR-only']['C']['F1']-1e-12 and r['metrics']['BRJ-lite']['R']['FP']<r['metrics']['MCR-only']['R']['FP'] and r['metrics']['BRJ-lite']['R']['TP']>=r['metrics']['MCR-only']['R']['TP']]
chosen={r['id'] for r in positive}
chosen.update(i for i in ['cdcp_01057','cdcp_00867','aaec_essay037'] if i in cases)
if secondary:chosen.add(sorted(secondary,key=lambda r:r['id'])[0]['id'])
if 'cdcp_01024' in cases:chosen.add('cdcp_01024')
if 'cdcp_01374' in cases:chosen.add('cdcp_01374')
chosen=sorted(chosen);byid={r['id']:r for r in rows}
book=['# Luna扩样正例与反例核验','',f"日期：2026年10月11日。范围：AAEC {agg['aaec']['documents']}篇、CDCP {agg['cdcp']['documents']}篇，含原16篇。列出全部关系F1改善案例，另保留典型误删、候选缺失、输入失败和误报减少案例。",'',
      '坐标均为原文零起点、左闭右开的Unicode字符区间；原生标注只按既定规则去掉跨度首尾空白。尝试序号采用轨迹JSON中零起点的attempt字段。主指标要求边界、类型、完整源集合、目标和标签全部匹配。分数为Luna启发式置信度；未覆写关系分固定为0.05。案例根据冻结输出评价后选择，不能据此估计总体有效率。','',
      '每篇保留原文、原生金标、候选与分数、初始／最终对象以及完整提交事务。未提交尝试见原始JSON；失败输出计为空预测属于评价约定，不表示算法执行了删除。','']
for ident in chosen:
    row=byid[ident];src=cases[ident];d=src['pool'];g=src['gold'];br=src['runs']['BRJ-lite'];ro=src['runs']['RelationOnly'];root=WORK/src['root'];q=read(root/'scores'/f'{ident}.json')
    book += [f'## {ident}','',f"语料：{row['corpus'].upper()}；波次：{row['wave']}；关系F1结果类别：{row['relation_outcome']}；BRJ运行状态：{br['status']}。",'',
      table(['方法','组件 TP / FP / FN','组件F1 %','关系 TP / FP / FN','关系F1 %'],[[method,countstr(row['metrics'][method]['C']),fmt(row['metrics'][method]['C']['F1']),countstr(row['metrics'][method]['R']),fmt(row['metrics'][method]['R']['F1'])] for method in ['g0','g1','MCR-only','RelationOnly','BRJ-lite']]),'',
      f"候选覆盖：组件 {row['coverage']['C_hits']}/{row['gold_C']}，完整关系 {row['coverage']['R_hits']}/{row['gold_R']}。",'',
      '### 原文','', '```text',d['text'],'```','', '### 原生金标','',
      table(['索引','字符区间','类型','原文'],[[i,f"[{c['char_start']},{c['char_end']})",c['type'],d['text'][c['char_start']:c['char_end']]] for i,c in enumerate(g['components'])]),'',
      table(['源索引集合','目标索引','标签'],[[','.join(map(str,r['sources'])),r['target'],r['type']] for r in g['relations']]) if g['relations'] else '原生金标没有关系。','',
      '### 候选组件与评分','',table(['候选ID','字符区间','类型','来源','分数','原文'],[[cid,f"[{c['start']},{c['end']})",c['type'],c['origin'],q['component_scores'][cid],c['quote']] for cid,c in d['components'].items()]),'']
    if br['status']=='completed':
        book+=['### 初始和最终对象','',f"初始候选：{br['initial_candidate']}。",'',table(['状态','组件ID','关系ID'],[[label,', '.join(state['C']) or '∅',', '.join(state['R']) or '∅'] for label,state in [('初始',br['initial']),('BRJ终态',br['final']),('RelationOnly终态',ro['final'])]]),'',
          '组件变化：'+str(row['changes']['BRJ-lite']['C'])+'；关系变化：'+str(row['changes']['BRJ-lite']['R'])+'。','']
        relids=set(br['initial']['R'])|set(br['final']['R'])|set(ro['final']['R'])
        book += [table(['关系ID','源→目标','标签','分数','初始','BRJ终态','RelationOnly终态'],[[rid,','.join(d['relations'][rid]['sources'])+' → '+d['relations'][rid]['target'],d['relations'][rid]['type'],q['relation_score_overrides'].get(rid,.05),int(rid in br['initial']['R']),int(rid in br['final']['R']),int(rid in ro['final']['R'])] for rid in sorted(relids)]),'','### 已提交事务','',
          table(['尝试序号','动作','删除组件','加入组件','组件效用增量','关系效用增量','终态关系'],[[a['attempt'],a['proposal']['kind'],','.join(a['proposal']['D']) or '∅',','.join(a['proposal']['B']) or '∅',f"{a['delta_phi_C']:.6f}",f"{a['delta_phi_R']:.6f}",','.join(a['after']['R']) or '∅'] for a in br['attempts'] if a['committed']]),'']
        if row['recovered_relations']:
            book+=['### 恢复的完整正确关系','']
            for rr in row['recovered_relations']:
                inraw=[gg['candidate_id'] for gg in d['graphs'] if rr['relation_id'] in gg['relations']]
                book+=[f"- **{rr['relation_id']}**：{rdesc(d,rr['relation'])}。最后进入终态的提交为尝试{rr['last_entry_attempt']}（{rr['proposal']['kind']}）；全部端点来自模型生成候选：{rr['all_endpoints_generated']}；原候选图已包含该完整关系：{', '.join(inraw) if inraw else '均未包含，由有限候选补充形成'}。"]
            book+=['']
    else:
        book+=['### 显式失败','',f"初始选择排名：`{br['ranks']}`。",'',f"解析错误：`{d['parse_errors']}`；图合法性：`{[(gg['candidate_id'],gg['issues']) for gg in d['graphs']]}`。",'',
              '该文档没有修正终态或提交轨迹，仍保留在评价分母；空输出计数不能解释为执行了组件／关系删除。','']
    gold_path=root/'evaluation'/(row['corpus']+'_gold.json')
    book+=['### 来源','',f"{link(root/'results/run_001'/f'{ident}__BRJ-lite.json','BRJ完整轨迹')}；{link(root/'results/run_001'/f'{ident}__RelationOnly.json','RelationOnly完整轨迹')}；{link(root/'scores'/f'{ident}.json','原始评分')}；{link(root/'candidate_pools.json','候选池及g0/g1')}；{link(gold_path,'原生标注')}。",'']
bookpath=WORK/'1011_Luna扩样正例与反例核验.md'
with bookpath.open('x') as f:f.write('\n'.join(book))

roots=[WORK/k for k in m['verified_wave_hashes']];modeltasks=sum(len(read(r/'model_dispatch_manifest.json')['calls']) for r in roots[1:]);ntotal=len(rows);nfail=sum(r['relation_outcome']=='failure' for r in rows)
stop=all(a['positive_ids'] for a in agg.values())
wavebody=[]
for wave,aa in m['by_wave'].items():
    for c,a in aa.items():wavebody.append([wave,c.upper(),a['documents'],a['outcomes'].get('improvement',0),a['outcomes'].get('harm',0),a['outcomes'].get('unchanged',0),a['outcomes'].get('failure',0),fmt(a['metrics']['MCR-only']['R']['F1'])+' → '+fmt(a['metrics']['BRJ-lite']['R']['F1'])])
metricbody=[]
for c,a in agg.items():
    for method in ['MCR-only','RelationOnly','BRJ-lite']:metricbody.append([c.upper(),a['documents'],method,countstr(a['metrics'][method]['C']),fmt(a['metrics'][method]['C']['F1']),countstr(a['metrics'][method]['R']),fmt(a['metrics'][method]['R']['F1'])])
positivebody=[[r['id'],r['wave'],fmt(r['metrics']['MCR-only']['R']['F1']),fmt(r['metrics']['BRJ-lite']['R']['F1']),fmt(r['metrics']['RelationOnly']['R']['F1']),r['changes']['BRJ-lite']['R']['TP_recovered'],r['changes']['BRJ-lite']['R']['TP_lost'],r['changes']['BRJ-lite']['R']['FP_removed'],r['changes']['BRJ-lite']['R']['FP_added']] for r in positive]
report=['# Luna扩样分析与正例核验记录','',f"已完成AAEC {agg['aaec']['documents']}篇、CDCP {agg['cdcp']['documents']}篇，共{ntotal}篇真实文档的分析。新增{ntotal-16}篇使用gpt-5.6-luna / low，原16篇预测、评分与结果按原字节复用。",'',
        f"AAEC有{len(agg['aaec']['positive_ids'])}篇严格关系F1改善，CDCP有{len(agg['cdcp']['positive_ids'])}篇；另有{nfail}篇显式失败，均保留在分母。"+('完成本波全部文档后，两套语料均达到预定的正例发现条件，停止扩样。' if stop else 'CDCP已覆盖预定审计集合的全部116个唯一文本，仍未发现严格关系F1改善案例，按停止规则结束扩样。'),'',
        f"CDCP另有{len(secondary)}篇满足补充条件：关系FP减少、TP不减少且组件F1不下降。它们可以作为局部误报抑制案例；这项事后描述不等同于主指标提升，也不用于改变扩样停止规则。",'',
        '## Material Passport','',
        '- Origin Skill: academic-research-suite / experiment-agent','- Origin Mode: run','- Origin Date: 2026-10-11','- Verification Status: VERIFIED recount; all replayed final states matched; six commit-path differences retained','- Version Label: Luna expanded case discovery','',
        '## 抽样与执行范围','',
        '先按用户确认扩为各32篇。样本沿用原训练侧审计集合，按原文token长度四分位分层，各层沿固定SHA256排序从2篇扩至8篇，新增每套语料24篇。之后仅对仍无严格关系F1正例的CDCP，每层再取4篇，每波最多16篇；波内全部运行完成再决定是否继续。可用上限为AAEC 64个唯一文本、CDCP 116个唯一文本。扩展顺序在新增预测前保存，不依据单篇结果重抽。', '',
        '这是一项按结果决定是否继续的探索性案例搜索。各波、负结果和失败均公开；文档来自训练侧而非独立测试集，且与早期182篇CPU审计数据嵌套。不能将找到的案例比例作为总体有效率，也不据此做显著性或泛化推断。','',
        f'本次新增{modeltasks}项Luna模型任务，包含预测与独立上下文评分；“任务数”不等于底层API调用次数。模型快照、采样温度、随机种子和token消耗未暴露。预测与评分任务不继承父对话，仅获指定原文／候选输入；文件白名单属于指令约束，共享文件系统并非操作系统隔离，子任务实际文件访问未作独立审计。','',
        '各文档生成g0、g1两个候选图，允许相同；它们来自一次回答，不是两个独立样本。候选构建、0.05缺省关系评分、修正核心、预算和接受条件延续原试验。组件评分全覆盖，关系采用显式覆写；评分并非校准概率，也不是论文中的训练评分器。','',
        table(['波次','语料','本波文档','改善','下降','不变','失败','关系F1 % 初始→BRJ'],wavebody),'',
        '## 全部样本的严格计数','',
        'F1按全部文档的TP、FP、FN汇总后计算，表中为百分数。原生跨度仅去除首尾空白，关系要求所有源组件、目标、类型、字符边界和标签同时正确。金标与预测均无关系时，本实现将关系F1定义为0，须另看FP和空集合匹配。失败方法没有返回图，按空输出计数，全部金标留作FN；这种评价约定不代表执行了删除。MCR列仍对其选择的原始图计数，并保留不合法标志。','',
        table(['语料','文档数','方法','组件 TP/FP/FN','组件F1 %','关系 TP/FP/FN','关系F1 %'],metricbody),'',
        '这些结果描述轻量流程在固定候选和启发式评分下的表现，不替代完整BR-J、训练侧增强、四格实验或全局求解比较。个别恢复成功与整批预测质量必须分开判断。','',
        '## 全部严格关系F1正例','',
        table(['文档','波次','初始F1 %','BRJ F1 %','RelationOnly F1 %','恢复TP','损失TP','移除FP','新增FP'],positivebody) if positive else '未发现严格关系F1改善案例。','',
        f"AAEC全部正例：{', '.join(agg['aaec']['positive_ids']) or '无'}。CDCP全部正例：{', '.join(agg['cdcp']['positive_ids']) or '无'}。",'',
        f'原文、原生金标、候选分数、初始和最终对象、具体事务详见{link(bookpath,"正例与反例核验册")}。以下解释只涉及实际发生的变化。','']
if 'aaec_essay001' in byid:
    report+=['AAEC essay001在MCR选择g1后缺失目标Claim和一个前提；尝试1先补入目标Claim，尝试7再插入该前提并重建受影响关系，恢复“人际交往技能将使孩子终身受益”对“合作能培养未来所需人际技能”的supports关系。关系F1从0升到12.50，RelationOnly仍为0。两个端点均来自Luna原始生成，g0本已含该正确关系，因此该例也暴露MCR初选会丢失已有正确对象。终态仍有9条FP和5条FN，不能只报告恢复。','']
if 'aaec_essay051' in byid:
    report+=['AAEC essay051通过尝试19插入缺失前提，恢复“多数图书馆设施可长期使用”对“投资图书馆有长期效果”的supports关系。两个端点来自生成候选；完整关系由有限候选补充形成，原g0、g1均未直接包含。关系F1从0升到8.00，RelationOnly仍为0。它比单纯去掉句末标点更适合说明组件增补与关系重建的实际路径，但不证明联合事务优于单对象或分步策略。','']
for r in positive:
    if r['corpus']!='cdcp':continue
    report+=[f"CDCP {r['id'].split('_',1)[1]}：初始关系计数{countstr(r['metrics']['MCR-only']['R'])}，BRJ终态{countstr(r['metrics']['BRJ-lite']['R'])}，严格关系F1由{fmt(r['metrics']['MCR-only']['R']['F1'])}升到{fmt(r['metrics']['BRJ-lite']['R']['F1'])}；RelationOnly为{fmt(r['metrics']['RelationOnly']['R']['F1'])}。恢复{r['changes']['BRJ-lite']['R']['TP_recovered']}条TP，损失{r['changes']['BRJ-lite']['R']['TP_lost']}条TP，移除{r['changes']['BRJ-lite']['R']['FP_removed']}条FP，新增{r['changes']['BRJ-lite']['R']['FP_added']}条FP。",'']
report+=['## 误报减少与负例','',
         '误报减少可以构成局部帮助，但当TP仍为0时，严格关系F1可能仍为0；不能把这类变化改名为F1提升。下表是评价后的补充描述，不参与预定的扩样停止条件。','',
         table(['CDCP文档','初始关系 TP/FP/FN','终态关系 TP/FP/FN','组件F1 % 初始→终态'],[[r['id'],countstr(r['metrics']['MCR-only']['R']),countstr(r['metrics']['BRJ-lite']['R']),fmt(r['metrics']['MCR-only']['C']['F1'])+' → '+fmt(r['metrics']['BRJ-lite']['C']['F1'])] for r in secondary]),'',
         '本次新增的CDCP 00312可作为局部受益案例：原生金标无关系，初始图多预测一条reason关系r0113；尝试22删除该边后，关系FP由1降到0，关系集合与空金标一致。组件未改变，组件F1保持50.00，RelationOnly也得到相同结果。该例能够说明减少误报，但没有恢复任何TP，不是严格关系F1提升，也不是联合策略独有的收益。','',
         'CDCP 01024是可直接解释的局部受益案例：原生标注没有关系，初始图却预测了两条reason关系。轨迹尝试0和12分别删除r0011、r0055（均为0.05缺省评分），关系FP由2降到0，关系集合与空金标一致。组件未改变且组件F1仍为0，RelationOnly得到相同终态，因此它支持“抑制关系误报”，不支持“恢复正确关系”或“联合策略独有优势”。该例来自原16篇，已按原字节复用，不能写成本次新增发现。','',
         'CDCP 01374也保留在核验册中：移除3条原有错误关系，同时加入1条错误关系，FP净减少2条（3→1），TP仍为0、FN仍为4。RelationOnly与BRJ终态相同；仅用“删掉两条错误边”概括会掩盖新增错误边，故保留完整事务。','',
         '原CDCP 01057的唯一正确关系仍因0.05缺省分被删除，关系F1从33.33降到0，RelationOnly出现相同损失。扩样没有覆盖或重算这项不利结果。对失败文档另存原始解析错误、候选合法性和MCR排名，完整列入下表。','',
         table(['失败文档','波次','原因'],[[r['id'],r['wave'],cases[r['id']]['pool']['parse_errors'] or [(g['candidate_id'],g['issues']) for g in cases[r['id']]['pool']['graphs'] if g['issues']]] for r in rows if r['relation_outcome']=='failure']),'',
         '## 候选覆盖与可解释边界','',
         table(['语料','金标组件','候选命中组件','金标关系','候选命中完整关系','多前提关系金标／候选命中'],[[c.upper(),a['coverage']['C_gold'],a['coverage']['C_hits'],a['coverage']['R_gold'],a['coverage']['R_hits'],str(a['coverage']['R_multisource_gold'])+' / '+str(a['coverage']['R_multisource_in_pool'])] for c,a in agg.items()]),'',
         f"BRJ恢复组件的来源计数：`{m['recovered_component_origins']}`。该来源分解不能替代仅标点规范化、单对象、分步或全局对照。",'',
         table(['语料','候选中完整正确关系','其中缺省0.05评分','评分高于0.5','高分但文档运行失败','最终保留'],[[c.upper(),d['candidate_gold_relation_hits'],d['default_score_hits'],d['above_half_hits'],d['high_score_hits_on_failed_documents'],d['final_retained_hits']] for c,d in diag['summary'].items()]),'',
         f"这项评分诊断在结果冻结后进行，仅作描述；没有用金标回填分数或重跑选例。完整分数、端点是否进入初始／终态及失败状态见{link(ROOT/'candidate_score_diagnostics.json','候选与评分诊断')}。候选已包含金标关系也不保证端点可被现有评分和预算选入。",'',
         '扩样可以增加案例覆盖，但不能补足原始文本边界、类型和完整关系未进入候选池的问题；也不能证明同型号评分器已校准。CDCP中还出现非连续多源关系、重叠组件或非法类型，均以实际失败保留。候选、评分及结构检查的诊断应先于“扩大规模就能证明有效”的结论。','',
         '## 复核与复用','',
         f"全部{ntotal}篇已从冻结对象独立复算；{2*ntotal}个文档策略运行已完成一次完整诊断重放，终态对象／显式失败全部一致，提交路径有{len(replay['commit_path_differences'])}组不同。所有完成运行的重放轨迹通过结构、预算和接受条件复核；不能据此声称路径完全确定。新旧输入、评分、程序和原输出哈希均核对，原v9论文保持不变。重放不再次调用Luna，只验证冻结分数后的本地流程。",'',
         f"提交路径差异涉及：{', '.join(x['id']+' / '+x['method'] for x in replay['commit_path_differences'])}。首次逐路径比较在essay317中止的记录也保留，没有选择一次通过的重放覆盖它。现有代码中存在集合遍历的浮点累加及未取整的效用并列排序，可能影响近似同分候选选择，但尚未做隔离实验确认单一原因；详见{link(ROOT/'replay_path_differences.json','重放路径差异')}和{link(ROOT/'replay_attempt_history.json','重放检查历史')}。",'',
         f"{link(ROOT/'combined_metrics.json','完整逐篇指标及分波汇总')}；{link(ROOT/'case_source_objects.json','案例原始对象')}；{link(ROOT/'replay_all.json','逐运行重放核验')}。",'',
         f"{link(ROOT/'integrity_audit.json','抽样与核心代码完整性核验')}；{link(ROOT/'stop_decision.json','扩样停止依据')}。原始协议保留旧试验的8篇字段，部分合并文件保留原三批次说明；本次真实任务数和文档数以各波sample_manifest、model_dispatch_manifest及逐篇结果为准。另有第4波解析失败处理的本地改动，仅用于保留非法类型输出并按失败计入分母，未修改修正核心或补造预测。",'',
         '各波原始材料：','']
for root in roots:report.append(f"- {root.name}：{link(root/'protocol.json','协议')}，{link(root/'sample_manifest.json','抽样')}，{link(root/'model_dispatch_manifest.json','模型任务')}，{link(root/'results/run_001/output_freeze.json','输出冻结')}，{link(root/'results/evaluation_001/metrics.json','评价')}。")
report+=['','论文后续修订可优先使用essay051说明生成候选中的前提补入与完整关系恢复，保留essay001的MCR选择问题及CDCP01057负例。CDCP可使用新增00312说明误报抑制，须按该实际变化命名。任何严格正例都需并列其余FP、FN及RelationOnly结果；当前试验仍不能替代完整主比较。','','## 全部文档结果','','结果列仅表示关系F1的变化；unchanged不表示组件或图结构没有变化。','',
         table(['文档','波次','初始组件F1 %','BRJ组件F1 %','初始关系F1 %','BRJ关系F1 %','RelationOnly关系F1 %','关系F1结果'],[[r['id'],r['wave'],fmt(r['metrics']['MCR-only']['C']['F1']),fmt(r['metrics']['BRJ-lite']['C']['F1']),fmt(r['metrics']['MCR-only']['R']['F1']),fmt(r['metrics']['BRJ-lite']['R']['F1']),fmt(r['metrics']['RelationOnly']['R']['F1']),r['relation_outcome']] for r in rows]),'']
reportpath=WORK/'1011_Luna扩样分析与正例核验记录.md'
with reportpath.open('x') as f:f.write('\n'.join(report))
write(ROOT/'report_manifest.json',{'files':{str(p.relative_to(WORK)):sha(p) for p in [reportpath,bookpath]},'cases_in_book':chosen,'positive_ids':[r['id'] for r in positive],'secondary_FP_reduction_ids':[r['id'] for r in secondary],'all_documents_listed':len(rows),'new_model_tasks':modeltasks})
print(json.dumps({'report':str(reportpath),'casebook':str(bookpath),'documents':len(rows),'positive_ids':[r['id'] for r in positive],'selected_cases':chosen},ensure_ascii=False,indent=2))
