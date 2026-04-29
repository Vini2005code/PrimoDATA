"""Engine SQLAlchemy compartilhada — modo ESTRITO.

Regras:
  1. Se `PRIMORDIAL_DATABASE_URL` estiver definida, ela é AUTORITATIVA.
     Não há fallback automático para `DATABASE_URL` — se a conexão com o
     banco primário falhar, o erro é registrado de forma clara e os
     endpoints retornam erros reais (em vez de "fingir" que estão
     funcionando com os dados de outro banco).
  2. Se `PRIMORDIAL_DATABASE_URL` NÃO estiver definida, usa
     `DATABASE_URL` (caminho legítimo de desenvolvimento puro no Replit).
  3. O engine sempre é criado, mesmo que a conexão falhe no startup,
     para que o servidor suba e os erros sejam visíveis nos endpoints.
"""
from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_CONNECT_TIMEOUT_SECONDS = 5


def _mask_url(url: str) -> str:
    """Esconde a senha em uma URL de conexão para log seguro."""
    try:
        p = urlparse(url)
        host = p.hostname or "?"
        port = p.port or "?"
        db = (p.path or "/").lstrip("/") or "?"
        user = p.username or "?"
        return f"{user}:***@{host}:{port}/{db}"
    except Exception:
        return "<url-mascarada>"


def _create(url: str) -> Engine:
    return create_engine(
        url,
        connect_args={
            "client_encoding": "utf8",
            "connect_timeout": _CONNECT_TIMEOUT_SECONDS,
        },
        pool_pre_ping=True,
    )


def _ping(eng: Engine) -> bool:
    """Valida a conexão com `SELECT 1`."""
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Falha no ping do banco: {e}")
        return False


def _build_engine() -> Engine:
    primary = settings.primary_database_url
    fallback = settings.fallback_database_url

    if primary:
        masked = _mask_url(primary)
        logger.info(
            f"Banco configurado (PRIMORDIAL_DATABASE_URL — modo estrito): {masked}"
        )
        eng = _create(primary)
        if _ping(eng):
            logger.info("✓ Conexão OK com o banco primário.")
        else:
            logger.error(
                "================================================================\n"
                f"  FALHA AO CONECTAR no banco primário: {masked}\n"
                "  O servidor vai subir, mas TODAS as consultas a banco vão\n"
                "  falhar até a conexão voltar. NÃO há fallback automático\n"
                "  para DATABASE_URL — verifique se o PostgreSQL externo está\n"
                "  acessível e se o tunnel ngrok está ativo.\n"
                "================================================================"
            )
        return eng

    if fallback:
        masked = _mask_url(fallback)
        logger.info(
            f"Banco configurado (DATABASE_URL — PRIMORDIAL não definida): {masked}"
        )
        eng = _create(fallback)
        if _ping(eng):
            logger.info("✓ Conexão OK com o banco de desenvolvimento.")
        else:
            logger.error(f"FALHA AO CONECTAR no banco de desenvolvimento: {masked}")
        return eng

    logger.error(
        "NENHUMA URL de banco configurada. "
        "Defina PRIMORDIAL_DATABASE_URL (produção) ou DATABASE_URL (dev)."
    )
    return _create("postgresql://postgres@localhost:5432/postgres")


engine: Engine = _build_engine()
