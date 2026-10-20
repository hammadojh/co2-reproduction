"""Ablation of the primary paper's 27 original features, with no new predictors."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stage0'))
from original_definitions import FULL_FEATURES,CALENDAR_FEATURES,LAG_FEATURES,TARGET_INDEPENDENT_OPERATIONAL_FEATURES
GROUPS={'calendar':CALENDAR_FEATURES+['year'],'co2_history':LAG_FEATURES,'operational':TARGET_INDEPENDENT_OPERATIONAL_FEATURES}
VARIANTS={'baseline':list(FULL_FEATURES),**{f'without_{g}':[f for f in FULL_FEATURES if f not in cols] for g,cols in GROUPS.items()},**{f'{g}_only':list(cols) for g,cols in GROUPS.items()}}
def feature_columns(variant):return VARIANTS[variant]
assert len(FULL_FEATURES)==27
assert set(sum(GROUPS.values(),[]))==set(FULL_FEATURES)
assert len(sum(GROUPS.values(),[]))==len(set(FULL_FEATURES))
assert all(set(cols)<=set(FULL_FEATURES) for cols in VARIANTS.values())
