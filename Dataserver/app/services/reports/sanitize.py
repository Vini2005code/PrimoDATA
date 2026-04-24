"""Whitelist de campos e enforcement LGPD para Relatórios.

Camada dupla de proteção:
  1. `allowed_fields()` retorna apenas colunas que NÃO estão na blacklist LGPD.
  2. `validate_fields()` rejeita explicitamente qualquer campo bloqueado,
     mesmo que o usuário tente burlar a whitelist do client.

Toda tentativa de acessar campo PII é registrada no canal `primordial.lgpd.audit`.
"""
from __future__ import annotations

from sqlalchemy import inspect

from app.core.cache import ttl_cache
from app.core.config import settings
from app.core.logging_setup import get_logger
from app.db.engine import engine

logger = get_logger(__name__)
audit = get_logger("primordial.lgpd.audit")

# Tipos categóricos seguros para GROUP BY (não numéricos, não datas, não PII).
_CATEGORICAL_HINTS = {"sexo", "diagnostico", "convenio", "status"}


@ttl_cache(seconds=settings.schema_cache_ttl)
def _columns_meta() -> dict[str, str]:
    """{coluna_lower: tipo_str} — cacheado pelo TTL de schema."""
    inspector = inspect(engine)
    return {
        c["name"].lower(): str(c["type"]).lower()
        for c in inspector.get_columns("pacientes")
    }


def blocked_fields() -> set[str]:
    """Campos LGPD bloqueados: união da blacklist com qualquer coluna PII conhecida."""
    return {b.lower() for b in settings.lgpd_blacklist}


def allowed_fields() -> list[str]:
    """Lista ordenada de colunas seguras (não-PII) disponíveis para o relatório."""
    blocked = blocked_fields()
    return sorted(c for c in _columns_meta() if c not in blocked)


def allowed_group_by() -> list[str]:
    """Subset categórico seguro para usar em GROUP BY."""
    safe = set(allowed_fields())
    return sorted(c for c in safe if c in _CATEGORICAL_HINTS)


def validate_fields(requested: list[str]) -> list[str]:
    """Garante que todos os campos pedidos existem E não são PII.

    Levanta ValueError com mensagem clara em caso de violação.
    Registra tentativa de acesso a PII no log de auditoria.
    """
    if not requested:
        return []
    cols = set(_columns_meta())
    blocked = blocked_fields()
    safe = set(allowed_fields())

    bad_pii = [f for f in requested if f in blocked]
    if bad_pii:
        audit.warning(
            f"Tentativa de exportar campos LGPD bloqueados: {bad_pii}"
        )
        raise ValueError(
            f"Campos protegidos pela LGPD não podem ser exportados: {', '.join(bad_pii)}."
        )

    bad_unknown = [f for f in requested if f not in cols]
    if bad_unknown:
        raise ValueError(
            f"Campos inexistentes na tabela pacientes: {', '.join(bad_unknown)}."
        )

    bad_filtered = [f for f in requested if f not in safe]
    if bad_filtered:
        raise ValueError(
            f"Campos não disponíveis para relatório: {', '.join(bad_filtered)}."
        )

    return requested


def validate_group_by(field: str) -> str:
    """Valida que o group_by está na lista de categóricos permitidos."""
    if field not in set(allowed_group_by()):
        raise ValueError(
            f"group_by inválido. Use um de: {', '.join(allowed_group_by())}."
        )
    return field
