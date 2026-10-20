"""Calendar component investigation; reuses unchanged nationwide fitting protocol."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']: os.environ[k]='1'
import sys,json,hashlib,time,fcntl
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage3_nationwide'))
import case as c
OUT=ROOT/'stage4_calendar/results'
c.OUT=OUT
REMOVALS={'month':['month_sin','month_cos'],'weekday':['dow_sin','dow_cos'],'day_of_year':['doy_sin','doy_cos'],'weekend':['is_weekend'],'year':['year'],'annual':['month_sin','month_cos','doy_sin','doy_cos'],'weekly':['dow_sin','dow_cos','is_weekend']}
for name,cols in REMOVALS.items(): c.VARIANTS['drop_'+name]=[x for x in c.FULL_FEATURES if x not in cols]
def worker(task):
 with c.threadpool_limits(limits=1): return c.case(*task)
def main():
 lock=(OUT/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 states=sorted(c.pd.read_csv(ROOT/'Manuscript V1/Data/extended_eligibility.csv').query('eligible').state)
 tasks=[(s,14,'drop_'+v,m) for v in REMOVALS for s in states for m in ['ridge','gam','hgb']]
 protected=[ROOT/'stage0/original_definitions.py',ROOT/'stage0/baseline.py',ROOT/'stage1/benchmark.py',ROOT/'stage3_nationwide/case.py',Path(__file__)]+list((ROOT/'Manuscript V1/Data/extended_state_daily').glob('*.csv'))
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 manifest=OUT/'source_hashes.json'
 if manifest.exists(): assert json.loads(manifest.read_text())==hashes
 else: manifest.write_text(json.dumps(hashes,indent=2))
 (OUT/'protocol.json').write_text(json.dumps(dict(states=states,horizon=14,removals=REMOVALS,expected=len(tasks),workers=6,protocol='unchanged stage3_nationwide/case.py; paired full-feature complete cases; retune each variant'),indent=2))
 rows=[];pending=[]
 for t in tasks:
  p=OUT/'checkpoints'/('_'.join(map(str,t))+'.json')
  if p.exists():rows.append(json.loads(p.read_text()))
  else:pending.append(t)
 with ProcessPoolExecutor(max_workers=6) as pool:
  jobs={pool.submit(worker,t):t for t in pending}
  for f in as_completed(jobs):
   t=jobs[f];r=f.result();(OUT/'checkpoints'/('_'.join(map(str,t))+'.json')).write_text(json.dumps(r));rows.append(r)
   (OUT/'status.json').write_text(json.dumps(dict(completed=len(rows),expected=len(tasks))))
   print(f'{len(rows)}/{len(tasks)} {t}',flush=True)
 c.pd.DataFrame(rows).to_csv(OUT/'metrics.csv',index=False)
 assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
if __name__=='__main__':main()
