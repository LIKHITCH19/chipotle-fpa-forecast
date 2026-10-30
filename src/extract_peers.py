"""Last-twelve-months (LTM) figures for Chipotle and fast-casual peers.

Fiscal calendars differ (CAVA's first quarter is 16 weeks, others end on
odd dates), so LTM is built the standard way from what each company files:
    LTM = last full fiscal year + current year-to-date - prior year-to-date

Restaurant-level costs are rebuilt from each company's own cost lines so the
margin uses one definition: revenue less food, labor, occupancy and other
restaurant operating costs (before D&A, pre-opening and G&A).

Output: data/processed/peers_ltm.csv
"""
import csv
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "sec"

COMPANIES = {
    "CMG": "Chipotle",
    "CAVA": "CAVA",
    "SG": "Sweetgreen",
    "SHAK": "Shake Shack",
}
# Wingstop is left out: it is almost entirely franchised, so it has no
# comparable restaurant-level cost base.

TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "food_paper": ["CostDirectMaterial", "CostOfGoodsSoldDirectMaterials"],
    "labor": ["CostDirectLabor", "LaborAndRelatedExpense", "CostOfGoodsSoldDirectLabor"],
    "occupancy": ["OccupancyNet"],
    "other_operating": ["OtherCostAndExpenseOperating", "OtherCostOfOperatingRevenue"],
    "restaurant_costs_total": ["CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization"],
    "operating_income": ["OperatingIncomeLoss"],
}


def days(f):
    return (date.fromisoformat(f["end"]) - date.fromisoformat(f["start"])).days


def periods(facts):
    """{(start, end): value}, latest filing wins."""
    best = {}
    for f in facts:
        if "start" not in f or not f.get("form", "").startswith("10-"):
            continue
        k = (f["start"], f["end"])
        if k not in best or f["filed"] > best[k][0]:
            best[k] = (f["filed"], f["val"])
    return {k: v[1] for k, v in best.items()}


def ltm(per, as_of=None):
    """Return (ltm_value, ltm_end) using the latest year-to-date period."""
    years = sorted([k for k in per if 350 <= days({"start": k[0], "end": k[1]}) <= 380], key=lambda k: k[1])
    if not years:
        return None, None
    candidates = []
    for fy in years:
        fy_end = date.fromisoformat(fy[1])
        for (s, e), v in per.items():
            if date.fromisoformat(s) - fy_end in (timedelta(days=1), timedelta(days=0)) and e > fy[1]:
                candidates.append((e, s, fy))
    if as_of:
        candidates = [c for c in candidates if c[0] <= as_of]
    if not candidates:
        fy = years[-1] if not as_of else max([y for y in years if y[1] <= as_of], default=None, key=lambda k: k[1])
        return (per[fy], fy[1]) if fy else (None, None)
    e, s, fy = max(candidates)
    ytd_len = (date.fromisoformat(e) - date.fromisoformat(s)).days
    # prior-year YTD: starts at the previous fiscal-year start, similar length
    prev_start = fy[0]
    prev = [(k, v) for k, v in per.items() if k[0] == prev_start and abs(days({"start": k[0], "end": k[1]}) - ytd_len) <= 7]
    if not prev:
        return None, None
    return per[fy] + per[(s, e)] - prev[0][1], e


def value(us, names, as_of=None, must_end=None):
    """LTM for the first tag that has data. With must_end, a tag whose latest
    period stops earlier (the company stopped using it) is ignored."""
    for n in names:
        if n in us and "USD" in us[n]["units"]:
            v, end = ltm(periods(us[n]["units"]["USD"]), as_of)
            if v is not None and (must_end is None or end == must_end):
                return v, end
    return None, None


rows = []
for ticker, name in COMPANIES.items():
    us = json.load(open(RAW / f"companyfacts_{ticker}.json"))["facts"]["us-gaap"]
    row = {"ticker": ticker, "company": name}
    rev, end = value(us, TAGS["revenue"])
    row["ltm_end"] = end
    for key, names in TAGS.items():
        row[key] = value(us, names, must_end=end)[0]
    # revenue twelve months earlier, for growth
    year_ago = (date.fromisoformat(end) - timedelta(days=364)).isoformat()
    prior, prior_end = value(us, TAGS["revenue"], as_of=(date.fromisoformat(year_ago) + timedelta(days=6)).isoformat())
    row["revenue_prior_ltm"] = prior
    row["prior_ltm_end"] = prior_end
    if row["restaurant_costs_total"] is None:
        parts = [row[k] for k in ("food_paper", "labor", "occupancy", "other_operating")]
        row["restaurant_costs_total"] = sum(parts) if None not in parts else None
    rows.append(row)

out = ROOT / "data" / "processed" / "peers_ltm.csv"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for r in rows:
    rl = 1 - r["restaurant_costs_total"] / r["revenue"] if r["restaurant_costs_total"] else None
    g = r["revenue"] / r["revenue_prior_ltm"] - 1 if r["revenue_prior_ltm"] else None
    print(r["ticker"], r["ltm_end"], r["prior_ltm_end"], f"rev {r['revenue']/1e6:,.0f}M",
          f"growth {g:.1%}" if g is not None else "", f"RLM {rl:.1%}" if rl else "",
          {k: (round(r[k] / r['revenue'] * 100, 1) if r[k] else None) for k in ("food_paper", "labor", "occupancy", "other_operating", "operating_income")})
