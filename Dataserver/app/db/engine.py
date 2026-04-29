"""Engine SQLAlchemy compartilhada com fallback automático.

Estratégia:
  1. Tenta o banco primário (`PRIMORDIAL_DATABASE_URL` — PG externo do cliente).
  2. Se a conexão falhar (timeout / refused / DNS), usa o fallback
     (`DATABASE_URL` — PG gerenciado pelo Replit) e registra aviso.
  3. Se ambos falharem, cria o engine apontando para o primário mesmo assim
     (assim os erros aparecem nos endpoints sem derrubar o startup do app).

Isso permite trabalhar localmente sem o tunnel ngrok ativo, sem precisar
mexer em variáveis de ambiente toda hora.
"""
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_CONNECT_TIMEOUT_SECONDS = 3


def _try_create(url: str, label: str) -> Engine | None:
    """Cria o engine e valida com `SELECT 1`. Retorna None se a conexão falhar."""
    try:
        eng = create_engine(
            url,
            connect_args={
                "client_encoding": "utf8",
                "connect_timeout": _CONNECT_TIMEOUT_SECONDS,
            },
            pool_pre_ping=True,
        )
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Banco de dados conectado: fonte={label}")
        return eng
    except Exception as e:
        logger.warning(f"Falha ao conectar no banco ({label}): {e}")
        return None


def _build_engine() -> Engine:
    primary = settings.primary_database_url
    fallback = settings.fallback_database_url

    if primary:
        eng = _try_create(primary, "primário (PRIMORDIAL_DATABASE_URL)")
        if eng is not None:
            return eng
        if fallback and fallback != primary:
            logger.warning(
                "Banco primário indisponível. Usando fallback "
                "(DATABASE_URL do Replit). Quando o tunnel/PG externo "
                "estiver de pé, reinicie o app para voltar ao primário."
            )
            eng = _try_create(fallback, "fallback (DATABASE_URL)")
            if eng is not None:
                return eng

    elif fallback:
        eng = _try_create(fallback, "fallback (DATABASE_URL)")
        if eng is not None:
            return eng

    # Último recurso: cria engine sem validar para não derrubar o startup;
    # erros vão aparecer claramente nos endpoints que usam o banco.
    logger.error("Nenhum banco de dados respondeu. Criando engine ocioso.")
    return create_engine(
        settings.database_url,
        connect_args={"client_encoding": "utf8"},
        pool_pre_ping=True,
    )


engine: Engine = _build_engine()
