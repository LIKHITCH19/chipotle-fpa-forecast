"""Recalculate an .xlsx with LibreOffice and look for formula errors.

openpyxl saves formulas but not their results, so the file has to be opened
and saved once by a spreadsheet program before the numbers can be read back.
LibreOffice does that headless.

    python src/recalc.py model/chipotle_fpa_model.xlsx
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

BAD = ("#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!", "Err:")


def recalc(path, timeout=120):
    """Recalculate in place. Returns (number of formulas, list of cells with errors)."""
    path = Path(path).resolve()
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("LibreOffice not found (needs soffice on the PATH).")
    with tempfile.TemporaryDirectory() as tmp:
        # a throwaway profile, so it works even if LibreOffice is already open
        profile = Path(tmp) / "profile"
        subprocess.run([soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--calc",
                        "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", tmp, str(path)],
                       capture_output=True, timeout=timeout)
        out = Path(tmp) / path.name
        if not out.exists():
            sys.exit(f"LibreOffice didn't write {path.name}")
        shutil.copyfile(out, path)

    formulas = load_workbook(path)
    values = load_workbook(path, data_only=True)
    n, bad = 0, []
    for ws in formulas.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    n += 1
                    v = values[ws.title][cell.coordinate].value
                    if isinstance(v, str) and v.startswith(BAD):
                        bad.append(f"{ws.title}!{cell.coordinate} {v}")
    return n, bad


if __name__ == "__main__":
    n, bad = recalc(sys.argv[1])
    print(f"{n} formulas, {len(bad)} errors")
    for b in bad[:50]:
        print(" ", b)
