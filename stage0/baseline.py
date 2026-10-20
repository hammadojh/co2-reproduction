"""Calendar-aligned, end-of-day forecasting baseline; original inputs stay read-only."""
import argparse, json, platform, time
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from original_definitions import (engineer_features, FULL_FEATURES, RIDGE_ALPHA_GRID,
 HGB_GRID, fit_predict_ridge, fit_predict_hgb, fit_predict_gam, metrics)
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'Manuscript V1/Data'


def prepare(sd, horizon):
    sd = sd.copy(); sd['date'] = pd.to_datetime(sd.date)
    if sd.date.duplicated().any(): raise ValueError('Duplicate dates')
    # Missing days remain missing: never shift across gaps or impute future data.
    sd = sd.set_index('date').sort_index().reindex(pd.date_range(sd.date.min(), sd.date.max(), freq='D'))
    sd.index.name = 'date'
    d = engineer_features(sd.reset_index())
    d['target_date'] = d.date + pd.Timedelta(days=horizon)
    d['target'] = d.co2_mass.shift(-horizon)
    return d.replace([np.inf, -np.inf], np.nan).dropna(subset=FULL_FEATURES+['target']).reset_index(drop=True)


def eligible_training(d, cutoff):
    # End-of-day origin: outcome dated cutoff is assumed observed, future ones aren't.
    return d[(d.date < cutoff) & (d.target_date <= cutoff)]


def predict(model, train, test, setting):
    args=(train[FULL_FEATURES].to_numpy(), train.target.to_numpy(), test[FULL_FEATURES].to_numpy())
    if model=='ridge': return fit_predict_ridge(*args, alpha=setting)[0]
    if model=='hgb': return fit_predict_hgb(*args, **setting)[0]
    return fit_predict_gam(*args, alpha=setting)


def tune(d, outer_cutoff):
    available=eligible_training(d,outer_cutoff)
    nval=max(int(len(available)*.15),20)
    val=available.iloc[-nval:]
    train=eligible_training(available,val.date.iloc[0])
    assert train.target_date.max() <= val.date.iloc[0]
    assert val.target_date.max() <= outer_cutoff
    settings={}
    for model,grid in [('ridge',RIDGE_ALPHA_GRID),('hgb',HGB_GRID),('gam',RIDGE_ALPHA_GRID)]:
        scores=[metrics(val.target,predict(model,train,val,s))['R2'] for s in grid]
        settings[model]=grid[int(np.argmax(scores))]
    return settings,dict(train_end=str(train.target_date.max()),validation_start=str(val.date.min()),validation_target_end=str(val.target_date.max()),selection_cutoff=str(outer_cutoff))


def run(state,horizon,out):
    sd=pd.read_csv(DATA/'extended_state_daily'/f'{state}.csv')
    d=prepare(sd,horizon)
    # Fix a common date across horizons and later feature variants, using calendar midpoint.
    full_dates=pd.date_range(pd.to_datetime(sd.date).min()+pd.Timedelta(days=30),pd.to_datetime(sd.date).max())
    start=full_dates[len(full_dates)//2]
    settings,tuning=tune(d,start)
    predictions=[];audit=[]
    for block in pd.date_range(start,d.date.max(),freq='14D'):
        test=d[(d.date>=block)&(d.date<block+pd.Timedelta(days=14))]
        if test.empty: continue
        train=eligible_training(d,block)
        assert train.target_date.max()<=block
        audit.append(dict(state=state,horizon=horizon,fit_date=block,last_training_target=train.target_date.max(),n_train=len(train),n_test=len(test)))
        # Fixed model between retrains, but each daily prediction uses that day's observed inputs.
        preds={m:predict(m,train,test,s) for m,s in settings.items()}
        preds['persistence']=test.co2_mass.to_numpy()
        for m,p in preds.items():
            frame=test[['date','target_date','target']].copy();frame['prediction']=p;frame['model']=m;frame['state']=state;frame['horizon']=horizon
            predictions.append(frame)
    pred=pd.concat(predictions,ignore_index=True)
    pred.to_csv(out/f'{state}_h{horizon}_predictions.csv',index=False)
    pd.DataFrame(audit).to_csv(out/f'{state}_h{horizon}_cutoffs.csv',index=False)
    (out/f'{state}_h{horizon}_settings.json').write_text(json.dumps(dict(settings=settings,tuning=tuning),indent=2))
    result=[]
    for m,g in pred.groupby('model'):
        result.append(dict(state=state,horizon=horizon,model=m,n=len(g),**metrics(g.target,g.prediction)))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--states',nargs='+',default=['TX','PA','CA']);p.add_argument('--horizons',nargs='+',type=int,default=[1,7,14]);p.add_argument('--output',default='results/pilot');a=p.parse_args()
    out=Path(__file__).parent/a.output;out.mkdir(parents=True,exist_ok=True)
    started=time.time();rows=[]
    with threadpool_limits(limits=1):
        for state in a.states:
            for h in a.horizons:
                rows+=run(state,h,out);pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
                print(f'{state} h={h}: complete ({time.time()-started:.1f}s)',flush=True)
    import sklearn,scipy
    (out/'environment.json').write_text(json.dumps(dict(python=platform.python_version(),platform=platform.platform(),numpy=np.__version__,pandas=pd.__version__,sklearn=sklearn.__version__,scipy=scipy.__version__,threads=1,elapsed_seconds=time.time()-started),indent=2))

if __name__=='__main__':main()
