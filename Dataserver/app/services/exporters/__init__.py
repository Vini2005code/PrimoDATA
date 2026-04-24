"""Exportadores multi-formato. Cada módulo recebe a saída uniforme de
`reports.query.run_report` e devolve `(bytes, content_type, suggested_filename)`.
"""
from app.services.exporters import (
    csv_exporter,
    json_exporter,
    pdf_exporter,
    xml_exporter,
)

__all__ = ["csv_exporter", "json_exporter", "xml_exporter", "pdf_exporter"]
