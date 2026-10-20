"""Scheduling-only override; preserve run.py and its source manifest."""
import os,sys,json,hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
import run as runner
from concurrent.futures import ProcessPoolExecutor
def pool(*args,**kwargs):
 kwargs['max_workers']=8
 return ProcessPoolExecutor(*args,**kwargs)
original_atomic=runner.atomic
def atomic(path,data):
 if path.name=='protocol.json':
  data['workers']=8
  data['scheduling_override']='run_fast.py; evaluation and feature code unchanged'
  data['scheduling_override_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 return original_atomic(path,data)
if __name__=='__main__':
 runner.ProcessPoolExecutor=pool
 runner.atomic=atomic
 print('Actual worker count: 8 (scheduling override only)',flush=True)
 runner.main()
