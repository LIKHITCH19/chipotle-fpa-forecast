"""Checks that the processed tables tie back to what Chipotle reported.

Writes data/processed/data_checks.csv and exits with an error if any fail.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
TOL_K = 5  # $ thousands; filings round each line independently

pnl = pd.read_csv(PROC / "cmg_pnl_quarterly.csv").set_index("quarter")
press = pd.read_csv(PROC / "cmg_pnl_press.csv").set_index("quarter")
units = pd.read_csv(PROC / "cmg_units_quarterly.csv").set_index("quarter")
split = pd.read_csv(PROC / "cmg_comps_split.csv").set_index("quarter")
results = []


def check(name, quarter, ok, detail=""):
    results.append({"check": name, "quarter": quarter, "result": "PASS" if ok else "FAIL",
                    "detail": detail})


# 1. XBRL lines vs the earnings release
for q in pnl.index:
    if q not in press.index:
        check("xbrl_vs_release", q, False, "no release")
        continue
    for col in [c for c in press.columns if c in pnl.columns]:
        a, b = pnl.at[q, col], press.at[q, col]
        if pd.isna(b):
            continue
        if col == "income_tax":
            b = abs(b)  # older releases show the provision in brackets
        if col == "diluted_eps":
            if q < "2024Q2":
                b = b / 50  # releases before the June 2024 split show pre-split EPS
            check("xbrl_vs_release", q, abs(a - b) <= 0.006, f"{col}: {a:.4f} vs release {b:.4f}")
            continue
        check("xbrl_vs_release", q, abs(a - b) <= TOL_K, f"{col}: filed {a:,.0f} vs release {b:,.0f}")

# 2. costs add up, and revenue less costs is operating income
cost_cols = ["food_bev_packaging", "labor", "occupancy", "other_operating", "g_and_a",
             "d_and_a", "pre_opening", "impairment_closures"]
for q, r in pnl.iterrows():
    total = r[cost_cols].sum()
    check("costs_sum_to_total", q, abs(total - r.total_operating_expenses) <= TOL_K,
          f"{total:,.0f} vs {r.total_operating_expenses:,.0f}")
    oi = r.revenue - r.total_operating_expenses
    check("revenue_less_costs", q, abs(oi - r.operating_income) <= TOL_K,
          f"{oi:,.0f} vs {r.operating_income:,.0f}")

# 3. restaurant count roll-forward
qs = list(units.index)
for prev, cur in zip(qs, qs[1:]):
    r = units.loc[cur]
    calc = units.at[prev, "restaurants_end"] + r.opened + r.closures + r.relocations
    check("restaurant_rollforward", cur, calc == r.restaurants_end,
          f"{calc:,.0f} vs {r.restaurants_end:,.0f}")

# 4. comps = transactions + check (each is rounded to 0.1)
for q, r in split.iterrows():
    comp = units.at[q, "comp_sales_pct"]
    s = r.transactions_pct + r.avg_check_pct
    check("comps_equal_tx_plus_check", q, abs(s - comp) <= 0.15, f"{s:.1f} vs {comp:.1f}")

# 5. our restaurant-level margin vs the margin Chipotle reports
reported = pd.read_csv(PROC / "cmg_reported_margin.csv").set_index("quarter")["restaurant_margin_reported_pct"]
for q, r in pnl.iterrows():
    if q not in reported.index:
        continue
    ours = 100 * (1 - (r.food_bev_packaging + r.labor + r.occupancy + r.other_operating) / r.revenue)
    check("restaurant_margin_vs_reported", q, abs(ours - reported[q]) <= 0.05,
          f"{ours:.2f}% vs reported {reported[q]:.1f}%")

out = pd.DataFrame(results)
out.to_csv(PROC / "data_checks.csv", index=False)
summary = out.groupby("check").result.value_counts().unstack(fill_value=0)
print(summary.to_string())
fails = out[out.result == "FAIL"]
if len(fails):
    print(fails.to_string(index=False))
    sys.exit(1)
print(f"All {len(out)} checks pass.")
