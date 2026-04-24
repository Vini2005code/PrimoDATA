"""Rotas do dashboard: gráficos fixados + exportação de PDF (consolidada e individual)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response

from app.core.logging_setup import get_logger
from app.schemas.chat import ExportChartIn, FixarChartIn
from app.services import dashboard_charts
from app.services.pdf_report import gerar_pdf_chart, gerar_pdf_dashboard

logger = get_logger(__name__)
router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M")


def _slug(text: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyz0123456789-"
    s = (text or "grafico").lower().replace(" ", "-")
    return "".join(c for c in s if c in keep)[:60] or "grafico"


# ---------------------------------------------------------------------------
# CRUD de gráficos fixados
# ---------------------------------------------------------------------------

@router.get("/charts")
async def listar():
    return JSONResponse({
        "charts": dashboard_charts.listar(),
        "limite": dashboard_charts.CHART_LIMIT,
    })


@router.post("/charts")
async def fixar(req: FixarChartIn):
    cd = req.chartData.model_dump()
    titulo = req.titulo or cd.get("title") or "Gráfico"
    res = dashboard_charts.adicionar(titulo, cd)
    if not res["ok"]:
        raise HTTPException(status_code=400,
                            detail=res["erro"] or "Falha ao fixar gráfico.")
    return JSONResponse({"id": res["id"], "titulo": titulo})


@router.delete("/charts/{chart_id}")
async def deletar(chart_id: int):
    if not dashboard_charts.deletar(chart_id):
        raise HTTPException(status_code=500, detail="Falha ao remover gráfico.")
    return JSONResponse({"ok": True, "id": chart_id})


# ---------------------------------------------------------------------------
# Exportação PDF
# ---------------------------------------------------------------------------

@router.get("/export-pdf")
async def export_dashboard_pdf():
    """PDF consolidado de todos os gráficos fixados."""
    try:
        charts = dashboard_charts.listar()
        pdf_bytes = await run_in_threadpool(
            gerar_pdf_dashboard,
            charts,
            "Relatório Clínico - Dashboard",
            (
                "Visão consolidada dos indicadores fixados pela equipe clínica. "
                "Os gráficos a seguir refletem o estado atual da base de pacientes."
            ),
        )
        filename = f"primordial-data-dashboard-{_ts()}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.error(f"Erro ao gerar PDF do dashboard: {e}")
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF.")


@router.get("/charts/{chart_id}/export-pdf")
async def export_pinned_chart_pdf(chart_id: int):
    """PDF de UM gráfico já fixado no dashboard."""
    chart = dashboard_charts.get(chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Gráfico não encontrado.")
    try:
        pdf_bytes = await run_in_threadpool(
            gerar_pdf_chart,
            chart["chartData"] or {},
            chart.get("titulo"),
        )
        filename = f"primordial-data-{_slug(chart.get('titulo') or '')}-{_ts()}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.error(f"Erro ao gerar PDF do chart {chart_id}: {e}")
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF.")


@router.post("/charts/export-pdf")
async def export_chart_inline_pdf(req: ExportChartIn):
    """PDF de um gráfico ainda NÃO fixado (vindo direto do chat)."""
    cd = req.chartData.model_dump()
    if not cd.get("type") or not (cd.get("labels") and cd.get("values")):
        raise HTTPException(status_code=400,
                            detail="chartData inválido (faltam labels/values/type).")
    try:
        titulo = req.titulo or cd.get("title") or "Gráfico"
        pdf_bytes = await run_in_threadpool(
            gerar_pdf_chart,
            cd,
            titulo,
            req.suggested_insight,
            req.analise,
        )
        filename = f"primordial-data-{_slug(titulo)}-{_ts()}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.error(f"Erro ao gerar PDF inline: {e}")
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF.")
