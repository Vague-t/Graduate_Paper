"""Verify coverage, cross-references and derived arithmetic in the global revision."""
from pathlib import Path
import re,json,hashlib
W=Path(__file__).resolve().parent;R=W.parent
s=(R/'report_1010_v1_full.md').read_text();old=(R/'report_1009_v4_full.md').read_text()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def table(text,n):
    m=re.search(r'^表'+re.escape(n)+r' [^\n]+\n\n((?:\|[^\n]*\n)+)',text,re.M)
    assert m,n
    return [[c.strip() for c in line.strip('|').split('|')] for line in m.group(1).strip().splitlines()]
preserved=[]
for new,prior in [('3-4','3-3'),('3-5','3-4'),('3-7','3-5'),('3-8','3-6'),('3-9','3-7'),('3-10','3-8')]+[(f'4-{i+1}',f'4-{i}') for i in range(1,10)]+[(f'5-{i}',f'5-{i}') for i in range(1,4)]:
    assert table(s,new)==table(old,prior),(new,prior);preserved.append([new,prior])
# Construction costs keep all five original construction columns.
assert table(s,'3-11')==[row[:-1] for row in table(old,'3-9')]
raw_names=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
for n in raw_names:assert sha(W/n)==sha(R/'_revision_1009_v4'/n),n
assert re.findall(r'\$\$(.*?)\$\$',s,re.S)==re.findall(r'\$\$(.*?)\$\$',old,re.S)
for text in [s,old]:
    assert '# 附录E ' in text and '# 附录F ' in text
assert s[s.index('# 附录E '):s.index('# 附录F ')]==old[old.index('# 附录E '):old.index('# 附录F ')]
# Every numbered table/figure/algorithm mentioned has a caption; sequences are continuous.
clean_source=re.sub(r'^\*\*(.+)\*\*$',r'\1',s,flags=re.M)
captions=re.findall(r'^(表[A-H1-6]-\d+|图[1-6]-\d+|算法[1-6]-\d+) ',clean_source,re.M)
assert len(captions)==len(set(captions))
mentioned=set(re.findall(r'(?:表[A-H1-6]-\d+|图[1-6]-\d+|算法[1-6]-\d+)',s))
assert not mentioned-set(captions),mentioned-set(captions)
for prefix in sorted(set(x.split('-')[0] for x in captions)):
    ns=[int(x.split('-')[1]) for x in captions if x.split('-')[0]==prefix]
    assert ns==list(range(1,len(ns)+1)),(prefix,ns)
assert re.findall(r'^\[(\d+)\] ',s,re.M)==list(map(str,range(1,50)))
assert len(re.findall(r'^!\[',s,re.M))==11
assert s.count('## 第')==6
assert '## 第三章 关系影响域约束的增强与成对学习' in s
assert '图5-2' not in s
assert '直接生成式基线' not in s
assert '优势主要体现在预算分配与过程可解释性' not in s
assert '允许尝试额度耗尽后提交' not in s[s.index('### 6.1'):s.index('### 6.2')]
r=json.loads((W/'scenario_results.json').read_text())
for ds in ['AAEC','CDCP']:
    metrics=r['metrics'][ds];c=r['costs'][ds]
    a=metrics['full_data_i0']['relation']['mean']-metrics['qos_i0']['relation']['mean']
    assert f'{a:.2f}' in s
    for v in [100*(c['global_equal']['mean_s']-c['t1_i1']['mean_s'])/c['global_equal']['mean_s'],100*c['t1_i1']['solver_s']/c['t1_i1']['mean_s']]:
        assert f'{v:.2f}%' in s
    diff=metrics['t1_i0']['relation']['mean']-metrics['t0_i1']['relation']['mean']
    assert f'{diff:.2f}个百分点' in s
