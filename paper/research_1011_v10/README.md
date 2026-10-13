# 1011 v10 冻结实验包

本目录为96篇新增文档的原始发布文件、转换、盲输入、Luna输出、分数、候选、求解执行、严格评价和重放。原始输出不被重放覆盖。文稿及中文报告位于包根目录，历史148篇的完整独立证据另见既有“1011_Luna扩样分析证据包.zip”。

## 身份与依赖

- 模型任务共43项：12项预测、31项评分；请求gpt-5.6-luna/low，全新无历史上下文，模型实际快照及采样参数未暴露。逐任务路径见两实验的model_execution_manifest.json。
- 本地实验环境：Python 3.9、NumPy 1.26.4、SciPy 1.13.1；MILP使用SciPy内置HiGHS。run_001/input_freeze.json保存实际平台、版本和代码哈希。
- 原生金标复核复用research_1010_v7_luna/evaluate.py的纯核验函数；CDCP原压缩包位于research_0920/data/cdcp_acl17.zip。二者纳入交付ZIP。
- 文稿制作使用独立的Codex bundled Python、lxml和LibreOffice headless；DOCX保留411个OMML对象。该文档运行环境与实验SciPy环境分开。

## 只读验证

运行包根目录verify_1011_v10_bundle.py可验证交付清单全部文件SHA256，不调用模型、不改结果。两份evaluation_001/independent_recount.json记录另一实现对所有逐篇和汇总计数的核对；evaluation_001/audit.json记录源数据和事务核验。

## 冻结输入重算

仅在完整复制出的临时副本中操作，保留收到的原包。将副本内results/evaluation_001、results/replay_001改名为原始备份，然后在包根目录用上述NumPy/SciPy环境依次运行：

```sh
python3 research_1011_v10/evaluate.py research_1011_v10/new_corpora
python3 research_1011_v10/replay.py research_1011_v10/new_corpora
python3 research_1011_v10/recount.py research_1011_v10/new_corpora
python3 research_1011_v10/evaluate.py research_1011_v10/cdcp_scoring
python3 research_1011_v10/replay.py research_1011_v10/cdcp_scoring
python3 research_1011_v10/recount.py research_1011_v10/cdcp_scoring
```

repair.py的vendor路径是可选的本地依赖搜索路径；不随包分发平台相关二进制。没有该目录时应在当前Python环境安装相同NumPy/SciPy。不要为了重放重新调用Luna。准备脚本保留作为生成协议的证据，完整重做历史抽样另依赖先前工作区；本包主要支持已冻结96篇的评价与执行重放。

## 解释范围

新语料的初始化失败以所有方法空预测计数，金标保持分母；历史148篇MCR保留原图，协议不合并。显式评分所有字段齐备不能证明模型已完成可靠逐对象思考。候选缺失、格式失败、预测误差和求解器执行分别报告。原稿的模拟主成绩仍非真实训练结果；此包不包含正式训练、完整BR-J或同目标全局系统比较。
