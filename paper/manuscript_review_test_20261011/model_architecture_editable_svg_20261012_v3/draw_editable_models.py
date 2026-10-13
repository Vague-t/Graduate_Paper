"""Editable model schematics; all illustrated objects are conceptual, not data."""
from pathlib import Path
import os, json, math, hashlib
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
QA = HERE / '_work' / 'qa'
QA.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(HERE / '_work' / 'mpl-cache'))
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch, Circle, Polygon
from audit_panel_alignment import require_matplotlib_panel_alignment

FONT = os.environ.get('THESIS_FIGURE_FONT', '/Library/Fonts/Arial Unicode.ttf')
font_manager.fontManager.addfont(FONT)
FONT_FAMILY = font_manager.FontProperties(fname=FONT).get_name()
mpl.rcParams.update({'font.family':'sans-serif', 'font.sans-serif':[FONT_FAMILY, 'Arial Unicode MS', 'DejaVu Sans'],
    'svg.fonttype':'none', 'pdf.fonttype':42, 'ps.fonttype':42, 'text.usetex':False,
    'figure.facecolor':'white', 'savefig.facecolor':'white', 'font.size':8})
INK='#202B35'; GREY='#697984'; EDGE='#A9B6C2'; BLUE='#2378B6'; CYAN='#1A9FA7'
PURPLE='#8268C7'; AMBER='#D58C20'; RED='#D36B84'; GREEN='#69A459'
PALE_BLUE='#EDF6FC'; PALE_AMBER='#FFF7E9'; PALE_GREY='#F0F3F5'
TOKEN=['#AAD7F6','#9CE1E8','#B8DEB3','#F9E5A3','#F2BFCE','#CDC2F1']
REPORT=[]

