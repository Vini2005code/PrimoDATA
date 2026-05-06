"""Exporta relatório como JSON (UTF-8, indentado, ensure_ascii=False)."""
from __future__ import annotations

import json


def dump(report: dict) -> tuple[bytes, str, str]:
    payload = {
        "meta": {
            "data_type": report["data_type"],
            "period": report["period"],
            "row_count": report["row_count"],
            "columns": report["columns"],
        },
        "summary": report.get("summary", {}),
        "rows": report["rows"],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    period = report["period"]["label"].replace("/", "-")
    filename = f"relatorio-primordial-{report['data_type']}-{period}.json"
    return body.encode("utf-8"), "application/json; charset=utf-8", filename
