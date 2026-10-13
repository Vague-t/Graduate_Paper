# AAEC / CDCP 0920 轻量诊断

这是实际执行过的 CPU 预实验，不是正式论文系统，也不是对历史实验的恢复。总体决策见 [0920 审计报告](/Users/channtang/Downloads/paper/0920可行性审计与两项创新评估.md)。

- 输入：公开语料的官方训练部分。
- 模型：稀疏线性 BIO/边界模型 + OOF 候选组件评分器 + 条件关系模型。
- 隔离：拟合、校准、审计按文本分组；无测试集调参。
- 输出：`results/` 中的数值、候选、逐编辑预测、划分及来源哈希。
- 状态：退出码 0，29.03 秒；有收敛警告；未独立重训复现。

## 执行命令

用户批准且实际运行：

```sh
python3 research_0920/run_feasibility.py --datasets aaec cdcp --split train-dev --max-minutes 20
```

脚本使用本目录 `vendor/` 中的 Python 3.9 / macOS arm64 依赖，不修改系统包：numpy 1.26.4、scipy 1.13.1、scikit-learn 1.6.1、joblib 1.5.3、threadpoolctl 3.6.0。其他平台应在独立环境安装相同版本，不能复制本机二进制库使用。

为防止静默覆盖，存在 `results/run_manifest.json` 时脚本会拒绝重复执行。需新实验时先明确新输出位置/版本；不要删除原结果来隐藏失败尝试。

## 数据文件

`data/aaec_brat.zip`、`data/aaec_split.csv`、`data/cdcp_acl17.zip`。数据来源及下载限制见[运行前协议](/Users/channtang/Downloads/paper/research_0920/预实验协议.md)。脚本只从 ZIP 读取指定训练文件，不解压或执行下载代码。

`.gitignore` 排除了原始数据、第三方依赖和缓存。报告、脚本与数值结果可供审阅；没有自动 commit/push。预测记录仅含位置、标签与分数，不复印全文语料。

## 不要误读结果

1. +128 候选跨度覆盖约 96%，不等于组件 F1，也不等于动作可恢复率。
2. 主选择策略全部是删除，TP 没增加；不能据此声称恢复了缺失组件。
3. CDCP 的初始模型很弱，不能外推正式模型的错误分布。
4. 关系结果使用 gold 端点，仅单前提子任务；不是完整 CDCP 端到端关系成绩。
5. `posthoc_integrity_audit.json` 是保存结果的事后重算，不是第二次训练实验。
