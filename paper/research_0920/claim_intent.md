# 本轮研究结论的主张边界（综合报告撰写前）

## Material Passport

- Origin Skill: academic-research-suite
- Origin Mode: bounded literature synthesis + experiment interpretation
- Origin Date: 2026-09-20
- Verification Status: ANALYZED
- Version Label: M-0920-feasibility-01

本轮不运行完整同行评审面板；评价是单一助手的研究判断，NOT_CALIBRATED。用户确认的目标是“两项可独立论证的论文创新、以 CCF B 类会议论文的研究说服力严格自查”，未指定具体会议/轨道；不声称存在统一的 CCF B 分数或达到任一会议录用线。

|主张 ID|计划主张|证据种类/指向|禁止扩大解释|
|---|---|---|---|
|C1|结构保持增强已有直接 AM 近邻；QOS 不显式输入关系，为局部关系条件增强留下需对照验证的差异|文献：bao2025qos，§4.1|不得说首次结构增强；未找到同方案不等于查新证明|
|C2|固定预算候选池在本轻量模型上有较高精确跨度覆盖|实验：0920-feasibility-run-01，两个 summary 的 recoverability|不是最终模型召回；不是可执行动作闭包、F1 或总体上界|
|C3|当前原子动作的可达性明显低于池覆盖，尤其 CDCP 的过度分割|保存预测的事后审计：overlap 数量分布|不是更强生成器或多步/聚簇事务的失败证明|
|C4|总体 AUC 和少量 F1 增益不能证明新评分能主动恢复组件；实际选择均为删除|实验：edit_discrimination / calibrated_policy / same_threshold_without_deletion|不能据此宣称评分器全面成功或协同机制成立|
|C5|条件关系诊断不等于错误端点下的端到端修正|协议、原生 CDCP 数据和 supplemental scorer|不使用条件 F1 冒充论文成绩|
|C6|两个创新作为研究方向可区分，但当前证据不足以认定两者已达到目标质量|C1–C5、0915 正文贡献与 0918 设计|不保证毕业/录用，不否定作者另处未提供的真实实验|
|C7|建议继续一次受限的神经模型验证，先修正动作可达性和好/中性/坏决策问题，再决定是否全量投入|研究建议，非已完成事实|不能写成新方法已有效；不能自动新增第三创新|

文献键：bao2025qos = EMNLP 2025 2025.emnlp-main.1351；sun2026weak = 2026.fever-1.1；das2025aasp = arXiv:2510.16363v1；baba2026gate = arXiv:2606.16047v1；tran2026instruct = 2026.argmining-1.11；niculae2017 = P17-1091；xiao2026argus = PMLR 337/xiao26a；guo2017 = PMLR 70/guo17a。

实验 ID：0920-feasibility-run-01；实际命令与哈希位于 results/run_manifest.json。执行成功但未独立重训复现，因此不是 VERIFIED。
