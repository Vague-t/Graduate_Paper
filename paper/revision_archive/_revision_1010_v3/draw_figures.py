"""Seven source-grounded method diagrams; Python/matplotlib only, no empirical data."""
from pathlib import Path
import os,sys,json,hashlib
W=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(W/'mpl-cache'))
sys.path.insert(0,str(W/'vendor'))
SK=W/'qa_tools'
sys.path.insert(0,str(SK))
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
from matplotlib import font_manager
from audit_panel_alignment import require_matplotlib_panel_alignment

FONT=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
font_manager.fontManager.addfont(str(FONT))
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial Unicode MS','DejaVu Sans'],
    'font.size':8.6,'svg.fonttype':'none','pdf.fonttype':42,'ps.fonttype':42,
    'axes.linewidth':0.7,'text.color':'#253541','figure.facecolor':'white',
    'savefig.facecolor':'white','text.usetex':False})
OUT=W/'figures';OUT.mkdir(exist_ok=True)
BLUE='#38698B';TEAL='#2E7877';ORANGE='#AF743B';GRAY='#687781';INK='#253541'
PALE_BLUE='#EEF4F8';PALE_TEAL='#EDF5F4';PALE_ORANGE='#FBF3E9';PALE_GRAY='#F4F6F7';LINE='#BAC5CC'
records=[]

