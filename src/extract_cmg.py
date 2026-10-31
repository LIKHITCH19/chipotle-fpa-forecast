"""Turn Chipotle's raw SEC downloads into tidy quarterly tables.

Outputs (data/processed/):
  cmg_pnl_quarterly.csv     income statement by quarter, $ thousands, from the
                            XBRL facts filed with each 10-Q/10-K. Q4 is not
                            filed on its own, so it is full year minus Q1-Q3.
  cmg_pnl_press.csv         the same lines read from each earnings release,
                            used only to check the XBRL numbers.
  cmg_units_quarterly.csv   openings, closures, restaurants at quarter end,
                            average restaurant sales and comparable sales.
  cmg_comps_split.csv       comparable sales split into transactions and
                            average check (disclosed from Q4 2023 onward).
  cmg_reported_margin.csv   restaurant-level margin as Chipotle states it in
                            each release (used to check our own calculation).
"""
import csv
import glob
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sec_tables import tables, _text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "sec"
OUT = ROOT / "data" / "processed"
FIRST, LAST = (2021, 1), (2026, 3)

# P&L line -> XBRL tags to try in order, and the sign to apply
LINES = {
    "revenue": (["Revenues"], 1),
    "food_bev_packaging": (["CostDirectMaterial"], 1),
    "labor": (["CostDirectLabor"], 1),
    "occupancy": (["OccupancyNet"], 1),
    "other_operating": (["OtherCostAndExpenseOperating"], 1),
    "g_and_a": (["GeneralAndAdministrativeExpense"], 1),
    "d_and_a": (["DepreciationDepletionAndAmortization"], 1),
    "pre_opening": (["PreOpeningCosts"], 1),
    "impairment_closures": (["GainLossOnSalesOfAssetsAndAssetImpairmentCharges"], -1),
    "total_operating_expenses": (["CostsAndExpenses"], 1),
    "operating_income": (["OperatingIncomeLoss"], 1),
    "interest_other_income": (["OtherNonoperatingIncomeExpense"], 1),
    "pretax_income": ([
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ], 1),
    "net_income": (["NetIncomeLoss"], 1),
    "diluted_shares": (["WeightedAverageNumberOfDilutedSharesOutstanding"], 1),
}
SPLIT_DATE = date(2024, 6, 26)  # 50-for-1 stock split
SPLIT_RATIO = 50

# Press release label -> line name (first match wins, label compared lowercase)
PRESS_LABELS = [
    ("total revenue", "revenue"),
    ("food, beverage and packaging", "food_bev_packaging"),
    ("labor", "labor"),
    ("occupancy", "occupancy"),
    ("other operating costs", "other_operating"),
    ("general and administrative expenses", "g_and_a"),
    ("depreciation and amortization", "d_and_a"),
    ("pre-opening costs", "pre_opening"),
    ("impairment", "impairment_closures"),
    ("loss on disposal", "impairment_closures"),
    ("total operating expenses", "total_operating_expenses"),
    ("income from operations", "operating_income"),
    ("interest and other income", "interest_other_income"),
    ("income before income taxes", "pretax_income"),
    ("provision for income taxes", "income_tax"),
    ("net income", "net_income"),
]


def quarters():
    y, q = FIRST
    while (y, q) <= LAST:
        yield y, q
        y, q = (y, q + 1) if q < 4 else (y + 1, 1)


def qlabel(y, q):
    return f"{y}Q{q}"


def quarter_end(y, q):
    return date(y, 3 * q, 31 if q in (1, 4) else 30)


# ---------- XBRL ----------
def latest_by_period(facts):
    """{(start, end): value} keeping the most recently filed value."""
    best = {}
    for f in facts:
        if "start" not in f or f.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
            continue
        key = (f["start"], f["end"])
        if key not in best or f["filed"] > best[key][0]:
            best[key] = (f["filed"], f["val"])
    return {k: v[1] for k, v in best.items()}


