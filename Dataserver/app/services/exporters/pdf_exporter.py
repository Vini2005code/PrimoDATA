"""Exporta relatório como PDF — reusa cabeçalho/estilos do `pdf_report`."""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.services.pdf_report import LGPD_NOTICE, PRIMARY_HEX, _new_doc, _styles


def _table(columns: list[str], rows: list[dict]):
    data = [[c.upper() for c in columns]]
    for r in rows:
        data.append(["" if r.get(c) is None else str(r.get(c)) for c in columns])
    t = Table(data, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PRIMARY_HEX)),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.whitesmoke, colors.HexColor("#F0F4F8")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7DEE5")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    return t


def dump(report: dict) -> tuple[bytes, str, str]:
    buf = io.BytesIO()
    doc = _new_doc(buf, "Primordial Data - Relatório")
    st = _styles()

    period = report["period"]
    titulo = (
        f"Relatório Primordial — {report['data_type'].title()} "
        f"({period['label']})"
    )

    story = [
        Paragraph(titulo, st["h1"]),
        Spacer(1, 0.2 * cm),
        Paragraph(
            f"Total de linhas: <b>{report['row_count']}</b> · "
            f"Período: <b>{period['label']}</b>",
            st["body"],
        ),
        Spacer(1, 0.4 * cm),
    ]

    if report["rows"]:
        story.append(_table(report["columns"], report["rows"]))
    else:
        story.append(Paragraph(
            "Nenhum registro encontrado para os filtros aplicados no mês atual.",
            st["body"],
        ))

    summary = report.get("summary") or {}
    if summary:
        story += [
            Spacer(1, 0.5 * cm),
            Paragraph("<b>Resumo</b>", st["body"]),
        ]
        for k, v in summary.items():
            story.append(Paragraph(f"• {k}: {v}", st["body"]))

    story += [Spacer(1, 0.6 * cm), Paragraph(LGPD_NOTICE, st["sub"])]

    doc.build(story)
    pdf_bytes = buf.getvalue()
    period_label = period["label"].replace("/", "-")
    filename = f"relatorio-primordial-{report['data_type']}-{period_label}.pdf"
    return pdf_bytes, "application/pdf", filename
