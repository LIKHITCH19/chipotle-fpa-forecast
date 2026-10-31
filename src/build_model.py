"""Build model/chipotle_fpa_model.xlsx from the processed data.

The workbook is formula-driven: historical figures are typed in (blue) from
the SEC filings, and everything in the forecast is calculated from the
Assumptions tab. Run src/run_model.py rather than this file directly; it
builds the workbook, recalculates it in LibreOffice and saves the scenario
snapshot and the locked Q3 forecast.
"""
import re
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = ROOT / "model" / "chipotle_fpa_model.xlsx"

FONT = "Arial"
BLUE, GREEN, BLACK, GREY = "0000FF", "008000", "000000", "808080"
NUM = '#,##0;(#,##0);"-"'
NUM1 = '#,##0.0;(#,##0.0);"-"'
PCT = '0.0%;(0.0%);"-"'
PCT2 = '0.00%;(0.00%);"-"'
BPS = '#,##0" bps";(#,##0" bps");"0 bps"'
EPS = '$0.00;($0.00);"-"'
FILL_FCST = PatternFill("solid", fgColor="EEF3FB")
FILL_HEAD = PatternFill("solid", fgColor="1F3A5F")
FILL_SECTION = PatternFill("solid", fgColor="E7E6E6")
FILL_KEY = PatternFill("solid", fgColor="FFFF00")


# ---------------------------------------------------------------- helpers
def font(color=BLACK, bold=False, italic=False, size=10):
    return Font(name=FONT, color=color, bold=bold, italic=italic, size=size)


def put(ws, ref, value, color=BLACK, fmt=None, bold=False, italic=False, fill=None, align=None):
    c = ws[ref]
    c.value = value
    c.font = font(color, bold, italic)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if align:
        c.alignment = Alignment(horizontal=align)
    return c


def title(ws, text, sub=None):
    put(ws, "A1", text, bold=True).font = font(bold=True, size=14)
    if sub:
        put(ws, "A2", sub, color=GREY, italic=True)


def header_row(ws, row, labels, start_col):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=start_col + i, value=lab)
        c.font = Font(name=FONT, bold=True, color="FFFFFF")
        c.fill = FILL_HEAD
        c.alignment = Alignment(horizontal="center")


def section(ws, row, text, last_col):
    for col in range(1, last_col + 1):
        ws.cell(row=row, column=col).fill = FILL_SECTION
    put(ws, f"A{row}", text, bold=True, fill=FILL_SECTION)


def note(ws, ref, text):
    ws[ref].comment = Comment(text, "Model")


# ---------------------------------------------------------------- data
pnl = pd.read_csv(PROC / "cmg_pnl_quarterly.csv").set_index("quarter")
units = pd.read_csv(PROC / "cmg_units_quarterly.csv").set_index("quarter")
split = pd.read_csv(PROC / "cmg_comps_split.csv").set_index("quarter")
peers = pd.read_csv(PROC / "peers_ltm.csv")

HIST_Q = list(pnl.index)                      # 2021Q1 .. latest reported quarter
assert HIST_Q[0] == "2021Q1" and HIST_Q[-1] >= "2026Q2", HIST_Q
# The forecast runs to Q4 2027 from whatever quarter comes after the last one
# reported. Oct 15 budget: Q3 2026 to Q4 2027. Oct 30 reforecast: Q4 2026 on.
FCST_Q = [q for q in ["2026Q3", "2026Q4", "2027Q1", "2027Q2", "2027Q3", "2027Q4"] if q not in HIST_Q]
MODEL_Q = HIST_Q[HIST_Q.index("2025Q1"):] + FCST_Q   # 2025Q1 .. 2027Q4 (12)
LAST_A, FIRST_F = HIST_Q[-1], FCST_Q[0]


def qname(q):
    return f"Q{q[-1]} {q[:4]}"


# Hist layout: C = Q4 2020 (opening restaurant count only), D.. = quarters
H_FIRST = 4
HCOL = {q: L(H_FIRST + i) for i, q in enumerate(HIST_Q)}   # D..Y
H_YEARS = [2021, 2022, 2023, 2024, 2025]
HYCOL = {y: L(H_FIRST + len(HIST_Q) + 1 + i) for i, y in enumerate(H_YEARS)}  # AA..AE

# Model layout: C..N quarters, P..R full years
MCOL = {q: L(3 + i) for i, q in enumerate(MODEL_Q)}
M_YEARS = {"FY2025A": "P", "FY2026E": "Q", "FY2027E": "R"}
M_YEAR_Q = {"FY2025A": MODEL_Q[0:4], "FY2026E": MODEL_Q[4:8], "FY2027E": MODEL_Q[8:12]}

# Assumptions layout: forecast quarters from column E
ACOL = {q: L(5 + i) for i, q in enumerate(FCST_Q)}
A27, A27_END = ACOL["2027Q1"], ACOL["2027Q4"]   # 2027 columns on Assumptions
A_WHY = L(5 + len(FCST_Q) + 1)                   # the "Why this number" column

wb = Workbook()

# ====================================================================== Cover
cv = wb.active
cv.title = "Cover"
title(cv, "Chipotle Mexican Grill: 2027 budget and Q3 2026 forecast model",
      "Independent analysis of public SEC filings. Not affiliated with Chipotle; not investment advice.")
lines = [
    ("What this model answers", True),
    ("How much restaurant-level margin Chipotle can recover in 2027, and which lever (traffic, price, food cost, labor) matters most.", False),
    ("It also holds a Q3 2026 forecast, made on Oct 15 before Chipotle reported (Oct 28, 2026), scored against the actual results on Q3_Forecast.", False),
    ("", False),
    ("How to use it", True),
    ("1. Pick a scenario on the Assumptions tab (cell C4: 1 = Base, 2 = Upside, 3 = Downside). Every tab updates.", False),
    ("2. Change any blue number on Assumptions to test your own view. Yellow cells are the key levers.", False),
    ("3. The Checks tab must say ALL CHECKS PASS. If it does not, something upstream is broken.", False),
    ("", False),
    ("Tabs", True),
    ("Assumptions - scenario selector and every forecast input, with the reason for each number", False),
    (f"Model - quarterly drivers, restaurant P&L and EPS: actuals Q1 2025 to {qname(LAST_A)}, forecast {qname(FIRST_F)} to Q4 2027", False),
    (f"Hist - {len(HIST_Q)} quarters of reported results (Q1 2021 to {qname(LAST_A)}) as filed, plus derived ratios", False),
    ("Q3_Forecast - the locked Q3 2026 forecast, management's commentary, and space for the actuals and variance", False),
    ("Margin_Bridge - what moved restaurant-level margin, cost line by cost line", False),
    ("Sensitivity - 2027 margin under different traffic, price, food and wage assumptions", False),
    ("Scenarios - Base, Upside and Downside side by side", False),
    ("Peers - Chipotle vs CAVA, Sweetgreen and Shake Shack on the same margin definition", False),
    ("Checks - ties to the filings and internal consistency tests", False),
    ("", False),
    ("Colour code", True),
    ("Blue text = typed-in input or reported figure.  Black = formula.  Green = link to another tab.  Yellow fill = key lever.", False),
    ("Shaded columns on Model = forecast periods.  $ figures are in thousands unless a label says otherwise.", False),
    ("", False),
    ("Sources", True),
    (f"SEC EDGAR: Chipotle 10-Q/10-K XBRL facts and quarterly earnings releases (8-K exhibit 99.1), Q1 2021 to {qname(LAST_A)}.", False),
    ("SEC EDGAR: CAVA, Sweetgreen and Shake Shack XBRL facts for the peer comparison.", False),
    ("U.S. Bureau of Labor Statistics: average hourly earnings in food services (CES7072200003), ground beef price (APU0000703112), CPI food away from home (CUSR0000SEFV).", False),
    ("Chipotle Q2 2026 earnings call (Jul 29, 2026) for management's Q3 commentary; Q3 2026 call (Oct 28, 2026) for the Q4 2026 and 2027 reforecast.", False),
]
r = 4
for text, bold in lines:
    put(cv, f"A{r}", text, bold=bold)
    r += 1
cv.column_dimensions["A"].width = 130

# ================================================================= Assumptions
a = wb.create_sheet("Assumptions")
title(a, "Assumptions", f"Blue = input. Change the scenario in C4. Forecast quarters run across columns E to {ACOL[FCST_Q[-1]]}.")
put(a, "A4", "Scenario in use (1 Base, 2 Upside, 3 Downside)", bold=True)
put(a, "C4", 1, color=BLUE, bold=True, fill=FILL_KEY, align="center")
put(a, "D4", '=INDEX({"Base","Upside","Downside"},C4)', bold=True)
dv = DataValidation(type="list", formula1='"1,2,3"', allow_blank=False)
a.add_data_validation(dv)
dv.add("C4")
note(a, "C4", "1 = Base, 2 = Upside, 3 = Downside. Every forecast cell reads the 'In use' rows below.")

header_row(a, 6, ["Driver", "", "Unit", ""] + [qname(q) for q in FCST_Q] + ["", "Why this number"], 1)

