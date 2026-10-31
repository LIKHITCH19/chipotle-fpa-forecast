# Q3 2026: forecast vs actual

Chipotle reported Q3 2026 on October 28. This compares the results with the
forecast I made on October 15 ([`q3_2026_forecast.md`](q3_2026_forecast.md)).
Numbers come from `src/score_forecast.py` and
[`output/q3_2026_variance.csv`](../output/q3_2026_variance.csv); the reasons
come from Chipotle's earnings release and the Q3 call
([my notes](sources/q3_2026_call_notes.md)).

## Summary

The headline numbers were close. Revenue came in 0.9% above my forecast,
restaurant-level margin was 7 bps lower (23.3% vs 23.4%), and EPS was $0.27,
as forecast. The restaurant count was exactly right (4,267), so the whole
$30.4M revenue gap came from sales per restaurant.

The margin was right partly for the wrong reasons. Traffic was much better
than I expected and average check was weaker. Food cost came in 40 bps better
than forecast, other operating costs 39 bps worse, and the two cancelled out.

## Line by line

| Line | Forecast | Actual | Variance | Why |
|---|---|---|---|---|
| Comparable sales | +1.0% | +2.1% | +112 bps | Traffic beat, check missed (below) |
| Transactions | -1.1% | +0.8% | +190 bps | Third positive quarter in a row. I assumed the cyclospora hit from July would keep traffic negative; it didn't |
| Average check | +2.1% | +1.3% | -80 bps | Price was 2.7%, in line with the "mid-2%" guide, but promotions and mix took off about 1.4 points. I had assumed 0.4 |
| Restaurants opened | 85 | 84 | -1 | |
| Restaurants at end of quarter | 4,267 | 4,267 | 0 | |
| Revenue | $3,262.8M | $3,293.2M | +0.9% | All from sales per restaurant |
| Food, beverage and packaging | 29.9% | 29.5% | -40 bps (better) | Chipotle credits menu price, tariff relief and a favourable limited-time-offer mix. Tariff relief wasn't in my assumptions |
| Labor | 25.6% | 25.7% | +13 bps (worse) | Extra hours to support promotions, wage inflation, bonuses and insurance costs |
| Occupancy | 5.5% | 5.4% | -5 bps (better) | More sales over the same rent |
| Other operating costs | 15.6% | 16.0% | +39 bps (worse) | Marketing, delivery mix, utilities and maintenance. Came in above management's own "mid-15%" guide |
| Restaurant-level margin | 23.4% | 23.3% | -7 bps | Food and other operating gaps nearly offset |
| G&A (GAAP) | $190.0M | $185.2M | -2.5% | I added $10M on top of the ~$180M non-GAAP guide for one-off items. The one-offs were only $1.5M, but adjusted G&A ($183.8M) ran above the guide |
| Income from operations | $451.4M | $452.0M | +0.1% | |
| Operating margin | 13.8% | 13.7% | -11 bps | |
| Net income | $344.2M | $339.9M | -1.3% | Interest income $5.2M vs my $7.5M, and a 25.6% tax rate vs my 25% |
| Diluted EPS | $0.272 | $0.268 | -$0.004 | Both round to $0.27 |

Management's own Q3 cost guidance implied a margin of about 23.6%. The actual
was 23.3%, so the driver model was closer than a straight read of the guidance.

## Driver model vs a statistical forecast

To check whether the driver model added anything, I compared it with two
forecasts that only look at past quarters (`src/baseline_forecast.py`):

| Method | Revenue | Error | Restaurant margin | Error |
|---|---|---|---|---|
| Driver model (Oct 15) | $3,262.8M | -0.9% | 23.4% | +7 bps |
| Holt-Winters | $3,255.4M | -1.1% | 23.6% | +24 bps |
| Seasonal naive | $3,223.0M | -2.1% | 24.5% | +117 bps |
| Actual | $3,293.2M | | 23.3% | |

The driver model was the most accurate on both. The margin is where it
mattered: a forecast that only follows the trend can't see a marketing
step-up or a promotion coming. Two caveats. This is one quarter, and the
baselines were built on Oct 30, after the results, although they only use
data through Q2 2026.

## What I changed for the reforecast

1. **Split average check into price and mix.** I treated mix as a steady
   -0.4 points. In Q3 it was about -1.4 because of promotions. Q4 now assumes
   price of ~3% (management's number) less about 1 point of mix.
2. **Other operating costs keep growing faster than sales for now.** Marketing
   stays in the high-3% range of sales in Q4, so I raised Q4 growth per
   restaurant to 6% before it slows in 2027.
3. **Traffic is no longer negative.** Q4 is flat (October softened, per
   management), and 2027 assumes +1.5% a quarter.

The new numbers are in the README under "Reforecast after Q3".
