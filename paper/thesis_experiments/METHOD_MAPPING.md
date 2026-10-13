# 当前论文 v6 与实验程序对应关系

本表以新代码的实际接口为准。旧论文的模拟成绩、模拟验收与当前新程序的执行身份分开；这里列出“已实现”只表示有具体代码，不代表目标模型完整实验已完成或通过效果验收。

## 第一部分：可靠增强与成对学习

| 论文内容 | 程序位置 | 实际行为与校验边界 |
|---|---|---|
| 3.2.1 全局/专项 LoRA | `modeling.DualLoRALinear`、`prefix_gate` | 基础冻结；q/k/v/o 双分支；门控只读当前之前的生成前缀；类型字段闭合后开启，组件结束关闭 |
| 3.2.2 线索提示与句子监督 | `ExtractionModel.encode_input`、`training.sentence_spans` | 六组词边界线索触发四向量提示；句内输入表示均值池化，结论跨度相交标记 BCE |
| 3.3.1 中心/完整入源/因素宇宙 | `augmentation.select_rewrite_set`、`factor_universe` | 固定哈希中心；全部直接入源；AAEC 全有向对；CDCP 连续至多三源候选加全部金标完整超边 |
| 3.3.2 完整条件生成 | `augmentation.build_generation_payload` | 全部改写槽位/只读端点及类型、正关系表、语义未知例外、确定性有限宇宙与 NONE 补集；可无损还原完整影响域，仅提供给训练侧增强器 |
| 3.3.2 字符输运 | `augmentation.transport` | 原生 Unicode 半开区间；全部组件、完整关系端点与原生属性绑定同时更新；只读文字不变但坐标可以移动 |
| 3.3.3 semantic unknown | `FactorUniverse.unknown` | 已标注联合源的无独立正标注真子集不作为原文/增强语义 NONE；显式正标注优先 |
| 3.3.3 盲审与因素掩码 | `augmentation.review_view`、`cli augment` | 原/新分别分类后再比较标签；任一组件含义变化/待定拒绝；关系未审核或待定取 mask=0，不能改写成 NONE |
| FactorMask / FullFilter | `review_view(mode=...)` | FactorMask 覆盖全部受影响正关系及有限 NONE；正关系覆盖不足时保留组件、清空关系学习；FullFilter 覆盖完整声明影响域，否则拒绝 |
| 3.4.1 辅助头 | `training.factor_predictions` | 输入全文独立前向；组件跨度均值+全文末表示；关系完整源均值+目标+全文末表示+无标签几何；标签只作监督 |
| 3.4.1 双侧 JS | `js_divergence`、`compute_source_loss` | 不 detach；组件 A+ 与可靠掩码取交集；关系正类/NONE 仅对非空组归一化 |
| 3.4.2 源文档归一化 | `compute_source_loss`、`train` | 头监督除以 1+m；成对项按接受视图平均；最后一批按实际源文档数归一化 |
| 原文完整生成 | `ExtractionModel.generation_loss` | 仅原文整图答案+EOS；增强完整输运图只作追踪，不绕过掩码加入生成损失 |
| 消融 | `TrainingConfig.variant` | T0、Heads、NoPair、CompPair、T1；同一源的增强/掩码在成对消融之间复用 |

含金标的增强条件只属于训练侧增强器，不能进入下游提取器的输入。所有最终推理入口只接收无 `graph` 字段的 `InputDocument`。

## 第二部分：候选、独立评分与依赖闭合推理

| 论文内容 | 程序位置 | 实际行为与校验边界 |
|---|---|---|
| 多候选及 G0 | `ExtractionModel.generate`、`legacy.select_initial` | 一路贪心与采样候选；完整图重排序；原生身份合法化；解析或剩余冲突失败显式保留 |
| 继承 I0 / 旧 BR-O | `legacy.repair_legacy`、`rank --with-i0` | 原生对象新移植，动态 DENS/COH/VAL 与非下降接受；有界 RemoveEdge、Promote/Demote、Replace、LocalRerun；不是 G0 |
| 有限跨度提案 | `proposals.SpanProposer` | 冻结全文编码+字符原生起止 BCE+类型头；最多 64 个补充跨度、每跨度前 2 类型；边界 beam 明示为有限召回近似 |
| CDCP 完整源组提案 | `proposals.build_group_prompt`、`parse_group_proposals` | 冻结指令模型读取预测组件目录；最多 64 组模型提案，加入规则后补充合计最多 256；保护原有长超边另计 |
| 固定候选宇宙 | `candidates.build_candidates` | 先检查最多 50000 实际槽位；补充最多 4096；需要裁剪时依赖冻结完整对象排序；缺分不猜测 |
| 完整对象评分 | `scoring.ObjectScorer` | 独立冻结文本编码；组件 NULL/原生类型头、完整关系正确性头；完整字符/类型/源组/标签匹配才为真 |
| OOF 拟合与校准 | `workflow`、`fit_scorer`、`fit_calibrators` | 三折候选来源隔离；fit/calibration/policy 源组分离；分族 Platt；校准保留各生成器部署分布，不用 union 虚构自然频率 |
| 固定分数与缺分 | `ObjectScorer.score`、`Scores` | 搜索前绑定池、编码器、头、校准参数摘要；同对象同分；缺失值保留，不当作低概率 |
| 4.4 依赖闭合事务 | `repair.evaluate_proposal` | 冲突旧组件闭合；全部接触关系；CDCP 已选域外失效槽位最小扩域；完整差集编辑计费 |
| 共同接受 | `repair` | ΔC≥0、ΔR≥0、总增量>δ；变化对象/事务关系齐分；整图合法、编辑预算可行才提交 |
| 4.5 局部/全局 | `repair.repair`、`global_repair` | 小池 Global，大池 Single；SetLocal 为显式消融；局部累计编辑、全局相对 G0 净编辑 |
| 分级求解证书 | MILP 返回元数据 | 区分主目标最优、二级最少编辑、三级破同分完成；可行 incumbent 不自动写成唯一最优 |
| 回滚/成本 | 事务账本、阶段 manifest | 拒绝仍计计算成本；提交失败不增加语义编辑；绑定前后图、固定分数及哈希链 |