def xbrl_quarterly():
    facts = json.load(open(RAW / "companyfacts_CMG.json"))["facts"]["us-gaap"]
    table = {qlabel(y, q): {"quarter": qlabel(y, q), "quarter_end": quarter_end(y, q).isoformat()}
             for y, q in quarters()}
    for line, (tags, sign) in LINES.items():
        values = {}
        for tag in tags:
            if tag in facts:
                unit = "shares" if line == "diluted_shares" else "USD"
                for k, v in latest_by_period(facts[tag]["units"][unit]).items():
                    values.setdefault(k, v)
        by_quarter, by_year = {}, {}
        for (start, end), v in values.items():
            days = (date.fromisoformat(end) - date.fromisoformat(start)).days
            e = date.fromisoformat(end)
            if 80 <= days <= 100:
                by_quarter[(e.year, (e.month - 1) // 3 + 1)] = v
            elif 350 <= days <= 380:
                by_year[e.year] = v
        for y, q in quarters():
            v = by_quarter.get((y, q))
            derived = False
            if v is None and q == 4 and y in by_year and line != "diluted_shares":
                parts = [by_quarter.get((y, i)) for i in (1, 2, 3)]
                if None not in parts:
                    v, derived = by_year[y] - sum(parts), True
            if v is not None and line == "diluted_shares" and quarter_end(y, q) < SPLIT_DATE and v < 1e8:
                v *= SPLIT_RATIO  # older filings report pre-split share counts
            row = table[qlabel(y, q)]
            row[line] = None if v is None else sign * v / (1 if line == "diluted_shares" else 1000)
            if derived:
                row["q4_derived_from_fy"] = "yes"
    rows = list(table.values())
    for r in rows:
        r.setdefault("q4_derived_from_fy", "")
        # The tagged tax line is inconsistent across filings; pre-tax income and
        # net income both tie to the releases, so tax is taken as the difference.
        r["income_tax"] = r["pretax_income"] - r["net_income"]
    return rows


def fill_q4_shares(pnl, press):
    """Q4 share counts only appear in the releases (in thousands)."""
    by_q = {r["quarter"]: r for r in press}
    for r in pnl:
        if r.get("diluted_shares") is None and r["quarter"] in by_q:
            shares = by_q[r["quarter"]].get("diluted_shares_000")
            if shares:
                shares *= 1000
                if date.fromisoformat(r["quarter_end"]) < SPLIT_DATE and shares < 1e8:
                    shares *= SPLIT_RATIO
                r["diluted_shares"] = shares
                r["q4_derived_from_fy"] += " (shares from release)"
    for r in pnl:
        r["diluted_eps"] = round(r["net_income"] * 1000 / r["diluted_shares"], 4)
    return pnl


# ---------- earnings releases ----------
def release_quarter(filing_date):
    d = date.fromisoformat(filing_date)
    if d.month <= 3:
        return d.year - 1, 4
    return d.year, (d.month - 1) // 3


def press_releases():
    for path in sorted(glob.glob(str(RAW / "filings" / "CMG" / "8-K_*"))):
        filing_date = Path(path).name[4:14]
        yield path, filing_date, release_quarter(filing_date)


def press_pnl():
    rows = []
    for path, filed, (y, q) in press_releases():
        raw = open(path, errors="ignore").read()
        row = {"quarter": qlabel(y, q), "source_file": Path(path).name}
        for text, trs in tables(raw):
            if "Three months ended" in text and "Total revenue" in text and "Labor" in text:
                diluted_seen = 0
                for label, nums in trs:
                    low = label.lower()
                    if low == "diluted" and nums:
                        # first "Diluted" row is EPS, the second is share count (thousands)
                        diluted_seen += 1
                        row["diluted_eps" if diluted_seen == 1 else "diluted_shares_000"] = nums[0]
                        continue
                    for key, line in PRESS_LABELS:
                        if low.startswith(key) and line not in row and nums:
                            row[line] = nums[0]
                            break
                break
        rows.append(row)
    return rows


UNIT_LABELS = [
    ("average restaurant sales, excluding", None),
    ("average restaurant sales", "avg_restaurant_sales"),
    ("comparable restaurant sales", "comp_sales_pct"),
    ("relocations", "relocations"),
    ("closures", "closures"),
    ("opened", "opened"),
    ("at end of period", "restaurants_end"),
    ("total", "restaurants_end"),
]


def unit_tables():
    """Each release has 5 quarters of unit data, newest first. Newer releases
    win when two of them cover the same quarter."""
    data = {}
    for path, filed, (y, q) in press_releases():
        raw = open(path, errors="ignore").read()
        for text, trs in tables(raw):
            if not any(l.lower().startswith("average restaurant sales") and n for l, n in trs):
                continue
            cols = {}
            for label, nums in trs:
                low = label.lower()
                if not nums:
                    continue
                for key, field in UNIT_LABELS:
                    if key in low:
                        if field:
                            if field == "closures" and field in cols:
                                cols[field] = [a + b for a, b in zip(cols[field], nums)]
                            elif field not in cols:
                                cols[field] = nums
                        break
            yy, qq = y, q
            for i in range(5):
                rec = {f: (v[i] if i < len(v) else None) for f, v in cols.items()}
                key = qlabel(yy, qq)
                if key not in data or filed > data[key]["source_release"]:
                    rec.update(quarter=key, source_release=filed)
                    data[key] = rec
                yy, qq = (yy, qq - 1) if qq > 1 else (yy - 1, 4)
            break  # first table only = company-owned restaurants
    return [data[k] for k in sorted(data)]


def comps_split():
    rows = []
    for path, filed, (y, q) in press_releases():
        t = _text(open(path, errors="ignore").read())
        t = re.sub(r"(\d) \.(\d)", r"\1.\2", t)
        t = re.sub(r"(\d) %", r"\1%", t)
        tx = re.search(r"(higher|lower|increase in|decrease in) transactions of (\d+\.\d)%", t)
        tx2 = re.search(r"(\d+\.\d)% (increase|decrease) in transactions", t)
        ck = re.search(r"(\d+\.\d)% (increase|decrease) in average check", t)
        ck2 = re.search(r"(increase|decrease) in average check of (\d+\.\d)%", t)
        if not (tx or tx2) or not (ck or ck2):
            continue
        if tx:
            trans = float(tx.group(2)) * (-1 if tx.group(1).startswith(("lower", "decrease")) else 1)
        else:
            trans = float(tx2.group(1)) * (-1 if tx2.group(2) == "decrease" else 1)
        if ck:
            check = float(ck.group(1)) * (-1 if ck.group(2) == "decrease" else 1)
        else:
            check = float(ck2.group(2)) * (-1 if ck2.group(1) == "decrease" else 1)
        rows.append({"quarter": qlabel(y, q), "transactions_pct": trans,
                     "avg_check_pct": check, "source_release": filed})
    return rows


def reported_margin():
    rows = []
    for path, filed, (y, q) in press_releases():
        t = _text(open(path, errors="ignore").read())
        t = re.sub(r"(\d) \.(\d)", r"\1.\2", t)
        t = re.sub(r"(\d) (\d)", r"\1\2", t)
        m = re.search(r"Restaurant level operating margin (?:\d )?(?:was|of) (\d+\.\d) ?%", t)
        if m:
            rows.append({"quarter": qlabel(y, q), "restaurant_margin_reported_pct": float(m.group(1)),
                         "source_release": filed})
    return rows


def write(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(OUT / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


if __name__ == "__main__":
    press = press_pnl()
    write("cmg_pnl_quarterly.csv", fill_q4_shares(xbrl_quarterly(), press))
    write("cmg_pnl_press.csv", press)
    write("cmg_units_quarterly.csv", unit_tables())
    write("cmg_comps_split.csv", comps_split())
    write("cmg_reported_margin.csv", reported_margin())
