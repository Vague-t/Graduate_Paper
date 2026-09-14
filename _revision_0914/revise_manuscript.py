"""Apply bounded, logged section/paragraph patches to the immutable 0913 baseline.

This is a legacy-manuscript revision record, not a claim of passing the complete
ARS 1.1 per-block adjudication/authorization contract. No experiment is run.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / '_revision_0914'
BASE = ROOT / 'report_0913.md'
baseline = BASE.read_text()
text = baseline
changes = []
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
source_hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                 for name in ['report_final.md', 'report_final.docx', 'report_0913.md', 'report_0913.docx']}

def replace(old, new, reason):
    global text
    assert text.count(old) == 1, (reason, text.count(old), old[:80])
    changes.append({'id': f'C{len(changes)+1:02d}', 'reason': reason,
                    'old_sha256': sha(old), 'new_sha256': sha(new),
                    'old': old, 'new': new})
    text = text.replace(old, new, 1)

def section(start, end, fragment, reason):
    old = text[text.index(start):text.index(end, text.index(start))]
    replace(old, (WORK / fragment).read_text().rstrip() + '\n\n', reason)

replace(text[:text.index('## 第一章')], (WORK / 'front.md').read_text().rstrip()+'\n\n',
        '更新版本说明和中英文摘要，统一两阶段研究主线，保留结果来源与证据边界')
section('### 1.2 ', '### 1.3 ', 'related_work.md', '按六条研究线索更新Related Work，补充9项直接或相邻研究并限定任务可比性')
section('### 1.3 ', '### 1.4 ', 'contributions.md', '采用两项方法贡献加一项验证工作，区分设计贡献与独立效果证据')
replace('第一章介绍研究问题、相关工作和贡献边界。第二章统一任务表示、序列化规范、评价口径及方法所需的技术基础。第三章讨论结论组件增强，明确其监督来源和可复现条件。第四章给出MCR-BR的评分与修正流程，分析算法保证范围并整理域内实验。第五章讨论粗粒度协议下的跨语料迁移。第六章总结研究内容及当前证据边界。附录给出实现核验清单和可单独实验的算法修订建议，不将建议视为已完成实验的方法。',
        '第一章介绍研究问题、相关工作及两项方法贡献。第二章统一任务表示、序列化规范、评价口径和训练—推理接口。第三章给出面向结论类组件的局部论辩结构保持增强方法及配套表示模块。第四章介绍完整候选图评估与异常驱动局部修正方法MCR-BR，分析其性质并整理域内结果。第五章在粗粒度标签和有向无标签连接协议下分析跨语料迁移。第六章总结研究工作及后续验证方向。附录保留实现核验清单与待实验的算法修订建议，不将建议视为已实现方法。',
        '同步论文组织结构与新贡献命名')
replace('### 2.6 本章小结', '''### 2.6 训练增强与推理修正的接口

第三章在训练集上构造结论中心增强样本，并将其与原始样本用于组件及结构化生成学习；第四章在测试输入上调用训练后的生成器，形成多个组件假设和对应候选图，再执行选择与局部修改。两个阶段共享第二章定义的组件坐标、类型和关系引用规范，但推理阶段的验证评分不回传为训练损失，本文未定义联合优化验证器和生成器的闭环训练算法。

因此，训练增强的作用应在推理策略固定时比较，图级选择与修正的作用应在生成器检查点及候选池固定时比较。完整框架可以报告组合后的表现，但不能用同一Full分数分别证明两个阶段的全部独立贡献。这一接口约定也是第三、四章同名配置核对的依据。

### 2.7 本章小结''', '补齐两阶段接口，防止混同联合训练和重复归因')
replace('## 第三章 面向结论类组件的结构感知增强', '## 第三章 面向结论类组件的局部论辩结构保持增强', '第三章标题突出具体增强单位而非宽泛技术组合')
replace('端到端论辩挖掘同时预测组件与关系，组件集合决定了后续关系搜索空间。若关键Claim未被识别，任何关系模块都无法在缺失节点上恢复正确边。为降低这一上游瓶颈，本章面向MajorClaim和Claim提出结论类组件优化方法：首先在训练数据层面生成带局部论证结构的增强样本，再在模型层面引入Claim-specific Adapter、Cue-aware Soft Prompting和辅助判别目标。三类机制分别补充样本多样性、强化类型相关参数更新并显式建模结论线索。',
        '端到端论辩挖掘中的组件集合限定了后续关系搜索空间；在固定组件集的关系预测设定下，遗漏Claim会使其关联金标准边不可达。本章据此设计面向结论类组件的局部论辩结构保持增强方法，以结论及其支撑或攻击邻域组织生成条件，在表达变化中保留类型与关系监督。Claim-specific Adapter、Cue-aware Soft Prompting和句子级辅助目标作为配套表示模块，与增强数据共同服务于结论组件学习，不分别列为独立创新。MajorClaim与局部Claim在当前关系表示中的作用不同，下文分别说明其增强条件和证据范围。',
        '第三章导言聚焦一个方法贡献，收紧固定组件条件')
replace('### 3.2 基于大语言模型的结构感知数据增强', '### 3.2 结论中心的局部结构保持增强', '统一方法命名')
replace('普通文本改写只约束句子语义，容易在改写后破坏组件边界或关系方向。本文以局部论辩子图而非孤立句子作为增强单位。',
        '若文本改写仅约束句子语义而未同步维护标注，组件边界和关系方向可能失配。本文以局部论辩子图而非孤立句子作为增强单位。',
        '避免无依据概括所有普通改写方法')
replace('### 3.3 面向结论组件的表示增强\n\n',
        '### 3.3 面向结论组件的配套表示增强\n\n本节的适配器、连续提示和辅助目标用于利用前节的训练监督，属于结论组件增强方案的配套实现。与DENIM的篇章结构前缀[7]<!--ref:sun2024--><!--anchor:section:Abstract-->和关联关键短语方法[0]<!--ref:das2025key--><!--anchor:section:3-->相比，本文关注结论类型条件和显式线索触发，而不将结构或线索的使用本身视为原创。三项模块的作用需分别通过受控消融解释。\n\n',
        '明确三个配套模块与近期相邻方法的关系')
replace('显式篇章线索对结论识别有帮助，但线索词与组件类型并非一一对应。', '显式篇章线索可作为结论识别的候选信号，但线索词与组件类型并非一一对应，其实际收益需由消融验证。', '将未独立验证的模块收益改为设计动机')
replace('結論组件优化后仍存在三类典型错误。' if '結論组件优化后仍存在三类典型错误。' in text else '结论组件优化后仍存在三类典型错误。',
        '结论组件学习需要重点检验以下三类潜在错误；当前缺少逐例输出，尚不将其视为已完成标注的错误分布。',
        '区分待检验失效机制与已有案例证据')
replace('本章围绕关键结论组件提出训练阶段优化方法。结构感知增强在保持局部图约束的条件下扩充训练样本，Claim-specific Adapter和Cue-aware Soft Prompting分别提供类型专项参数与篇章线索，多目标训练则增加结论存在性监督。原稿分类别记录呈现了正向差值，但尚需完成配置核验、增强独立消融和Premise性能检查，才能确认本章各机制对候选质量的具体贡献。',
        '本章以结论中心局部子图作为增强单位，将表达多样化与组件类型、关系端点和方向保持相结合，并通过分层筛选控制监督一致性。类型条件适配、线索感知提示和辅助目标作为配套模块支持结论组件学习。与孤立改写相比，该设计的差异是显式维护局部关系监督，其独立收益仍需通过等训练预算的增强对照验证。原稿分类别记录呈现了正向差值，但配置核验、Premise性能和门控可执行性仍是解释结果的必要前提。',
        '第三章小结与创新点一对应，不把结构保持等同于已证明增益')
replace('## 第四章 基于多候选评估与有界修正的论辩图生成方法', '## 第四章 基于候选图评估与异常驱动局部修正的论辩图生成', '第四章标题突出反馈对象与触发机制')
replace('本章提出MCR-BR推理时结构恢复框架。其核心思想不是用规则替代模型预测，而是保留多个由模型生成的结构假设，以确定性约束和单独调用的语义验证信号选择初始图，再在有限预算内对局部异常进行可回退修复。完整流程包括候选组件生成、候选图构建、一致性评分、初始解选择、异常检测和有界修正六个阶段。',
        '本章提出基于完整候选图评估与异常驱动局部修正的MCR-BR方法。其评估对象包含组件和关系，先为多个组件假设构建完整图，再以结构检查和单独调用的语义验证信号选择初始状态；检测到的异常触发局部动作，并通过接受检查、回退、轮数和接受动作数限制控制修改。完整流程包括候选组件生成、候选图构建、一致性评分、初始解选择、异常检测和有界局部修正六个阶段。这里的“有界”特指所定义的修正步数约束，不代表已给出全部生成与验证调用的严格上界。',
        '第四章导言与创新点二对应，限定有界含义')
replace('简单后处理可以删除非法边，却不能补回缺失组件；无约束Self-Refine又可能在修改错误部分的同时破坏原本正确的结构。',
        '仅删除非法边的后处理不能补回缺失组件；自由生成式修订则可能同时改变正确结构。MCR-BR据此限定修改对象和接受条件，但其当前动作集合同样不提供一般性的缺失节点插入能力。',
        '公平描述后处理和自修正，避免暗示本方法可补回所有遗漏')
replace('### 4.6 域内主要结果', '''#### 4.5.3 近期相关方法的比较边界

第一章补充的近期研究用于更新方法定位，并不自动成为已复现的实验基线。DENIM[7]<!--ref:sun2024--><!--anchor:section:Abstract-->和AASP[0]<!--ref:das2025aasp--><!--anchor:section:Abstract-->是优先考虑的生成式或结构预测对照，但需先统一数据划分、输入粒度及精确匹配评价。Cabessa等的分类生成方法[0]<!--ref:cabessa2025--><!--anchor:section:2.2-->、关键短语方法和FOL-AM基于给定组件的任务设定，不能直接并入现有端到端分数表。若将其改造为端到端流程，应单列组件分割器和新增计算成本。

Tran等的LLM-refine[0]<!--ref:tran2025--><!--anchor:section:4.2-->为多候选判断提供相邻对照思路，但其课堂话轮分割候选与本文整图不同。比较其思想时需要重新定义整图选择基线，不能沿用原论文任务分数。ARGUS属于端到端系统演示，组件分割研究只覆盖部分子任务；本稿不为这些方法补造统一实验结果，也不据现有表格宣称超过全部近期方法。

### 4.6 域内主要结果''', '补充近期基线可比性说明，不修改实验表格或虚构新基线分数')
replace('本章提出完整的MCR-BR结构恢复流程。多候选生成避免过早提交单一组件集合，多维评分将结构和语义信号用于候选选择，有界修正则把检测到的异常转化为局部、可回退的修改动作。现有域内结果、消融、验证器替换与Oracle记录呈现了值得进一步验证的趋势；本章同时指出软合法性选择、非法初始图恢复和调用预算的限制。各模块的独立贡献及预算匹配优势仍需通过可复现实验建立。',
        '本章以完整候选图为评估对象，将多候选选择与异常驱动局部修正连接起来，明确了异常、动作、接受条件和回退的关系。这是相对于一般多采样和自由文本自修正的具体设计差异，而不是对两类已有思想的首次提出。现有域内、消融、验证器替换和Oracle记录为分析完整配置提供依据；BR的净收益需在固定候选池下解释，额外计算的价值需经预算匹配比较。软合法性、非法初始图恢复和遗漏节点操作仍限定着当前方法的适用范围。',
        '第四章小结强调可辨识设计差异与BR净收益条件')
replace('本章检验第三、四章方法在训练域与测试域不一致时的表现。跨领域实验不作为独立算法创新，而作为对结构恢复框架适用范围的补充验证。为避免不同标签体系造成不可比较结果，本文首先定义粗粒度组件映射和无标签连接协议，再分析零样本迁移结果及其局限。',
        '本章在训练域与测试域不一致的条件下分析第三、四章方法的表现，作为两项方法贡献的适用性验证，而非第三项算法创新。与利用辅助语料联合训练的MT-AM[0]<!--ref:morio2022--><!--anchor:section:Abstract-->不同，本章声明的零样本设定仅使用源域训练监督。鉴于近期句子级论辩识别研究揭示了词汇线索与跨数据集泛化之间的风险[0]<!--ref:feger2025--><!--anchor:section:Abstract-->，本章特别区分领域变化、标签归约和评价口径，避免将域内正向结果直接外推到目标域。',
        '第五章接入跨语料经典与近期研究，明确源域监督设定')
replace('因此，本章将跨领域结果定位为适用性证据，而不是对通用领域泛化能力的最终证明。后续可通过增加AbstRCT等目标域、开展双向迁移和比较多种标签对齐策略，进一步检验结论的稳定性。',
        '因此，本章将跨领域结果定位为特定协议下的适用性证据，而不是通用领域泛化能力的证明。还需关注Cue-aware分支是否依赖源域常见结论词；可在目标域按有无线索词分组报告性能，并比较关闭该分支时的变化。这是受近期泛化研究启发的待验证问题，不是已经完成的实验。增加AbstRCT等目标域、开展双向迁移和比较多种标签对齐策略，可进一步检验结论稳定性。',
        '将近期泛化风险转化为本文具体的线索分支检验建议')
section('### 6.1 ', '### 6.2 ', 'summary.md', '总结同步两项方法贡献和验证工作，保留证据边界')
replace('0913版使用academic-research-suite的论文修订与引用核查流程，基于原稿和审阅意见进行编辑。辅助工作包括措辞修改、结构调整、公开文献元数据与相关论述核查、公式和指标一致性检查，以及Word排版；未运行训练实验，未生成人工标注结果，未代替作者确认研究事实。作者应逐项审阅修改，核对引用、实现和实验数据，并按学校及学院适用要求确认是否以及如何披露辅助工具使用。',
        '0914版在0913版基础上，参照academic-research-suite的论文修订、文献检索和引用核查要求，依据作者认可的贡献定位进行修改。辅助工作包括研究主线整理、近期公开文献核查、任务与评价边界比较、局部措辞修订、引用编号检查和Word排版，并保存逐段差异及修改说明。未运行训练实验，未生成人工标注结果，未将论文全文上传外部研究服务，未代替作者确认研究事实。当前遗留稿件缺少完整逐块路线图与裁决链，本轮使用可追溯局部补丁记录，不声称通过ARS全套逐块授权或研究完整性认证。作者应审阅修改，核对引用、实现和数据，并按学校及学院适用要求确认辅助工具披露方式。',
        '更新辅助工具披露及遗留稿件修订流程边界')

# Preserve all experiment tables, mathematical expressions, and evidence flags.
def experiment_rows(t):
    return [line for line in t[t.index('## 第三章'):t.index('## 第六章')].splitlines() if line.startswith('|')]
assert experiment_rows(text) == experiment_rows(baseline)
maths = lambda t: re.findall(r'\$\$(.*?)\$\$|\$([^$\n]+)\$', t, re.S)
assert maths(text) == maths(baseline), 'Unrequested mathematical change'
assert set(re.findall(r'待核验(R\d\d)', text)) == set(re.findall(r'待核验(R\d\d)', baseline))

refs = json.loads((ROOT / '_revision_0913/references.json').read_text())
refs.update(json.loads((WORK / 'new_references.json').read_text()))
main, tail = text.split('## 参考文献\n', 1)
appendices = '## 附录A' + tail.split('## 附录A', 1)[1]
order = []
def renumber(m):
    key = m.group(1)
    assert key in refs, key
    if key not in order: order.append(key)
    return f'[{order.index(key)+1}]<!--ref:{key}-->'
main = re.sub(r'\[\d+\]<!--ref:([^>]+)-->', renumber, main)
assert set(order) == set(refs), (set(refs)-set(order))
bibliography = '\n\n'.join(f'[{i}] {refs[k]["entry"]} [来源]({refs[k]["url"]})' for i,k in enumerate(order,1))
text = main.rstrip()+'\n\n## 参考文献\n\n'+bibliography+'\n\n'+appendices
assert '[0]' not in text
assert not any(ord(c)<32 and c!='\n' for c in text)
(ROOT / 'report_0914.md').write_text(text)
(WORK / 'text_changes.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2))
(WORK / 'references.json').write_text(json.dumps(refs, ensure_ascii=False, indent=2))
(WORK / 'citation_map.json').write_text(json.dumps({k:i for i,k in enumerate(order,1)}, ensure_ascii=False, indent=2))
(WORK / 'report_0913_to_0914.diff').write_text(''.join(difflib.unified_diff(baseline.splitlines(True),text.splitlines(True),fromfile='report_0913.md',tofile='report_0914.md')))
audit = {'baseline_sha256': sha(baseline), 'output_md_sha256': sha(text),
         'source_file_hashes': source_hashes, 'text_patch_count': len(changes),
         'references_before':21, 'references_after':len(refs), 'added_references':9,
         'added_2025_2026_references':8, 'experiment_table_rows_preserved':len(experiment_rows(text)),
         'equations_preserved':len(maths(text)), 'unresolved_evidence_items':14,
         'experiments_rerun':False, 'new_results_created':False,
         'ars_full_authorization_or_integrity_pass_claimed':False}
for name,digest in source_hashes.items(): assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
(WORK / 'build_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
print(json.dumps(audit, ensure_ascii=False, indent=2))
