"""Recalculate an .xlsx in LibreOffice and report formula errors.

openpyxl writes formulas without results, so the file is opened and re-saved
by LibreOffice (headless), which computes every formula. Prints JSON:
{"status": "success" | "errors_found", "total_formulas": n, "total_errors": n, "errors": [...]}

Usage: python src/recalc.py path/to/file.xlsx [timeout_seconds]
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

ERRORS = ("#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!", "Err:")


def main(path, timeout=120):
    path = Path(path).resolve()
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print(json.dumps({"error": "LibreOffice (soffice) not found"}))
        sys.exit(1)
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        cmd = [soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--calc",
               "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", tmp, str(path)]
        subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        out = Path(tmp) / path.name
        if not out.exists():
            print(json.dumps({"error": "LibreOffice did not produce a file"}))
            sys.exit(1)
        shutil.copyfile(out, path)

    formulas = load_workbook(path)
    values = load_workbook(path, data_only=True)
    total, errors = 0, []
    for ws in formulas.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    total += 1
                    v = values[ws.title][cell.coordinate].value
                    if isinstance(v, str) and v.startswith(ERRORS):
                        errors.append(f"{ws.title}!{cell.coordinate}: {v}")
    print(json.dumps({"status": "errors_found" if errors else "success", "total_formulas": total,
                      "total_errors": len(errors), "errors": errors[:50]}))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 120)
