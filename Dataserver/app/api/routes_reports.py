"""Endpoints da aba 'Relatórios Primordial'.

Auth: por ora desativada (igual ao restante do app). Para reativar, basta
adicionar `dependencies=[Depends(require_user)]` no APIRouter abaixo.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response

from app.core.logging_setup import get_logger
from app.schemas.reports import ReportFilters, ReportFormat
from app.services.exporters import (
    csv_exporter,
    json_exporter,
    pdf_exporter,
    xml_exporter,
)
from app.services.reports import query, sanitize

logger = get_logger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/meta")
def meta() -> JSONResponse:
    """Metadados para a UI montar o formulário (campos, group_by, formatos, mês)."""
    return JSONResponse({
        "period": query.current_month_label(),
        "fields": sanitize.allowed_fields(),
        "group_by_options": sanitize.allowed_group_by(),
        "data_types": ["bruto", "agregado", "metrica"],
        "formats": [f.value for f in ReportFormat],
        "limit": {"min": 1, "max": 1000, "default": 50},
        "blocked_lgpd": sorted(sanitize.blocked_fields()),
    })


@router.post("/preview")
def preview(filters: ReportFilters) -> JSONResponse:
    """Executa o relatório e devolve JSON (mesma forma que /export?format=json,
    mas sem Content-Disposition — usado pela tabela de pré-visualização da UI)."""
    try:
        report = query.run_report(filters)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Erro em /api/reports/preview: {e}")
        raise HTTPException(status_code=500, detail="Falha ao gerar pré-visualização.")
    return JSONResponse(report)


@router.post("/export")
async def export(
    filters: ReportFilters,
    format: ReportFormat = Query(default=ReportFormat.CSV),
) -> Response:
    """Gera o relatório e exporta no formato solicitado.

    - CSV/JSON/XML: serialização leve, em memória.
    - PDF: roda em threadpool (não bloqueia o event loop).
    """
    try:
        report = query.run_report(filters)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Erro ao executar relatório: {e}")
        raise HTTPException(status_code=500, detail="Falha ao gerar relatório.")

    try:
        if format == ReportFormat.CSV:
            body, ctype, fname = csv_exporter.dump(report)
        elif format == ReportFormat.JSON:
            body, ctype, fname = json_exporter.dump(report)
        elif format == ReportFormat.XML:
            body, ctype, fname = xml_exporter.dump(report)
        else:  # PDF
            body, ctype, fname = await run_in_threadpool(pdf_exporter.dump, report)
    except Exception as e:
        logger.error(f"Erro ao exportar {format.value}: {e}")
        raise HTTPException(status_code=500, detail=f"Falha ao exportar {format.value}.")

    return Response(
        content=body,
        media_type=ctype,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
