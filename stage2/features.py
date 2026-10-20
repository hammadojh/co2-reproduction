"""Prespecified causal feature groups; no feature selection against test outcomes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stage0'))
import numpy as np
import pandas as pd
from original_definitions import engineer_features,FULL_FEATURES
GROUPS={
 'relative_dynamics':['co2_relative_change_1d','co2_relative_change_7d','co2_relative_departure_7d'],
 'weekday_history':['target_weekday_co2_mean4','target_weekday_co2_std4'],
 'operational_history':['load_relative_week_change','heat_per_mwh_mean7','facility_change_7d'],
}
NEW_FEATURES=[f for group in GROUPS.values() for f in group]
VARIANTS={'baseline':[],**{f'add_{g}':[g] for g in GROUPS},'all':list(GROUPS),**{f'without_{g}':[x for x in GROUPS if x!=g] for g in GROUPS}}

def ratio(numerator,denominator):
    # No arbitrary epsilon or full-data scaling. Nonpositive/absent reference => unavailable.
    return numerator/denominator.where(denominator>0)

def feature_columns(variant):
    return FULL_FEATURES+[f for g in VARIANTS[variant] for f in GROUPS[g]]

def engineer(sd,horizon):
    if not isinstance(horizon,int) or horizon<1:raise ValueError('Positive integer horizon required')
    sd=sd.copy();sd['date']=pd.to_datetime(sd.date)
    if sd.date.duplicated().any():raise ValueError('Duplicate dates')
    sd=sd.set_index('date').sort_index().reindex(pd.date_range(sd.date.min(),sd.date.max(),freq='D'));sd.index.name='date'
    d=engineer_features(sd.reset_index());c=d.co2_mass
    d['co2_relative_change_1d']=ratio(c-c.shift(1),c.shift(1))
    d['co2_relative_change_7d']=ratio(c-c.shift(7),c.shift(7))
    d['co2_relative_departure_7d']=ratio(c-d.co2_mass_roll7_mean,d.co2_mass_roll7_mean)
    # Most recent date <=t with the same weekday as t+h, then preceding 3 weeks.
    offset=(-horizon)%7
    history=pd.concat([c.shift(offset+7*k) for k in range(4)],axis=1)
    complete=history.notna().all(axis=1)
    d['target_weekday_co2_mean4']=history.mean(axis=1).where(complete)
    d['target_weekday_co2_std4']=history.std(axis=1,ddof=1).where(complete)
    recent_load=d.gross_load_mwh.rolling(7,min_periods=7).mean()
    previous_load=d.gross_load_mwh.shift(7).rolling(7,min_periods=7).mean()
    d['load_relative_week_change']=ratio(recent_load-previous_load,previous_load)
    # Retain the original heat_per_mwh definition, including its +1 denominator.
    d['heat_per_mwh_mean7']=d.heat_per_mwh.rolling(7,min_periods=7).mean()
    d['facility_change_7d']=d.n_facilities-d.n_facilities.shift(7)
    d['target_date']=d.date+pd.Timedelta(days=horizon)
    d['target']=c.shift(-horizon)
    return d.replace([np.inf,-np.inf],np.nan)

def prepare_variants(sd,horizon):
    """All variants use the all-features complete-case population for fair ablation."""
    d=engineer(sd,horizon).dropna(subset=FULL_FEATURES+NEW_FEATURES+['target']).reset_index(drop=True)
    return {v:d[['date','target_date','target']+feature_columns(v)].copy() for v in VARIANTS}
