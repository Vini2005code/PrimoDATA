"""CRUD dos gráficos fixados no dashboard (limite global)."""
from __future__ import annotations

import json

from sqlalchemy import text

from app.core.config import settings
from app.core.logging_setup import get_logger
from app.db.engine import engine

logger = get_logger(__name__)

CHART_LIMIT = settings.dashboard_chart_limit


def listar() -> list[dict]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, titulo, chart_data, posicao, criada_em "
                    "FROM dashboard_charts ORDER BY posicao ASC, id ASC"
                )
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "titulo": r[1],
                    "chartData": r[2],
                    "posicao": r[3],
                    "criada_em": r[4].isoformat() if r[4] else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Erro ao listar dashboard_charts: {e}")
        return []


def get(chart_id: int) -> dict | None:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                text(
                    "SELECT id, titulo, chart_data, posicao, criada_em "
                    "FROM dashboard_charts WHERE id = :id"
                ),
                {"id": chart_id},
            ).fetchone()
            if not r:
                return None
            return {
                "id": r[0],
                "titulo": r[1],
                "chartData": r[2],
                "posicao": r[3],
                "criada_em": r[4].isoformat() if r[4] else None,
            }
    except Exception as e:
        logger.error(f"Erro ao buscar dashboard_chart {chart_id}: {e}")
        return None


def adicionar(titulo: str, chart_data: dict) -> dict:
    """Insere respeitando o limite. Retorna {ok, id, erro}."""
    if not chart_data or not chart_data.get("type"):
        return {"ok": False, "id": None, "erro": "chartData inválido"}
    try:
        with engine.begin() as conn:
            total = (
                conn.execute(text("SELECT COUNT(*) FROM dashboard_charts")).scalar()
                or 0
            )
            if total >= CHART_LIMIT:
                return {
                    "ok": False,
                    "id": None,
                    "erro": f"Limite de {CHART_LIMIT} gráficos atingido.",
                }
            row = conn.execute(
                text(
                    "INSERT INTO dashboard_charts (titulo, chart_data, posicao) "
                    "VALUES (:t, CAST(:cd AS JSONB), :p) RETURNING id"
                ),
                {
                    "t": (titulo or "Gráfico")[:200],
                    "cd": json.dumps(chart_data),
                    "p": total,
                },
            ).fetchone()
            return {"ok": True, "id": row[0] if row else None, "erro": None}
    except Exception as e:
        logger.error(f"Erro ao adicionar dashboard_chart: {e}")
        return {"ok": False, "id": None, "erro": "erro interno"}


def deletar(chart_id: int) -> bool:
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM dashboard_charts WHERE id = :id"),
                {"id": chart_id},
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao deletar dashboard_chart {chart_id}: {e}")
        return False
