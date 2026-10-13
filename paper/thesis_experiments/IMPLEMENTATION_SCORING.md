# 冻结对象评分与有限提案实现

本文件对应当前论文第四章 4.2–4.3 节、原配置 `preview_config.json` 中的评分/提案接口。论文原有模拟表格不作为训练数据，代码不读取那些表格，也不生成预定的“通过”值。三类组件相互独立：第三章训练期语义辅助头、这里的完整对象正确性评分器、独立跨度召回头。

## 1. 实际模块与身份

- `HFTextEncoder` 用 Hugging Face `AutoModel` 和 fast tokenizer 编码**输入全文**，不拼接金标答案。编码器参数冻结，保持 `eval()`；超过输入限制直接失败，不截断尾文。身份保存模型名、请求 revision、解析出的 commit、tokenizer SHA256；本地模型路径额外计算权重文件 SHA256。正式运行应传固定 revision。
- `TinyTextEncoder` 是真实运行的固定随机字符嵌入调试器，有确定性 seed、宽度和版本；它不是预训练模型，不是 Qwen 替代成绩。
- `ObjectScorer` 组件头为 `Linear → GELU → Dropout(0.1) → Linear`，默认隐藏宽度 1024，输出 `NULL + 原生类型`。关系头同样为两层 MLP，输出一个完整对象正确性的 logit，校准后为概率。模型保存/加载校验编码器身份和头参数摘要。
- `SpanProposer` 使用独立线性起止头和原生类型头。它拟合真实训练标注，推理只接受没有 `gold` 字段的 `InputDocument`。
- CDCP 源组提案器采用**独立声明的指令模型调用**。`build_group_prompt` 输入全文及预测组件目录；`parse_group_proposals` 解析完整源集合和目标。此处是对论文未指定实现的工程补全，不能称为旧实验已经使用过的模块。调用模型及其 revision 由运行入口登记。

冻结 HF 编码器支持 `quantization_config`、`device_map` 等模型加载选项。24 GB GPU 可使用 4-bit Qwen 编码；本模块不将冻结编码器拷贝成训练用生成器，也不默认保证多个 7B 实例可同时驻留。

## 2. 完整对象特征与监督

组件特征是跨度平均隐状态、全文平均隐状态及六项位置量：原生起止位置、长度、首/尾 token 内残差、覆盖 token 比例。不同原生字符边界即使覆盖相同 token，也不会因键或特征构造被强制合并。

关系特征包括完整源组跨度表示的均值、目标跨度表示、全文上下文、源/目标原生类型、待核查关系标签、源到目标方向、相对距离及源组大小。所有特征由固定输入与完整对象确定，不读取当前选中图的度数、边数或搜索状态。

组件监督对每个候选跨度计算 `NULL/原生类型`。关系正例必须与金标的完整源集合、目标边界、所有端点类型及关系标签全部精确一致。错误跨度、错误类型、错误标签以及金标联合源的无单独标注真子集均为**完整对象不匹配**负例；这不等于把真子集声明成语义 `NONE`，第三章的语义未知掩码仍由训练模块管理。

`fit_scorer(..., require_oof=True)` 检查候选记录绑定的持出源组与训练源组不重叠：

```python
pool.metadata['oof'] = {
    'held_out_source_group': doc.source_group,
    'trained_source_groups': [...],
}
```

生成器和跨度头各自的训练清单、折分及所有增强视图隔离还需由调度入口绑定；接口检查不能单独证明模型训练过程真实遵守了清单。

拟合接口只接收 `fit`、`train` 或 `oof_fit`。测试、校准和策略选择标签不能进入该接口。训练过程记录实际 loss，不设置期待的效果阈值。训练按文档和对象批次推进，避免保存所有文档的高维对象特征矩阵。

## 3. 校准与搜索前冻结

`fit_calibrators` 仅接收 `calibration`，检查拟合/校准源组隔离，并要求未过采样的自然候选分布。组件与关系分别拟合 Platt logistic；每族必须有正负类，不能以空集或单一类别伪造校准通过。这里明确采用正斜率约束以保持排序，并施加极小数值正则；这是可记录的工程选择。

`score(pool)` 绑定候选池摘要、模型和编码器身份、校准参数摘要。返回映射只读；同池同身份复用同一缓存。合法的低概率保留为低概率，未评分、越界和非有限值保留 `None`。全文编码失败时全池缺分并记录原因，不能自动补 0.5 或 0。是否允许未校准诊断分进入实验由运行入口决定；元数据明确标记 `calibrated=False`。

