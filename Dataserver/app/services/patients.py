"""Acesso a dados da tabela `pacientes` (somente leitura)."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import inspect, text

from app.core.cache import ttl_cache
from app.core.config import settings
from app.core.logging_setup import get_logger
from app.db.engine import engine

logger = get_logger(__name__)


@ttl_cache(seconds=settings.schema_cache_ttl)
def _all_columns() -> list[str]:
    """Lista crua das colunas de `pacientes` (cacheado por TTL)."""
    inspector = inspect(engine)
    return [c["name"] for c in inspector.get_columns("pacientes")]


def _safe_columns() -> list[str]:
    """Retorna apenas colunas que NÃO estão na blacklist LGPD."""
    blacklist = {b.lower() for b in settings.lgpd_blacklist}
    return [c for c in _all_columns() if c.lower() not in blacklist]


def get_clinical_context() -> str:
    """Resumo anonimizado do banco para enviar à IA (LGPD)."""
    try:
        with engine.connect() as conn:
            safe_cols = _safe_columns()
            if not safe_cols:
                return "Aviso: nenhuma coluna segura para LGPD foi encontrada."

            # SEGURANÇA: a interpolação de `safe_cols` na f-string abaixo é segura
            # porque os nomes de coluna NUNCA vêm de input do usuário — vêm
            # exclusivamente do `sqlalchemy.inspect()` (ver `_all_columns`) e
            # passam pela `_safe_columns()`, que aplica a allowlist da LGPD
            # (`settings.lgpd_blacklist`). Valores são parametrizados.
            query = text(
                f"SELECT {', '.join(safe_cols)} FROM pacientes LIMIT :limit"
            )
            df = pd.read_sql(
                query, conn, params={"limit": settings.max_patients_context}
            )

            if df.empty:
                return "O banco está conectado, mas a tabela 'pacientes' está vazia."

            resumo = (
                f"--- RESUMO DO BANCO (Total: {len(df)} registros analisados) ---\n"
            )
            for col in df.select_dtypes(include=["int64", "float64"]).columns:
                resumo += (
                    f"Métrica de {col}: média={df[col].mean():.1f}, "
                    f"min={df[col].min()}, max={df[col].max()}\n"
                )
            return f"{resumo}\nLISTA DE DADOS (Anonimizados):\n{df.to_string(index=False)}"
    except Exception as e:
        logger.error(f"Erro ao extrair contexto clínico: {e}")
        return "Erro técnico: não foi possível ler a estrutura do banco."


def count_patients() -> int:
    """Total absoluto de pacientes."""
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT COUNT(*) FROM pacientes")).fetchone()
            return int(row[0]) if row else 0
    except Exception as e:
        logger.error(f"Erro ao contar pacientes: {e}")
        return 0


def dashboard_metrics() -> dict:
    """KPIs do dashboard, calculados dinamicamente conforme as colunas existentes."""
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            cols = {c["name"].lower() for c in inspector.get_columns("pacientes")}

            parts = ["COUNT(*) as total"]
            parts.append(
                "AVG(idade) as media_idade" if "idade" in cols else "0 as media_idade"
            )
            parts.append(
                "COUNT(DISTINCT diagnostico) as diagnosticos_unicos"
                if "diagnostico" in cols else "0 as diagnosticos_unicos"
            )
            if "status" in cols:
                parts.append("COUNT(CASE WHEN status = 'ativo' THEN 1 END) as ativos")
                parts.append("COUNT(CASE WHEN status = 'alta' THEN 1 END) as altas")
            else:
                parts.append("0 as ativos")
                parts.append("0 as altas")

            row = conn.execute(text(f"SELECT {', '.join(parts)} FROM pacientes")).fetchone()
            if not row:
                return _empty_metrics()
            return {
                "total_pacientes": row[0] or 0,
                "media_idade": round(float(row[1]), 1) if row[1] else 0,
                "diagnosticos_unicos": row[2] or 0,
                "ativos": row[3] or 0,
                "altas": row[4] or 0,
                "colunas_detectadas": sorted(cols),
            }
    except Exception as e:
        logger.error(f"Erro ao calcular métricas do dashboard: {e}")
        return _empty_metrics()


def _empty_metrics() -> dict:
    return {
        "total_pacientes": 0,
        "media_idade": 0,
        "diagnosticos_unicos": 0,
        "ativos": 0,
        "altas": 0,
    }
