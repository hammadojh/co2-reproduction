"""Resumable, locked, two-worker nationwide extension of the original-feature pilot."""
import os
os.environ['PYTHONDONTWRITEBYTECODE']='1'
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[name]='1'
import sys, json, time, hashlib, platform, fcntl, traceback, random
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
OUT=BASE/'results'
sys.path.insert(0,str(BASE))
from case import case, VARIANTS, GROUPS, FULL_FEATURES, threadpool_limits, threadpool_info, pd
HORIZONS=[1,7,14]
MODELS=['ridge','gam','hgb']

def atomic(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    tmp.replace(path)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def key(task):
    s,h,v,m=task
    return f'{s}_h{h}_{m}_{v}'

def worker(task):
    started=time.monotonic()
    with threadpool_limits(limits=1):
        result=case(*task)
        result['native_threads']=threadpool_info()
    result['elapsed_s']=time.monotonic()-started
    result['completed_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    return result

def main():
    for folder in [OUT,OUT/'predictions',OUT/'checkpoints']:
        folder.mkdir(exist_ok=True)
    lock=(BASE/'run.lock').open('a+')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('Nationwide run already holds the lock; no duplicate started.')
    lock.seek(0);lock.truncate();lock.write(str(os.getpid()));lock.flush()
    data=ROOT/'Manuscript V1/Data/extended_state_daily'
    eligible=pd.read_csv(ROOT/'Manuscript V1/Data/extended_eligibility.csv')
    states=sorted(eligible.loc[eligible.eligible,'state'])
    assert len(states)==45 and set(states)=={p.stem for p in data.glob('*.csv')}
    tasks=[(s,h,v,m) for s in states for h in HORIZONS for v in VARIANTS for m in MODELS]
    # Pilot cases first make regression verification visible early; shuffle each tier.
    pilot=[t for t in tasks if t[0] in ['TX','PA','CA']]
    rest=[t for t in tasks if t[0] not in ['TX','PA','CA']]
    random.Random(42).shuffle(pilot);random.Random(42).shuffle(rest);tasks=pilot+rest
    manifest_path=BASE/'source_manifest.json'
    protected=[p for folder in ['Manuscript V1','stage0','stage1','stage2','stage3','stage3_original'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='.DS_Store']
    protected += [p for p in ROOT.glob('*.docx')]
    source=[BASE/'case.py',BASE/'run.py',BASE/'summarize.py']
    hashes={str(p.relative_to(ROOT)):digest(p) for p in protected+source}
    if manifest_path.exists():
        assert json.loads(manifest_path.read_text())==hashes,'Protected inputs or runner changed; refusing mixed-protocol resume.'
    else:atomic(manifest_path,hashes)
    atomic(OUT/'protocol.json',dict(states=states,horizons=HORIZONS,models=MODELS,variants=VARIANTS,groups=GROUPS,expected=len(tasks),workers=2,native_threads_per_worker=1,missingness='daily reindex, no imputation; identical full-feature complete-case dates for all models and variants',tuning='original 12-setting grids; prospective validation; same pilot cutoff and 14-calendar-day retraining',python=platform.python_version(),platform=platform.platform()))
    rows={}
    for task in tasks:
        cp=OUT/'checkpoints'/f'{key(task)}.json'
        if cp.exists():
            r=json.loads(cp.read_text())
            assert (OUT/'predictions'/f'{key(task)}.csv').exists() and (OUT/f'{key(task)}_audit.json').exists()
            rows[key(task)]=r
    pending=[t for t in tasks if key(t) not in rows]
    failures={};started=time.monotonic();initial=len(rows)
    def status(state):
        elapsed=time.monotonic()-started
        done=len(rows)-initial
        atomic(OUT/'status.json',dict(status=state,pid=os.getpid(),completed=len(rows),expected=len(tasks),remaining=len(tasks)-len(rows),failures=failures,elapsed_this_run_s=elapsed,estimated_remaining_s=(elapsed/done*(len(tasks)-len(rows)) if done else None),updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
    status('running')
    print(f'START pid={os.getpid()} completed={len(rows)} expected={len(tasks)} workers=2 native_threads=1',flush=True)
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(worker,t):(t,0) for t in pending}
        while futures:
            future=next(as_completed(futures));task,attempt=futures.pop(future)
            try:
                r=future.result();atomic(OUT/'checkpoints'/f'{key(task)}.json',r);rows[key(task)]=r
                print(f'{len(rows)}/{len(tasks)} {key(task)} {r["elapsed_s"]:.2f}s',flush=True)
            except Exception:
                error=traceback.format_exc()
                if attempt==0:
                    print(f'RETRY {key(task)} {error}',flush=True)
                    futures[pool.submit(worker,task)]=(task,1)
                else:failures[key(task)]=error;print(f'FAILED {key(task)} {error}',flush=True)
            status('running')
    # Every case is independently durable; this aggregate is rebuilt on resume.
    pd.DataFrame(rows.values()).drop(columns=['native_threads'],errors='ignore').to_csv(OUT/'metrics.csv',index=False)
    status('failed' if failures else 'completed')
    if failures:raise SystemExit(1)
    import subprocess
    subprocess.run([sys.executable,'-B',str(BASE/'summarize.py')],check=True)
    status('verified')

if __name__=='__main__':main()
