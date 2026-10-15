from pathlib import Path
from html import escape
import json
import subprocess

ROOT = Path(__file__).parent
INK = '#23323e'
BLUE = '#31698f'
TEAL = '#337b6b'
PURPLE = '#7562a0'
ORANGE = '#b57532'
GRAY = '#64727e'
RED = '#aa5961'


def sub(s):
    return f'<tspan baseline-shift="sub" font-size="18">{s}</tspan>'


def sup(s):
    return f'<tspan baseline-shift="super" font-size="18">{s}</tspan>'


class Diagram:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
        for name,color in [('gray',GRAY),('blue',BLUE),('purple',PURPLE),('red',RED),('teal',TEAL),('orange',ORANGE)]:
            self.parts.append(f'<defs><marker id="{name}" viewBox="0 0 10 10" refX="8.2" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker></defs>')
        self.parts.append(f'<rect width="100%" height="100%" fill="white"/><g font-family="Noto Sans CJK SC, Noto Sans CJK JP, sans-serif" fill="{INK}" stroke-linejoin="round" stroke-linecap="round">')

    def rect(self, x, y, w, h, fill='white', stroke=GRAY, dashed=False, radius=7, width=1.8):
        dash = ' stroke-dasharray="7 5"' if dashed else ''
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{dash}/>')

    def text(self, x, y, value, size=22, color=INK, weight=400, anchor='middle'):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>')

    def math(self, x, y, value, size=25, color=INK, anchor='middle'):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="Noto Serif, DejaVu Serif, serif" font-size="{size}" fill="{color}" text-anchor="{anchor}">{value}</text>')

    def line(self, points, color=GRAY, dashed=False, arrow=False, width=2):
        colors={GRAY:'gray',BLUE:'blue',PURPLE:'purple',RED:'red',TEAL:'teal',ORANGE:'orange'}
        marker=f' marker-end="url(#{colors.get(color,"gray")})"' if arrow else ''
        dash=' stroke-dasharray="7 5"' if dashed else ''
        path='M '+' L '.join(f'{x} {y}' for x,y in points)
        self.parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}"{marker}{dash}/>')

    def arrow(self, points, color=GRAY, dashed=False):
        self.line(points,color,dashed,True)

    def node(self,x,y,label,fill='#e1edf6',stroke=BLUE,r=23,size=24):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        if label: self.text(x,y+8,label,size,INK)

    def matrix(self,x,y,cols=4,rows=2,cell=12,color=BLUE,fill='#cfe3f1'):
        for r in range(rows):
            for c in range(cols):self.rect(x+c*cell,y+r*cell,cell,cell,fill,color,radius=0,width=1)

    def bars(self,x,y,heights,color=BLUE,fill='#cfe3f1',w=18,gap=6):
        for j,h in enumerate(heights):self.rect(x+j*(w+gap),y-h,w,h,fill,color,radius=0,width=1)
        self.line([(x-3,y),(x+len(heights)*(w+gap)-gap+3,y)],color,width=1)

    def write(self, name):
        svg=ROOT/f'{name}.svg'
        svg.write_text('\n'.join(self.parts)+'</g></svg>',encoding='utf-8')
        subprocess.run(['inkscape',str(svg),'--export-type=png','--export-width=3200',f'--export-filename={ROOT/name}.png'],check=True,capture_output=True)
        subprocess.run(['inkscape',str(svg),f'--actions=select-all;object-to-path;export-filename:{ROOT/name}.outlined.svg;export-do;'],check=True,capture_output=True)


d=Diagram(1200,885)
d.text(165,40,'双视图与可靠因素',24,BLUE,600)
d.text(505,40,'共享抽取模型',24,BLUE,600)
d.text(965,40,'因素预测与监督',24,BLUE,600)

# Original and augmented texts are the only model inputs; labels are below.
colors=['#d4e5f2','#d4e5f2','#f5d8a6','#f5d8a6','#e0d6ef','#e0d6ef','#f0f2f4','#f0f2f4']
for y,title,is_aug in [(94,'原文 x',False),(347,'改写 x′',True)]:
    d.text(165,y-15,title,24,BLUE if not is_aug else PURPLE,600)
    for j,col in enumerate(colors):d.rect(43+j*30,y,30,31,col,BLUE if not is_aug else PURPLE,radius=0,width=1.5)
    d.arrow([(287,y+15),(335,y+15)],BLUE if not is_aug else PURPLE)

