"""CRUD de conversas e mensagens (chat com persistência)."""
from __future__ import annotations

import json

from sqlalchemy import text

from app.core.logging_setup import get_logger
from app.db.engine import engine

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Helpers de domínio
# ----------------------------------------------------------------------

def plano_to_chart_data(plano: dict | None) -> dict | None:
    """Converte o `plano` da IA → formato chartData consumido pelo frontend."""
    if not plano:
        return None
    tipo = plano.get("tipo_grafico")
    if not tipo or tipo == "null":
        return None
    return {
        "type": tipo,
        "title": plano.get("titulo") or "",
        "labels": plano.get("eixo_x") or [],
        "values": plano.get("valores") or [],
    }


# ----------------------------------------------------------------------
# Conversas
# ----------------------------------------------------------------------

def criar_conversa(titulo: str = "Nova conversa") -> int | None:
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text("INSERT INTO conversas (titulo) VALUES (:t) RETURNING id"),
                {"t": (titulo or "Nova conversa")[:200]},
            ).fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao criar conversa: {e}")
        return None


def renomear_conversa(conversa_id: int, titulo: str) -> bool:
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE conversas SET titulo = :t, atualizada_em = NOW() "
                    "WHERE id = :id"
                ),
                {"t": (titulo or "")[:200], "id": conversa_id},
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao renomear conversa {conversa_id}: {e}")
        return False


def deletar_conversa(conversa_id: int) -> bool:
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM conversas WHERE id = :id"),
                {"id": conversa_id},
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao deletar conversa {conversa_id}: {e}")
        return False


def listar_conversas(limite: int = 100) -> list[dict]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, titulo, criada_em, atualizada_em "
                    "FROM conversas ORDER BY atualizada_em DESC LIMIT :l"
                ),
                {"l": limite},
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "titulo": r[1],
                    "criada_em": r[2].isoformat() if r[2] else None,
                    "atualizada_em": r[3].isoformat() if r[3] else None,
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Erro ao listar conversas: {e}")
        return []


def get_conversa(conversa_id: int) -> dict | None:
    try:
        with engine.connect() as conn:
            cab = conn.execute(
                text(
                    "SELECT id, titulo, criada_em, atualizada_em "
                    "FROM conversas WHERE id = :id"
                ),
                {"id": conversa_id},
            ).fetchone()
            if not cab:
                return None

            msgs = conn.execute(
                text(
                    "SELECT id, role, content, has_chart, chart_data, sugestao, criada_em "
                    "FROM mensagens WHERE conversa_id = :id "
                    "ORDER BY criada_em ASC, id ASC"
                ),
                {"id": conversa_id},
            ).fetchall()

            return {
                "id": cab[0],
                "titulo": cab[1],
                "criada_em": cab[2].isoformat() if cab[2] else None,
                "atualizada_em": cab[3].isoformat() if cab[3] else None,
                "messages": [
                    {
                        "id": m[0],
                        "role": m[1],
                        "content": m[2] or "",
                        "hasChart": bool(m[3]),
                        "chartData": m[4],
                        "sugestao": m[5],
                        "criada_em": m[6].isoformat() if m[6] else None,
                    }
                    for m in msgs
                ],
            }
    except Exception as e:
        logger.error(f"Erro ao buscar conversa {conversa_id}: {e}")
        return None


# ----------------------------------------------------------------------
# Mensagens
# ----------------------------------------------------------------------

def adicionar_mensagem(
    conversa_id: int,
    role: str,
    content: str,
    chart_data: dict | None = None,
    sugestao: str | None = None,
) -> int | None:
    if role not in ("user", "assistant"):
        raise ValueError("role deve ser 'user' ou 'assistant'")
    try:
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO mensagens "
                    "(conversa_id, role, content, has_chart, chart_data, sugestao) "
                    "VALUES (:cid, :r, :c, :h, CAST(:cd AS JSONB), :s) RETURNING id"
                ),
                {
                    "cid": conversa_id,
                    "r": role,
                    "c": content or "",
                    "h": bool(chart_data),
                    "cd": json.dumps(chart_data) if chart_data is not None else None,
                    "s": sugestao,
                },
            ).fetchone()
            conn.execute(
                text("UPDATE conversas SET atualizada_em = NOW() WHERE id = :id"),
                {"id": conversa_id},
            )
            return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao adicionar mensagem na conversa {conversa_id}: {e}")
        return None
