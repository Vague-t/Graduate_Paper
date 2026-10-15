# 硕士论文独立审阅材料

完整材料包：`thesis_review_full_20261015.zip`（57,240,535 字节，54.6 MiB，90 个文件）。这是完整 ZIP，可直接解压，不需要分包还原或 Git LFS。

包含当前 v5 Word/PDF、学校规范与模板、蒋梓浩等参考论文、会议摘要和整理记录、原 PDF 的 33 条注释、聊天侧 5 条批注、历次审阅和修订记录、拓展调研及审阅提示词。

当前审阅基线为 v5。用户已确认 9B、4B、7B 正式实验完成，正文已替换为实测结果。会议材料是聊天中提供的整理记录，不是录音逐字稿；既有分析供独立复核。

## 已有本地仓库

在本地 Graduate_Paper 仓库目录执行以下命令，即可将交付目录取到当前工作区，无需切换分支：

```bash
git fetch origin review-materials-20261015
git restore --source=FETCH_HEAD --worktree -- review-materials/20261015
```

完整包位于 `review-materials/20261015/thesis_review_full_20261015.zip`。

## 尚未克隆仓库

只下载这次交付目录，避免拉取仓库中大量历史论文和图片：

```bash
git clone --depth 1 --filter=blob:none --no-checkout --branch review-materials-20261015 https://github.com/Vague-t/Graduate_Paper.git thesis-review-materials
git -C thesis-review-materials sparse-checkout set --no-cone /review-materials/20261015/
git -C thesis-review-materials checkout
```

## 交给审阅 agent

将完整 ZIP 和 `REVIEW_PROMPT.txt` 一起交给审阅 agent。解压后从 `审阅材料/00_先读说明.txt` 开始阅读。

原始文件逐份校验，未修改论文内容。完整包 SHA256 见 `SHA256SUMS`；Linux 可运行 `sha256sum -c SHA256SUMS`，macOS 可运行 `shasum -a 256 -c SHA256SUMS`。

此包是作者侧审阅材料，保留历史批注和原稿署名，不是学校匿名盲审提交包。
