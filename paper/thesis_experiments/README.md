# 论辩结构抽取：可靠增强训练与依赖闭合推理实验代码

本目录把当前论文 v6 的第三章、第四章和两阶段组合实验实现为可执行程序。训练采用真实 PyTorch/Hugging Face 前向、反向与参数更新；结构修正调用真实 SciPy/HiGHS MILP。旧论文中的模拟表格不作为本程序输入，也不会被当成新实验结果。

本次本地验收：**136 项测试通过**；真实 Qwen2.5-0.5B 在一篇 CDCP 训练文档上执行 64 步更新后，自由生成合法完整图，adapter 重载损失一致。这是单样本过拟合诊断，不是测试集效果。详见 [本地验证报告](LOCAL_VALIDATION.md) 和 [版本审查记录](CODE_REVIEW.md)。

后续服务器按 **单卡 24GB、Qwen2.5-7B-Instruct、NF4 双重量化、bf16、gradient checkpointing、单源微批 × 32 次累积** 配置。24GB 是待实测的配置目标；长文档、双视图和候选规模仍可能触发显存或上下文限制。程序显式失败，不静默截断文本或删除测试分母。

## 两个部分分别包含什么

| 部分 | 实现内容 |
|---|---|
| 第三章 | 全局/结论专项 LoRA、可见前缀门控、四向量线索提示、句子 BCE、组件/完整关系辅助头、双侧 JS、源文档归一化、字符坐标输运、完整影响域、semantic unknown、FactorMask/FullFilter 盲审 |
| 第四章 | 原生候选池、独立跨度提案器、CDCP 完整源组提案、三折 OOF 评分训练、分族校准、训练侧策略选择、完整对象固定评分、依赖闭合事务、局部/全局求解、编辑账本及回退 |
| 实验组织 | T0/Heads/NoPair/CompPair/T1、继承 I0 与新 I1、训练/校准/策略/测试分离、种子 17/29/43、原生 TP/FP/FN、配对统计与运行清单 |

**I0 包含 BR-O；G0 只是共同初始图。** `rank --with-i0` 调用 `legacy.py` 的原生 BR-O 新实现，保留已有动态评分及 RemoveEdge、Promote/Demote、Replace、LocalRerun 动作。它不声称复现了历史论文的原始检查点。I1 从相同 G0 开始；不能把 I0 的终态作为 I1 的起点，也不能把 G0 的成绩标为 I0。

## 文件入口

- [服务器完整运行步骤](SERVER_RUNBOOK.md)
- [论文方法与程序对应表](METHOD_MAPPING.md)
- [第三章训练实现说明](IMPLEMENTATION_TRAINING.md)
- [第四章候选/事务/求解说明](IMPLEMENTATION_INFERENCE.md)
- [独立对象评分与校准说明](IMPLEMENTATION_SCORING.md)
- `argrepair/cli.py`：所有阶段命令；`argrepair/workflow.py`：依赖计划与逐阶段执行。
- `configs/local_tiny.json`：随机小模型，离线构造测试。
- `configs/local_qwen05b.json`：真实 Qwen2.5-0.5B、CPU float32、短上下文初调。
- `configs/server_24gb.json`：7B 服务器实验工程配置。

## 本地使用

要求 Python 3.11 或以上。已有环境位于本目录 `.venv`；新机器先安装依赖：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
OMP_NUM_THREADS=2 python -m pytest -q
python -m argrepair --help
```

随机小模型诊断：

```bash
OMP_NUM_THREADS=2 python -m argrepair smoke \
  --config configs/local_tiny.json \
  --out runs/tiny_smoke_001
```

真实小预训练模型初调前，下载并固定版本：

```bash
python scripts/download_model.py \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --revision 7ae557604adf67be50417f59c2c2f167def9a775 \
  --output models/Qwen2.5-0.5B-Instruct
OMP_NUM_THREADS=2 python -m argrepair smoke \
  --pretrained --config configs/local_qwen05b.json \
  --out runs/qwen05b_smoke_001
```

本地 0.5B 与服务器 7B 的模型、头维度、上下文和更新预算不同，初调结果不得并入正式主表。随机 tiny 或随机 mini Qwen2 的测试只验证执行、梯度和接口，不代表预训练模型效果。

默认小模型 smoke 只做一次更新，允许如实记录生成解析失败。复查本次通过结构输出校验的 **单训练源 64 步过拟合诊断**，完成 prepare 后使用：

```bash
OMP_NUM_THREADS=2 python -m argrepair smoke --pretrained \
  --config configs/local_qwen05b_overfit_debug.json \
  --out runs/qwen05b_overfit_debug_001
