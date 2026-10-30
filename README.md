# Chipotle: 2027 margin budget and a Q3 2026 forecast

Work in progress. An FP&A-style look at Chipotle (CMG) built from its public
SEC filings: a driver-based 2027 budget for restaurant-level margin, and a Q3
2026 forecast to check against the actual results.

Independent analysis; not affiliated with Chipotle and not investment advice.

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
