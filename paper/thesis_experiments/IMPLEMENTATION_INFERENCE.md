# 第四章推理实现说明

此代码是根据论文定义新实现并实际调用 SciPy/HiGHS 的实验程序。它不复用旧模拟主表输出，不把构造单元测试当作目标模型结果。参考版本为 `protocol_identity_audit_20261012_v6/论文规范排版稿_v6.docx`；实现概念对应 4.2–4.5 节。

## 接口与职责

- `build_candidates(InputDocument, initial, candidate_graphs, span_proposals, group_proposals, config, relation_score_fn)` 构造冻结池。`InputDocument` 没有 gold 字段，传入带标注 `Document` 会报错。
- `SpanProposal(start, end, type_scores, score, token_count)` 和 `GroupProposal(sources, target, score)` 分别接收独立跨度头、完整源组模型的输出。模型生成与训练在其他模块完成。
- `evaluate_proposal(pool, scores, current, Proposal(...), config)` 评估一次完整依赖闭合事务。
- `repair(..., method='I1')` 按规模固定路由：不超过 2500 变量时 Global，否则 Single。也可显式运行 Global、Single、SetLocal、RelationOnly、Sequential、G0。
- `global_repair` 可独立调用；`replay_ledger` 检查输入/评分快照、哈希链、整图合法性、差分效用和预算。

**G0 不是 I0。** I0 包含旧 BR-O。顶层 `rank --with-i0` 调用单独的 `legacy.py` 原生对象新实现，身份为 `I0_NATIVE_BR_O_REIMPLEMENTATION`；这是依据已有参考流程的新移植，不声称复现历史原始检查点。此处 `repair` 的 `method='I0'/'BR-O'` 仍明确报错，因为本模块专门实现 I1/相应消融，不能偷偷用“不修正”或本章修正替代继承系统。

## 候选协议

初始图必须通过共同合法化，模块不猜测边界或删除冲突来制造初始合法性。成功解析的合法组件受保护；关系解析失败不会抹去独立合法组件。保护对象不受补充数量上限裁剪，保护是保留在候选池，不是强制终态选中。

补充跨度按提案分去重、排序，最多 64 个，每跨度最多 2 个原生类型。若提供模型 `token_count` 则执行 64-token 限制；未提供时只记录长度约束未核验，不通过字符数假装模型 token 数。`SpanProposer` 提供该计数。

AAEC 枚举兼容有向二元槽位。CDCP 至多 64 个模型完整源组提案，加上实际预测分段中相邻 2/3 成员的规则源组，补充总计至多 256，已有长超边完整保护。模型提案优先；规则提案分数缺省相同时按完整规范键排序。这是冻结的具体队列实现选择。CDCP 只在最终选中组件序列上约束连续性；候选池中可以保留当前尚不合法、以后可能合法的源组。

预检流式计数上限 50000 个实际槽位，超出时显式失败。补充槽位最终最多 4096，裁剪时按冻结完整对象分的槽位内最大值排序，槽位的全部原生标签共同保留。确需裁剪却没有评分函数、缺少任一标签评分时明确失败。NONE 由不选择任何正标签表示。

## 事务与整数规划

完整组件身份为原生字符半开区间和类型；关系身份含全部源成员、目标和原生标签。类型/边界替换按删除旧对象、加入新对象计费。

组件冲突闭合覆盖所有冲突旧对象。Single 允许 0→1、1→0、1→1；SetLocal 另外允许 1→2、2→1，并检查拆合包络及每事务至多三个组件编辑。全部接触变化端点的关系进入事务；已选事务外关系若因 CDCP 连续性失效，则将整个槽位最小扩域。未选且新变合法的非接触槽位不会被隐式加入，需要后续纯关系提案实际执行。

MILP 同时约束重叠、端点存在、标签互斥、CDCP 连续源、分项效用门和编辑预算。无环及单出边为显式可选协议，默认不擅自启用。全局约束 `y_h + z_w <= 1` 精确处理超边源成员之间被选中的非源组件。

局部相对当前状态累计编辑，全局相对 G0 计净编辑。有效概率采用 `2q-kappa` 的固定计数效用；提交前独立复核 `ΔC>=0、ΔR>=0、加权Δ>delta`。变化对象和完整事务域的缺分、非有限值、非概率值都会拒绝；域外未变对象可在差分中相消。全局要求全池齐分。

三级破同分先固定最大主效用，再固定最少实际编辑，不使用微小权重扰动。论文 B0625 与 B0690 的第三级描述存在差别，代码明确区分：局部默认使用真正的 `Graph.key` 最小值（空元组及短前缀优先）；全局默认依 B0690 按对象规范键逐位优先保持 G0。两者不混称同一种字典序，可用 `local_tie_break` / `global_tie_break` 显式选择并在元数据中记录。`graph_key` 实现先检查能否终止当前对象序列，再找最小可选的下一个对象，避免把二元位的零优先误当成可变长对象元组排序。第三级有调用上限。超时带有效 incumbent 可以提交，但记录主目标及破同分完成状态，不称其唯一最优。数学不可行、无 incumbent、无效 incumbent、评分缺失及求解异常分别记录；全局初始图可行，若求解器报不可行会标记实现/数值失败。

Sequential 是明确的消融：先按组件效用提交组件变更并删除失效旧关系，再尝试关系补全。第一阶段不要求关系分项非负，这正是取消共同接受的差别；因此不得用它声称 I1 的单调性质。两个阶段分别记录与计费，外层仍计一次尝试/接受。

