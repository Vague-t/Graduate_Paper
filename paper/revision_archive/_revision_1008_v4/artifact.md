# 1008 v4 论文逐项润色排版契约

用户授权范围为按当前 V3 问题清单逐项润色论文。最新 V3 正文、DOCX、问题清单与修改对照均保持不变；V3-10 已撤销，本轮不恢复作者分工声明。论文内容由主代理审定，本文件只约束模板重用与版面验证。

保留模板：`/Users/channtang/Downloads/paper/report_1008_v3_full.docx`。SHA-256：`e3cda7c0e31b57f908b6c89c685967c1b713c85646565de1a59ecc7968a752f1`。最新参考渲染为 `_revision_1008_v3/v3_10_withdrawal/render`，88 页；撤销 V3-10 后仅物理页 17、79 改动并已全尺寸检查，其余 86 页与先前全页检查图像像素相同。参考包、几何、样式与各部件散列保存于本目录 `template-evidence.json`。本轮不覆盖旧证据。

输出源文为 `/Users/channtang/Downloads/paper/report_1008_v4_full.md`，输出 DOCX 为 `/Users/channtang/Downloads/paper/report_1008_v4_full.docx`。所有构建脚本、页码缓存、临时字体缓存和渲染中间件仅写本目录 `_revision_1008_v4`；原脚本通过只读导入重用，并禁用旧目录 Python 字节码写入。

模板沿用 3 节纵向 A4，210 × 297 mm；左 28 mm，右、上、下 25 mm。双语封面无页码，前置部分大写罗马页码自 I 起，正文阿拉伯页码自 1 起。页眉与页脚位置、各节几何及分节逻辑不变。本轮页眉警示改为“1008-v4 逐项润色稿　含非实测占位　勿送审”。中文沿用既有宋体类，西文字体 Times New Roman；正文 12 pt、20.5 pt 行距；章、节、小节为 18、14、12 pt，黑色。

编辑槽位包括经过审定的正文段落、伪码、补充机制表、题注、目录缓存和因内容变化而重算的跨页位置。保留六章与现有附录总体结构，原生 OMML，不将公式栅格化。插图使用原 7 张 `_revision_1007_v2/figures` 资产，保持 157 mm 宽度与原图最小字号。原有 32 条独立公式、46 条参考文献、125 个非实测 P 数值占位须核对；新增文字不能伪装为已完成的实验或替代尚缺的实证材料。

三级目录保留原生 TOC 字段、可点击缓存与 6 pt 一级条目前间距；图表目录使用独立样式。每轮构建后根据实际 PDF 重新计算页码，重建后复核缓存与最终 PDF 一致。Word 后续刷新设置 `updateFields=true`，不使用 LibreOffice 另存 DOCX 更新字段，未通过 Word 桌面渲染验证。

算法行使用每级两个源空格表示嵌套，输入输出不编号，其余步骤自动连续编号。行号独立左齐，正文按 7 mm 加每级 4 mm 缩进，回行同位，10.5 pt 字、15 pt 行距，控制词加粗。续页必须在完整控制块处切分，重复算法编号并标“续”。初始不继承旧切点，按新页面确定。

数值表沿用三线表，文字机制表沿用浅网格与原字体。表头重复且行高自适应，跨页按渲染调整切分，并使用独立续题注。不得缩小字号强行保持旧页数。

包内 `theme`、`fontTable`、`numbering`、`webSettings`、原媒体、`customXml` 与约定文档属性为 preserve-only，最终逐部件校验散列；正文、页眉页脚、styles、settings、关系清单和核心属性为用户授权可变部件。正文和新增表重建仍基于保留模板包，而非空白样式。

质量门包括源文散列锁定、动态标题与题注数量、全部图像资产散列、原生公式与编号、P 占位多重集合、算法缩进、表分段数据保真、三级目录页码、旧文件散列和包内 preserve-only 部件核验。必须使用 bundled Python 与 packaged `render_docx.py`，只允许 bundled LibreOffice：`/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/MacOS/soffice`，禁止桌面 LibreOffice。每轮使用全新渲染目录；最终所有 PNG 逐页全尺寸检查并记录。QA PDF 和页面图仅为内部检查，不作为用户请求的交付物。排版 QA 不证明实验完成、文献事实、院系合规或所有 Word 版本一致。

最终冻结源文 SHA-256 为 `9dea07abbf986cf499c1ab3ff8ba249989ca1815481dfefa220ede70b24b7080`，最终渲染 `render_pass6` 共 89 页。机械审计、DOCX 包完整性与全部 89 页原分辨率视觉检查均通过，详细证据见 `final_audit.json` 和 `layout_qa.json`。算法续页与表格切点按最终分页重算；发现的第 3 章末两行近空页已由主代理压缩重复小结句修复，未缩小正文或算法字号。