class Diagram:
    def __init__(self,name,h):
        self.name=name;self.h=h
        width_in=157/25.4
        self.fig=plt.figure(figsize=(width_in,h/25.4))
        self.ax=self.fig.add_axes([0,0,1,1]);self.ax.set_xlim(0,157);self.ax.set_ylim(h,0);self.ax.axis('off')
        self.texts=[];self.boxes=[]
    def text(self,x,y,s,fs=8.6,color=INK,ha='center',va='center',weight='normal',**kw):
        t=self.ax.text(x,y,s,fontsize=fs,color=color,ha=ha,va=va,fontweight=weight,linespacing=1.32,**kw)
        self.texts.append(t);return t
    def box(self,x,y,w,h,s='',fill='white',edge=LINE,fs=8.6,lw=.65,dash=False):
        p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0,rounding_size=1.2',facecolor=fill,edgecolor=edge,linewidth=lw,linestyle=(0,(4,3)) if dash else 'solid',zorder=1)
        self.ax.add_patch(p)
        if s:
            t=self.text(x+w/2,y+h/2,s,fs=fs,zorder=3)
            self.boxes.append((p,t))
        return p
    def title(self,x,y,s,color=BLUE):self.text(x,y,s,fs=9.3,color=color,ha='left')
    def line(self,pts,color=LINE,lw=.7,dash=False):
        xs,ys=zip(*pts);self.ax.plot(xs,ys,color=color,lw=lw,ls=(0,(4,3)) if dash else '-',zorder=1)
    def arrow(self,pts,color=INK,dash=False,lw=.9):
        if len(pts)>2:self.line(pts[:-1],color,lw,dash)
        p=FancyArrowPatch(pts[-2],pts[-1],arrowstyle='-|>',mutation_scale=7.5,linewidth=lw,color=color,linestyle=(0,(4,3)) if dash else '-',shrinkA=0,shrinkB=0,zorder=2)
        self.ax.add_patch(p)
    def node(self,x,y,label,color=GRAY,fill='white',w=13,h=8):self.box(x-w/2,y-h/2,w,h,label,fill,color,fs=8.2)
    def legend(self,y):
        self.arrow([(4,y),(13,y)],color=GRAY);self.text(16,y,'数据／表示',fs=7.8,ha='left',color=GRAY)
        self.arrow([(51,y),(60,y)],color=GRAY,dash=True);self.text(63,y,'监督／控制',fs=7.8,ha='left',color=GRAY)
    def save(self):
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        bad=[]
        for p,t in self.boxes:
            a=p.get_window_extent(renderer);b=t.get_window_extent(renderer)
            if b.x0<a.x0+1 or b.x1>a.x1-1 or b.y0<a.y0+1 or b.y1>a.y1-1:bad.append(t.get_text())
        assert not bad,('text exceeds node',self.name,bad)
        require_matplotlib_panel_alignment(self.fig,json_out=OUT/f'{self.name}.alignment.json',tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
        self.fig.savefig(OUT/f'{self.name}.svg')
        self.fig.savefig(OUT/f'{self.name}.pdf')
        self.fig.savefig(OUT/f'{self.name}.png',dpi=600)
        self.fig.savefig(OUT/f'{self.name}.preview.png',dpi=300)
        records.append({'name':self.name,'width_mm':157,'height_mm':self.h,'dpi':600,'axes':1,'kind':'mechanism schematic; not empirical evidence','text_count':len(self.texts),'minimum_source_font_pt':min(t.get_fontsize() for t in self.texts),'sha256':{ext:hashlib.sha256((OUT/f'{self.name}.{ext}').read_bytes()).hexdigest() for ext in ['svg','pdf','png']}})
        plt.close(self.fig)

def argument_example():
    d=Diagram('argument_example',94)
    d.title(4,5,'原始文本',GRAY);d.text(153,5,'人为构造的教学片段',fs=7.8,ha='right',color=GRAY)
    d.box(4,10,149,27,fill=PALE_GRAY,edge=PALE_GRAY)
    for y,s in [(16,'学校应该增加图书馆经费。'),(23,'图书馆现有座位不足，而且开放时间偏短。'),(30,'图书馆应该延长开放时间。食堂应该增加餐食窗口。')]:d.text(8,y,s,ha='left')
    d.arrow([(47,37),(47,44)],color=GRAY);d.arrow([(126,37),(126,44)],color=GRAY)
    d.title(4,47,'组件识别：完整跨度与类型',BLUE)
    d.title(105,47,'关系识别',TEAL)
    d.line([(99,49),(99,90)])
    rows=[(56,'c1  Claim','学校应该增加图书馆经费'),(67,'c2  Premise','图书馆现有座位不足，\n而且开放时间偏短'),(79,'c3  Claim','图书馆应该延长开放时间'),(89,'c4  Claim','食堂应该增加餐食窗口')]
    for y,head,body in rows:
        d.text(4,y-2.6,head,fs=7.7,color=BLUE,ha='left')
        d.text(30,y,body,fs=8.2,ha='left')
    d.node(111,69,'c2',TEAL,PALE_TEAL,w=11)
    d.node(146,58,'c1',TEAL,PALE_TEAL,w=11)
    d.node(146,80,'c3',TEAL,PALE_TEAL,w=11)
    d.arrow([(116.5,67),(127,58),(140.5,58)],color=TEAL)
    d.arrow([(116.5,71),(127,80),(140.5,80)],color=TEAL)
    d.text(126,54,'Support',fs=7.6,color=TEAL)
    d.text(126,84,'Support',fs=7.6,color=TEAL)
    d.text(127,91,'c2 → c4：NONE（无边）',fs=7.6,color=GRAY)
    d.save()

def research_relationship():
    d=Diagram('research_relationship',92)
    d.box(10,4,137,18,'共同依赖：关系以完整组件为端点\n跨度、类型或存在性变化后，依赖关系须同步处理',PALE_GRAY,PALE_GRAY)
    d.arrow([(78.5,22),(78.5,26),(39,26),(39,32)],color=GRAY)
    d.arrow([(78.5,26),(118,26),(118,32)],color=GRAY)
    for x,color,bg,title,a,b in [(4,BLUE,PALE_BLUE,'训练阶段  监督保持','改变文本表达\n风险：类型或关系标签漂移','关系影响域检查 + 成对学习\n保持监督与图因素对应'),(83,TEAL,PALE_TEAL,'推理阶段  结构恢复','固定原文，修改预测组件\n风险：关系仍绑定旧端点','依赖闭合事务 + 原子提交\n联合恢复组件与关系')]:
        d.title(x+3,35,title,color)
        d.box(x,41,70,15,a,'white',LINE)
        d.arrow([(x+35,56),(x+35,61)],color=color)
        d.box(x,61,70,15,b,bg,color)
    d.box(15,83,127,7,'继承基础：ICIC专项建模与MCR初始图选择',PALE_GRAY,PALE_GRAY,fs=8.2)
    d.arrow([(39,83),(39,76)],color=GRAY,dash=True);d.arrow([(118,83),(118,76)],color=GRAY,dash=True)
    d.save()

def framework():
    d=Diagram('framework',103)
    d.title(4,5,'训练阶段  离线增强与成对学习',BLUE)
    for x,s,fill in [(4,'训练原文与金标\n指定槽位改写','white'),(57,'关系影响域检查\n丢弃不合格变体',PALE_BLUE),(110,'原文 + 合格增强文\n成对图因素学习',PALE_BLUE)]:d.box(x,12,43,16,s,fill,BLUE if fill!= 'white' else LINE)
    d.arrow([(47,20),(57,20)],BLUE);d.arrow([(100,20),(110,20)],BLUE)
    d.text(4,36,'ICIC共享生成器：基础模型冻结；\n适配模块与训练辅助头可训练',ha='left',fs=8.1,color=GRAY)
    d.box(110,34,43,11,'训练后生成器\n移除辅助头',PALE_GRAY,LINE,fs=8.3)
    d.arrow([(131.5,28),(131.5,34)],BLUE)
    d.line([(4,49),(153,49)],LINE)
    d.title(4,54,'推理阶段  固定原文上的结构恢复',TEAL)
    for x,s in [(4,'测试原文\n不提供金标'),(57,'完整候选 → MCR\n共用合法化得初始图'),(110,'固定候选宇宙\n冻结完整对象分')]:d.box(x,61,43,14,s,PALE_GRAY if x==4 else 'white',LINE,fs=8.2)
    d.arrow([(47,68),(57,68)],TEAL);d.arrow([(100,68),(110,68)],TEAL)
    d.arrow([(131.5,45),(131.5,51),(78.5,51),(78.5,61)],GRAY,dash=True)
    for x,s in [(110,'组件与关系\n依赖闭合事务'),(57,'完整方案检查\n提交或整体回退'),(4,'预算内迭代\n输出最终完整图')]:d.box(x,82,43,12,s,PALE_TEAL,TEAL,fs=8.2)
    d.arrow([(131.5,75),(131.5,82)],TEAL);d.arrow([(110,88),(100,88)],TEAL);d.arrow([(57,88),(47,88)],TEAL)
    d.legend(99)
    d.save()

def augmentation():
    d=Diagram('augmentation',114)
    d.title(4,5,'只改写A = {c1, c2}，核对全部受影响因素',BLUE)
    d.box(4,13,70,66,fill=PALE_BLUE,edge=BLUE,dash=True)
    d.text(39,19,'可改写组件',color=BLUE);d.text(118,19,'只读组件',color=GRAY)
    d.box(9,25,60,15,'c1 · Claim\n学校应该增加图书馆经费','white',BLUE,fs=8.2)
    d.box(9,59,60,16,'c2 · Premise\n图书馆现有座位不足，\n而且开放时间偏短','white',BLUE,fs=8.2)
    d.box(94,25,59,15,'c3 · Claim\n图书馆应该延长开放时间','white',GRAY,fs=8.2)
    d.box(94,59,59,16,'c4 · Claim\n食堂应该增加餐食窗口','white',GRAY,fs=8.2)
    d.arrow([(23,59),(23,40)],BLUE);d.text(46,49,'内部\nSupport',fs=8.1,color=BLUE)
    d.arrow([(69,63),(83,63),(83,32.5),(94,32.5)],TEAL)
    d.text(122,46,'跨边界 Support',fs=8.2,color=TEAL)
    d.text(123,52,'c2 → c4：NONE，无边',fs=7.8,color=GRAY)
    d.text(78.5,85,'影响域：与A相交的全部合法端点组合；图中仅列举部分',fs=8.1,color=GRAY)
    for x,s in [(4,'指定槽位改写\n保留其余文本'),(57,'全文回填与重分词\n更新全部坐标及端点'),(110,'核对完整影响域\n任一标签漂移即拒绝')]:d.box(x,92,43,14,s,PALE_BLUE if x==110 else 'white',BLUE if x==110 else LINE,fs=8.1)
    d.arrow([(47,99),(57,99)],BLUE);d.arrow([(100,99),(110,99)],BLUE)
    d.text(78.5,111,'只读组件也可能位移；内部／跨边界与正关系／NONE分别核对',fs=7.8,color=GRAY)
    d.save()

def training_architecture():
    d=Diagram('training_architecture',148)
    d.title(4,5,'两个输入视图',BLUE);d.title(92,5,'监督与对应',ORANGE)
    d.box(4,10,73,15,'x：指令 + 原文\nx′：指令 + 合格增强文',PALE_BLUE,BLUE)
    d.box(92,10,61,15,'金标跨度／标签与组件对应φ\n不拼入回答前的输入上下文',PALE_ORANGE,ORANGE,fs=8.2)
    d.arrow([(40.5,25),(40.5,32)],BLUE)
    d.box(4,32,149,39,fill=PALE_GRAY,edge=LINE)
    d.title(8,38,'两视图共享生成器（继承ICIC）',GRAY)
    d.box(8,43,44,15,'Qwen2.5-7B-Instruct\n基础权重W0：冻结','white',GRAY,fs=8.0)
    d.box(57,43,43,15,'全局LoRA\n可训练；全部位置','white',BLUE,fs=8.2)
    d.box(105,43,44,15,'条件连续提示\n可训练；各视图独立触发','white',BLUE,fs=8.1)
    d.text(78.5,65,'结论专用LoRA：仅闭合结论类型后的组件字段启用，其余位置门控为0',fs=7.8,color=GRAY)
    d.box(4,78,68,14,'输入端表示 h_input、h_end\n回答开始前提取',PALE_BLUE,BLUE,fs=8.3)
    d.box(90,78,63,14,'答案生成与句子辅助头\n继承生成目标与句子监督','white',GRAY,fs=8.3)
    d.arrow([(38,71),(38,78)],BLUE);d.arrow([(121.5,71),(121.5,78)],GRAY)
    d.box(4,98,68,15,'新增：组件类型头与关系状态头\n关系状态含NONE；仅训练使用',PALE_BLUE,BLUE,fs=8.2)
    d.box(90,98,63,15,'因素金标监督 + JS对齐\n组件A+与关系影响域D_A',PALE_BLUE,BLUE,fs=8.2)
    d.arrow([(38,92),(38,98)],BLUE);d.arrow([(72,105.5),(90,105.5)],BLUE)
    # Supervision follows a reserved right-side lane, never through generator inputs.
    d.arrow([(153,17.5),(156,17.5),(156,85),(153,85)],ORANGE,dash=True)
    d.arrow([(156,85),(156,105.5),(153,105.5)],ORANGE,dash=True)
    d.box(4,119,149,10,'联合目标：继承损失 + 因素监督／成对对齐；按源文档归一化',PALE_GRAY,LINE,fs=8.2)
    d.arrow([(121.5,113),(121.5,119)],BLUE)
    d.arrow([(153,90),(154.5,90),(154.5,124),(153,124)],GRAY)
    d.text(4,135,'因素梯度更新新增头、全局LoRA及触发的提示；不直接更新结论专用LoRA。',fs=7.7,ha='left',color=GRAY)
    d.text(4,140,'基础权重始终冻结；辅助头在开发评价和测试时移除。',fs=7.7,ha='left',color=GRAY)
    d.legend(145)
    d.save()

def repair():
    d=Diagram('repair',131)
    d.title(4,5,'原文固定，预测对象及其关系共同变化',TEAL)
    d.box(4,11,149,12,'“图书馆现有座位不足，而且开放时间偏短”',PALE_GRAY,PALE_GRAY)
    d.box(4,30,64,20,'旧c2 · Premise\n图书馆现有座位不足\n（短跨度）','white',GRAY,fs=8.5)
    d.box(89,30,64,20,'新c2 · Premise\n图书馆现有座位不足，\n而且开放时间偏短',PALE_TEAL,TEAL,fs=8.5)
    d.arrow([(68,40),(89,40)],TEAL);d.text(78.5,35,'替换',fs=8.1,color=TEAL)
    d.text(78.5,56,'跨度不同即为不同对象；不按显示ID继承旧边',fs=8.2,color=GRAY)
    d.box(4,62,149,13,'删除旧对象全部入边与出边；重判新对象的全部合法关系组合（含NONE）','white',LINE,fs=8.2)
    d.arrow([(121,50),(121,62)],TEAL)
    d.box(4,81,149,13,'固定域外关系并复核整图约束；失效已选槽位最小扩域且计费，仍失败则拒绝','white',LINE,fs=8.1)
    d.arrow([(78.5,75),(78.5,81)],TEAL)
    d.box(4,100,149,13,'接受门：组件与关系分项效用分别不降；总增益超过正阈值；整图合法且预算内',PALE_ORANGE,ORANGE,fs=8.0)
    d.arrow([(78.5,94),(78.5,100)],TEAL)
    d.box(4,119,70,10,'全部通过：组件与关系原子提交',PALE_TEAL,TEAL,fs=8.0)
    d.box(83,119,70,10,'任一失败：整体回退，保留原图',PALE_GRAY,GRAY,fs=8.0)
    d.arrow([(39,113),(39,119)],TEAL,dash=True);d.arrow([(118,113),(118,119)],GRAY,dash=True)
    d.save()

def bounded_execution():
    d=Diagram('bounded_execution',148)
    d.title(4,5,'多候选驱动的有界执行',TEAL)
    steps=[(11,15,'01  初始化','原文 → K个完整候选 → MCR与共用合法化 → 初始合法图'),
           (32,15,'02  冻结','候选宇宙、完整对象分、效用及资源配置；辅助头不参与推理'),
           (53,15,'03  取批','按状态枚举六类提议并轮转；批长6；每轮尝试32、接受3'),
           (74,22,'04  闭合评估','冲突闭合 → 端点依赖域 → 最小扩域 → 局部ILP\n超时可行解保留非最优身份；复核整图、分项、总增益和预算')]
    for y,h,title,body in steps:
        d.box(12,y,141,h,fill=PALE_TEAL if y>=53 else PALE_GRAY,edge=TEAL if y>=53 else LINE)
        d.text(17,y+4.3,title,fs=8.2,color=TEAL,ha='left')
        d.text(17,y+10.3,body,fs=7.8,ha='left',va='top' if y==74 else 'center')
    for y in [26,47,68]:d.arrow([(82.5,y),(82.5,y+6)],TEAL)
    d.box(12,103,68,17,'有合格项：按效用、编辑、键择优\n再查接受、编辑及提交资源\n原子提交；不重复增加尝试',PALE_TEAL,TEAL,fs=7.9)
    d.box(86,103,67,17,'无合格项：保留独立no-op\n有评估资源则继续余批\n队列或评估资源耗尽则停止','white',GRAY,fs=7.9)
    d.arrow([(46,96),(46,103)],TEAL,dash=True);d.arrow([(119.5,96),(119.5,103)],GRAY,dash=True)
    d.arrow([(12,111.5),(6,111.5),(6,60.5),(12,60.5)],TEAL,dash=True)
    d.arrow([(153,111.5),(155.5,111.5),(155.5,60.5),(153,60.5)],GRAY,dash=True)
    d.text(78.5,126,'同状态续游标；未见状态建队列。所有尝试计费，只有实际提交计编辑。',fs=7.7,color=GRAY)
    d.box(12,133,141,9,'停止／中断：返回最后完整合法图与原因；提交失败恢复完整状态',PALE_GRAY,LINE,fs=8.0)
    d.arrow([(119.5,120),(119.5,123)],GRAY,dash=True);d.arrow([(119.5,129),(119.5,133)],GRAY,dash=True)
    d.text(78.5,146,'实线：数据／表示；虚线：分支与循环控制',fs=7.7,color=GRAY)
    d.save()

if __name__=='__main__':
    funcs=[argument_example,research_relationship,framework,augmentation,training_architecture,repair,bounded_execution]
    selected=set(sys.argv[1:])
    for f in funcs:
        if not selected or f.__name__ in selected:f()
    old=json.loads((W/'figure_exports.json').read_text()) if (W/'figure_exports.json').exists() else []
    names={r['name'] for r in records};all_records=[r for r in old if r['name'] not in names]+records
    (W/'figure_exports.json').write_text(json.dumps(all_records,ensure_ascii=False,indent=2)+'\n')
    print('Exported',','.join(r['name'] for r in records))
