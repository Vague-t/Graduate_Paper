# 0914-v3 定向研究记录

日期：2026-09-14。范围：查找与局部结构增强、候选图修订及统一任务训练直接相邻的公开研究；不是系统综述或穷尽性新颖性认证。查询不包含未公开稿件全文，仅使用公开研究主题词与论文标题。

检索式包括：argument mining "structure preserving" augmentation claim 2025 2026；argument mining graph refinement repair candidates 2026；"Structure-Preserving Document-Level Data Augmentation"；"End-to-End Argument Mining through Autoregressive Argumentative" 2026。

|来源|本轮实际核对范围|处理|
|:---|:---|:---|
|[Sun等 FEVER 2026](https://aclanthology.org/2026.fever-1.1/)|官方摘要、作者、会议、年份、页码1–12及DOI|加入正文，只比较伪标注降噪与结构条件增强的任务路径，不借用其性能作为本文结果|
|[Xiao与Li UAI 2026](https://proceedings.mlr.press/v337/xiao26a.html)|官方摘要与书目信息，PMLR 337:7536–7551|加入正文，区分形式语义下的最小代价修复和本文启发式抽取修正；不声称本轮验证其定理证明|
|[Savigny与Yun AMELIA](https://journals.sagepub.com/doi/10.1177/19462174251413169)|期刊摘要、作者、2026-01-28上线时间、17卷1期、DOI|加入正文，只说明统一19个数据集和三种训练策略；页码未补造|
|[CoDa](https://aclanthology.org/2024.findings-naacl.238/)、[DENIM](https://aclanthology.org/2024.findings-acl.689/)、[课堂LLM-refine](https://aclanthology.org/2025.aimecon-main.13/)|官方论文页定向核查|继续作为邻近工作，未复现实验|
|[AASP arXiv](https://arxiv.org/abs/2510.16363)及[作者主页](https://fac.iitg.ac.in/anand.ashish/publications.html)|公开摘要、版本与作者公开的IJCNN 2025列表|原稿明确引用arXiv v1，保留该版本；没有把会议元数据与未读会议全文混成一个引用|
|[Structure-Preserving Document-Level Data Augmentation via Discourse Parsing](https://openreview.net/pdf?id=7XjHpd5IaQ)|公开匿名稿首页与摘要，涉及篇章关系保持及摘要/问答|作为追踪线索；本轮未确认作者和最终发表版本，没有冒充具名正式发表论文纳入文献表|

已有30篇文献在本轮未全部重新逐篇审计，新增3篇后按全文首次引用重排为33篇。新增正文均用已读摘要作为locator；未声称阅读全文、人工已读、来源证明本文新颖性或完成外部专家独立评审。

方法核对另以本地am/augment.py、repair.py、pipeline.py、schema.py、metrics.py和config.py为依据。构造例脚本直接调用参考实现，固定边判断，不加载模型、不调用外部API。
