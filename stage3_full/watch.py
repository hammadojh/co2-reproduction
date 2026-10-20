import json,time
from pathlib import Path
r=Path(__file__).resolve().parents[1]
start=time.monotonic();initial=None
while True:
 states=[json.loads((r/f/'results/status.json').read_text()) for f in ['stage3_nationwide','stage3_full']]
 total=sum(s['completed'] for s in states)
 if initial is None:initial=total
 rate=(total-initial)/(time.monotonic()-start) if time.monotonic()>start else 0
 print(json.dumps(dict(completed=total,expected=6615,failures=sum(len(s['failures']) for s in states),states=[s['status'] for s in states],recent_cases_per_second=round(rate,2),remaining_minutes=round((6615-total)/rate/60,1) if rate>0 else None)),flush=True)
 if all(s['status'] in ['verified','computed','completed','failed'] for s in states):break
 time.sleep(30)
