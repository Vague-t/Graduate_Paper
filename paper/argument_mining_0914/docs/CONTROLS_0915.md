# 0915 匹配增强与保守关系修正

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: 用户授权的实验工程实现与离线软件检查
- Origin Date: 2026-09-15
- Verification Status: UNVERIFIED（真实语料上的效果）；软件检查单独见 `validation_0915_final/`
- Version Label: controls_0915_v1

## 交付边界

这是在 0914 参考工程上增加的新实验能力，不是恢复历史实验。未下载数据、模型，未调用付费 API，未运行 AAEC/CDCP 正式训练，未改论文历史分数。构造样例通过不能证明新方法有效或创新成立。

保留原版的评分、动作与默认配置语义。新增开关默认关闭。不要将原版分数填入保守版结果行，也不要将已有 Full 检查点用于冒充重新训练后的增强消融。

## 1. 增强对照定义

|组别|中心策略|生成提示中的显式局部关系|作用|
|---|---|---|---|
|A0|无增强|不适用|完整原始训练集|
|A1|结论中心|不提供|改写对照|
|A2|结论中心|提供|A2 对 A1 检验显式结构条件|
|A3|匹配后的随机中心|提供|A2 对 A3 检验中心选择策略|
|A4|匹配后的随机中心|不提供|与其他三组构成两因素设计|

结论中心延续增强代码原定义：AAEC 为 Claim/MajorClaim；CDCP 为 Policy/Value。这与原评分覆盖集合不完全相同，应在论文中分别定义，不能混称为同一个集合。普通版仍给出组件类型、保留槽位并使用同样的全文语义筛选，因此只能称“不提供显式局部关系条件的改写对照”。

所有局部单位均为中心及其直接入邻居；结构提示包含该节点集合的全部诱导边。每篇原始文档先按固定种子打乱结论中心，最多取 4 个。对每个结论单位，从同文档、组件数相同、诱导边数相同、原始槽位总 token 数处于同一分箱的未使用中心中均匀抽样。默认分箱宽 32，是工程初始值，不是论文已经使用或验证的超参数。

随机集合包括结论中心，也可能抽到同一个中心；不强行排除它而偷换成“非结论中心”。必须报告 `same_center`、`same_unit`、`random_is_conclusion` 和候选数量。若随机臂几乎全部仍是结论中心，中心类型的对比强度不足；不能凭这套配置宣称已经验证结论类型优势。应先审查实际训练图的候选分布，再另立更宽的匹配协议，不自动放宽规则。

同一来源和相同接受数量并不保证文本语义或计算量相同。输出长度、跨边界关系语义、人工抽检和原始/增强比例仍需审查。

### 1.1 冻结中心计划（不需要模型）

以下命令均在工程目录中执行，输出目录须不存在：

```bash
cd /Users/channtang/Downloads/paper/argument_mining_0914
source .venv/bin/activate
python -m am plan-augmentation --input data/processed/aaec/train.jsonl --seed 17 --max-pairs 4 --token-bin-width 32 --out runs/aaec_center_plan_s17
```

`plan.json` 绑定输入文档、种子和匹配规则，增强与匹配阶段会重新计算验证。只接受未增强的原始 train 文档，拒绝 dev/test 与混合语料。不能按测试分数修改计划。

### 1.2 生成四个臂（需要真实本地模型）

```bash
python -m am augment --config configs/augment_plain.json --input data/processed/aaec/train.jsonl --plan runs/aaec_center_plan_s17/plan.json --out runs/aaec_A1_s17
python -m am augment --config configs/augment_structure.json --input data/processed/aaec/train.jsonl --plan runs/aaec_center_plan_s17/plan.json --out runs/aaec_A2_s17
python -m am augment --config configs/augment_random_structure.json --input data/processed/aaec/train.jsonl --plan runs/aaec_center_plan_s17/plan.json --out runs/aaec_A3_s17
python -m am augment --config configs/augment_random_plain.json --input data/processed/aaec/train.jsonl --plan runs/aaec_center_plan_s17/plan.json --out runs/aaec_A4_s17
python -m am match-augmentation --original data/processed/aaec/train.jsonl --plan runs/aaec_center_plan_s17/plan.json --runs runs/aaec_A1_s17 runs/aaec_A2_s17 runs/aaec_A3_s17 runs/aaec_A4_s17 --out runs/aaec_matched_s17
```

