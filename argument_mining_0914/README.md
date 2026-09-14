# 0914 论辩挖掘实验项目

这是依据论文新建的参考实现，不是原实验代码的恢复，也没有复现论文中的 83.71、64.83 等分数。项目可执行数据转换、训练、增强、候选生成、评分、局部修正及评价；目前验证限于合成样例和随机初始化的小模型。未下载数据集或 Qwen 权重，未运行 AAEC/CDCP 正式实验。

## 先运行离线检查

在本项目目录执行；当前机器已配置独立 `.venv`，没有修改系统 Python。

```bash
source .venv/bin/activate
python -m am --help
python scripts/validate_project.py
python -m am demo --out runs/my_first_synthetic_demo
```

`demo` 使用固定的人工样例和预设回复，只演示流程；其中的分数不能写入论文实验表。输出目录必须不存在，程序不会覆盖旧 run。检查结果见 `validation/test_report.json` 和 `validation/test_output.txt`。

在另一台机器上安装：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[ml]'
python scripts/validate_project.py
```

核心数据/评价代码只用 Python 标准库；模型路径使用 PyTorch 2.8.0、Transformers 4.57.6、Safetensors 0.7.0。此次实际环境另记录在验证报告中。CUDA、驱动和显存是否足够需要在目标服务器试跑，不能由本机小模型测试保证。

## 目录与入口

|位置|内容|
|---|---|
|`am/data.py`、`schema.py`|原始语料转换、严格 Schema、坐标、划分与泄漏检查|
|`am/model.py`、`train.py`|冻结骨干、全局/因果条件 LoRA、连续提示、辅助头、训练和检查点|
|`am/augment.py`|训练集局部子图改写、全文槽位回填、结构及语义筛选|
|`am/pipeline.py`、`repair.py`|五种推理策略、固定候选池、混合评分、四类局部动作|
|`am/backend.py`|验证缓存、模型调用与 token 预算、失败记录|
|`am/metrics.py`|精确匹配 micro-F1、粗标签迁移、候选 Oracle 诊断|
|`configs/`|19 份具名的新实验配置；不是旧结果的配置恢复|
|`docs/IMPLEMENTATION.md`|算法实现选择、与原稿差异、评价口径和限制|
|`docs/EXPERIMENT_MATRIX.md`|建议实验矩阵及公平比较要求|
|`tests/`|纯逻辑测试和实际小模型前向/反向/保存加载测试|

## 准备真实数据：必须提供显式划分

自行取得有使用权限的 AAEC/CDCP 数据。项目不捆绑数据、不下载数据，也不猜测原论文划分。创建 JSON 划分文件，列出真实文档 ID，三个集合必须非空且互斥。例如以下只是格式示意，不是可用于正式实验的划分：

```json
{"train":["真实训练文档ID"],"dev":["真实验证文档ID"],"test":["真实测试文档ID"]}
```

AAEC 接受同目录的 `.txt` 和 BRAT `.ann`，ID 为文件名去扩展名。CDCP 接受 `.txt` 和 `.ann.json`，JSON 方言详见实现说明。

```bash
python -m am prepare --corpus aaec --raw-dir data/raw/aaec --splits data/aaec_splits.json --out data/processed/aaec
python -m am prepare --corpus cdcp --raw-dir data/raw/cdcp --splits data/cdcp_splits.json --out data/processed/cdcp
python -m am audit-data data/processed/aaec/train.jsonl data/processed/aaec/dev.jsonl data/processed/aaec/test.jsonl --out data/aaec_audit.json
```

CDCP 若包含多前提区间，默认拒绝并提示人工决定。`--multi-premise expand` 会显式展开为逐前提二元边，改变表示，必须单列协议，不能自动声称与原表或外部基线对齐。转换器目前只通过构造样例测试；首次导入真实语料后，要抽样核对原文、跨度和关系，确认实际发布格式受支持。

训练/验证/测试不允许同一 `source_id` 或完全相同文本跨集。模糊近重复、主题泄漏和预训练污染不由这项检查排除。

## 准备本地模型并训练

从 [Qwen 官方模型页](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) 获取相应文件并遵守许可，放到 `models/Qwen2.5-7B-Instruct`，或修改配置的 `model.path`。程序仅从本地读取，`trust_remote_code=False`；不会调用付费 API 或自动下载模型。

除 `cpu_inspection.json` 外，具名配置以单卡 CUDA/bfloat16 为目标。学习率、目标层、上下文长度等是本次的新建议值，需要验证集调试；CPU 配置只适合检查和小模型，不是建议用 Mac CPU 训练 7B。

```bash
python -m am config --config configs/aaec_full_br_k3.json
python -m am train --config configs/aaec_full_br_k3.json --train data/processed/aaec/train.jsonl --dev data/processed/aaec/dev.jsonl --out runs/aaec_full_s17_train
```

`best/` 只保存可训练参数，不复制骨干权重。按验证集生成损失选择检查点，不使用测试集。最大上下文 8192 是新实现的限制；超长训练样本报错，推理调用失败会记录，不静默截断。应先检查所有样本长度和显存，再启动完整训练。

训练不支持自动断点续训、分布式训练或量化。生成端采用逐 token 无 KV-cache 的参考路径，便于核对状态门控，但速度较慢；不要把它直接作为吞吐量优化实现。建议先在少量真实训练/验证样本上检查输出格式和资源消耗。

## 推理、复用候选池、评价

同一 Full 检查点先生成 K=3 候选并使用序列概率选取，再复用这个候选池运行重排序与 BR：

```bash
python -m am infer --config configs/aaec_full_logprob_k3.json --checkpoint runs/aaec_full_s17_train/best --input data/processed/aaec/test.jsonl --out runs/aaec_logprob_s17
python -m am infer --config configs/aaec_full_rerank_k3.json --checkpoint runs/aaec_full_s17_train/best --input data/processed/aaec/test.jsonl --cache runs/aaec_logprob_s17/candidates.jsonl --out runs/aaec_rerank_s17
python -m am infer --config configs/aaec_full_br_k3.json --checkpoint runs/aaec_full_s17_train/best --input data/processed/aaec/test.jsonl --cache runs/aaec_logprob_s17/candidates.jsonl --out runs/aaec_br_s17
python -m am evaluate --gold data/processed/aaec/test.jsonl --predictions runs/aaec_br_s17/predictions.jsonl --run-manifest runs/aaec_br_s17/manifest.json --out runs/aaec_br_s17/evaluation.json
```

候选缓存核验文档、模型/适配器、生成配置、随机种子、标签空间和候选数。缓存节省本次实际调用，但其生成成本仍占逻辑实验预算；不要把缓存后的时延当成完整端到端时延。`status=ok` 表示产生了可评价图，不代表结构合法或语义正确；另看 `structurally_valid`。解析失败、验证失败均保留文档，不从评价分母中删除。

每个 run 保存配置/代码/数据哈希、模型身份、原始候选、动作记录、预测及成本。新实现默认生成器和验证器共享同一已加载检查点；这是不同提示的两次调用，不是独立模型验证。

跨域实验仍加载 AAEC 检查点、输出 AAEC 源标签；只在评价时把双方映射为粗类型和有向 Link：

```bash
python -m am infer --config configs/aaec_to_cdcp.json --checkpoint runs/aaec_full_s17_train/best --input data/processed/cdcp/test.jsonl --out runs/aaec_to_cdcp_s17
python -m am evaluate --coarse --gold data/processed/cdcp/test.jsonl --predictions runs/aaec_to_cdcp_s17/predictions.jsonl --run-manifest runs/aaec_to_cdcp_s17/manifest.json --out runs/aaec_to_cdcp_s17/evaluation.json
```

`evaluate` 的 `--coarse` 必须显式提供；它不会仅根据配置文件名切换指标。

## 训练增强

```bash
python -m am augment --config configs/augment_structure.json --input data/processed/aaec/train.jsonl --out runs/aaec_aug_structure_s17
python -m am augment --config configs/augment_plain.json --input data/processed/aaec/train.jsonl --out runs/aaec_aug_plain_s17
```

示例使用本地基础模型进行增强，不读取 dev/test。结构版在提示中提供局部边；plain 版隐藏边但保持相同组件槽位和后续筛选，用来隔离结构条件的作用，不能等同于已发表方法的复现。每种增强得到的 `train.jsonl` 包含原始及最终保留的新样本。语义筛选由模型判断，不能替代人工抽检；应报告最终保留率而非只统计局部通过率。

比较 no-aug/plain/structure 时固定配套模块、推理策略、种子和更新预算；plain 与 structure 应匹配最终接受样本量。`training.max_optimizer_steps` 可设相同正整数上限，`early_stopping` 可关闭，但还必须检查实际 `optimizer_steps` 是否相等，以及每次更新的有效样本/token 数。仅设置上限并不能证明 FLOPs 相等；同样 epochs 更不代表相同训练预算。

## 多随机种子及交付边界

建议新实验预先固定 17/29/43/71/101 等种子，各自训练和推理；这是新计划，不是原稿使用的种子。编辑一份配置中的 `seed` 后，训练和推理须一致。汇总实际评价报告：

```bash
python -m am summarize runs/aaec_br_s17/evaluation.json runs/aaec_br_s29/evaluation.json runs/aaec_br_s43/evaluation.json --out runs/aaec_br_summary.json
```

程序要求种子不同、非种子配置/数据/评价协议一致，报告均值和样本标准差（ddof=1）。不同种子不是统计独立性的证明；该命令不做显著性检验。旧稿“±”含义仍未知。

尚未实现或验证：外部 FLAN-T5/RoBERTa 基线、真正语法约束解码、Self-Refine、Llama 验证器、金标准组件替换 Oracle、节点 Insert、非法中间状态逐步修复、真实数据端到端结果、目标 GPU 上的效率测量。完整结果表需在这些证据补齐后重建，不能把配置文件存在当成实验已完成。