for y,prime in [(190,False),(440,True)]:
    labels=['c₁','c₂','c₃'] if not prime else ['c₁′','c₂′','c₃′']
    d.arrow([(81,y),(138,y)],BLUE)
    d.arrow([(252,y),(195,y)],GRAY if prime else BLUE,dashed=prime)
    d.text(110,y-20,'r₁′' if prime else 'r₁',22,BLUE)
    d.text(223,y-20,'待定' if prime else 'r₂',22,GRAY if prime else BLUE)
    for x,label,fill in zip([58,166,275],labels,['#d4e5f2','#f5d8a6','#e0d6ef']):
        d.node(x,y,label,fill,BLUE if not prime else PURPLE,r=23,size=22)
d.arrow([(166,220),(166,245)],GRAY)
d.text(166,280,'A 改写 · 坐标迁移 φ',22,GRAY)
d.arrow([(166,292),(166,313)],GRAY)
d.text(166,493,'V 审核 → 可靠因素掩码',22,TEAL,600)
for y,name,labels,vals in [(554,'m'+sub('C'),['c₁′','c₂′','c₃′'],[1,1,1]),(647,'m'+sub('R'),['r₁′','r₂′','无关系'],[1,0,1])]:
    d.math(45,y+25,name,25,TEAL)
    for x,w,label,value in [(104,51,labels[0],vals[0]),(173,51,labels[1],vals[1]),(242,68,labels[2],vals[2])]:
        d.text(x+w/2,y-12,label,22)
        d.rect(x,y,w,36,'#dcece7' if value else '#e8ebed',TEAL if value else GRAY)
        d.text(x+w/2,y+27,str(value),24,TEAL if value else GRAY,600)
d.text(166,724,'0：不参与增强侧损失',22,GRAY)

# Shared model: the two views are passes through the same parameters, not teachers.
d.rect(340,65,325,517,'#f6f7f8',GRAY)
d.text(503,104,'抽取生成器 G（参数共享）',22,INK,600)
d.rect(365,143,275,107,'#e5ebef',GRAY)
d.math(503,181,'基础权重 W'+sub('0')+'（冻结）',23)
d.matrix(398,201,cols=7,rows=2,cell=14,color=GRAY,fill='#cad4dc')
d.rect(365,278,275,85,'#fff4e6',ORANGE)
d.text(503,308,'全局 LoRA（可训练）',22,ORANGE,600)
d.matrix(394,324,cols=3,rows=1,cell=16,color=ORANGE,fill='#f0cb94')
d.matrix(560,324,cols=3,rows=1,cell=16,color=ORANGE,fill='#f0cb94')
d.math(471,346,'A'+sub('g'),23,ORANGE)
d.math(535,346,'B'+sub('g'),23,ORANGE)
d.arrow([(488,335),(515,335)],ORANGE)
d.rect(365,392,275,129,'#fff4e6',ORANGE)
d.text(503,425,'结论 LoRA（可训练）',22,ORANGE,600)
d.math(503,463,'g'+sub('t')+' · B'+sub('c')+' A'+sub('c'),27,ORANGE)
d.text(503,499,'生成结论类型后开启',22,ORANGE)
d.text(503,558,'每个视图独立前向，共享参数',22,GRAY)
d.line([(668,321),(681,321)],GRAY)
d.arrow([(681,321),(681,191),(691,191)],BLUE)
d.arrow([(681,321),(681,442),(691,442)],PURPLE)
d.matrix(695,177,cols=3,rows=2,cell=12,color=BLUE,fill='#cfe3f1')
d.matrix(695,428,cols=3,rows=2,cell=12,color=PURPLE,fill='#e1d6ef')
d.math(713,162,'H(x)',22,BLUE)
d.math(700,482,'H(x′)',22,PURPLE)

# Both input representations feed the two shared auxiliary heads.
for top,kind,desc in [(65,'C','组件跨度均值 ⊕ 全文表示'),(347,'R','源组件均值 ⊕ 目标 ⊕ 全文与位置')]:
    d.rect(754,top,427,252,'#fcfdfd',GRAY)
    d.text(968,top+36,'组件类型辅助头（共享）' if kind=='C' else '关系状态辅助头（共享）',23,TEAL,600)
    d.text(968,top+73,desc,22,GRAY)
    yy=top+135
    d.matrix(778,yy-12,cols=3,rows=1,cell=13,color=BLUE,fill='#cfe3f1')
    d.matrix(778,yy+37,cols=3,rows=1,cell=13,color=PURPLE,fill='#e1d6ef')
    d.rect(844,yy-22,91,88,'#fff4e6',ORANGE)
    d.math(890,yy+13,'f'+sub(kind),28,ORANGE)
    d.text(890,yy+47,'两层',22,ORANGE)
    d.arrow([(820,yy-5),(839,yy-5)],BLUE)
    d.arrow([(820,yy+43),(839,yy+43)],PURPLE)
    d.arrow([(939,yy-5),(970,yy-5)],BLUE)
    d.arrow([(939,yy+43),(970,yy+43)],PURPLE)
    d.math(1060,yy-33,'p'+sub(kind)+'(x)',23,BLUE)
    d.math(1060,yy+24,'p'+sub(kind)+'(x′)',23,PURPLE)
    d.bars(1010,yy,[14,25,10],BLUE,'#cfe3f1',w=25,gap=15)
    d.bars(1010,yy+57,[13,24,12],PURPLE,'#e1d6ef',w=25,gap=15)
    d.rect(770,top+207,200,34,'#e2efe9',TEAL)
    domain='c ∈ A⁺, m'+sub('C')+'(c)=1' if kind=='C' else 'ω ∈ J'+sub('A')+', m'+sub('R')+'(ω)=1'
    d.math(870,top+232,domain,22,TEAL)
    d.arrow([(974,top+224),(994,top+224)],TEAL)
    d.math(1090,top+232,'JS(p'+sub(kind)+',p′'+sub(kind)+')',23,TEAL)
    d.line([(1118,yy),(1157,yy),(1157,top+201)],BLUE)
    d.line([(1118,yy+57),(1157,yy+57)],PURPLE)
    d.arrow([(1157,top+201),(1090,top+201),(1090,top+210)],TEAL)


