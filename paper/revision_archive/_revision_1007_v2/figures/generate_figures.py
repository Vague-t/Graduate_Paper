#!/usr/bin/env python3
"""Seven author-designed, non-empirical thesis mechanism figures.

Run with the bundled Python. Dependencies: reportlab, pypdfium2, Pillow.
PNG/PDF are canonical for print; SVG contains editable vector shapes and text,
with explicit Chinese font fallbacks. No data, fitted result or measured curve
is created here. All coordinates use points at an exact print width of 157 mm.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from html import escape
from math import atan2, cos, pi, sin
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
WIDTH = 157 * 72 / 25.4
FONT = "MechanismChinese"
FONT_PATH = Path("/Library/Fonts/Arial Unicode.ttf")
MIN_FONT = 9.0
RECORDS = []


def gray(value):
    v = round(value * 255)
    return f"rgb({v},{v},{v})"


@dataclass
class Diagram:
    stem: str
    height: float
    meaning: str
    audit: list[str]
    elements: list[str] = field(default_factory=list)
    labels: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.path = ROOT / (self.stem + ".pdf")
        self.c = canvas.Canvas(str(self.path), pagesize=(WIDTH, self.height),
                               pageCompression=1, invariant=1)
        self.c.setTitle(self.stem + " — 方法机制示意，非实测")
        self.c.setAuthor("Author-designed manuscript mechanism")
        self.elements.append(f'<rect width="{WIDTH}" height="{self.height}" fill="white"/>')

    def text(self, x, y, lines, *, size=9.3, leading=12.5,
             align="center", color=0.06, max_width=None):
        assert size >= MIN_FONT
        if isinstance(lines, str):
            lines = lines.split("\n")
        self.c.setFont(FONT, size)
        self.c.setFillGray(color)
        for i, line in enumerate(lines):
            w = pdfmetrics.stringWidth(line, FONT, size)
            if max_width is not None and w > max_width + 0.1:
                raise ValueError(f"{self.stem}: text too wide ({w:.1f}>{max_width}): {line}")
            yy = y + i * leading
            left = x if align == "left" else x - w if align == "right" else x - w/2
            assert left >= 1 and left + w <= WIDTH - 1, (self.stem, line, left, w)
            assert yy - size >= 0 and yy < self.height, (self.stem, line, yy)
            if align == "center":
                self.c.drawCentredString(x, self.height-yy, line)
            elif align == "right":
                self.c.drawRightString(x, self.height-yy, line)
            else:
                self.c.drawString(x, self.height-yy, line)
            anchor = {"left": "start", "right": "end", "center": "middle"}[align]
            self.elements.append(
                f'<text x="{x:.3f}" y="{yy:.3f}" font-size="{size}" '
                f'text-anchor="{anchor}" fill="{gray(color)}" '
                f'textLength="{w:.3f}" lengthAdjust="spacingAndGlyphs">{escape(line)}</text>')
            self.labels.append({"text": line, "font_pt": size,
                                "bounds": [round(left,3), round(yy-size,3), round(w,3), size]})

    def rect(self, x, y, w, h, *, fill=1, stroke=.22, lw=.8, dash=None, radius=3):
        self.c.saveState()
        self.c.setFillGray(fill)
        self.c.setStrokeGray(stroke)
        self.c.setLineWidth(lw)
        if dash:
            self.c.setDash(dash)
        self.c.roundRect(x, self.height-y-h, w, h, radius, stroke=1, fill=1)
        self.c.restoreState()
        dashattr = f' stroke-dasharray="{" ".join(map(str,dash))}"' if dash else ""
        self.elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                             f'rx="{radius}" fill="{gray(fill)}" stroke="{gray(stroke)}" '
                             f'stroke-width="{lw}"{dashattr}/>')

    def box(self, x, y, w, h, lines, *, size=9.3, fill=1, leading=12.5,
            stroke=.22, lw=.8, dash=None):
        self.rect(x,y,w,h,fill=fill,stroke=stroke,lw=lw,dash=dash)
        if isinstance(lines,str):
            lines=lines.split("\n")
        assert len(lines)*leading <= h-3, (self.stem, lines, h)
        baseline=y+(h-len(lines)*leading)/2+leading*.79
        self.text(x+w/2,baseline,lines,size=size,leading=leading,max_width=w-10)

    def line(self, points, *, lw=1, color=.15, dash=None):
        self.c.saveState()
        self.c.setStrokeGray(color)
        self.c.setLineWidth(lw)
        if dash:
            self.c.setDash(dash)
        p=self.c.beginPath()
        p.moveTo(points[0][0],self.height-points[0][1])
        for x,y in points[1:]:
            p.lineTo(x,self.height-y)
        self.c.drawPath(p,stroke=1)
        self.c.restoreState()
        dashattr = f' stroke-dasharray="{" ".join(map(str,dash))}"' if dash else ""
        coords=" ".join(f"{x:.3f},{y:.3f}" for x,y in points)
        self.elements.append(f'<polyline points="{coords}" fill="none" stroke="{gray(color)}" '
                             f'stroke-width="{lw}"{dashattr}/>')

    def arrow(self, points, *, lw=1, color=.12, dash=None, head=4.4):
        self.line(points,lw=lw,color=color,dash=dash)
        x,y=points[-1]
        a=atan2(y-points[-2][1],x-points[-2][0])
        vertices=[(x,y)]+[(x-head*cos(a+t),y-head*sin(a+t)) for t in (-pi/7,pi/7)]
        self.c.saveState()
        self.c.setFillGray(color)
        p=self.c.beginPath()
        p.moveTo(x,self.height-y)
        for px,py in vertices[1:]:
            p.lineTo(px,self.height-py)
        p.close()
        self.c.drawPath(p,stroke=0,fill=1)
        self.c.restoreState()
        coords=" ".join(f"{px:.3f},{py:.3f}" for px,py in vertices)
        self.elements.append(f'<polygon points="{coords}" fill="{gray(color)}"/>')

    def legend(self, y):
        self.arrow([(17,y-3),(42,y-3)])
        self.text(49,y,"数据／表示",size=9,align="left")
        self.arrow([(118,y-3),(143,y-3)],dash=(3,2))
        self.text(150,y,"控制／调用",size=9,align="left")
        self.text(WIDTH-16,y,"灰底：新增模块",size=9,align="right")

    def save(self,dpi):
        self.text(WIDTH/2,self.height-7,"人为构造的机制示意；非实测结果",size=9,color=.3)
        self.c.showPage()
        self.c.save()
        svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="157mm" '
             f'height="{self.height*25.4/72:.4f}mm" viewBox="0 0 {WIDTH} {self.height}" '
             'role="img">\n'
             f'<title>{escape(self.stem)}</title><desc>{escape(self.meaning)}</desc>\n'
             '<g font-family="Arial Unicode MS, Noto Sans CJK SC, Songti SC, sans-serif">\n'
             +'\n'.join(self.elements)+'\n</g></svg>\n')
        self.path.with_suffix('.svg').write_text(svg,encoding='utf-8')
        doc=pdfium.PdfDocument(str(self.path))
        page=doc[0]
        bitmap=page.render(scale=dpi/72,fill_color=(255,255,255,255))
        im=bitmap.to_pil().convert('RGB')
        im.save(self.path.with_suffix('.png'),dpi=(dpi,dpi))
        dimensions=im.size
        bitmap.close(); page.close(); doc.close()
        RECORDS.append(dict(stem=self.stem,width_mm=157,height_mm=round(self.height*25.4/72,3),
                            min_font_pt=min(x['font_pt'] for x in self.labels),dpi=dpi,
                            pixels=list(dimensions),meaning=self.meaning,semantic_audit=self.audit,
                            png=self.stem+'.png',svg=self.stem+'.svg',pdf=self.stem+'.pdf',
                            labels=self.labels))
        print(self.stem, dimensions, f'{self.height*25.4/72:.1f}mm',flush=True)


def argument_example(dpi):
    d=Diagram('argument_example',278,'同一人为构造片段的原文、组件及有向关系；NONE 表示不输出边。',[
        '原文由四句组成；c2 是一个完整前提，同时支持 c1 与 c3。',
        '图中只画两条 Support 边；c2 与 c4 的 NONE 仅作文字说明，无连线。',
        '组件以原文跨度及类型共同定义；右侧节点仅是这些完整组件的显示简写。'])
    d.rect(12,8,WIDTH-24,80,fill=.97)
    d.text(23,24,'原文（人为构造）',size=10,align='left')
    d.text(23,40,['学校应该增加图书馆经费。',
                 '图书馆现有座位不足，而且开放时间偏短。',
                 '图书馆应该延长开放时间。食堂应该增加素食窗口。'],
           size=9.3,leading=13,align='left',max_width=WIDTH-46)
    d.arrow([(WIDTH/2,88),(WIDTH/2,104)])
    d.rect(12,106,246,148)
    d.text(24,122,'组件识别：完整跨度＋类型',size=10,align='left')
    d.text(23,142,['c1 · Claim：学校应该增加图书馆经费',
                  'c2 · Premise：图书馆现有座位不足，',
                  '                    而且开放时间偏短',
                  'c3 · Claim：图书馆应该延长开放时间',
                  'c4 · Claim：食堂应该增加素食窗口'],
           size=9.2,leading=21,align='left',max_width=224)
    d.rect(270,106,163,148)
    d.text(351.5,122,'关系识别：完整组件为端点',size=9.2,max_width=153)
    d.box(281,164,32,23,'c2',size=9.3)
    d.box(390,133,32,23,'c1',size=9.3)
    d.box(390,195,32,23,'c3',size=9.3)
    d.arrow([(313,171),(348,144.5),(390,144.5)])
    d.arrow([(313,180),(348,206.5),(390,206.5)])
    d.text(350,137,'Support',size=9)
    d.text(350,220,'Support',size=9)
    d.box(281,219,32,23,'c4',size=9.3)
    d.text(371,241,'c2→c4：NONE，无边',size=9,max_width=113)
    d.save(dpi)


def research_relationship(dpi):
    d=Diagram('research_relationship',260,'共同的组件—关系依赖问题引出训练监督保持与推理结构恢复两条研究路径。',[
        '训练阶段允许受控改写原文；推理阶段原文固定，只编辑预测论辩图。',
        'ICIC 为继承基础；两条新增路径之间不存在推理反哺训练或自训练闭环。',
        '图示研究问题与机制目标，不承诺未经测量的效果。'])
    d.box(44,8,357,39,'共同依赖：关系以完整组件为端点\n组件的跨度、类型或存在性改变，依赖关系需同步处理',size=9.5,fill=.95)
    d.arrow([(WIDTH/2,47),(WIDTH/2,59),(119,59),(119,74)])
    d.arrow([(WIDTH/2,59),(326,59),(326,74)])
    d.rect(13,74,201,128,fill=.98)
    d.rect(231,74,201,128,fill=.98)
    d.text(113.5,91,'训练侧：监督保持',size=10.2)
    d.text(331.5,91,'推理侧：结构恢复',size=10.2)
    d.box(27,101,173,35,'受控文本改写\n风险：类型或关系标签漂移',size=9.3)
    d.box(245,101,173,35,'固定原文，预测组件发生变化\n风险：关系仍绑定旧端点',size=9.3)
    d.arrow([(113.5,136),(113.5,150)])
    d.arrow([(331.5,136),(331.5,150)])
    d.box(27,150,173,39,'完整影响域检查＋成对学习\n保持可用监督与图因素对应',size=9.3,fill=.91)
    d.box(245,150,173,39,'依赖闭合事务＋原子提交\n联合恢复组件与受影响关系',size=9.3,fill=.91)
    d.box(52,218,341,24,'继承基础：ICIC 专项建模与 MCR 初始图选择',size=9.4)
    d.arrow([(113.5,218),(113.5,202)],dash=(3,2))
    d.arrow([(331.5,218),(331.5,202)],dash=(3,2))
    d.save(dpi)


def framework(dpi):
    d=Diagram('framework',235,'离线增强、共享生成器训练与测试期冻结评分后的联合恢复接口。',[
        '增强检查离线完成；仅合格增强文参与成对训练。',
        '训练后生成器仅前向用于推理；训练辅助头在测试移除。',
        'MCR 及完整候选生成继承 ICIC；冻结对象评分独立于训练辅助头。',
        '事务恢复不更新生成器或对象评分；测试输入无金标且原文不变。'])
    d.text(17,16,'训练：离线增强 → 共享生成器学习',size=10.2,align='left')
    d.box(17,25,111,31,'训练原文与金标\n指定槽位改写',size=9.4)
    d.box(161,25,119,31,'完整影响域检查\n不合格变体丢弃',size=9.4,fill=.92)
    d.box(313,25,115,31,'原文＋合格增强文\n成对图因素学习',size=9.3,fill=.92)
    d.arrow([(128,40.5),(161,40.5)])
    d.arrow([(280,40.5),(313,40.5)])
    d.text(17,72,['ICIC 生成器：基础模型冻结；',
                  '适配模块与训练辅助头可训练'],size=9.2,align='left')
    d.box(292,70,136,22,'训练后生成器；移除辅助头',size=9)
    d.arrow([(370.5,56),(370.5,70)])
    d.line([(14,99),(431,99)],color=.6,lw=.65)
    d.text(17,114,'推理：固定原文 → 完整图候选 → 联合恢复',size=10.2,align='left')
    d.box(17,124,111,31,'新的测试原文\n没有金标',size=9.4)
    d.box(161,124,119,31,'完整候选 → MCR\n共享合法化；得到 G0',size=9.2)
    d.box(313,124,115,31,'固定候选宇宙\n冻结完整对象评分',size=9.3)
    d.arrow([(128,139.5),(161,139.5)])
    d.arrow([(280,139.5),(313,139.5)])
    d.arrow([(428,81),(440,81),(440,120),(220.5,120),(220.5,124)],dash=(3,2))
    d.box(313,167,115,31,'组件与关系\n依赖闭合事务',size=9.3,fill=.92)
    d.box(161,167,119,31,'合格则提交\n否则整体回退',size=9.3,fill=.92)
    d.box(17,167,111,31,'预算内迭代\n输出最终完整图',size=9.3,fill=.92)
    d.arrow([(370.5,155),(370.5,167)])
    d.arrow([(313,182.5),(280,182.5)])
    d.arrow([(161,182.5),(128,182.5)])
    d.legend(214)
    d.save(dpi)


def augmentation(dpi):
    d=Diagram('augmentation',326,'选定组件的关系影响域包含内部与跨边界的全部合法端点组合，包括 NONE。',[
        'A={c1,c2} 可改写，c3/c4 内容只读；只读不等于坐标不变。',
        '内部与跨边界是位置分类，Support 与 NONE 是关系状态分类，二者不混同。',
        '这里只显示两条 Support 和一个 NONE 示例；影响域包含全部合法组合，不限于画出的边。',
        '回填后全文重分词并输运全部坐标与端点；任一标签漂移拒绝整个变体。'])
    d.text(17,19,'只改写 A={c1,c2}；检查全部受影响关系因素',size=10.1,align='left')
    d.rect(17,33,199,185,fill=.96,dash=(4,3))
    d.text(116.5,51,'可改写组件',size=9.8)
    d.text(340,51,'只读组件',size=9.8)
    d.box(31,64,171,41,'c1 · Claim\n学校应该增加图书馆经费',size=9.3)
    d.box(31,155,171,49,'c2 · Premise\n图书馆现有座位不足，\n而且开放时间偏短',size=9.3)
    d.box(260,64,169,41,'c3 · Claim\n图书馆应该延长开放时间',size=9.3)
    d.box(260,177,169,35,'c4 · Claim\n食堂应该增加素食窗口',size=9.3)
    d.arrow([(63,155),(63,105)],lw=1.25)
    d.text(135,133,'内部 Support',size=9.2)
    d.arrow([(202,176),(237,176),(237,84.5),(260,84.5)],lw=1.25)
    d.text(340,127,'跨边界 Support',size=9.2)
    d.text(340,149,['c2→c4：跨边界组合','NONE，不输出边'],size=9.1,leading=12)
    d.text(WIDTH/2,235,'影响域：所有与 A 相交的合法端点组合；图中仅列举部分',size=9.2)
    d.box(17,246,117,39,'指定槽位改写\n保留其余文本',size=9.3,fill=.94)
    d.box(164,246,117,39,'全文回填与重分词\n全部坐标／端点输运',size=9.3)
    d.box(311,246,117,39,'逐项核对完整影响域\n任一标签漂移则拒绝',size=9.2)
    d.arrow([(134,265.5),(164,265.5)])
    d.arrow([(281,265.5),(311,265.5)])
    d.text(WIDTH/2,305,'只读组件也可能位移；内部／跨边界与有边／NONE 分开核对',size=9.2)
    d.save(dpi)


def training_architecture(dpi):
    d=Diagram('training_architecture',368,'成对视图共享生成器；金标与对应仅用于训练监督，输入端因素对齐不训练结论专用 LoRA。',[
        'x 与合格 x′ 共用同一生成器；输入仅含指令与各自原文，不含金标答案。',
        'W0 冻结；继承的全局 LoRA 和被当前视图触发的连续提示可训练。',
        '结论专用 LoRA 仅在已闭合结论类型后的相应生成字段触发；输入端、类型未闭合及关系区域 g_t=0。',
        '输入端 h_input/h_end 提供新增组件类型与关系状态头；关系状态包括 NONE；辅助头仅训练使用。',
        '原生 ICIC 句级辅助头、Lgen 与 Lsent 继承；新增因素监督及 JS 成对一致性。',
        '金标跨度、标签及 φ 不拼入回答前的输入上下文；因素监督覆盖全部组件与声明因素宇宙，JS 对齐限定组件 A+ 与关系 D_A；两个视图均接受金标锚定。',
        '输入端因素损失不直接更新结论专用 LoRA；其可训练性来自生成路径损失；每源文档对变体归一化。'])
    d.box(15,9,169,34,'视图 x：指令＋原文\n视图 x′：指令＋合格增强文',size=9.3)
    d.box(249,9,181,34,'金标跨度／标签＋对应 φ\n不拼入回答前的输入上下文',size=9.1)
    d.arrow([(99.5,43),(99.5,58)])
    d.rect(15,58,415,102)
    d.text(27,75,'两视图共享生成器（继承 ICIC）',size=10,align='left')
    d.box(26,84,113,36,'Qwen2.5-7B-Instruct\n基础模型 W0 冻结',size=9.1)
    d.box(154,84,124,36,'全局 LoRA\n可训练；全部位置',size=9.2)
    d.box(292,84,127,36,'条件连续提示\n可训练；各视图独立触发',size=9.0)
    d.box(26,128,393,24,'结论专用 LoRA（可训练）：仅闭合结论类型后的组件字段启用；其余 g_t=0',size=9.0)
    d.arrow([(99.5,160),(99.5,174)])
    d.arrow([(350,160),(350,174)])
    d.box(15,174,183,30,'输入端表示 h_input、h_end\n在答案生成之前提取',size=9.2)
    d.box(245,174,185,30,'答案生成路径与句级辅助头\n继承：Lgen＋λsent Lsent',size=9.2)
    d.arrow([(106.5,204),(106.5,217)])
    d.box(15,217,183,39,'新增：组件类型头＋关系状态头\n关系状态含 NONE；仅训练使用',size=9.1,fill=.92)
    d.box(245,217,185,39,'因素监督：全部组件／声明因素宇宙\nJS 对齐：组件 A+／关系 D_A',size=9.1,fill=.92)
    d.arrow([(198,236.5),(245,236.5)])
    d.line([(430,26),(440,26),(440,236.5)])
    d.arrow([(440,189),(430,189)])
    d.arrow([(440,236.5),(430,236.5)])
    d.arrow([(337.5,256),(337.5,274)])
    d.arrow([(337.5,204),(436,204),(436,286),(418,286)])
    d.box(27,274,391,25,'联合目标：继承损失＋新增因素监督／对齐；按源文档归一化',size=9.2)
    d.text(17,315,'梯度边界：因素损失更新新增头、全局 LoRA 与触发的提示；',size=9.1,align='left')
    d.text(17,328,'不直接更新结论专用 LoRA。W0 始终冻结，辅助头测试时移除。',size=9.1,align='left')
    d.legend(347)
    d.save(dpi)


def repair(dpi):
    d=Diagram('repair',332,'固定原文上替换一个完整组件，并在一个原子事务中重建其所有依赖关系。',[
        '旧 c2 短跨度与新 c2 完整跨度是不同语义对象；相同显示 ID 不传递边或标签。',
        '旧组件全部入边、出边失效，新组件全部合法关系组合重判，含 NONE。',
        '外部关系固定但整图约束须重新检查；无法维持则扩大事务或拒绝。',
        '组件与关系分项效用各不下降，总效用增益大于固定正阈值；合法且预算内才原子提交。',
        '示例只说明替换机制，不断言更长跨度一定更正确，不预设新 Support。'])
    d.box(15,8,415,36,'输入原文始终不变\n“图书馆现有座位不足，而且开放时间偏短”',size=9.4,fill=.96)
    d.box(15,57,176,47,'旧 c2 · Premise\n图书馆现有座位不足\n（短跨度）',size=9.3)
    d.box(254,57,176,47,'新 c2 · Premise\n图书馆现有座位不足，\n而且开放时间偏短',size=9.3,fill=.92)
    d.arrow([(191,80.5),(254,80.5)],lw=1.2)
    d.text(222.5,72,'替换',size=9.2)
    d.text(WIDTH/2,120,'跨度不同即为不同对象；不按显示 ID 继承原边',size=9.3)
    d.box(31,135,383,36,'删除旧 c2 的全部入边与出边\n重新判定新 c2 的全部合法关系组合，包括 NONE',size=9.4)
    d.arrow([(WIDTH/2,171),(WIDTH/2,184)])
    d.box(31,184,383,32,'外部关系保持固定，但须重新核对整图约束\n如产生外部依赖冲突：扩大事务或拒绝',size=9.3)
    d.arrow([(WIDTH/2,216),(WIDTH/2,229)])
    d.box(31,229,383,36,'组件分项效用不降；关系分项效用不降\n总效用增益大于正阈值；整图合法且预算内',size=9.3,fill=.92,lw=1.1)
    d.box(31,285,171,25,'全部通过：组件＋关系原子提交',size=9.1,fill=.92)
    d.box(243,285,171,25,'任一不满足：整体回退，保留原图',size=9.0)
    d.arrow([(145,265),(145,285)])
    d.arrow([(300,265),(300,285)],dash=(3,2))
    d.save(dpi)


def bounded_execution(dpi):
    d=Diagram('bounded_execution',368,'冻结候选和对象评分后，在有限预算内构造、求解、核验和提交依赖闭合事务。',[
        '新测试原文经 K 个完整候选、MCR 和共享合法化得到 G0，继承 ICIC 路径。',
        '搜索前建立并冻结 U/P、q_C/q_R、编辑成本、阈值和缓存；评分器 OOF 拟合并离线校准，不是训练辅助头。',
        '有限提案队列含 D0、B、S_R；独立 no-op 在局部求解器之外保存当前合法图。',
        '每个提案先抵消相同对象并做冲突闭包，再重判所有入/出及 NONE 关系因素，外部关系固定。',
        '局部 ILP 的可行解仍需核验整图合法、分项效用不降、总增益大于固定正阈值和剩余预算。',
        '超时但有可行 incumbent 可经复核接受并记录 gap；无可行解时保留求解状态，不等同数学不可行。',
        '合格事务按总效用最大、编辑更少、语义键排序；原子提交后重建提案队列而不重评分或重训练。',
        '失败试探也计入尝试与时间预算；无合格事务/no-op 或预算耗尽时输出当前完整合法图。'])
    d.box(15,8,414,30,'测试原文 → K 个完整候选 → MCR 与共享合法化 → 当前图 G0',size=9.3)
    d.arrow([(222,38),(222,49)])
    d.box(15,49,414,34,'搜索前冻结：候选宇宙 U/P、对象评分 q_C/q_R、成本与阈值\n评分器独立 OOF 拟合并离线校准；非训练辅助头',size=9.1,fill=.95)
    d.arrow([(222,83),(222,97)])
    d.box(34,97,264,34,'有限提案队列：D0、B、S_R\n记录试探；检查剩余尝试／时间／编辑预算',size=9.2,fill=.93)
    d.box(323,97,106,34,'独立 no-op\n保留当前合法图',size=9.2)
    d.arrow([(376,83),(376,97)],dash=(3,2))
    d.arrow([(166,131),(166,143)])
    d.box(34,143,395,34,'抵消相同对象 → 组件冲突闭包 → 新组件集合 C′\n闭合全部入／出与 NONE 关系空间；外部关系固定',size=9.2,fill=.93)
    d.arrow([(231.5,177),(231.5,189)])
    d.box(34,189,395,34,'局部 ILP → 复核可行候选：整图合法、两分项效用不降\n总效用增益 > 正阈值，且不超过剩余预算',size=9.2,fill=.93)
    d.text(231.5,239,'超时有可行解：复核后可用并记录 gap；无可行解：拒绝该试探',size=9.0)
    d.box(34,253,237,35,'合格者择优：总效用 → 更少编辑 → 语义键\n组件与关系原子提交；重建提案队列',size=9.1,fill=.9)
    d.box(304,253,125,35,'无合格事务／no-op\n或预算耗尽：停止',size=9.1)
    d.arrow([(50,223),(50,253)])
    d.line([(361,223),(361,229),(441,229)],dash=(3,2))
    d.arrow([(429,114),(441,114),(441,245),(366.5,245),(366.5,253)],dash=(3,2))
    d.arrow([(34,270.5),(20,270.5),(20,114),(34,114)],dash=(3,2))
    d.text(17,312,'循环只更新当前图与提案；评分、阈值及原文始终不变',size=9.2,align='left')
    d.box(304,300,125,26,'输出当前完整合法图',size=9.2)
    d.arrow([(366.5,288),(366.5,300)])
    d.legend(347)
    d.save(dpi)


FIGURES = [argument_example,research_relationship,framework,augmentation,
           training_architecture,repair,bounded_execution]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dpi',type=int,default=300)
    parser.add_argument('--only',choices=[f.__name__ for f in FIGURES])
    args=parser.parse_args()
    pdfmetrics.registerFont(TTFont(FONT,str(FONT_PATH)))
    for fn in FIGURES:
        if not args.only or args.only==fn.__name__:
            fn(args.dpi)
    manifest=ROOT/'semantic_manifest.json'
    records=RECORDS
    if args.only and manifest.exists():
        previous=json.loads(manifest.read_text())['figures']
        mapping={r['stem']:r for r in previous}
        mapping.update({r['stem']:r for r in records})
        records=list(mapping.values())
    manifest.write_text(json.dumps(dict(
        source='Author-approved report_1007_v1_full.md; v2 artifact contract',
        status='Constructed mechanisms, not measured results',
        generator='generate_figures.py',
        font=str(FONT_PATH),
        svg_font_note='Editable vector text; explicit system fallbacks. Embedded-font PDF and 300 dpi PNG are print-canonical.',
        figures=records),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
