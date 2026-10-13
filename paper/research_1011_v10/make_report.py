"""Create readable experimental report and complete per-document evidence."""
from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parent;R=B.parent
read=lambda p:json.loads(p.read_text())
link=lambda p,label=None:f'[{label or p.name}]({p.resolve()})'
def table(headers,rows):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join([':---']*len(headers))+'|']+['|'+'|'.join(str(x).replace('|','／').replace('\n',' ') for x in row)+'|' for row in rows])
def ccount(m):return '/'.join(str(m[x]) for x in ['TP','FP','FN'])
def fmt(x):return f'{x*100:.2f}'
metrics={name:read(B/name/'results/evaluation_001/metrics.json') for name in ['new_corpora','cdcp_scoring']}
old=read(R/'research_1011_luna_expansion_analysis/combined_metrics.json')
report=['# 1011 v10 新语料实验与方法调整报告','日期：2026年10月11日。对应 report_1011_v10_full，原 v9 与既有实验输出保持不变。实际新执行96篇文档、12项预测任务和31项盲评分任务，均请求 gpt-5.6-luna / low；每篇两张图来自同次回答。修正与对照共256条执行记录，另外256条冻结分数重放记录。任务数量不代表底层API调用数。',
'## 本次结论',
'新增两套可用于原生组件—关系抽取的语料：2025年的ArgUNSC、2024年的CasiMedicos-Arg。本次各固定32篇；另从未用于此前Luna诊断的CDCP训练文档固定32篇，比较原评分与原生定义加显式评分的组合调整。预测、候选、初始图和预算在CDCP两条件间共用，不按结果追加样本。',
'新语料没有出现严格关系F1改善。CDCP 00846出现一个严格正例，关系F1由0升至18.18，但RelationOnly同样恢复；32篇总体上，原生显式BRJ-lite由原评分的0改善至1.60，仍低于共同初始图的3.33。该结果支持改进评分输入，不支持宣布联合修正总体有效。',
'已有AAEC扩样中的essay051和essay001提供非标点恢复案例，保留于正文4.6.7；它们有助于说明补入候选端点如何打开关系恢复空间，但不足以隔离集合动作、共同决策或局部求解的独立贡献。全部负结果与失败仍保留。',
'## 数据检索、来源与适配',
table(['数据集','一手来源','可用对象','本次实际范围'],[
['ArgUNSC (2025)','[论文](https://aclanthology.org/2025.argmining-1.20/)；[作者仓库](https://github.com/mpoiaganova/political-argument-mining)','claim/premise，support/attack，原生二元关系','144篇发布文档→142篇完整转换→120篇满足8000字符限制→固定32篇'],
['CasiMedicos-Arg (2024)','[论文](https://aclanthology.org/2024.emnlp-main.1026/)；[固定数据版本](https://huggingface.co/datasets/HiTZ/casimedicos-arg/tree/54a07ccf2993afc42a368e04682125b6f7b13be4)','Claim/Premise，Support/Attack，原生二元关系','英文官方test 125行→117行有token→93行全部端点可唯一映射→固定32篇'],
['CDCP','[作者发布包](https://facultystaff.richmond.edu/~jpark/data/cdcp_acl17.zip)','五类组件，reason/evidence，完整源集合','官方train；排除前期审计文本，再固定32篇']]),
'ArgUNSC保留发布原句，逐字定位组件，跨句组件仅允许从来源句内开始；两篇重复ID/重叠文档整篇排除。原论文2973条关系与当前快照3009条去重关系存在版本差异；后者由组件表和独立关系对CSV双向校对，不人为对齐论文计数。',
'CasiMedicos按有序token/BIO还原边界，句内单空格、句间换行。关系端点仅作NFKC、空白与末尾标点归一化后的唯一完整匹配，不作语义或编辑距离补配。论文558个标注病例与当前发布553个有token的行不完全一致，故使用快照真实分母。任何端点无法完整映射的文档整篇排除。这是可转换子集研究，不能当成官方完整测试集成绩。',
'CasiMedicos的一般医学知识标为Claim，病例具体观察标为Premise，允许Claim支持Claim；与其他语料名称相同的类型不合并语义。只使用英文，未将同一病例的四种语言重复计算。ArgUNSC作者仓库保存MIT许可，CasiMedicos数据卡保存CC-BY 4.0声明。来源文件、许可和哈希见 '+link(B/'pre_experiment_manifest.json')+'、'+link(B/'datasets/conversion_audit.json')+'。',
'## 冻结协议与真实执行',
'各语料按token长度四分位分层，层内按SHA256(V10-LUNA-FIXED32|语料|原文)取前8篇。全部样本、盲输入、金标快照、提示及代码在预测前冻结。子任务为全新上下文，只允许读取任务指定的原文与候选文件；这是指令层盲化，共享文件系统并非操作系统权限隔离。金标在父任务用于数据转换和抽样，未交给预测/评分任务；评价在执行输出冻结后进行。',
'每8篇一项预测任务，每篇g0/g1构造有限带类型跨度池和句末标点变体；二元槽位按不重叠端点补充，CDCP多源组合仅由生成图及其端点变体提供。未展开所有类型、未用金标补跨度或源组合。新语料多源输出按原生二元格式失败保留，不拆平挽救，也未作格式重试。',
'128次尝试、12次接受、组件/关系24/96次累计编辑，每文档累计5秒MILP、单次至多0.25秒。效用按规范ID顺序求和；评分缺失的守卫覆盖最小合法化扩域后的关系集合。组件/关系评分是模型启发式判断，不是训练评分器或校准概率。模型实际快照、温度、种子、token用量未暴露，未臆填。',
'新实验初始化失败时，MCR和两修正策略均为空预测，完整金标分母保留。旧148篇历史MCR保留原始被选图，即使结构非法，两种协议分开报告。原16篇及132篇扩样没有重算替换。',
'## 全部严格结果',
'F1以百分数表示，按全部文档TP、FP、FN作微平均。组件严格键包含原文字符跨度与类型；完整关系还要求整个源集合、目标、方向和标签全部一致。']
rows=[]
for corpus,a in old['aggregate'].items():
    for method in ['MCR-only','RelationOnly','BRJ-lite']:
        m=a['metrics'][method];rows.append([corpus+' 历史扩样',a['documents'],method,fmt(m['C']['F1']),fmt(m['R']['F1']),ccount(m['C']),ccount(m['R'])])
