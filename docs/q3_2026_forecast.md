# Q3 2026 forecast (locked before the results)

Chipotle reports Q3 2026 on **October 28, 2026**. This is my forecast for the
quarter, made from the Base case of the model and saved in
[`output/q3_2026_forecast_locked.csv`](../output/q3_2026_forecast_locked.csv)
on Oct 15, before the release. The same numbers went up on Tableau Public on
Oct 16 (the dashboard's publish date is the outside record). Once the actual
numbers are out, they go next to it in the `Q3_Forecast` tab of the workbook and
in the scorecard below. I won't change the forecast after that.

## The forecast

| Line | My forecast | What management said on Jul 29 | Actual |
|---|---|---|---|
| Comparable sales | +1.0% | "somewhere around a plus 1%" | |
| Transactions | -1.1% | | |
| Average check | +2.1% | menu price "mid-2% range" | |
| Restaurants opened | 85 | ~350 for the year | |
| Restaurants at end of quarter | 4,267 | | |
| Revenue | $3,263M (+8.6% y/y) | | |
| Food, beverage and packaging | 29.9% of revenue | "just under 30%" | |
| Labor | 25.6% | "mid-25% range" | |
| Occupancy | 5.5% | not guided | |
| Other operating costs | 15.6% | "mid-15% range" | |
| Restaurant-level margin | 23.4% | about 23.6% implied | |
| G&A (GAAP) | $190M | ~$180M non-GAAP | |
| Operating margin | 13.8% | | |
| Diluted EPS | $0.27 | | |

## How I got there

**Sales.** Management expects comps of about +1%, which already assumes the
roughly 200 bps hit from the cyclospora issue carries through the quarter. With
menu price in the mid-2% range and the usual ~0.4 points of negative mix
(Q2 had 1.6% price and 1.2% check), average check comes out at +2.1%. That leaves
transactions at about -1.1%. Revenue is restaurants times revenue per restaurant:
about 4,227 average restaurants in the quarter, each doing about $772K, which is
Q3 2025's level plus comps, less the ~1.3 points that new restaurants always
take off the average (see the `Hist` tab).

**Costs.** Each cost line starts from the same quarter last year and is moved by
cost inflation, price and volume:

- Food: +1.7% cost inflation per transaction (beef is up 7.4% y/y at retail,
  partly offset by cheaper avocados and dairy), against +2.1% check. That lands at
  29.9%, which matches "just under 30%".
- Labor: 2.5% wage inflation. Half of the hours are treated as fixed, so falling
  transactions push the percentage up. I land at 25.6%, a little above
  management's "mid-25%", because I don't think they get as much productivity on
  negative traffic.
- Other operating: up 5% per restaurant (marketing has been stepped up all year),
  which gives 15.6%.

**Below the restaurant line.** G&A of $190M (the $180M non-GAAP guide plus the
legal, restructuring and retention costs that sit in GAAP G&A; they were $14M in
Q2 2026), D&A at 3.0% of revenue, a 25% tax rate and another 1.2% off
the share count from buybacks.

## What would make me wrong

- **Traffic.** Every point of transactions is worth about $33M of revenue in the
  quarter. If the late-July softness got worse, comps could be flat or negative.
- **Labor.** If labor comes in at 25.5%, the middle of Chipotle's "mid-25%"
  guide, margin is about 10 bps higher than my forecast.
- **One-off G&A.** Items that Chipotle strips out of adjusted G&A added $12M in
  Q2 2025 and $14M in Q2 2026. A swing of that size is about $0.01 of EPS.

## Scorecard (filled in after October 28)

| | Forecast | Actual | Variance | Main reason |
|---|---|---|---|---|
| Revenue | $3,263M | | | |
| Comparable sales | +1.0% | | | |
| Restaurant-level margin | 23.4% | | | |
| Diluted EPS | $0.27 | | | |
