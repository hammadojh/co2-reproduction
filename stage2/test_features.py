import unittest,sys
from pathlib import Path
import numpy as np
import pandas as pd
from features import engineer,prepare_variants,NEW_FEATURES,FULL_FEATURES
from baseline import prepare
class FeatureTests(unittest.TestCase):
 def setUp(self):
  n=100;self.sd=pd.DataFrame(dict(date=pd.date_range('2020-01-01',periods=n),co2_mass=np.arange(1,n+1,dtype=float),gross_load_mwh=np.arange(10,n+10,dtype=float),heat_input=np.arange(10,n+10,dtype=float)*2,so2_mass=np.ones(n),nox_mass=np.ones(n),n_facilities=np.arange(n)+50))
 def test_hand_calculated_values(self):
  d=engineer(self.sd,1);i=40;r=d.iloc[i]
  self.assertAlmostEqual(r.co2_relative_change_1d,1/40)
  self.assertAlmostEqual(r.co2_relative_change_7d,7/34)
  self.assertAlmostEqual(r.co2_relative_departure_7d,(41-37)/37)
  expected=np.array([35,28,21,14]);self.assertAlmostEqual(r.target_weekday_co2_mean4,expected.mean());self.assertAlmostEqual(r.target_weekday_co2_std4,expected.std(ddof=1))
  self.assertAlmostEqual(r.load_relative_week_change,(47-40)/40)
  self.assertEqual(r.facility_change_7d,7)
 def test_weekday_alignment_all_horizons(self):
  for h in [1,2,3,5,7,10,14]:
   d=engineer(self.sd,h);offset=(-h)%7
   for k in range(4):self.assertEqual((d.date.iloc[40]-pd.Timedelta(days=offset+7*k)).dayofweek,d.target_date.iloc[40].dayofweek)
   self.assertAlmostEqual(d.iloc[40].target_weekday_co2_mean4,np.mean([41-offset-7*k for k in range(4)]))
 def test_future_invariance(self):
  for h in [1,7,14]:
   a=engineer(self.sd,h);changed=self.sd.copy();changed.loc[61:,'co2_mass']*=100;changed.loc[61:,'gross_load_mwh']*=100;changed.loc[61:,'heat_input']*=100;changed.loc[61:,'n_facilities']*=100
   b=engineer(changed,h);np.testing.assert_allclose(a.loc[:60,NEW_FEATURES],b.loc[:60,NEW_FEATURES],equal_nan=True)
 def test_calendar_gaps_not_compressed(self):
  d=engineer(self.sd.drop(index=34),1);self.assertTrue(pd.isna(d.iloc[40].target_weekday_co2_mean4));self.assertEqual(d.iloc[40].target,42)
 def test_zero_denominator_unavailable(self):
  self.sd.loc[39,'co2_mass']=0;d=engineer(self.sd,1);self.assertTrue(pd.isna(d.iloc[40].co2_relative_change_1d))
 def test_baseline_preserved_and_population_equal(self):
  variants=prepare_variants(self.sd,7);ref=prepare(self.sd,7).set_index('date')
  for v,d in variants.items():self.assertEqual(list(d.date),list(variants['baseline'].date))
  d=variants['baseline'].set_index('date');np.testing.assert_allclose(d[FULL_FEATURES],ref.loc[d.index,FULL_FEATURES]);np.testing.assert_allclose(d.target,ref.loc[d.index].target)
if __name__=='__main__':unittest.main()
