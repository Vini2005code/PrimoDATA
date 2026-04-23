"""Renderização de gráficos para envio inline (Base64) — usado pelo chat.

Mantido como utilitário de compatibilidade. O frontend usa Chart.js a partir
do `chartData`; este helper continua disponível para casos em que o cliente
precise da imagem pronta.
"""
from __future__ import annotations

import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

from app.core.logging_setup import get_logger

logger = get_logger(__name__)

CHART_COLORS = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
    "#8b5cf6", "#06b6d4", "#f97316", "#ec4899",
]

sns.set_context("talk")
sns.set_style("white")
plt.rcParams["axes.prop_cycle"] = plt.cycler(color=CHART_COLORS[:3])


def gerar_imagem_grafico(plano: dict) -> str:
    """Renderiza o `plano` (resposta da IA) em PNG Base64."""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    tipo = plano.get("tipo_grafico", "bar")
    eixo_x = plano.get("eixo_x", []) or []
    valores = plano.get("valores", []) or []
    cores = CHART_COLORS[: len(eixo_x)] if eixo_x else CHART_COLORS

    try:
        if tipo == "pie":
            ax.pie(valores, labels=eixo_x, autopct="%1.1f%%", startangle=90, colors=cores)
        elif tipo == "donut":
            ax.pie(valores, labels=eixo_x, autopct="%1.1f%%", startangle=90,
                   colors=cores, pctdistance=0.85)
            ax.add_artist(plt.Circle((0, 0), 0.70, fc="#f8fafc"))
        elif tipo == "line":
            ax.plot(eixo_x, valores, marker="o", color=CHART_COLORS[0], linewidth=2)
            ax.fill_between(eixo_x, valores, alpha=0.1, color=CHART_COLORS[0])
        else:
            bars = ax.bar(eixo_x, valores, color=cores)
            ax.bar_label(bars, padding=3, fontweight="bold")

        ax.set_title(plano.get("titulo", "Análise Clínica"),
                     fontsize=14, fontweight="bold", pad=15)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img_b64
    except Exception as e:
        logger.error(f"Erro ao gerar imagem do gráfico: {e}")
        plt.close(fig)
        return ""
