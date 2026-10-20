"""Describe changed scores; do not attribute all changes to a single correction."""
from pathlib import Path
import hashlib,json
import pandas as pd
from baseline import DATA,ROOT
base=Path(__file__).parent
new=pd.read_csv(base/'results/pilot/summary.csv')
old=pd.read_csv(DATA/'multihorizon_summary.csv')
gam=pd.read_csv(DATA/'gam_national_summary.csv')
rows=[]
for r in new.to_dict('records'):
    src=gam if r['model']=='gam' else old
    match=src[(src.state==r['state'])&(src.horizon==r['horizon'])].iloc[0]
    col={'ridge':'R2_ridge','hgb':'R2_HGB','gam':'R2_GAM','persistence':'R2_persist'}[r['model']]
    rows.append(dict(state=r['state'],horizon=r['horizon'],model=r['model'],original_R2=match[col],corrected_R2=r['R2'],change_R2=r['R2']-match[col],original_n=match['n'],corrected_n=r['n']))
c=pd.DataFrame(rows);c.to_csv(base/'results/pilot/original_vs_corrected.csv',index=False)
manifest=json.loads((base/'source_manifest.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in manifest.items())
print('All',len(manifest),'original file hashes unchanged.')
print(new.groupby(['horizon','model']).R2.mean().unstack().round(4).to_string())
print('Mean change vs original',c.groupby('model').change_R2.mean().round(4).to_dict())
