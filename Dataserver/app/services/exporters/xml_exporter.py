"""Exporta relatório como XML estruturado (defusedxml na leitura é
recomendação para parsing; aqui só escrevemos, não parseamos input externo)."""
from __future__ import annotations

import re
from xml.etree.ElementTree import Element, SubElement, tostring


def _safe_tag(name: str) -> str:
    """Garante que um nome seja válido como tag XML."""
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    if not name or not re.match(r"[A-Za-z_]", name[0]):
        name = "f_" + name
    return name


def dump(report: dict) -> tuple[bytes, str, str]:
    root = Element("relatorio_primordial")
    meta = SubElement(root, "meta")
    SubElement(meta, "data_type").text = str(report["data_type"])
    SubElement(meta, "row_count").text = str(report["row_count"])
    period = SubElement(meta, "period")
    for k, v in report["period"].items():
        SubElement(period, _safe_tag(k)).text = str(v)

    summary = SubElement(root, "summary")
    for k, v in (report.get("summary") or {}).items():
        SubElement(summary, _safe_tag(k)).text = str(v)

    columns = report["columns"]
    rows_el = SubElement(root, "rows")
    for r in report["rows"]:
        row_el = SubElement(rows_el, "row")
        for col in columns:
            SubElement(row_el, _safe_tag(col)).text = (
                "" if r.get(col) is None else str(r.get(col))
            )

    body = tostring(root, encoding="utf-8", xml_declaration=True)
    period_label = report["period"]["label"].replace("/", "-")
    filename = f"relatorio-primordial-{report['data_type']}-{period_label}.xml"
    return body, "application/xml; charset=utf-8", filename
