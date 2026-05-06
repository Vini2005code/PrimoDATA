"""Exporta relatório como CSV (UTF-8 com BOM para abrir bem no Excel BR)."""
from __future__ import annotations

import csv
import io


def dump(report: dict) -> tuple[bytes, str, str]:
    columns = report["columns"]
    rows = report["rows"]

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM para Excel
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({c: r.get(c, "") for c in columns})

    period = report["period"]["label"].replace("/", "-")
    filename = f"relatorio-primordial-{report['data_type']}-{period}.csv"
    return buf.getvalue().encode("utf-8"), "text/csv; charset=utf-8", filename
