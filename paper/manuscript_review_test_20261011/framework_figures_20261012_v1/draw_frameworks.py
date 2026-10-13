"""Three source-grounded conceptual frameworks. No experimental values are plotted."""
from pathlib import Path
import os
import json

HERE = Path(__file__).resolve().parent
QA = HERE / "_work" / "qa"
QA.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(HERE / "_work" / "mpl-cache"))

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
from audit_panel_alignment import require_matplotlib_panel_alignment

font_manager.fontManager.addfont("/Library/Fonts/Arial Unicode.ttf")
mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial Unicode MS", "DejaVu Sans"],
    "font.size": 8.2, "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "text.usetex": False, "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.linewidth": 0.7,
})
INK = "#273540"
GREY = "#667580"
EDGE = "#8A969E"
BLUE = "#36769A"
AMBER = "#9E6E2E"
PALE_BLUE = "#EAF3F9"
PALE_AMBER = "#FBF1E0"
PALE_GREY = "#F1F4F6"
LIGHT_BLUE = "#F8FBFD"
LIGHT_AMBER = "#FFFCF7"
MM = 72 / 25.4
EXPORTS = []


class Diagram:
    def __init__(self, name, height):
        self.name, self.height = name, height
        width_in = 180 / 25.4
        self.fig = plt.figure(figsize=(width_in, height / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set(xlim=(0, 180), ylim=(height, 0))
        self.ax.axis("off")
        self.boxtexts, self.texts, self.module_rects = [], [], []

    def text(self, x, y, value, fs=8.2, color=INK, ha="center", va="center", **kwargs):
        artist = self.ax.text(x, y, value, fontsize=fs, color=color, ha=ha, va=va,
                              linespacing=1.35, zorder=5, **kwargs)
        self.texts.append(artist)
        return artist

    def box(self, x, y, w, h, value="", fill="white", edge=EDGE, fs=8.2, dash=False, radius=1.5):
        patch = FancyBboxPatch((x, y), w, h,
                              boxstyle=f"round,pad=0,rounding_size={radius}",
                              facecolor=fill, edgecolor=edge, linewidth=.75,
                              linestyle=(0, (4, 3)) if dash else "-", zorder=2)
        self.ax.add_patch(patch)
        if value:
            t = self.text(x+w/2, y+h/2, value, fs=fs)
            self.boxtexts.append((patch, t))
        self.module_rects.append({"text": value, "x": x, "y": y, "w": w, "h": h})
        return patch

    def group(self, x, y, w, h, title, color=BLUE, fill=LIGHT_BLUE):
        p = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0,rounding_size=2",
                          facecolor=fill, edgecolor=color, linewidth=.8,
                          linestyle=(0, (4, 3)), zorder=0)
        self.ax.add_patch(p)
        self.text(x+3, y+4.2, title, fs=9.1, color=color, ha="left")

    def line(self, points, color=INK, lw=.8, dash=False):
        xs, ys = zip(*points)
        self.ax.plot(xs, ys, color=color, lw=lw,
                     ls=(0, (3.5, 2.5)) if dash else "-", zorder=1,
                     solid_capstyle="butt", solid_joinstyle="round")

    def arrow(self, points, color=INK, dash=False, lw=.8):
        if len(points) > 2:
            self.line(points[:-1], color, lw, dash)
        self.ax.add_patch(FancyArrowPatch(points[-2], points[-1],
                         arrowstyle="-|>", mutation_scale=7,
                         linewidth=lw, color=color, shrinkA=0, shrinkB=0,
                         linestyle=(0, (3.5, 2.5)) if dash else "-", zorder=3))

    def node(self, x, y, label, fill="white", edge=EDGE, radius=3.4):
        self.ax.add_patch(Circle((x, y), radius, facecolor=fill, edgecolor=edge,
                                lw=.8, zorder=3))
        self.text(x, y, label, fs=8)

    def title(self, title, subtitle):
        self.text(90, 5.5, title, fs=12, color=INK)
        self.text(90, 12, subtitle, fs=7.7, color=GREY)

    def save(self):
        self.fig.canvas.draw()
        require_matplotlib_panel_alignment(
            self.fig, json_out=QA / f"{self.name}.alignment.json",
            overlay_svg=QA / f"{self.name}.alignment.svg",
            tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True,
        )
        renderer = self.fig.canvas.get_renderer()
        containment = []
        for patch, t in self.boxtexts:
            p, q = patch.get_window_extent(renderer), t.get_window_extent(renderer)
            ok = (q.x0 >= p.x0 + .5 and q.x1 <= p.x1 - .5 and
                  q.y0 >= p.y0 + .5 and q.y1 <= p.y1 - .5)
            containment.append({"text": t.get_text(), "contained": bool(ok),
                                "box_pt": [v*72/self.fig.dpi for v in p.bounds],
                                "text_pt": [v*72/self.fig.dpi for v in q.bounds]})
        report = {
            "single_canvas_alignment": "NOT APPLICABLE: semantic groups on one axes, no comparable quantitative panels",
            "dimensions_mm": [180, self.height], "module_rects_mm": self.module_rects,
            "text_containment": containment,
            "all_contained": all(r["contained"] for r in containment),
        }
        (QA / f"{self.name}.geometry.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        if not report["all_contained"]:
            print("CONTAINMENT REVIEW", self.name, [r["text"] for r in containment if not r["contained"]])
        for ext in ["pdf", "svg", "png"]:
            self.fig.savefig(HERE / f"{self.name}.{ext}", dpi=600, facecolor="white")
        self.fig.savefig(QA / f"{self.name}.preview.png", dpi=300, facecolor="white")
        EXPORTS.append({"name": self.name, "dimensions_mm": [180, self.height],
                        "minimum_font_pt": min(t.get_fontsize() for t in self.texts)})
        plt.close(self.fig)


def overview():
    d = Diagram("01_论文总体框架", 166)
    d.title("可靠监督与依赖闭合协同的论辩挖掘框架", "从训练阶段的监督保持，到推理阶段的完整结构决策")
    d.group(6, 19, 168, 49, "(a)  创新点一：关系影响域约束的增强与成对学习", BLUE, LIGHT_BLUE)
    d.box(12, 33, 26, 21, "训练原文\n原生标注图", PALE_GREY)
    d.box(47, 33, 34, 21, "局部改写与标注输运\n关系影响域审核\n可靠对应与因素掩码", PALE_BLUE, BLUE, fs=8)
    d.box(90, 33, 43, 21, "共享生成器上的成对学习\n原文生成＋可靠因素监督\n组件／关系分布对齐", PALE_BLUE, BLUE, fs=8)
    d.box(142, 33, 26, 21, "训练后的\n生成器 θ", PALE_GREY)
    for a,b in [(38,47),(81,90),(133,142)]: d.arrow([(a,43.5),(b,43.5)])
    d.text(90, 61, "原文保留完整监督；增强仅学习通过审核的因素；辅助头仅用于训练。", fs=7.8, color=GREY)

    d.arrow([(155,54),(155,75),(177,75),(177,91),(60.5,91),(60.5,96)], color=BLUE)
    d.text(136, 75, "生成器参数传递", fs=7.5, color=BLUE)
    d.group(6, 81, 168, 57, "(b)  创新点二：多候选驱动的依赖闭合论辩图修正", AMBER, LIGHT_AMBER)
    d.box(12, 96, 25, 21, "待预测原文 x\n文本保持不变", PALE_GREY, fs=8)
    d.box(46, 96, 29, 21, "多候选生成\n组件假设＋完整图", PALE_GREY, fs=8)
    d.box(84, 96, 27, 21, "整图重排序\n共同合法化\n初始图 G₀", PALE_GREY, fs=8)
    d.box(120, 96, 27, 21, "依赖闭合决策\n候选与评分冻结\n共同求解与接受", PALE_AMBER, AMBER, fs=7.8)
    d.box(156, 96, 12, 21, "输出\n完整\n论辩图", PALE_GREY, fs=8)
    for a,b in [(37,46),(75,84),(111,120),(147,156)]: d.arrow([(a,106.5),(b,106.5)])
    d.box(47, 123, 100, 10, "独立对象评分器 qC / qR：训练内 OOF 候选拟合，开发校准与策略选择", fill="white", edge=AMBER, fs=7.4)
    d.arrow([(133.5,123),(133.5,117)], color=AMBER)
    d.text(29, 128, "冻结后评分", fs=7.5, color=AMBER)

    d.box(12, 144, 156, 11, "统一评价：严格组件／完整关系 F1  ·  训练×推理四格对照  ·  误改与成本分析", PALE_GREY, fs=8)
    d.arrow([(162,117),(178,117),(178,149.5),(168,149.5)])
    for x, color, label in [(17, PALE_BLUE, "新增训练机制"),(66, PALE_AMBER, "新增推理机制"),(115, PALE_GREY, "继承模块／阶段接口")]:
        d.ax.add_patch(Rectangle((x,159),3,3,facecolor=color,edgecolor=EDGE,lw=.5))
        d.text(x+5,160.5,label,fs=7.4,ha="left",color=GREY)
    d.save()


def training():
    d = Diagram("02_创新点一_可靠因素成对学习", 188)
    d.title("关系影响域约束的增强与成对学习框架", "核心：先建立可靠监督对应，再约束原文与增强视图的因素预测")
    d.group(6, 19, 168, 79, "(a)  可靠增强视图构造", BLUE, LIGHT_BLUE)
    d.box(11, 32, 29, 19, "训练原文 x\n金标图 G=(C,R)", PALE_GREY, fs=8)
    d.box(48, 32, 33, 19, "选定改写组件 A\n定义关系影响域 D_A", PALE_BLUE, BLUE, fs=8)
    d.box(89, 32, 35, 19, "槽位改写与全文回填\n更新坐标及全部端点 φ", PALE_BLUE, BLUE, fs=7.9)
    d.box(132, 32, 37, 19, "组件检查＋关系审核\n形成可靠掩码 mC / mR", PALE_BLUE, BLUE, fs=7.9)
    for a,b in [(40,48),(81,89),(124,132)]: d.arrow([(a,41.5),(b,41.5)])
    d.text(34,58,"影响域：内部与跨边界",fs=8,color=BLUE)
    d.text(90,58,"身份输运：φ(C)=C′",fs=8,color=BLUE)
    d.text(146,58,"因素状态决定损失入口",fs=8,color=BLUE)
    d.line([(62,62),(62,91)],color="#C5D6E0",lw=.6)
    d.line([(117,62),(117,91)],color="#C5D6E0",lw=.6)
    d.box(14,64,22,24,fill=PALE_BLUE,edge=BLUE,dash=True)
    d.text(17,67,"A",fs=7.4,color=BLUE)
    d.node(25,71,"a",PALE_BLUE,BLUE,2.7)
    d.node(25,82,"b",PALE_BLUE,BLUE,2.7)
    d.node(50,82,"c",radius=2.7)
    d.arrow([(25,79.3),(25,73.7)],color=BLUE)
    d.arrow([(47.3,82),(27.7,82)],color=BLUE)
    d.text(45,74.5,"跨边界",fs=7.4,color=GREY)
    d.text(36,92,"正关系与 NONE 均核查",fs=7.4,color=GREY)
    d.box(67,65,20,12,"c : [b,e)",PALE_GREY,fs=7.8)
    d.box(93,65,20,12,"c′ : [b′,e′)",PALE_BLUE,BLUE,fs=7.8)
    d.arrow([(87,71),(93,71)],color=BLUE)
    d.text(90,83,"组件双射，非 token 双射\n只读组件坐标也同步更新",fs=7.5,color=GREY)
    d.text(121,68,"稳定且端点有效 → m=1",fs=7.6,ha="left")
    d.text(121,76,"变化／待定／未审 → m=0",fs=7.6,ha="left")
    d.text(121,86,"组件检查失败：拒绝视图\n关系不确定：屏蔽该因素",fs=7.5,ha="left",color=GREY)

    d.box(13,103,154,10,"构造输出：增强全文 x′、全部组件对应 φ、可靠因素掩码；原文与金标始终保留",PALE_BLUE,BLUE,fs=7.8)
    d.arrow([(150.5,98),(150.5,103)],color=BLUE)
    d.arrow([(90,113),(90,119)],color=BLUE)

    d.group(6,119,168,46,"(b)  双视图共享表示与可靠因素学习",BLUE,LIGHT_BLUE)
    d.box(12,132,23,10,"原文 x",PALE_GREY,fs=8.3)
    d.box(12,149,23,10,"增强文 x′",PALE_BLUE,BLUE,fs=8.3)
    d.box(45,132,34,27,"共享生成器 θ\n冻结基础权重\nLoRA＋连续提示",PALE_GREY,fs=8)
    d.arrow([(35,137),(45,137)])
    d.arrow([(35,154),(45,154)],color=BLUE)
    d.box(89,132,31,27,"训练辅助头\n组件类型 pC\n关系状态 pR",PALE_BLUE,BLUE,fs=8)
    d.arrow([(79,145.5),(89,145.5)])
    d.box(130,132,38,27,"可靠标签监督 CE\n组件＋关系成对 JS\nφ 对齐，掩码筛选",PALE_BLUE,BLUE,fs=8)
    d.arrow([(120,145.5),(130,145.5)])

    d.box(12,170,156,10,"总目标：原文生成与句子监督 ＋ 可靠因素头监督 ＋ 组件／关系成对项",PALE_BLUE,BLUE,fs=8.1)
    d.arrow([(149,159),(149,170)],color=BLUE)
    d.text(90,184,"按源文档归一化；正关系与 NONE 分组平均；两视图均保留梯度；评价时移除辅助头。",fs=7.4,color=GREY)
    d.save()


def inference():
    d = Diagram("03_创新点二_依赖闭合修正", 207)
    d.title("多候选驱动的依赖闭合论辩图修正框架", "核心：组件变化及完整关系的增删，共同进入结构决策")
    d.group(6,19,168,39,"(a)  固定输入、候选与评分",AMBER,LIGHT_AMBER)
    d.box(11,31,46,21,"多候选生成与整图重排序\n共同合法化 → 初始图 G₀\n推理原文 x 保持不变",PALE_GREY,fs=8)
    d.box(67,31,46,21,"有限候选 U、V、P\n保留初始对象与竞争假设\nCDCP 保留完整源集合",PALE_AMBER,AMBER,fs=8)
    d.box(123,31,46,21,"独立完整对象评分 qC / qR\n训练内 OOF 拟合与校准\n搜索前冻结，缺分保持未知",PALE_AMBER,AMBER,fs=7.8)
    d.arrow([(57,41.5),(67,41.5)])
    d.arrow([(113,41.5),(123,41.5)])

    d.arrow([(146,52),(146,63),(120,63),(120,66)],color=AMBER)
    d.box(60,66,60,12,"检查评分齐备性与规模 n=|V|+|P|",PALE_AMBER,AMBER,fs=8)
    d.box(11,66,37,12,"全部缺分：返回 G₀",PALE_GREY,fs=8)
    d.arrow([(60,72),(48,72)],color=GREY)
    d.arrow([(74,78),(74,84),(47,84),(47,89)],color=AMBER)
    d.arrow([(106,78),(106,84),(133,84),(133,89)],color=AMBER)
    d.box(11,89,72,26,"全局路径：评分齐备且 n ≤ 2500\n全部组件与关系联合 ILP 选择\n相对 G₀ 计算净编辑与分项效用",PALE_AMBER,AMBER,fs=8.1)
    d.box(97,89,72,26,"局部路径：n > 2500 或部分缺分\n单对象提议＋依赖闭合＋局部 ILP\n逐次检查并累计编辑",PALE_AMBER,AMBER,fs=8.1)
    d.box(105,118,56,9,"可选扩展：集合局部 BR-J",fill="white",edge=AMBER,fs=7.6,dash=True)
    d.arrow([(163,115),(163,122.5),(161,122.5)],color=AMBER,dash=True)

    d.group(6,133,168,30,"(b)  求解内共同约束：冲突闭合与完整端点依赖",AMBER,LIGHT_AMBER)
    d.text(12,143,"替换前",fs=7.5,ha="left",color=GREY)
    d.text(101,143,"重建后",fs=7.5,ha="left",color=GREY)
    for x,l in [(28,"c"),(48,"b"),(68,"a")]:
        d.node(x,149,l,PALE_AMBER if l=="b" else "white",AMBER if l=="b" else EDGE)
    for a,b in [(31.4,44.6),(51.4,64.6)]: d.arrow([(a,149),(b,149)],color=AMBER)
    for x,l in [(118,"c"),(138,"b′"),(158,"a")]:
        d.node(x,149,l,PALE_AMBER if l=="b′" else "white",AMBER if l=="b′" else EDGE)
    for a,b in [(121.4,134.6),(141.4,154.6)]: d.arrow([(a,149),(b,149)],color=AMBER)
    d.arrow([(79,149),(99,149)],color=AMBER)
    d.text(48,158,"旧端点及全部入出关系计入删除",fs=7.5,color=GREY)
    d.text(136,158,"新端点与完整关系共同重建",fs=7.5,color=GREY)
    d.line([(47,115),(47,129),(101,129),(101,115)],color=AMBER)
    d.arrow([(90,129),(90,133)],color=AMBER)

    d.arrow([(90,163),(90,170)],color=AMBER)
    d.box(11,170,108,24,"完整状态复核与共同接受\nΔΦC ≥ 0，ΔΦR ≥ 0，ΔΦ > δ\n整图合法＋编辑预算满足＋所需评分有效",PALE_AMBER,AMBER,fs=8.3)
    d.box(135,170,34,10,"通过：提交完整图",PALE_GREY,fs=8)
    d.box(135,184,34,10,"未通过：保持合法旧图",PALE_GREY,fs=7.6)
    d.arrow([(119,176),(128,176),(128,175),(135,175)],color=AMBER)
    d.arrow([(119,188),(128,188),(128,189),(135,189)],color=GREY)
    d.text(90,200,"图中为机制示意；局部拒绝触及缺分对象的事务；代理效用提高不保证真实 F1 提高。",fs=7.4,color=GREY)
    d.save()


if __name__ == "__main__":
    overview()
    training()
    inference()
    (QA / "exports.json").write_text(json.dumps(EXPORTS, ensure_ascii=False, indent=2))
    import pymupdf
    joined = pymupdf.open()
    for record in EXPORTS:
        with pymupdf.open(HERE / f"{record['name']}.pdf") as doc:
            joined.insert_pdf(doc)
    joined.save(HERE / "三份框架图_合订版.pdf", garbage=4, deflate=True)
    joined.close()
    print(json.dumps(EXPORTS, ensure_ascii=False, indent=2))
