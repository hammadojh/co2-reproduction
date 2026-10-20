# Extracted unchanged model and feature definitions from supplied notebook.
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler
SEED = 42
RENAME_RAW_COLUMNS = {
    "State": "state", "Facility Name": "facility_name", "Facility ID": "facility_id",
    "Date": "date", "Gross Load (MWh)": "gross_load_mwh", "Steam Load (1000 lb)": "steam_load",
    "SO2 Mass (short tons)": "so2_mass", "CO2 Mass (short tons)": "co2_mass",
    "NOx Mass (short tons)": "nox_mass", "Heat Input (mmBtu)": "heat_input",
}

def _mincount_sum(s: pd.Series) -> float:
    """Sum that returns NaN (not 0) when every value in the group is missing."""
    return s.sum(min_count=1)

def build_state_daily_from_raw(csv_dir):
    """Reconstruct the TX/PA/CA state-day dataset from raw CAMPD yearly exports.

    Mirrors the standalone dataset-construction stage (Section 5 below)
    exactly, so results computed here are directly comparable to the
    manuscript's reported values.
    """
    csv_dir = Path(csv_dir)
    files = sorted(csv_dir.glob("daily-emissions-facility-aggregation*.csv"))
    if not files:
        raise FileNotFoundError(f"No CAMPD exports found in {csv_dir}")
    df = pd.concat([pd.read_csv(f, parse_dates=["Date"]) for f in files], ignore_index=True)
    df.columns = [c.strip() for c in df.columns]
    df = df.drop_duplicates(subset=["State", "Facility ID", "Date"]).rename(columns=RENAME_RAW_COLUMNS)
    df = df[(df["date"] >= "2023-01-01") & (df["date"] <= "2025-12-31")].copy()

    sd = (
        df[df.state.isin(FOCUS_STATES)]
        .groupby(["state", "date"], as_index=False)
        .agg(
            co2_mass=("co2_mass", _mincount_sum),
            so2_mass=("so2_mass", _mincount_sum),
            nox_mass=("nox_mass", _mincount_sum),
            gross_load_mwh=("gross_load_mwh", _mincount_sum),
            heat_input=("heat_input", _mincount_sum),
            n_facilities=("facility_id", "nunique"),
        )
        .sort_values(["state", "date"])
        .reset_index(drop=True)
    )
    return sd

def load_state_daily(path):
    """Load an already-built state-day CSV (columns: state, date, co2_mass, ...)."""
    return pd.read_csv(path, parse_dates=["date"])

CALENDAR_FEATURES = [
    "month_sin", "month_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos", "is_weekend",
]

LAG_FEATURES = [
    "co2_mass_lag0",
    "co2_mass_lag1", "co2_mass_lag2", "co2_mass_lag3", "co2_mass_lag7",
    "co2_mass_lag14", "co2_mass_lag30",
    "co2_mass_roll7_mean", "co2_mass_roll7_std",
    "co2_mass_roll14_mean", "co2_mass_roll14_std",
    "co2_mass_roll30_mean", "co2_mass_roll30_std",
]

TARGET_INDEPENDENT_OPERATIONAL_FEATURES = [
    "gross_load_mwh", "heat_input", "so2_mass", "nox_mass", "n_facilities", "heat_per_mwh",
]

CURRENT_EMISSIONS_TRANSFORM_FEATURES = [
    "co2_per_mwh", "so2_co2_ratio",
]

FULL_FEATURES = (
    CALENDAR_FEATURES + ["year"] + LAG_FEATURES + TARGET_INDEPENDENT_OPERATIONAL_FEATURES
)

FEATURE_GROUPS = {
    "calendar_only": CALENDAR_FEATURES + ["year"],
    "co2_history_only": LAG_FEATURES,
    "target_independent_operational_only": TARGET_INDEPENDENT_OPERATIONAL_FEATURES,
    "current_emissions_transforms_only": CURRENT_EMISSIONS_TRANSFORM_FEATURES,
    "co2_history_plus_operational": LAG_FEATURES + TARGET_INDEPENDENT_OPERATIONAL_FEATURES,
    "full": FULL_FEATURES,
}

