"""Build, recalculate and finish the Excel model.

1. Builds the workbook (src/build_model.py).
2. Recalculates it once per scenario in LibreOffice and saves each scenario's
   outputs on the Scenarios tab.
3. Saves the Base-case Q3 2026 forecast as fixed values on Q3_Forecast, and
   also as output/q3_2026_forecast_locked.csv.
4. Writes output/model_quarterly.csv, output/scenarios.csv and output/levers.csv
   for the charts and the dashboard.

Needs LibreOffice (soffice) on the PATH. Usage:
    python src/run_model.py           # rebuild; keeps the locked Q3 forecast if one is saved
    python src/run_model.py --relock  # overwrite the locked Q3 forecast with the current Base case
"""
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_model as bm  # noqa: E402

ROOT = bm.ROOT
OUTDIR = ROOT / "output"
LOCK_FILE = OUTDIR / "q3_2026_forecast_locked.csv"
RECALC = Path(__file__).resolve().parent / "recalc.py"


def recalc(path):
    res = subprocess.run([sys.executable, str(RECALC), str(path), "120"], capture_output=True, text=True)
    out = json.loads(res.stdout)
    if out.get("status") != "success":
        raise SystemExit(f"Recalculation problem in {path.name}: {out}")
    return out


def values(path):
    return load_workbook(path, data_only=True)


def run_scenarios():
    results = {}
    tmp = Path(tempfile.mkdtemp())
    for k, name in [(1, "Base"), (2, "Upside"), (3, "Downside")]:
        bm.wb["Assumptions"]["C4"] = k
        p = bm.build(tmp / f"scenario_{k}.xlsx")
        recalc(p)
        wb = values(p)
        sc, q3, model = wb["Scenarios"], wb["Q3_Forecast"], wb["Model"]
        results[name] = {
            "scenarios": {lab: sc[f"B{r}"].value for lab, r in bm.LAYOUT["sc_rows"].items()},
            "q3": {key: q3[f"C{r}"].value for key, r in bm.LAYOUT["q3_rows"].items()},
            "quarters": [
                {"quarter": q, "scenario": name,
                 **{key: model[f"{bm.MCOL[q]}{bm.MR[key]}"].value
                    for key in ["opened", "rest_end", "avg_rest", "tx", "check", "comps", "rpr", "rev2", "food_pct",
                                "labor_pct", "occ_pct", "oth_pct", "rlm", "rlp", "ga", "oi", "opm", "ni", "eps"]},
                 "type": "forecast" if q in bm.FCST_Q else "actual"}
                for q in bm.MODEL_Q],
            "needed_tx": wb["Sensitivity"][bm.LAYOUT["sens_needed"]].value,
            "needed_ck": wb["Sensitivity"][bm.LAYOUT["sens_needed_ck"]].value,
            "levers": {wb["Sensitivity"][f"A{r}"].value: wb["Sensitivity"][f"C{r}"].value
                       for r in range(bm.LAYOUT["levers"][0], bm.LAYOUT["levers"][1] + 1)},
        }
    shutil.rmtree(tmp)
    return results


def read_lock():
    with open(LOCK_FILE) as fh:
        return {row["key"]: float(row["value"]) for row in csv.DictReader(fh)}


def main():
    keep_lock = "--relock" not in sys.argv
    OUTDIR.mkdir(exist_ok=True)
    res = run_scenarios()

    # scenario snapshot
    sc = bm.wb["Scenarios"]
    for lab, r in bm.LAYOUT["sc_rows"].items():
        for col, name in zip("CDE", ["Base", "Upside", "Downside"]):
            sc[f"{col}{r}"] = res[name]["scenarios"][lab]
    sc["A3"] = f"Saved {date.today().isoformat()} by src/run_model.py."

    # locked Q3 forecast
    if keep_lock and LOCK_FILE.exists():
        lock = read_lock()
    else:
        lock = res["Base"]["q3"]
        with open(LOCK_FILE, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["key", "label", "value"])
            labels = {key: lab for lab, _, key, _, _ in bm.F3}
            for key, v in lock.items():
                w.writerow([key, labels[key], repr(v)])
    q3 = bm.wb["Q3_Forecast"]
    for key, r in bm.LAYOUT["q3_rows"].items():
        q3[f"D{r}"] = lock[key]

    bm.wb["Assumptions"]["C4"] = 1
    final = bm.build()
    out = recalc(final)

    # dashboard extracts
    rows = [row for name in ("Base", "Upside", "Downside") for row in res[name]["quarters"]]
    with open(OUTDIR / "model_quarterly.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(OUTDIR / "scenarios.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["output", "Base", "Upside", "Downside"])
        for lab in bm.LAYOUT["sc_rows"]:
            w.writerow([lab] + [res[n]["scenarios"][lab] for n in ("Base", "Upside", "Downside")])

    with open(OUTDIR / "levers.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario", "lever", "fy2027_margin_change_bps"])
        for name in ("Base", "Upside", "Downside"):
            for lever, bps in res[name]["levers"].items():
                w.writerow([name, lever, round(bps, 1)])
        w.writerow([])
        w.writerow(["scenario", "to get back to the FY2025 margin", "needed"])
        for name in ("Base", "Upside", "Downside"):
            w.writerow([name, "transactions growth", res[name]["needed_tx"]])
            w.writerow([name, "average check growth", res[name]["needed_ck"]])

    wb = values(final)
    print(f"{final.relative_to(ROOT)}: {out['total_formulas']} formulas, {out['total_errors']} errors")
    print("Checks:", wb["Checks"]["B3"].value)
    for name in ("Base", "Upside", "Downside"):
        s = res[name]["scenarios"]
        print(f"  {name:8} FY26 RLM {s['FY2026E restaurant-level margin']:.2%}  FY27 RLM {s['FY2027E restaurant-level margin']:.2%}"
              f"  FY27 EPS ${s['FY2027E diluted EPS']:.2f}"
              f"  to get back to FY25 margin: tx {res[name]['needed_tx']} or check {res[name]['needed_ck']}")
        print("           levers (bps):", {k: round(v) for k, v in res[name]["levers"].items()})


if __name__ == "__main__":
    main()
