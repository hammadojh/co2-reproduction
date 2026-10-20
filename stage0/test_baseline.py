import unittest
import pandas as pd
import numpy as np
from baseline import prepare, eligible_training, DATA, FULL_FEATURES, tune
from unittest.mock import patch

class TemporalTests(unittest.TestCase):
    def setUp(self):
        self.sd=pd.read_csv(DATA/'extended_state_daily/TX.csv').iloc[:200].copy()
    def test_exact_calendar_horizons_despite_gap(self):
        d=prepare(self.sd.drop(index=100),7)
        truth=self.sd.set_index('date').co2_mass
        self.assertTrue(((d.target_date-d.date).dt.days==7).all())
        np.testing.assert_allclose(d.target,[truth[str(x.date())] for x in d.target_date])
        self.assertNotIn(pd.Timestamp(self.sd.iloc[100].date),set(d.target_date))
    def test_unavailable_targets_excluded(self):
        d=prepare(self.sd,14);cut=d.date.iloc[100];tr=eligible_training(d,cut)
        self.assertTrue((tr.target_date<=cut).all())
        self.assertTrue((tr.date<cut).all())
        self.assertLess(len(tr),100)
    def test_future_inputs_do_not_change_past_features(self):
        cut=pd.Timestamp(self.sd.date.iloc[130]);old=prepare(self.sd,7)
        new=self.sd.copy();new.loc[pd.to_datetime(new.date)>cut,'co2_mass']*=100
        new=prepare(new,7)
        np.testing.assert_allclose(old.loc[old.date<=cut,FULL_FEATURES],new.loc[new.date<=cut,FULL_FEATURES])
    def test_tuning_respects_both_information_cutoffs(self):
        d=prepare(self.sd,14);outer=d.date.iloc[120]
        calls=[]
        def fake_predict(model,train,test,setting):
            calls.append((train.target_date.max(),test.date.min(),test.target_date.max()))
            return np.repeat(train.target.mean(),len(test))
        with patch('baseline.predict',side_effect=fake_predict):
            tune(d,outer)
        self.assertEqual(len(calls),36)
        for last_train,first_val,last_val in calls:
            self.assertLessEqual(last_train,first_val)
            self.assertLessEqual(last_val,outer)

    def test_missing_feature_does_not_retarget_neighbor(self):
        self.sd.loc[100,'gross_load_mwh']=np.nan
        d=prepare(self.sd,7);row=d[d.date==pd.Timestamp(self.sd.date.iloc[93])].iloc[0]
        self.assertEqual(row.target,self.sd.co2_mass.iloc[100])

if __name__=='__main__':unittest.main()
