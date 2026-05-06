"""SQL parametrizado para relatórios do mês atual.

Regras invioláveis:
- Janela temporal SEMPRE no banco: data_admissao no mês corrente.
- LIMIT SEMPRE aplicado (cap servidor já validado pelo Pydantic).
- Nomes de coluna NUNCA vêm do request — só da whitelist em sanitize.py.
- Valores filtráveis (status, convenio) entram via bindparams.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.sql import bindparam

from app.core.logging_setup import get_logger
from app.db.engine import engine
from app.schemas.reports import ReportFilters
from app.services.reports.sanitize import (
    allowed_fields,
    validate_fields,
    validate_group_by,
)

logger = get_logger(__name__)

PT_MES = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def current_month_label() -> dict:
    """Identificador human + ISO do mês corrente."""
    today = date.today()
    return {
        "year": today.year,
        "month": today.month,
        "label": f"{PT_MES[today.month]}/{today.year}",
        "iso_start": today.replace(day=1).isoformat(),
    }


def _month_clause() -> str:
    """Cláusula SQL do mês atual — usa CURRENT_DATE no servidor (sem injeção)."""
    return (
        "data_admissao >= date_trunc('month', CURRENT_DATE) "
        "AND data_admissao <  date_trunc('month', CURRENT_DATE) + interval '1 month'"
    )


def _build_where(filters: ReportFilters) -> tuple[str, dict]:
    parts: list[str] = [_month_clause()]
    params: dict = {}
    if filters.status:
        parts.append("status IN :status_list")
        params["status_list"] = tuple(filters.status)
    if filters.convenio:
        parts.append("convenio IN :convenio_list")
        params["convenio_list"] = tuple(filters.convenio)
    return " AND ".join(parts), params


def _expand_in(stmt, params: dict):
    """Expande tuplas de valor em IN (...) com bindparam(expanding=True)."""
    binds = []
    if "status_list" in params:
        binds.append(bindparam("status_list", expanding=True))
    if "convenio_list" in params:
        binds.append(bindparam("convenio_list", expanding=True))
    return stmt.bindparams(*binds) if binds else stmt


def _serialize(value):
    """Converte tipos não-JSON-friendly (date, datetime) para str."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def run_report(filters: ReportFilters) -> dict:
    """Executa o relatório e devolve estrutura uniforme.

    Retorno: {
        "data_type": str,
        "period":   {year, month, label, iso_start},
        "columns":  [...],
        "rows":     [{...}, ...],
        "row_count": int,
        "summary":  {...},   # KPIs auxiliares quando aplicável
    }
    """
    period = current_month_label()
    where, params = _build_where(filters)
    params["lim"] = filters.limit

    if filters.data_type == "bruto":
        cols = validate_fields(filters.fields)
        select_cols = ", ".join(cols)
        sql = f"SELECT {select_cols} FROM pacientes WHERE {where} ORDER BY id LIMIT :lim"
        stmt = _expand_in(text(sql), params)
        with engine.connect() as conn:
            result = conn.execute(stmt, params)
            rows = [
                {k: _serialize(v) for k, v in dict(r._mapping).items()}
                for r in result
            ]
        return {
            "data_type": "bruto",
            "period": period,
            "columns": cols,
            "rows": rows,
            "row_count": len(rows),
            "summary": {"total_no_mes_apos_filtros": len(rows)},
        }

    if filters.data_type == "agregado":
        gb = validate_group_by(filters.group_by or "")
        sql = (
            f"SELECT {gb} AS categoria, COUNT(*) AS total "
            f"FROM pacientes WHERE {where} "
            f"GROUP BY {gb} ORDER BY total DESC LIMIT :lim"
        )
        stmt = _expand_in(text(sql), params)
        with engine.connect() as conn:
            result = conn.execute(stmt, params)
            rows = [
                {"categoria": r[0] if r[0] is not None else "(não informado)", "total": int(r[1])}
                for r in result
            ]
        total_geral = sum(r["total"] for r in rows)
        return {
            "data_type": "agregado",
            "period": period,
            "columns": ["categoria", "total"],
            "rows": rows,
            "row_count": len(rows),
            "summary": {
                "group_by": gb,
                "total_grupos": len(rows),
                "total_geral_no_mes_apos_filtros": total_geral,
            },
        }

    # data_type == "metrica"
    safe_cols = set(allowed_fields())
    pieces = ["COUNT(*) AS total"]
    if "idade" in safe_cols:
        pieces.append("AVG(idade)::numeric(6,1) AS media_idade")
    else:
        pieces.append("0 AS media_idade")
    if "status" in safe_cols:
        pieces += [
            "COUNT(*) FILTER (WHERE status='ativo') AS ativos",
            "COUNT(*) FILTER (WHERE status='alta')  AS altas",
        ]
    else:
        pieces += ["0 AS ativos", "0 AS altas"]

    sql_kpi = f"SELECT {', '.join(pieces)} FROM pacientes WHERE {where}"
    stmt = _expand_in(text(sql_kpi), params)
    with engine.connect() as conn:
        kpi_row = conn.execute(stmt, params).fetchone()

    rows = [
        {"metrica": "Total de pacientes (mês)", "valor": int(kpi_row[0] or 0)},
        {"metrica": "Idade média",              "valor": float(kpi_row[1] or 0)},
        {"metrica": "Pacientes ativos",         "valor": int(kpi_row[2] or 0)},
        {"metrica": "Altas",                    "valor": int(kpi_row[3] or 0)},
    ]
    return {
        "data_type": "metrica",
        "period": period,
        "columns": ["metrica", "valor"],
        "rows": rows,
        "row_count": len(rows),
        "summary": {"escopo": "mês corrente", "filtros_aplicados": params},
    }
