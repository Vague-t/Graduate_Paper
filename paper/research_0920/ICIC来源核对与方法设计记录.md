# ICIC 来源核对与本轮方法设计记录

日期：2026-09-20。对应交付：../0920基于ICIC2026的双创新方法设计.md。

## 1. 本轮范围

从“以现有诊断决定是否继续投入”转为作者本轮要求的“假设关键实验支持，设计两项有实质增量的方法”。未追加模型训练、数据集评测或联网模型调用；未覆盖正文、上传资料或推送仓库。

使用 academic-research-suite 的有界方法蓝图与来源核查规范。主代理阅读指令、原文和已有设计，独立子任务分别核对 ICIC 来源、训练增量和数学设计。这不是外部专家评审或跨模型盲审；判断 NOT_CALIBRATED。

## 2. ICIC 原文核验

- 作者：Chen Tang, Min Peng, Gang Tian；单位 Wuhan University。
- 题名：Improving End-to-End Argument Mining with LLMs via Multi-Candidate Reranking and Bounded Repair。
- DOI：[10.65286/icic.v22i1.76896](https://doi.org/10.65286/icic.v22i1.76896)。
- 出版落地页：[ICIC2026 Posters / Poster Volume I](http://poster-openaccess.com/article_detail.php?paper_id=5295&conf=ICIC&year=2026)。页面标注 Toronto, July 22–26, 2026，页码“-”。不补造页码、不等同于 Springer LNCS 书目。
- PDF：[公开全文](http://poster-openaccess.com/files/icic2026/poster%20I/5295/5295.pdf)。
- 本地：sources/icic_2026_5295.pdf，15 页，SHA256 为 56baabdd086a00c7539a20adc4c99e6bdd996194a2875efffd26bf04ae3130fd。
- 提取文本：sources/icic_2026_5295.txt，SHA256 为 e0253134588636ad047c6164105a5432be484b050bd86d2f87336422d9870d4b。
- 预检：sources/icic_2026_5295.preflight.json 状态 UNAVAILABLE，原因是 PDF 对象偏移警告，三种页数计数均为 15。该状态不被改写为 VERIFIED。
- 实际阅读：主代理读完整提取文本；视觉检查方法公式与动作说明所在第 6、7、8 个 PDF 页面。章节锚为 §4.1–4.4；不把成功提取和局部视觉检查扩展为整份 PDF 版式认证。
- 作者已通过本轮回复确认该题名就是所指 ICIC 论文。

浏览工具访问 DOI/该站失败；来源核查子任务使用命令行跟随公开 DOI 跳转、读取 HTTP 页面并下载公开 PDF 后取得全文。没有绕过登录、付费墙或验证码。该站 HTTPS 连接不可用，HTTP 文件本身的传输不提供 TLS 保护，因此记录文件哈希；哈希保证本地副本可追踪，不证明出版机构身份真实性。

早先“论文严格审阅意见_2026-09-13.md”所述未完成出版信息核验，现在有了新证据。保留历史记录，本文件记录状态更新。

## 3. 真正改变方法设计的发现

1. ICIC §4.4 已有结论专项 LoRA、Cue-aware Soft Prompting 和辅助 BCE，不能重新计作学位论文新增。
2. ICIC §4.3 已能改变组件类型或跨度，故新方案不能以“既改组件又改关系”作为主要区别。
3. 公开原文没有局部结构保持增强方法；训练侧可以从模型专项优化推进到有关系约束的成对监督。
4. 0915 已有边界边事后检查，本轮新增必须具体落在前置完整影响域、NONE 与图对齐损失。
5. 0918 能量的固定候选和原子事务可以继承，但本轮将 Split/Merge 纳入有界集合替换，并用完整对象正确性计数解释接受标准。
6. 旧方案的编辑惩罚不再进入主势函数，避免仅靠回到初始图附近取得增分；成本单列硬预算。
7. 不加入临时的保形风险保证。F1 条件分析需要逐次误差界，普通校准不能提供该保证。

## 4. 本轮文献核查范围

|来源|本轮核查|实际用途|
|---|---|---|
|[Bao 等，EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1351/)|出版页、PDF §4.1 及相邻方法内容|结构保持增强直接近邻；关系不显式输入的准确边界|
|[Stab & Gurevych，2017](https://aclanthology.org/J17-3005/)|出版页；沿用既有方法阅读记录|联合类型/关系优化不是新思想|
|[Niculae 等，2017](https://aclanthology.org/P17-1091/)|出版页；沿用既有记录|结构化预测及 CDCP 基础|
|[Sun 等，FEVER 2026](https://aclanthology.org/2026.fever-1.1/)|出版页和摘要；方法范围沿用 0918/0920 阅读记录|训练期边界改进和关系去噪近邻|
|[Caputo 等，EACL 2026 Findings](https://aclanthology.org/2026.findings-eacl.272/)|出版页，摘要级|分割近邻，不据此断言其没有任何未读机制|
|[Lipton 等，2014](https://arxiv.org/abs/1402.1892)|作者预印本元数据和摘要；本轮 F1 恒等式独立代数推导|避免把已有 F1 阈值思想认作原创；不直接移植其全部假设与结论|

方法：从精确题名、作者及 DOI 检索发现来源，再读取一次来源。文献间的差异属于限定任务/条件下的比较，不是互相矛盾的实验结论；上述新颖性定位是方法建议，仍需作者确认，不是穷尽查新。

主要检索式：

- "Chen Tang" "2026" "ICIC"
- "Tang" "argument mining" "ICIC" 2026
- "Improving End-to-End Argument Mining with LLMs"
- "Improving End-to-End Argument Mining with LLMs via Multi-Candidate Reranking and Bounded Repair"
- "10.65286/icic.v22i1.76896"
- "Chen Tang" "Multi-Candidate"
- Lipton Elkan Narayanaswamy 2014 optimal threshold F1 half optimal F1 calibrated probabilities arxiv

## 5. 数学与方法交叉检查

本轮以推导和构造例检查，未把它们包装为新数据实验：

- 改写映射限定为组件 ID/端点映射，不是 token 双射。
- 一致性约束辅助因素，不声称整个生成器严格等变。
- q_R 必须包含错误端点下的完整关系正确性，不能用 gold-conditioned 关系概率替代。
- 有限终止依赖固定状态势函数与严格增长，不是任意编辑头输出正值。
- 局部差值精确性依赖固定评分条件与完整依赖闭合。
- F1 公式分别用于组件与关系 micro-F1；不混用宏平均和两个任务的组合分。
- 成组替换例采用取值合法且与合法图分布相容的边际概率。
- 局部搜索不能理论性战胜相同目标下充分求解的全局 ILP。
- 主保守门可能拒绝真正有益但评分不确定的动作；这是需测量的代价。
- 最后一次独立检查发现并补齐 RelationOnly：组件不变时仍可通过显式关系种子修复边，并将纯关系成本计入预算；相同规则扩展至超边。

## 6. 交付与未改动项

新增方法设计、主张登记、本文记录与公开来源副本。report_0915_v1.md/docx、0918 设计及 0920 实验结果不覆盖。源数据与模型成绩不改写。

作者下一步最值得核准的是：方法定位是否接受、公开 ICIC PDF 是否最终版本，以及正式 CDCP 关系评价协议。获得这些确认后可以进入新方法正文与工程实现，而不再沿旧创新表述继续补丁式扩写。

## 7. 作者澄清后的归属修订（方法蓝图 v1.1）

作者明确：ICIC 是本人近期成果，可以作为学位论文创新的一部分基础。据此纠正前版将“ICIC 已有”与“不能算学位论文创新”混同的表述。

- 学位论文的两项完整贡献可以包含 ICIC 中属于作者本人完成的原创工作；不自动要求会议成果之外再新增两项完整创新。
- 原 ICIC 结论组件优化纳入第一项的前期基础；MCR-BR 纳入第二项的前期核心，而不只作为外部基线。
- “不能重复计算”限定为不能将已有机制误标成相对 ICIC 的新增、不能拆同一工作凑数量；不否认其作为学位论文研究内容和贡献的资格。
- 保留原创性比较、引用前期成果、说明合作分工与结果版本的要求；不据此认定武汉大学具体制度或保证毕业。
- 修订蓝图第 1、2、5、6、10、11 节及总体贡献表述；技术公式、数据、实验结果及现有论文正文未改动。