d.line([(734,190),(742,190)],BLUE)
d.line([(742,190),(742,477)],BLUE)
d.line([(734,441),(737,441),(737,244)],PURPLE)
d.line([(737,441),(737,525)],PURPLE)
d.arrow([(742,195),(775,195)],BLUE)
d.arrow([(737,244),(775,244)],PURPLE)
d.arrow([(742,477),(775,477)],BLUE)
d.arrow([(737,525),(775,525)],PURPLE)

# Original-only generation path and factor-supervision targets are kept separate.
d.arrow([(503,586),(503,623)],GRAY)
d.rect(340,628,325,108,'#f8fafc',BLUE)
d.text(503,660,'仅原文：完整图与句子监督',22,BLUE,600)
d.node(374,704,'',r=11,fill='#d4e5f2')
d.node(407,686,'',r=11,fill='#f5d8a6')
d.node(425,719,'',r=11,fill='#e0d6ef')
d.line([(383,698),(398,691)],BLUE)
d.line([(384,708),(414,716)],BLUE)
d.math(548,708,'L'+sub('gen')+' + 0.5L'+sub('sent'),23,BLUE)
d.rect(754,628,427,108,'#f7fbf9',TEAL)
d.text(967,660,'因素辅助监督：交叉熵',23,TEAL,600)
d.text(967,696,'原文可审核因素＋增强可靠因素',22)
d.text(967,725,'类型与关系标签不输入抽取器 G',22,GRAY)
d.arrow([(312,665),(325,665),(325,759),(967,759),(967,740)],TEAL,True)
d.text(600,793,'辅助损失更新全局 LoRA；结论分支随对应生成路径更新；辅助头仅用于训练。',22,GRAY)
d.rect(25,817,1155,53,'#f0f5f8',BLUE)
d.math(600,852,'L = L'+sub('IC')+' + λ'+sub('sup')+'L'+sub('heads')+sup('sup')+' + λ'+sub('C')+'L'+sub('C')+sup('align')+' + λ'+sub('R')+'L'+sub('R')+sup('align'),28,BLUE)
d.write('fig3_2_technical')


d=Diagram(1200,750)
d.text(600,31,'独立对象评分器 S：评分头另行训练与校准，修正期间参数固定',24,BLUE,600)
d.rect(25,48,1155,158,'#f7fafc',BLUE)
d.rect(44,65,220,51,'white',BLUE)
d.text(154,100,'原文 x',23,BLUE,600)
d.rect(44,135,220,51,'white',PURPLE)
d.math(154,169,'候选 V、P 的特征',23,PURPLE)
d.arrow([(269,91),(305,91)],BLUE)
d.rect(310,71,218,110,'#e5ebef',GRAY)
d.text(419,104,'冻结文本编码器',23,GRAY,600)
d.matrix(359,127,cols=7,rows=2,cell=16,color=GRAY,fill='#cad4dc')
d.line([(532,125),(551,125),(551,90)],GRAY)
d.line([(551,125),(551,160)],GRAY)
d.arrow([(551,90),(572,90)],GRAY)
d.arrow([(551,160),(572,160)],GRAY)
d.rect(577,61,204,55,'#fff4e6',ORANGE)
d.text(679,96,'组件评分头',23,ORANGE,600)
d.rect(577,133,204,55,'#fff4e6',ORANGE)
d.text(679,169,'关系评分头',23,ORANGE,600)
d.arrow([(786,90),(858,90)],BLUE)
d.arrow([(786,160),(858,160)],TEAL)
d.rect(864,65,292,119,'white',BLUE)
d.text(1010,98,'固定完整对象评分',23,BLUE,600)
d.math(1010,137,'q'+sub('C')+'(v),  q'+sub('R')+'(r)',26)
d.text(1010,169,'缓存并供两种求解复用',22,GRAY)
d.line([(269,160),(280,160),(280,198),(560,198),(560,125),(679,125)],PURPLE)
d.arrow([(679,125),(679,119)],PURPLE)
d.line([(560,198),(679,198)],PURPLE)
d.arrow([(679,198),(679,191)],PURPLE)
d.text(600,235,'全局：共同选择组件与关系；局部：固定组件提议，重新选择全部受影响关系。',22,GRAY)

