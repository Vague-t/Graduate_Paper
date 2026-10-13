# 1010-v8 诊断统计与复算材料

本包对应论文附录D.3的六张新增统计表。数据身份：既存2026-09-20 CPU诊断的事后重分析；不是目标LLM实验，也不是BR-J、全局ILP或训练增强效果。

六份CSV分别提供逐文档错误、端点分组、预算覆盖、提议组成、策略结果及对象变化。diagnostic_supplement.json提供输入文件哈希、重采样口径、完整汇总和校验结果。没有新增真实案例叙述。

在原paper工作区保留research_0920/data、research_0920/results及原诊断脚本和协议，解压本包后，使用具有NumPy的Python运行：

    python3 _revision_1010_v8/analyze_saved_diagnostics.py

脚本只提取并执行原模块的纯数据读取及计数函数，不导入训练模块，不拟合模型，不调用外部服务，不执行求解器。输出写入_revision_1010_v8，既存输入保持只读。原语料和既存运行记录未重复打包；缺少输入时不能独立复算。

execution_evidence_inventory.json列出已有有限检查及尚未执行的目标系统验收；输入名称对应先前方案，不代表字段已完成绑定。final_audit.json和visual_review.json仅记录文档与复算交付检查，不是研究有效性证明。
