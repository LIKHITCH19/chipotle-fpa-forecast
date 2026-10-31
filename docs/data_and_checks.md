# Data sources and checks

## Where the numbers come from

| Data | Source | Coverage | Used for |
|---|---|---|---|
| Chipotle income statement | SEC EDGAR XBRL company facts (10-Q and 10-K) | Q1 2021 - Q3 2026 | `Hist`, `Model` actuals |
| Restaurant openings, closures, count, average restaurant sales, comparable sales | Unit table in each quarterly earnings release (8-K, exhibit 99.1) | Q4 2019 - Q3 2026 | `Hist`, revenue drivers |
| Transactions and average check | Text of each earnings release | Q4 2023 - Q3 2026 (not split out before that) | `Hist`, sales drivers |
| Restaurant-level margin as Chipotle reports it | Earnings releases | 22 quarters | Checking my own calculation |
| CAVA, Sweetgreen, Shake Shack | SEC EDGAR XBRL company facts | Last twelve months to mid-2026 (Chipotle to Sep 2026) | `Peers` |
| Restaurant wages, ground beef price, menu prices | Bureau of Labor Statistics API (series CES7072200003, CES7072200008, APU0000703112, CUSR0000SEFV, CUSR0000SAF11) | 2019 - Sep 2026 | Setting cost assumptions |
| Management guidance for Q3 2026 | Chipotle Q2 2026 earnings call, Jul 29, 2026 | | Comparing my Q3 forecast |
| Management guidance for Q4 2026 and 2027 | Chipotle Q3 2026 earnings call, Oct 28, 2026 ([notes](sources/q3_2026_call_notes.md)) | | The reforecast |

`src/fetch_data.py` downloads everything and records each file's URL and
download time in `data/raw/download_log.csv`. The raw files (about 75 MB) are not
in the repo; run the script to get them.

## Two things that need handling

- **Q4 is never filed on its own.** The 10-K only has full-year numbers, so Q4 =
  full year minus Q1 to Q3. Every derived Q4 is then checked against the Q4
  earnings release.
- **The June 2024 stock split.** Chipotle split its shares 50-for-1. Share counts
  in older filings are multiplied by 50 so EPS is comparable across the whole
  history.

## Checks

`src/check_data.py` runs 468 checks on the processed data. All pass.

| Check | Count | What it tests |
|---|---|---|
| Filed numbers vs the earnings release | 362 | Every income statement line, every quarter, matches the release within $5K (the only gaps are $2K of rounding in Q4 2024) |
| Costs add up | 23 | The cost lines sum to total operating expenses |
| Revenue less costs | 23 | Revenue minus total expenses equals operating income |
| Restaurant roll-forward | 27 | Last quarter's count + openings - closures - relocations = this quarter's count, exactly |
| Comps = transactions + check | 12 | The split adds back to reported comps (within rounding) |
| My margin vs Chipotle's | 21 | Restaurant-level margin calculated from the cost lines matches the margin Chipotle states, within 0.05 points |

The workbook has its own `Checks` tab (14 checks) covering the same ties plus
the forecast logic: restaurants roll forward, revenue equals restaurants times
revenue per restaurant, full years equal the sum of their quarters, and the
margin bridges add up.

For the Oct 15 budget I also rebuilt the Base-case forecast separately in
Python and compared it to the Excel results. They matched to the last decimal.

## Limitations

- **Company-level only.** No store, region or menu-item data is public, so the
  model works at the level an FP&A team would use for the top-down budget.
- **Traffic and check split only since Q4 2023.** Before that, Chipotle
  described the split in words but didn't give numbers.
- **Cost drivers are inferred.** Chipotle doesn't publish its own wage or food
  inflation. Assumptions start from what management said and from cost
  increases backed out of the filings, and BLS data gives the outside view.
- **Peers aren't perfectly comparable.** Fiscal calendars differ, Sweetgreen only
  tags total restaurant costs, Shake Shack's food cost isn't in its standard
  tags and its revenue includes licensing, and Wingstop is left out because it's
  almost entirely franchised.
- **Lever effects are one at a time.** In real life a price increase also moves
  traffic. The sensitivity tables show each lever with everything else held
  still.
