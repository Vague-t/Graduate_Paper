# 0914定向文献核查记录

日期：2026-09-14。范围：围绕现有论文的贡献定位与Related Work补充公开研究，不开展系统综述，不上传论文全文，不调用外部论文改写服务。

检索主题：2025—2026 argument mining / end-to-end / large language models；结构与数据增强；candidate / refine / repair；cross-corpus generalization；中文论辩资源。采用公开网络检索，并优先打开ACL Anthology、AAAI出版页及作者arXiv版本。对Cabessa、关键短语、FOL-AM和Tran论文查阅方法部分确认输入条件，避免由摘要中“end-to-end”或“joint”字样推定与本文同口径。

纳入9篇，见new_references.json。8篇属于2025—2026年，MT-AM（2022）作为缺失的重要直接研究补入。既有DENIM（2024）保留并加强差异解释。旧21篇沿用0913核查记录，不声称本轮再次通读全部原文。

关键修正依据：

- Cabessa §2.2（PDF第2页）：任务为ACC/ARI/ARC等，不能把其分类成绩称为本文的跨度精确匹配F1。
- Das关键短语 §1及§3（PDF第1、3—4页）：组件跨度给定，提取关联组件对的概念联系，追加到目标ANL；不是普通结论词表。
- FOL-AM §1—2（PDF第1—2页）：明确预分割组件；多跳规则推理不能与本文逐边判别等同。
- Tran §4.2（PDF第3—4页）：四种LLM分割加两种整话轮候选，再选六者之一；说明多候选论辩判断已存在，但不同于整图BR。
- ARGUS：AAAI官方条目明确Demonstration Track；不能列作新修正算法或全面性能突破。
- AASP：实际访问arXiv v1，页面注明accepted version/to appear IJCNN 2025；不自行补会议DOI和页码。
- Feger：摘要限定17个英文句子级数据集，作为泛化风险依据而非整图系统实验证据。

未纳入：仅第三方介绍而未完成原始论文关键核查的条目；会议信息不明确的OpenReview材料；仅方法思想相似但非论辩抽取的通用图推理/自验证预印本。未声称这些论文无价值或不存在，仅未用于本轮定向更新。

新文献不产生新的实验基线成绩；所有正文比较为机制与任务边界比较。引用编号按首次出现重排，保留ref slug与章节定位注释，Word中隐藏这些机器可追踪注释，仅显示数字引用和文末来源链接。
