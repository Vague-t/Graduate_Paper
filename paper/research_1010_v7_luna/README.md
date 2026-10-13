# AM-LUNA-20261010-001 复算说明

主记录：1011_v7_Luna真实预测与联合修正尝试记录.md；逐例记录：1011_v7_Luna逐例标注与修正轨迹.md。原始模型输出、分数和结果不可覆写。

## 环境

原运行：macOS arm64、Python 3.9.6、numpy 1.26.4、scipy 1.13.1。脚本优先查找相邻research_0920/vendor，否则使用当前Python环境已安装的相同依赖。没有重新安装环境。

在解压后的父目录运行：

```sh
python3 research_1010_v7_luna/test_repair.py
python3 research_1010_v7_luna/replay.py
```

replay.py只读冻结候选和分数，不调用模型、不读取金标；核对最终图及接受索引，新增带时间戳的重放记录，不覆盖run_001。浮点库、MILP版本或资源变化可能影响耗时及限时下的结果。原始记录以results/run_001为准。

evaluate.py包含独立的原始标注读取与轨迹审计；已生成results/evaluation_001，默认拒绝覆盖。要重新生成同名评估，在临时副本中移走该评估目录，再运行evaluate.py；不会重跑Luna或修改预测。原生标注审核需要相邻research_0920/data中的aaec_brat.zip、aaec_split.csv、cdcp_acl17.zip。

不要直接重新运行prepare_data.py、graph_core.py或repair.py覆盖既有数据。它们含防覆写检查。prepare_data.py另依赖早期research_0920/run_feasibility.py及来源清单；交付包保留其源码用于追溯，但使用已冻结blind_inputs即可复算本轮，不必重新抽样。

## 文件组织

- blind_inputs：模型收到的16篇原文；raw_predictions：真实生成输出。
- prompts：任务提示原文与评分指令；model_dispatch_manifest.json：模型覆盖与分配。
- candidate_pools.json / scoring_inputs / scores：固定候选及真实模型评分；缺省关系0.05是预先声明的粗略规则。
- evaluation：另存的原始标注与来源；results/run_001：32次修正的完整轨迹及前后冻结清单。
- results/evaluation_001：严格指标、候选覆盖、逐对象恢复/损失、独立核验。
- logs：测试、实际修正、评估和重放终端记录。

ZIP包含本轮材料及核验所需的3个原始数据文件，不包含Python依赖。主记录中的绝对本地链接适合原工作区；移至其他机器后按文件名和上述相对路径打开。包内SHA256SUMS.json核验字节完整性。生成模型的快照、随机种子、temperature和底层token数未知，因此“可重放”指冻结预测与分数后的确定性流程，不保证重新调用Luna会产生相同输出。