```

该配置的 `smoke.training_data` 默认为 `data/native_v2/cdcp_train.jsonl`；若 prepare 使用其他目录，先修改该路径。它不接触测试标注，也没有接受的真实增强视图；成对项的执行和梯度由单独的双视图测试覆盖。

## 数据准备

本机历史原始文件位于 `../research_0920/data/`：`aaec_brat.zip`、`aaec_split.csv`、`cdcp_acl17.zip`。程序直接读取指定 ZIP 内容，不执行下载的脚本。

```bash
python -m argrepair prepare \
  --raw ../research_0920/data \
  --out data/native_run_001 --seed 17
```

实际完成的数据准备快照 `data/native_v2/data_audit.json` 中，去重后的训练文档为 AAEC 319、CDCP 580，官方测试分别保留 80、150 篇。字符边界、训练重复文档和任何标注异常均有审计记录。v2 同时保留 AAEC 的原生 Stance 属性，并在增强时同步其组件坐标；当前抽取任务不新增 Stance 预测头。正式使用应从你有权使用的原始语料重新 prepare，并检查本次摘要；分发代码包不应捆绑原始语料、生成的全文 JSONL 或模型权重。

`*_inputs.jsonl` 只含文档 ID、全文和来源信息，推理入口拒绝金标字段；`*_test.jsonl` 仅交给 evaluate。CDCP 一条联合源超边始终是一个完整关系对象。

加载 tokenizer 但不加载模型权重的全量预检：

```bash
python scripts/preflight.py --data data/native_v2 \
  --config configs/local_qwen05b.json --out runs/preflight_qwen05b.json
```

预检对训练数据核查原生图、输入/答案/总上下文和因素数量；测试只读取无标注输入。超长会返回失败清单及非零退出码；这不验证 GPU 显存，也不自动删掉长文档。正式 7B 应改用锁定的服务器配置另跑一次。


## 正式实验入口

完成服务器环境、数据和模型版本固定后：

```bash
python -m argrepair plan --data data/native_run_001 \
  --config configs/server_24gb_locked.json \
  --out runs/paper_001 --corpus both --seeds 17 29 43
python -m argrepair run-plan --plan runs/paper_001/plan.json
```

`plan` 只生成具体依赖计划，不启动训练；`run-plan` 顺序执行，避免同一张卡并发加载多个阶段模型。查看 `plan.json`、`comparisons.json` 后再开始长任务。详细分阶段命令、资源预检、失败处理、续跑边界见 runbook。

## 运行身份与结果边界

每个阶段保存 `manifest.json`、输入与代码摘要、配置、状态、输出摘要和实际耗时；训练另保存损失、梯度范数、实际源数、模型身份及 adapter。推理保存候选池/评分快照、失败原因和事务账本。NoRisk 保留共同接受、合法性、评分与编辑预算，仅将正增量阈值设为 `10 × numeric_tol` 并不沿用开发集禁修开关。Regenerate 默认关闭，只有绑定真实 I1 资源凭证后才进入等预算主要比较。显存峰值只在实际 CUDA 训练时记录。

- 生成器：经过本轮训练的 Qwen 提取模型；辅助分类头属于第三章训练模块。
- 审核器与源组提案器：`chat` 中显式指定的冻结指令模型，以独立任务提示调用，记录原始响应和预算。它们不会自动共享提取模型的 adapter。
- 评分编码器：`encoder` 中独立指定的冻结模型；完整对象评分头另行拟合、校准，不使用第三章语义类别概率冒充正确率。
- “运行完成”表示代码阶段完成；审核可靠性、生成质量、校准质量和论文增益仍由真实语料评价确定。若没有接受增强或没有有效候选，必须保留并解释该结果，不能补造成功样例。

局部与全局第三级破同分规则也明确分开：局部默认最小 `Graph.key`，全局默认按规范对象顺序优先保持 G0；均先最大主效用、再最少编辑。求解超时、仅有可行 incumbent、破同分未完成分别记录，不混称唯一最优。

依赖和基础模型可核对官方资料：[Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)、[SciPy MILP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)、[Transformers bitsandbytes 量化说明](https://huggingface.co/docs/transformers/quantization/bitsandbytes)。运行身份以本地 revision、文件摘要和实际日志为准。
