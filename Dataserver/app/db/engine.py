"""Engine SQLAlchemy compartilhada."""
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings

# Engine único para toda a aplicação. `client_encoding=utf8` evita
# problemas com acentuação em Postgres locais.
engine: Engine = create_engine(
    settings.database_url,
    connect_args={"client_encoding": "utf8"},
    pool_pre_ping=True,
)