# A real, already documented type-change transaction, not invented scores or model blocks.
d.rect(25,257,668,346,'white',GRAY)
d.text(359,287,'AAEC 文档 essay077：同跨度的类型替换',23,BLUE,600)
d.math(178,326,'G'+sub('0')+'（局部）',24)
d.math(518,326,'G′（局部）',24)
for x1,xb,new in [(73,267,False),(405,594,True)]:
    for yy,label in [(369,'a₁'),(510,'a₂')]:
        d.node(x1,yy,label,'#dbe8f0',BLUE,r=25,size=24)
        d.text(x1,yy+48,'前提',22,GRAY)
    d.rect(xb-54,401,108,77,'#e2efe9' if new else '#f3dfe1',TEAL if new else RED)
    d.text(xb,429,'b新' if new else 'b旧',23,TEAL if new else RED,600)
    d.text(xb,462,'论点' if new else '主论点',22)
    d.math(xb,511,'q'+sub('C')+(' = 0.958' if new else ' = 0.899'),22,TEAL if new else RED)
    if not new:
        d.arrow([(97,380),(207,420)],RED,True)
        d.arrow([(97,498),(207,460)],RED,True)
        d.text(162,373,'攻击',22,RED)
        d.text(161,525,'攻击',22,RED)
    else:
        d.arrow([(429,498),(534,460)],TEAL)
        d.text(489,526,'支持',22,TEAL)
d.arrow([(327,439),(369,439)],GRAY)
d.text(359,583,'删除旧端点关系，重新选择新端点关系；两个前提保持不变。',22,GRAY)

d.rect(718,257,462,346,'#f7faf9',TEAL)
d.text(949,291,'选择变量与结构约束',24,TEAL,600)
d.math(949,331,'z'+sub('v')+' ∈ {0,1},  y'+sub('r')+' ∈ {0,1}',27)
d.text(949,371,'同跨度类型互斥、组件不重叠',22)
d.math(949,406,'z'+sub('b旧')+' + z'+sub('b新')+' ≤ 1',26,TEAL)
d.text(949,444,'选中关系的全部端点必须存在',22)
d.math(949,480,'y'+sub('r')+' ≤ z'+sub('c')+'，∀c ∈ Ends(r)',25,TEAL)
d.text(949,520,'同槽位至多一个关系标签',22)
d.math(949,555,'∑'+sub('r∈Γₛ')+' y'+sub('r')+' ≤ 1',26,TEAL)
d.text(949,585,'其余语料约束见正文',22,GRAY)

d.rect(25,621,1155,112,'#f0f5f8',BLUE)
d.math(600,655,'Φ = w'+sub('C')+'∑'+sub('v')+'(2q'+sub('C')+'(v) − κ'+sub('C')+')z'+sub('v')+' + w'+sub('R')+'∑'+sub('r')+'(2q'+sub('R')+'(r) − κ'+sub('R')+')y'+sub('r'),27,BLUE)
d.math(600,692,'接受：ΔΦ'+sub('C')+' ≥ 0，ΔΦ'+sub('R')+' ≥ 0，ΔΦ &gt; δ；结构合法且编辑预算未超限。',24)
d.text(600,721,'图示事务：ΔΦ = 1.534 > 0.20；组件编辑2次、关系编辑3次，整体接受。',22,GRAY)
d.write('fig4_1_technical')

mapping=json.loads(Path('/workspace/thesis_v7_revision_20261015/figures/original_mapping.json').read_text())
for item in mapping:
    key=item['name']+'_technical'
    item['replacement_png']=str(ROOT/(key+'.png'))
    item['replacement_svg']=str(ROOT/(key+'.outlined.svg'))
    item['editable_svg']=str(ROOT/(key+'.svg'))
    item['replacement_viewbox']=[1200,885 if item['name']=='fig3_2' else 750]
    item['minimum_body_font_px']=22
    item['recommended_extent']=item['original_extent']
    item['notes']='技术方法图；正文最小22px，必要公式上下标18px；保留现有显示宽高，同时替换PNG及SVG。'
(ROOT/'mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