## 执行、复核与边界

局部调度按六类动作轮转，以有限枚举数、每轮/总尝试数、接受数、累计编辑和墙钟时间限制。相同状态保留队列游标，不重新评估已取出的提案。耗尽尝试额度后，已评估合格项仍可提交；时间或实际编辑不足时不提交。失败保留最后一个完整合法图。

账本提交前构造整份记录，绑定池/分数/前后图身份及前一记录哈希；提交钩子异常时不修改内存状态、不增加语义编辑。该保证是单进程完整状态提交；服务器持久化文件使用上层原子写入接口，不能声称跨进程数据库事务。

`tests/test_candidates.py`、`tests/test_repair.py` 覆盖论文 b→b′ 教学算例、关系分项下降、缺分、CDCP 非接触失效与新合法槽位、拆合、净/累计预算、超时故障注入、提交回滚和回放篡改检查，并将 4 组连续随机评分的小问题全局主目标、24 组含大量同分的离散随机评分三级目标与穷举结果比较。另检查缺失初始对象分、非整数 incumbent 和各求解阶段共用时间预算。测试构造图不属于自然语料模型实测。

旧论文模拟数值、训练效果、校准效果与正式单卡 24GB 资源上限均不由这些测试证明；后续须用服务器运行清单与实际输出报告。

当前专项验证：`OMP_NUM_THREADS=2 .venv/bin/python -m pytest -q tests/test_candidates.py tests/test_repair.py`，25 passed（2026-10-12；小规模真实 SciPy MILP 与构造故障测试）。

## 后续补齐：NoRisk、Regenerate 与完整执行计划

`repair_no_risk(pool, scores, config)` 沿用冻结的成本、权重、预算、候选与评分，仅把 `delta` 设置成 `10 * numeric_tol`；外层不执行 `policy.enabled=false` 的风险停用。默认 `numeric_tol=1e-9` 时正间隔为 `1e-8`。主策略已选出 κR 时沿用该值，未选出时沿用预声明基础配置（默认 κR=1），不使用测试标签重新选择成本。因此 NoRisk 仍有结构合法性和组件/关系分项门。

`python -m argrepair.regeneration --help` 提供完整图重生成及 MCR 重排序的独立入口，接收 `--config --out --inputs --ranked --adapter --reference-budget`。生成与重排序语义审核共享一个追加模型调用/输入 token/输出 token 账本；审核调用不能藏在“重排序”名义下免计费。预算不足导致的失败保留 G0 与文档分母；已经调用模型但无法获得实际消耗的异常标记为 `failed_usage_unknown`，不能通过正式预算匹配门。

参考预算文件为 `{"documents": [...]}`，每个文档记录包含 `doc_id`、`input_sha256`、`checkpoint_sha256`、`reference_method: "I1"`、`limits: {calls,input_tokens,output_tokens}`、`accounting_complete: true`、`evidence_file` 与 `evidence_sha256`。`evidence_file` 必须是真实执行收据，具有相同身份和上限、`evidence_type: "EXECUTED_CODE_OUTPUT_NOT_HISTORICAL_THESIS_RESULTS"`、完整 `usage_records` 及非空 `source_artifacts`。每个来源记录给出 `path`、`sha256`，可选 `record_indices`；实际逐调用输入/输出 token 必须与收据逐条吻合。未提供这样的证据时，函数仍可作显式未匹配的调试，但 `verify_matched_predictions` 不允许其进入等预算统计。

这一接口**不会凭空生成 I1 预算证据**。旧论文的“2 次调用、AAEC 4096/2048、CDCP 6144/3072”是历史模拟协议，不能直接作为当前程序的实际消耗。上限相同也不要求实际消耗恰好相同；所有追加调用均须纳入同一计费边界，求解 CPU 成本单独报告。当前若缺少完整 I1 逐调用收据，应保持 `regeneration.enabled=false`，并使用已声明的六组主比较；获得真实收据后可运行独立命令或启用第七组。

`make_plan` 的策略集只使用每折 **T1** 的单一 OOF 池，保留对应 G0，不对 T0/T1 候选做 union。所选策略在最终 T0/T1 推理间共享。评分器拟合仍可使用预先声明的 T0/T1 联合候选家族；校准与策略评分按部署裁剪规则处理。

计划默认包含 NoRisk，共六组主要比较/语料。设置 `regeneration.enabled=true` 及 `regeneration.reference_budget_manifest` 后加入 Regenerate，该路径支持 `{corpus}`、`{seed}`、`{output}` 占位符。逐文档预算匹配验证位于评价与统计之前；缺失证据不会被当作成功。每个修复阶段另调用 `argrepair.analysis`，报告校准、初始 TP 损失、候选规模和已记录时延。

`run-plan --resume` 只跳过完全匹配的已完成阶段：核对计划、配置、源数据、代码、全部输入文件（含 checkpoint 目录及训练身份）、全部输出的哈希。失败/中断或未经确认的输出目录不会覆盖，需保留并使用新版本目录。尚未产生阶段状态、但所需外部文件尚缺时，可补足该文件后恢复已完成的前序阶段。

补充验证覆盖完整计划参数解析、T1 独立策略池、共享策略路径、输入/输出/配置/代码/目录权重漂移、失败保留、NoRisk 的冻结分数与真实 ObjectScorer 集成，以及 Regenerate 调用计费、预算不足、解析失败、未知消耗和证据哈希核验。
