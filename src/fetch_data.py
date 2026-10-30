"""Pull the raw inputs for the Chipotle model.

Sources
- SEC EDGAR: XBRL company facts and filing lists for Chipotle and a few
  fast-casual peers, plus Chipotle's 10-Q/10-K documents and the earnings
  press releases (8-K item 2.02, exhibit 99) since 2021. The press releases
  are the only place transactions and average check are broken out.
- BLS (public API, no key needed): restaurant wages, ground beef prices and
  menu price indexes, used as cost and pricing drivers.

Everything lands in data/raw/ untouched, and data/raw/download_log.csv
records where each file came from.

Run from the project folder:  .venv/bin/python src/fetch_data.py
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

COMPANY = "CMG"
PEERS = ["CAVA", "SG", "SHAK", "WING"]
FIRST_YEAR = 2021

# BLS series ids. Any id the API doesn't recognise is reported and skipped.
BLS_SERIES = {
    "CES7072200003": "Avg hourly earnings, all employees, food services and drinking places",
    "CES7072200008": "Avg hourly earnings, production/nonsupervisory, food services and drinking places",
    "APU0000703112": "Avg retail price, ground beef 100% beef, per lb",
    "CUSR0000SEFV": "CPI, food away from home (SA)",
    "CUSR0000SAF11": "CPI, food at home (SA)",
}

log_rows = []


def read_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def log(dest, url, when=None):
    when = when or datetime.now(timezone.utc)
    log_rows.append({
        "file": dest.relative_to(ROOT).as_posix(),
        "url": url,
        "bytes": dest.stat().st_size,
        "downloaded_utc": when.strftime("%Y-%m-%d %H:%M:%S"),
    })


def fetch(session, url, dest, pause=0.15):
    """Download url to dest unless it is already there. Returns the bytes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        mtime = datetime.fromtimestamp(dest.stat().st_mtime, timezone.utc)
        log(dest, url, mtime)
        return dest.read_bytes()
    resp = None
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=30)
        except requests.RequestException as err:
            print(f"  network error ({type(err).__name__}), retrying: {url}")
            time.sleep(3)
            continue
        time.sleep(pause)  # SEC allows 10 requests a second; stay well under
        if resp.status_code == 200:
            dest.write_bytes(resp.content)
            log(dest, url)
            return resp.content
        if resp.status_code in (429, 503):
            time.sleep(5 * (attempt + 1))
            continue
        break
    print(f"  skipped ({resp.status_code if resp is not None else 'no response'}): {url}")
    if resp.status_code == 403 and "sec.gov" in url:
        print("  The SEC refused the request. It usually means it did not accept")
        print("  the SEC_USER_AGENT line in .env (name plus a working email).")
    return None


def sec_session():
    agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not agent or "example.com" in agent:
        sys.exit("Set SEC_USER_AGENT in .env first (see .env.example).")
    s = requests.Session()
    s.headers.update({"User-Agent": agent, "Accept-Encoding": "gzip, deflate"})
    return s


def ticker_to_cik(session):
    raw = fetch(session, "https://www.sec.gov/files/company_tickers.json",
                RAW / "sec" / "company_tickers.json")
    if raw is None:
        sys.exit("Could not get the SEC ticker list, stopping.")
    table = json.loads(raw)
    return {row["ticker"]: int(row["cik_str"]) for row in table.values()}


def filings_since(submissions, year):
    recent = submissions["filings"]["recent"]
    keys = list(recent.keys())
    for i in range(len(recent["accessionNumber"])):
        row = {k: recent[k][i] for k in keys}
        if row["filingDate"][:4] >= str(year):
            yield row


def pull_company(session, ticker, cik, with_documents):
    cik10 = f"{cik:010d}"
    print(f"{ticker} (CIK {cik})")
    fetch(session, f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json",
          RAW / "sec" / f"companyfacts_{ticker}.json")
    subs_raw = fetch(session, f"https://data.sec.gov/submissions/CIK{cik10}.json",
                     RAW / "sec" / f"submissions_{ticker}.json")
    if not with_documents or subs_raw is None:
        return

    folder = RAW / "sec" / "filings" / ticker
    for f in filings_since(json.loads(subs_raw), FIRST_YEAR):
        acc = f["accessionNumber"].replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}"
        if f["form"] in ("10-Q", "10-K"):
            name = f"{f['form']}_{f['reportDate']}_{f['primaryDocument']}"
            fetch(session, f"{base}/{f['primaryDocument']}", folder / name)
        elif f["form"] == "8-K" and "2.02" in (f.get("items") or ""):
            index = fetch(session, f"{base}/index.json",
                          folder / "_index" / f"{acc}.json")
            if index is None:
                continue
            for item in json.loads(index)["directory"]["item"]:
                doc = item["name"].lower()
                if "99" in doc and doc.endswith((".htm", ".html")):
                    fetch(session, f"{base}/{item['name']}",
                          folder / f"8-K_{f['filingDate']}_{item['name']}")


def pull_bls():
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    body = {"seriesid": list(BLS_SERIES), "startyear": "2019", "endyear": "2026"}
    dest = RAW / "bls" / "bls_series.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.post(url, json=body, timeout=60)
    except requests.RequestException as err:
        print(f"  BLS request failed ({type(err).__name__}); rerun later for this part")
        return
    data = resp.json()
    if data.get("status") != "REQUEST_SUCCEEDED":
        print(f"  BLS said: {data.get('status')} {data.get('message')}")
        return
    dest.write_text(json.dumps(data, indent=1))
    log(dest, url + " (POST " + ",".join(BLS_SERIES) + ")")
    for series in data["Results"]["series"]:
        print(f"  {series['seriesID']}: {len(series['data'])} months")


def write_log():
    path = RAW / "download_log.csv"
    old = []
    if path.exists():
        with path.open(newline="") as fh:
            old = list(csv.DictReader(fh))
    seen = {r["file"] for r in log_rows}
    rows = [r for r in old if r["file"] not in seen] + log_rows
    rows.sort(key=lambda r: r["file"])
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["file", "url", "bytes", "downloaded_utc"])
        writer.writeheader()
        writer.writerows(rows)


def main():
    read_env()
    session = sec_session()
    ciks = ticker_to_cik(session)
    for ticker in [COMPANY] + PEERS:
        if ticker not in ciks:
            print(f"{ticker}: not in the SEC ticker list, skipped")
            continue
        pull_company(session, ticker, ciks[ticker], with_documents=(ticker == COMPANY))
    write_log()  # save progress before the BLS step
    print("BLS")
    pull_bls()
    write_log()
    files = [p for p in RAW.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files) / 1e6
    print(f"Done: {len(files)} files, {size:.1f} MB in data/raw/")


if __name__ == "__main__":
    main()