`score_relations(doc, components, relations)` 提供候选资源裁剪时的完整关系评分，原图可为空。源组提案分仅用于召回排序，不冒充这里的校准概率。

## 4. 跨度与源组提案边界

为了支持词内原生边界，代码把冻结 token 隐状态投射到其覆盖的字符，并在线性边界头前附加 token 内位置和全文位置两个量。BCE 直接监督原生起始字符和末尾字符，输出半开区间 `[start,end)`。这是相对“冻结隐状态上线性起止头”的明确细化；若 tokenizer 根本不覆盖金标边界，拟合会报错而不是改写金标。

默认每侧最多 256 个预测边界进入组合，再按起止概率乘积排序，最多输出 64 个跨度，每跨度至多 64 个编码 token，并保留前 2 个原生类型。有限边界 beam 是显式的召回近似，需要在训练侧覆盖分析中一起登记；不保证枚举全文全部字符区间。保护原图对象不在本模块裁剪，由 `candidates.py` 单独管理。

CDCP JSON 提案按完整源集合及目标去重，默认最多 64 组。无模型分数时使用 0 加规范键确定顺序，不虚构置信度。无效 ID、重复源、目标自引用、不兼容跨度、非法分数使调用失败；不“修复”到金标。候选层再加入相邻 2/3 成员规则组合，合计上限 256，受保护关系另计。模型提示中的连续性是建议，最终选中图的连续性必须由候选/求解层检查。

## 5. 公开接口

```python
encoder = TinyTextEncoder(hidden_size=32, seed=17)  # 仅离线诊断
# encoder = HFTextEncoder(model_id, revision=commit, device='cuda', ...)
scorer = ObjectScorer(encoder, corpus='cdcp')
fit_scorer(scorer, fit_examples, require_oof=True)
fit_calibrators(scorer, calibration_examples)
scores = scorer.score(frozen_pool)
scorer.save('scorer.pt')
scorer = ObjectScorer.load('scorer.pt', encoder)

span = SpanProposer(encoder, corpus='cdcp')
fit_span_proposer(span, train_documents)
proposals = span.propose(input_document)
groups = propose_groups(input_document, predicted_components, independent_hf_generate)
```

`ObjectScorer` 和 `SpanProposer` 默认可训练头位于 CPU。冻结编码器可位于 GPU；如需头在 GPU 上训练，可分别移动 `component_head/relation_head` 或 `boundary_head/type_head`，避免对已量化的共享编码器重复执行整体 `.to()`。

## 6. 校验范围

`tests/test_scoring.py` 覆盖完整对象标签、联合源真子集、词内 offset、拟合参数实际变化、编码器冻结、禁用标签分区、OOF 记录、自然分布校准、源组隔离、缺分、不可变缓存和保存/加载身份。

`tests/test_proposals.py` 覆盖字符边界残差、BCE/类型训练实际执行、无 gold 推理接口、数量和 token 限制、保存/加载、完整源组去重及无效模型 JSON 拒绝。

运行结果由主实验入口另行汇总；本文件的接口描述不代表全量服务器训练或论文数据集效果已经验证。

### 部署候选分布与实际本地验证补充

未裁剪的三折 OOF 池最多检查 50,000 个槽位，可以用于评分器拟合；T0/T1 训练候选可按原生身份取并集并保留各来源记录。校准必须逐生成器保持其实际部署频率，不能把两套池先合并后假称自然分布。`prune_pool_for_calibration` 在不读标注的情况下，用已拟合且冻结的头把每个校准池分别裁至“受保护槽位另计、补充至多 4096”，再汇总自然候选记录拟合 Platt；所有组件均保留。

`scorer.pruning_relation_scores` / `score_relations_for_pruning` 统一返回**未校准** sigmoid 排序信号。部署构池与校准构池调用同一接口，避免不同 Platt 参数在浮点饱和后引入不同并列排序。最终事务效用仍使用校准后的 `score()`，不能把排序信号混同为已校准正确率。裁剪记录绑定原始头身份、原池摘要、上限和实际数量。

策略网格预先规定只用 T1 的独立 OOF 策略池选择，冻结后共同应用于 T0/T1；不先合并两个生成器的候选与初始图。该选择需作为实验协议披露，也不保证对 T0 与 T1 的误改风险相同。

本地除了 TinyTextEncoder 的实际梯度更新，还验证了一个临时创建的单层随机 BERT：通过正式 HF `AutoModel` 加载本地权重、保留 native offset、冻结编码器并运行对象评分。该检查是 HF 软件路径验证，不是预训练模型效果或论文结果。
