# 本地验证报告（2026-10-13）

本报告对应当前实验代码，论文正文没有修改。代码快照摘要：`7e00d89e8fdda3ce780e84926aa09517d6f41784644c81799b5a89c75d30906e`；逐文件摘要见 `validation/source_snapshot.json`。

## 已执行结果

| 验证 | 实际结果 | 证据 |
|---|---|---|
| 完整测试 | 136 passed，0 failures/errors | `validation/pytest.txt`、`pytest.xml` |
| 两种语料随机 tiny 端到端 | 真实优化器更新、构造双视图、评分/校准优化、跨度提案、六条修复路径、账本回放通过 | `runs/tiny_e2e_20261012_final` |
| 原始语料读取 | AAEC 319/80，CDCP 580/150 篇；CDCP 完整多源关系、词内字符边界及 AAEC Stance 属性保留 | `validation/data_audit.json` |
| 全文长度/因素预检 | 1,129 篇；最大输入 763、训练输出 862、总长 1,524 token，最大因素数 2,438，无溢出 | `validation/context_preflight.json` |
| 真实预训练模型 | Qwen2.5-0.5B，CPU float32；1 篇官方训练文档，64 次参数更新 | `validation/pretrained_report.json`、`pretrained_training_log.jsonl` |
| 自由生成与重载 | 输出 2 个组件、1 个关系，56 token、EOS 正常结束，结构校验通过；重载损失一致 | `validation/pretrained_generation.json` |
| 依赖与编译 | pip check 无破损依赖；Python 源码编译通过 | `requirements-lock-local.txt`；实际命令日志 |
| 服务器计划 | 双语料、3 个 seed，生成 573 个有序阶段（含内部准备）；未启动服务器计算 | `runs/server_plan_24gb_reviewable/plan.json` |

本机使用 0.5B 的实际分词器做预检，服务器仍应对下载后的 7B 分词器重新运行。上述 token 数不是显存测量。

## 小模型诊断的解释

使用官方训练文档 `cdcp_00785`，生成损失由 0.83787006 降至 0.00030430；保存重载后为 0.00030430。该样例已被训练，合法输出不能作为泛化能力、测试集 F1 或方法增益证据。

最初 1 步、8 步诊断的自由生成未通过解析，原始记录保留于 `validation/diagnostic_history.json` 及对应 runs 目录。后续 64 步过拟合诊断才通过完整图输出校验。早期冻结评分 metadata 序列化缺陷也保留在失败记录中，修复后已有专门回归测试。

此真实模型调试没有接受的增强视图，成对项为零。完整成对项、掩码、双侧梯度和原文/变体归一化通过独立构造双视图和随机 mini Qwen2 HF 测试验证。评分/跨度的真实模型接口使用训练标签构造候选进行调试，未进行自然候选校准质量评估。

## 尚需服务器实际完成

单卡 24GB 配置已经提供，但 CUDA、bitsandbytes、峰值显存尚未在本机验证。需要按 `SERVER_RUNBOOK.md` 运行短样本和最长样本/双视图负载检查，再执行完整 OOF 与最终训练。正式主表、置信区间、审核接受率、风险与成本均须由这次服务器运行生成。

默认计划每语料 6 项主要比较。Regenerate 实现了预算计费和验证入口，但在真实 I1 逐调用资源凭证齐备前关闭；启用并通过匹配后才扩为每语料 7 项（共 14 项）。外部论文系统和历史检查点不因本代码测试通过而视为已复现。

代码包不包含虚拟环境、模型权重、原始/全文语料或服务器训练结果。工作目录保留本机调试 checkpoint，压缩包通过下载/prepare 命令恢复相应依赖。