class Diagram:
    def __init__(self,name,height):
        self.name=name; self.width=1600; self.height=height; self.factor=200/1600*72/25.4
        width_in=200/25.4
        self.fig=plt.figure(figsize=(width_in, height/1600*width_in))
        self.ax=self.fig.add_axes([0,0,1,1]); self.ax.set(xlim=(0,1600),ylim=(height,0)); self.ax.axis('off')
        self.counter=0; self.section='canvas'; self.texts=[]; self.boxtexts=[]; self.objects=[]
    def obj(self,a,kind):
        self.counter+=1; ident=f'{self.section}-{kind}-{self.counter:04d}'
        a.set_gid(ident); self.objects.append({'id':ident,'kind':kind}); return a
    def text(self,x,y,s,size=23,color=INK,ha='center',va='center',weight='normal'):
        a=self.ax.text(x,y,s,fontsize=size*self.factor,color=color,ha=ha,va=va,
                       fontweight=weight,linespacing=1.35,zorder=8)
        self.obj(a,'text'); self.texts.append(a); return a
    def box(self,x,y,w,h,s='',fill='white',edge=EDGE,size=22,dash=False,r=7,lw=.7,z=3):
        a=FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0,rounding_size={r}',
            facecolor=fill,edgecolor=edge,linewidth=lw,linestyle=(0,(4,3)) if dash else '-',zorder=z)
        self.ax.add_patch(a); self.obj(a,'module')
        if s: self.boxtexts.append((a,self.text(x+w/2,y+h/2,s,size)))
        return a
    def rect(self,x,y,w,h,fill,edge=EDGE,lw=.55,z=4):
        a=Rectangle((x,y),w,h,facecolor=fill,edgecolor=edge,linewidth=lw,zorder=z)
        self.ax.add_patch(a); return self.obj(a,'rect')
    def poly(self,pts,fill,edge=EDGE,lw=.65,z=4):
        a=Polygon(pts,closed=True,facecolor=fill,edgecolor=edge,linewidth=lw,zorder=z)
        self.ax.add_patch(a); return self.obj(a,'polygon')
    def group(self,x,y,w,h,title,color=BLUE,fill='#FBFDFF',dash=True,size=26):
        self.box(x,y,w,h,fill=fill,edge=color,dash=dash,r=10,z=0,lw=.85)
        self.text(x+16,y+27,title,size,color,ha='left')
    def line(self,pts,color=INK,lw=.85,dash=False,z=6):
        xs,ys=zip(*pts); a,=self.ax.plot(xs,ys,color=color,lw=lw,ls=(0,(4,3)) if dash else '-',zorder=z)
        return self.obj(a,'line')
    def arrow(self,pts,color=INK,dash=False,lw=.9):
        if len(pts)>2: self.line(pts[:-1],color,lw,dash)
        a=FancyArrowPatch(pts[-2],pts[-1],arrowstyle='-|>',mutation_scale=8,linewidth=lw,
            color=color,shrinkA=0,shrinkB=0,linestyle=(0,(4,3)) if dash else '-',zorder=6)
        self.ax.add_patch(a); return self.obj(a,'arrow')
    def tokens(self,x,y,w,h,n=8,prime=False,labels=True):
        for i in range(n):
            self.rect(x+i*w/n,y,w/n-1,h,TOKEN[i%len(TOKEN)],BLUE,.55)
            if labels: self.text(x+(i+.5)*w/n,y+h/2,f'x{i+1}'+('′' if prime else ''),size=20)
    def matrix(self,x,y,w,h,rows=5,cols=6,purple=False):
        palette=['#E9E2FA','#D5C6F3','#BBA4E7'] if purple else ['#E2F1FD','#BEDFF7','#92C9EE']
        for r in range(rows):
            for c in range(cols): self.rect(x+c*w/cols,y+r*h/rows,w/cols,h/rows,palette[(r*3+c*2)%3],PURPLE if purple else BLUE,.35)
    def vector(self,x,y,w=64,h=15,color=BLUE,n=5):
        pale={BLUE:'#C0E3FB',PURPLE:'#DED1FA',CYAN:'#B4E9E9',GREEN:'#C9E5BC',RED:'#F4CED9',AMBER:'#FFE6B2'}.get(color,PALE_BLUE)
        for i in range(n): self.rect(x+i*w/n,y,w/n,h,pale,color,.45)
    def node(self,x,y,s='',fill=PALE_BLUE,edge=BLUE,r=17):
        a=Circle((x,y),r,facecolor=fill,edgecolor=edge,linewidth=.9,zorder=7);self.ax.add_patch(a);self.obj(a,'node')
        if s:self.text(x,y,s,size=22 if r>=16 else 18)
    def graph(self,x,y,w=120,h=85,labels=False,variant=0,changed=False):
        p=[(x+w*.12,y+h*.4),(x+w*.52,y+h*.12),(x+w*.52,y+h*.83),(x+w*.91,y+h*.43)]
        edges=[(0,1),(0,2),(1,3),(2,3)]
        if variant==0: edges.append((1,2))
        for a,b in edges:self.edge(p[a],p[b],12,color=AMBER if changed and (a==1 or b==1) else INK)
        for i,pt in enumerate(p):self.node(*pt,['a','b′' if changed else 'b','c','d'][i] if labels else '',[TOKEN[0],TOKEN[4],PALE_GREY,TOKEN[2]][i],BLUE if i==0 else RED if i==1 else GREY if i==2 else GREEN,r=12)
    def edge(self,a,b,r=17,color=INK,dash=False):
        dx=b[0]-a[0];dy=b[1]-a[1];dist=math.hypot(dx,dy)
        self.arrow([(a[0]+dx*r/dist,a[1]+dy*r/dist),(b[0]-dx*r/dist,b[1]-dy*r/dist)],color,dash,lw=.75)
    def hyper(self,x,y,w=160,h=80,labels=True):
        p1=(x,y+15);p2=(x,y+h-15);hub=(x+w*.45,y+h/2);tar=(x+w,y+h/2)
        self.edge(p1,hub,15);self.edge(p2,hub,15);self.arrow([(hub[0]+14,hub[1]),(tar[0]-16,tar[1])])
        self.node(*p1,'a' if labels else '',TOKEN[0],BLUE,r=16);self.node(*p2,'b' if labels else '',TOKEN[4],RED,r=16)
        self.poly([(hub[0],hub[1]-14),(hub[0]+14,hub[1]),(hub[0],hub[1]+14),(hub[0]-14,hub[1])],TOKEN[0],BLUE,z=7)
        self.node(*tar,'c' if labels else '',TOKEN[2],GREEN,r=16)
    def stack(self,x,y,w=125,h=145,label='Qwen2.5',layers=3,color=GREY):
        step=22; depth=15; front=PALE_GREY if color==GREY else PALE_BLUE
        self.box(x,y,w,h,fill=front,edge=color,r=4,z=3)
        self.poly([(x+w,y),(x+w+depth,y-depth),(x+w+depth,y+h-depth),(x+w,y+h)],'#D2DADF' if color==GREY else '#B4D5EF',color,z=4)
        for i in range(layers):
            yy=y+i*step
            self.poly([(x,yy),(x+depth,yy-depth),(x+w+depth,yy-depth),(x+w,yy)],'#E6EBEE' if color==GREY else '#D5E9F8',color,z=4)
            self.rect(x,yy,w,17,'#D6DDE2' if color==GREY else '#B5D8F3',color,z=5)
        self.text(x+w/2,y+h-(16 if h<90 else 32),label,size=23)
        if h>=125:self.text(x+w/2,y+h-10,'Transformer',size=18,color=GREY)
    def mlp(self,x,y,w=100,h=70,label='MLP'):
        self.box(x,y,w,h,fill=PALE_GREY,edge=GREY,r=7)
        top=max(38,h*.35); bottom=h-12
        ya=y+top+(bottom-top)*.2; yb=y+top+(bottom-top)*.8
        p=[[(x+16,ya),(x+16,yb)],[(x+w*.5,y+top),(x+w*.5,y+(top+bottom)/2),(x+w*.5,y+bottom)],[(x+w-16,ya),(x+w-16,yb)]]
        for layer1,layer2 in zip(p[:-1],p[1:]):
            for a in layer1:
                for b in layer2:self.line([a,b],EDGE,.4,z=4)
        for layer in p:
            for a in layer:self.node(*a,r=5,edge=GREY)
        self.text(x+w/2,y+19,label,size=18)
    def mask(self,x,y,labels,values,color=BLUE,cw=42):
        for i,(lab,val) in enumerate(zip(labels,values)):
            self.text(x+(i+.5)*cw,y,lab,size=20)
            self.box(x+i*cw,y+16,cw-2,27,str(val),fill=PALE_BLUE if val else PALE_GREY,edge=color if val else EDGE,size=20,r=2)
    def title(self,s,subtitle=None):
        self.text(800,33,s,size=38)
        if subtitle:self.text(800,66,subtitle,size=19,color=GREY)
    def finish(self):
        self.fig.canvas.draw()
        require_matplotlib_panel_alignment(self.fig,json_out=QA/f'{self.name}.alignment.json',
            overlay_svg=QA/f'{self.name}.alignment.svg',tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
        renderer=self.fig.canvas.get_renderer(); containment=[]
        for p,t in self.boxtexts:
            a=p.get_window_extent(renderer);b=t.get_window_extent(renderer)
            containment.append({'text':t.get_text(),'contained':bool(b.x0>=a.x0 and b.x1<=a.x1 and b.y0>=a.y0 and b.y1<=a.y1)})
        outside=[]
        for t in self.texts:
            a=t.get_window_extent(renderer); f=self.fig.bbox
            if a.x0<f.x0 or a.x1>f.x1 or a.y0<f.y0 or a.y1>f.y1:outside.append(t.get_text())
        self.fig.savefig(HERE/(self.name+'.svg'),dpi=300)
        self.fig.savefig(HERE/(self.name+'.pdf'),dpi=300)
        self.fig.savefig(HERE/(self.name+'.png'),dpi=300)
        self.fig.savefig(QA/f'{self.name}.preview.png',dpi=300)
        p=HERE/f'{self.name}.svg'; tree=ET.parse(p);root=tree.getroot();ns={'s':'http://www.w3.org/2000/svg'}
        ET.register_namespace('',ns['s']); ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
        ET.register_namespace('inkscape','http://www.inkscape.org/namespaces/inkscape')
        title=ET.Element('{'+ns['s']+'}title');title.text=self.name;root.insert(0,title)
        desc=ET.Element('{'+ns['s']+'}desc');desc.text='模型结构示意。文字、模块、矩阵与箭头均为独立可编辑对象；无嵌入位图。';root.insert(1,desc)
        for g in root.findall('.//s:g',ns):
            ident=g.get('id','')
            if any(ident==o['id'] for o in self.objects):
                visible=''.join(g.itertext()).strip()
                g.set('{http://www.inkscape.org/namespaces/inkscape}label',ident+((': '+visible) if visible else ''))
        tree.write(p,encoding='utf-8',xml_declaration=True)
        images=root.findall('.//s:image',ns);texts=root.findall('.//s:text',ns)
        assert not images and len(texts)>50
        record={'name':self.name,'dimensions_mm':[200,self.height/8],'minimum_font_pt':min(t.get_fontsize() for t in self.texts),
                'editable_text_elements':len(texts),'vector_paths':len(root.findall('.//s:path',ns)),'embedded_images':len(images),
                'stable_object_ids':len(self.objects),'text_containment':containment,'outside_canvas':outside,
                'alignment':'NOT APPLICABLE: single schematic canvas; no comparable quantitative axes'}
        (QA/f'{self.name}.objects.json').write_text(json.dumps(self.objects,ensure_ascii=False,indent=2))
        (QA/f'{self.name}.geometry.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
        REPORT.append(record);plt.close(self.fig)

def overview():
    d=Diagram('01_总体模型架构_可编辑',1000)
    d.title('可靠成对学习与依赖闭合的论辩挖掘模型')
    d.section='training-stage';d.group(15,70,1570,445,'(a) 训练：可靠因素成对学习',BLUE,fill='#FCFEFF',dash=False,size=29)
    d.section='paired-inputs';d.group(30,116,540,384,'',BLUE,size=23)
    d.text(49,170,'原文 x',22,ha='left');d.tokens(150,152,398,33)
    d.text(72,211,'组件对应 φ',22,BLUE,ha='left')
    d.box(70,226,275,103,fill='white',edge=BLUE,dash=True)
    d.box(80,230,155,92,fill='#F9F4FE',edge=PURPLE,dash=True)
    d.text(159,247,'A',19,PURPLE)
    for x,l,c in [(105,'c₁',TOKEN[0]),(207,'c₂',TOKEN[4]),(313,'c₃',TOKEN[2])]:d.node(x,280,l,c,r=19)
    d.arrow([(125,280),(187,280)]);d.arrow([(227,280),(293,280)])
    d.text(156,301,'r₁',19);d.text(260,301,'r₂',19)
    d.text(449,259,'槽位改写\n坐标与端点输运',21,BLUE)
    d.text(449,316,'关系影响域审核',21,BLUE)
    d.arrow([(548,169),(589,169),(589,210),(620,210)])
    d.text(49,365,'增强文 x′',22,ha='left');d.tokens(165,348,383,33,n=9,prime=True)
    d.arrow([(548,364),(589,364),(589,337),(620,337)])
    d.text(53,408,'可靠因素掩码',22,ha='left')
    d.text(76,475,'mC',22);d.mask(110,438,['c₁','c₂','c₃'],[1,1,1],cw=46)
    d.text(323,475,'mR',22);d.mask(360,438,['r₁','r₂','NONE'],[1,1,0],cw=59)
    d.section='shared-generator';d.group(604,116,240,294,'共享生成器 θ',BLUE,size=24)
    d.stack(626,198,128,164)
    d.box(779,188,49,158,fill=PALE_BLUE,edge=BLUE)
    d.text(803,217,'LoRA',19,BLUE)
    for yy in [249,273,297]:d.rect(788,yy,32,16,TOKEN[0],BLUE)
    d.arrow([(767,280),(779,280)]);d.node(804,335,'+',r=11)
    d.text(718,391,'基础权重冻结',21,GREY)
    d.section='representations';d.group(869,116,245,294,'隐藏状态与跨度表示',BLUE,size=22)
    for yy,lab,purp in [(192,'H（原文）',False),(310,'H′（增强文）',True)]:
        d.text(947,yy-12,lab,20);d.matrix(885,yy+4,85,68,4,5,purp)
        d.arrow([(845,yy+37),(880,yy+37)])
        d.arrow([(975,yy+37),(1004,yy+37)])
        for j,c in enumerate([BLUE,RED,GREEN]):d.vector(1016,yy+j*22,75,14,c)
    d.section='training-heads';d.group(1137,116,430,294,'辅助任务头（仅训练）',BLUE,size=24)
    for y,lab,sym in [(162,'组件类型头','C'),(286,'关系状态头','R')]:
        d.box(1150,y,300,105,fill='white',edge=EDGE)
        d.text(1163,y+19,lab,22,ha='left')
        for j,purp in enumerate([False,True]):
            d.text(1180,y+49+j*31,'p'+sym+('′' if purp else ''),22)
            d.vector(1209,y+41+j*31,113,20,PURPLE if purp else BLUE,n=6)
        d.text(1355,y+67,'} JS',25,BLUE)
    d.line([(1099,229),(1124,229),(1124,346),(1099,346)],BLUE,lw=.7)
    d.arrow([(1124,245),(1147,245)],BLUE)
    d.arrow([(1124,332),(1147,332)],BLUE)
    d.text(1506,241,'可靠监督\nCE + JS',23)
    d.arrow([(540,486),(580,486),(580,445),(1124,445),(1124,408),(1480,408),(1480,335)],BLUE,True,lw=.8)
    d.text(1300,434,'可靠因素监督选择',20,BLUE)
    d.section='original-objectives';d.box(864,462,690,37,fill=PALE_GREY,edge=EDGE,dash=True)
    d.text(1209,481,'仅原文 x：完整生成监督 Lgen  +  句子监督 Lsent',22)
    d.arrow([(754,370),(850,370),(850,481),(864,481)])
    d.section='inference-stage';d.group(15,535,1570,425,'(b) 推理：依赖闭合结构修正',AMBER,fill='#FFFEFB',dash=False,size=29)
    d.text(799,523,'参数 θ',18,BLUE)
    d.arrow([(724,411),(724,526),(441,526),(441,627),(459,627)],BLUE,True)
    d.section='candidate-generation';d.text(44,610,'输入原文 x',23,ha='left');d.tokens(40,635,382,35,n=6)
    d.text(230,703,'文本保持不变',21,GREY)
    d.stack(461,637,112,80,layers=2);d.arrow([(425,653),(455,653)])
    d.text(521,606,'生成器',22)
    for i in range(3):
        xx=626+i*151;d.box(xx,605,137,120,fill='white',edge=BLUE,dash=True)
        d.text(xx+24,623,'G'+str(i+1),21);d.graph(xx+10,643,113,61,variant=i)
        d.vector(xx+32,709,65,10,[BLUE,PURPLE,GREEN][i])
    d.arrow([(590,662),(621,662)])
    d.text(844,577,'多候选论辩图与组件假设',23)
    d.box(1098,639,120,67,'重排序\n共同合法化',PALE_AMBER,AMBER,size=21)
    d.arrow([(1068,670),(1093,670)])
    d.box(1367,604,181,123,fill='white',edge=AMBER,dash=True)
    d.text(1457,623,'初始图 G₀',23);d.graph(1380,649,150,63)
    d.arrow([(1220,670),(1361,670)])
    d.section='fixed-universe';d.group(30,754,651,111,'固定候选 U、V、P',AMBER,fill='white',size=22)
    d.text(120,802,'跨度 U',21);d.vector(60,824,115,16,BLUE)
    d.text(332,802,'带类型组件 V',21);d.text(332,835,'(b, e, t)',22)
    d.text(546,797,'完整关系 P',21);d.hyper(476,811,145,41,False)
    d.arrow([(842,727),(842,740),(348,740),(348,754)])
    d.section='independent-scorer';d.box(139,883,542,57,fill=PALE_BLUE,edge=BLUE,dash=True)
    d.text(154,911,'独立评分器',22,ha='left');d.box(301,891,97,40,'MLP',PALE_GREY,GREY,size=22)
    d.text(525,911,'qC / qR  冻结',22);d.arrow([(405,912),(433,912)])
    d.text(70,915,'原文 x',22);d.arrow([(107,912),(135,912)])
    d.arrow([(568,865),(568,882)],BLUE)
    d.arrow([(681,788),(702,788),(702,847),(723,847)],AMBER)
    d.section='joint-decision';d.group(727,754,552,186,'依赖闭合联合决策',AMBER,PALE_AMBER,size=24)
    d.box(746,805,514,33,'固定效用 Φ = wCΦC + wRΦR',fill='white',edge=AMBER,size=22)
    d.arrow([(684,912),(709,912),(709,822),(742,822)],BLUE)
    d.arrow([(1456,729),(1456,746),(1295,746),(1295,794),(1279,794)])
    d.text(854,854,'替换组件 b → b′',20)
    d.graph(759,875,192,50,labels=True,changed=True)
    d.box(996,850,114,57,'全局 ILP',PALE_BLUE,BLUE,size=21)
    d.text(1129,878,'或',22)
    d.box(1150,850,111,57,'有界局部',PALE_GREY,EDGE,size=20)
    d.text(1127,929,'结构 + 分项增益 + 预算约束',18)
    d.section='acceptance';d.box(1300,816,143,116,fill=PALE_AMBER,edge=AMBER)
    d.text(1371,834,'共同接受',21)
    d.text(1371,891,'ΔΦC ≥ 0\nΔΦR ≥ 0\nΔΦ > δ',20)
    d.arrow([(1280,872),(1296,872)])
    d.graph(1463,849,98,64);d.text(1510,821,'最终图',22,BLUE)
    d.arrow([(1447,872),(1466,872)])
    d.text(1493,946,'未通过：保留当前图',18,GREY)
    d.text(800,984,'模型结构示意  ·  蓝色：训练创新  /  橙色：推理创新  /  灰色：继承模块',20,GREY)
    d.finish()

def paired_model():
    d=Diagram('02_可靠成对学习模型_可编辑',1180)
    d.title('关系影响域约束的增强与成对学习模型')
    d.section='reliable-views';d.group(15,80,476,796,'1  可靠双视图构造',BLUE,fill='#FCFEFF',size=28)
    d.text(43,149,'原文 x',23,ha='left');d.tokens(133,131,329,31,8,labels=False)
    for y,prime in [(212,False),(466,True)]:
        d.box(68,y,241,137,fill='white',edge=BLUE,dash=True,r=15)
        d.text(188,y+23,'改写集合 A',23)
        for x,label,fill in [(108,'c₁',TOKEN[0]),(262,'c₂',TOKEN[4]),(431,'c₃',TOKEN[2])]:
            d.node(x,y+85,label+('′' if prime else ''),fill,r=20)
        d.arrow([(242,y+85),(129,y+85)])
        d.text(185,y+64,'r₁'+('′' if prime else ''),21)
        d.arrow([(410,y+85),(283,y+85)],GREY if prime else INK,dash=prime)
        d.text(358,y+64,'r₂′ 待定' if prime else 'r₂',20,GREY if prime else INK)
        d.text(187,y+119,'内部因素',21)
        d.text(366,y+121,'跨边界因素',20)
    d.text(253,379,'组件对应 φ：C → C′',23,BLUE)
    d.text(43,428,'增强文 x′',23,ha='left');d.tokens(158,411,304,31,9,True,False)
    d.text(253,647,'槽位改写 · 坐标与端点输运',25,BLUE)
    d.text(75,711,'组件 mC',22);d.mask(139,682,['c₁','c₂','c₃'],[1,1,1],cw=76)
    d.text(75,789,'关系 mR',22);d.mask(139,760,['r₁','r₂','NONE'],[1,0,1],cw=76)
    d.text(255,840,'仅可靠对应因素进入增强损失',22,BLUE)
    d.section='shared-generator';d.group(505,80,442,796,'2  共享生成器 θ',BLUE,size=28)
    for y,prime in [(142,False),(506,True)]:
        d.text(527,y,'增强文 x′' if prime else '原文 x',23,ha='left')
        d.tokens(533,y+23,222,24,9 if prime else 8,prime,False)
        d.arrow([(650,y+50),(650,y+82)])
        d.stack(559,y+105,177,188,layers=4)
        d.box(572,y+301,151,27,'基础权重冻结',PALE_GREY,GREY,size=19)
        d.text(551,y+77,'连续提示',19,BLUE,ha='left')
        d.vector(522,y+113,22,71,CYAN,n=2)
        d.arrow([(544,y+150),(558,y+150)],BLUE)
        d.box(787,y+256,104,39,'LoRA',PALE_BLUE,BLUE,size=22)
        d.arrow([(752,y+271),(784,y+271)],BLUE)
        d.text(839,y+320,'可训练',20,BLUE)
        d.text(836,y+90,'H′（增强文）' if prime else 'H（原文）',21)
        d.matrix(790,y+117,92,101,6,5,prime)
        d.arrow([(753,y+162),(785,y+162)])
        d.text(915,y+64,'跨度\n池化',19)
        d.arrow([(885,y+162),(899,y+162)])
        for j,col in enumerate([BLUE,GREEN,RED]):d.vector(902,y+130+j*27,31,17,col,n=2)
    d.text(741,490,'共享可训练参数 θ',21,BLUE)
    d.line([(934,304),(955,304),(955,668),(934,668)],BLUE,lw=.7)
    d.line([(955,304),(955,261)],BLUE,lw=.7)
    d.arrow([(955,261),(977,261)],BLUE)
    d.arrow([(955,611),(977,611)],BLUE)
    d.section='component-head';d.group(963,80,622,796,'3  可靠因素预测与对齐',BLUE,size=28)
    d.box(980,135,424,267,fill='white',edge=EDGE)
    d.text(995,158,'3.1  组件类型头（共享）',25,BLUE,ha='left')
    d.text(1047,215,'[ci ; hend]',22)
    d.vector(999,242,91,18,BLUE);d.vector(999,277,91,18,CYAN)
    d.arrow([(1095,261),(1112,261)]);d.mlp(1119,215,99,113,'2层 MLP')
    for yy,prime in [(232,False),(326,True)]:
        d.text(1281,yy-17,'pC′' if prime else 'pC',23)
        d.vector(1246,yy,93,25,PURPLE if prime else BLUE)
    d.arrow([(1220,260),(1233,260),(1233,244),(1243,244)])
    d.arrow([(1233,260),(1233,337),(1243,337)])
    d.text(1366,287,'} JS',25,BLUE)
    d.section='relation-head';d.box(980,421,424,338,fill='white',edge=EDGE)
    d.text(995,450,'3.2  关系状态头（共享）',25,CYAN,ha='left')
    d.text(1018,494,'源集 S',20)
    d.hyper(1021,520,70,52,False)
    d.text(1055,585,'完整多源',18,GREY)
    d.text(1006,620,'目标 v',20,ha='left');d.vector(1076,609,48,17,BLUE,n=3)
    d.text(1006,655,'hend',20,ha='left');d.vector(1076,644,48,17,CYAN,n=3)
    d.text(1006,690,'几何 η',20,ha='left');d.vector(1076,679,48,17,AMBER,n=6)
    d.mlp(1142,542,83,126,'MLP')
    d.arrow([(1125,610),(1138,610)])
    for yy,prime in [(547,False),(650,True)]:
        d.text(1294,yy-20,'pR′' if prime else 'pR',23)
        d.vector(1252,yy,85,25,PURPLE if prime else BLUE)
    d.arrow([(1226,604),(1239,604),(1239,559),(1248,559)])
    d.arrow([(1239,604),(1239,662),(1248,662)])
    d.text(1370,607,'} JS',25,BLUE)
    d.text(1193,730,'supports / attacks / NONE',21)
    d.section='reliable-supervision';d.box(1420,135,147,624,fill=PALE_BLUE,edge=BLUE)
    d.text(1494,171,'可靠标签\n监督 CE',23)
    d.box(1431,223,123,48,'原生标注',fill='white',edge=BLUE,size=22)
    d.text(1493,311,'仅用于\n损失计算',21)
    d.box(1431,356,123,43,'mC = 1',fill='white',edge=BLUE,size=23)
    d.box(1431,685,123,43,'mR = 1',fill='white',edge=BLUE,size=23)
    d.arrow([(1493,271),(1493,279)],BLUE,True)
    d.arrow([(1398,288),(1412,288),(1412,377),(1428,377)],BLUE,True)
    d.arrow([(1398,607),(1411,607),(1411,707),(1428,707)],BLUE,True)
    d.arrow([(368,799),(470,799),(470,854),(1569,854),(1569,707),(1557,707)],BLUE,True)
    d.text(1180,837,'可靠因素监督选择',22,BLUE)
    d.text(1235,803,'两视图保留梯度；基础权重冻结',21,GREY)
    d.section='training-objectives';d.group(15,897,1570,241,'4  训练目标：原文完整监督 + 增强可靠因素对齐',BLUE,size=28)
    d.text(46,977,'原文 x',23,ha='left');d.tokens(42,1001,179,32,8,labels=False)
    d.stack(261,986,108,113,layers=2)
    d.arrow([(225,1018),(255,1018)])
    d.box(417,955,201,102,fill='white',edge=BLUE,dash=True)
    d.text(517,974,'原文完整论辩图',22);d.graph(438,1001,158,43)
    d.arrow([(386,1018),(403,1018),(403,1010),(415,1010)])
    d.box(660,977,150,46,'完整生成监督',PALE_BLUE,BLUE,size=21)
    d.arrow([(622,1000),(654,1000)])
    d.vector(422,1090,92,21,BLUE)
    d.arrow([(403,1018),(403,1101),(417,1101)])
    d.box(559,1076,104,48,'句子监督头',fill='white',edge=BLUE,size=20)
    d.box(704,1076,106,48,'句子监督',PALE_BLUE,BLUE,size=21)
    d.arrow([(518,1101),(555,1101)]);d.arrow([(667,1101),(700,1101)])
    d.box(850,988,461,91,fill=PALE_BLUE,edge=BLUE)
    d.text(1081,1014,'L = L原文 + λsup L监督',25)
    d.text(1081,1051,'+ λC LC + λR LR',25)
    d.arrow([(814,1000),(830,1000),(830,1034),(846,1034)])
    d.arrow([(814,1101),(830,1101),(830,1034)])
    d.text(1081,1110,'源文档归一化',22,GREY)
    d.stack(1375,992,107,94,layers=2)
    d.box(1510,1001,59,68,'LoRA',PALE_BLUE,BLUE,size=20)
    d.arrow([(1317,1034),(1368,1034)])
    d.text(1469,961,'训练后的生成器 θ',23)
    d.text(1471,1110,'辅助头仅用于训练',22,GREY)
    d.text(800,1164,'模型结构示意  ·  φ 表示组件身份输运，不要求 token 一一对应',20,GREY)
    d.finish()

def inference_model():
    d=Diagram('03_依赖闭合修正模型_可编辑',1200)
    d.title('多候选驱动的依赖闭合论辩图修正模型')
    d.section='candidate-generation';d.group(15,82,1010,565,'1  多候选生成分支（生成器）',BLUE,fill='#FCFEFF',dash=False,size=29)
    d.text(47,178,'输入原文 x',23,ha='left')
    d.box(43,213,91,129,fill='white',edge=GREY,r=1)
    for yy in [239,257,275,293,311]:d.line([(57,yy),(116,yy)],GREY,1)
    d.text(90,379,'固定不变',22,GREY)
    d.stack(185,221,126,133,layers=4);d.text(251,176,'生成器 θ',23)
    d.arrow([(137,276),(178,276)])
    d.box(367,145,401,251,fill=PALE_BLUE,edge=BLUE,dash=True)
    d.text(567,174,'多候选论辩图',24)
    for i in range(3):
        xx=380+i*127;d.box(xx,202,118,177,fill='white',edge='#BAD6EA')
        d.text(xx+59,224,'G'+str(i+1),23)
        d.graph(xx+4,253,108,83,variant=i)
        d.vector(xx+19,354,81,14,[BLUE,PURPLE,GREEN][i])
    d.arrow([(330,278),(363,278)])
    d.box(802,252,111,73,'重排序\n共同合法化',PALE_AMBER,AMBER,size=21)
    d.arrow([(772,289),(798,289)])
    d.box(935,206,75,174,fill='white',edge=BLUE)
    d.text(972,229,'G₀',24)
    for a,b in [((972,274),(951,337)),((972,274),(993,337))]:d.edge(a,b,11)
    d.node(972,274,r=11);d.node(951,337,fill=TOKEN[2],edge=GREEN,r=11);d.node(993,337,fill=TOKEN[4],edge=RED,r=11)
    d.arrow([(918,289),(931,289)])
    d.section='candidate-universe';d.group(83,439,918,187,'搜索前冻结候选与对象身份',BLUE,fill=PALE_BLUE,size=25)
    for x,w in [(96,186),(293,220),(525,258),(795,194)]:d.box(x,491,w,119,fill='white',edge='#BAD6EA')
    d.text(189,512,'跨度 U',23)
    for i,c in enumerate([BLUE,GREEN,RED]):d.vector(130+i*10,537+i*20,92,12,c,n=1)
    d.text(403,512,'带类型组件 V',23);d.text(403,551,'(b, e, t)',23)
    d.vector(345,578,115,15,BLUE,n=4)
    d.text(654,512,'完整关系 P',23);d.hyper(558,541,183,48,False);d.text(654,598,'(S, v, ℓ)',19)
    d.text(892,512,'G₀ 对象',23);d.graph(819,541,141,53)
    d.arrow([(567,398),(567,419),(542,419),(542,435)])
    d.arrow([(969,382),(969,417),(892,417),(892,435)])
    d.section='independent-scorer';d.group(15,668,1010,464,'2  独立文本评分分支（对象评分器）',BLUE,fill='#FCFEFF',dash=False,size=29)
    d.text(82,765,'原文 x',23);d.box(43,793,79,145,fill='white',edge=GREY,r=1)
    for yy in [818,839,860,881,902]:d.line([(55,yy),(110,yy)],GREY,1)
    d.text(82,972,'固定不变',21,GREY)
    d.stack(161,827,113,112,label='编码器',layers=3,color=GREY)
    d.text(218,780,'独立文本编码',21)
    d.arrow([(126,864),(155,864)])
    d.matrix(318,812,98,129,7,6);d.text(366,780,'文本表示 Hx',22)
    d.arrow([(290,864),(314,864)])
    d.text(486,796,'跨度池化',22)
    for i,c in enumerate([BLUE,GREEN,RED]):d.vector(450,830+i*38,70,19,c,n=4)
    d.arrow([(420,864),(445,864)])
    d.text(569,767,'组件向量',21)
    d.box(548,801,73,149,fill='white',edge=BLUE)
    for i,c in enumerate([BLUE,GREEN,RED]):d.vector(559,824+i*39,50,19,c,n=3)
    d.arrow([(524,865),(543,865)])
    d.section='component-score';d.group(658,723,343,167,'完整组件评分 qC',AMBER,fill='#FFFDFA',size=24)
    d.mlp(672,775,103,78,'2层 MLP')
    d.arrow([(622,840),(640,840),(640,814),(668,814)])
    d.text(872,785,'qC(c | x)',25)
    d.vector(807,819,139,25,BLUE,n=5)
    d.text(864,870,'完整对象正确性',21)
    d.arrow([(780,814),(801,814)])
    d.section='relation-score';d.group(658,906,343,167,'完整关系评分 qR',AMBER,fill='#FFFDFA',size=24)
    d.mlp(672,957,103,78,'2层 MLP')
    d.arrow([(622,904),(640,904),(640,997),(668,997)])
    d.text(872,966,'qR(r | x)',25)
    d.vector(807,1003,139,25,GREEN,n=5)
    d.text(864,1054,'完整源集 + 目标 + 类型',19)
    d.arrow([(780,997),(801,997)])
    d.text(829,1105,'训练内 OOF 拟合 · 校准后冻结',23,GREY)
    d.text(350,1025,'关系输入：S、v、端点类型、ℓ、全文',21)
    d.text(350,1072,'与训练阶段的辅助头相互独立',21,BLUE)
    d.section='joint-decision';d.group(1045,82,540,965,'3  依赖闭合联合决策',AMBER,fill=PALE_AMBER,dash=False,size=29)
    d.section='conflict-closure';d.box(1069,151,492,292,fill='white',edge=AMBER,dash=True)
    d.text(1085,175,'组件冲突闭合',25,ha='left')
    d.text(1091,226,'文本位置',19,ha='left')
    d.line([(1191,226),(1535,226)],GREY,.7)
    for i in range(13):d.line([(1191+i*28,219),(1191+i*28,233)],GREY,.45)
    d.rect(1220,201,130,10,TOKEN[0],BLUE);d.rect(1305,211,170,10,'#FFE2B3',AMBER)
    d.text(1280,188,'b',20);d.text(1390,198,'b′',20)
    for x,prime in [(1098,False),(1363,True)]:
        a=(x+10,296);b=(x+129,296);c=(x+72,377)
        d.edge(a,b,19,AMBER if prime else BLUE);d.edge(b,c,19,AMBER if prime else INK);d.edge(a,c,19,GREY)
        d.node(*a,'c',TOKEN[0],BLUE,r=19);d.node(*b,'b′' if prime else 'b',TOKEN[4] if prime else TOKEN[3],AMBER,r=19)
        d.node(*c,'a',TOKEN[2],GREEN,r=19)
    d.text(1185,420,'旧端点及其全部关系',21)
    d.text(1451,420,'新端点与完整关系',21)
    d.line([(1315,258),(1315,400)],EDGE,.6,True)
    d.arrow([(1013,289),(1065,289)])
    d.section='fixed-utility';d.box(1069,460,492,90,fill='white',edge=AMBER)
    d.text(1315,481,'固定对象效用函数',25)
    d.text(1315,520,'Φ = wC ΦC + wR ΦR',29)
    d.arrow([(1003,814),(1030,814),(1030,520),(1065,520)],BLUE)
    d.arrow([(1003,997),(1037,997),(1037,537),(1065,537)],GREEN)
    d.arrow([(1003,553),(1057,553),(1057,573),(1069,573)])
    d.section='solver-constraints';d.box(1069,566,492,54,'求解内：闭合 · 合法性 · 分项增益 · 预算',fill='#FFF0D3',edge=AMBER,size=21)
    d.arrow([(1315,550),(1315,563)],AMBER)
    d.section='solver-alternatives';d.box(1072,638,216,177,fill=PALE_BLUE,edge=BLUE)
    d.box(1348,638,210,177,fill=PALE_GREY,edge=EDGE)
    d.text(1180,660,'全局 ILP',26)
    d.text(1180,704,'联合组件 / 关系选择',21)
    d.text(1180,751,'max Φ(z, y)',28)
    d.text(1180,791,'z, y ∈ {0, 1}',23)
    d.text(1318,729,'或',27,AMBER)
    d.text(1453,660,'有界局部',26)
    d.text(1453,704,'组件提案 + 关系补全',21)
    d.graph(1375,736,153,49,labels=True,changed=True)
    d.arrow([(1180,620),(1180,635)],AMBER);d.arrow([(1453,620),(1453,635)],AMBER)
    d.box(1362,826,181,35,'集合 BR-J：可选',fill='white',edge=BLUE,size=20,dash=True)
    d.line([(1453,815),(1453,824)],BLUE,.6,True)
    d.text(1309,887,'评分齐备且 n ≤ 2500：全局；其余：局部',20)
    d.text(1316,920,'全局：净编辑  /  局部：累计编辑',20,GREY)
    d.section='common-acceptance';d.box(1102,944,426,81,fill='white',edge=AMBER)
    d.text(1315,965,'共同接受：整图合法、预算内',23)
    d.text(1315,1001,'ΔΦC ≥ 0，ΔΦR ≥ 0，ΔΦ > δ',24)
    d.arrow([(1180,816),(1180,865),(1084,865),(1084,985),(1098,985)],AMBER)
    d.arrow([(1559,727),(1572,727),(1572,985),(1532,985)],AMBER)
    d.section='final-output';d.box(1047,1070,256,95,fill=PALE_BLUE,edge=BLUE)
    d.box(1321,1070,264,95,fill=PALE_GREY,edge=GREY,dash=True)
    d.text(1175,1090,'通过：完整论辩图',23,BLUE);d.graph(1107,1110,134,44,variant=1)
    d.text(1453,1093,'未通过：保留当前合法图',21)
    d.text(1453,1134,'评分全缺失：保留 G₀',21,GREY)
    d.arrow([(1210,1027),(1210,1066)],AMBER)
    d.arrow([(1423,1027),(1423,1066)],GREY)
    d.text(800,1186,'模型结构示意  ·  代理效用改善不等于真实 F1 提高',20,GREY)
    d.finish()

if __name__=='__main__':
    overview();paired_model();inference_model()
    (HERE/'editable_manifest.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
    for r in REPORT:print(r['name'],r['editable_text_elements'],'editable texts,',r['embedded_images'],'images, outside:',r['outside_canvas'])
