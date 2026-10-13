"""Three Python-only thesis plots of disclosed hypothetical counts.

Contract: keep the existing three questions, sizes and method colors. Training
panels show ordered learning comparisons in each native task; four-cell panels
show conditional inference increments; risk bars expose TP gains and losses.
No panel is empirical evidence. No p values or significance marks are plotted.
Mean/SD panels use three fixed simulation seeds. Risk uses cumulative counts,
so no across-seed SD is attached to a cumulative-count ratio. The source JSON
is preserved; there is no filtering, imputation, rescaling of F1 or model fit.
"""
from pathlib import Path
import os,sys,json,hashlib
W=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(W/'mpl-cache')
sys.path.insert(0,'/private/tmp/paper-1010-v7-figure-deps')
sys.path.insert(0,'/Users/channtang/.codex/skills/nature-figure/scripts')
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from audit_panel_alignment import require_matplotlib_panel_alignment
font_manager.fontManager.addfont('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial Unicode MS','DejaVu Sans'],'font.size':7.3,'axes.labelsize':7.5,'xtick.labelsize':7,'ytick.labelsize':7,'axes.linewidth':.65,'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,'pdf.fonttype':42,'svg.fonttype':'none','figure.facecolor':'white','savefig.facecolor':'white','legend.frameon':False})
d=json.loads((W/'scenario_results.json').read_text());out=W/'figures'
BLUE='#245A7B';ORANGE='#B86A2D';GRAY='#6B7175'
records=[]
def save(fig,name):
 fig.canvas.draw()
 require_matplotlib_panel_alignment(fig,json_out=out/f'{name}.alignment.json',tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
 fig.savefig(out/f'{name}.pdf')
 fig.savefig(out/f'{name}.svg')
 fig.savefig(out/f'{name}.png',dpi=600)
 fig.savefig(out/f'{name}.preview.png',dpi=300)
 records.append({'name':name,'evidence':'ESTIMATED_SCENARIO_NOT_MEASURED','source_sha256':hashlib.sha256((W/'scenario_results.json').read_bytes()).hexdigest(),'files':{ext:hashlib.sha256((out/f'{name}.{ext}').read_bytes()).hexdigest() for ext in ['pdf','svg','png']}})
 plt.close(fig)
def pairfig(h):
 fig,axs=plt.subplots(1,2,figsize=(157/25.4,h/25.4))
 fig.subplots_adjust(left=.09,right=.985,bottom=.26,top=.77,wspace=.27)
 for ax,ds in zip(axs,['AAEC','CDCP']):
  ax.set_title(ds,fontsize=10,pad=20)
  ax.text(0,1.025,'严格关系 F1（%）',transform=ax.transAxes,ha='left',va='bottom',fontsize=7.1)
  ax.grid(axis='y',color='#DDE2E5',linewidth=.45);ax.set_axisbelow(True)
 return fig,axs

fig,axs=pairfig(157*238/550)
methods=['t0_i0','plain_i0','qos_i0','full_data_i0','head_i0','t1_i0']
labels=['T0','普通增强','QOS式','增强基础','加头监督','T1']
for ax,ds in zip(axs,['AAEC','CDCP']):
 y=np.array([d['metrics'][ds][m]['relation']['mean'] for m in methods]);err=np.array([d['metrics'][ds][m]['relation']['sd'] for m in methods])
 ax.errorbar(range(6),y,yerr=err,color=BLUE,marker='o',markersize=3,linewidth=1.05,capsize=2,elinewidth=.7)
 ax.set_xticks(range(6),labels);ax.set_xlim(-.25,5.25)
 ax.set_ylim(np.floor(min(y-err)-1),np.ceil(max(y+err)+1))
fig.text(.5,.055,'估算情景 · 三个固定情景种子的均值 ± 样本标准差',ha='center',fontsize=7,color=GRAY)
save(fig,'training_results')

fig,axs=pairfig(157*240/550)
for ax,ds in zip(axs,['AAEC','CDCP']):
 for methods,color,label in [(['t0_i0','t0_i1'],GRAY,'T0'),(['t1_i0','t1_i1'],BLUE,'T1')]:
  y=np.array([d['metrics'][ds][m]['relation']['mean'] for m in methods]);err=np.array([d['metrics'][ds][m]['relation']['sd'] for m in methods])
  ax.errorbar([0,1],y,yerr=err,color=color,marker='o',markersize=3,linewidth=1.05,capsize=2,elinewidth=.7,label=label)
  for x,v,e in zip([0,1],y,err):ax.annotate(f'{v:.2f}',(x,v+e),xytext=(0,4),textcoords='offset points',ha='center',fontsize=7.2,color=color)
 ax.set_xticks([0,1],['I0 初始预测','I1 联合修正']);ax.set_xlim(-.2,1.2)
 ax.set_ylim(np.floor(d['metrics'][ds]['t0_i0']['relation']['mean']-2),np.ceil(d['metrics'][ds]['t1_i1']['relation']['mean']+3))
handles,labels=axs[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.09),ncol=2,fontsize=7)
fig.text(.5,.025,'估算情景 · 误差棒为三个固定情景种子的样本标准差',ha='center',fontsize=7,color=GRAY)
save(fig,'four_cell_results')

fig,ax=plt.subplots(figsize=(157/25.4,157*235/480/25.4))
fig.subplots_adjust(left=.105,right=.97,bottom=.23,top=.80)
xs=np.arange(2);width=.25
for offset,key,color,label in [(-width/2,'recovered',BLUE,'恢复真阳性'),(width/2,'lost_tp',ORANGE,'损失原TP')]:
 values=[100*d['risk'][ds]['t1_i1']['relation'][key]/d['risk'][ds]['t1_i1']['relation']['base_tp'] for ds in ['AAEC','CDCP']]
 bars=ax.bar(xs+offset,values,width,color=color,label=label)
 ax.bar_label(bars,fmt='%.2f',padding=5,fontsize=8)
ax.set_xticks(xs,['AAEC','CDCP']);ax.set_ylim(0,17);ax.set_yticks([0,5,10,15])
ax.grid(False);ax.set_axisbelow(True)
fig.text(.105,.90,'每100个初始关系TP对应的对象数',ha='left',fontsize=8)
fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.54,.035),ncol=2,fontsize=7.5)
fig.text(.5,.012,'估算情景 · 分子与分母均由三个情景种子的计数累计',ha='center',fontsize=7,color=GRAY)
save(fig,'recovery_risk')
(out/'plot_manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
print('Three hypothetical plots exported; original diagrams retained.')
