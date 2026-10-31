"""Score the locked Q3 2026 forecast against what Chipotle reported.

Reads the forecast saved on Oct 15 (output/q3_2026_forecast_locked.csv),
the Q3 actuals pulled from the 10-Q and the Oct 28 earnings release
(data/processed), and the statistical baselines (output/q3_2026_baseline.csv).

Writes
  output/q3_2026_variance.csv   line-by-line forecast vs actual
  output/q3_2026_accuracy.csv   revenue and margin error: driver model vs baselines
"""
import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC, OUT = ROOT / "data" / "processed", ROOT / "output"
Q, PREV_Q, LY_Q = "2026Q3", "2026Q2", "2025Q3"

pnl = pd.read_csv(PROC / "cmg_pnl_quarterly.csv").set_index("quarter")
units = pd.read_csv(PROC / "cmg_units_quarterly.csv").set_index("quarter")
split = pd.read_csv(PROC / "cmg_comps_split.csv").set_index("quarter")
if Q not in pnl.index:
    raise SystemExit(f"No {Q} actuals yet. Run src/fetch_data.py and src/extract_cmg.py first.")

with open(OUT / "q3_2026_forecast_locked.csv") as fh:
    rows = list(csv.DictReader(fh))
fcst = {r["key"]: float(r["value"]) for r in rows}
label = {r["key"]: r["label"] for r in rows}

p = pnl.loc[Q]
rev = p.revenue
actual = {
    "comps": units.loc[Q, "comp_sales_pct"] / 100,
    "tx": split.loc[Q, "transactions_pct"] / 100,
    "check": split.loc[Q, "avg_check_pct"] / 100,
    "opened": units.loc[Q, "opened"],
    "rest_end": units.loc[Q, "restaurants_end"],
    "rev2": rev,
    "food_pct": p.food_bev_packaging / rev,
    "labor_pct": p.labor / rev,
    "occ_pct": p.occupancy / rev,
    "oth_pct": p.other_operating / rev,
    "rlm": 1 - (p.food_bev_packaging + p.labor + p.occupancy + p.other_operating) / rev,
    "ga": p.g_and_a,
    "oi": p.operating_income,
    "opm": p.operating_income / rev,
    "ni": p.net_income,
    "eps": p.net_income / p.diluted_shares * 1000,
}

# percentages and margins are compared in points, everything else in % of forecast
points = {"comps", "tx", "check", "food_pct", "labor_pct", "occ_pct", "oth_pct", "rlm", "opm"}
out = []
for key, f in fcst.items():
    a = float(actual[key])
    row = {"key": key, "line": label[key], "forecast": f, "actual": a, "variance": a - f}
    if key in points:
        row["variance_bps"] = round((a - f) * 10000)
        row["variance_pct"] = ""
    else:
        row["variance_bps"] = ""
        row["variance_pct"] = (a - f) / f
    out.append(row)
var = pd.DataFrame(out)

# revenue gap: more restaurants vs more revenue per restaurant
avg_rest_a = (units.loc[PREV_Q, "restaurants_end"] + units.loc[Q, "restaurants_end"]) / 2
avg_rest_f = (units.loc[PREV_Q, "restaurants_end"] + fcst["rest_end"]) / 2
rpr_f = fcst["rev2"] / avg_rest_f
from_units = (avg_rest_a - avg_rest_f) * rpr_f
from_rpr = rev - fcst["rev2"] - from_units
extra = pd.DataFrame([
    {"key": "rev_from_restaurants", "line": "Revenue gap from restaurant count ($000)", "variance": from_units},
    {"key": "rev_from_sales_per_restaurant", "line": "Revenue gap from sales per restaurant ($000)", "variance": from_rpr},
])
var = pd.concat([var, extra], ignore_index=True)
var.to_csv(OUT / "q3_2026_variance.csv", index=False)

# driver model vs the statistical baselines
acc = [{"method": "Driver model (locked Oct 15)", "revenue_m": fcst["rev2"] / 1000, "restaurant_margin": fcst["rlm"]}]
base = OUT / "q3_2026_baseline.csv"
if base.exists():
    acc += pd.read_csv(base)[["method", "revenue_m", "restaurant_margin"]].to_dict("records")
acc = pd.DataFrame(acc)
acc["revenue_error_pct"] = acc.revenue_m / (rev / 1000) - 1
acc["margin_error_bps"] = ((acc.restaurant_margin - actual["rlm"]) * 10000).round()
acc.loc[len(acc)] = {"method": "Actual", "revenue_m": rev / 1000, "restaurant_margin": actual["rlm"],
                     "revenue_error_pct": 0.0, "margin_error_bps": 0}
acc.to_csv(OUT / "q3_2026_accuracy.csv", index=False)

pd.set_option("display.width", 140)
print(var[["line", "forecast", "actual", "variance_bps", "variance_pct"]].to_string(index=False))
print(f"\nRevenue gap ${(rev - fcst['rev2']) / 1000:,.1f}M: restaurants ${from_units / 1000:,.1f}M, "
      f"sales per restaurant ${from_rpr / 1000:,.1f}M")
print()
print(acc.to_string(index=False))
