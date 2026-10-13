# v13数据与复算说明

本目录数据身份：真实训练语料与标注 + 使用金标构造的主预测图 + 明确模拟的验收补充 + 实际运行的构造输入求解 + 既有Luna输出案例。没有新增目标模型训练、Luna调用、真人审核或GPU测量。

## 环境

实际使用Python 3.9.6、NumPy 1.26.4、SciPy 1.13.1。ZIP不含Python环境、vendor二进制或模型权重。脚本先尝试研究目录中的vendor路径，路径不存在时使用当前Python环境的已安装库。SciPy需包含milp/HiGHS。

## 内容

- data：原生训练文本及金标、重复组、排除清单和字符坐标规范化。
- simulation：67425张图、对象宇宙、134850行计数、结果、端点链及清单。gold_used_in_construction=true。
- acceptance_scenario：模拟审核、学习曲线、分数、时延、假定实现状态以及E1—E8。PASS_SIMULATED不是真实验收。
- mechanism：4组构造输入及16条实际求解结果；共26次求解调用。局部F1不是全文模型成绩。
- cases：10个来源案例和4个同批四格案例；包括全图、分数、原文和来源哈希。

## 复算

请解压到独立副本，保留根目录结构。在副本根目录执行以下步骤。生成器会覆盖v13输出；不要在需要保持原证据的目录直接重跑。旧来源材料保持不改。

```sh
python3 research_1011_v13/prepare_corpus.py
python3 research_1011_v13/generate_graph_scenario.py
python3 research_1011_v13/supplement_acceptance.py
python3 research_1011_v13/run_mechanism_fixtures.py
python3 research_1011_v13/build_cases.py
python3 _revision_1011_v13/derive_analysis.py
python3 _revision_1011_v13/compose_content.py
python3 _revision_1011_v13/content_audit.py
```

前三类模拟在相同依赖下可重复生成；实际求解的耗时和时间戳会随运行变化，若正文记录更新的耗时，其文件哈希也随之变化。只复核现有计数与来源，可直接运行content_audit.py，无需重跑求解或模型。

历史引用表保留上版来源身份，当前包不会重新联网核对文献。历史通用代码可能含已退出本稿研究范围的其他语料支持分支；这不表示v13重新引入它们。
