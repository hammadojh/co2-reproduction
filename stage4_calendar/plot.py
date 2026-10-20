from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent/'results'
s=pd.read_csv(OUT/'summary.csv')
order=['month','weekday','day_of_year','weekend','year','annual','weekly']
labels=['Month cycle','Weekday cycle','Day-of-year cycle','Weekend','Year','Both annual cycles','All weekly inputs']
fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True,sharex=True,layout='constrained')
for ax,model,color in zip(axes,['ridge','gam','hgb'],['#64748b','#0f766e','#c2410c']):
 d=s[s.model==model].set_index('variant').loc[['drop_'+v for v in order]]
 ax.barh(labels,d.mean_R2_loss,color=color);ax.axvline(0,color='black',lw=.7);ax.set_title(model.upper());ax.set_xlabel('Mean R² loss after removal');ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
axes[0].invert_yaxis()
fig.suptitle('Which calendar inputs matter at 14 days?\n45 states; each variant retuned; positive values mean removal hurt',fontsize=12)
fig.savefig(OUT/'calendar_components.png',dpi=180);fig.savefig(OUT/'calendar_components.pdf');plt.close(fig)