for name,met in metrics.items():
    for corpus,a in met['aggregate'].items():
        for method,m in a['metrics'].items():
            if method in ['g0','g1']:continue
            rows.append([corpus+' 新固定样本',a['documents'],method,fmt(m['C']['F1']),fmt(m['R']['F1']),ccount(m['C']),ccount(m['R'])])
report.append(table(['语料与协议','篇数','方法','组件F1','关系F1','组件TP/FP/FN','关系TP/FP/FN'],rows))
report.extend(['历史扩样采用探索性找例停止规则，不能估计总体提升概率。历史与新增共244篇唯一Luna样本，但不得跨原生任务、划分和失败口径汇总成一个成绩；也不与先前182篇CPU诊断简单相加。',
'## 候选、格式与评分的限制'])
rows=[]
for name,met in metrics.items():
    for corpus,a in met['aggregate'].items():
        c=a['coverage'];rows.append([corpus,a['documents'],f"{a['parsed_graphs']}/64",f"{a['valid_graphs']}/64",a['initial_failures'],f"{c['C_hits']}/{c['C_gold']}",f"{c['R_hits']}/{c['R_gold']}",f"{c['R_multisource_in_pool']}/{c['R_multisource_gold']}"])
report.append(table(['语料','文档','解析图','结构有效图','初始化失败文档','组件候选覆盖','完整关系候选覆盖','多源关系候选覆盖'],rows))
report.extend(['ArgUNSC的6个图、CasiMedicos的35个图违反二元元数；后者另有3个图违反结构检查。CasiMedicos13篇没有任何可解析图，另外1篇MCR选中非法图，总计14篇初始化失败。它们均进入分母。格式失败与任务质量的区别需要保留，不能把未能进入算法的错误解释成算法删除。',
'在ArgUNSC中，池内4条正确关系全为默认0.05；CasiMedicos池内3条中2条为默认，剩余正确关系也低于0.5。新增CDCP池内5条正确关系在原评分下全为默认0.05；原生显式方案只有1条达到0.5。显式评分所有235个组件与3670条关系均有数字，无null。字段齐备不证明模型进行了可靠的逐对象判断，且没有语料样本实际触发null守卫；守卫行为由单独接口测试支持。',
'前期116篇CDCP还存在74个精确跨度但类型错误的初始组件，包括35个value→fact、14个testimony→fact。由于候选只保留生成时给出的类型，后续关系评分无法补回缺失的原生类型。新32篇的8条完整多源金标关系均不在池中，评分调整同样无法解决。',
'## 小幅方法调整与论文理据',
table(['调整','已实施范围','现有证据','不能声称'],[
['原生任务注册','新两套二元语料；CDCP保留联合源范围','原始标注及独立转换复核','不同语料同名类型可直接共享语义'],
['CDCP原生定义 + 显式对象分数','固定候选和共同MCR的32篇配对比较','BRJ-lite 0→1.60；00846恢复1条reason','单独识别提示定义或输出覆盖各自作用；总体优于初始图'],
['未知评分拒绝','变化组件及事务闭合域关系有null则拒绝','6项接口检查通过；本批null为0','守卫在本批已经造成真实任务提升'],
['规范ID求和','固定phi浮点累加顺序','新256条执行记录重放终态、接受序列均一致','模型重采样稳定性或整体方法可重复性已证明']]),
'保留两阶段主框架、固定效用、依赖闭合、接受门及预算。将动机收紧为“候选可达、评分有区分力时检验端点修正”，避免将合法提交与金标提升等同。没有新增第三项算法创新，没有用本批金标调阈值或挑选重试。',
'## CDCP 00846：有用但有限的正例',
'完整原文及对象见下方逐例核验册。关键原文为“消费者未必知道债权人及其联系方式”，目标为“通知应列明债权人的地址和电话”。原生金标是fact [126,229) → policy [0,125) 的reason。端点已在初始图中；关系r0067由有限槽位补充，原生成图并未直接给出这条正确关系。',
'原评分q(r0067)=0.05，原生显式q=0.75；BRJ-lite第0次尝试为关系提议，D=B=∅，ΔφC=0、ΔφR=0.50，加入r0067。最终组件集合不变，关系计数由0/3/7变为1/3/6，F1从0到18.18。RelationOnly终态相同；不能把这一例归为集合组件修正收益。另两个文档00334、00710原有正确关系均未保住，解释了总体仍低于MCR。',
'## 正文落实与核验入口',
'正文4.6.7重新组织为历史扩样、新语料及CDCP配对对照，新增表4-9至4-11；D.10—D.12登记协议、转换、覆盖、成本和回放。摘要、第一章、4.7、第五章对象讨论、第六章、A/C/H同步更新。原模拟主比较仍保留明确身份，正式训练与全局比较未被标记完成。',
'全部计数经第二套不导入主评价器的对象复算通过；96篇金标还从发布CSV、BIO/JSONL或CDCP原压缩包独立核对。256条重放终态与接受序列全部一致。真实MILP时间仅覆盖修正阶段，未包含模型预测评分、候选准备或端到端延迟，不能用来宣称速度优势。',
'指标文件：'+ '；'.join(link(B/n/'results/evaluation_001/metrics.json',n) for n in metrics)+'。完整逐篇原文、金标、图和接受轨迹：'+link(B/'casebook.md')+'；机器可读对象：'+link(B/'case_source_objects.json')+'。历史正反例：'+link(R/'1011_Luna扩样正例与反例核验.md')+'。'])
allobjects=[];book=['# 1011 v10 全部96篇逐例核验册','所有文档按实验目录和ID排序，包含失败。坐标为当前冻结原文的零基半开字符区间；CasiMedicos为规定的token重建文本。金标不参与预测和分数生成。本册只将冻结材料并列呈现。']
for name,met in metrics.items():
    root=B/name;pool={d['id']:d for d in read(root/'candidate_pools.json')['documents']};gold={d['id']:d for p in (root/'evaluation').glob('*_gold.json') for d in read(p)['documents']};common=read(root/'results/run_001/common_initial_states.json')
    for row in sorted(met['documents'],key=lambda x:x['id']):
        ident=row['id'];d=pool[ident];g=gold[ident];runs={p.stem.split('__',1)[1]:read(p) for p in sorted((root/'results/run_001').glob(ident+'__*.json'))}
        allobjects.append({'experiment':name,'id':ident,'text':d['text'],'gold':g,'candidate_components':d['components'],'candidate_relations':d['relations'],'raw_parsed_graphs':d['graphs'],'parse_errors':d['parse_errors'],'common_initial':common[ident],'metrics':row,'run_files':{k:str((root/'results/run_001'/f'{ident}__{k}.json').relative_to(B)) for k in runs},'terminal_states':{k:{key:v.get(key) for key in ['status','initial','final','accepted_attempts']} for k,v in runs.items()}})
        book.extend(['## '+name+' / '+ident,'### 原文','\n'.join('> '+line for line in d['text'].splitlines()),'### 金标组件',table(['编号','区间','原生类型','原文'],[[i,f"[{c['char_start']},{c['char_end']})",c['type'],d['text'][c['char_start']:c['char_end']]] for i,c in enumerate(g['components'])]),'### 金标完整关系',table(['源组件集合','目标','标签'],[[','.join(map(str,x['sources'])),x['target'],x['type']] for x in g['relations']]),'### 结果',table(['配置','组件TP/FP/FN','组件F1','关系TP/FP/FN','关系F1'],[[k,ccount(v['C']),fmt(v['C']['F1']),ccount(v['R']),fmt(v['R']['F1'])] for k,v in row['metrics'].items() if k not in ['g0','g1']]),'解析错误：`'+json.dumps(d['parse_errors'],ensure_ascii=False)+'`。共同初选：'+str(row['initial_candidate'])+'；初始化失败：'+str(row['initial_failure'])+'。'])
        for k,v in runs.items():
            book.append('### '+k+' 轨迹')
            book.append(link(root/'results/run_001'/f'{ident}__{k}.json','完整冻结执行记录')+'；status='+v['status'])
            if v['status']=='completed':
                book.append('初始 C='+str(v['initial']['C'])+'；R='+str(v['initial']['R'])+'。终态 C='+str(v['final']['C'])+'；R='+str(v['final']['R'])+'。')
                book.append(table(['尝试索引','动作','D','B','ΔφC','ΔφR','接受后C','接受后R'],[[i,a['proposal']['kind'],','.join(a['proposal']['D']),','.join(a['proposal']['B']),f"{a['delta_phi_C']:.4f}",f"{a['delta_phi_R']:.4f}",','.join(a['after']['C']),','.join(a['after']['R'])] for i,a in enumerate(v['attempts']) if a['committed']]))
(B/'case_source_objects.json').write_text(json.dumps(allobjects,ensure_ascii=False,indent=2)+'\n')
(B/'casebook.md').write_text('\n\n'.join(book)+'\n')
(R/'1011_v10新语料实验与方法调整报告.md').write_text('\n\n'.join(report)+'\n')
print(json.dumps({'documents':len(allobjects),'report':str(R/'1011_v10新语料实验与方法调整报告.md'),'casebook_bytes':(B/'casebook.md').stat().st_size},ensure_ascii=False))
