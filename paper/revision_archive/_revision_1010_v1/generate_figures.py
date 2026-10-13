"""Code-native mechanism diagrams and plots from the disclosed scenario."""
from pathlib import Path
import json
W=Path(__file__).resolve().parent
source=(W.parent/'_revision_1009_v2/generate_figures.py').read_text()
source=source.replace('队列检查完或资源用尽停止；非空合格批择优原子提交。','尝试耗尽停止新评估；已有合格项另查接受、编辑和提交资源。')
source=source.replace("'有合格项：整批择优\\n总效用 → 少编辑 → 语义键\\n原子提交；失败完整回退'", "'合格项按效用、编辑、键择优\\n另查接受、编辑及提交资源\\n原子提交；不增加外层尝试'")
source=source.replace("'本批无合格：保留no-op\\n仍有余批且额度允许：继续\\n队列或资源耗尽：停止'", "'无合格项：保留no-op\\n可启动新评估则继续余批\\n队列或评估资源耗尽停止'")
source=source.replace('src=inspect.getsource(m.repair)', '''import textwrap
save_src=textwrap.dedent(inspect.getsource(m.Diagram.save)).replace('人为构造的机制示意；非实测结果','方法机制示意')
exec(save_src,m.__dict__)
m.Diagram.save=m.save
for stem in ['argument_example','research_relationship','framework','augmentation','training_architecture']:
    getattr(m,stem)(300)
src=inspect.getsource(m.repair)''')
exec(compile(source,str(W/'generate_mechanisms.py'),'exec'),globals())

from reportlab.graphics.shapes import Drawing,Line,String,Rect
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor,black,white
import pypdfium2 as pdfium
import math
d=json.loads((W/'scenario_results.json').read_text())
blue=HexColor('#245A7B');orange=HexColor('#B86A2D');gray=HexColor('#6B7175')
FONT=m.FONT
def text(dr,x,y,s,size=9,anchor='start',color=black):
    dr.add(String(x,y,s,fontName=FONT,fontSize=size,textAnchor=anchor,fillColor=color))
def save(dr,name):
    text(dr,dr.width-8,dr.height-10,'人工情景',7.5,'end',gray)
    path=W/'figures'/f'{name}.pdf';renderPDF.drawToFile(dr,str(path))
    doc=pdfium.PdfDocument(str(path));page=doc[0]
    bitmap=page.render(scale=300/72,fill_color=(255,255,255,255));bitmap.to_pil().convert('RGB').save(W/'figures'/f'{name}.png',dpi=(300,300))
    bitmap.close();page.close();doc.close()
def drawing(w=550,h=238):
    dr=Drawing(w,h);dr.add(Rect(0,0,w,h,strokeColor=None,fillColor=white));return dr
def panel(dr,x,y,w,h,data,xmin,xmax,ymin,ymax,xticks,yticks,colors,markers=None):
    lp=LinePlot();lp.x=x;lp.y=y;lp.width=w;lp.height=h;lp.data=data
    for ax in [lp.xValueAxis,lp.yValueAxis]:
        ax.labels.fontName=FONT;ax.labels.fontSize=8;ax.strokeWidth=.6;ax.strokeColor=gray
    lp.xValueAxis.valueMin=xmin;lp.xValueAxis.valueMax=xmax;lp.xValueAxis.valueSteps=xticks
    lp.yValueAxis.valueMin=ymin;lp.yValueAxis.valueMax=ymax;lp.yValueAxis.valueSteps=yticks
    lp.yValueAxis.visibleGrid=True;lp.yValueAxis.gridStrokeColor=HexColor('#DDE2E5');lp.yValueAxis.gridStrokeWidth=.45
    for i,c in enumerate(colors):
        lp.lines[i].strokeColor=c;lp.lines[i].strokeWidth=1.3
        lp.lines[i].symbol=makeMarker((markers or ['FilledCircle']*len(colors))[i]);lp.lines[i].symbol.size=4;lp.lines[i].symbol.fillColor=c;lp.lines[i].symbol.strokeColor=c
    dr.add(lp)
    return lp,lambda a:x+(a-xmin)/(xmax-xmin)*w,lambda a:y+(a-ymin)/(ymax-ymin)*h
def errors(dr,xm,ym,xs,ys,es,color):
    for x,y,e in zip(xs,ys,es):
        dr.add(Line(xm(x),ym(y-e),xm(x),ym(y+e),strokeColor=color,strokeWidth=.8))
        for b in [y-e,y+e]:dr.add(Line(xm(x)-2,ym(b),xm(x)+2,ym(b),strokeColor=color,strokeWidth=.8))

methods=['t0_i0','plain_i0','qos_i0','full_data_i0','head_i0','t1_i0']
labels=['T0','普通增强','QOS式','增强基础','加头监督','T1']
dr=drawing()
for j,ds in enumerate(['AAEC','CDCP']):
    ys=[d['metrics'][ds][m]['relation']['mean'] for m in methods];errs=[d['metrics'][ds][m]['relation']['sd'] for m in methods]
    lo=math.floor(min(ys)-2);hi=math.ceil(max(ys)+2)
    lp,xm,ym=panel(dr,32+j*275,45,236,147,[list(enumerate(ys))],-.15,5.15,lo,hi,list(range(6)),list(range(lo,hi+1,2)),[blue])
    lp.xValueAxis.labels.visible=False
    for k,label in enumerate(labels):text(dr,xm(k),27,label,8,'middle')
    errors(dr,xm,ym,range(6),ys,errs,blue)
    text(dr,150+j*275,219,ds,12,'middle');text(dr,32+j*275,202,'严格关系 F1（%）',8)
