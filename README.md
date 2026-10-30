# Chipotle: 2027 margin budget and a Q3 2026 forecast

Work in progress. An FP&A-style look at Chipotle (CMG) built from its public
SEC filings: a driver-based 2027 budget for restaurant-level margin, and a Q3
2026 forecast to check against the actual results.

Independent analysis; not affiliated with Chipotle and not investment advice.

## Q3 2026 scorecard

| | My forecast | Chipotle's guidance | Actual | Variance |
|---|---|---|---|---|
| Comparable sales | +1.0% | about +1% | *Oct 28* | |
| Revenue | $3,263M | | | |
| Restaurant-level margin | 23.4% | ~23.6% implied | | |
| Diluted EPS | $0.27 | | | |

Reasoning: [`docs/q3_2026_forecast.md`](docs/q3_2026_forecast.md).

## Data

`src/fetch_data.py` downloads Chipotle's 10-Q/10-K XBRL facts and quarterly
earnings releases from SEC EDGAR, the same for a few fast-casual peers, and
restaurant wage, beef and menu-price series from the BLS API.

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env            # add your name and email; the SEC requires it
.venv/bin/python src/fetch_data.py
```
