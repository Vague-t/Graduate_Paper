#!/usr/bin/env python3
"""Reproduce the three 1007 manuscript mechanism figures, without network access.

Run with the bundled Python:
  /Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 figures.py

Dependencies supplied by the desktop runtime: reportlab, pypdfium2, Pillow.
Matplotlib is absent from that runtime, so these diagrams use native vector PDF
drawing and PDFium rasterization instead. PDFs retain embedded Chinese text.
All artwork is exactly 157 mm wide; every label is at least 9 pt at that width.
The source of every depicted mechanism is the author-approved manuscript design;
these are constructed mechanism illustrations, not measured data or real cases.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from math import atan2, cos, pi, sin
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
WIDTH_MM = 157.0
WIDTH = WIDTH_MM * 72 / 25.4
FONT = "MechanismChinese"
MIN_FONT_PT = 9.0
FONT_CANDIDATES = (
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/STHeiti Light.ttc"),
)


def register_font(explicit: str | None = None) -> Path:
    candidates = [Path(explicit)] if explicit else FONT_CANDIDATES
    for path in candidates:
        if path.is_file():
            try:
                pdfmetrics.registerFont(TTFont(FONT, str(path)))
                return path
            except Exception:
                continue
    raise RuntimeError("No usable Chinese TrueType font. Supply --font PATH.")


@dataclass
class Diagram:
    path: Path
    height: float

    def __post_init__(self):
        self.c = canvas.Canvas(str(self.path), pagesize=(WIDTH, self.height),
                               pageCompression=1, invariant=1)
        self.c.setTitle(self.path.stem + " — 方法机制示意，非实测案例")
        self.c.setAuthor("Manuscript mechanism illustration")

    def text(self, x, y, lines, *, size=9.4, leading=13.2, align="center",
             color=0.08, max_width=None):
        """Draw text at top-origin baseline coordinates, checking text width."""
        assert size >= MIN_FONT_PT, f"Font too small: {size}"
        if isinstance(lines, str):
            lines = lines.split("\n")
        self.c.setFont(FONT, size)
        self.c.setFillGray(color)
        for i, line in enumerate(lines):
            width = pdfmetrics.stringWidth(line, FONT, size)
            if max_width is not None and width > max_width + 0.1:
                raise ValueError(f"Text too wide ({width:.1f}>{max_width}): {line}")
            baseline = self.height - y - i * leading
            if align == "center":
                self.c.drawCentredString(x, baseline, line)
            elif align == "right":
                self.c.drawRightString(x, baseline, line)
            else:
                self.c.drawString(x, baseline, line)

    def rect(self, x, y, w, h, *, fill=1, stroke=0.18, lw=0.85,
             dash=None, radius=4):
        self.c.saveState()
        self.c.setFillGray(fill)
        self.c.setStrokeGray(stroke)
        self.c.setLineWidth(lw)
        if dash:
            self.c.setDash(dash)
        self.c.roundRect(x, self.height-y-h, w, h, radius,
                         stroke=1, fill=1)
        self.c.restoreState()

    def box(self, x, y, w, h, lines, *, size=9.4, fill=1,
            stroke=0.18, lw=0.85, leading=13.3, dash=None):
        self.rect(x, y, w, h, fill=fill, stroke=stroke, lw=lw, dash=dash)
        if isinstance(lines, str):
            lines = lines.split("\n")
        block = len(lines) * leading
        baseline = y + (h - block) / 2 + leading * 0.79
        self.text(x+w/2, baseline, lines, size=size, leading=leading,
                  max_width=w-10)

    def line(self, points, *, gray=0.2, lw=1.0, dash=None):
        self.c.saveState()
        self.c.setStrokeGray(gray)
        self.c.setLineWidth(lw)
        if dash:
            self.c.setDash(dash)
        p = self.c.beginPath()
        p.moveTo(points[0][0], self.height-points[0][1])
        for x, y in points[1:]:
            p.lineTo(x, self.height-y)
        self.c.drawPath(p, stroke=1)
        self.c.restoreState()

    def arrow(self, points, *, gray=0.12, lw=1.1, dash=None, head=4.7):
        self.line(points, gray=gray, lw=lw, dash=dash)
        x, y = points[-1]
        x0, y0 = points[-2]
        angle = atan2(y-y0, x-x0)
        self.c.saveState()
        self.c.setFillGray(gray)
        p = self.c.beginPath()
        p.moveTo(x, self.height-y)
        for turn in (-pi/7, pi/7):
            px, py = x-head*cos(angle+turn), y-head*sin(angle+turn)
            p.lineTo(px, self.height-py)
        p.close()
        self.c.drawPath(p, stroke=0, fill=1)
        self.c.restoreState()

    def footer(self):
        self.text(WIDTH/2, self.height-8, "方法机制示意  非实测案例", size=9.1,
                  color=0.28)

    def save(self, dpi):
        self.footer()
        self.c.showPage()
        self.c.save()
        document = pdfium.PdfDocument(str(self.path))
        page = document[0]
        bitmap = page.render(scale=dpi/72, fill_color=(255, 255, 255, 255))
        image = bitmap.to_pil().convert("RGB")
        image.save(self.path.with_suffix(".png"), dpi=(dpi, dpi))
        width, height = image.size
        bitmap.close()
        page.close()
        document.close()
        print(f"{self.path.stem}: {WIDTH_MM:.0f} × {self.height*25.4/72:.1f} mm; "
              f"{width} × {height} px; {dpi} dpi; minimum font {MIN_FONT_PT:g} pt")


def framework(out: Path, dpi: int):
    d = Diagram(out / "framework.pdf", 492)
    d.rect(12, 14, WIDTH-24, 205, fill=0.972, stroke=0.58, lw=0.75)
    d.text(24, 34, "训练阶段：文本增强与监督保持", size=10.5, align="left")
    d.box(24, 57, 112, 45, "训练金标文本\n及其论辩图")
    d.box(164, 57, 112, 45, "指定组件改写\n保留其余文本", fill=0.91)
    d.box(304, 57, 117, 45, "标签与语义检查\n含完整关系影响域", fill=0.91)
    d.arrow([(136, 79.5), (164, 79.5)])
    d.arrow([(276, 79.5), (304, 79.5)])

    d.box(160, 138, 131, 64, "原文＋合格增强文\n成对图因素学习\n共享生成器＋辅助头", fill=0.91)
    d.box(24, 138, 112, 48, "训练后生成器\nICIC 专项建模基础")
    d.arrow([(362.5, 102), (362.5, 167), (291, 167)])
    d.text(322, 153, "通过", size=9.1)
    d.arrow([(160, 162), (136, 162)])
    d.box(317, 187, 97, 23, "拒绝该增强变体", size=9.1, fill=1)
    d.arrow([(362.5, 167), (362.5, 187)])
    d.text(389, 180, "失败", size=9.1)
    d.text(225.5, 214, "辅助头仅用于训练", size=9.1)

    d.rect(12, 244, WIDTH-24, 227, fill=0.985, stroke=0.58, lw=0.75)
    d.text(24, 263, "测试阶段：组件与关系联合恢复", size=10.5, align="left")
    d.box(24, 287, 112, 46, "新的输入原文\n测试时没有金标")
    d.box(164, 287, 112, 46, "多候选完整图\n继承 ICIC")
    d.box(304, 287, 117, 46, "MCR 初始选择\n继承 ICIC")
    d.arrow([(136, 310), (164, 310)])
    d.arrow([(276, 310), (304, 310)])
    # Forward-only use of a trained model; no inference-to-training arrow.
    d.arrow([(80, 186), (80, 230), (220, 230), (220, 287)], dash=(3, 2))
    d.text(274, 235, "调用训练后生成器", size=9.0)

    d.box(304, 355, 117, 51, "固定候选宇宙\n及完整对象评分")
    d.box(164, 355, 112, 51, "组件＋关系\n依赖闭合事务（新增）", fill=0.89, size=9.1)
    d.box(24, 355, 112, 51, "合格则接受\n否则原子回退", fill=0.89)
    d.arrow([(362.5, 333), (362.5, 355)])
    d.arrow([(304, 380.5), (276, 380.5)])
    d.arrow([(164, 380.5), (136, 380.5)])
    d.box(24, 430, 112, 29, "最终完整论辩图", fill=0.94)
    d.arrow([(80, 406), (80, 430)])
    d.text(291, 431, ["固定候选与评分，原文不变", "推理评分不回传训练生成器"],
           size=9.1, max_width=261)
    d.save(dpi)


def augmentation(out: Path, dpi: int):
    d = Diagram(out / "augmentation.pdf", 414)
    d.text(17, 21, "只改写 A={c1,c2}，核对其全部受影响关系因素", size=10.3,
           align="left", max_width=WIDTH-34)

    d.rect(18, 44, 205, 255, fill=0.948, stroke=0.35, dash=(4, 3), lw=1.0)
    d.text(120.5, 65, "可改写组件", size=9.8)
    d.text(342, 65, "只读组件", size=9.8)
    d.box(33, 87, 175, 55, "c1 · Claim\n增加图书馆经费", fill=1, size=9.6)
    d.box(33, 208, 175, 68, "c2 · Premise\n现有座位不足\n而且开放时间偏短", fill=1, size=9.6)
    d.box(265, 87, 159, 55, "c3 · Claim\n延长图书馆开放时间", fill=0.982, size=9.6)
    d.box(265, 231, 159, 48, "c4 · Claim\n增加食堂素食窗口", fill=0.982, size=9.6)

    # The only two relation edges in this figure are Support edges.
    d.arrow([(83, 208), (83, 142)], lw=1.3)
    d.text(146, 174, "内部 Support", size=9.3, max_width=114)
    d.arrow([(208, 233), (241, 233), (241, 114.5), (265, 114.5)], lw=1.3)
    d.text(330, 170, "跨边界 Support", size=9.3, max_width=166)
    # NONE is an endpoint-combination state: no line is drawn to c4.
    d.text(342, 196, ["c2→c4：跨边界组合", "NONE，不输出边"], size=9.1,
           max_width=164)

    d.text(17, 322, "标签保持检查", size=10.1, align="left")
    d.box(18, 336, 112, 37, "槽位改写\n类型保持", size=9.3, fill=0.948)
    d.box(164, 336, 112, 37, "全文回填\n全部坐标输运", size=9.3)
    d.box(310, 336, 114, 37, "逐项核对影响域\n任一漂移则拒绝", size=9.3)
    d.arrow([(130, 354.5), (164, 354.5)])
    d.arrow([(276, 354.5), (310, 354.5)])
    d.text(WIDTH/2, 391, "目标：组件类型、关系方向与标签、NONE 状态均保持", size=9.1,
           max_width=WIDTH-28)
    d.save(dpi)


def repair(out: Path, dpi: int):
    d = Diagram(out / "repair.pdf", 481)
    d.rect(17, 14, WIDTH-34, 48, fill=0.95, stroke=0.45)
    d.text(WIDTH/2, 31, "输入原文始终不变", size=10.3)
    d.text(WIDTH/2, 50, "“图书馆现有座位不足，而且开放时间偏短”", size=9.4,
           max_width=WIDTH-54)

    d.box(21, 84, 167, 52, "旧 c2 · Premise\n图书馆现有座位不足（短跨度）", size=9.5)
    d.box(253, 84, 171, 52, "新 c2 · Premise\n图书馆现有座位不足，\n而且开放时间偏短", size=9.3,
          leading=12.8, fill=0.91)
    d.arrow([(188, 110), (253, 110)], lw=1.25)
    d.text(220, 98, "替换", size=9.1)
    d.text(WIDTH/2, 154, "跨度不同，视为不同的完整组件对象", size=9.3)

    d.rect(16, 169, WIDTH-32, 293, fill=0.983, stroke=0.5, dash=(4, 3))
    d.text(28, 189, "在副本中构造并复核一个完整事务", size=10.0, align="left")
    d.box(51, 204, WIDTH-102, 42,
          "旧 c2 的全部入边、出边失效\n端点已变，不默认继承 Support", size=9.6)
    d.box(51, 266, WIDTH-102, 46,
          "新 c2 的所有合法关系重新判定\n含入边、出边及 NONE；外部关系固定", size=9.6)
    d.arrow([(WIDTH/2, 246), (WIDTH/2, 266)])
    d.box(38, 332, WIDTH-76, 62,
          "组件分项效用不降；关系分项效用不降\n总效用严格增加（超过固定正阈值）\n整图合法，且在编辑预算内", size=9.6,
          fill=0.91, lw=1.25, leading=15.3)
    d.arrow([(WIDTH/2, 312), (WIDTH/2, 332)])

    d.box(35, 419, 166, 37, "全部通过\n组件与关系一起提交", size=9.4, fill=0.89)
    d.box(246, 419, 166, 37, "任一不满足\n整体回退，保留原图", size=9.4)
    d.arrow([(174, 394), (174, 407), (118, 407), (118, 419)])
    d.arrow([(273, 394), (273, 407), (329, 407), (329, 419)])
    d.save(dpi)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "figures")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--font", help="Chinese TrueType font path")
    args = parser.parse_args()
    if args.dpi < 300:
        parser.error("Use at least 300 dpi for manuscript output.")
    font_path = register_font(args.font)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"Embedded font: {font_path}")
    for draw in (framework, augmentation, repair):
        draw(args.out, args.dpi)


if __name__ == "__main__":
    main()
