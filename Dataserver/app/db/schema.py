"""Schema (DDL) das tabelas usadas pela aplicação.

Idempotente — pode ser executado em todo startup.

NOTA: A tabela `usuarios` foi removida deste DDL porque o módulo de
autenticação está desativado (ver `Dataserver/_disabled/auth/`). Quando o
auth for reativado, o DDL correspondente deve ser restaurado aqui:

    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username VARCHAR(80) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        criada_em TIMESTAMP NOT NULL DEFAULT NOW()
    );
"""
from sqlalchemy import text

from app.core.logging_setup import get_logger
from app.db.engine import engine

logger = get_logger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS conversas (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL DEFAULT 'Nova conversa',
    criada_em TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizada_em TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mensagens (
    id SERIAL PRIMARY KEY,
    conversa_id INTEGER NOT NULL REFERENCES conversas(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL DEFAULT '',
    has_chart BOOLEAN NOT NULL DEFAULT FALSE,
    chart_data JSONB,
    sugestao TEXT,
    criada_em TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mensagens_conversa
    ON mensagens (conversa_id, criada_em);

CREATE TABLE IF NOT EXISTS dashboard_charts (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL DEFAULT 'Gráfico',
    chart_data JSONB NOT NULL,
    posicao INTEGER NOT NULL DEFAULT 0,
    criada_em TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


def init_schema() -> None:
    """Cria todas as tabelas se ainda não existirem."""
    try:
        with engine.begin() as conn:
            for stmt in (s.strip() for s in DDL.split(";") if s.strip()):
                conn.execute(text(stmt))
        logger.info("Schema inicializado.")
    except Exception as e:
        logger.error(f"Falha ao inicializar schema: {e}")
        raise
