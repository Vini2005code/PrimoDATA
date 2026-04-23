"""Geração de relatórios PDF do Primordial DATA.

Layout:
    - Cabeçalho institucional (logo/marca + data/hora)
    - Bloco de análise textual
    - Gráficos em alta definição (matplotlib)
    - Rodapé LGPD

Usado por main.py em /api/dashboard/export-pdf.
"""
from __future__ import annotations

import io 
import logging
from datetime import datetime
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

logger = logging.getLogger(__name__)

# Paleta HSL convertida para hex (mesma do frontend)
PALETTE_HEX = [
    "#1f8be0",   # primary  hsl(210, 78%, 46%)
    "#1ec1a3",   # accent   hsl(168, 76%, 42%)
    "#f59e0b",   # warning  hsl( 38, 92%, 50%)
    "#ef4444",   # danger   hsl(  0, 84%, 60%)
    "#8b5cf6",   # purple   hsl(262, 80%, 50%)
    "#16a34a",   # success  hsl(142, 76%, 36%)
]
PRIMARY_HEX = PALETTE_HEX[0]


# --------------------------------------------------------------------------
# Helpers de gráfico (matplotlib em alta resolução)
# --------------------------------------------------------------------------

def _render_chart_image(chart_data: dict) -> io.BytesIO | None:
    """Renderiza um chartData {type,title,labels,values} como PNG HD."""
    try:
        tipo = (chart_data.get("type") or "bar").lower()
        labels = chart_data.get("labels") or []
        values = chart_data.get("values") or []
        title = chart_data.get("title") or "Gráfico"
        if not labels or not values:
            return None

        fig, ax = plt.subplots(figsize=(7.5, 4))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        cores = (PALETTE_HEX * ((len(labels) // len(PALETTE_HEX)) + 1))[: len(labels)]

        if tipo == "pie":
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90,
                   colors=cores, textprops={"fontsize": 10})
        elif tipo == "donut":
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90,
                   colors=cores, pctdistance=0.82,
                   wedgeprops=dict(width=0.42, edgecolor="white"),
                   textprops={"fontsize": 10})
        elif tipo == "line":
            ax.plot(labels, values, marker="o", color=PRIMARY_HEX, linewidth=2.2)
            ax.fill_between(range(len(labels)), values, alpha=0.12, color=PRIMARY_HEX)
            ax.grid(alpha=0.25, linestyle="--")
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
        else:  # bar (padrão)
            bars = ax.bar(labels, values, color=cores)
            ax.bar_label(bars, padding=3, fontsize=9, fontweight="bold")
            ax.grid(axis="y", alpha=0.25, linestyle="--")
            ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)

        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=200, bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Falha ao renderizar gráfico para PDF: {e}")
        return None


# --------------------------------------------------------------------------
# Cabeçalho / rodapé
# --------------------------------------------------------------------------

LGPD_NOTICE = (
    "Documento gerado automaticamente pelo Primordial DATA · Inteligência Clínica. "
    "Todos os dados apresentados são agregados e anonimizados em conformidade "
    "com a LGPD (Lei nº 13.709/2018). Este relatório é de uso restrito da "
    "equipe clínica responsável."
)


def _draw_header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4

    # ---- Cabeçalho ----
    canvas.setFillColor(colors.HexColor(PRIMARY_HEX))
    canvas.rect(0, height - 1.3 * cm, width, 1.3 * cm, fill=1, stroke=0)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(2 * cm, height - 0.85 * cm, "Primordial DATA")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(2 * cm, height - 1.15 * cm, "Inteligência Clínica")

    canvas.setFont("Helvetica", 9)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    canvas.drawRightString(width - 2 * cm, height - 1.0 * cm, f"Emitido em {agora}")

    # ---- Rodapé ----
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.6 * cm, width - 2 * cm, 1.6 * cm)

    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica-Oblique", 7.5)
    text = canvas.beginText(2 * cm, 1.25 * cm)
    for linha in _wrap_text(LGPD_NOTICE, 130):
        text.textLine(linha)
    canvas.drawText(text)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#9ca3af"))
    canvas.drawRightString(width - 2 * cm, 0.7 * cm,
                           f"Página {doc.page}")
    canvas.restoreState()


def _wrap_text(text: str, width: int) -> list[str]:
    palavras = text.split()
    linhas, atual = [], ""
    for p in palavras:
        if len(atual) + len(p) + 1 <= width:
            atual = (atual + " " + p).strip()
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------

def gerar_pdf_dashboard(
    charts: Iterable[dict],
    titulo_relatorio: str = "Relatório do Dashboard",
    analise_texto: str | None = None,
) -> bytes:
    """Gera um PDF a partir de uma lista de dicts:

        { "titulo": "...", "chartData": {type, title, labels, values},
          "suggested_insight": "...", "analise": "..." }

    Retorna os bytes do PDF.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.9 * cm,
        bottomMargin=2.0 * cm,
        title="Primordial DATA - Relatório",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16,
                        textColor=colors.HexColor("#0f172a"),
                        spaceAfter=4, leading=20)
    sub = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9.5,
                         textColor=colors.HexColor("#475569"),
                         spaceAfter=14)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12,
                        textColor=colors.HexColor("#0f172a"),
                        spaceBefore=10, spaceAfter=6, leading=16)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10,
                          textColor=colors.HexColor("#1f2937"),
                          spaceAfter=8, leading=14)
    insight = ParagraphStyle("Insight", parent=body, fontSize=9.5,
                             textColor=colors.HexColor("#0d9488"),
                             leftIndent=8, spaceBefore=4, spaceAfter=12,
                             leading=13)

    story: list = []
    story.append(Paragraph(titulo_relatorio, h1))
    story.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", sub))

    if analise_texto:
        story.append(Paragraph("Análise", h2))
        story.append(Paragraph(analise_texto.replace("\n", "<br/>"), body))

    charts = list(charts)
    if not charts:
        story.append(Paragraph(
            "Nenhum gráfico fixado no dashboard no momento.", body))
    else:
        story.append(Paragraph("Gráficos fixados", h2))
        for idx, c in enumerate(charts):
            cd = c.get("chartData") or {}
            titulo = c.get("titulo") or cd.get("title") or f"Gráfico {idx + 1}"
            story.append(Paragraph(titulo, h2))

            img_buf = _render_chart_image(cd)
            if img_buf is not None:
                img = Image(img_buf, width=16 * cm, height=8.5 * cm)
                img.hAlign = "CENTER"
                story.append(img)
            else:
                story.append(Paragraph("(Gráfico indisponível)", body))

            insight_text = c.get("suggested_insight") or c.get("sugestao")
            if insight_text:
                story.append(Paragraph(f"<b>Insight:</b> {insight_text}",
                                       insight))

            story.append(Spacer(1, 0.3 * cm))
            # Quebra de página a cada 2 gráficos para respirar visualmente
            if (idx + 1) % 2 == 0 and idx + 1 < len(charts):
                story.append(PageBreak())

    doc.build(story, onFirstPage=_draw_header_footer,
              onLaterPages=_draw_header_footer)
    return buf.getvalue()
