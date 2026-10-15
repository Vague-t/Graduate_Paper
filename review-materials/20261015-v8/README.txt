硕士论文完整审阅材料｜当前基线：2026-10-15 v8

推荐直接读取已经展开的 materials/ 目录，不必先下载或解压ZIP。
共175个文件，包含最新v8、学校模板、四篇参考成稿、导师PDF与68条原批注、会议摘要与整理、历史稿、历次审阅、图源、技能及校验清单。展开内容逐文件与已发布完整包一致，本轮没有改动论文。

材料入口：
https://github.com/Vague-t/Graduate_Paper/tree/review-materials-20261015/review-materials/20261015-v8/materials

最新v8 Word直接下载：
https://raw.githubusercontent.com/Vague-t/Graduate_Paper/review-materials-20261015/review-materials/20261015-v8/materials/01_%E6%9C%80%E6%96%B0%E7%A8%BF_v8/%E8%AE%BA%E6%96%87_v8_%E6%89%B9%E6%B3%A8%E4%BF%AE%E8%AE%A2%E4%B8%8E%E6%96%B9%E6%B3%95%E5%9B%BE%E9%87%8D%E7%BB%98_%E5%90%AB%E6%A8%A1%E6%8B%9F%E8%A1%A5%E5%85%85.docx

最新v8 PDF预览直接下载：
https://raw.githubusercontent.com/Vague-t/Graduate_Paper/review-materials-20261015/review-materials/20261015-v8/materials/01_%E6%9C%80%E6%96%B0%E7%A8%BF_v8/%E8%AE%BA%E6%96%87_v8_%E6%89%B9%E6%B3%A8%E4%BF%AE%E8%AE%A2%E4%B8%8E%E6%96%B9%E6%B3%95%E5%9B%BE%E9%87%8D%E7%BB%98_%E5%90%AB%E6%A8%A1%E6%8B%9F%E8%A1%A5%E5%85%85_%E6%8E%92%E7%89%88%E9%A2%84%E8%A7%88.pdf

新agent使用：先读 materials/00_先读说明.txt，再使用本目录 REVIEW_PROMPT.txt。
学校规范与四篇成稿位于 materials/02_学校规范与参考成稿/；原始批注、会议及重要澄清位于 materials/03_会议与原始批注/。
AAEC/CDCP正式结果已由作者确认实测；ArgUNSC是同一AM任务的模拟补充。04历史稿与旧审阅报告不能覆盖当前v8内容。

推荐Git下载（仅取展开的材料目录；适用于Git Bash、终端、PowerShell和CMD）
使用支持sparse-checkout的较新Git。以下使用一个尚不存在的新本地目录；逐条执行，上一条成功后再继续，不操作其他工作区：

git clone --depth 1 --filter=blob:none --no-checkout --single-branch --no-tags --branch review-materials-20261015 https://github.com/Vague-t/Graduate_Paper.git Graduate_Paper_review_v8
git -C Graduate_Paper_review_v8 sparse-checkout set --no-cone "/review-materials/20261015-v8/materials/"
git -C Graduate_Paper_review_v8 checkout review-materials-20261015

论文和所有审阅资料此时已是普通文件，位置：
Graduate_Paper_review_v8/review-materials/20261015-v8/materials/

可选完整性核验（需要Python；Windows可将python3替换为py）：
python3 Graduate_Paper_review_v8/review-materials/20261015-v8/materials/11_索引与校验/verify_package.py

后续更新这个专用下载目录：
git -C Graduate_Paper_review_v8 pull --ff-only

下载中断后，如果目标目录已经创建且是有效的Git仓库，可重试上面的第二、第三条命令；更新时使用上面的pull命令。
不要对有个人改动的工作区使用强制重置或清理命令。首次下载请选择尚不存在的目标目录，已有下载目录使用上面的更新命令。

保留的ZIP交付
thesis_review_v8_20261015.zip，81,562,714字节，解压后175文件。
SHA256：ac0033ae15ef76afbf2d0b61956e29026cf18027b1a7117f2c6049c63be5347a
ZIP原件保持不变；其内的prompt仍包含相同审阅任务，只是取件说明较早使用ZIP入口。本目录独立REVIEW_PROMPT已补充直接读取materials的方式。
本目录CONTENTS.json/CONTENTS.csv是展开材料的索引；materials/SHA256SUMS校验展开内容，外层SHA256SUMS校验ZIP及外层说明文件。

历史记录
review-materials/20261015是此前v5材料快照；当前审阅入口是本目录20261015-v8。
本包是作者侧独立审阅交接材料，不含全部训练日志、模型权重或会议录音，不是学校匿名送审附件。
