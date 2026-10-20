"""Derive concise findings from the verified national summary files."""
from pathlib import Path
import pandas as pd
BASE=Path(__file__).resolve().parent

def section():
 h=pd.read_csv(BASE/'results/full_horizon_summary.csv').set_index(['model','variant','horizon'])
 d=pd.read_csv(BASE/'results/full_state_distribution.csv').set_index(['model','variant','horizon'])
 n=pd.read_csv(BASE/'results/full_model_variant_summary.csv').set_index(['model','variant'])
 lines=['## Main findings','',
 'The nonlinear models’ longer-horizon advantage depends strongly on the original calendar/year feature group under this corrected protocol. Without that group, Ridge has the highest national mean R² at every tested horizon. This is a conditional predictive comparison, not a causal finding or proof that complexity never helps.','',
 '**Fourteen-day forecasts, mean R² across 45 states:**','',
 '| Inputs | Ridge | GAM | HGB |','|---|---:|---:|---:|']
 for v,label in [('baseline','All original features'),('without_calendar','Without calendar/year')]:lines.append('| '+label+' | '+' | '.join(f'{h.loc[(m,v,14),"R2"]:.4f}' for m in ['ridge','gam','hgb'])+' |')
 lines += ['',f'Removing calendar/year at fourteen days worsens GAM in {int(d.loc[("gam","without_calendar",14),"states_worsened"])}/45 states and HGB in {int(d.loc[("hgb","without_calendar",14),"states_worsened"])}/45 states. Median R² losses are {d.loc[("gam","without_calendar",14),"median_R2_loss"]:.4f} and {d.loc[("hgb","without_calendar",14),"median_R2_loss"]:.4f}, respectively, close to the corresponding mean losses. This pattern is therefore not driven solely by a few extreme state results.','',
 'With all original features, Ridge leads the national means at one and two days; GAM leads at three through fourteen days. HGB is slightly below Ridge at three days and first exceeds it at the tested five-day horizon. The earlier reported three-day HGB crossover must therefore not be repeated unchanged after these corrections. These rankings describe averages, without formal significance tests.','',
 'CO₂ history is the most consequential removed group for Ridge when averaged across all state/horizon cases. Calendar/year is the most consequential group for GAM and HGB. Operational inputs contribute comparatively little incremental predictive value when the other groups remain, although their correlated information can still be useful when history is absent.','',
 'The most defensible manuscript addition is a nationwide original-feature ablation explaining which predictor group supports the model-by-horizon pattern. The calendar/year group bundles year, annual cycles, weekday cycles and weekend status; further decomposition would be needed to attribute the result to any one component.','']
 return '\n'.join(lines)

if __name__=='__main__':
 p=BASE/'REPORT.md';text=p.read_text();marker='## National mean R²';assert marker in text
 intro,rest=text.split(marker,1)
 if '## Main findings' in intro:intro=intro.split('## Main findings',1)[0]
 p.write_text(intro+section()+'\n'+marker+rest)
 print(section())