四个臂除中心/策略字段外必须采用相同配置、后端与源代码。生成文件和调用成本文件做哈希核验；重复样本、未知配对、计划篡改、跨集输入会被拒绝。

只保留四臂均成功接受的配对，每对每臂保留一篇全文回填后的增强文档。所有 A0–A4 均保留完整原始训练集；A1–A4 再添加同一批配对。输出 `A0/train.jsonl` 至 `A4/train.jsonl` 与 `matching_report.json`，报告接受前后数量、缺失臂、同中心情况、每文档保留数、全部尝试调用成本和数据长度。

零共同配对直接报错，不输出可误认作增强的纯原文实验组。共同接受会引入筛选子集偏差，所有臂生成但最终丢弃的成本也必须计入；不能为了匹配只报告保留样本的成本。语义过滤器仍是同一模型，不是独立真值或人工验收。

### 1.3 训练预算与检查点选择

```bash
python -m am train --config configs/aaec_controls_train_single.json --train runs/aaec_matched_s17/A0/train.jsonl --dev data/processed/aaec/dev.jsonl --out runs/aaec_A0_train_s17
```

对 A1–A4 分别替换训练输入与输出目录并重新训练，均采用同一配置和同一单候选推理协议。该配置的 1000 次优化器更新、每 100 步验证、最多 100 个 epoch 是可编辑的试跑模板，不是已经确定的正式实验预算。先在训练/开发集上检查资源与收敛，再统一冻结预算。多种子需统一修改计划与四个增强配置的 seed；也可以先固定一份增强数据，仅改变训练种子，但必须明确这不包含增强随机性的方差。

新增 `eval_every_steps` 使各组按相同步数验证和选择最佳 dev loss 检查点，避免各组每轮长度不同造成验证机会不同。原版该字段为 null，仍按 epoch 验证。训练结束必须核对：

- `requested_step_budget_met` 为 true，实际 `optimizer_steps` 相同；仅有上限不够。
- `evaluation_steps` 一致；记录 `selected_optimizer_step`，不得人工挑测试最优模型。
- `effective_batch_size_histogram`：末尾不足批次可能造成每次更新样本量不同。
- `observed_examples`、`sample_exposures`、`observed_input_tokens`、`observed_response_tokens`。

`observed_input_tokens` 是实际训练样本的提示+目标序列 token 次数，不含额外连续提示位置，也不含开发集前向与反向计算倍率；不是完整 FLOPs。相同步数不构成严格等算力证明。组件比例由实际全文数据统计决定，不能仅按被改写局部的类型数声称类别不平衡已经缓解。

## 2. 保守关系修正

|配置|固定组件|固定覆盖节点和阈值|严格涨分|新增边须经验证器支持|
|---|---|---|---|---|
|aaec_full_br_k3|否|否|否|无独立硬门槛|
|aaec_br_fixed_components_only|是|否|否|无独立硬门槛|
|aaec_br_frozen_coverage_only|否|是|否|无独立硬门槛|
|aaec_br_both_frozen|是|是|否|无独立硬门槛|
|aaec_br_conservative|是|是|是|是|

每次修正开始后冻结覆盖集合及每个节点的阈值；它只作用于这一初始图的修正，不应用于候选池重排序，不宣称跨候选图已经可比。原 0.4/0.4/0.2 权重、候选生成与选择策略保持不变，以免混入权重调参因素。

保守版禁止 Promote/Demote 和 Replace，并对所有动作的结果再次校验组件完全不变，防止 LocalRerun 或其他入口绕过。任何新出现的关系都必须得到当前文本验证器的支持；判断失败不能当成通过。同分或下降拒绝。低覆盖只能触发尝试，没有可接受动作就保持原图结束，不强迫补边。

