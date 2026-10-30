"""Read the tables in an SEC HTML filing as lists of cleaned cell values.

The earnings releases spread one number over several cells ("$", "3,104",
"%", "(2.5", "%)"), so each row is rebuilt into: a label plus a list of
numbers in column order. Negative numbers in brackets come back negative.
"""
import html
import re

CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)
NUM = re.compile(r"^\(?-?[\d,]*\.?\d+\)?$")


def _text(fragment):
    t = re.sub(r"<[^>]+>", " ", fragment)
    t = html.unescape(t).replace("​", "").replace("﻿", "")
    return re.sub(r"\s+", " ", t).strip()


def _number(token):
    neg = token.startswith("(") or token.endswith(")")
    value = float(token.strip("()").replace(",", ""))
    return -value if neg else value


def parse_row(row_html):
    cells = [_text(c) for c in CELL.findall(row_html)]
    label_parts, numbers = [], []
    for cell in cells:
        token = cell.replace("$", "").replace("%", "").replace(" ", "")
        if token in ("", "-", "—", "(", ")"):
            if token in ("-", "—") and label_parts:
                numbers.append(0.0)
            continue
        if token.endswith(")") and not token.startswith("(") and numbers:
            continue  # stray closing bracket cell
        if NUM.match(token):
            numbers.append(_number(token))
        elif not numbers:
            label_parts.append(cell)
    return " ".join(label_parts).strip(), numbers


def tables(raw_html):
    """Yield (table_text, rows) where rows = [(label, numbers), ...]."""
    for t in TABLE.findall(raw_html):
        rows = [parse_row(r) for r in ROW.findall(t)]
        rows = [r for r in rows if r[0] or r[1]]
        yield _text(t), rows