for idx,code in enumerate(['t0_i0','t1_i0','t0_i1','t1_i1'],2):
    row=table(s,'5-4')[idx]
    for ds,col in [('AAEC',1),('CDCP',3)]:
        expected=r['metrics'][ds][code]['relation']['mean']-r['metrics'][ds]['t0_i0']['relation']['mean']
        assert row[col]==f'{expected:+.2f}'
g=table(s,'5-5')
assert g[-1]==['超过3个／0','—','—','—','—']
for k in [1,2,3]:
    raw=r['cdcp_source_strata']['t0_i0'][str(k)]
    n=raw[0][0]+raw[0][2]
    assert all(a[0]+a[2]==n for a in raw)
    assert g[k+1][0]==f'{k}个／{n}'

# Each row binds an agreed suggestion to verifiable revised text and a remaining evidence condition.
items=[
('1.1','真实问题规模','1.1、3.1、4.1、H.1','四层均记录源文档数、变体数、被审因素数和漂移数','诊断协议已写入；真实基线材料待取得'),
('1.2','错误维度与重叠','4.1、H.1','上述维度不直接相加为互斥因果比例','已明确分类顺序及独立恢复维度'),
('1.3','方法入口的小表','表3-1、表4-1','训练侧诊断与方法响应（诊断方案）','已加入两张小表；不填造数量级'),
('1.4','教学例与真实例分工','4.6.6、H.4','教学例只解释机制','已区分机制案例与真实取证格式'),
('2.1','统一第一贡献定位','摘要、1.3、第三章、6.1','关系影响域约束的增强与成对学习','标题、摘要、关键词、贡献与结论已同步'),
('2.2','中心与成熟工具归属','3.1、1.3.3','结论优先是默认区域选择策略','保留前期成果和中心负结果'),
('2.3','保留梯度和等变边界','3.4、3.5、F.2','对齐项不直接训练该分支','保留原有输入隔离与梯度定义'),
('2.4','T-B同损失比较','3.6.1、3.6.3、G.3','相同基础损失、匹配训练规模与更新条件','明确1.79／1.83为数据构造差值'),
('2.5','两轨及训练成本','3.6.1、表3-7至3-11、H.2','两轨不拼接为同资源优势','主成绩标匹配轨，固定尝试训练小时移存档'),
('3.1','非复制与编辑距离','3.6.2、H.2','规范化编辑距离采用固定评价分词器','度量与分母已落实；原始文本缺失，未造结果'),
('3.2','容易样本选择偏向','3.6.2、H.2','训练侧冻结的长度、关系数及显式／隐式关系组','写入联合分组分析'),
('3.3','因素与变体单位','3.6.2、H.1','本章不主张筛选器的变体级精确率','保持因素审计，不强加变体准确性主张'),
('4.1','等条件全局为主要对照','RQ2、4.1、4.6.1','把同候选、同评分的全局ILP作为主要竞争方案','已调整核心研究问题'),
('4.2','求解与端到端预算分开','2.6.3、4.6.1、H.3','当前情景只提供等求解预算行','协议已写入，未将旧行改称新实验'),
('4.3','少量预算与图规模','H.3','预定0.5、1、2倍三个逐文档总额度','定义预算点、分组及失败分母'),
('4.4','状态、gap与最优性','4.6.1、H.3','局部子问题的界不拼成整图全局界','保留状态字段，真实证书待运行'),
('4.5','可复核事务轨迹','4.6.6、B.5、H.4','可复核轨迹需能重算该次接受或拒绝','完整原文和对象轨迹要求已落地'),
('4.6','正面解释强全局取舍','4.6.5、5.4、6.1','当前情景没有支持“局部更安全”或突出的效率优势','复算小时间差及求解占比；明确简化条件'),
('5.1','裁剪前组合与评分成本','4.2.5、H.3','裁剪前完整槽位、全部标签评分对象','补规模分析、计费对象与字段'),
('5.2','预检依据及失败保留','4.2.5、H.3','金标仍进入FN与失败率','阈值依训练侧测量，保留失败'),
('5.3','候选策略改变条件','4.2.5','若裁剪前枚举不可承受，再比较预筛选或受限生成','保持现策略，规定改变后重验共同候选'),
('5.4','真实3成员与零样本组','5.5、表5-5','超过3个／0','纠正分组并新增每组金标数'),
('5.5','长超边保护与新建','5.5、H.4','保护长超边与新建长超边分别以初始命中／遗漏金标为分母','明确保护池可选回与新增枚举的区别'),
('6.1','扩大外部研究检索','1.2、G.1、G.2','UniASA','11组表内方法及2项输入边界参照，新增3文献'),
('6.2','外部可运行性与选择','G.2、G.4','CDCP转换模块不在仓库中','明确代码缺口，选择优先接入方法；未复跑'),
('6.3','QOS适配差异','表G-2','当前数据构造对照的适配范围','列输入、范围、过滤、规模、损失、评价'),
('6.4','外部评价兼容性','G.4','共同评价只比较可直接导出的原生完整对象','规定原配置与共同任务双轨，不混榜'),
('6.5','历史记录身份','附录E、G.1','原论文成绩不并入本版人工情景主表','附录E全文保持不变'),
('7.1','四格及条件增量','5.1','两阶段各自带来多少增量','保留主表与非正交互'),
('7.2','共同独有及新错误','5.2、H.4','共同修复、各自独有修复、组合新增、仍遗漏与新破坏','给出集合与记录，未伪造交集统计'),
('7.3','训练改变修正条件','5.3','初始错误减少、候选改善或评分适配','分开三条路径，不做单因归因'),
('7.4','配置选择的新增分析','5.4','T1＋I0同时优于T0＋I1','由旧数据复算在线选择并说明一次性投入边界'),
('7.5','失败层次与案例','5.5、H.4','动作不可表达需要穷尽声明邻域或给出规则证据','明确最早阻断及未搜索到不等于不可达'),
('7.6','减少重复表图','第四、五章','相对共同起点的关系增量与在线额外时间','风险图移第四章，成本表去掉重复F1'),
('8.1','摘要独立身份','中英文摘要','the numbers are not empirical model results','中英文摘要及实验题注已标人工情景'),
('8.2','正文与附录层级','第二、四章；A.6、B.6','完整示例、坐标往返和异常处理见附录A.6','序列化、坐标细则和证明移附录'),
('8.3','逐章叙事与总结','1.4、3.1、4.1、第五章、6.1','方法价值最终由现实问题规模、可复核输出和相应代价支撑','第六章去调度细节，统一研究层次'),
('8.4','执行规约与复现性保留','算法、B.3、B.4.3、F.2','提议评估与提交的预算判定','保留原始执行条件及32个陈列公式'),
('8.5','推进顺序和停止条件','6.3、H.5','关键假设不成立时，先调整定位或简化机制','明确先诊断后正式比较，不以检查数量扩张'),
]
coverage=[]
for ident,topic,loc,needle,status in items:
    assert needle in s,(ident,needle)
    line=s[:s.index(needle)].count('\n')+1
    coverage.append({'id':ident,'topic':topic,'locations':loc,'line':line,'anchor':needle,'status':status})
out={'passed':True,'source_sha256':sha(R/'report_1010_v1_full.md'),'review_source':str(R/'1009_v4全局评审与完整修改建议.md'),'covered_subitems':len(coverage),'covered_main_items':list(range(1,9)),'preserved_numeric_tables':preserved,'unchanged_raw_files':raw_names,'numbered_captions':len(captions),'numbered_tables':len([x for x in captions if x.startswith('表')]),'references':49,'display_equations':32,'appendix_E_unchanged':True,'evidence_scope':'WRITING_AND_ARITHMETIC; real evidence conditions remain unexecuted','items':coverage}
(W/'review_coverage.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['items','preserved_numeric_tables']},ensure_ascii=False))
