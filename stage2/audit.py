"""Profile candidate features on development dates only; never score models."""
from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
from features import engineer,NEW_FEATURES,FULL_FEATURES,GROUPS,VARIANTS,feature_columns
from baseline import DATA
BASE=Path(__file__).parent;OUT=BASE/'results';OUT.mkdir(exist_ok=True)
coverage=[];profiles=[]
for p in sorted((DATA/'extended_state_daily').glob('*.csv')):
 sd=pd.read_csv(p);sd['date']=pd.to_datetime(sd.date)
 dates=pd.date_range(sd.date.min()+pd.Timedelta(days=30),sd.date.max());cut=dates[len(dates)//2]
 # Physically truncate observations at the pre-existing evaluation boundary.
 dev=sd[sd.date<=cut].copy()
 for h in [1,2,3,5,7,10,14]:
  d=engineer(dev,h);base=d.dropna(subset=FULL_FEATURES+['target']);allcase=base.dropna(subset=NEW_FEATURES)
  coverage.append(dict(state=p.stem,horizon=h,development_cutoff=cut,baseline_origins=len(base),all_feature_origins=len(allcase),lost_origins=len(base)-len(allcase),loss_pct=100*(len(base)-len(allcase))/len(base)))
  for f in NEW_FEATURES:
   s=base[f];profiles.append(dict(state=p.stem,horizon=h,feature=f,missing=int(s.isna().sum()),unique=int(s.nunique()),minimum=s.min(),median=s.median(),maximum=s.max(),constant=s.nunique()<=1))
  assert (base.target_date<=cut).all()
pd.DataFrame(coverage).to_csv(OUT/'development_coverage.csv',index=False);pd.DataFrame(profiles).to_csv(OUT/'development_feature_profiles.csv',index=False)
plan=dict(status='frozen candidates before ablation; no performance screening',groups=GROUPS,variants={v:feature_columns(v) for v in VARIANTS},pilot_states=['TX','PA','CA'],pilot_horizons=[1,7,14],models=['ridge','gam','hgb'],selection='No group selected or rejected on held-out test performance',comparison_population='All variants on intersection of valid dates for all candidate features',source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/'features.py',BASE/'audit.py',BASE/'test_features.py']})
(OUT/'candidate_plan.json').write_text(json.dumps(plan,indent=2))
c=pd.DataFrame(coverage);print('Combinations',len(c));print('Total lost origins',c.lost_origins.sum(),'max loss pct',c.loss_pct.max());print('Pilot coverage',c[c.state.isin(['TX','PA','CA'])&c.horizon.isin([1,7,14])].to_string(index=False));print('Constant features by name',pd.DataFrame(profiles).groupby('feature').constant.sum().to_dict())