# Reforecast of Oct 30, 2026 (after Q3 results). The Oct 15 budget's inputs
# are in the git history and in output/budget_oct15/.
scen = {
    "Transactions growth, y/y": dict(
        unit="%", rows={
            "Base": [0.000, 0.015, 0.015, 0.015, 0.015],
            "Upside": [0.005, 0.025, 0.025, 0.025, 0.025],
            "Downside": [-0.010, 0.000, 0.000, 0.005, 0.005]},
        why="Q3 transactions were +0.8%, the third positive quarter. Q4: management guided comps of about +2% with "
            "price near 3% and said October softened, so transactions are taken as flat. 2027 assumes +1.5%, a slow "
            "recovery; management called the exit rate 3-4% comps but gave no 2027 guide."),
    "Average check growth, y/y": dict(
        unit="%", rows={
            "Base": [0.020, 0.015, 0.015, 0.015, 0.015],
            "Upside": [0.023, 0.020, 0.020, 0.020, 0.020],
            "Downside": [0.018, 0.010, 0.010, 0.010, 0.010]},
        why="Q3: price 2.7% but check only +1.3%, so promotions and mix took ~1.4 pts. Q4: price ~3% (Oct 28 call) "
            "less ~1 pt of mix. 2027: management said pricing near 2% is 'just not looking like' it will happen, so "
            "check growth is set at 1.5%."),
    "Food cost inflation per transaction": dict(
        unit="%", rows={
            "Base": [0.030, 0.025, 0.020, 0.020, 0.020],
            "Upside": [0.025, 0.015, 0.010, 0.010, 0.010],
            "Downside": [0.035, 0.035, 0.030, 0.030, 0.030]},
        why="Q4: management put underlying cost of sales inflation at ~3% and food at ~30.5% of sales. 2027: "
            "'low to mid-single-digit' inflation; beef is still the main pressure (BLS ground beef +7.4% y/y, Sep 2026)."),
    "Restaurant wage inflation": dict(
        unit="%", rows={
            "Base": [0.035, 0.030, 0.030, 0.030, 0.030],
            "Upside": [0.025, 0.025, 0.025, 0.025, 0.025],
            "Downside": [0.045, 0.045, 0.045, 0.045, 0.045]},
        why="Q3 labor came in at 25.7% with extra hours for promotions. Q4 is set so labor lands near management's "
            "'around 26%'. BLS food-service hourly earnings are up 4.3% y/y (Aug 2026), hence the Downside."),
    "Other operating cost growth per restaurant": dict(
        unit="%", rows={
            "Base": [0.060, 0.035, 0.035, 0.035, 0.035],
            "Upside": [0.050, 0.025, 0.025, 0.025, 0.025],
            "Downside": [0.070, 0.050, 0.050, 0.050, 0.050]},
        why="Q3 other operating was 16.0% (marketing, delivery mix, utilities, maintenance). Q4 guide ~16% with "
            "marketing in the high-3% range. Management sees ~3% marketing as the right level for 2027, so growth slows."),
}
INUSE = {}   # driver -> row number of the 'In use' row
r = 7
for name, spec in scen.items():
    put(a, f"A{r}", name, bold=True)
    put(a, f"{A_WHY}{r}", spec["why"], italic=True)
    a[f"{A_WHY}{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    a.merge_cells(f"{A_WHY}{r}:{A_WHY}{r + 3}")
    start = r
    for k, (sname, vals) in enumerate(spec["rows"].items()):
        rr = r + k
        put(a, f"B{rr}", sname)
        put(a, f"C{rr}", spec["unit"], color=GREY)
        for q, v in zip(FCST_Q, vals):
            put(a, f"{ACOL[q]}{rr}", v, color=BLUE, fmt=PCT)
    rr = r + 3
    put(a, f"B{rr}", "In use", bold=True)
    for q in FCST_Q:
        c = ACOL[q]
        put(a, f"{c}{rr}", f"=CHOOSE($C$4,{c}{start},{c}{start + 1},{c}{start + 2})", fmt=PCT, bold=True)
    for q in FCST_Q:
        a[f"{ACOL[q]}{start}"].fill = FILL_KEY
    INUSE[name] = rr
    r += 5

put(a, f"A{r}", "Same in every scenario", bold=True)
r += 1
common = [
    ("Restaurant openings (company-owned)", "#", [117, 60, 70, 90, 130], NUM,
     "2026: management expects ~350 company-owned openings; 233 opened in Q1-Q3, leaving ~117 for Q4. 2027: "
     "340-360 in the U.S. and Canada (Oct 28), taken as 350, back-end loaded like 2026."),
    ("Closures and relocations (net)", "#", [-4] * 5, NUM, "Average of the last eight quarters (about -4 per quarter)."),
    ("Non-comp revenue effect", "%", [-0.013] * 5, PCT,
     "Revenue per average restaurant grows ~1.3 pts slower than comps because new restaurants open below the "
     "system average (Hist: about -1.3 pts on average over the last eight quarters; -1.5 in Q3 2026)."),
    ("Occupancy cost growth per restaurant", "%", [0.04] * 5, PCT,
     "Rent escalators plus newer Chipotlane sites. Backed out from the filings: 4.0% in Q2 2026, 3.9% in Q3 2026."),
    ("Labor: share of hours that is fixed", "x", [0.5] * 5, '0.00',
     "Half of labor hours don't move with traffic (minimum crew per shift). Unchanged from the Oct 15 budget, "
     "which got Q3 labor within 13 bps."),
    ("Other operating: share that is fixed", "x", [0.4] * 5, '0.00',
     "Utilities, repairs and part of marketing are fixed; delivery fees and card fees move with sales."),
    ("G&A ($000); blank = same quarter last year x (1 + G&A growth)", "$000", [191000, 193000, 193000, 193000, 193000], NUM,
     "Q4: management guided ~$189M non-GAAP; GAAP adds ~$1.5M of retention stock awards. 2027: the H2 2026 "
     "non-GAAP run rate (~$186M a quarter) plus ~4% for wages and headcount."),
    ("G&A growth for blank quarters", "%", [0.04] * 5, PCT, "Only used if a G&A cell above is left blank."),
    ("Depreciation and amortization, % of revenue", "%", [0.031] * 5, PCT, "3.0-3.1% for the last four quarters."),
    ("Pre-opening cost per opening ($000)", "$000", [170] * 5, NUM, "About $164K per opening in Q2 2026 and $180K in Q3."),
    ("Impairment, closures and disposals ($000)", "$000", [12000] * 5, NUM, "$13-14M a quarter in Q2 and Q3 2026."),
    ("Interest and other income ($000)", "$000", [5000, 4500, 4500, 4500, 4500], NUM,
     "Falling as cash and investments fund buybacks ($5.2M in Q3 2026, $19.8M a year earlier)."),
    ("Effective tax rate", "%", [0.25] * 5, PCT, "Management guides an underlying 24-26% for 2026 (Q3 was 25.6%)."),
    ("Diluted share count change, q/q", "%", [-0.008] * 5, PCT,
     "Buybacks slowed: $110M in Q3 2026, and the diluted count fell 0.9% from Q2. Assumed -0.8% a quarter."),
]
COMMON = {}
for name, unit, vals, fmt, why in common:
    put(a, f"A{r}", name)
    put(a, f"C{r}", unit, color=GREY)
    for q, v in zip(FCST_Q, vals):
        if v is not None:
            put(a, f"{ACOL[q]}{r}", v, color=BLUE, fmt=fmt)
        else:
            a[f"{ACOL[q]}{r}"].number_format = fmt
    put(a, f"{A_WHY}{r}", why, italic=True)
    a[f"{A_WHY}{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    COMMON[name] = r
    r += 1
for k in ("Restaurant openings (company-owned)",):
    for q in FCST_Q:
        a[f"{ACOL[q]}{COMMON[k]}"].fill = FILL_KEY

a.column_dimensions["A"].width = 52
a.column_dimensions["B"].width = 10
a.column_dimensions["C"].width = 6
a.column_dimensions["D"].width = 2
for q in FCST_Q:
    a.column_dimensions[ACOL[q]].width = 11
a.column_dimensions[L(5 + len(FCST_Q))].width = 2
a.column_dimensions[A_WHY].width = 95
a.freeze_panes = "E7"

AREF = lambda name, q: f"Assumptions!{ACOL[q]}${INUSE[name]}" if name in INUSE else f"Assumptions!{ACOL[q]}${COMMON[name]}"

# ======================================================================= Hist
h = wb.create_sheet("Hist")
title(h, "Reported quarterly results", "Typed in from SEC filings ($ thousands). Q4 = full year less Q1-Q3, "
      "because companies don't file Q4 on its own. Calculated rows below are formulas.")
header_row(h, 4, ["Line item", "Source", "Q4 2020"] + [qname(q) for q in HIST_Q] + [""] + [f"FY{y}" for y in H_YEARS], 1)

HROW = {}
hist_items = [
    ("Revenue", "revenue", "XBRL Revenues"),
    ("Food, beverage and packaging", "food_bev_packaging", "XBRL CostDirectMaterial"),
    ("Labor", "labor", "XBRL CostDirectLabor"),
    ("Occupancy", "occupancy", "XBRL OccupancyNet"),
    ("Other operating costs", "other_operating", "XBRL OtherCostAndExpenseOperating"),
    ("General and administrative", "g_and_a", "XBRL GeneralAndAdministrativeExpense"),
    ("Depreciation and amortization", "d_and_a", "XBRL DepreciationDepletionAndAmortization"),
    ("Pre-opening costs", "pre_opening", "XBRL PreOpeningCosts"),
    ("Impairment, closures and asset disposals", "impairment_closures", "XBRL GainLossOnSales...ImpairmentCharges (sign flipped)"),
    ("Total operating expenses", "total_operating_expenses", "XBRL CostsAndExpenses"),
    ("Income from operations", "operating_income", "XBRL OperatingIncomeLoss"),
    ("Interest and other income, net", "interest_other_income", "XBRL OtherNonoperatingIncomeExpense"),
    ("Income before income taxes", "pretax_income", "XBRL pre-tax income"),
    ("Provision for income taxes", "income_tax", "Pre-tax income less net income"),
    ("Net income", "net_income", "XBRL NetIncomeLoss"),
    ("Diluted weighted-average shares (000)", "diluted_shares", "XBRL; pre-split periods x50 (50-for-1 split, Jun 2024)"),
]
r = 5
section(h, r, "Income statement ($ thousands)", 31)
r += 1
for label, col, src in hist_items:
    put(h, f"A{r}", label)
    put(h, f"B{r}", src, color=GREY, italic=True)
    for q in HIST_Q:
        v = pnl.at[q, col]
        if col == "diluted_shares":
            v = v / 1000
        put(h, f"{HCOL[q]}{r}", float(round(v, 3)), color=BLUE, fmt=NUM)
    HROW[col] = r
    r += 1

r += 1
section(h, r, "Restaurants and sales trends", 31)
r += 1
unit_items = [
    ("Restaurants opened", "opened", "Earnings release, unit table"),
    ("Permanent closures", "closures", "Earnings release"),
    ("Relocations", "relocations", "Earnings release"),
    ("Restaurants at end of period", "restaurants_end", "Earnings release"),
    ("Average restaurant sales ($000, trailing 12 months)", "avg_restaurant_sales", "Earnings release"),
    ("Comparable restaurant sales growth", "comp_sales_pct", "Earnings release"),
]
for label, col, src in unit_items:
    put(h, f"A{r}", label)
    put(h, f"B{r}", src, color=GREY, italic=True)
    for q in HIST_Q:
        v = units.at[q, col]
        if col == "comp_sales_pct":
            put(h, f"{HCOL[q]}{r}", float(v) / 100, color=BLUE, fmt=PCT)
        else:
            put(h, f"{HCOL[q]}{r}", float(v), color=BLUE, fmt=NUM)
    HROW[col] = r
    r += 1
put(h, f"C{HROW['restaurants_end']}", float(units.at["2020Q4", "restaurants_end"]), color=BLUE, fmt=NUM)
note(h, f"C{HROW['restaurants_end']}", "Restaurants at Dec 31, 2020 (Q4 2020 earnings release); "
     "needed for the Q1 2021 average restaurant count.")

for label, col in [("Comparable transactions growth", "transactions_pct"), ("Average check growth", "avg_check_pct")]:
    put(h, f"A{r}", label)
    put(h, f"B{r}", "Earnings release text (disclosed from Q4 2023)", color=GREY, italic=True)
    for q in HIST_Q:
        if q in split.index:
            put(h, f"{HCOL[q]}{r}", float(split.at[q, col]) / 100, color=BLUE, fmt=PCT)
    HROW[col] = r
    r += 1

rep_df = pd.read_csv(PROC / "cmg_reported_margin.csv").set_index("quarter")
rep = {q: v / 100 for q, v in rep_df["restaurant_margin_reported_pct"].items()}
put(h, f"A{r}", "Restaurant-level margin as reported by Chipotle")
put(h, f"B{r}", "Earnings release (non-GAAP)", color=GREY, italic=True)
for q in HIST_Q:
    if q in rep:
        put(h, f"{HCOL[q]}{r}", rep[q], color=BLUE, fmt=PCT)
HROW["rlm_reported"] = r
r += 2

section(h, r, "Calculated", 31)
r += 1
R = HROW


def hrow(label, key, formula_fn, fmt, first_ok=True):
    """formula_fn(col_letter, prev_col_letter, col_4_back or None) -> formula"""
    global r
    put(h, f"A{r}", label)
    for i, q in enumerate(HIST_Q):
        c = HCOL[q]
        prev = L(H_FIRST + i - 1)
        back4 = HCOL[HIST_Q[i - 4]] if i >= 4 else None
        f = formula_fn(c, prev, back4)
        if f is not None:
            put(h, f"{c}{r}", f, fmt=fmt)
    HROW[key] = r
    r += 1


hrow("Revenue growth, y/y", "rev_growth", lambda c, p, b: f"={c}{R['revenue']}/{b}{R['revenue']}-1" if b else None, PCT)
for label, key in [("Food, beverage and packaging % of revenue", "food"), ("Labor %", "labor"),
                   ("Occupancy %", "occupancy"), ("Other operating costs %", "other_operating")]:
    src = {"food": "food_bev_packaging"}.get(key, key)
    hrow(label, key + "_pct", lambda c, p, b, s=src: f"={c}{R[s]}/{c}{R['revenue']}", PCT)
hrow("Restaurant-level margin", "rlm", lambda c, p, b: f"=1-SUM({c}{R['food_pct']}:{c}{R['other_operating_pct']})", PCT)
hrow("G&A % of revenue", "ga_pct", lambda c, p, b: f"={c}{R['g_and_a']}/{c}{R['revenue']}", PCT)
hrow("Operating margin", "op_margin", lambda c, p, b: f"={c}{R['operating_income']}/{c}{R['revenue']}", PCT)
hrow("Effective tax rate", "tax_rate", lambda c, p, b: f"={c}{R['income_tax']}/{c}{R['pretax_income']}", PCT)
hrow("Diluted EPS ($)", "eps", lambda c, p, b: f"={c}{R['net_income']}/{c}{R['diluted_shares']}", EPS)
hrow("Average restaurants in quarter", "avg_rest",
     lambda c, p, b: f"=({p}{R['restaurants_end']}+{c}{R['restaurants_end']})/2", NUM1)
hrow("Revenue per average restaurant ($000)", "rpr", lambda c, p, b: f"={c}{R['revenue']}/{c}{R['avg_rest']}", NUM1)
hrow("Revenue per restaurant growth, y/y", "rpr_growth",
     lambda c, p, b: f"={c}{R['rpr']}/{b}{R['rpr']}-1" if b else None, PCT)
hrow("Non-comp effect (RPR growth vs comps)", "noncomp",
     lambda c, p, b: f"=(1+{c}{R['rpr_growth']})/(1+{c}{R['comp_sales_pct']})-1" if b else None, PCT)
hrow("Pre-opening cost per opening ($000)", "preopen_per",
     lambda c, p, b: f"=IF({c}{R['opened']}=0,0,{c}{R['pre_opening']}/{c}{R['opened']})", NUM1)
r += 1
section(h, r, "Tie-out checks (should all be zero)", 31)
r += 1
cost_cols = ["food_bev_packaging", "labor", "occupancy", "other_operating", "g_and_a", "d_and_a", "pre_opening",
             "impairment_closures"]
hrow("Costs less total operating expenses", "chk_costs",
     lambda c, p, b: "=ROUND(" + "+".join(f"{c}{R[k]}" for k in cost_cols) + f"-{c}{R['total_operating_expenses']},0)", NUM)
hrow("Revenue less expenses less operating income", "chk_oi",
     lambda c, p, b: f"=ROUND({c}{R['revenue']}-{c}{R['total_operating_expenses']}-{c}{R['operating_income']},0)", NUM)
hrow("Restaurant roll-forward difference", "chk_roll",
     lambda c, p, b: f"={p}{R['restaurants_end']}+{c}{R['opened']}+{c}{R['closures']}+{c}{R['relocations']}-{c}{R['restaurants_end']}", NUM)
hrow("Our margin less reported margin (pts, rounded)", "chk_rlm",
     lambda c, p, b: f'=IF({c}{R["rlm_reported"]}="",0,ROUND(({c}{R["rlm"]}-{c}{R["rlm_reported"]})*100,1))', '0.0')

# full-year columns on Hist
fy_sum_rows = [k for _, k, _ in hist_items if k != "diluted_shares"] + ["opened", "closures", "relocations"]
for y in H_YEARS:
    yc = HYCOL[y]
    qs = [q for q in HIST_Q if q.startswith(str(y))]
    c1, c4 = HCOL[qs[0]], HCOL[qs[-1]]
    for k in fy_sum_rows:
        put(h, f"{yc}{R[k]}", f"=SUM({c1}{R[k]}:{c4}{R[k]})", fmt=NUM)
    put(h, f"{yc}{R['restaurants_end']}", f"={c4}{R['restaurants_end']}", fmt=NUM)
    put(h, f"{yc}{R['diluted_shares']}", f"=AVERAGE({c1}{R['diluted_shares']}:{c4}{R['diluted_shares']})", fmt=NUM)
    for key, src in [("food_pct", "food_bev_packaging"), ("labor_pct", "labor"), ("occupancy_pct", "occupancy"),
                     ("other_operating_pct", "other_operating")]:
        put(h, f"{yc}{R[key]}", f"={yc}{R[src]}/{yc}{R['revenue']}", fmt=PCT)
    put(h, f"{yc}{R['rlm']}", f"=1-SUM({yc}{R['food_pct']}:{yc}{R['other_operating_pct']})", fmt=PCT)
    put(h, f"{yc}{R['ga_pct']}", f"={yc}{R['g_and_a']}/{yc}{R['revenue']}", fmt=PCT)
    put(h, f"{yc}{R['op_margin']}", f"={yc}{R['operating_income']}/{yc}{R['revenue']}", fmt=PCT)
    put(h, f"{yc}{R['tax_rate']}", f"={yc}{R['income_tax']}/{yc}{R['pretax_income']}", fmt=PCT)
    put(h, f"{yc}{R['eps']}", f"={yc}{R['net_income']}/{yc}{R['diluted_shares']}", fmt=EPS)
    if y > 2021:
        put(h, f"{yc}{R['rev_growth']}", f"={yc}{R['revenue']}/{HYCOL[y - 1]}{R['revenue']}-1", fmt=PCT)

h.column_dimensions["A"].width = 46
h.column_dimensions["B"].width = 30
for col in range(3, 3 + 1 + len(HIST_Q) + 1 + len(H_YEARS)):
    h.column_dimensions[L(col)].width = 11
h.freeze_panes = "C5"

# ====================================================================== Model
m = wb.create_sheet("Model", 1)
title(m, "Quarterly model ($ thousands)", None)
put(m, "A2", '="Scenario in use: "&Assumptions!$D$4', color=GREEN, italic=True)
header_row(m, 4, ["", ""] + [qname(q) for q in MODEL_Q] + [""] + list(M_YEARS), 1)
for q in MODEL_Q:
    c = MCOL[q]
    put(m, f"{c}5", "Forecast" if q in FCST_Q else "Actual", color=GREY, italic=True, align="center")
for y, c in M_YEARS.items():
    put(m, f"{c}5", "Forecast" if y.endswith("E") else "Actual", color=GREY, italic=True, align="center")

MR = {}
row = 6


def mline(label, key, hist_fn, fcst_fn, fmt, annual_fn=None, bold=False, how=""):
    """hist_fn(col, q) and fcst_fn(col, q) return formulas; annual_fn(year_col, first_q_col, last_q_col)."""
    global row
    put(m, f"A{row}", label, bold=bold)
    if how:
        put(m, f"B{row}", how, color=GREY, italic=True)
    MR[key] = row
    for q in MODEL_Q:
        c = MCOL[q]
        if q in FCST_Q:
            f = fcst_fn(c, q)
            color = BLACK
        else:
            f = hist_fn(c, q)
            color = GREEN if isinstance(f, str) and re.fullmatch(r"=Hist![A-Z]+\d+", f) else BLACK
        if f is not None:
            put(m, f"{c}{row}", f, color=color, fmt=fmt, bold=bold, fill=FILL_FCST if q in FCST_Q else None)
        elif q in FCST_Q:
            m[f"{c}{row}"].fill = FILL_FCST
    if annual_fn:
        for y, yc in M_YEARS.items():
            qs = M_YEAR_Q[y]
            f = annual_fn(yc, MCOL[qs[0]], MCOL[qs[-1]], y)
            if f is not None:
                put(m, f"{yc}{row}", f, fmt=fmt, bold=bold)
    row += 1


def back4(col):
    """Column four quarters earlier on the Model sheet."""
    from openpyxl.utils import column_index_from_string as ci
    return L(ci(col) - 4)


def prev(col):
    from openpyxl.utils import column_index_from_string as ci
    return L(ci(col) - 1)


H = lambda key, q: f"Hist!{HCOL[q]}{HROW[key]}"
FY_HIST = {"FY2025A": 2025}
SUMY = lambda yc, a1, a2, y: f"=SUM({a1}{row}:{a2}{row})"

section(m, row, "Restaurants", 18)
row += 1
mline("Restaurants opened", "opened", lambda c, q: "=" + H("opened", q),
      lambda c, q: "=" + AREF("Restaurant openings (company-owned)", q), NUM, SUMY)
mline("Closures and relocations (net)", "closures",
      lambda c, q: f"={H('closures', q)}+{H('relocations', q)}",
      lambda c, q: "=" + AREF("Closures and relocations (net)", q), NUM, SUMY)
mline("Restaurants at end of quarter", "rest_end", lambda c, q: "=" + H("restaurants_end", q),
      lambda c, q: f"={prev(c)}{MR['rest_end']}+{c}{MR['opened']}+{c}{MR['closures']}", NUM,
      lambda yc, a1, a2, y: f"={a2}{MR['rest_end']}", bold=True)
mline("Average restaurants in quarter", "avg_rest", lambda c, q: "=" + H("avg_rest", q),
      lambda c, q: f"=({prev(c)}{MR['rest_end']}+{c}{MR['rest_end']})/2", NUM1,
      lambda yc, a1, a2, y: f"=AVERAGE({a1}{row}:{a2}{row})")
row += 1
section(m, row, "Sales drivers", 18)
row += 1
mline("Transactions growth, y/y", "tx", lambda c, q: "=" + H("transactions_pct", q),
      lambda c, q: "=" + AREF("Transactions growth, y/y", q), PCT,
      lambda yc, a1, a2, y: f"=AVERAGE({a1}{row}:{a2}{row})", how="FY = average of quarters")
mline("Average check growth, y/y", "check", lambda c, q: "=" + H("avg_check_pct", q),
      lambda c, q: "=" + AREF("Average check growth, y/y", q), PCT,
      lambda yc, a1, a2, y: f"=AVERAGE({a1}{row}:{a2}{row})", how="FY = average of quarters")
mline("Comparable sales growth", "comps", lambda c, q: "=" + H("comp_sales_pct", q),
      lambda c, q: f"=(1+{c}{MR['tx']})*(1+{c}{MR['check']})-1", PCT,
      lambda yc, a1, a2, y: f"=AVERAGE({a1}{row}:{a2}{row})", bold=True, how="(1+transactions)x(1+check)-1")
mline("Non-comp effect (new-restaurant dilution)", "noncomp", lambda c, q: "=" + H("noncomp", q),
      lambda c, q: "=" + AREF("Non-comp revenue effect", q), PCT)
mline("Revenue per restaurant growth, y/y", "rpr_g", lambda c, q: "=" + H("rpr_growth", q),
      lambda c, q: f"=(1+{c}{MR['comps']})*(1+{c}{MR['noncomp']})-1", PCT)
mline("Revenue per average restaurant ($000)", "rpr", lambda c, q: "=" + H("rpr", q),
      lambda c, q: f"={back4(c)}{row}*(1+{c}{MR['rpr_g']})", NUM1, how="same quarter last year x (1+growth)")
mline("Revenue", "revenue", lambda c, q: "=" + H("revenue", q),
      lambda c, q: f"={c}{MR['avg_rest']}*{c}{MR['rpr']}", NUM, SUMY, bold=True, how="avg restaurants x revenue per restaurant")
mline("Revenue growth, y/y", "rev_g", lambda c, q: "=" + H("rev_growth", q),
      lambda c, q: f"={c}{MR['revenue']}/{back4(c)}{MR['revenue']}-1", PCT,
      lambda yc, a1, a2, y: (f"={yc}{MR['revenue']}/Hist!{HYCOL[2024]}{HROW['revenue']}-1" if y == "FY2025A"
                             else f"={yc}{MR['revenue']}/{prev(yc)}{MR['revenue']}-1"))
row += 1
section(m, row, "Restaurant operating costs, % of revenue", 18)
row += 1
TX = lambda c: f"((1+{c}{MR['tx']})*(1+{c}{MR['noncomp']})-1)"
PCT_ANNUAL = lambda dollar_key: (lambda yc, a1, a2, y: f"={yc}{MR[dollar_key]}/{yc}{MR['rev2']}")
mline("Food, beverage and packaging", "food_pct", lambda c, q: "=" + H("food_pct", q),
      lambda c, q: f"={back4(c)}{row}*(1+{AREF('Food cost inflation per transaction', q)})/(1+{c}{MR['check']})", PCT,
      how="last year % x (1+food inflation) / (1+check growth)")
mline("Labor", "labor_pct", lambda c, q: "=" + H("labor_pct", q),
      lambda c, q: (f"={back4(c)}{row}*(1+{AREF('Restaurant wage inflation', q)})"
                    f"*(1+(1-{AREF('Labor: share of hours that is fixed', q)})*{TX(c)})/(1+{c}{MR['rpr_g']})"), PCT,
      how="last year % x wage x variable hours / revenue per restaurant")
mline("Occupancy", "occ_pct", lambda c, q: "=" + H("occupancy_pct", q),
      lambda c, q: f"={back4(c)}{row}*(1+{AREF('Occupancy cost growth per restaurant', q)})/(1+{c}{MR['rpr_g']})", PCT,
      how="last year % x (1+rent growth) / revenue per restaurant")
mline("Other operating costs", "oth_pct", lambda c, q: "=" + H("other_operating_pct", q),
      lambda c, q: (f"={back4(c)}{row}*(1+{AREF('Other operating cost growth per restaurant', q)})"
                    f"*(1+(1-{AREF('Other operating: share that is fixed', q)})*{TX(c)})/(1+{c}{MR['rpr_g']})"), PCT,
      how="same logic as labor")
mline("Restaurant-level margin", "rlm", lambda c, q: f"=1-SUM({c}{MR['food_pct']}:{c}{MR['oth_pct']})",
      lambda c, q: f"=1-SUM({c}{MR['food_pct']}:{c}{MR['oth_pct']})", PCT, bold=True)
row += 1
section(m, row, "Income statement ($ thousands)", 18)
row += 1
mline("Revenue", "rev2", lambda c, q: f"={c}{MR['revenue']}", lambda c, q: f"={c}{MR['revenue']}", NUM, SUMY, bold=True)
for label, key, pkey, hkey in [("Food, beverage and packaging", "food", "food_pct", "food_bev_packaging"),
                               ("Labor", "labor", "labor_pct", "labor"), ("Occupancy", "occ", "occ_pct", "occupancy"),
                               ("Other operating costs", "oth", "oth_pct", "other_operating")]:
    mline(label, key, lambda c, q, hk=hkey: "=" + H(hk, q),
          lambda c, q, pk=pkey: f"={c}{MR[pk]}*{c}{MR['rev2']}", NUM, SUMY)
mline("Restaurant-level operating profit", "rlp", lambda c, q: f"={c}{MR['rev2']}-SUM({c}{MR['food']}:{c}{MR['oth']})",
      lambda c, q: f"={c}{MR['rev2']}-SUM({c}{MR['food']}:{c}{MR['oth']})", NUM, SUMY, bold=True)
GA_IN = "G&A ($000); blank = same quarter last year x (1 + G&A growth)"
mline("General and administrative", "ga", lambda c, q: "=" + H("g_and_a", q),
      lambda c, q: (f'=IF({AREF(GA_IN, q)}="",{back4(c)}{row}*(1+{AREF("G&A growth for blank quarters", q)}),'
                    f'{AREF(GA_IN, q)})'), NUM, SUMY)
mline("Depreciation and amortization", "da", lambda c, q: "=" + H("d_and_a", q),
      lambda c, q: f"={c}{MR['rev2']}*{AREF('Depreciation and amortization, % of revenue', q)}", NUM, SUMY)
mline("Pre-opening costs", "preopen", lambda c, q: "=" + H("pre_opening", q),
      lambda c, q: f"={c}{MR['opened']}*{AREF('Pre-opening cost per opening ($000)', q)}", NUM, SUMY)
mline("Impairment, closures and disposals", "impair", lambda c, q: "=" + H("impairment_closures", q),
      lambda c, q: "=" + AREF("Impairment, closures and disposals ($000)", q), NUM, SUMY)
mline("Income from operations", "oi", lambda c, q: f"={c}{MR['rlp']}-SUM({c}{MR['ga']}:{c}{MR['impair']})",
      lambda c, q: f"={c}{MR['rlp']}-SUM({c}{MR['ga']}:{c}{MR['impair']})", NUM, SUMY, bold=True)
mline("Interest and other income", "interest", lambda c, q: "=" + H("interest_other_income", q),
      lambda c, q: "=" + AREF("Interest and other income ($000)", q), NUM, SUMY)
mline("Income before income taxes", "pretax", lambda c, q: f"={c}{MR['oi']}+{c}{MR['interest']}",
      lambda c, q: f"={c}{MR['oi']}+{c}{MR['interest']}", NUM, SUMY)
mline("Provision for income taxes", "tax", lambda c, q: "=" + H("income_tax", q),
      lambda c, q: f"={c}{MR['pretax']}*{AREF('Effective tax rate', q)}", NUM, SUMY)
mline("Net income", "ni", lambda c, q: f"={c}{MR['pretax']}-{c}{MR['tax']}",
      lambda c, q: f"={c}{MR['pretax']}-{c}{MR['tax']}", NUM, SUMY, bold=True)
mline("Diluted shares (000)", "shares", lambda c, q: "=" + H("diluted_shares", q),
      lambda c, q: f"={prev(c)}{row}*(1+{AREF('Diluted share count change, q/q', q)})", NUM,
      lambda yc, a1, a2, y: f"=AVERAGE({a1}{row}:{a2}{row})")
mline("Diluted EPS ($)", "eps", lambda c, q: f"={c}{MR['ni']}/{c}{MR['shares']}",
      lambda c, q: f"={c}{MR['ni']}/{c}{MR['shares']}", EPS,
      lambda yc, a1, a2, y: f"=SUM({a1}{row}:{a2}{row})", bold=True, how="FY = sum of quarters")
mline("EPS growth, y/y", "eps_g", lambda c, q: (f"={c}{MR['eps']}/{H('eps', HIST_Q[HIST_Q.index(q) - 4])}-1"),
      lambda c, q: f"={c}{MR['eps']}/{back4(c)}{MR['eps']}-1", PCT,
      lambda yc, a1, a2, y: (f"={yc}{MR['eps']}/SUM(Hist!{HCOL['2024Q1']}{HROW['eps']}:Hist!{HCOL['2024Q4']}{HROW['eps']})-1"
                             if y == "FY2025A" else f"={yc}{MR['eps']}/{prev(yc)}{MR['eps']}-1"))
row += 1
section(m, row, "Margins", 18)
row += 1
mline("Restaurant-level margin", "rlm2", lambda c, q: f"={c}{MR['rlp']}/{c}{MR['rev2']}",
      lambda c, q: f"={c}{MR['rlp']}/{c}{MR['rev2']}", PCT,
      lambda yc, a1, a2, y: f"={yc}{MR['rlp']}/{yc}{MR['rev2']}", bold=True)
mline("Operating margin", "opm", lambda c, q: f"={c}{MR['oi']}/{c}{MR['rev2']}",
      lambda c, q: f"={c}{MR['oi']}/{c}{MR['rev2']}", PCT,
      lambda yc, a1, a2, y: f"={yc}{MR['oi']}/{yc}{MR['rev2']}", bold=True)
mline("G&A % of revenue", "ga_pct", lambda c, q: f"={c}{MR['ga']}/{c}{MR['rev2']}",
      lambda c, q: f"={c}{MR['ga']}/{c}{MR['rev2']}", PCT,
      lambda yc, a1, a2, y: f"={yc}{MR['ga']}/{yc}{MR['rev2']}")

# annual % lines in the cost block (need rev2, so filled in after)
for key, dkey in [("food_pct", "food"), ("labor_pct", "labor"), ("occ_pct", "occ"), ("oth_pct", "oth")]:
    for y, yc in M_YEARS.items():
        put(m, f"{yc}{MR[key]}", f"={yc}{MR[dkey]}/{yc}{MR['rev2']}", fmt=PCT)
for y, yc in M_YEARS.items():
    put(m, f"{yc}{MR['rlm']}", f"=1-SUM({yc}{MR['food_pct']}:{yc}{MR['oth_pct']})", fmt=PCT, bold=True)

m.column_dimensions["A"].width = 40
m.column_dimensions["B"].width = 34
for q in MODEL_Q:
    m.column_dimensions[MCOL[q]].width = 11
m.column_dimensions["O"].width = 2
for yc in M_YEARS.values():
    m.column_dimensions[yc].width = 12
m.freeze_panes = "C6"

# ================================================================ Q3_Forecast
f3 = wb.create_sheet("Q3_Forecast")
Q3_REPORTED = "2026Q3" in HIST_Q
title(f3, "Q3 2026: forecast vs actual",
      "Locked forecast = the Base case saved on Oct 15, 2026, before Chipotle reported on Oct 28. "
      + ("Actuals link to the Model (from the 10-Q and earnings release)." if Q3_REPORTED else
         "Type the actuals into column F after the release; variance fills in."))
header_row(f3, 4, ["Line", "Unit", "Model now (scenario in use)", "Locked forecast (Base)",
                   "Management commentary (Jul 29 call)", "Actual (reported Oct 28)", "Variance (actual - forecast)",
                   "What explains the gap"], 1)
q3 = MCOL["2026Q3"]
# short reasons, from docs/q3_2026_variance.md
GAP = {
    "comps": "Traffic turned positive (+0.8%) instead of falling; check was weaker.",
    "tx": "Third straight quarter of positive transactions; I assumed the cyclospora hit would hold traffic down.",
    "check": "Price was 2.7% as guided, but mix took off ~1.4 pts (promotions, LTO mix).",
    "opened": "One fewer opening than forecast.",
    "rev2": "All from sales per restaurant; restaurant count was exactly right.",
    "food_pct": "Tariff relief and favourable LTO mix, not in my assumptions.",
    "labor_pct": "Extra labor for promotions and insurance costs.",
    "occ_pct": "Higher sales spread the fixed rent.",
    "oth_pct": "Marketing and delivery mix ran above the mid-15% guide.",
    "rlm": "Food and other operating gaps nearly cancelled out.",
    "ga": "GAAP one-offs were smaller than in Q2.",
    "oi": "Higher revenue offset by a slightly lower margin.",
    "opm": "",
    "ni": "Lower interest income and a 25.6% tax rate vs my 25%.",
    "eps": "Same as net income; share count close to forecast.",
}
F3 = [
    ("Comparable sales growth", "%", "comps", PCT, "about +1%"),
    ("Transactions growth", "%", "tx", PCT, ""),
    ("Average check growth", "%", "check", PCT, "menu price mid-2%"),
    ("Restaurants opened", "#", "opened", NUM, "~350 for 2026"),
    ("Restaurants at end of quarter", "#", "rest_end", NUM, ""),
    ("Revenue ($000)", "$000", "rev2", NUM, ""),
    ("Food, beverage and packaging %", "%", "food_pct", PCT, "just under 30%"),
    ("Labor %", "%", "labor_pct", PCT, "mid-25%"),
    ("Occupancy %", "%", "occ_pct", PCT, ""),
    ("Other operating costs %", "%", "oth_pct", PCT, "mid-15%"),
    ("Restaurant-level margin", "%", "rlm", PCT, ""),
    ("G&A ($000)", "$000", "ga", NUM, "~$180M non-GAAP"),
    ("Income from operations ($000)", "$000", "oi", NUM, ""),
    ("Operating margin", "%", "opm", PCT, ""),
    ("Net income ($000)", "$000", "ni", NUM, ""),
    ("Diluted EPS ($)", "$", "eps", EPS, ""),
]
F3ROW = {}
for i, (label, unit, key, fmt, mgmt) in enumerate(F3):
    rr = 5 + i
    F3ROW[key] = rr
    put(f3, f"A{rr}", label)
    put(f3, f"B{rr}", unit, color=GREY)
    put(f3, f"C{rr}", f"=Model!{q3}{MR[key]}", color=GREEN, fmt=fmt)
    f3[f"D{rr}"].number_format = fmt          # filled with values by run_model.py
    f3[f"D{rr}"].font = font(BLUE, bold=True)
    put(f3, f"E{rr}", mgmt, color=GREY, italic=True)
    if Q3_REPORTED:
        put(f3, f"F{rr}", f"=Model!{q3}{MR[key]}", color=GREEN, fmt=fmt)
        put(f3, f"H{rr}", GAP.get(key, ""), italic=True)
    else:
        f3[f"F{rr}"].number_format = fmt
        f3[f"F{rr}"].font = font(BLUE)
        f3[f"F{rr}"].fill = FILL_KEY
    put(f3, f"G{rr}", f'=IF(F{rr}="","",F{rr}-D{rr})', fmt=(PCT2 if fmt == PCT else fmt))
rr = 5 + len(F3) + 1
put(f3, f"A{rr}", "Management's Q3 cost guidance implies a restaurant-level margin of about", italic=True)
put(f3, f"D{rr}", "=1-(0.299+0.255+D{0}+0.155)".format(F3ROW["occ_pct"]), fmt=PCT, italic=True)
note(f3, f"D{rr}", "Food 'just under 30%' taken as 29.9%, labor 'mid-25%' as 25.5%, other 'mid-15%' as 15.5%. "
     "Occupancy was not guided, so the locked forecast's occupancy % is used.")
F3_IMPLIED = rr
put(f3, f"A{rr + 2}", "Revenue variance split: restaurants vs revenue per restaurant", bold=True)
put(f3, f"A{rr + 3}", "From more/fewer average restaurants ($000)")
put(f3, f"A{rr + 4}", "From higher/lower revenue per restaurant ($000)")
put(f3, f"B{rr + 3}", "Actual avg restaurants")
f3[f"C{rr + 3}"].font = font(BLUE)
f3[f"C{rr + 3}"].fill = FILL_KEY
note(f3, f"C{rr + 3}", "Enter (end of Q2 restaurants + end of Q3 restaurants) / 2 from the Q3 release.")
if Q3_REPORTED:
    put(f3, f"C{rr + 3}", f"=Model!{q3}{MR['avg_rest']}", color=GREEN, fmt=NUM1)
put(f3, f"D{rr + 3}", f"=(Model!{MCOL['2026Q2']}{MR['rest_end']}+D{F3ROW['rest_end']})/2", fmt=NUM1)
put(f3, f"G{rr + 3}", f'=IF(OR(C{rr + 3}="",F{F3ROW["rev2"]}=""),"",(C{rr + 3}-D{rr + 3})*D{rr + 5})', fmt=NUM)
put(f3, f"G{rr + 4}", f'=IF(G{rr + 3}="","",G{F3ROW["rev2"]}-G{rr + 3})', fmt=NUM)
put(f3, f"B{rr + 5}", "Forecast revenue per restaurant")
put(f3, f"D{rr + 5}", f"=D{F3ROW['rev2']}/D{rr + 3}", fmt=NUM1)
F3_SPLIT = rr + 3
f3.column_dimensions["A"].width = 40
f3.column_dimensions["B"].width = 8
for c in "CDEFG":
    f3.column_dimensions[c].width = 22
f3.column_dimensions["H"].width = 50
f3.freeze_panes = "C5"

# ============================================================== Margin_Bridge
mb = wb.create_sheet("Margin_Bridge")
title(mb, "Restaurant-level margin bridge",
      "Each bar is the change in one cost line as a share of revenue. A cost line that rose takes margin away.")


def bridge(top, label, start_label, end_label, start_cells, end_cells, sheet):
    """start_cells/end_cells: dict line -> cell ref for % of revenue, plus 'rlm'."""
    header_row(mb, top, [label, "Margin / change", "bps"], 1)
    rows = [(start_label, f"={sheet}{start_cells['rlm']}")]
    for name, k in [("Food, beverage and packaging", "food"), ("Labor", "labor"), ("Occupancy", "occ"),
                    ("Other operating costs", "oth")]:
        rows.append((name, f"=-({sheet}{end_cells[k]}-{sheet}{start_cells[k]})"))
    rows.append((end_label, f"={sheet}{end_cells['rlm']}"))
    for i, (lab, f) in enumerate(rows):
        rr = top + 1 + i
        put(mb, f"A{rr}", lab, bold=i in (0, len(rows) - 1))
        put(mb, f"B{rr}", f, color=GREEN, fmt=PCT2, bold=i in (0, len(rows) - 1))
        if 0 < i < len(rows) - 1:
            put(mb, f"C{rr}", f"=B{rr}*10000", fmt=BPS)
    chk = top + len(rows) + 1
    put(mb, f"A{chk}", "Check: start + changes - end (should be 0)", italic=True, color=GREY)
    put(mb, f"B{chk}", f"=ROUND(B{top + 1}+SUM(B{top + 2}:B{top + 5})-B{top + 6},10)", fmt=PCT2, italic=True)
    return top + 1, chk


def hcells(q):
    c = HCOL[q]
    return {"rlm": f"{c}${HROW['rlm']}", "food": f"{c}${HROW['food_pct']}", "labor": f"{c}${HROW['labor_pct']}",
            "occ": f"{c}${HROW['occupancy_pct']}", "oth": f"{c}${HROW['other_operating_pct']}"}


def mcells(col):
    return {"rlm": f"{col}${MR['rlm']}", "food": f"{col}${MR['food_pct']}", "labor": f"{col}${MR['labor_pct']}",
            "occ": f"{col}${MR['occ_pct']}", "oth": f"{col}${MR['oth_pct']}"}


b1, chk1 = bridge(4, "Q2 2025 to Q2 2026 (actual)", "Q2 2025 margin", "Q2 2026 margin",
                  hcells("2025Q2"), hcells("2026Q2"), "Hist!")
b2, chk2 = bridge(14, "Q2 2024 peak to Q2 2026 (actual)", "Q2 2024 margin", "Q2 2026 margin",
                  hcells("2024Q2"), hcells("2026Q2"), "Hist!")
b3, chk3 = bridge(24, "FY2025 to FY2026E (scenario in use)", "FY2025 margin", "FY2026E margin",
                  mcells("P"), mcells("Q"), "Model!")
b4, chk4 = bridge(34, "FY2026E to FY2027E (scenario in use)", "FY2026E margin", "FY2027E margin",
                  mcells("Q"), mcells("R"), "Model!")
BRIDGE_CHECKS = [chk1, chk2, chk3, chk4]

# waterfall helper for bridge 1 (stacked columns with an invisible base)
put(mb, "E3", "Chart data for the Q2 2025 to Q2 2026 waterfall", italic=True, color=GREY)
header_row(mb, 4, ["Step", "Base", "Drop", "Rise", "Total"], 5)
steps = ["Q2 2025", "Food", "Labor", "Occupancy", "Other", "Q2 2026"]
for i, s in enumerate(steps):
    rr = 5 + i
    put(mb, f"E{rr}", s)
    if i in (0, 5):
        put(mb, f"F{rr}", 0, fmt=PCT)
        put(mb, f"G{rr}", 0, fmt=PCT)
        put(mb, f"H{rr}", 0, fmt=PCT)
        put(mb, f"I{rr}", f"=B{b1 + i}", fmt=PCT)
    else:
        # running level before this step = start + sum of earlier changes
        level_before = f"(B{b1}+SUM(B{b1 + 1}:B{b1 + i})-B{b1 + i})"
        put(mb, f"F{rr}", f"=MIN({level_before},{level_before}+B{b1 + i})", fmt=PCT)
        put(mb, f"G{rr}", f"=MAX(0,-B{b1 + i})", fmt=PCT)
        put(mb, f"H{rr}", f"=MAX(0,B{b1 + i})", fmt=PCT)
        put(mb, f"I{rr}", 0, fmt=PCT)
ch = BarChart()
ch.type = "col"
ch.grouping = "stacked"
ch.overlap = 100
ch.title = "Restaurant-level margin, Q2 2025 to Q2 2026"
data = Reference(mb, min_col=6, max_col=9, min_row=4, max_row=10)
ch.add_data(data, titles_from_data=True)
ch.set_categories(Reference(mb, min_col=5, min_row=5, max_row=10))
ch.series[0].graphicalProperties.noFill = True
ch.series[0].graphicalProperties.line.noFill = True
ch.series[1].graphicalProperties.solidFill = "C0504D"
ch.series[2].graphicalProperties.solidFill = "4F81BD"
ch.series[3].graphicalProperties.solidFill = "1F3A5F"
ch.y_axis.number_format = "0%"
ch.y_axis.scaling.min = 0.20
ch.y_axis.scaling.max = 0.29
ch.legend = None
ch.height, ch.width = 8, 16
mb.add_chart(ch, "E13")
mb.column_dimensions["A"].width = 38
mb.column_dimensions["B"].width = 16
mb.column_dimensions["C"].width = 12
for c in "EFGHI":
    mb.column_dimensions[c].width = 11

# ================================================================ Sensitivity
s = wb.create_sheet("Sensitivity")
title(s, "FY2027E restaurant-level margin sensitivity",
      "Annual approximation of the Model's cost logic, starting from FY2026E cost ratios. Other inputs are the "
      "2027 averages of the scenario in use.")
params = [
    ("FY2026E food %", f"=Model!Q{MR['food_pct']}", PCT),
    ("FY2026E labor %", f"=Model!Q{MR['labor_pct']}", PCT),
    ("FY2026E occupancy %", f"=Model!Q{MR['occ_pct']}", PCT),
    ("FY2026E other operating %", f"=Model!Q{MR['oth_pct']}", PCT),
    ("2027 transactions growth", f"=AVERAGE(Model!K{MR['tx']}:N{MR['tx']})", PCT),
    ("2027 average check growth", f"=AVERAGE(Model!K{MR['check']}:N{MR['check']})", PCT),
    ("2027 food cost inflation", f"=AVERAGE(Assumptions!{A27}{INUSE['Food cost inflation per transaction']}:{A27_END}{INUSE['Food cost inflation per transaction']})", PCT),
    ("2027 wage inflation", f"=AVERAGE(Assumptions!{A27}{INUSE['Restaurant wage inflation']}:{A27_END}{INUSE['Restaurant wage inflation']})", PCT),
    ("2027 occupancy growth per restaurant", f"=AVERAGE(Assumptions!{A27}{COMMON['Occupancy cost growth per restaurant']}:{A27_END}{COMMON['Occupancy cost growth per restaurant']})", PCT),
    ("2027 other cost growth per restaurant", f"=AVERAGE(Assumptions!{A27}{INUSE['Other operating cost growth per restaurant']}:{A27_END}{INUSE['Other operating cost growth per restaurant']})", PCT),
    ("Non-comp effect", f"=AVERAGE(Assumptions!{A27}{COMMON['Non-comp revenue effect']}:{A27_END}{COMMON['Non-comp revenue effect']})", PCT),
    ("Labor fixed share", f"=Assumptions!{A27}{COMMON['Labor: share of hours that is fixed']}", "0.00"),
    ("Other operating fixed share", f"=Assumptions!{A27}{COMMON['Other operating: share that is fixed']}", "0.00"),
]
P = {}
for i, (lab, f, fmt) in enumerate(params):
    rr = 4 + i
    put(s, f"A{rr}", lab)
    put(s, f"B{rr}", f, color=GREEN, fmt=fmt)
    P[lab] = f"$B${rr}"
rr = 4 + len(params) + 1
put(s, f"A{rr}", "This table at the scenario's own inputs")
SENS_SELF = rr
put(s, f"A{rr + 1}", "Model FY2027E margin (quarterly build)")
put(s, f"B{rr + 1}", f"=Model!R{MR['rlm']}", color=GREEN, fmt=PCT)
note(s, f"A{rr}", "Small gaps to the Model come from doing the maths on full-year ratios instead of quarter by quarter.")


def rlm_formula(tx, ck, fi, w):
    nc, og, oi = P["Non-comp effect"], P["2027 occupancy growth per restaurant"], P["2027 other cost growth per restaurant"]
    fl, fo = P["Labor fixed share"], P["Other operating fixed share"]
    rprg = f"((1+{tx})*(1+{ck})*(1+{nc}))"
    vol = f"((1+{tx})*(1+{nc})-1)"
    food = f"{P['FY2026E food %']}*(1+{fi})/(1+{ck})"
    labor = f"{P['FY2026E labor %']}*(1+{w})*(1+(1-{fl})*{vol})/{rprg}"
    occ = f"{P['FY2026E occupancy %']}*(1+{og})/{rprg}"
    oth = f"{P['FY2026E other operating %']}*(1+{oi})*(1+(1-{fo})*{vol})/{rprg}"
    return f"=1-({food}+{labor}+{occ}+{oth})"


put(s, f"B{SENS_SELF}", rlm_formula(P["2027 transactions growth"], P["2027 average check growth"],
                                     P["2027 food cost inflation"], P["2027 wage inflation"]), fmt=PCT)

t1 = SENS_SELF + 4
put(s, f"A{t1 - 1}", "Table 1: FY2027E margin by transactions growth (rows) and average check growth (columns)", bold=True)
tx_vals = [-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04]
ck_vals = [0.0, 0.01, 0.015, 0.02, 0.03, 0.04]
put(s, f"A{t1}", "Transactions \\ Check", bold=True)
for j, v in enumerate(ck_vals):
    put(s, f"{L(2 + j)}{t1}", v, color=BLUE, fmt=PCT, bold=True)
for i, v in enumerate(tx_vals):
    rr = t1 + 1 + i
    put(s, f"A{rr}", v, color=BLUE, fmt=PCT, bold=True)
    for j in range(len(ck_vals)):
        c = L(2 + j)
        put(s, f"{c}{rr}", rlm_formula(f"$A{rr}", f"{c}${t1}", P["2027 food cost inflation"], P["2027 wage inflation"]), fmt=PCT)
T1 = (t1, len(tx_vals), len(ck_vals))

t2 = t1 + len(tx_vals) + 4
put(s, f"A{t2 - 1}", "Table 2: FY2027E margin by food cost inflation (rows) and wage inflation (columns)", bold=True)
fi_vals = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05]
w_vals = [0.02, 0.03, 0.035, 0.04, 0.05, 0.06]
put(s, f"A{t2}", "Food \\ Wage", bold=True)
for j, v in enumerate(w_vals):
    put(s, f"{L(2 + j)}{t2}", v, color=BLUE, fmt=PCT, bold=True)
for i, v in enumerate(fi_vals):
    rr = t2 + 1 + i
    put(s, f"A{rr}", v, color=BLUE, fmt=PCT, bold=True)
    for j in range(len(w_vals)):
        c = L(2 + j)
        put(s, f"{c}{rr}", rlm_formula(P["2027 transactions growth"], P["2027 average check growth"], f"$A{rr}", f"{c}${t2}"), fmt=PCT)

t3 = t2 + len(fi_vals) + 4
put(s, f"A{t3 - 1}", "Table 3: which lever moves FY2027E margin most? Margin change from a 1-point move in each driver", bold=True)
header_row(s, t3, ["Lever (+1 point, everything else at the scenario's inputs)", "Margin change", "bps"], 1)
base_rlm = f"B{SENS_SELF}"
tx0, ck0 = P["2027 transactions growth"], P["2027 average check growth"]
fi0, w0 = P["2027 food cost inflation"], P["2027 wage inflation"]
levers = [
    ("Transactions growth +1 pt", rlm_formula(f"({tx0}+0.01)", ck0, fi0, w0)),
    ("Average check (price) +1 pt", rlm_formula(tx0, f"({ck0}+0.01)", fi0, w0)),
    ("Food cost inflation -1 pt", rlm_formula(tx0, ck0, f"({fi0}-0.01)", w0)),
    ("Wage inflation -1 pt", rlm_formula(tx0, ck0, fi0, f"({w0}-0.01)")),
]
for i, (lab, f) in enumerate(levers):
    rr = t3 + 1 + i
    put(s, f"A{rr}", lab)
    put(s, f"B{rr}", "=" + f[1:] + f"-{base_rlm}", fmt=PCT2)
    put(s, f"C{rr}", f"=B{rr}*10000", fmt=BPS, bold=True)
LEVER_ROWS = (t3 + 1, t3 + len(levers))

t4 = t3 + len(levers) + 7
put(s, f"A{t4 - 4}", "Table 4: what would it take?", bold=True)
put(s, f"A{t4 - 3}", "Target FY2027E margin (default: FY2025 actual)")
put(s, f"B{t4 - 3}", f"=Model!P{MR['rlm2']}", color=GREEN, fmt=PCT, fill=FILL_KEY)
note(s, f"B{t4 - 3}", "Linked to the FY2025 restaurant-level margin. Type over it to test another target.")
header_row(s, t4, ["Transactions growth", "FY2027E margin", "", "Average check growth", "FY2027E margin"], 1)
tx_fine = [round(-0.02 + 0.0025 * k, 4) for k in range(57)]    # -2% .. +12%
ck_fine = [round(0.0025 * k, 4) for k in range(41)]            # 0% .. 10%
for i, v in enumerate(tx_fine):
    rr = t4 + 1 + i
    put(s, f"A{rr}", v, color=BLUE, fmt=PCT2)
    put(s, f"B{rr}", rlm_formula(f"$A{rr}", ck0, fi0, w0), fmt=PCT2)
for i, v in enumerate(ck_fine):
    rr = t4 + 1 + i
    put(s, f"D{rr}", v, color=BLUE, fmt=PCT2)
    put(s, f"E{rr}", rlm_formula(tx0, f"$D{rr}", fi0, w0), fmt=PCT2)
tgt = f"$B${t4 - 3}"


def needed(col_x, col_y, n, label_cell, row_label):
    first, last = t4 + 1, t4 + n
    put(s, f"A{label_cell}", row_label)
    put(s, f"B{label_cell}", (f'=IF({col_y}{first}>={tgt},"{"<="} "&TEXT({col_x}{first},"0.0%"),'
                              f'IF({col_y}{last}<{tgt},"more than "&TEXT({col_x}{last},"0.0%"),'
                              f'TEXT(INDEX({col_x}{first}:{col_x}{last},MATCH({tgt},{col_y}{first}:{col_y}{last},1)+1),"0.0%")))'),
        bold=True, align="right")


needed("A", "B", len(tx_fine), t4 - 2, "Transactions growth needed (at the scenario's check growth)")
needed("D", "E", len(ck_fine), t4 - 1, "Average check growth needed (at the scenario's transactions)")
SENS_NEEDED = f"B{t4 - 2}"
SENS_NEEDED_CK = f"B{t4 - 1}"
cs = CellIsRule(operator="greaterThanOrEqual", formula=[tgt], fill=PatternFill("solid", fgColor="D9EAD3"))
s.conditional_formatting.add(f"B{t1 + 1}:{L(1 + len(ck_vals))}{t1 + len(tx_vals)}", cs)
s.conditional_formatting.add(f"B{t2 + 1}:{L(1 + len(w_vals))}{t2 + len(fi_vals)}", cs)
s.column_dimensions["A"].width = 40
for j in range(2, 9):
    s.column_dimensions[L(j)].width = 12

# ================================================================== Scenarios
sc = wb.create_sheet("Scenarios")
title(sc, "Scenario comparison",
      "Base, Upside and Downside are saved results from running the model under each scenario "
      "(src/run_model.py). The 'Live' column follows the selector on Assumptions.")
header_row(sc, 4, ["Output", "Live (scenario in use)", "Base", "Upside", "Downside"], 1)
SC_ITEMS = [
    (f"Next quarter ({qname(FIRST_F)}) comparable sales", f"=Model!{MCOL[FIRST_F]}{MR['comps']}", PCT),
    (f"Next quarter ({qname(FIRST_F)}) revenue ($000)", f"=Model!{MCOL[FIRST_F]}{MR['rev2']}", NUM),
    (f"Next quarter ({qname(FIRST_F)}) restaurant-level margin", f"=Model!{MCOL[FIRST_F]}{MR['rlm']}", PCT),
    (f"Next quarter ({qname(FIRST_F)}) diluted EPS", f"=Model!{MCOL[FIRST_F]}{MR['eps']}", EPS),
    ("FY2026E revenue ($000)", f"=Model!Q{MR['rev2']}", NUM),
    ("FY2026E comparable sales (avg of quarters)", f"=Model!Q{MR['comps']}", PCT),
    ("FY2026E restaurant-level margin", f"=Model!Q{MR['rlm2']}", PCT),
    ("FY2026E operating margin", f"=Model!Q{MR['opm']}", PCT),
    ("FY2026E diluted EPS", f"=Model!Q{MR['eps']}", EPS),
    ("FY2027E revenue ($000)", f"=Model!R{MR['rev2']}", NUM),
    ("FY2027E revenue growth", f"=Model!R{MR['rev_g']}", PCT),
    ("FY2027E comparable sales (avg of quarters)", f"=Model!R{MR['comps']}", PCT),
    ("FY2027E restaurant-level margin", f"=Model!R{MR['rlm2']}", PCT),
    ("FY2027E margin change vs FY2025 (bps)", f"=(Model!R{MR['rlm2']}-Model!P{MR['rlm2']})*10000", BPS),
    ("FY2027E operating margin", f"=Model!R{MR['opm']}", PCT),
    ("FY2027E diluted EPS", f"=Model!R{MR['eps']}", EPS),
    ("FY2027E EPS growth", f"=Model!R{MR['eps_g']}", PCT),
]
SCROW = {}
for i, (lab, f, fmt) in enumerate(SC_ITEMS):
    rr = 5 + i
    SCROW[lab] = rr
    put(sc, f"A{rr}", lab)
    put(sc, f"B{rr}", f, color=GREEN, fmt=fmt)
    for c in "CDE":
        sc[f"{c}{rr}"].number_format = fmt
        sc[f"{c}{rr}"].font = font(BLUE)
rr = 5 + len(SC_ITEMS) + 1
put(sc, f"A{rr}", "Key differences in the drivers (2027 averages)", bold=True)
SC_DRIVERS = rr + 1
for i, name in enumerate(scen):
    r2 = SC_DRIVERS + i
    first = INUSE[name] - 3
    put(sc, f"A{r2}", name)
    for j, c in enumerate("CDE"):
        put(sc, f"{c}{r2}", f"=AVERAGE(Assumptions!{A27}{first + j}:{A27_END}{first + j})", color=GREEN, fmt=PCT)
sc.column_dimensions["A"].width = 46
for c in "BCDE":
    sc.column_dimensions[c].width = 20

# ====================================================================== Peers
pe = wb.create_sheet("Peers")
title(pe, "Fast-casual peers, last twelve months",
      "Restaurant-level margin rebuilt from each company's filed cost lines: revenue less food, labor, occupancy "
      "and other restaurant costs (before D&A, pre-opening and G&A).")
cols = ["Company", "LTM ending", "Revenue ($M)", "Revenue a year earlier ($M)", "Revenue growth",
        "Restaurant-level costs ($M)", "Restaurant-level margin", "Food & packaging %", "Labor %", "Occupancy %",
        "Other operating %", "Operating income ($M)", "Operating margin", "", "Food & packaging ($M)",
        "Labor ($M)", "Occupancy ($M)", "Other operating ($M)", "Notes"]
header_row(pe, 4, cols, 1)
notes = {
    "CMG": f"Four quarters to {qname(LAST_A)}.",
    "CAVA": "CAVA's Q1 is 16 weeks; LTM built as last fiscal year + YTD - prior YTD.",
    "SG": "Only total restaurant operating costs are tagged in XBRL, so the cost lines are not split.",
    "SHAK": "Food & paper is not in the standard tags, so the margin can't be rebuilt. Revenue includes licensing; "
            "LTM includes the 53-week fiscal 2025.",
}
for i, rr_ in peers.iterrows():
    rr = 5 + i
    put(pe, f"A{rr}", rr_["company"])
    put(pe, f"B{rr}", rr_["ltm_end"])
    put(pe, f"C{rr}", round(rr_["revenue"] / 1e6, 1), color=BLUE, fmt=NUM1)
    put(pe, f"D{rr}", round(rr_["revenue_prior_ltm"] / 1e6, 1), color=BLUE, fmt=NUM1)
    put(pe, f"E{rr}", f"=C{rr}/D{rr}-1", fmt=PCT)
    if pd.notna(rr_["restaurant_costs_total"]):
        put(pe, f"F{rr}", round(rr_["restaurant_costs_total"] / 1e6, 1), color=BLUE, fmt=NUM1)
        put(pe, f"G{rr}", f"=1-F{rr}/C{rr}", fmt=PCT, bold=True)
    else:
        put(pe, f"G{rr}", "n/a", color=GREY, align="right")
    for c, dc, k in zip("HIJK", "OPQR", ["food_paper", "labor", "occupancy", "other_operating"]):
        if pd.notna(rr_[k]):
            put(pe, f"{dc}{rr}", round(rr_[k] / 1e6, 1), color=BLUE, fmt=NUM1)
            put(pe, f"{c}{rr}", f"={dc}{rr}/C{rr}", fmt=PCT)
        else:
            put(pe, f"{c}{rr}", "n/a", color=GREY, align="right")
    put(pe, f"L{rr}", round(rr_["operating_income"] / 1e6, 1), color=BLUE, fmt=NUM1)
    put(pe, f"M{rr}", f"=L{rr}/C{rr}", fmt=PCT)
    put(pe, f"S{rr}", notes[rr_["ticker"]], color=GREY, italic=True)
put(pe, f"A{6 + len(peers)}", "Source: SEC EDGAR XBRL company facts (10-Q/10-K). Wingstop is left out because it is "
    "almost entirely franchised, so it has no comparable restaurant cost base.", color=GREY, italic=True)
pe.column_dimensions["A"].width = 14
pe.column_dimensions["B"].width = 12
for c in "CDEFGHIJKLMOPQR":
    pe.column_dimensions[c].width = 13
pe.column_dimensions["N"].width = 2
pe.column_dimensions["S"].width = 90

# ===================================================================== Charts
cht = wb.create_sheet("Charts")
title(cht, "Charts", "Quarterly revenue and restaurant-level margin, actual and forecast (scenario in use).")
header_row(cht, 4, ["Quarter", "Revenue ($M)", "Restaurant-level margin", "Comparable sales"], 1)
for i, q in enumerate(MODEL_Q):
    rr = 5 + i
    put(cht, f"A{rr}", qname(q) + (" (F)" if q in FCST_Q else ""))
    put(cht, f"B{rr}", f"=Model!{MCOL[q]}{MR['rev2']}/1000", color=GREEN, fmt=NUM)
    put(cht, f"C{rr}", f"=Model!{MCOL[q]}{MR['rlm']}", color=GREEN, fmt=PCT)
    put(cht, f"D{rr}", f"=Model!{MCOL[q]}{MR['comps']}", color=GREEN, fmt=PCT)
bc = BarChart()
bc.title = "Revenue by quarter ($M)"
bc.add_data(Reference(cht, min_col=2, min_row=4, max_row=4 + len(MODEL_Q)), titles_from_data=True)
bc.set_categories(Reference(cht, min_col=1, min_row=5, max_row=4 + len(MODEL_Q)))
bc.legend = None
bc.height, bc.width = 7.5, 18
cht.add_chart(bc, "F4")
lc = LineChart()
lc.title = "Restaurant-level margin"
lc.add_data(Reference(cht, min_col=3, min_row=4, max_row=4 + len(MODEL_Q)), titles_from_data=True)
lc.set_categories(Reference(cht, min_col=1, min_row=5, max_row=4 + len(MODEL_Q)))
lc.y_axis.number_format = "0%"
lc.y_axis.scaling.min = 0.20
lc.y_axis.scaling.max = 0.30
lc.legend = None
lc.height, lc.width = 7.5, 18
cht.add_chart(lc, "F20")
cht.column_dimensions["A"].width = 16
for c in "BCD":
    cht.column_dimensions[c].width = 14

# ===================================================================== Checks
ck = wb.create_sheet("Checks", 1)
title(ck, "Checks", "Every row should say PASS.")
header_row(ck, 5, ["Check", "Value", "Result"], 1)
HQ = f"{HCOL[HIST_Q[0]]}{{r}}:{HCOL[HIST_Q[-1]]}{{r}}"
checks = [
    ("Hist: costs add up to total operating expenses (max gap, $000)",
     f"=SUMPRODUCT(MAX(ABS(Hist!{HQ.format(r=HROW['chk_costs'])})))", "=IF(B{r}<=5,\"PASS\",\"FAIL\")"),
    ("Hist: revenue less expenses equals operating income (max gap, $000)",
     f"=SUMPRODUCT(MAX(ABS(Hist!{HQ.format(r=HROW['chk_oi'])})))", "=IF(B{r}<=5,\"PASS\",\"FAIL\")"),
    ("Hist: restaurant counts roll forward exactly (max gap)",
     f"=SUMPRODUCT(MAX(ABS(Hist!{HQ.format(r=HROW['chk_roll'])})))", "=IF(B{r}=0,\"PASS\",\"FAIL\")"),
    ("Hist: our margin matches Chipotle's reported margin (max gap, pts)",
     f"=SUMPRODUCT(MAX(ABS(Hist!{HQ.format(r=HROW['chk_rlm'])})))", "=IF(B{r}<=0.1,\"PASS\",\"FAIL\")"),
    ("Hist: FY2025 revenue = sum of quarters ($000)",
     f"=Hist!{HYCOL[2025]}{HROW['revenue']}-SUM(Hist!{HCOL['2025Q1']}{HROW['revenue']}:{HCOL['2025Q4']}{HROW['revenue']})",
     "=IF(ABS(B{r})<1,\"PASS\",\"FAIL\")"),
    ("Model: actual quarters tie to Hist revenue ($000)",
     f"=SUM(Model!{MCOL['2025Q1']}{MR['rev2']}:{MCOL[LAST_A]}{MR['rev2']})-SUM(Hist!{HCOL['2025Q1']}{HROW['revenue']}:{HCOL[LAST_A]}{HROW['revenue']})",
     "=IF(ABS(B{r})<1,\"PASS\",\"FAIL\")"),
    ("Model: actual quarters tie to Hist net income ($000)",
     f"=SUM(Model!{MCOL['2025Q1']}{MR['ni']}:{MCOL[LAST_A]}{MR['ni']})-SUM(Hist!{HCOL['2025Q1']}{HROW['net_income']}:{HCOL[LAST_A]}{HROW['net_income']})",
     "=IF(ABS(B{r})<1,\"PASS\",\"FAIL\")"),
    (f"Model: forecast restaurants roll forward (Q4 2027 end - {qname(LAST_A)} end - openings - closures)",
     f"=Model!{MCOL['2027Q4']}{MR['rest_end']}-Model!{MCOL[LAST_A]}{MR['rest_end']}-SUM(Model!{MCOL[FIRST_F]}{MR['opened']}:{MCOL['2027Q4']}{MR['opened']})-SUM(Model!{MCOL[FIRST_F]}{MR['closures']}:{MCOL['2027Q4']}{MR['closures']})",
     "=IF(ABS(B{r})<0.001,\"PASS\",\"FAIL\")"),
    ("Model: forecast revenue = average restaurants x revenue per restaurant ($000)",
     f"=SUMPRODUCT(Model!{MCOL[FIRST_F]}{MR['avg_rest']}:{MCOL['2027Q4']}{MR['avg_rest']},Model!{MCOL[FIRST_F]}{MR['rpr']}:{MCOL['2027Q4']}{MR['rpr']})-SUM(Model!{MCOL[FIRST_F]}{MR['rev2']}:{MCOL['2027Q4']}{MR['rev2']})",
     "=IF(ABS(B{r})<1,\"PASS\",\"FAIL\")"),
    ("Model: margin from % lines equals margin from $ lines (max gap)",
     f"=SUMPRODUCT(MAX(ABS(Model!{MCOL['2025Q1']}{MR['rlm']}:{MCOL['2027Q4']}{MR['rlm']}-Model!{MCOL['2025Q1']}{MR['rlm2']}:{MCOL['2027Q4']}{MR['rlm2']})))",
     "=IF(B{r}<0.000001,\"PASS\",\"FAIL\")"),
    ("Model: FY2027E net income = sum of quarters ($000)",
     f"=Model!R{MR['ni']}-SUM(Model!{MCOL['2027Q1']}{MR['ni']}:{MCOL['2027Q4']}{MR['ni']})",
     "=IF(ABS(B{r})<1,\"PASS\",\"FAIL\")"),
    ("Assumptions: scenario selector is 1, 2 or 3", "=Assumptions!C4",
     "=IF(OR(B{r}=1,B{r}=2,B{r}=3),\"PASS\",\"FAIL\")"),
    ("Margin bridges: start + changes = end (sum of abs gaps)",
     "=" + "+".join(f"ABS(Margin_Bridge!B{c})" for c in BRIDGE_CHECKS), "=IF(B{r}<0.000001,\"PASS\",\"FAIL\")"),
    ("Q3_Forecast: locked forecast is filled in", f"=COUNT(Q3_Forecast!D5:D{4 + len(F3)})",
     f"=IF(B{{r}}={len(F3)},\"PASS\",\"FAIL\")"),
]
for i, (lab, val, res) in enumerate(checks):
    rr = 6 + i
    put(ck, f"A{rr}", lab)
    put(ck, f"B{rr}", val, fmt='#,##0.000')
    put(ck, f"C{rr}", res.format(r=rr), bold=True, align="center")
last = 6 + len(checks) - 1
put(ck, "A3", "Overall", bold=True)
put(ck, "B3", f'=IF(COUNTIF(C6:C{last},"PASS")={len(checks)},"ALL CHECKS PASS",'
    f'COUNTIF(C6:C{last},"FAIL")&" CHECK(S) FAILED")', bold=True)
green = PatternFill("solid", fgColor="D9EAD3")
red = PatternFill("solid", fgColor="F4CCCC")
ck.conditional_formatting.add(f"C6:C{last}", CellIsRule(operator="equal", formula=['"PASS"'], fill=green))
ck.conditional_formatting.add(f"C6:C{last}", CellIsRule(operator="equal", formula=['"FAIL"'], fill=red))
ck.conditional_formatting.add("B3", FormulaRule(formula=['B3="ALL CHECKS PASS"'], fill=green))
ck.conditional_formatting.add("B3", FormulaRule(formula=['B3<>"ALL CHECKS PASS"'], fill=red))
put(ck, f"A{last + 2}", "Note: the Q3 locked forecast is a saved record, so it will not change if you edit the "
    "assumptions. That is on purpose.", color=GREY, italic=True)
ck.column_dimensions["A"].width = 86
ck.column_dimensions["B"].width = 18
ck.column_dimensions["C"].width = 12

# sheet order
order = ["Cover", "Assumptions", "Model", "Q3_Forecast", "Margin_Bridge", "Sensitivity", "Scenarios", "Peers",
         "Charts", "Hist", "Checks"]
wb._sheets = [wb[n] for n in order]
for ws in wb.worksheets:
    ws.sheet_view.showGridLines = False

# where run_model.py writes saved values
LAYOUT = {
    "q3_rows": F3ROW, "q3_col": "D", "sc_rows": SCROW, "model_rows": MR, "mcol": MCOL,
    "sens_needed": SENS_NEEDED, "sens_needed_ck": SENS_NEEDED_CK, "q3_implied": F3_IMPLIED,
    "levers": LEVER_ROWS,
}


def build(path=OUT):
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.properties.creator = "Likhit Vardhan Chiliveri"
    wb.properties.lastModifiedBy = "Likhit Vardhan Chiliveri"
    wb.properties.title = "Chipotle FP&A model"
    wb.save(path)
    return path


if __name__ == "__main__":
    print(build())
