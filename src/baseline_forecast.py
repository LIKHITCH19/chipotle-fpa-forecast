"""Statistical baseline for Q3 2026, to compare against the driver model.

A driver model is only worth the effort if it beats a simple forecast that
knows nothing about restaurants, prices or costs. This script makes two of
those, using only the quarters reported up to Q2 2026 (the same information
the driver model had):

  1. Seasonal naive: same quarter last year, with revenue grown at the
     trailing four-quarter growth rate.
  2. Holt-Winters exponential smoothing (statsmodels), additive trend and
     multiplicative seasonality for revenue, additive for margin.

Settings are the textbook defaults and were not tuned. Note: this baseline
was written on Oct 30, 2026, after Chipotle reported Q3, so unlike the
driver forecast it was not locked in advance. It only reads data through
Q2 2026, so the actual Q3 numbers can't leak in.

Writes output/q3_2026_baseline.csv.
"""
import warnings
from pathlib import Path

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ROOT = Path(__file__).resolve().parent.parent
CUTOFF = "2026Q2"
TARGET = "2026Q3"

pnl = pd.read_csv(ROOT / "data" / "processed" / "cmg_pnl_quarterly.csv").set_index("quarter")
pnl = pnl.loc[:CUTOFF]
costs = ["food_bev_packaging", "labor", "occupancy", "other_operating"]
revenue = pnl["revenue"] / 1000  # $M
margin = 1 - pnl[costs].sum(axis=1) / pnl["revenue"]

idx = pd.PeriodIndex([f"{q[:4]}Q{q[-1]}" for q in pnl.index], freq="Q")
revenue.index = idx
margin.index = idx
last_year = pd.Period(TARGET, freq="Q") - 4

# 1. seasonal naive
trailing_growth = revenue.iloc[-4:].sum() / revenue.iloc[-8:-4].sum() - 1
naive_rev = revenue[last_year] * (1 + trailing_growth)
naive_rlm = margin[last_year]

# 2. Holt-Winters
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    hw_rev = ExponentialSmoothing(revenue, trend="add", seasonal="mul", seasonal_periods=4).fit()
    hw_rlm = ExponentialSmoothing(margin, trend="add", seasonal="add", seasonal_periods=4).fit()
ets_rev = float(hw_rev.forecast(1).iloc[0])
ets_rlm = float(hw_rlm.forecast(1).iloc[0])

out = pd.DataFrame([
    {"method": "Seasonal naive", "revenue_m": naive_rev, "restaurant_margin": naive_rlm,
     "note": f"Q3 2025 x trailing 4-quarter growth ({trailing_growth:.1%}); margin = Q3 2025"},
    {"method": "Holt-Winters", "revenue_m": ets_rev, "restaurant_margin": ets_rlm,
     "note": "additive trend; multiplicative (revenue) / additive (margin) seasonality; default fit"},
])
path = ROOT / "output" / "q3_2026_baseline.csv"
out.to_csv(path, index=False)
print(out.to_string(index=False, formatters={"revenue_m": "{:,.1f}".format, "restaurant_margin": "{:.2%}".format}))
