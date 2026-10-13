"""Build a human-readable record directly from the frozen real outputs."""
from pathlib import Path
import json, hashlib, csv, io
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
REPORT=WORK/'1011_v7_Luna真实预测与联合修正尝试记录.md'
CASES=WORK/'1011_v7_Luna逐例标注与修正轨迹.md'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pct(v):return f'{100*v:.2f}'
def esc(v):return str(v).replace('|','\\|').replace('\n','<br>')
def ck(c):return (c['start'],c['end'],c['type'])
def rk(r,cs):return (tuple(sorted(ck(cs[c]) for c in r['sources'])),ck(cs[r['target']]),r['type'])
def table(head,rows):return '\n'.join(['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(esc(v) for v in row)+'|' for row in rows])
def link(label,p):return f'[{label}]({p})'
def create(p,text):
    if p.exists():raise FileExistsError(p)
    p.write_text(text)

def main():
    m=read(ROOT/'results/evaluation_001/metrics.json');audit=read(ROOT/'results/evaluation_001/audit.json');assert audit['status']=='PASS'
    docs=read(ROOT/'candidate_pools.json')['documents'];dm={d['id']:d for d in docs};gs={g['id']:g for c in ['aaec','cdcp'] for g in read(ROOT/'evaluation'/f'{c}_gold.json')['documents']}
    protocol=read(ROOT/'protocol.json');freeze=read(ROOT/'results/run_001/input_freeze.json')
    assert sha(WORK/'report_1010_v7_full.md')==protocol['manuscript']['sha256']
    assert sha(WORK/'report_1010_v7_full.docx')=='168531e234421afcf7f09f2f4c07a1e5cba0ee042435f43d643e142a8fc7cb99'
    for p,h in freeze['hashes'].items():assert sha(ROOT/p)==h
    replay=sorted((ROOT/'results').glob('replay_*.json'))[-1];assert read(replay)['status']=='PASS'
    dispatch=[]
    for task,when,prompt,ids in [
        ('luna_predict_aaec','2026-10-10T15:59:53.154537Z','predict_aaec.txt',[d['id'] for d in docs if d['corpus']=='aaec']),
        ('luna_predict_cdcp','2026-10-10T16:00:10.018006Z','predict_cdcp.txt',[d['id'] for d in docs if d['corpus']=='cdcp']),
        ('luna_score_aaec_a','2026-10-10T16:05:35.684116Z','score_aaec_a.txt',[d['id'] for d in docs[:4]]),
        ('luna_score_aaec_b','2026-10-10T16:05:45.813715Z','score_aaec_b.txt',[d['id'] for d in docs[4:8]]),
        ('luna_score_cdcp','2026-10-10T16:05:55.537404Z','score_cdcp.txt',[d['id'] for d in docs[8:]])]:
        dispatch.append({'task':task,'dispatched_at_utc':when,'model_override':'gpt-5.6-luna','reasoning_effort':'low','fork_turns':'none','prompt_file':'prompts/'+prompt,'prompt_sha256':sha(ROOT/'prompts'/prompt),'documents':ids})
    create(ROOT/'model_dispatch_manifest.json',json.dumps({'calls':dispatch,'status':'completed','scope':'5 agent tasks, underlying API-call and token counts not exposed','prompt_archive':'Exact dispatched user-visible task messages saved after execution; scoring_instructions.md existed before scoring calls.','blinding':'Instructional input restriction with no inherited conversation; shared filesystem is not OS isolation; child file-access trace not independently verified.'},ensure_ascii=False,indent=2)+'\n')
    summaryrows=[];riskrows=[];covrows=[];costrows=[];docrows=[]
    for c in ['aaec','cdcp']:
        a=m['aggregate'][c]
        for name in ['MCR-only','RelationOnly','BRJ-lite']:
            x=a['metrics'][name]
            summaryrows.append([c.upper(),name,pct(x['C']['F1']),f"{x['C']['TP']}/{x['C']['FP']}/{x['C']['FN']}",pct(x['R']['F1']),f"{x['R']['TP']}/{x['R']['FP']}/{x['R']['FN']}"])
        for k in ['C','R']:
            x=a['changes']['BRJ-lite'][k];riskrows.append([c.upper(),'组件' if k=='C' else '完整关系',x['TP_recovered'],x['TP_lost'],x['FP_removed'],x['FP_added']])
        x=a['coverage'];covrows.append([c.upper(),x['C_candidates'],f"{x['C_hits']}/{x['C_gold']}",x['R_candidates'],f"{x['R_hits']}/{x['R_gold']}",f"{x['R_multisource_in_pool']}/{x['R_multisource_gold']}"])
        for name in ['BRJ-lite','RelationOnly']:
            x=m['costs'][c+'__'+name];costrows.append([c.upper(),name,x['attempts'],x['accepts'],x['calls'],f"{x['wall_seconds']:.6f}",f"{x['solver_seconds']:.6f}"])
    for r in m['documents']:
        docrows.append([r['id'],pct(r['metrics']['MCR-only']['C']['F1']),pct(r['metrics']['BRJ-lite']['C']['F1']),pct(r['metrics']['MCR-only']['R']['F1']),pct(r['metrics']['BRJ-lite']['R']['F1']),r['relation_outcome']])
    # Complete casebook: every sampled document, all gold, all component candidates,
    # all relation objects selected in either raw graph or final method, every commit.
    book=['---','experiment_id: AM-LUNA-20261010-001','artifact_type: complete_casebook','date: 2026-10-11','status: ANALYZED','---','', '# v7 Luna真实尝试：16篇逐例标注与修正轨迹','',
          '主记录：'+link('实验条件、汇总结果与解释',REPORT)+'。此处保留全部16篇，顺序按ID排列。字符坐标采用原文从0开始的半开区间 `[start,end)`；金标仅修剪两端空白，标点保留数据集本身的规则。完整关系以带类型端点和整个源集合匹配。',
          '', '候选组件表中的“命中”是输出冻结后对照金标得到的诊断，不曾提供给预测/评分模型。表中的分数是固定启发式置信度。两个原始图的ID已经机械映射到候选池统一ID；未改动其语义对象。', '']
    for r in m['documents']:
        ident=r['id'];d=dm[ident];g=gs[ident];s=read(ROOT/'scores'/f'{ident}.json');br=read(ROOT/'results/run_001'/f'{ident}__BRJ-lite.json');ro=read(ROOT/'results/run_001'/f'{ident}__RelationOnly.json')
        goldC=[(c['char_start'],c['char_end'],c['type']) for c in g['components']];GC=set(goldC);GR={(tuple(sorted(goldC[i] for i in x['sources'])),goldC[x['target']],x['type']) for x in g['relations']}
        book.extend([f'## {ident}','',f"MCR选择 `{br['initial_candidate']}`。完整关系F1：{pct(r['metrics']['MCR-only']['R']['F1'])} → {pct(r['metrics']['BRJ-lite']['R']['F1'])}；组件F1：{pct(r['metrics']['MCR-only']['C']['F1'])} → {pct(r['metrics']['BRJ-lite']['C']['F1'])}。",'',
                     '### 原文','', '\n'.join('> '+line for line in d['text'].splitlines()),'', '### 原始标注','',
                     table(['金标组件ID','字符区间','类型','原文'],[[f'g{i}',f'[{c[0]},{c[1]})',c[2],d['text'][c[0]:c[1]]] for i,c in enumerate(goldC)]),'',
                     table(['金标关系ID','完整源集合','目标','标签'],[[f'gr{i}',','.join('g'+str(j) for j in x['sources']),'g'+str(x['target']),x['type']] for i,x in enumerate(g['relations'])]) if g['relations'] else '原始标注没有正关系。','',
                     '### 固定候选组件与分数','',table(['ID','区间','类型','q_C','来源','严格命中','原文'],[[cid,f"[{c['start']},{c['end']})",c['type'],s['component_scores'][cid],'生成' if c['origin']=='generated' else '句末标点变体','是' if ck(c) in GC else '否',c['quote']] for cid,c in d['components'].items()]),'',
                     '### 原始图、初始图与最终图',''])
        graphs=[(x['candidate_id'],x['components'],x['relations']) for x in d['graphs']]+[('MCR-only',br['initial']['C'],br['initial']['R']),('BRJ-lite',br['final']['C'],br['final']['R']),('RelationOnly',ro['final']['C'],ro['final']['R'])]
        book.append(table(['图','组件ID','关系ID'],[[name,', '.join(C),', '.join(R) or '空'] for name,C,R in graphs]));book.append('')
        selected=sorted({rid for name,C,R in graphs for rid in R})
        book.extend([table(['关系ID','完整源集合','目标','标签','q_R','严格命中'],[[rid,','.join(d['relations'][rid]['sources']),d['relations'][rid]['target'],d['relations'][rid]['type'],s['relation_score_overrides'].get(rid,.05),'是' if rk(d['relations'][rid],d['components']) in GR else '否'] for rid in selected]),'',
                     '### BRJ-lite已提交事务','',table(['尝试索引','动作','删除组件','加入组件','删除关系','加入关系','ΔΦ_C','ΔΦ_R'],[[a['attempt'],a['proposal']['kind'],','.join(a['proposal']['D']) or '空',','.join(a['proposal']['B']) or '空',','.join(sorted(set(a['before']['R'])-set(a['after']['R']))) or '空',','.join(sorted(set(a['after']['R'])-set(a['before']['R']))) or '空',f"{a['delta_phi_C']:.4f}",f"{a['delta_phi_R']:.4f}"] for a in br['attempts'] if a['committed']]) if br['accepted_attempts'] else '没有提交事务。','',
                     f"BRJ-lite停止原因 `{br['stop_reason']}`；累计组件编辑 {br['component_edits_total']}，关系编辑 {br['relation_edits_total']}。所有失败提议、可行但未被批次选中的提议及求解状态见 "+link('完整BRJ-lite轨迹',ROOT/'results/run_001'/f'{ident}__BRJ-lite.json')+'；'+link('RelationOnly轨迹',ROOT/'results/run_001'/f'{ident}__RelationOnly.json')+'。',''])
    create(CASES,'\n'.join(book)+'\n')
    text=f'''---
experiment_id: AM-LUNA-20261010-001
sample_batch: AAEC-CDCP-TRAIN-16-LUNA-V7
date: 2026-10-11
started_local: 2026-10-10T23:59:18+08:00
model_requested: gpt-5.6-luna
reasoning_effort: low
status: ANALYZED
material_state: real_model_outputs_and_real_solver_runs
formal_thesis_replication: false
manuscript_version: report_1010_v7_full
tags: [argument-mining, real-data-pilot, AAEC, CDCP, BRJ, negative-results]
---

# v7：Luna真实预测与联合修正尝试记录

## 1. 这次实际完成了什么

本轮从真实AAEC和CDCP训练侧材料各固定8篇，以用户指定的 `gpt-5.6-luna`、`low` 推理强度生成每篇2个候选图，再用同型号的新上下文任务盲评候选对象，实际运行依赖闭合联合修正及固定组件的RelationOnly对照。共16篇、32个生成图、32次修正运行；没有按结果换样本，没有用金标扰动生成“预测”，没有补写模拟F1。论文v7的Markdown和Word保持原样。

这次结果不一致：AAEC组件严格F1提高，关系只恢复2条，同时新增58条错误关系；CDCP丢失了唯一一条初始正确关系。它提供了能复算的初步案例和失败证据，尚不能证明论文完整方法有效，也不能直接替换v7的主实验表。

材料状态为 **EXECUTED → ANALYZED**：输入、模型输出、对象分、求解轨迹及标注核对均已保存。原始档案与冻结输出哈希检查通过，32条运行轨迹的合法性、分项门、事务外不变性和预算检查通过，冻结分数重放32次得到相同最终图及接受索引。此处核验的是这次轻量实现与记录，未完成训练侧、神经评分器、正式测试集或同目标全局对照的实证验证。

## 2. 数据来源、选择和信息边界

AAEC来源为 [TU Darmstadt Argument Annotated Essays 2.0记录](https://tudatalib.ulb.tu-darmstadt.de/handle/tudatalib/2422)，本地压缩包此前经固定提交的 [pie-datasets镜像](https://github.com/ArneBinder/pie-datasets/tree/83fb46f904b13f335b6da3cce2fc7004d802ce4e/data/datasets/ArgumentAnnotatedEssays-2.0)取得。CDCP为 [作者提供的语料压缩包](https://facultystaff.richmond.edu/~jpark/data/cdcp_acl17.zip)，对应 [ACL 2017论文](https://aclanthology.org/P17-1091/)。本轮核实来源并复用工作区已有的原始压缩包，重新检查ZIP完整性和先前来源哈希；没有声称重新下载成功。原始站点/下载接口本轮存在403、ZIP读取能力或网络解析限制，AAEC原站与镜像逐字节相同仍未得到独立确认。

{table(['本地原始文件','字节数','SHA-256'],[[Path(x['path']).name,x['bytes'],x['sha256']] for x in protocol['data_sources']])}

实际读取AAEC划分文件得到TRAIN 322篇；CDCP压缩包TRAIN 581篇，沿用已记录的00411排除规则后580篇。本次这16篇均来自训练侧，未使用官方测试集。AAEC的322与v7参考配置的320不同，因此不能称为按v7既定划分完成的正式实验。

样本从既有按源文本哈希分组、种子920的训练侧审计分区中选取：按词元长度分为4层，每层按预定文本哈希排序取2篇。选择发生在Luna预测之前，与本次预测、修正或准确率无关。既有审计分区曾用于早期CPU诊断，这也不是新保留的独立测试集。具体ID、层号、文本哈希见 {link('sample_manifest.json',ROOT/'sample_manifest.json')}。

预测任务只分配原文；评分任务只分配原文与固定候选对象，不显示初始图成员身份，不分配标注、论文或评估结果。5个模型任务都使用 `fork_turns=none`，不继承本聊天上下文。该隔离由任务输入与指令约束实现；子任务共享文件系统，未建立操作系统级沙箱，也未独立核验每次子任务文件访问。公开语料是否曾进入基础模型预训练无法确认。金标在数据准备阶段被读取并另存，未用于选取难度或修正；**输出冻结后**，主评估流程才读取所选文档的标注并计算准确率。

## 3. 模型与实现：和v7对应到哪一步

5个模型任务分为生成2个、评分3个；这不是底层API调用次数统计。每篇的g0、g1来自同一任务回答，不能当作两个独立随机种子。工具未暴露具体模型快照、采样种子、temperature、输入输出token和费用，记录为未知；未虚构这些字段。全部提示与分配表见 {link('model_dispatch_manifest.json',ROOT/'model_dispatch_manifest.json')} 和 `prompts/`。生成/评分分配提示为调用原文归档，文件归档时间晚于调用；共用评分指令文件在评分前已经存在。

|环节|本次实际执行|与v7完整实现的差异|
|---|---|---|
|初始生成|Luna生成精确原文引文、类型和完整关系，每篇2图|未微调Qwen/LoRA；组件与关系在一次回答中输出，未拆成两个独立模型阶段|
|候选组件|生成对象并集＋一次句末标点去除变体，共210个|没有训练跨度头，没有每跨度全类型展开，也没有完整±1边界/合并拆分补充|
|关系候选|兼容组件的全部二元槽位；保留模型给出的完整多源槽位及其边界变体；每槽保留全部标签，共5404个|未穷举全部2/3源组合；无4096槽位截断发生。保留原生多源格式不等于覆盖到了真实多源关系|
|对象评分|新上下文Luna固定评分，210个组件显式分；149条关系有覆写，其余5255条取事先规定的0.05|同型号启发式置信度，既未训练MLP，也未校准；不能解释为精确正确概率或误差独立证据|
|MCR|0.4覆盖＋0.4语义连贯＋0.2合法性，关系验证用q≥0.5，同分按生成槽位|16篇均选择g0，因此本轮没有显示重排序优于第一候选的证据|
|BRJ-lite|5种组件形态＋纯关系；冲突闭合；全部接触关系重求解；CDCP最小合法化扩域；事务外关系不变|是v7核心接受机制的轻量适配，不是全部候选生成和训练系统复现|
|RelationOnly|同初始图、候选、分数、预算，仅允许纯关系事务|仅完成这一项受控对照，未完成单对象、分步、全局ILP或外部系统对照|

固定计数效用为 `Φ_C=Σ(2q_C−1)`、`Φ_R=Σ(2q_R−1)`；接受要求 `ΔΦ_C≥0`、`ΔΦ_R≥0`、`ΔΦ_C+ΔΦ_R>0.01`，以及整图合法、预算满足。因q并非校准概率，这只是代理目标，不能把门限通过写成真实F1保证。

每事务最多3个组件编辑；累计组件24、关系96；每轮32次尝试、3次接受，最多4轮，批长6。单次MILP上限0.25秒，逐文档总求解上限AAEC 3秒、CDCP 5秒，线程1。原生CDCP源连续性以当前选中组件的文档顺序判定；不额外加入无环或树约束。关系补全先最大化效用，再最小化编辑，再确定性解同分；本次139次实际提交均获得唯一最优且最少编辑的证明，没有将超时 incumbent 写成最优解。

运行环境为Python 3.9.6、NumPy 1.26.4、SciPy 1.13.1，实际调用 `scipy.optimize.milp` 的HiGHS后端。HiGHS的独立版本号未由本次接口单独记录；`threads`选项被SciPy作为未公开选项透传，相关警告保留在求解调用日志。候选、分数、参数和核心代码冻结时间为 `{freeze['frozen_at_utc']}`；32次输出冻结于 `{m['output_freeze_at_utc']}`。

## 4. 实际结果

以下均为严格微平均F1，显示范围0—100；计数顺序为TP/FP/FN。组件必须跨度及类型完全匹配；关系必须整个带类型源集合、目标、方向和标签完全匹配。没有改用重叠匹配或拆开多源关系来抬高分数。分母同时保留全部16篇，包括无正关系的文档；单文档TP=FP=FN=0时F1约定为0，另记FP变化。

{table(['语料','方法','组件F1','组件计数','完整关系F1','关系计数'],summaryrows)}

两个原始候选也完整保留：AAEC g0/g1的组件F1为2.41/2.52，关系均为0；CDCP为40.96/34.57、5.71/0。MCR本轮全选g0。表中RelationOnly与BRJ-lite共享这个初始图，不用金标挑“最佳候选”。

相对MCR-only，BRJ-lite的对象变化如下，恢复与损失分开计数：

{table(['语料','对象','恢复TP','损失TP','移除FP','新增FP'],riskrows)}

AAEC并非普遍恢复了关系：8篇中只有2篇关系F1提高，6篇不变；CDCP为1篇下降、7篇不变，没有关系F1改善的文档。CDCP组件F1还在00428、01282两篇下降；不能用关系F1的“未变”描述整图无风险。RelationOnly在AAEC删除全部32条初始错误关系，但因没有恢复真关系，F1仍为0；在CDCP也删除了那1条正确关系。

### 4.1 候选覆盖首先限制了能恢复什么

{table(['语料','组件候选数','金标组件在池内','关系候选数','金标完整关系在池内','金标多源关系在池内'],covrows)}

AAEC的金标组件覆盖只有33/126（26.19%），完整关系3/82（3.66%）；CDCP分别为19/49（38.78%）、1/17（5.88%）。后者的2条金标多源关系均不在池内。这里是**对象是否存在于候选池的覆盖率**，并非计算了受预算和兼容性约束的Oracle最优F1。池外真实对象无法被本次求解器恢复。

AAEC新恢复的30个正确组件中，28个来自句末标点变体，另外2个来自另一生成图中的对象。故组件改善主要受边界规范影响；没有“仅标点规范化”的对照时，不能将这30个恢复全部解释为联合事务的新增研究贡献。低初始分也暴露了Luna本次输出在边界、类型和遗漏方面与数据标注规范不一致。

### 4.2 全部逐文档结果

{table(['文档','初始组件F1','修正组件F1','初始关系F1','修正关系F1','关系结果'],docrows)}

## 5. 按预定规则选出的真实案例

每个语料分别按ID字典序选关系F1改善、下降、不变的首篇；不存在的类别明确留空。原文、金标、所有候选组件、两原始图、最终图和逐次提交详见 {link('16篇逐例标注与修正轨迹',CASES)}。

### 5.1 AAEC essay078：一条关系在端点替换后被恢复

这是AAEC首个改善案例。组件F1从0升至50.00，完整关系F1从0升至10.53，最后关系计数为1 TP、8 FP、9 FN。正确关系是Premise `[1766,1802)` “it may spur its economic development” → Claim `[1511,1587)` “taking environmental consequences seriously can enhance working efficiencies”，标签supports。

初始图采用包含句末句号的c012、c010，两个严格端点都不匹配。尝试62将c010替换为去句号的c009，删除旧端点相关关系并重新选择新关系；尝试83再将c012替换为c011，加入完整新关系r0329（q_R=0.62）。后一次的ΔΦ_C=0.12、ΔΦ_R=0.24，达到事务接受条件。原关系没有按显示ID直接继承。这是实际发生的端点变化与依赖重建案例，但仍同时出现8条最终错误关系，不能只展示恢复的一条。

### 5.2 CDCP 01057：分项门通过，却删掉真实正确关系

这是CDCP唯一关系F1下降案例，33.33降至0。初始r0063是fact `[139,178)` “The check either bounced or it did not.” → policy `[0,138)`，标签reason，完整匹配金标。评分器没有给它覆写分数，所以按事先规定取q_R=0.05，其效用为−0.90。

第0次尝试保持全部组件不变，删除r0063，得到ΔΦ_C=0、ΔΦ_R=+0.90，合法性和预算也通过，于是整笔提交。真实TP从1变0。这不是求解器未遵守接受门，而是错误的评分输入使代理目标奖励了误删。RelationOnly同样丢失这条关系，说明此次负例不依赖组件集合变化。该样本还能提醒后续不要把未覆写分数自动视为可靠负例。

### 5.3 AAEC essay037：组件有改善，关系仍为0

这是AAEC首个关系F1不变案例。组件F1从0升至13.79，关系TP仍为0，最终8条关系全部错误。候选池中只有2/21个正确组件，0/16条完整正确关系；无论如何优化本次固定候选，真实关系都无法恢复。该例支持“先检查候选完整端点覆盖”的诊断顺序，不能作为某种求解器不如另一种求解器的证明。

### 5.4 CDCP 00396：换标签提高分数，但依然是错误关系

这是CDCP首个关系F1不变案例。金标没有正关系，模型却给出一条evidence关系；修正将其替换成reason。两个标签评分分别为0.88和0.94，因此ΔΦ_R=0.12，满足接受门；FP依旧为1，真实关系F1仍为0。“代理效用提高”和“做了修改”均不能单独作为有效恢复的案例标准。

AAEC没有关系F1下降类别、CDCP没有改善类别，因此没有为凑齐正反例而另选样本。唯一实际提交的拆分事务出现在CDCP 00428，组件F1从50.00降到40.00；本次没有提交合并事务。集合动作的存在与合法性已得到执行记录，但尚无集合动作必要性的正向实证。

## 6. 成本、异常和验证

下面是各8篇的本地修正累计时间，单位秒。包括该方法的初始图选择、队列构造、提议检查和求解；**不包括模型生成/评分、读取文件、候选构建和本轮实现开发时间**。两方法分开计时，求解次数计入所有主目标、编辑次目标和唯一性检查调用。不能将这里的毫秒级求解耗时写成整个系统的端到端成本。

{table(['语料','方法','尝试数','提交数','MILP调用','本地修正累计秒','其中求解秒'],costrows)}

32次运行全部正常结束，初始图失败0；本地求解无超时、无无效incumbent。共1632次MILP调用：516次返回最优，1116次不可行；后者包括858次没有满足门限/预算的提议以及258次排除同分替代解的唯一性证明，不能把所有不可行状态当作程序故障。未达到严格接受门的提议正常拒绝，未删除记录。共258项候选事务满足条件，批次最终提交139项，其余未成为该批次最佳项。

执行前6项测试覆盖：小例穷举与MILP一致、同分编辑与字典序、组件获益不能抵销关系损失、CDCP非接触旧超边失效扩域、新合法未选超边不自动入域、固定组件与调度预算、全部评分ID覆盖（其中若干断言合并于同一测试）。原始档案另由独立读取逻辑逐篇核对：AAEC直接读取原T/R标注；CDCP直接展开原生源范围并保留为一条完整超边，16篇全部一致。完整轨迹审核32/32通过。冻结分数重放未进行任何新的模型推理，32/32最终对象及接受索引一致。

模型任务的真实token、费用和服务端推理耗时未暴露，不能补估成实测数值。当前候选只有210个组件、5404条关系，且省略大量完整论文候选；这些耗时不支持关于真实大候选空间、局部对全局优势或线上采用门槛的结论。求解全部成功也不能替代评分质量和真实准确率检查。

## 7. 后续润色论文可以怎样使用

可作为“真实语料上的初步诊断/案例试验”单列，并明确使用Luna及轻量候选与评分配置。建议正文采用如下可核对表述：

> 在AAEC和CDCP训练侧各8篇固定文档上，我们进行了未经任务微调的低强度模型预测及有限候选修正尝试。结果显示，完整端点候选覆盖与固定对象评分直接限制修正效果。AAEC中实际观察到端点边界替换及依赖关系重建，但组件收益主要来自标点边界变体；CDCP中还观察到分项代理效用均不下降而真实正确关系被删除的情况。因此，候选覆盖和对象评分需要先行验证，本次试验不据此宣称完整方法优于既有系统。

这段仅陈述本次执行事实，不与v7已有假设计数混合，也不把训练侧样本称为测试集。若将数值写入论文，需附本次模型、样本ID、严格匹配、候选简化、评分默认值以及正负结果；可用01057作为代理门限边界的真实负例，用078展示依赖重建路径。

下一轮建议先修复生成的标注规范对齐和跨度召回，加入仅标点规范化对照，避免把边界清理收益误归因；再用独立用途的真实候选标注训练/校准评分器，特别检查默认低分遗漏真关系。候选覆盖足够后，再固定协议比较单对象、BRJ和同目标全局求解，以及原生多源恢复。调整提示或阈值应建立新的实验ID，并以新保留文档评价；不在这16篇上调好后复报为本轮独立结果。

本轮未进行训练增强、成对损失训练、训练外神经对象评分、外部系统比较、同目标全局对照、完整两阶段四格；仍不能回答训练创新有效性、集合动作必要性、局部求解采用价值或正式测试成绩。后续是否升级为正式实验需要确定骨干权重、算力、数据划分和训练配置，本轮未擅自补定或运行。

## 8. 记录索引与复算

- {link('全部16篇逐例记录',CASES)}：原文、原始标注、候选、原始两图、修正结果及每次提交。
- {link('协议',ROOT/'protocol.json')}、{link('评分协议',ROOT/'scoring_protocol.json')}、{link('模型任务与提示索引',ROOT/'model_dispatch_manifest.json')}：执行条件和边界。
- {link('原始AAEC预测',ROOT/'raw_predictions/aaec_luna.json')}、{link('原始CDCP预测',ROOT/'raw_predictions/cdcp_luna.json')}：原样保留的模型输出。
- {link('固定候选池',ROOT/'candidate_pools.json')}、{link('输入冻结清单',ROOT/'results/run_001/input_freeze.json')}、{link('输出冻结清单',ROOT/'results/run_001/output_freeze.json')}：完整对象、代码与文件哈希。
- {link('精确指标与成本',ROOT/'results/evaluation_001/metrics.json')}、{link('逐对象恢复及损失',ROOT/'results/evaluation_001/object_changes.json')}、{link('独立审核',ROOT/'results/evaluation_001/audit.json')}、{link('本地重放核验',replay)}。
- {link('联合修正实现',ROOT/'repair.py')}、{link('独立评估与审核实现',ROOT/'evaluate.py')}、{link('复算说明',ROOT/'README.md')}。

原论文Markdown SHA-256：`{sha(WORK/'report_1010_v7_full.md')}`。Word SHA-256：`{sha(WORK/'report_1010_v7_full.docx')}`。均与执行前记录相同。实验ID按10月10日启动时间命名，实际预测和修正跨越上海时间10月10日至11日，未回填为同日完成。
'''
    create(REPORT,text)
    readme=f'''# AM-LUNA-20261010-001 复算说明

主记录：{REPORT.name}；逐例记录：{CASES.name}。原始模型输出、分数和结果不可覆写。

## 环境

原运行：macOS arm64、Python 3.9.6、numpy 1.26.4、scipy 1.13.1。脚本优先查找相邻research_0920/vendor，否则使用当前Python环境已安装的相同依赖。没有重新安装环境。

在解压后的父目录运行：

```sh
python3 research_1010_v7_luna/test_repair.py
python3 research_1010_v7_luna/replay.py
```

replay.py只读冻结候选和分数，不调用模型、不读取金标；核对最终图及接受索引，新增带时间戳的重放记录，不覆盖run_001。浮点库、MILP版本或资源变化可能影响耗时及限时下的结果。原始记录以results/run_001为准。

evaluate.py包含独立的原始标注读取与轨迹审计；已生成results/evaluation_001，默认拒绝覆盖。要重新生成同名评估，在临时副本中移走该评估目录，再运行evaluate.py；不会重跑Luna或修改预测。原生标注审核需要相邻research_0920/data中的aaec_brat.zip、aaec_split.csv、cdcp_acl17.zip。

不要直接重新运行prepare_data.py、graph_core.py或repair.py覆盖既有数据。它们含防覆写检查。prepare_data.py另依赖早期research_0920/run_feasibility.py及来源清单；交付包保留其源码用于追溯，但使用已冻结blind_inputs即可复算本轮，不必重新抽样。

## 文件组织

- blind_inputs：模型收到的16篇原文；raw_predictions：真实生成输出。
- prompts：任务提示原文与评分指令；model_dispatch_manifest.json：模型覆盖与分配。
- candidate_pools.json / scoring_inputs / scores：固定候选及真实模型评分；缺省关系0.05是预先声明的粗略规则。
- evaluation：另存的原始标注与来源；results/run_001：32次修正的完整轨迹及前后冻结清单。
- results/evaluation_001：严格指标、候选覆盖、逐对象恢复/损失、独立核验。
- logs：测试、实际修正、评估和重放终端记录。

ZIP包含本轮材料及核验所需的3个原始数据文件，不包含Python依赖。主记录中的绝对本地链接适合原工作区；移至其他机器后按文件名和上述相对路径打开。包内SHA256SUMS.json核验字节完整性。生成模型的快照、随机种子、temperature和底层token数未知，因此“可重放”指冻结预测与分数后的确定性流程，不保证重新调用Luna会产生相同输出。
'''
    create(ROOT/'README.md',readme)
    print(json.dumps({'report':str(REPORT),'report_chars':len(text),'casebook':str(CASES),'casebook_chars':len('\n'.join(book)),'cases':len(docs)},ensure_ascii=False))

if __name__=='__main__':main()
