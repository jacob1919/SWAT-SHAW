"""Scientific plots from the audited post-review JSON and CSV artifacts."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/interface_cases'
summary=json.loads((OUT/'summary.json').read_text())
basin=json.loads((OUT/'basin_checks.json').read_text())
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
fig,axes=plt.subplots(1,2,figsize=(13,5.6),gridspec_kw={'width_ratios':[1,1.5]},layout='constrained')
colors=['#334E68','#D57A36','#207D78']
models=['official','existing_ft','shaw'];labels=['Official SWAT+','Existing freeze-thaw','SWAT+SHAW']
fields=['et','surq_gen','perc']
x=np.arange(3);width=.24
for i,(m,label,color) in enumerate(zip(models,labels,colors)):
    v=[basin['totals'][m][f] for f in fields]
    bars=axes[0].bar(x+(i-1)*width,v,width,label=label,color=color)
    axes[0].bar_label(bars,fmt='%.0f',fontsize=8,padding=3)
axes[0].set_xticks(x,['ET','Surface runoff','Percolation'])
axes[0].set_ylabel('Evaluation-period depth (mm)')
axes[0].set_title('A  Full basin: common corrected AWC',loc='left',fontweight='bold')
axes[0].set_ylim(0,1700);axes[0].legend(frameon=False,loc='upper right',fontsize=9)
names=['legacy_hru1','radiation_hru1','height_hru1','combined_hru1','corrected_hru1','thermal_hru1','rain6h_hru1']
tick=['Legacy','Radiation','Height','Both','+ AWC','Estimated\nbottom T','6 h rain']
x=np.arange(len(names))
for j,(field,label,color) in enumerate([('runoff_mm','Surface runoff','#D57A36'),('percolation_mm','Percolation','#207D78')]):
    v=[summary['cases'][n]['ledger']['evaluation_totals_mm'][field] for n in names]
    bars=axes[1].bar(x+(j-.5)*.35,v,.35,label=label,color=color)
    axes[1].bar_label(bars,fmt='%.0f',fontsize=8,padding=3)
axes[1].set_xticks(x,tick,rotation=25,ha='right')
axes[1].set_ylabel('HRU 1 evaluation-period depth (mm)')
axes[1].set_title('B  HRU 1: interface and boundary sensitivity',loc='left',fontweight='bold')
axes[1].legend(frameon=False,fontsize=9);axes[1].set_ylim(0,1350)
for ax in axes:
    ax.set_axisbelow(True);ax.grid(axis='y',color='#dddddd',lw=.5)
fig.suptitle('Canadian process comparison | 1 Jan 2021 – 30 Apr 2023',fontsize=15,fontweight='bold')
fig.supxlabel('Panel B: first four cases use original AWC; last three use corrected AWC. Last two vary one factor from + AWC.\nSimulated differences only: no observational accuracy or energy-closure claim.',fontsize=9)
for ext in ('png','pdf'):fig.savefig(OUT/('review_process_comparison.'+ext))
print('Saved review_process_comparison.png and .pdf')
