# Memo: what to plan for in Chipotle's 2027 restaurant margin

**To:** CFO (hypothetical; this is an independent exercise using public filings)
**From:** Likhit Vardhan Chiliveri, FP&A
**Re:** 2027 budget, restaurant-level margin
**Model:** [`model/chipotle_fpa_model.xlsx`](../model/chipotle_fpa_model.xlsx)

### Update after Q3 results (Oct 30)

Q3 came in as forecast at the margin line (23.3% vs my 23.4%), but the mix
underneath changed: traffic recovered, and promotions ate more of the price
than I expected. After rolling the model forward, the Base case for 2027 is
**22.4%**, down from 23.1% in the memo below. Management called a mid-24%
margin the 2027 baseline, but that assumes pricing keeps up with ~3% cost
inflation, and on the same call they said 2% pricing looks unlikely. The
recommendations below still stand. The case for testing price has got
stronger, and other operating costs (16.0% of sales in Q3) are now the
clearest place to look for savings. Details: [`q3_2026_variance.md`](q3_2026_variance.md)
and the README's reforecast section.

The memo as written on Oct 15 follows.

### Bottom line

Plan 2027 restaurant-level margin at **about 23%**, not a return to the 26-27%
of 2023-24. Price is the only lever big enough to close the gap on its own, so
the budget question is really how much price we're willing to take while
traffic is still fragile.

### Where we are

- Restaurant-level margin fell from 26.7% in 2024 to 25.4% in 2025, and was
  24.3% in the first half of 2026 (26.8% a year earlier).
- In Q2 2026, margin was 2.1 points lower than a year earlier. Other operating
  costs (the line that holds marketing and delivery fees) took 93 bps, food
  75 bps (mainly beef and freight), labor 29 bps and occupancy 17 bps.
- Same-store traffic fell in all four quarters of 2025 and is only now flat to
  slightly positive. We have kept price increases to about 1.5-2.5%, below the
  3.5% that restaurant prices rose nationally in the last year (CPI, food away
  from home).

### What the model says for 2027

| Scenario | Comps | Restaurant margin | Diluted EPS |
|---|---|---|---|
| Upside | +5.6% | 24.9% | $1.45 |
| **Base** | **+3.3%** | **23.1%** | **$1.23** |
| Downside | 0.0% | 20.1% | $0.91 |

In the Base case margin slips about half a point from 2026 (23.6%) even with comps
back above 3%. Wage, rent and marketing costs per restaurant are growing faster
than sales per restaurant, and every year's new restaurants open below the
system average (about 1.3 points off revenue per restaurant). EPS still grows,
helped by 8% more restaurants and buybacks.

### Which lever matters most

Effect on 2027 margin of a one-point move, Base case:

| Lever | Margin effect |
|---|---|
| Average check (price) +1 pt | +75 bps |
| Food cost inflation -1 pt | +29 bps |
| Wage inflation -1 pt | +25 bps |
| Traffic +1 pt | +24 bps |

To get back to 2025's 25.4% margin we would need check growth of about 5.3%
(vs 2.0% in the Base case) or traffic growth of about 12%, which is not
realistic. A point of price is worth three points of traffic, so price stays
margin-positive unless each point of it costs more than about three points of
traffic. That is the trade to test.

### Recommendations

1. **Budget at ~23% margin and say so early.** A plan that assumes 2024-level
   margins will miss.
2. **Test one extra point of price in a few markets** before rolling it out,
   and track transactions weekly in those markets against control markets.
3. **Go after other operating costs.** They did the most damage this year.
   Ask for a return-on-spend review of the marketing step-up and the delivery
   fee mix before the 2027 marketing budget is set.
4. **Lock in beef.** Food cost is the second-biggest lever; longer contracts
   reduce the risk of the downside case.
5. **Report these monthly:** transactions, average check, food cost per
   transaction, labor hours per restaurant, other operating cost per
   restaurant, and the new-restaurant gap. Definitions are in
   [`docs/kpi_tree.md`](kpi_tree.md).

*Caveats: built only from public filings and management commentary. The
lever effects assume the other drivers stay put; in practice a price increase
would also move traffic.*
