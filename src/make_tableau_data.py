"""Long-format CSVs for the Tableau dashboard (output/tableau/).

These are the data sources for tableau/chipotle_fpa_dashboard.twbx.
"""
import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC, OUT = ROOT / "data" / "processed", ROOT / "output"
TAB = OUT / "tableau"
TAB.mkdir(parents=True, exist_ok=True)

pnl = pd.read_csv(PROC / "cmg_pnl_quarterly.csv").set_index("quarter")
units = pd.read_csv(PROC / "cmg_units_quarterly.csv").set_index("quarter")
split = pd.read_csv(PROC / "cmg_comps_split.csv").set_index("quarter")
mq = pd.read_csv(OUT / "model_quarterly.csv")
peers = pd.read_csv(PROC / "peers_ltm.csv")
levers = pd.read_csv(OUT / "levers.csv", nrows=12)
lock = {r["key"]: float(r["value"]) for r in csv.DictReader(open(OUT / "q3_2026_forecast_locked.csv"))}


def label(q):
    return f"{q[:4]} Q{q[-1]}"


def margin(q):
    r = pnl.loc[q]
    return 1 - (r.food_bev_packaging + r.labor + r.occupancy + r.other_operating) / r.revenue


# 1. quarterly series: actuals plus each forecast scenario (joined at the last actual so the lines connect)
rows = []
for q in pnl.index:
    rows.append({"quarter": label(q), "series": "Actual", "restaurant_margin": margin(q),
                 "revenue_m": pnl.at[q, "revenue"] / 1000, "comparable_sales": units.at[q, "comp_sales_pct"] / 100,
                 "diluted_eps": pnl.at[q, "net_income"] * 1000 / pnl.at[q, "diluted_shares"]})
for name in ("Base", "Upside", "Downside"):
    rows.append({**rows[len(pnl) - 1], "series": f"{name} forecast"})
    for _, r in mq[(mq.scenario == name) & (mq.type == "forecast")].iterrows():
        rows.append({"quarter": label(r.quarter), "series": f"{name} forecast", "restaurant_margin": r.rlm,
                     "revenue_m": r.rev2 / 1000, "comparable_sales": r.comps, "diluted_eps": r.eps})
pd.DataFrame(rows).to_csv(TAB / "quarterly.csv", index=False)

# 2. margin bridge Q2 2025 -> Q2 2026, cost lines only (the chart title carries the start and end)
q0, q1 = "2025Q2", "2026Q2"
steps = []
for lab, col in [("Food & packaging", "food_bev_packaging"), ("Labor", "labor"), ("Occupancy", "occupancy"),
                 ("Other operating", "other_operating")]:
    d = -(pnl.at[q1, col] / pnl.at[q1, "revenue"] - pnl.at[q0, col] / pnl.at[q0, "revenue"]) * 1e4
    steps.append((lab, d))
pd.DataFrame(steps, columns=["cost_line", "margin_change_bps"]).to_csv(TAB / "bridge.csv", index=False)

# 3. levers (Base case)
lv = levers[levers.scenario == "Base"][["lever", "fy2027_margin_change_bps"]]
lv.columns = ["lever", "margin_change_bps"]
lv.to_csv(TAB / "levers.csv", index=False)

# 4. traffic vs check, long format
tv = []
for q in split.index:
    tv.append({"quarter": label(q), "component": "Transactions", "growth": split.at[q, "transactions_pct"] / 100})
    tv.append({"quarter": label(q), "component": "Average check", "growth": split.at[q, "avg_check_pct"] / 100})
pd.DataFrame(tv).to_csv(TAB / "traffic_check.csv", index=False)

# 5. peers, long format
pr = []
for _, r in peers.iterrows():
    pr.append({"company": r.company, "metric": "Revenue growth (LTM)", "value": r.revenue / r.revenue_prior_ltm - 1})
    if pd.notna(r.restaurant_costs_total):
        pr.append({"company": r.company, "metric": "Restaurant-level margin (LTM)",
                   "value": 1 - r.restaurant_costs_total / r.revenue})
pd.DataFrame(pr).to_csv(TAB / "peers.csv", index=False)

# 6. Q3 scorecard (display strings, so the table needs no number formatting)
shown = [("1 Comparable sales", f"{lock['comps']:+.1%}"), ("2 Revenue", f"${lock['rev2'] / 1000:,.0f}M"),
         ("3 Restaurant-level margin", f"{lock['rlm']:.1%}"), ("4 Diluted EPS", f"${lock['eps']:.2f}")]
actual = {}
var_file = OUT / "q3_2026_variance.csv"
if var_file.exists():
    v = pd.read_csv(var_file).set_index("key")["actual"]
    actual = {"1": f"{v['comps']:+.1%}", "2": f"${v['rev2'] / 1000:,.0f}M", "3": f"{v['rlm']:.1%}", "4": f"${v['eps']:.2f}"}
sc = []
for line, value in shown:
    sc.append({"line": line[2:], "order": line[0], "column": "My forecast", "shown": value})
    sc.append({"line": line[2:], "order": line[0], "column": "Reported", "shown": actual.get(line[0], "Oct 28")})
pd.DataFrame(sc).to_csv(TAB / "q3_scorecard.csv", index=False)
print("wrote", sorted(p.name for p in TAB.glob("*.csv")))