局限：验证器仍可能误判；固定组件不能纠正边界/类型错误；初始图含多个非法项时仍可能因“候选须整体合法”而无法逐步修复。局部重跑在低覆盖事件中仍可能考察很多源节点。两种冻结单项消融用于区分机制，保守版与双冻结版的差异还混合了严格涨分和新增边门槛，不能将这个差异归于某一项。

### 2.1 同检查点、同候选池开发集评估

先使用一份实际完成的新训练检查点。下列检查点路径是待产生的运行产物，不表示本地已有：

```bash
python -m am infer --config configs/aaec_full_logprob_k3.json --checkpoint runs/aaec_full_s17_train/best --input data/processed/aaec/dev.jsonl --out runs/aaec_dev_pool_s17
python -m am infer --config configs/aaec_full_rerank_k3.json --checkpoint runs/aaec_full_s17_train/best --input data/processed/aaec/dev.jsonl --cache runs/aaec_dev_pool_s17/candidates.jsonl --out runs/aaec_dev_rerank_s17
python -m am infer --config configs/aaec_full_br_k3.json --checkpoint runs/aaec_full_s17_train/best --input data/processed/aaec/dev.jsonl --cache runs/aaec_dev_pool_s17/candidates.jsonl --out runs/aaec_dev_original_br_s17
python -m am infer --config configs/aaec_br_conservative.json --checkpoint runs/aaec_full_s17_train/best --input data/processed/aaec/dev.jsonl --cache runs/aaec_dev_pool_s17/candidates.jsonl --out runs/aaec_dev_conservative_br_s17
python -m am audit-repair --gold data/processed/aaec/dev.jsonl --traces runs/aaec_dev_original_br_s17/traces.jsonl --out runs/aaec_dev_original_audit_s17
python -m am audit-repair --gold data/processed/aaec/dev.jsonl --traces runs/aaec_dev_conservative_br_s17/traces.jsonl --out runs/aaec_dev_conservative_audit_s17
```

其余三个修正消融替换配置和输出目录即可，必须使用同一 `candidates.jsonl`，不能只写相同 seed 便认为候选相同。默认同调用/token 上限，不代表实际消耗相同。无缓存端到端时延与缓存后墙钟时间不得混比。

### 2.2 审计口径

`audit-repair` 独立于推理，仅在事后读取 gold；核对所有文档 ID 与公开输入文本/词元哈希。输出包含：

- 修正前后组件与关系的精确匹配 micro P/R/F1，关系端点包含类型。
- 正确对象丢失、正确对象新增、误报变化。正确对象丢失率分母是修正前全部正确对象，不是“被触及正确对象”；不把集合变化冒充一对一动作归因。
- 同一修正评分尺度下，内部总分上升而文档 F1 下降的文档数/比例。不能将该文档比例当成语料 micro-F1 的变化。
- 每类动作尝试数、接受数；新 trace 记录被接受动作的前后图，可以逐动作审计。旧 trace 缺失时明确标为 unavailable。
- 实际与逻辑调用/token、已观测耗时。解析和验证失败的文档仍留在任务指标分母中；没有初始/最终评分的文档仅不进入评分背离诊断分母。

审计不执行显著性检验、不给出因果结论、不验证伪造日志的真实性；不同实验的同池性仍须核对候选缓存和 run manifest。先开发集审计，再冻结规则，最后一次性运行测试集。

## 3. 可立即运行的离线软件检查

```bash
python scripts/validate_project.py --out validation_0915_final
python scripts/diagnose_controls.py --out runs/constructed_controls_0915_final
```

第一次交付已运行这些命令；重跑请使用新的输出目录名。测试涵盖匹配生成/导出、计划与结果绑定、原反例回归、所有组件修改入口、同分拒绝、新增边门槛、错误边删除、失败分母，以及随机初始化微型模型的训练与预算记录。诊断目录的 F1 仅针对人工构造图，绝不能作为 AAEC/CDCP 实验表数据。
