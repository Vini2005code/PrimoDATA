"""Rotas do domínio SIASUS (Inteligência Regional / DataSUS).

REGRA DE OURO: este módulo é ISOLADO do domínio clínico. Nenhuma rota aqui
deve consultar a tabela `pacientes`, `conversas`, `mensagens` ou
`dashboard_charts`. Da mesma forma, as rotas em `routes_chat.py`,
`routes_conversations.py`, `routes_dashboard.py` e `routes_reports.py` não
devem consultar `atendimentos_siasus`.

Por enquanto, as rotas retornam stubs vazios — a ingestão dos dados públicos
do DataSUS será implementada em uma próxima entrega.
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.logging_setup import get_logger
from app.db.engine import engine

logger = get_logger(__name__)

router = APIRouter(prefix="/siasus", tags=["siasus"])


def _count_atendimentos() -> int:
    """Total de registros já carregados na tabela `atendimentos_siasus`."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT COUNT(*) FROM atendimentos_siasus")
            ).fetchone()
            return int(row[0]) if row else 0
    except Exception as e:
        logger.warning(f"SIASUS: falha ao contar atendimentos: {e}")
        return 0


@router.get("/")
async def siasus_meta():
    """Metadados gerais do domínio SIASUS (status da ingestão)."""
    total = _count_atendimentos()
    return {
        "modulo": "Portal SIASUS",
        "total_atendimentos": total,
        "status": "aguardando_ingestao" if total == 0 else "operacional",
        "fonte": "Engine Primordial Data — Base SIASUS 2026",
    }


@router.get("/cids-top")
async def siasus_cids_top(limit: int = 10):
    """Top CIDs da região (placeholder — sem dados ainda)."""
    return {
        "labels": [],
        "values": [],
        "total_atendimentos": _count_atendimentos(),
        "limit": max(1, min(limit, 50)),
    }


@router.get("/tendencias-mensais")
async def siasus_tendencias_mensais():
    """Tendências mensais de atendimentos (placeholder — sem dados ainda)."""
    return {
        "labels": [],
        "values": [],
        "total_atendimentos": _count_atendimentos(),
    }


@router.get("/custos")
async def siasus_custos():
    """Custos totais do SUS por município (placeholder — sem dados ainda)."""
    return {
        "labels": [],
        "values": [],
        "total_atendimentos": _count_atendimentos(),
    }
