"""Static charts for the README (images/*.png).

Reads the processed data and the model outputs written by run_model.py.
"""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROC, OUT, IMG = ROOT / "data" / "processed", ROOT / "output", ROOT / "images"
IMG.mkdir(exist_ok=True)

# palette (validated categorical order: blue, orange, aqua) and chart chrome
BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
NEUTRAL = "#52514e"
SOURCE = "Source: Chipotle 10-Q/10-K filings and earnings releases (SEC EDGAR); forecast from model/chipotle_fpa_model.xlsx."

family = next((f for f in ("Inter", "Arial", "Helvetica", "DejaVu Sans")
               if any(f == x.name for x in font_manager.fontManager.ttflist)), "DejaVu Sans")
plt.rcParams.update({
    "font.family": family, "font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.titlelocation": "left",
})


def finish(fig, name, source=SOURCE):
    fig.text(0.01, -0.03, source, fontsize=7.5, color=MUTED, ha="left", va="top")
    fig.savefig(IMG / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("images/" + name)


def qlab(q):
    return f"Q{q[-1]} '{q[2:4]}"


pnl = pd.read_csv(PROC / "cmg_pnl_quarterly.csv").set_index("quarter")
units = pd.read_csv(PROC / "cmg_units_quarterly.csv").set_index("quarter")
split = pd.read_csv(PROC / "cmg_comps_split.csv").set_index("quarter")
mq = pd.read_csv(OUT / "model_quarterly.csv")
levers = pd.read_csv(OUT / "levers.csv", nrows=12)
peers = pd.read_csv(PROC / "peers_ltm.csv")

# ---------------------------------------------------------------- 1. margin trend
hist = (1 - (pnl.food_bev_packaging + pnl.labor + pnl.occupancy + pnl.other_operating) / pnl.revenue)
fc = mq[mq.type == "forecast"]
quarters = list(hist.index) + list(fc[fc.scenario == "Base"].quarter)
x = {q: i for i, q in enumerate(quarters)}
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot([x[q] for q in hist.index], hist.values * 100, color=INK2, lw=2, label="Actual")
last = hist.index[-1]
ends = {}
for name, color in [("Upside", AQUA), ("Base", BLUE), ("Downside", ORANGE)]:
    s = fc[fc.scenario == name]
    xs = [x[last]] + [x[q] for q in s.quarter]
    ys = [hist[last] * 100] + list(s.rlm * 100)
    ax.plot(xs, ys, color=color, lw=2, ls="--" if name == "Base" else "-", label=f"{name} forecast")
    ends[name] = (xs[-1], ys[-1], color)
order = sorted(ends.items(), key=lambda kv: -kv[1][1])
for k, (name, (xe, ye, color)) in enumerate(order):
    ax.annotate(f"{name} {ye:.1f}%", (xe, ye), xytext=(8, 0), textcoords="offset points", va="center",
                fontsize=9, color=INK)
peak = hist.idxmax()
ax.annotate(f"Peak {hist[peak] * 100:.1f}%\n{qlab(peak)}", (x[peak], hist[peak] * 100), xytext=(0, 10),
            textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.axvspan(x[last] + 0.5, len(quarters) - 0.5, color="#f0efec", zorder=0)
ax.text(x[last] + 0.8, 29.6, "Forecast", fontsize=8.5, color=MUTED)
ticks = [q for q in quarters if q.endswith("Q1") or q.endswith("Q3")]
ax.set_xticks([x[q] for q in ticks], [qlab(q) for q in ticks], fontsize=8.5)
ax.set_xlim(-0.5, len(quarters) + 2.5)
ax.set_ylim(17, 30.5)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_title("Restaurant-level margin by quarter: actual and forecast", pad=22)
ax.text(0, 1.02, "Labels at the right are Q4 2027. Margin is seasonal: Q2 is always the high point.",
        transform=ax.transAxes, fontsize=9, color=INK2)
ax.legend(loc="lower left", frameon=False, fontsize=8.5, ncol=4)
finish(fig, "margin_trend.png")

# ---------------------------------------------------------------- 2. margin bridge
q0, q1 = "2025Q2", "2026Q2"
pct = lambda q, c: pnl.at[q, c] / pnl.at[q, "revenue"] * 100
start, end = hist[q0] * 100, hist[q1] * 100
steps = [("Food &\npackaging", -(pct(q1, "food_bev_packaging") - pct(q0, "food_bev_packaging"))),
         ("Labor", -(pct(q1, "labor") - pct(q0, "labor"))),
         ("Occupancy", -(pct(q1, "occupancy") - pct(q0, "occupancy"))),
         ("Other\noperating", -(pct(q1, "other_operating") - pct(q0, "other_operating")))]
fig, ax = plt.subplots(figsize=(8.5, 4.4))
labels = ["Q2 2025"] + [s[0] for s in steps] + ["Q2 2026"]
level = start
ax.bar(0, start, color=NEUTRAL, width=0.6)
ax.text(0, start + 0.08, f"{start:.1f}%", ha="center", va="bottom", fontsize=10, color=INK, fontweight="bold")
for i, (lab, d) in enumerate(steps, start=1):
    bottom = min(level, level + d)
    ax.bar(i, abs(d), bottom=bottom, color=RED if d < 0 else BLUE, width=0.6)
    ax.text(i, bottom - 0.08, f"{d * 100:+.0f} bps", ha="center", va="top", fontsize=9.5, color=INK)
    ax.plot([i - 0.7, i + 0.3], [level, level], color=AXIS, lw=0.8)
    level += d
ax.bar(5, end, color=NEUTRAL, width=0.6)
ax.text(5, end + 0.08, f"{end:.1f}%", ha="center", va="bottom", fontsize=10, color=INK, fontweight="bold")
ax.set_xticks(range(6), labels, fontsize=9)
ax.set_ylim(24, 28)
ax.set_yticks([24, 25, 26, 27, 28])
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_title("What took 2.1 points off Chipotle's restaurant margin (Q2 2025 to Q2 2026)", pad=12)
ax.grid(axis="x", visible=False)
finish(fig, "margin_bridge.png", "Source: Chipotle Q2 2025 and Q2 2026 10-Q filings. Each bar is the change in that "
       "cost line as a share of revenue.")

# ---------------------------------------------------------------- 3. levers
b = levers[levers.scenario == "Base"].sort_values("fy2027_margin_change_bps")
fig, ax = plt.subplots(figsize=(8.5, 3.4))
names = {"Transactions growth +1 pt": "Traffic (transactions) +1 pt", "Average check (price) +1 pt": "Price (average check) +1 pt",
         "Food cost inflation -1 pt": "Food cost inflation -1 pt", "Wage inflation -1 pt": "Wage inflation -1 pt"}
ys = range(len(b))
ax.barh(list(ys), b.fy2027_margin_change_bps, color=BLUE, height=0.55)
for y, v in zip(ys, b.fy2027_margin_change_bps):
    ax.text(v + 1, y, f"+{v:.0f} bps", va="center", fontsize=10, color=INK)
ax.set_yticks(list(ys), [names[n] for n in b.lever], fontsize=10, color=INK)
ax.set_xlim(0, 90)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}")
ax.set_xlabel("Change in FY2027E restaurant-level margin (bps), Base case", fontsize=9)
ax.grid(axis="y", visible=False)
ax.set_title("One point of price is worth three points of traffic", pad=12)
finish(fig, "levers.png", "Source: Sensitivity tab of model/chipotle_fpa_model.xlsx. Price assumes traffic does not "
       "change in response.")

# ---------------------------------------------------------------- 4. traffic vs check
sq = list(split.index)
fig, ax = plt.subplots(figsize=(9.5, 4))
w = 0.38
xs = range(len(sq))
ax.bar([i - w / 2 - 0.01 for i in xs], split.transactions_pct, width=w, color=BLUE, label="Transactions")
ax.bar([i + w / 2 + 0.01 for i in xs], split.avg_check_pct, width=w, color=ORANGE, label="Average check")
comps = units.loc[sq, "comp_sales_pct"]
ax.scatter(list(xs), comps, color=INK, s=22, zorder=3, label="Comparable sales")
for i, v in zip(xs, comps):
    ax.annotate(f"{v:+.1f}%", (i, max(v, split.transactions_pct.iloc[i], split.avg_check_pct.iloc[i])),
                xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8, color=INK)
ax.axhline(0, color=AXIS, lw=1)
ax.set_xticks(list(xs), [qlab(q) for q in sq], fontsize=8.5)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_ylim(-6.5, 13)
ax.grid(axis="x", visible=False)
ax.legend(loc="upper right", frameon=False, fontsize=8.5, ncol=3)
ax.set_title("Same-store sales: traffic fell through 2025 while price growth stayed low", pad=12)
finish(fig, "traffic_vs_check.png", "Source: Chipotle earnings releases. Chipotle has split comparable sales into "
       "transactions and check only since Q4 2023.")

# ---------------------------------------------------------------- 5. peers
pr = peers.copy()
pr["growth"] = (pr.revenue / pr.revenue_prior_ltm - 1) * 100
pr["rlm"] = (1 - pr.restaurant_costs_total / pr.revenue) * 100
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
for ax, col, ttl in [(axes[0], "growth", "Revenue growth, last 12 months"),
                     (axes[1], "rlm", "Restaurant-level margin, last 12 months")]:
    d = pr.dropna(subset=[col]).sort_values(col)
    colors = [BLUE if t == "CMG" else "#b7b5ad" for t in d.ticker]
    ax.barh(d.company, d[col], color=colors, height=0.55)
    for y, v in enumerate(d[col]):
        ax.text(max(v, 0) + 0.6, y, f"{v:.1f}%", va="center", ha="left", fontsize=9.5, color=INK)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_title(ttl, fontsize=11, pad=8)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    lo = min(0, d[col].min()) - 4
    ax.set_xlim(lo, d[col].max() + 8)
fig.tight_layout()
finish(fig, "peers.png", "Source: SEC XBRL filings, LTM to mid-2026. Margin rebuilt as revenue less food, labor, "
       "occupancy and other restaurant costs. Shake Shack's margin can't be rebuilt from its tagged data, and its "
       "LTM includes a 53rd week.")