def engineer_features(state_df):
    """Add calendar, lag/rolling, and operational-ratio features to one state's daily series.

    d[t] uses only information available at or before t (lag/rolling features are
    shifted by at least 1 day before the window is computed), so no leakage from
    the forecast target enters the feature set.
    """
    d = state_df.sort_values("date").copy().reset_index(drop=True)
    d["day_of_week"] = d["date"].dt.dayofweek
    d["month"] = d["date"].dt.month
    d["year"] = d["date"].dt.year
    d["day_of_year"] = d["date"].dt.dayofyear
    d["is_weekend"] = (d["day_of_week"] >= 5).astype(int)
    d["month_sin"] = np.sin(2 * np.pi * d["month"] / 12)
    d["month_cos"] = np.cos(2 * np.pi * d["month"] / 12)
    d["dow_sin"] = np.sin(2 * np.pi * d["day_of_week"] / 7)
    d["dow_cos"] = np.cos(2 * np.pi * d["day_of_week"] / 7)
    d["doy_sin"] = np.sin(2 * np.pi * d["day_of_year"] / 365.25)
    d["doy_cos"] = np.cos(2 * np.pi * d["day_of_year"] / 365.25)
    for lag in [0, 1, 2, 3, 7, 14, 30]:
        d[f"co2_mass_lag{lag}"] = d["co2_mass"].shift(lag)
    for w in [7, 14, 30]:
        d[f"co2_mass_roll{w}_mean"] = d["co2_mass"].shift(1).rolling(w).mean()
        d[f"co2_mass_roll{w}_std"] = d["co2_mass"].shift(1).rolling(w).std()
    d["co2_per_mwh"] = d["co2_mass"] / (d["gross_load_mwh"] + 1)
    d["so2_co2_ratio"] = d["so2_mass"] / (d["co2_mass"] + 1)
    d["heat_per_mwh"] = d["heat_input"] / (d["gross_load_mwh"] + 1)
    return d

def make_xy(state_df, feature_cols, horizon=1):
    """Build (X, y_target, y_current, dates) for a given horizon, dropping rows
    with insufficient lag history. y_target is the actual CO2 mass at t+horizon;
    y_current is CO2 mass at t (used for the persistence baseline)."""
    d = engineer_features(state_df)
    d = d.dropna(subset=feature_cols + ["co2_mass"]).reset_index(drop=True)
    X = d[feature_cols].to_numpy()
    y_target = d["co2_mass"].shift(-horizon).to_numpy()
    y_current = d["co2_mass"].to_numpy()
    dates = d["date"].to_numpy()
    X, y_target, y_current, dates = X[:-horizon], y_target[:-horizon], y_current[:-horizon], dates[:-horizon]
    return X, y_target, y_current, dates

def chronological_split(n, train_frac=0.70, val_frac=0.15):
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    return n_train, n_val, n - n_train - n_val

def metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    return {
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "MAPE": float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100),
        "R2": float(r2_score(y_true, y_pred)),
    }

def fit_predict_ridge(X_train, y_train, X_test, alpha=1.0):
    scaler = StandardScaler().fit(X_train)
    model = Ridge(alpha=alpha, random_state=SEED).fit(scaler.transform(X_train), y_train)
    return model.predict(scaler.transform(X_test)), model

def fit_predict_hgb(X_train, y_train, X_test, learning_rate=0.06,
                     max_depth=3, max_iter=120, min_samples_leaf=14):
    model = HistGradientBoostingRegressor(
        random_state=SEED, learning_rate=learning_rate, max_depth=max_depth,
        max_iter=max_iter, min_samples_leaf=min_samples_leaf,
    ).fit(X_train, y_train)
    return model.predict(X_test), model

HGB_GRID = [
    {"learning_rate": 0.03, "max_depth": 2, "max_iter": 100, "min_samples_leaf": 10},
    {"learning_rate": 0.03, "max_depth": 3, "max_iter": 150, "min_samples_leaf": 14},
    {"learning_rate": 0.03, "max_depth": 4, "max_iter": 150, "min_samples_leaf": 20},
    {"learning_rate": 0.06, "max_depth": 2, "max_iter": 80, "min_samples_leaf": 10},
    {"learning_rate": 0.06, "max_depth": 3, "max_iter": 120, "min_samples_leaf": 14},
    {"learning_rate": 0.06, "max_depth": 4, "max_iter": 120, "min_samples_leaf": 20},
    {"learning_rate": 0.06, "max_depth": 5, "max_iter": 100, "min_samples_leaf": 25},
    {"learning_rate": 0.1, "max_depth": 2, "max_iter": 80, "min_samples_leaf": 10},
    {"learning_rate": 0.1, "max_depth": 3, "max_iter": 100, "min_samples_leaf": 14},
    {"learning_rate": 0.1, "max_depth": 4, "max_iter": 80, "min_samples_leaf": 20},
    {"learning_rate": 0.15, "max_depth": 3, "max_iter": 80, "min_samples_leaf": 14},
    {"learning_rate": 0.15, "max_depth": 4, "max_iter": 60, "min_samples_leaf": 25},
]

RIDGE_ALPHA_GRID = [0.1, 0.3, 1, 3, 10, 30, 50, 100, 200, 300, 500, 1000]

def fit_predict_gam(Xtr, ytr, Xte, alpha=1.0, n_knots=5):
    model = make_pipeline(
        StandardScaler(),
        SplineTransformer(n_knots=n_knots, degree=3, include_bias=False),
        Ridge(alpha=alpha, random_state=SEED),
    )
    model.fit(Xtr, ytr)
    return model.predict(Xte)