text(dr,275,7,'误差线为三个种子的样本标准差',8,'middle',gray)
save(dr,'training_results')

dr=drawing(h=260)
for j,ds in enumerate(['AAEC','CDCP']):
    b=d['budget'][ds];x=[v['mean_s'] for v in b];y=[v['relation_f1'] for v in b]
    more=[[(d['costs'][ds][m]['mean_s'],d['metrics'][ds][m]['relation']['mean'])] for m in ['global_equal','global_long']]
    xmax=90 if j==0 else 130;lo=math.floor(min(y)-2);hi=math.ceil(max(y)+3)
    lp,xm,ym=panel(dr,32+j*275,58,232,151,[list(zip(x,y))]+more,10,xmax,lo,hi,list(range(20,xmax+1,20)),list(range(lo,hi+1,2)),[blue,orange,gray],['FilledCircle','FilledSquare','FilledTriangle'])
    for q in b:
        dx,dy={0:(4,7),1:(5,-12),2:(-20,8),4:(9,-11)}[q['rounds']]
        text(dr,xm(q['mean_s'])+dx,ym(q['relation_f1'])+dy,f"{q['rounds']}轮",9)
    text(dr,148+j*275,239,ds,12,'middle');text(dr,32+j*275,220,'严格关系 F1（%）',8);text(dr,148+j*275,31,'逐文档平均时间（秒）',9,'middle')
for x,label,c in [(108,'局部轮数',blue),(234,'全局等时限',orange),(377,'全局大预算',gray)]:
    dr.add(Line(x-16,9,x-4,9,strokeColor=c,strokeWidth=2));text(dr,x,6,label,8)
save(dr,'budget_results')

dr=drawing(h=240)
for j,ds in enumerate(['AAEC','CDCP']):
    methods=[['t0_i0','t0_i1'],['t1_i0','t1_i1']]
    data=[[(i,d['metrics'][ds][m]['relation']['mean']) for i,m in enumerate(ms)] for ms in methods]
    lo=math.floor(data[0][0][1]-2);hi=math.ceil(data[1][1][1]+3)
    lp,xm,ym=panel(dr,38+j*275,42,225,152,data,-.15,1.15,lo,hi,[0,1],list(range(lo,hi+1,4)),[gray,blue])
    lp.xValueAxis.labels.visible=False
    for k,label in enumerate(['I0 初始预测','I1 联合修正']):text(dr,xm(k),24,label,9,'middle')
    for ms,dat,col in zip(methods,data,[gray,blue]):
        errors(dr,xm,ym,[0,1],[a[1] for a in dat],[d['metrics'][ds][m]['relation']['sd'] for m in ms],col)
        for x,y in dat:text(dr,xm(x),ym(y)+8,f'{y:.2f}',9,'middle',col)
    text(dr,150+j*275,221,ds,12,'middle');text(dr,38+j*275,204,'严格关系 F1（%）',8)
for x,label,c in [(227,'T0',gray),(291,'T1',blue)]:
    dr.add(Line(x-17,8,x-4,8,strokeColor=c,strokeWidth=2));text(dr,x,5,label,9)
save(dr,'four_cell_results')

dr=drawing(480,235);chart=VerticalBarChart();chart.x=45;chart.y=38;chart.width=397;chart.height=147
chart.data=[[100*d['risk'][ds]['t1_i1']['relation'][key]/d['risk'][ds]['t1_i1']['relation']['base_tp'] for ds in ['AAEC','CDCP']] for key in ['recovered','lost_tp']]
chart.categoryAxis.categoryNames=['AAEC','CDCP'];chart.categoryAxis.labels.fontName=FONT;chart.categoryAxis.labels.fontSize=10
chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=20;chart.valueAxis.valueStep=5;chart.valueAxis.labels.fontName=FONT;chart.valueAxis.labels.fontSize=8;chart.valueAxis.visibleGrid=True;chart.valueAxis.gridStrokeColor=HexColor('#DDE2E5');chart.valueAxis.gridStrokeWidth=.5
chart.bars[0].fillColor=blue;chart.bars[1].fillColor=orange;chart.bars.strokeColor=None
chart.barLabelFormat='%.2f';chart.barLabels.fontName=FONT;chart.barLabels.fontSize=9;chart.barLabels.nudge=6;chart.barLabels.boxAnchor='s'
chart.barWidth=24;chart.groupSpacing=22;chart.barSpacing=8;dr.add(chart)
text(dr,45,202,'每100个初始关系TP对应的对象数',9)
for x,label,c in [(260,'恢复真阳性',blue),(365,'损失原TP',orange)]:
    dr.add(Rect(x-13,219,8,7,fillColor=c,strokeColor=None));text(dr,x,218,label,9)
save(dr,'recovery_risk')
print('mechanisms and four scenario plots generated')
