"""Budget conditions from explicitly simulated records; no measured runtime."""
from pathlib import Path
import os,sys,json
W=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(W/'mpl-cache'))
sys.path.insert(0,str(W.parent/'_revision_1010_v3/vendor'))
sys.path.insert(0,str(W/'qa_tools'))
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from audit_panel_alignment import require_matplotlib_panel_alignment
font_manager.fontManager.addfont('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial Unicode MS','DejaVu Sans'],'font.size':8.3,'svg.fonttype':'none','pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'legend.frameon':False,'figure.facecolor':'white','savefig.facecolor':'white','text.usetex':False})
r=json.loads((W/'supplement_results.json').read_text());fig,axes=plt.subplots(1,2,figsize=(157/25.4,80/25.4),sharey=True)
fig.subplots_adjust(left=.10,right=.98,bottom=.36,top=.83,wspace=.23)
for ax,group,title in zip(axes,['all','large'],['a  整体 148篇','b  大规模组 49篇']):
 for method,label,color,marker in [('local','局部 BR-J','#286B8B','o'),('global','全局 ILP','#B77336','s')]:
  rows=sorted([x for x in r['budget'] if x['dataset']=='CDCP' and x['group']==group and x['method']==method],key=lambda x:x['multiplier'])
  ax.errorbar([x['multiplier']*36 for x in rows],[x['mean_f1'] for x in rows],yerr=[x['sd_f1'] for x in rows],label=label,color=color,marker=marker,ms=3.2,lw=1.1,elinewidth=.7,capsize=2)
 ax.set_title(title,loc='left',fontsize=9,pad=10)
 ax.set_xticks([18,36,72]);ax.set_xlim(12,78);ax.set_ylim(53,64);ax.set_yticks([54,57,60,63]);ax.grid(axis='y',lw=.45,color='#DFE4E8');ax.set_axisbelow(True)
 ax.set_xlabel('端到端时限（秒）',fontsize=8.3,labelpad=5);ax.tick_params(labelsize=8,length=3,pad=3)
axes[0].set_ylabel('严格关系 F1（%）',fontsize=8.3,labelpad=7)
fig.text(.98,.95,'CDCP规模模拟情景',ha='right',va='top',fontsize=8,color='#687781')
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.11),ncol=2,fontsize=8.2,handlelength=2.2,columnspacing=2)
fig.text(.5,.035,'误差棒：三个模拟种子的样本标准差；预检失败保留在分母中',ha='center',fontsize=7.7,color='#687781')
fig.canvas.draw()
require_matplotlib_panel_alignment(fig,json_out=W/'figures/budget_conditions.alignment.json',tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
fig.savefig(W/'figures/budget_conditions.svg')
fig.savefig(W/'figures/budget_conditions.pdf')
fig.savefig(W/'figures/budget_conditions.png',dpi=600)
fig.savefig(W/'figures/budget_conditions.preview.png',dpi=300)
plt.close(fig)
print('Exported budget conditions at 157 x 80 mm')