`I0_NATIVE_BR_O_REIMPLEMENTATION` 是本轮新实现身份；不得将它写成“历史原始检查点已复现”。`repair.py` 的 I1 求解接口不接受名为 I0 的替代路径，I0 由单独的 `legacy.py` 实现。

## 模块到底用了什么

| 模块 | 服务器默认模型/实现 | 训练状态及记录 |
|---|---|---|
| 提取生成器 | Qwen2.5-7B-Instruct + 双 LoRA + soft prompt | 训练更新 LoRA/提示/辅助头；基础权重冻结；保存 adapter、模型清单和实际训练 loss |
| 增强生成器 | `chat.model_id` 指定的冻结 Qwen2.5-7B-Instruct | 仅指令调用，输出槽位替换；保存原始输出和 token/调用预算 |
| 语义审核器 | 同一固定基础模型的独立无答案分类请求 | 类型、meaning、关系任务分开；不读取期待标签；与增强器共享基础模型不意味着误差独立 |
| 评分编码器 | `encoder.model_id` 指定的冻结 Qwen2.5-7B-Instruct `AutoModel` | 无生成器 adapter，参数不更新；模型/tokenizer/权重摘要绑定评分头 |
| 完整对象评分头 | 1024 隐层两层 MLP | 真实 OOF 候选拟合，再独立校准；不是第三章语义辅助头 |
| 跨度提案器 | 冻结编码器+原生字符起止头+类型头 | 从训练侧真实标注拟合；与提取生成器分开记录 |
| CDCP 源组提案器 | `chat.model_id` 固定指令调用 | 本轮明确补全的具体实现，输入只含预测组件，不使用金标源组；没有捏造独立“已训练提案器”检查点 |
| 求解器 | SciPy/HiGHS MILP | 无训练参数；实际求解时间、状态、incumbent 复核和预算记录 |

本地 `local_qwen05b` 将这些 HF 基础模型替换为精确版本的 0.5B，CPU float32；`local_tiny` 的提取/编码器是随机调试模型。每个 profile 与每轮 manifest 单独命名，不混报模型规模。

## 第五章与协议差异

1. 四格为 T0/I0、T1/I0、T0/I1、T1/I1。T1/I0 改训练但保留 BR-O；T0/I1 替换推理配置。I0 与 I1 都从共同重排序/合法化 G0 分支运行。
2. 推理消融包括 RelationOnly、Sequential、Single、SetLocal、Global。Sequential 明确允许先提交组件再尝试关系补全，不具有共同接受的分项单调保证。
3. NoRisk 使用同一冻结评分、κ、依赖闭合、合法性、分项门与编辑预算，仅令 `delta=10 × numeric_tol` 并不沿用 policy 的禁修开关；配置由计划保存，不能用测试结果选择。
4. Regenerate 必须有逐文档真实 I1 调用/token 资源证据，并绑定相同检查点/输入；没有该证据时默认不启用，也不能搬用历史模拟的“两调用”数字声称等预算。
5. 局部三级 tie 默认真正的 `Graph.key` 最小值；全局三级 tie 默认按规范对象顺序优先保持 G0。这是论文两处描述差异的显式实现决定，不把两者都称为相同字典序。
6. 训练侧策略选择预先只使用 T1 的独立 OOF policy 池；冻结策略共同应用于最终 T0/T1，不合并不同生成器的初始图。这一选择不保证 T0/T1 风险相同，必须报告。
7. 工程默认每个 MILP 调用 5 秒、阶段总 90 秒，具体以冻结配置为准。若要比较论文中 AAEC 3 秒与 CDCP 5 秒，应分别冻结语料配置后运行，不在测试途中切换。
8. 当前计划的主要比较族在 `comparisons.json` 中明确登记；不能与历史模拟稿 14 项比较族默认为同一个实验。统计使用真实文档×种子×方法 TP/FP/FN，配对重采样并对登记主要族校正。

## 证据与可复现范围

第三章专项测试已真实验证 native 输运、语义未知、盲审掩码、只读语义漂移、双侧 JS、门控无未来答案、冻结/可训练梯度、源归一化、实际 optimizer 更新和保存加载；随机 mini Qwen2 还实际运行了 HF 双视图 checkpoint 前后向与缓存生成。它们是软件执行证据，不是目标语料收益证明。

每次实验应保留：原始数据摘要、代码摘要、精确模型 revision、生成与审核记录、真实接受/拒绝视图、折分/来源、OOF 候选、校准参数、策略选择记录、完整计数、失败覆盖、求解证书和成本。CPU 诊断、构造图、故障注入、随机模型与服务器目标模型结果应分别报告。
